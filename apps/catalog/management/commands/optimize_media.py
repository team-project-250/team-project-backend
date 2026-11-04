"""Convert every stored image to a scaled-down WebP (see ``config/images.py``).

Covers each ``ImageField`` of the project's own apps — equipment photos,
gallery images, review avatars, the hero background — so a new image field
is picked up without touching this command. The converted file is saved next
to the original (``equipment/hd-6-15.png`` -> ``equipment/hd-6-15.webp``) and
the database row is pointed at it. Originals are left in storage, so a
conversion can be rolled back by pointing the rows at them again.
"""

from django.apps import apps
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import models
from PIL import UnidentifiedImageError

from config.images import WEBP_SUFFIX, to_webp, webp_name


def image_fields():
    """Yield ``(model, field)`` for every ImageField of the project's apps.

    Yields:
        Tuples of the model class and its ``ImageField`` instance.
    """
    for model in apps.get_models():
        if not model.__module__.startswith("apps."):
            continue
        for field in model._meta.get_fields():
            if isinstance(field, models.ImageField):
                yield model, field


class Command(BaseCommand):
    """``manage.py optimize_media`` — convert stored images to WebP."""

    help = "Convert stored images to scaled-down WebP and update the database."

    def add_arguments(self, parser):
        """Register the command-line options.

        Args:
            parser: The command's ``argparse.ArgumentParser``.
        """
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only list the images that would be converted; change nothing.",
        )

    def handle(self, *args, **options):
        """Convert each non-WebP image once and repoint every row using it.

        Args:
            *args: Unused; required by :class:`BaseCommand`'s signature.
            **options: Parsed command-line options.
        """
        dry_run = options["dry_run"]
        # Original name -> converted name, or None if it couldn't be converted.
        # The same file can back several rows; it's converted only once.
        converted: dict[str, str | None] = {}
        size_before = size_after = updated_rows = 0

        for model, field in image_fields():
            rows = (
                model.objects.exclude(**{field.name: ""})
                .exclude(**{f"{field.name}__isnull": True})
                .values_list("pk", field.name)
            )
            for pk, name in rows:
                if name.lower().endswith(WEBP_SUFFIX):
                    continue
                if name not in converted:
                    converted[name], before, after = self._convert(
                        field.storage, name, dry_run
                    )
                    size_before += before
                    size_after += after
                new_name = converted[name]
                if new_name is None:
                    continue
                if not dry_run:
                    model.objects.filter(pk=pk).update(**{field.name: new_name})
                updated_rows += 1

        files = sum(1 for new_name in converted.values() if new_name)
        if dry_run:
            self.stdout.write(
                f"Dry run: {files} images ({size_before / 1e6:.1f} MB) in "
                f"{updated_rows} rows would be converted to WebP."
            )
            return
        self.stdout.write(
            self.style.SUCCESS(
                f"Converted {files} images to WebP: {size_before / 1e6:.1f} MB -> "
                f"{size_after / 1e6:.1f} MB; updated {updated_rows} rows."
            )
        )

    def _convert(self, storage, name, dry_run):
        """Store a WebP copy of ``name`` unless one is already there.

        Args:
            storage: The field's storage backend.
            name: Storage name of the original image.
            dry_run: Only look the original up, don't convert or save.

        Returns:
            ``(new_name, size_before, size_after)``; ``new_name`` is ``None``
            if the original is missing or isn't an image.
        """
        new_name = webp_name(name)
        if not storage.exists(name):
            self.stdout.write(self.style.WARNING(f"Missing in storage: {name}"))
            return None, 0, 0
        if dry_run:
            self.stdout.write(f"{name} -> {new_name}")
            return new_name, storage.size(name), 0
        if storage.exists(new_name):
            return new_name, 0, 0

        with storage.open(name) as original:
            data = original.read()
        try:
            webp = to_webp(data)
        except UnidentifiedImageError:
            self.stdout.write(self.style.WARNING(f"Not an image, skipped: {name}"))
            return None, 0, 0
        saved_name = storage.save(new_name, ContentFile(webp))
        self.stdout.write(f"{name} -> {saved_name}")
        return saved_name, len(data), len(webp)
