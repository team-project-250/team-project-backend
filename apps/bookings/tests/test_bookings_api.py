import datetime
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.catalog.models import Category, Equipment
from apps.locations.models import City

pytestmark = pytest.mark.django_db


def today_plus(days):
    return (timezone.localdate() + datetime.timedelta(days=days)).isoformat()


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


def test_create_booking_success(client, equipment, city):
    payload = {
        "equipment": equipment.slug,
        "city": city.slug,
        "customer_name": "Іван",
        "customer_phone": "+380501234567",
        "customer_email": "ivan@example.com",
        "start_date": today_plus(1),
        "end_date": today_plus(2),
        "delivery_method": "pickup",
        "payment_method": "cash",
    }
    response = client.post("/api/bookings/", payload, content_type="application/json")
    assert response.status_code == 201
    assert response.json()["total_price"] == "1300.00"


def test_create_booking_rejects_invalid_email(client, equipment, city):
    payload = {
        "equipment": equipment.slug,
        "city": city.slug,
        "customer_name": "Іван",
        "customer_phone": "+380501234567",
        "customer_email": "not-an-email",
        "start_date": today_plus(1),
        "end_date": today_plus(2),
        "delivery_method": "pickup",
        "payment_method": "cash",
    }
    response = client.post("/api/bookings/", payload, content_type="application/json")
    assert response.status_code == 400
    assert "customer_email" in response.json()


def test_create_booking_rejects_invalid_phone(client, equipment, city):
    payload = {
        "equipment": equipment.slug,
        "city": city.slug,
        "customer_name": "Іван",
        "customer_phone": "0501234567",
        "customer_email": "ivan@example.com",
        "start_date": today_plus(1),
        "end_date": today_plus(2),
        "delivery_method": "pickup",
        "payment_method": "cash",
    }
    response = client.post("/api/bookings/", payload, content_type="application/json")
    assert response.status_code == 400
    assert "customer_phone" in response.json()


def test_create_booking_courier_requires_address(client, equipment, city):
    payload = {
        "equipment": equipment.slug,
        "city": city.slug,
        "customer_name": "Іван",
        "customer_phone": "+380501234567",
        "customer_email": "ivan@example.com",
        "start_date": today_plus(1),
        "end_date": today_plus(2),
        "delivery_method": "courier",
        "payment_method": "cash",
    }
    response = client.post("/api/bookings/", payload, content_type="application/json")
    assert response.status_code == 400
    assert "delivery_address" in response.json()


def test_create_booking_rejects_overlap(client, equipment, city):
    payload = {
        "equipment": equipment.slug,
        "city": city.slug,
        "customer_name": "Іван",
        "customer_phone": "+380501234567",
        "customer_email": "ivan@example.com",
        "start_date": today_plus(1),
        "end_date": today_plus(5),
        "delivery_method": "pickup",
        "payment_method": "cash",
    }
    assert (
        client.post(
            "/api/bookings/", payload, content_type="application/json"
        ).status_code
        == 201
    )

    payload["start_date"], payload["end_date"] = today_plus(3), today_plus(7)
    assert (
        client.post(
            "/api/bookings/", payload, content_type="application/json"
        ).status_code
        == 409
    )


def test_quote_endpoint(client, equipment):
    payload = {
        "equipment": equipment.slug,
        "start_date": today_plus(1),
        "end_date": today_plus(3),
        "delivery_method": "courier",
    }
    response = client.post(
        "/api/bookings/quote/", payload, content_type="application/json"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["rental_days"] == 3
    assert data["delivery_fee"] == "100.00"


def test_quote_rejects_end_before_start(client, equipment):
    payload = {
        "equipment": equipment.slug,
        "start_date": today_plus(5),
        "end_date": today_plus(2),
        "delivery_method": "pickup",
    }
    response = client.post(
        "/api/bookings/quote/", payload, content_type="application/json"
    )
    assert response.status_code == 400
    assert "end_date" in response.json()


def test_quote_rejects_past_start(client, equipment):
    payload = {
        "equipment": equipment.slug,
        "start_date": today_plus(-2),
        "end_date": today_plus(1),
        "delivery_method": "pickup",
    }
    response = client.post(
        "/api/bookings/quote/", payload, content_type="application/json"
    )
    assert response.status_code == 400
