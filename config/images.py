"""WebP conversion for uploaded media.

Product photos arrived as multi-megabyte PNGs (up to ~5000 px), while the
site never shows them larger than ~600 CSS px. Serving them as-is burned
through the media bucket's daily download allowance in a few dozen page
views. Images are therefore stored as WebP, scaled down to at most
:data:`MAX_SIZE` px on the longer side, which keeps them sharp on 2x
(Retina) screens at a fraction of the size.
"""

import io
from pathlib import PurePosixPath

from PIL import Image, ImageOps

MAX_SIZE = 1200
QUALITY = 85
WEBP_SUFFIX = ".webp"


def to_webp(data: bytes) -> bytes:
    """Convert image bytes to a WebP no larger than :data:`MAX_SIZE` px.

    Transparency is kept; smaller images are not upscaled.

    Args:
        data: The source image in any format Pillow can read.

    Returns:
        The WebP-encoded image.

    Raises:
        PIL.UnidentifiedImageError: ``data`` is not an image.
    """
    with Image.open(io.BytesIO(data)) as source:
        image = ImageOps.exif_transpose(source)
        has_alpha = image.mode in ("RGBA", "LA", "PA") or (
            image.mode == "P" and "transparency" in image.info
        )
        image = image.convert("RGBA" if has_alpha else "RGB")
        image.thumbnail((MAX_SIZE, MAX_SIZE), Image.Resampling.LANCZOS)
        out = io.BytesIO()
        image.save(out, "WEBP", quality=QUALITY, method=6)
    return out.getvalue()


def webp_name(name: str) -> str:
    """Return the storage name ``name`` gets once converted to WebP.

    Args:
        name: A storage path, e.g. ``"equipment/hd-6-15.png"``.

    Returns:
        The same path with a ``.webp`` suffix, e.g. ``"equipment/hd-6-15.webp"``.
    """
    return str(PurePosixPath(name).with_suffix(WEBP_SUFFIX))
