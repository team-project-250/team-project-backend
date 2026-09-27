import pytest

from apps.catalog.models import Category, Equipment
from apps.locations.models import City

pytestmark = pytest.mark.django_db


@pytest.fixture
def cities():
    return {
        "lutsk": City.objects.create(name="Луцьк", slug="lutsk", is_default=True),
        "lviv": City.objects.create(name="Львів", slug="lviv"),
    }


@pytest.fixture
def categories():
    return {
        "vacuum": Category.objects.create(
            name="Пилососи", slug="vacuum-cleaners", order=1
        ),
        "steam": Category.objects.create(
            name="Пароочисники", slug="steam-cleaners", order=2
        ),
    }


@pytest.fixture
def equipment(categories, cities):
    puzzi = Equipment.objects.create(
        name="Karcher Puzzi 8/1",
        slug="karcher-puzzi-8-1",
        sku="PUZZI-8-1",
        category=categories["vacuum"],
        price_per_day="650.00",
        rating="4.80",
        is_popular=True,
    )
    puzzi.available_cities.set([cities["lutsk"]])

    sc4 = Equipment.objects.create(
        name="Karcher SC 4 Deluxe",
        slug="karcher-sc-4-deluxe",
        sku="SC-4-DELUXE",
        category=categories["steam"],
        price_per_day="600.00",
        rating="4.50",
    )
    sc4.available_cities.set([cities["lviv"]])

    Equipment.objects.create(
        name="Списана техніка",
        slug="retired",
        sku="RETIRED-1",
        category=categories["vacuum"],
        price_per_day="100.00",
        is_active=False,
    )
    return {"puzzi": puzzi, "sc4": sc4}


def test_list_hides_inactive(client, equipment):
    results = client.get("/api/equipment/").json()["results"]
    assert len(results) == 2
    assert "retired" not in [e["slug"] for e in results]


def test_default_ordering_is_rating_desc(client, equipment):
    results = client.get("/api/equipment/").json()["results"]
    assert [e["slug"] for e in results] == ["karcher-puzzi-8-1", "karcher-sc-4-deluxe"]


def test_filter_by_category(client, equipment):
    results = client.get("/api/equipment/?category=steam-cleaners").json()["results"]
    assert [e["slug"] for e in results] == ["karcher-sc-4-deluxe"]


def test_filter_by_city(client, equipment):
    results = client.get("/api/equipment/?city=lviv").json()["results"]
    assert [e["slug"] for e in results] == ["karcher-sc-4-deluxe"]


def test_sort_by_price_ascending(client, equipment):
    results = client.get("/api/equipment/?ordering=price_per_day").json()["results"]
    assert [e["slug"] for e in results] == ["karcher-sc-4-deluxe", "karcher-puzzi-8-1"]


def test_is_popular_filter(client, equipment):
    results = client.get("/api/equipment/?is_popular=true").json()["results"]
    assert [e["slug"] for e in results] == ["karcher-puzzi-8-1"]


def test_detail_includes_nested_blocks(client, equipment):
    data = client.get("/api/equipment/karcher-puzzi-8-1/").json()
    assert set(data) >= {
        "id",
        "name",
        "slug",
        "sku",
        "category",
        "description",
        "price_per_day",
        "rating",
        "images",
        "specs",
        "included_items",
        "benefits",
        "available_cities",
    }
    assert data["available_cities"] == ["lutsk"]


def test_pagination_page_size_is_8(client, categories):
    for i in range(10):
        Equipment.objects.create(
            name=f"Item {i}",
            slug=f"item-{i}",
            sku=f"SKU-{i}",
            category=categories["vacuum"],
            price_per_day="100.00",
        )
    data = client.get("/api/equipment/").json()
    assert len(data["results"]) == 8
    assert data["count"] == 10
