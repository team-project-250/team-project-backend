import pytest

from apps.catalog.models import Category

pytestmark = pytest.mark.django_db


def test_categories_list_active_only(client):
    Category.objects.create(name="Пилососи", slug="vacuum-cleaners", order=1)
    Category.objects.create(name="Приховано", slug="hidden", order=2, is_active=False)

    results = client.get("/api/categories/").json()
    assert [c["name"] for c in results] == ["Пилососи"]
