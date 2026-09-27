import datetime

import pytest
from django.core.cache import cache
from django.utils import timezone

from apps.bookings.models import Booking, CallbackRequest
from apps.bookings.services import create_booking
from apps.catalog.models import Category, Equipment
from apps.locations.models import City

pytestmark = pytest.mark.django_db


def today_plus(days):
    return timezone.localdate() + datetime.timedelta(days=days)


@pytest.fixture(autouse=True)
def _reset_throttle_cache():
    """CallbackRequestCreateView is rate-limited; the test client's requests
    all share one IP, so without this, tests earlier in the run would trip
    the throttle for tests later in the same process."""
    cache.clear()


def test_create_callback_request_minimal(client):
    response = client.post(
        "/api/callback-requests/",
        {"phone": "+380501234567"},
        content_type="application/json",
    )
    assert response.status_code == 201
    request = CallbackRequest.objects.get()
    assert request.is_processed is False
    assert request.equipment is None


def test_create_callback_request_with_equipment_and_dates(client):
    category = Category.objects.create(name="Пилососи", slug="vacuum-cleaners")
    equipment = Equipment.objects.create(
        name="Karcher Puzzi 8/1",
        slug="karcher-puzzi-8-1",
        sku="PUZZI-8-1",
        category=category,
        price_per_day="650.00",
    )
    response = client.post(
        "/api/callback-requests/",
        {
            "phone": "+380501234567",
            "equipment": equipment.slug,
            "start_date": "2026-10-01",
            "end_date": "2026-10-03",
        },
        content_type="application/json",
    )
    assert response.status_code == 201
    assert CallbackRequest.objects.get().equipment == equipment


def test_phone_is_required(client):
    response = client.post(
        "/api/callback-requests/", {}, content_type="application/json"
    )
    assert response.status_code == 400
    assert "phone" in response.json()


def test_invalid_phone_format_rejected(client):
    response = client.post(
        "/api/callback-requests/",
        {"phone": "0501234567"},  # missing +380
        content_type="application/json",
    )
    assert response.status_code == 400
    assert "phone" in response.json()


@pytest.fixture
def equipment():
    category = Category.objects.create(name="Пилососи", slug="vacuum-cleaners")
    return Equipment.objects.create(
        name="Karcher Puzzi 8/1",
        slug="karcher-puzzi-8-1",
        sku="PUZZI-8-1",
        category=category,
        price_per_day="650.00",
    )


def test_past_start_date_rejected(client, equipment):
    response = client.post(
        "/api/callback-requests/",
        {
            "phone": "+380501234567",
            "equipment": equipment.slug,
            "start_date": today_plus(-1).isoformat(),
            "end_date": today_plus(2).isoformat(),
        },
        content_type="application/json",
    )
    assert response.status_code == 400


def test_date_conflict_returns_409(client, equipment):
    city = City.objects.create(name="Луцьк", slug="lutsk", is_default=True)
    equipment.available_cities.add(city)
    create_booking(
        equipment=equipment,
        city=city,
        customer_name="Іван",
        customer_phone="+380671112233",
        customer_email="ivan@example.com",
        start_date=today_plus(1),
        end_date=today_plus(5),
        delivery_method=Booking.DeliveryMethod.PICKUP,
        payment_method=Booking.PaymentMethod.CASH,
    )

    response = client.post(
        "/api/callback-requests/",
        {
            "phone": "+380501234567",
            "equipment": equipment.slug,
            "start_date": today_plus(3).isoformat(),
            "end_date": today_plus(7).isoformat(),
        },
        content_type="application/json",
    )
    assert response.status_code == 409


def test_duplicate_request_returns_existing_with_200(client, equipment):
    payload = {"phone": "+380501234567", "equipment": equipment.slug}

    first = client.post(
        "/api/callback-requests/", payload, content_type="application/json"
    )
    assert first.status_code == 201

    second = client.post(
        "/api/callback-requests/", payload, content_type="application/json"
    )
    assert second.status_code == 200
    assert CallbackRequest.objects.count() == 1


def test_different_equipment_is_not_a_duplicate(client, equipment):
    other_category = Category.objects.create(name="Пароочисники", slug="steamers")
    other_equipment = Equipment.objects.create(
        name="Karcher SC 4",
        slug="karcher-sc-4",
        sku="SC-4",
        category=other_category,
        price_per_day="600.00",
    )

    client.post(
        "/api/callback-requests/",
        {"phone": "+380501234567", "equipment": equipment.slug},
        content_type="application/json",
    )
    response = client.post(
        "/api/callback-requests/",
        {"phone": "+380501234567", "equipment": other_equipment.slug},
        content_type="application/json",
    )
    assert response.status_code == 201
    assert CallbackRequest.objects.count() == 2
