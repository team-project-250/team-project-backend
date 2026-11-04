import io
import urllib.error

import pytest
from django.core.management import call_command
from PIL import Image

from apps.bookings.models import Booking
from apps.catalog.models import Category, Equipment, EquipmentSpec
from apps.content.models import AboutSection, HeroSection
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
    assert Equipment.objects.get(slug="karcher-hd-6-15").model == "Kärcher HD 6/15"

    lutsk = City.objects.get(slug="lutsk")
    assert lutsk.pickup_address == "вул. Соборна, 12"
    assert lutsk.working_hours == "Пн-Нд: Цілодобово 24/7"


def test_seed_demo_content_matches_the_site():
    """TP250-72 / TP250-73: hero subtitle and the about block as on the site."""
    run_seed(skip_images=True)

    assert HeroSection.load().subtitle == (
        "Професійні мийні пилососи, пароочисники та апарати високого тиску "
        "без купівлі дорогого обладнання"
    )
    about = AboutSection.load()
    assert about.description.startswith("EasyRent — сервіс оренди")
    assert [f.text for f in about.features.all()] == [
        "Плит та витяжок",
        "Важкодоступних місць та кутів",
        "Підлоги будь-якого типу (плитка, ламінат, лінолеум)",
        "Вікон, дзеркал, скляних поверхонь, душових кабін та сантехнік",
        "Дитячих іграшок (дезінфекція)",
        "Плитки та міжплиткових швів",
    ]


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


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def png_bytes():
    out = io.BytesIO()
    Image.new("RGB", (2000, 1000), "yellow").save(out, "PNG")
    return out.getvalue()


def test_seed_demo_downloads_missing_images_as_webp(monkeypatch, tmp_path):
    requested = []

    def fake_urlopen(url, timeout):
        requested.append(url)
        return FakeResponse(png_bytes())

    monkeypatch.setattr(seed_demo.urllib.request, "urlopen", fake_urlopen)
    run_seed(assets_url="https://assets.example/img/")

    assert "https://assets.example/img/equipment/hd-6-15.png" in requested
    assert "https://assets.example/img/avatar-1.png" in requested
    assert Equipment.objects.get(slug="karcher-hd-6-15").main_image.name == (
        "equipment/hd-6-15.webp"
    )
    with Image.open(tmp_path / "equipment" / "hd-6-15.webp") as image:
        assert image.format == "WEBP"
        assert image.size == (1200, 600)

    requested.clear()
    run_seed(assets_url="https://assets.example/img/")
    assert requested == []


def test_seed_demo_skips_a_download_that_is_not_an_image(monkeypatch, tmp_path):
    monkeypatch.setattr(
        seed_demo.urllib.request,
        "urlopen",
        lambda url, timeout: FakeResponse(b"<html>404</html>"),
    )
    out = io.StringIO()
    call_command("seed_demo", stdout=out)

    assert "Not an image, skipped" in out.getvalue()
    assert not (tmp_path / "equipment" / "hd-6-15.webp").exists()


def test_seed_demo_survives_being_offline(monkeypatch):
    def offline(url, timeout):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(seed_demo.urllib.request, "urlopen", offline)
    out = io.StringIO()
    call_command("seed_demo", stdout=out)

    assert "Could not download" in out.getvalue()
    assert Equipment.objects.count() == 14
