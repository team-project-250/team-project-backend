"""Smoke tests for the content admin — renders every changelist/add page
and confirms the singleton lock (has_add_permission) actually blocks a
second row once one exists.
"""

import pytest

from apps.content.models import HeroSection

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client(client, django_user_model):
    user = django_user_model.objects.create_superuser(
        username="admin", email="admin@example.com", password="pass"
    )
    client.force_login(user)
    return client


@pytest.mark.parametrize(
    "url",
    [
        "/admin/content/herosection/",
        "/admin/content/aboutsection/",
        "/admin/content/rentalstep/",
        "/admin/content/rentalterm/",
        "/admin/content/sitesettings/",
    ],
)
def test_changelist_renders(admin_client, url):
    assert admin_client.get(url).status_code == 200


def test_singleton_add_allowed_when_empty(admin_client):
    assert admin_client.get("/admin/content/herosection/add/").status_code == 200


def test_singleton_add_blocked_once_a_row_exists(admin_client):
    HeroSection.objects.create(title="Hero")
    assert admin_client.get("/admin/content/herosection/add/").status_code == 403


def test_singleton_change_still_allowed(admin_client):
    hero = HeroSection.objects.create(title="Hero")
    response = admin_client.get(f"/admin/content/herosection/{hero.pk}/change/")
    assert response.status_code == 200
