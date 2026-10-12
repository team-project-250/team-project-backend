"""Coverage for the Card-page additions: badges, suitable_for, breadcrumbs,
detail 404s, and the related-equipment endpoint.
"""

import pytest

from apps.catalog.models import Category, Equipment, EquipmentBadge, EquipmentUseCase

pytestmark = pytest.mark.django_db


@pytest.fixture
def categories():
    return {
        "vacuum": Category.objects.create(name="Пилососи", slug="vacuum-cleaners"),
        "steam": Category.objects.create(name="Пароочисники", slug="steam-cleaners"),
        "mowers": Category.objects.create(name="Газонокосарки", slug="mowers"),
    }


@pytest.fixture
def main_equipment(categories):
    equipment = Equipment.objects.create(
        name="Karcher SC 4 Deluxe",
        slug="karcher-sc-4-deluxe",
        sku="SC-4-DELUXE",
        category=categories["steam"],
        price_per_day="650.00",
    )
    EquipmentBadge.objects.create(
        equipment=equipment, label="Оригінал Karcher", order=1
    )
    EquipmentBadge.objects.create(equipment=equipment, label="Хіт", order=2)
    EquipmentUseCase.objects.create(
        equipment=equipment, text="Хімчистки килимового покриття", order=1
    )
    EquipmentUseCase.objects.create(
        equipment=equipment, text="Хімчистки меблів і салону авто", order=2
    )
    return equipment


def test_detail_includes_badges_suitable_for_and_breadcrumbs(client, main_equipment):
    data = client.get(f"/api/equipment/{main_equipment.slug}/").json()

    assert [b["label"] for b in data["badges"]] == ["Оригінал Karcher", "Хіт"]
    assert [s["text"] for s in data["suitable_for"]] == [
        "Хімчистки килимового покриття",
        "Хімчистки меблів і салону авто",
    ]
    # No model set -> the last crumb falls back to the full name.
    assert data["breadcrumbs"] == [
        {"label": "Головна", "url": "/"},
        {"label": "Каталог", "url": "/catalog"},
        {"label": "Karcher SC 4 Deluxe", "url": None},
    ]


def test_breadcrumbs_have_three_levels_ending_with_the_model(client, categories):
    """TP250-76: the site shows "Головна / Каталог / <model>" — no category
    level and the model rather than the full product name."""
    equipment = Equipment.objects.create(
        name="Апарат високого тиску Kärcher HD 6/15",
        model="Kärcher HD 6/15",
        slug="karcher-hd-6-15",
        sku="HD-6-15",
        category=categories["steam"],
        price_per_day="700.00",
    )

    data = client.get(f"/api/equipment/{equipment.slug}/").json()

    assert data["model"] == "Kärcher HD 6/15"
    assert data["breadcrumbs"] == [
        {"label": "Головна", "url": "/"},
        {"label": "Каталог", "url": "/catalog"},
        {"label": "Kärcher HD 6/15", "url": None},
    ]


def test_list_does_not_include_badges_or_suitable_for(client, main_equipment):
    """These belong on the product page only, not the catalog cards."""
    item = client.get("/api/equipment/").json()["results"][0]
    assert "badges" not in item
    assert "suitable_for" not in item


def test_detail_404_for_unknown_slug(client):
    assert client.get("/api/equipment/does-not-exist/").status_code == 404


def test_detail_404_for_inactive_equipment(client, categories):
    Equipment.objects.create(
        name="Списана техніка",
        slug="retired",
        sku="RETIRED-1",
        category=categories["vacuum"],
        price_per_day="100.00",
        is_active=False,
    )
    assert client.get("/api/equipment/retired/").status_code == 404


def test_related_prefers_same_category_first(client, main_equipment, categories):
    same_category = Equipment.objects.create(
        name="Karcher SC 3",
        slug="karcher-sc-3",
        sku="SC-3",
        category=categories["steam"],
        price_per_day="600.00",
    )
    other_category = Equipment.objects.create(
        name="Газонокосарка Karcher",
        slug="karcher-mower",
        sku="MOWER-1",
        category=categories["mowers"],
        price_per_day="500.00",
    )

    results = client.get(f"/api/equipment/{main_equipment.slug}/related/").json()

    slugs = [item["slug"] for item in results]
    assert main_equipment.slug not in slugs
    assert slugs[0] == same_category.slug  # same category ranks first
    assert other_category.slug in slugs  # filled in once category runs out


def test_related_respects_limit(client, main_equipment, categories):
    for i in range(5):
        Equipment.objects.create(
            name=f"Item {i}",
            slug=f"item-{i}",
            sku=f"SKU-{i}",
            category=categories["steam"],
            price_per_day="100.00",
        )
    results = client.get(
        f"/api/equipment/{main_equipment.slug}/related/?limit=2"
    ).json()
    assert len(results) == 2


def test_related_includes_availability(client, main_equipment, categories):
    Equipment.objects.create(
        name="Karcher SC 3",
        slug="karcher-sc-3",
        sku="SC-3",
        category=categories["steam"],
        price_per_day="600.00",
    )
    results = client.get(f"/api/equipment/{main_equipment.slug}/related/").json()
    assert results[0]["availability"] == {"status": "available", "available_from": None}


def test_related_404_for_unknown_slug(client):
    assert client.get("/api/equipment/does-not-exist/related/").status_code == 404


def test_related_returns_absolute_image_urls(client, main_equipment, categories):
    """TP250-78: /related/ returned "/media/..." while every other endpoint
    returned absolute URLs, so images broke on a frontend on another host."""
    Equipment.objects.create(
        name="Karcher SC 3",
        slug="karcher-sc-3",
        sku="SC-3",
        category=categories["steam"],
        price_per_day="600.00",
        main_image="equipment/sc-3.png",
    )

    results = client.get(f"/api/equipment/{main_equipment.slug}/related/").json()

    assert results[0]["main_image"] == "http://testserver/media/equipment/sc-3.png"
