"""Smoke tests — confirm the project is wired together."""

import pytest


def test_openapi_schema_is_served(client):
    response = client.get("/api/schema/")

    assert response.status_code == 200


def test_swagger_ui_is_served(client):
    response = client.get("/api/docs/")

    assert response.status_code == 200


@pytest.mark.django_db
def test_admin_login_page_is_served(client):
    response = client.get("/admin/login/")

    assert response.status_code == 200


@pytest.mark.django_db
def test_unhandled_exception_returns_json_500_outside_debug(
    client, settings, monkeypatch
):
    """An exception DRF's default handler doesn't know about (not
    Http404/PermissionDenied/APIException) must still come back as JSON,
    not Django's HTML error page — see config/exception_handler.py."""
    from apps.locations.models import City
    from apps.locations.serializers import CitySerializer

    City.objects.create(name="Луцьк", slug="lutsk", is_default=True)

    def boom(self, instance):
        raise ValueError("boom")

    monkeypatch.setattr(CitySerializer, "to_representation", boom)
    settings.DEBUG = False

    response = client.get("/api/cities/")

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error."}
