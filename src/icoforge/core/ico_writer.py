"""ICO file writing.

Builds the ICO binary container manually rather than delegating to
``Image.save(format="ICO", sizes=...)``.  Pillow's built-in ICO saver
re-rescales a single base image for every entry, which discards per-size
processing (different resample algorithms, per-size source overrides from
phase 2).  Writing the container by hand lets us embed each pre-processed
image verbatim.

ICO binary layout (all integers little-endian):
  ICONDIR        6 bytes  – magic / entry count
  ICONDIRENTRY  16 bytes  – one per image (offset + metadata)
  image data           – PNG or DIB per entry; we always use PNG
"""

from __future__ import annotations

import io
import struct
from pathlib import Path

from PIL import Image

from icoforge.core.models import SizeSpec

# --- struct formats (little-endian) -----------------------------------------

# ICONDIR: reserved(H) type(H) count(H)
_ICONDIR = struct.Struct("<HHH")

# ICONDIRENTRY: width(B) height(B) colorCount(B) reserved(B)
#               planes(H) bitCount(H) bytesInRes(I) imageOffset(I)
_ICONDIRENTRY = struct.Struct("<BBBBHHII")

_ICONDIR_SIZE = _ICONDIR.size        # 6
_ICONDIRENTRY_SIZE = _ICONDIRENTRY.size  # 16


def write_ico(target: Path, images: list[tuple[Image.Image, SizeSpec]]) -> None:
    """Write a multi-size ICO file from a list of pre-processed images.

    Each image is embedded verbatim as a PNG chunk inside the ICO container,
    so per-size resampling decisions made upstream are fully preserved.

    Args:
        target: Destination path for the ``.ico`` file.  Parent directories
            are created automatically.
        images: Pre-sized ``(image, spec)`` pairs.  Every image must already
            be at the dimensions stated in its :class:`~icoforge.core.models.SizeSpec`;
            pass an empty list to get a ``ValueError``.

    Raises:
        ValueError: ``images`` is empty, or an image's pixel dimensions do not
            match its ``SizeSpec``.
    """
    if not images:
        raise ValueError("Cannot write an ICO file with no images")

    _validate_sizes(images)

    # Sort largest-first – conventional order in ICO files.
    ordered = sorted(images, key=lambda pair: pair[1].width * pair[1].height, reverse=True)

    encoded = [_encode_png(img) for img, _ in ordered]

    n = len(ordered)
    data_start = _ICONDIR_SIZE + _ICONDIRENTRY_SIZE * n

    offsets: list[int] = []
    cursor = data_start
    for blob in encoded:
        offsets.append(cursor)
        cursor += len(blob)

    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("wb") as fh:
        fh.write(_ICONDIR.pack(0, 1, n))
        for (_, spec), blob, offset in zip(ordered, encoded, offsets):
            fh.write(_pack_entry(spec, len(blob), offset))
        for blob in encoded:
            fh.write(blob)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _validate_sizes(images: list[tuple[Image.Image, SizeSpec]]) -> None:
    for img, spec in images:
        if img.size != (spec.width, spec.height):
            raise ValueError(
                f"Image size {img.size} does not match SizeSpec "
                f"{(spec.width, spec.height)}"
            )


def _encode_png(img: Image.Image) -> bytes:
    """Encode an image as PNG bytes (RGBA, lossless)."""
    rgba = img if img.mode == "RGBA" else img.convert("RGBA")
    buf = io.BytesIO()
    rgba.save(buf, format="PNG")
    return buf.getvalue()


def _pack_entry(spec: SizeSpec, blob_size: int, offset: int) -> bytes:
    """Pack one ICONDIRENTRY.

    Width/height are stored as 0 when the dimension is 256 (ICO convention).
    """
    w = 0 if spec.width == 256 else spec.width
    h = 0 if spec.height == 256 else spec.height
    return _ICONDIRENTRY.pack(
        w, h,
        0,               # colorCount – 0 means more than 256 colours
        0,               # reserved
        1,               # planes
        spec.bit_depth,  # bitCount
        blob_size,
        offset,
    )
