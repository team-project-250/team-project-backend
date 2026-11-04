"""Tests for the WebP conversion helpers in ``config/images.py``."""

import io

import pytest
from PIL import Image, UnidentifiedImageError

from config.images import MAX_SIZE, to_webp, webp_name


def encode(image, fmt="PNG"):
    out = io.BytesIO()
    image.save(out, fmt)
    return out.getvalue()


def decode(data):
    image = Image.open(io.BytesIO(data))
    image.load()
    return image


def test_to_webp_scales_down_to_max_size_keeping_proportions():
    image = decode(to_webp(encode(Image.new("RGB", (3000, 1500), "gray"))))

    assert image.format == "WEBP"
    assert image.size == (MAX_SIZE, MAX_SIZE // 2)


def test_to_webp_does_not_upscale_small_images():
    image = decode(to_webp(encode(Image.new("RGB", (300, 200), "gray"))))

    assert image.size == (300, 200)


def test_to_webp_keeps_transparency():
    source = Image.new("RGBA", (100, 100), (255, 255, 0, 0))

    image = decode(to_webp(encode(source)))

    assert image.mode == "RGBA"
    assert image.getpixel((50, 50))[3] == 0


def test_to_webp_rejects_non_images():
    with pytest.raises(UnidentifiedImageError):
        to_webp(b"not an image")


def test_webp_name_replaces_the_suffix():
    assert webp_name("equipment/gallery/hd-6-15-2.png") == (
        "equipment/gallery/hd-6-15-2.webp"
    )
