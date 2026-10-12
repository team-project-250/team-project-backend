"""Load demo/seed data for local development and staging.

The demo catalog, cities and reviews mirror what the frontend site shows
(``team-project-frontend/src/data``), so the API and the site describe the
same equipment. Extend ``FIXTURES`` as new apps add their own fixtures.
"""

import json
import urllib.error
import urllib.request
from datetime import timedelta
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.bookings.models import Booking
from apps.bookings.services import create_booking
from apps.catalog.models import (
    Equipment,
    EquipmentBadge,
    EquipmentBenefit,
    EquipmentImage,
    EquipmentIncludedItem,
    EquipmentSpec,
    EquipmentUseCase,
)
from apps.locations.models import City
from apps.reviews.models import Review

FIXTURES = [
    "cities",
    "categories",
    "equipment",
    "reviews",
    "hero",
    "about",
    "rental_steps",
    "rental_terms",
    "delivery_payment",
    "site_settings",
]

EQUIPMENT_FIXTURE = (
    Path(__file__).resolve().parents[3] / "catalog" / "fixtures" / "equipment.json"
)

# Child rows that belong entirely to a fixture equipment item — replaced on
# every run so stale specs/images from an older fixture don't linger.
EQUIPMENT_CHILD_MODELS = (
    EquipmentImage,
    EquipmentSpec,
    EquipmentIncludedItem,
    EquipmentBenefit,
    EquipmentBadge,
    EquipmentUseCase,
)

# The images live in the frontend repo; seed_demo downloads them from the
# deployed site into MEDIA storage so the API serves the same pictures.
DEMO_ASSETS_URL = "https://team-project-250.github.io/team-project-frontend/img/images/"
DOWNLOAD_TIMEOUT_SECONDS = 15

# Recognisable, obviously-fake phone — not a real person's number — used so
# the demo bookings created below can be found and replaced on the next
# seed_demo run instead of piling up duplicates.
DEMO_BOOKING_PHONE = "+380000000000"
DEMO_BOOKING_EMAIL = "demo@example.com"

# (equipment slug, city slug, days from today) — a few items show as
# "Заброньовано до ДД.ММ", like on the site. Dates are relative to today so
# they never go stale.
DEMO_BOOKINGS = [
    ("karcher-nt-35-1-ap", "lutsk", 10),
    ("karcher-nt-65-2-eco", "kyiv", 16),
    ("karcher-hd-6-15", "odesa", 7),
]


class Command(BaseCommand):
    """``manage.py seed_demo`` — loads every app's demo fixture, demo
    bookings and the demo images, so a fresh database has the same data
    the site shows."""

    help = "Load demo/seed data (fixtures, bookings, images) for local development."

    def add_arguments(self, parser):
        """Register the command-line options.

        Args:
            parser: The command's ``argparse.ArgumentParser``.
        """
        parser.add_argument(
            "--skip-images",
            action="store_true",
            help="Don't download equipment photos and review avatars.",
        )
        parser.add_argument(
            "--assets-url",
            default=DEMO_ASSETS_URL,
            help="Base URL the demo images are downloaded from.",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete all reviews before loading (drops leftovers from older "
            "demo data).",
        )

    def handle(self, *args, **options):
        """Load every fixture in :data:`FIXTURES`, seed demo bookings and
        download the demo images.

        Args:
            *args: Unused; required by :class:`BaseCommand`'s signature.
            **options: Parsed command-line options.
        """
        with transaction.atomic():
            if options["reset"]:
                Review.objects.all().delete()
            self._clear_equipment_children()
            for fixture in FIXTURES:
                self.stdout.write(f"Loading fixture: {fixture}")
                call_command("loaddata", fixture, verbosity=0)
            self._seed_demo_bookings()

        if not options["skip_images"]:
            self._download_images(options["assets_url"])
        self.stdout.write(self.style.SUCCESS("Seed data loaded."))

    def _clear_equipment_children(self):
        """Delete specs, images, badges etc. of the fixture's equipment so
        loaddata recreates them exactly as the fixture describes."""
        objects = json.loads(EQUIPMENT_FIXTURE.read_text(encoding="utf-8"))
        pks = [obj["pk"] for obj in objects if obj["model"] == "catalog.equipment"]
        for model in EQUIPMENT_CHILD_MODELS:
            model.objects.filter(equipment_id__in=pks).delete()

    def _seed_demo_bookings(self):
        """Replace the demo bookings (identified by
        :data:`DEMO_BOOKING_PHONE`) with fresh ones starting today."""
        Booking.objects.filter(customer_phone=DEMO_BOOKING_PHONE).delete()

        start_date = timezone.localdate()
        for slug, city_slug, days in DEMO_BOOKINGS:
            try:
                equipment = Equipment.objects.get(slug=slug)
                city = City.objects.get(slug=city_slug)
            except (Equipment.DoesNotExist, City.DoesNotExist):
                self.stdout.write(f"Skipping demo booking for {slug}: not found.")
                continue

            booking = create_booking(
                equipment=equipment,
                city=city,
                customer_name="Демо клієнт",
                customer_phone=DEMO_BOOKING_PHONE,
                customer_email=DEMO_BOOKING_EMAIL,
                start_date=start_date,
                end_date=start_date + timedelta(days=days),
                delivery_method=Booking.DeliveryMethod.PICKUP,
                payment_method=Booking.PaymentMethod.CASH,
                comment="Демо-бронювання для перевірки бейджа доступності.",
            )
            self.stdout.write(
                f"Demo booking {booking.number}: {equipment.name} booked until "
                f"{booking.end_date.isoformat()}."
            )

    def _download_images(self, assets_url):
        """Download every demo image that isn't in MEDIA storage yet.

        Args:
            assets_url: Base URL; equipment photos are fetched from
                ``<assets_url>equipment/<file>``, avatars from
                ``<assets_url><file>``.
        """
        equipment_images = list(
            Equipment.objects.exclude(main_image="").values_list(
                "main_image", flat=True
            )
        ) + list(EquipmentImage.objects.values_list("image", flat=True))
        avatars = Review.objects.exclude(avatar="").values_list("avatar", flat=True)

        wanted = [(name, "equipment/" + Path(name).name) for name in equipment_images]
        wanted += [(name, Path(name).name) for name in avatars]
        missing = [(n, src) for n, src in wanted if not default_storage.exists(n)]
        if not missing:
            return

        self.stdout.write(f"Downloading {len(missing)} demo images from {assets_url}")
        for name, source in missing:
            url = assets_url.rstrip("/") + "/" + source
            try:
                with urllib.request.urlopen(
                    url, timeout=DOWNLOAD_TIMEOUT_SECONDS
                ) as response:
                    default_storage.save(name, ContentFile(response.read()))
            except (urllib.error.URLError, TimeoutError) as exc:
                self.stdout.write(
                    self.style.WARNING(
                        f"Could not download {url} ({exc}); skipping the remaining "
                        "images. Re-run seed_demo later, or pass --skip-images."
                    )
                )
                return
