"""Load demo/seed data for local development and staging.

Extend ``FIXTURES`` as new apps add their own fixtures.
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand

FIXTURES = [
    "cities",
    "reviews",
]


class Command(BaseCommand):
    help = "Load demo/seed data (fixtures) for local development."

    def handle(self, *args, **options):
        for fixture in FIXTURES:
            self.stdout.write(f"Loading fixture: {fixture}")
            call_command("loaddata", fixture)
        self.stdout.write(self.style.SUCCESS("Seed data loaded."))
