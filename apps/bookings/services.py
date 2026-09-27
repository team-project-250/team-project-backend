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
    """Raised when a booking's date range is invalid (end before start,
    or the start date is in the past)."""


class EquipmentNotInCityError(BookingError):
    """Raised when equipment is booked for a city it isn't available in."""


class EquipmentNotAvailableError(BookingError):
    """Raised when equipment already has a conflicting booking for the
    requested date range."""


def generate_booking_number() -> str:
    """Generate a random, currently-unused booking number.

    Returns:
        A string like ``"ER-12345"`` that no existing
        :class:`~apps.bookings.models.Booking` currently uses.

    Raises:
        RuntimeError: If no unused number was found after 10 attempts
            (astronomically unlikely with a 100,000-number space).
    """
    for _ in range(10):
        candidate = "ER-" + "".join(random.choices(string.digits, k=5))
        if not Booking.objects.filter(number=candidate).exists():
            return candidate
    raise RuntimeError("Could not generate a unique booking number")


def calculate_rental_days(start_date: date, end_date: date) -> int:
    """Count rental days inclusively (both the start and end date count).

    Args:
        start_date: The first day of the rental.
        end_date: The last day of the rental.

    Returns:
        The number of days, e.g. 1 for the same start/end date.
    """
    return (end_date - start_date).days + 1


def quote_price(
    *, equipment: Equipment, start_date: date, end_date: date, delivery_method: str
) -> dict:
    """Compute the price breakdown for a rental, without creating a booking.

    Args:
        equipment: The equipment being priced.
        start_date: The first day of the rental.
        end_date: The last day of the rental.
        delivery_method: One of ``Booking.DeliveryMethod``'s values; only
            ``"courier"`` adds :data:`DELIVERY_FEE`.

    Returns:
        A dict with ``rental_days``, ``price_per_day``, ``delivery_fee``
        and ``total_price``.
    """
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
    """Validate a rental date range.

    Args:
        start_date: The first day of the rental.
        end_date: The last day of the rental.

    Raises:
        InvalidDateRangeError: If `end_date` is before `start_date`, or
            `start_date` is before today (Kyiv local date).
    """
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
    doesn't require a city).

    Args:
        equipment: The equipment to check.
        start_date: The first day of the requested rental.
        end_date: The last day of the requested rental.
        exclude_booking_id: A booking pk to ignore when checking for
            conflicts — used when re-validating an existing booking
            (e.g. on update) against itself.

    Raises:
        EquipmentNotAvailableError: If an active booking for `equipment`
            overlaps the given date range.
    """
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
    """Validate that `equipment` can be booked in `city` for the given dates.

    Args:
        equipment: The equipment to check.
        city: The :class:`~apps.locations.models.City` the booking is for.
        start_date: The first day of the requested rental.
        end_date: The last day of the requested rental.
        exclude_booking_id: See :func:`assert_no_overlap`.

    Raises:
        EquipmentNotInCityError: If `equipment` isn't listed as available
            in `city`.
        EquipmentNotAvailableError: If the dates conflict with an existing
            active booking — see :func:`assert_no_overlap`.
    """
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
    """Validate and create a booking, with its price frozen at creation time.

    Locks the equipment row (``select_for_update``) before checking for
    overlaps, so two concurrent requests for the same equipment can't both
    succeed for conflicting dates.

    Args:
        equipment: The equipment to book.
        city: The :class:`~apps.locations.models.City` to book it in.
        customer_name: The customer's full name.
        customer_phone: The customer's phone number (``+380XXXXXXXXX``).
        customer_email: The customer's email address.
        start_date: The first day of the rental.
        end_date: The last day of the rental.
        delivery_method: One of ``Booking.DeliveryMethod``'s values.
        payment_method: One of ``Booking.PaymentMethod``'s values.
        delivery_address: Required only when `delivery_method` is courier.
        comment: An optional free-text note from the customer.

    Returns:
        The newly created :class:`~apps.bookings.models.Booking`.

    Raises:
        InvalidDateRangeError: See :func:`assert_dates_valid`.
        EquipmentNotInCityError: See :func:`assert_available`.
        EquipmentNotAvailableError: See :func:`assert_available`.
        django.db.IntegrityError: If a unique booking number still
            couldn't be reserved after :data:`NUMBER_COLLISION_RETRIES`
            attempts (a concurrent booking for other equipment keeps
            grabbing the same generated number).
    """
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
    """Raised when a booking number/phone combination doesn't match any
    booking."""


class BookingNotCancellableError(BookingError):
    """Raised when a booking exists but is no longer eligible for
    cancellation (wrong status, or the rental has already started)."""


def get_bookings_by_phone(phone: str):
    """Look up every booking made with a given phone number.

    Args:
        phone: The customer's phone number, exactly as stored.

    Returns:
        A ``QuerySet`` of :class:`~apps.bookings.models.Booking`, newest
        first.
    """
    return Booking.objects.filter(customer_phone=phone).order_by("-created_at")


def cancel_booking(*, number: str, phone: str) -> Booking:
    """Cancel a booking, if the phone number matches and it's still eligible.

    Args:
        number: The booking number (e.g. ``"ER-12345"``).
        phone: The phone number that must match the booking's
            `customer_phone` (the only "credential" a customer has, since
            there are no accounts).

    Returns:
        The now-cancelled :class:`~apps.bookings.models.Booking`.

    Raises:
        BookingNotFoundError: If no booking matches both `number` and
            `phone` together (a wrong phone gives the same error as a
            wrong number, so the error message can't be used to confirm
            a guessed booking number).
        BookingNotCancellableError: If the booking's status isn't
            pending/confirmed, or its rental has already started.
    """
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

    Args:
        phone: The customer's phone number (``+380XXXXXXXXX``).
        equipment: The equipment the customer is interested in, if any.
        start_date: The first day the customer wants, if given.
        end_date: The last day the customer wants, if given.
        comment: An optional free-text note.

    Returns:
        A ``(request, created)`` tuple — `created` is `False` when an
        identical, still-unprocessed request for the same phone +
        equipment was submitted within the last few minutes (double
        submit / accidental resend), in which case the existing request
        is returned instead of creating a duplicate.

    Raises:
        InvalidDateRangeError: See :func:`assert_dates_valid` (only when
            both dates are given).
        EquipmentNotAvailableError: See :func:`assert_no_overlap` (only
            when both dates and `equipment` are given).
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
