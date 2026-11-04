import io

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management import call_command
from PIL import Image

from apps.catalog.models import Category, Equipment, EquipmentImage
from apps.reviews.models import Review

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def png_bytes(size=(2000, 2000)):
    out = io.BytesIO()
    Image.new("RGB", size, "yellow").save(out, "PNG")
    return out.getvalue()


@pytest.fixture
def media():
    default_storage.save("equipment/hd.png", ContentFile(png_bytes()))
    default_storage.save("equipment/gallery/hd-2.png", ContentFile(png_bytes()))
    default_storage.save("reviews/avatar.png", ContentFile(png_bytes((100, 100))))

    category = Category.objects.create(name="Апарати", slug="washers")
    equipment = Equipment.objects.create(
        name="HD",
        slug="hd",
        sku="HD",
        category=category,
        price_per_day="100.00",
        main_image="equipment/hd.png",
    )
    # Same file behind two rows: it must be converted only once.
    other = Equipment.objects.create(
        name="HD copy",
        slug="hd-copy",
        sku="HD-COPY",
        category=category,
        price_per_day="100.00",
        main_image="equipment/hd.png",
    )
    image = EquipmentImage.objects.create(
        equipment=equipment, image="equipment/gallery/hd-2.png"
    )
    review = Review.objects.create(
        author_name="Олена",
        rating=5,
        text="Добре",
        published_on="2026-01-01",
        avatar="reviews/avatar.png",
    )
    return {"equipment": equipment, "other": other, "image": image, "review": review}


def run(*args):
    out = io.StringIO()
    call_command("optimize_media", *args, stdout=out)
    return out.getvalue()


def test_converts_every_image_field_to_webp(media, tmp_path):
    output = run()

    for obj, field in [
        (media["equipment"], "main_image"),
        (media["other"], "main_image"),
        (media["image"], "image"),
        (media["review"], "avatar"),
    ]:
        obj.refresh_from_db()
        assert getattr(obj, field).name.endswith(".webp")

    with Image.open(tmp_path / "equipment" / "hd.webp") as image:
        assert image.format == "WEBP"
        assert image.size == (1200, 1200)
    assert "Converted 3 images to WebP" in output
    assert "updated 4 rows" in output


def test_keeps_the_originals(media, tmp_path):
    run()

    assert (tmp_path / "equipment" / "hd.png").exists()


def test_dry_run_changes_nothing(media, tmp_path):
    output = run("--dry-run")

    media["equipment"].refresh_from_db()
    assert media["equipment"].main_image.name == "equipment/hd.png"
    assert not (tmp_path / "equipment" / "hd.webp").exists()
    assert "Dry run: 3 images" in output


def test_running_twice_is_a_no_op(media):
    run()
    output = run()

    assert "Converted 0 images" in output


def test_missing_file_is_reported_and_its_row_left_alone(media):
    default_storage.delete("equipment/gallery/hd-2.png")

    output = run()

    media["image"].refresh_from_db()
    assert media["image"].image.name == "equipment/gallery/hd-2.png"
    assert "Missing in storage: equipment/gallery/hd-2.png" in output
