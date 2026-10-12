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
