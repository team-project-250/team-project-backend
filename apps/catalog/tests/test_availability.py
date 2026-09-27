import datetime
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.bookings.models import Booking
from apps.bookings.services import create_booking
from apps.catalog.models import Category, Equipment
from apps.catalog.services import equipment_availability
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


def make_booking(equipment, city, start, end):
    return create_booking(
        equipment=equipment,
        city=city,
        customer_name="Іван",
        customer_phone="+380501234567",
        customer_email="ivan@example.com",
        start_date=start,
        end_date=end,
        delivery_method=Booking.DeliveryMethod.PICKUP,
        payment_method=Booking.PaymentMethod.CASH,
    )


def test_equipment_available_with_no_bookings(equipment):
    result = equipment_availability(equipment, timezone.localdate())
    assert result == {"status": "available", "available_from": None}


def test_equipment_booked_today(equipment, city):
    booking = make_booking(equipment, city, today_plus(0), today_plus(2))
    result = equipment_availability(equipment, timezone.localdate())
    assert result["status"] == "booked"
    assert result["available_from"] == booking.end_date + datetime.timedelta(days=1)


def test_cancelled_booking_does_not_block(equipment, city):
    booking = make_booking(equipment, city, today_plus(0), today_plus(2))
    booking.status = Booking.Status.CANCELLED
    booking.save(update_fields=["status"])

    result = equipment_availability(equipment, timezone.localdate())
    assert result["status"] == "available"


def test_list_includes_availability(client, equipment):
    data = client.get("/api/equipment/").json()
    assert data["results"][0]["availability"] == {
        "status": "available",
        "available_from": None,
    }


def test_detail_includes_availability(client, equipment, city):
    booking = make_booking(equipment, city, today_plus(0), today_plus(2))
    data = client.get(f"/api/equipment/{equipment.slug}/").json()
    assert data["availability"]["status"] == "booked"
    assert (
        data["availability"]["available_from"]
        == (booking.end_date + datetime.timedelta(days=1)).isoformat()
    )


def test_filter_availability(client, equipment, city):
    make_booking(equipment, city, today_plus(0), today_plus(2))
    available = client.get("/api/equipment/?availability=available").json()["results"]
    booked = client.get("/api/equipment/?availability=booked").json()["results"]
    assert available == []
    assert len(booked) == 1


def test_availability_calendar_lists_booked_days(client, equipment, city):
    start, end = today_plus(2), today_plus(4)
    make_booking(equipment, city, start, end)

    month = start.strftime("%Y-%m")
    data = client.get(
        f"/api/equipment/{equipment.slug}/availability/?month={month}"
    ).json()

    expected = set()
    day = start
    while day <= end:
        expected.add(day.isoformat())
        day += datetime.timedelta(days=1)
    assert set(data["unavailable_dates"]) == expected


def test_availability_calendar_rejects_bad_month(client, equipment):
    response = client.get(f"/api/equipment/{equipment.slug}/availability/?month=bad")
    assert response.status_code == 400


@pytest.mark.parametrize("month", ["2026-13", "2026-00", "0-05", "2026-5-1"])
def test_availability_calendar_rejects_out_of_range_month(client, equipment, month):
    response = client.get(
        f"/api/equipment/{equipment.slug}/availability/?month={month}"
    )
    assert response.status_code == 400


def test_available_from_skips_back_to_back_bookings(equipment, city):
    make_booking(equipment, city, today_plus(0), today_plus(2))
    second = make_booking(equipment, city, today_plus(3), today_plus(5))

    expected = second.end_date + datetime.timedelta(days=1)
    assert equipment_availability(equipment, timezone.localdate()) == {
        "status": "booked",
        "available_from": expected,
    }


def test_list_available_from_skips_back_to_back_bookings(client, equipment, city):
    make_booking(equipment, city, today_plus(0), today_plus(2))
    second = make_booking(equipment, city, today_plus(3), today_plus(5))

    data = client.get("/api/equipment/").json()["results"][0]["availability"]
    assert data == {
        "status": "booked",
        "available_from": (second.end_date + datetime.timedelta(days=1)).isoformat(),
    }


def test_available_from_ignores_bookings_after_a_gap(equipment, city):
    first = make_booking(equipment, city, today_plus(0), today_plus(2))
    make_booking(equipment, city, today_plus(5), today_plus(6))

    result = equipment_availability(equipment, timezone.localdate())
    assert result["available_from"] == first.end_date + datetime.timedelta(days=1)


def test_future_booking_does_not_make_today_booked(equipment, city):
    make_booking(equipment, city, today_plus(1), today_plus(2))
    result = equipment_availability(equipment, timezone.localdate())
    assert result == {"status": "available", "available_from": None}
