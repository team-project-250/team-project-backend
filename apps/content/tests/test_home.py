import pytest

from apps.catalog.models import Category, Equipment
from apps.content.models import HeroSection
from apps.locations.models import City
from apps.reviews.models import Review

pytestmark = pytest.mark.django_db


def test_home_returns_all_sections_even_on_an_empty_db(client):
    response = client.get("/api/home/")
    assert response.status_code == 200
    data = response.json()
    assert set(data) == {
        "hero",
        "about",
        "rental_steps",
        "rental_terms",
        "settings",
        "cities",
        "categories",
        "popular_equipment",
        "reviews",
    }
    assert data["cities"] == []
    assert data["popular_equipment"] == []


def test_home_includes_seeded_content(client):
    HeroSection.objects.create(title="Оренда техніки")
    City.objects.create(name="Луцьк", slug="lutsk", is_default=True)
    category = Category.objects.create(name="Пилососи", slug="vacuum-cleaners")
    Equipment.objects.create(
        name="Popular",
        slug="popular",
        sku="POP-1",
        category=category,
        price_per_day="500.00",
        is_popular=True,
    )
    Equipment.objects.create(
        name="Not popular",
        slug="not-popular",
        sku="NP-1",
        category=category,
        price_per_day="500.00",
        is_popular=False,
    )
    Review.objects.create(
        author_name="Іван",
        rating=5,
        text="Добре",
        published_on="2026-01-01",
        is_published=True,
    )

    data = client.get("/api/home/").json()
    assert data["hero"]["title"] == "Оренда техніки"
    assert [c["slug"] for c in data["cities"]] == ["lutsk"]
    assert [e["slug"] for e in data["popular_equipment"]] == ["popular"]
    assert len(data["reviews"]) == 1

    # regression: popular_equipment must carry the same `availability` shape
    # as /api/equipment/ — a serializer field silently disappears from the
    # output instead of erroring if the view forgets to annotate it.
    assert data["popular_equipment"][0]["availability"] == {
        "status": "available",
        "available_from": None,
    }


def test_home_limits_popular_equipment_and_reviews(client):
    category = Category.objects.create(name="Пилососи", slug="vacuum-cleaners")
    for i in range(10):
        Equipment.objects.create(
            name=f"Item {i}",
            slug=f"item-{i}",
            sku=f"SKU-{i}",
            category=category,
            price_per_day="100.00",
            is_popular=True,
        )
    for i in range(10):
        Review.objects.create(
            author_name=f"User {i}",
            rating=5,
            text="...",
            published_on="2026-01-01",
            is_published=True,
        )

    data = client.get("/api/home/").json()
    assert len(data["popular_equipment"]) == 8
    assert len(data["reviews"]) == 6
