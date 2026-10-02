import io
import urllib.error

import pytest
from django.core.management import call_command

from apps.bookings.models import Booking
from apps.catalog.models import Category, Equipment, EquipmentSpec
from apps.locations.management.commands import seed_demo
from apps.locations.models import City
from apps.reviews.models import Review

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def run_seed(**options):
    call_command("seed_demo", stdout=io.StringIO(), **options)


def test_seed_demo_matches_the_site_catalog():
    run_seed(skip_images=True)

    assert Category.objects.filter(name="Апарати високого тиску").exists()
    assert Category.objects.count() == 7
    assert Equipment.objects.count() == 14
    assert Equipment.objects.filter(available_cities__slug="lutsk").count() == 14
    assert Review.objects.count() == 4

    lutsk = City.objects.get(slug="lutsk")
    assert lutsk.pickup_address == "вул. Соборна, 12"
    assert lutsk.working_hours == "Пн-Нд: Цілодобово 24/7"


def test_seed_demo_is_idempotent():
    run_seed(skip_images=True)
    specs = EquipmentSpec.objects.count()

    run_seed(skip_images=True)

    assert EquipmentSpec.objects.count() == specs
    assert Booking.objects.filter(
        customer_phone=seed_demo.DEMO_BOOKING_PHONE
    ).count() == len(seed_demo.DEMO_BOOKINGS)


def test_seed_demo_replaces_stale_equipment_children():
    run_seed(skip_images=True)
    equipment = Equipment.objects.get(slug="karcher-hd-6-15")
    EquipmentSpec.objects.create(equipment=equipment, label="Stale", value="x")

    run_seed(skip_images=True)

    assert not EquipmentSpec.objects.filter(label="Stale").exists()


def test_seed_demo_reset_drops_old_reviews():
    Review.objects.create(
        pk=99, author_name="Old demo", rating=5, text="x", published_on="2026-01-01"
    )

    run_seed(skip_images=True, reset=True)

    assert not Review.objects.filter(pk=99).exists()


def test_seed_demo_downloads_missing_images(monkeypatch, tmp_path):
    requested = []

    class FakeResponse(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def fake_urlopen(url, timeout):
        requested.append(url)
        return FakeResponse(b"image-bytes")

    monkeypatch.setattr(seed_demo.urllib.request, "urlopen", fake_urlopen)
    run_seed(assets_url="https://assets.example/img/")

    assert "https://assets.example/img/equipment/hd-6-15.png" in requested
    assert "https://assets.example/img/avatar-1.png" in requested
    assert (tmp_path / "equipment" / "hd-6-15.png").read_bytes() == b"image-bytes"

    requested.clear()
    run_seed(assets_url="https://assets.example/img/")
    assert requested == []


def test_seed_demo_survives_being_offline(monkeypatch):
    def offline(url, timeout):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(seed_demo.urllib.request, "urlopen", offline)
    out = io.StringIO()
    call_command("seed_demo", stdout=out)

    assert "Could not download" in out.getvalue()
    assert Equipment.objects.count() == 14
