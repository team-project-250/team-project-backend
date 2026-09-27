import datetime
from decimal import Decimal

import pytest
from django.db import IntegrityError
from django.utils import timezone

from apps.bookings.models import Booking
from apps.bookings.services import (
    EquipmentNotAvailableError,
    EquipmentNotInCityError,
    InvalidDateRangeError,
    calculate_rental_days,
    create_booking,
    generate_booking_number,
    quote_price,
)
from apps.catalog.models import Category, Equipment
from apps.locations.models import City

pytestmark = pytest.mark.django_db


def today_plus(days):
    return timezone.localdate() + datetime.timedelta(days=days)


@pytest.fixture
def city():
    return City.objects.create(name="Луцьк", slug="lutsk", is_default=True)


@pytest.fixture
def equipment(city):
    category = Category.objects.create(name="Пилососи", slug="vacuum-cleaners")
    eq = Equipment.objects.create(
        name="Karcher Puzzi 8/1",
        slug="karcher-puzzi-8-1",
        sku="PUZZI-8-1",
        category=category,
        price_per_day=Decimal("650.00"),
    )
    eq.available_cities.add(city)
    return eq


def make_booking(equipment, city, **overrides):
    data = {
        "equipment": equipment,
        "city": city,
        "customer_name": "Іван",
        "customer_phone": "+380501234567",
        "customer_email": "ivan@example.com",
        "start_date": today_plus(1),
        "end_date": today_plus(2),
        "delivery_method": Booking.DeliveryMethod.PICKUP,
        "payment_method": Booking.PaymentMethod.CASH,
    }
    data.update(overrides)
    return create_booking(**data)


def test_calculate_rental_days_is_inclusive():
    assert calculate_rental_days(today_plus(1), today_plus(1)) == 1
    assert calculate_rental_days(today_plus(1), today_plus(3)) == 3


def test_quote_price_courier_adds_delivery_fee(equipment):
    quote = quote_price(
        equipment=equipment,
        start_date=today_plus(1),
        end_date=today_plus(2),
        delivery_method=Booking.DeliveryMethod.COURIER,
    )
    assert quote["delivery_fee"] == Decimal("100.00")
    assert quote["total_price"] == Decimal("650.00") * 2 + Decimal("100.00")


def test_quote_price_pickup_has_no_delivery_fee(equipment):
    quote = quote_price(
        equipment=equipment,
        start_date=today_plus(1),
        end_date=today_plus(1),
        delivery_method=Booking.DeliveryMethod.PICKUP,
    )
    assert quote["delivery_fee"] == Decimal("0")


def test_booking_number_format_and_uniqueness():
    numbers = {generate_booking_number() for _ in range(20)}
    assert len(numbers) == 20
    for number in numbers:
        assert number.startswith("ER-") and len(number) == 8


def test_create_booking_happy_path(equipment, city):
    booking = make_booking(equipment, city, end_date=today_plus(2))
    assert booking.rental_days == 2
    assert booking.total_price == Decimal("1300.00")
    assert booking.status == Booking.Status.PENDING


def test_create_booking_rejects_past_start_date(equipment, city):
    with pytest.raises(InvalidDateRangeError):
        make_booking(equipment, city, start_date=today_plus(-1))


def test_create_booking_rejects_wrong_city(equipment):
    other_city = City.objects.create(name="Одеса", slug="odesa")
    with pytest.raises(EquipmentNotInCityError):
        make_booking(equipment, other_city)


def test_create_booking_rejects_overlapping_dates(equipment, city):
    make_booking(equipment, city, start_date=today_plus(5), end_date=today_plus(10))
    with pytest.raises(EquipmentNotAvailableError):
        make_booking(equipment, city, start_date=today_plus(8), end_date=today_plus(12))


def test_cancelled_booking_does_not_block_new_one(equipment, city):
    first = make_booking(
        equipment, city, start_date=today_plus(5), end_date=today_plus(10)
    )
    first.status = Booking.Status.CANCELLED
    first.save(update_fields=["status"])

    second = make_booking(
        equipment, city, start_date=today_plus(8), end_date=today_plus(12)
    )
    assert second.number != first.number


def test_create_booking_retries_on_booking_number_collision(
    equipment, city, monkeypatch
):
    first = make_booking(equipment, city)
    numbers = iter([first.number, "ER-99999"])
    monkeypatch.setattr(
        "apps.bookings.services.generate_booking_number", lambda: next(numbers)
    )

    second = make_booking(
        equipment, city, start_date=today_plus(5), end_date=today_plus(6)
    )
    assert second.number == "ER-99999"


def test_create_booking_gives_up_after_repeated_collisions(
    equipment, city, monkeypatch
):
    first = make_booking(equipment, city)
    monkeypatch.setattr(
        "apps.bookings.services.generate_booking_number", lambda: first.number
    )

    with pytest.raises(IntegrityError):
        make_booking(equipment, city, start_date=today_plus(5), end_date=today_plus(6))
