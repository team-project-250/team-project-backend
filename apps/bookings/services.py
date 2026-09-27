"""Booking business logic — pricing, availability and creation.

Concurrency: create_booking() takes a row lock on the Equipment being
booked (select_for_update) before checking for overlapping bookings.
This serialises concurrent booking attempts for the SAME equipment —
a plain overlap query on Booking cannot do that on its own, because a
SELECT ... FOR UPDATE on a query matching zero rows locks nothing.
"""

import random
import string
from datetime import date, timedelta
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.bookings.models import Booking, CallbackRequest
from apps.catalog.models import Equipment

DELIVERY_FEE = Decimal("100.00")

NUMBER_COLLISION_RETRIES = 3

# How long a repeat "1-click" request for the same phone + equipment is
# treated as a duplicate (double submit / accidental resend) rather than a
# new lead.
CALLBACK_DUPLICATE_WINDOW = timedelta(minutes=5)


class BookingError(Exception):
    """Base class for booking validation failures."""


class InvalidDateRangeError(BookingError):
    pass


class EquipmentNotInCityError(BookingError):
    pass


class EquipmentNotAvailableError(BookingError):
    pass


def generate_booking_number() -> str:
    for _ in range(10):
        candidate = "ER-" + "".join(random.choices(string.digits, k=5))
        if not Booking.objects.filter(number=candidate).exists():
            return candidate
    raise RuntimeError("Could not generate a unique booking number")


def calculate_rental_days(start_date: date, end_date: date) -> int:
    return (end_date - start_date).days + 1


def quote_price(
    *, equipment: Equipment, start_date: date, end_date: date, delivery_method: str
) -> dict:
    rental_days = calculate_rental_days(start_date, end_date)
    delivery_fee = (
        DELIVERY_FEE
        if delivery_method == Booking.DeliveryMethod.COURIER
        else Decimal("0")
    )
    total_price = equipment.price_per_day * rental_days + delivery_fee
    return {
        "rental_days": rental_days,
        "price_per_day": equipment.price_per_day,
        "delivery_fee": delivery_fee,
        "total_price": total_price,
    }


def assert_dates_valid(start_date: date, end_date: date) -> None:
    if end_date < start_date:
        raise InvalidDateRangeError("Дата завершення не може бути раніше дати початку.")
    if start_date < timezone.localdate():
        raise InvalidDateRangeError("Дата початку оренди не може бути в минулому.")


def assert_no_overlap(
    *, equipment: Equipment, start_date: date, end_date: date, exclude_booking_id=None
) -> None:
    """Raise if `equipment` already has an active booking touching this
    date range. Shared by the full booking flow (assert_available, which
    also checks the city) and the "1-click" quick-booking flow (which
    doesn't require a city)."""
    conflicts = Booking.objects.filter(
        equipment=equipment,
        status__in=Booking.ACTIVE_STATUSES,
        start_date__lte=end_date,
        end_date__gte=start_date,
    )
    if exclude_booking_id:
        conflicts = conflicts.exclude(pk=exclude_booking_id)
    if conflicts.exists():
        raise EquipmentNotAvailableError(
            f"«{equipment.name}» вже заброньована на обрані дати."
        )


def assert_available(
    *,
    equipment: Equipment,
    city,
    start_date: date,
    end_date: date,
    exclude_booking_id=None,
) -> None:
    if not equipment.available_cities.filter(pk=city.pk).exists():
        raise EquipmentNotInCityError(
            f"«{equipment.name}» недоступна у місті {city.name}."
        )
    assert_no_overlap(
        equipment=equipment,
        start_date=start_date,
        end_date=end_date,
        exclude_booking_id=exclude_booking_id,
    )


@transaction.atomic
def create_booking(
    *,
    equipment: Equipment,
    city,
    customer_name: str,
    customer_phone: str,
    customer_email: str,
    start_date: date,
    end_date: date,
    delivery_method: str,
    payment_method: str,
    delivery_address: str = "",
    comment: str = "",
) -> Booking:
    # Lock the equipment row so two concurrent requests for it serialise.
    equipment = Equipment.objects.select_for_update().get(pk=equipment.pk)

    assert_dates_valid(start_date, end_date)
    assert_available(
        equipment=equipment, city=city, start_date=start_date, end_date=end_date
    )
    pricing = quote_price(
        equipment=equipment,
        start_date=start_date,
        end_date=end_date,
        delivery_method=delivery_method,
    )

    fields = {
        "equipment": equipment,
        "city": city,
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "customer_email": customer_email,
        "start_date": start_date,
        "end_date": end_date,
        "delivery_method": delivery_method,
        "delivery_address": delivery_address,
        "payment_method": payment_method,
        "comment": comment,
        **pricing,
    }
    # generate_booking_number() checks for uniqueness, but a concurrent
    # booking for OTHER equipment (not covered by the row lock above) can
    # still grab the same number in between — retry instead of a 500.
    for attempt in range(NUMBER_COLLISION_RETRIES):
        try:
            with transaction.atomic():
                return Booking.objects.create(
                    number=generate_booking_number(), **fields
                )
        except IntegrityError:
            if attempt == NUMBER_COLLISION_RETRIES - 1:
                raise
    raise AssertionError("unreachable")


class BookingNotFoundError(BookingError):
    pass


class BookingNotCancellableError(BookingError):
    pass


def get_bookings_by_phone(phone: str):
    return Booking.objects.filter(customer_phone=phone).order_by("-created_at")


def cancel_booking(*, number: str, phone: str) -> Booking:
    try:
        booking = Booking.objects.get(number=number, customer_phone=phone)
    except Booking.DoesNotExist as exc:
        raise BookingNotFoundError("Бронювання не знайдено.") from exc

    if booking.status not in (Booking.Status.PENDING, Booking.Status.CONFIRMED):
        raise BookingNotCancellableError("Це бронювання вже не можна скасувати.")
    if booking.start_date <= timezone.localdate():
        raise BookingNotCancellableError("Оренда вже почалась — скасування недоступне.")

    booking.status = Booking.Status.CANCELLED
    booking.save(update_fields=["status", "updated_at"])
    return booking


def submit_callback_request(
    *,
    phone: str,
    equipment: Equipment | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    comment: str = "",
) -> tuple[CallbackRequest, bool]:
    """ "Забронювати в 1 клік" — a lead for a manager to call back, not a
    real reservation (see the Card-page summary for why CallbackRequest
    was chosen over Booking here).

    If both dates are given, they're validated the same way a real
    booking's dates are (not in the past, end >= start) and, when
    equipment is also given, checked for a date conflict — but a
    request with no dates (just a phone number) is always accepted, to
    keep the "1-click" flow genuinely low-friction.

    Returns (request, created) — `created` is False when an identical,
    still-unprocessed request for the same phone + equipment was
    submitted within the last few minutes (double submit / accidental
    resend), in which case the existing request is returned instead of
    creating a duplicate.
    """
    if start_date is not None and end_date is not None:
        assert_dates_valid(start_date, end_date)
        if equipment is not None:
            assert_no_overlap(
                equipment=equipment, start_date=start_date, end_date=end_date
            )

    if equipment is not None:
        existing = CallbackRequest.objects.filter(
            phone=phone,
            equipment=equipment,
            is_processed=False,
            created_at__gte=timezone.now() - CALLBACK_DUPLICATE_WINDOW,
        ).first()
        if existing is not None:
            return existing, False

    request = CallbackRequest.objects.create(
        phone=phone,
        equipment=equipment,
        start_date=start_date,
        end_date=end_date,
        comment=comment,
    )
    return request, True
