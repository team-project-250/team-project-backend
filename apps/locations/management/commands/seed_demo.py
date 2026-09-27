"""Load demo/seed data for local development and staging.

Extend ``FIXTURES`` as new apps add their own fixtures.
"""

from datetime import timedelta

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.bookings.models import Booking
from apps.bookings.services import create_booking
from apps.catalog.models import Equipment
from apps.locations.models import City

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

# Recognisable, obviously-fake phone — not a real person's number — used so
# the demo booking created below can be found again on the next seed_demo
# run instead of piling up duplicates.
DEMO_BOOKING_PHONE = "+380000000000"
DEMO_BOOKING_EMAIL = "demo@example.com"

# How many days out the demo booking runs. A literal "booked until 12.03"
# date (as in the mockup) would go stale the moment it's in the past, so
# this is computed relative to *today* every time seed_demo runs instead.
DEMO_BOOKING_LENGTH_DAYS = 20


class Command(BaseCommand):
    """``manage.py seed_demo`` — loads every app's demo fixture plus one
    demo booking, so a fresh database has realistic data to browse."""

    help = "Load demo/seed data (fixtures) for local development."

    def handle(self, *args, **options):
        """Load every fixture in :data:`FIXTURES`, then seed a demo booking.

        Args:
            *args: Unused; required by :class:`BaseCommand`'s signature.
            **options: Unused; required by :class:`BaseCommand`'s signature.
        """
        for fixture in FIXTURES:
            self.stdout.write(f"Loading fixture: {fixture}")
            call_command("loaddata", fixture)

        self._seed_demo_booking()
        self.stdout.write(self.style.SUCCESS("Seed data loaded."))

    def _seed_demo_booking(self):
        """Book "Karcher SC 4 Deluxe" in Луцьк for the next few weeks, so
        the catalog/card "Заброньовано до ДД.ММ" badge has something real
        to show. Safe to run repeatedly — skips if it already exists."""
        try:
            equipment = Equipment.objects.get(slug="karcher-sc-4-deluxe")
            city = City.objects.get(slug="lutsk")
        except (Equipment.DoesNotExist, City.DoesNotExist):
            self.stdout.write(
                "Skipping demo booking: seed equipment/city not found "
                "(load the catalog and locations fixtures first)."
            )
            return

        already_booked = Booking.objects.filter(
            equipment=equipment,
            customer_phone=DEMO_BOOKING_PHONE,
            status__in=Booking.ACTIVE_STATUSES,
        ).exists()
        if already_booked:
            self.stdout.write("Demo booking already exists, skipping.")
            return

        start_date = timezone.localdate()
        end_date = start_date + timedelta(days=DEMO_BOOKING_LENGTH_DAYS)
        booking = create_booking(
            equipment=equipment,
            city=city,
            customer_name="Демо клієнт",
            customer_phone=DEMO_BOOKING_PHONE,
            customer_email=DEMO_BOOKING_EMAIL,
            start_date=start_date,
            end_date=end_date,
            delivery_method=Booking.DeliveryMethod.PICKUP,
            payment_method=Booking.PaymentMethod.CASH,
            comment="Демо-бронювання для перевірки бейджа доступності.",
        )
        available_from = end_date + timedelta(days=1)
        self.stdout.write(
            f"Demo booking {booking.number}: {equipment.name} booked until "
            f"{end_date.isoformat()} (available again {available_from.isoformat()})."
        )
