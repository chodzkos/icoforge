"""ICO file writing.

Builds the ICO binary container manually rather than delegating to
``Image.save(format="ICO", sizes=...)``.  Pillow's built-in ICO saver
re-rescales a single base image for every entry, which discards per-size
processing (different resample algorithms, per-size source overrides from
phase 2).  Writing the container by hand lets us embed each pre-processed
image verbatim.

ICO binary layout (all integers little-endian):
  ICONDIR        6 bytes  - magic / entry count
  ICONDIRENTRY  16 bytes  - one per image (offset + metadata)
  image data           - PNG per entry, bit depth determined by SizeSpec.bit_depth
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

_ICONDIR_SIZE = _ICONDIR.size  # 6
_ICONDIRENTRY_SIZE = _ICONDIRENTRY.size  # 16


def write_ico(target: Path, images: list[tuple[Image.Image, SizeSpec]]) -> None:
    """Write a multi-size ICO file from a list of pre-processed images.

    Each image is embedded as a PNG chunk inside the ICO container.  The PNG
    colour mode and the ICONDIRENTRY bitCount field both reflect the
    ``SizeSpec.bit_depth`` of that entry:

    * ``32`` - RGBA PNG (full alpha channel).
    * ``24`` - RGB PNG (no alpha; transparent pixels should be pre-composited
      by the caller onto a solid background, see :func:`converter._flatten_alpha`).
    * ``8``  - palette PNG (mode P, up to 256 colours; transparency is preserved
      via the PNG ``tRNS`` chunk when the source has an alpha channel).

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

    # Sort largest-first - conventional order in ICO files.
    ordered = sorted(images, key=lambda pair: pair[1].width * pair[1].height, reverse=True)

    encoded = [_encode_png(img, spec.bit_depth) for img, spec in ordered]

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
        for (_, spec), blob, offset in zip(ordered, encoded, offsets, strict=False):
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
                f"Image size {img.size} does not match SizeSpec {(spec.width, spec.height)}"
            )


def _encode_png(img: Image.Image, bit_depth: int) -> bytes:
    """Encode *img* as PNG bytes at the requested *bit_depth*.

    Args:
        img: Source image (any mode; converted internally).
        bit_depth: Target colour depth — 8 (palette), 24 (RGB), or 32 (RGBA).

    Returns:
        Raw PNG bytes ready for embedding in the ICO container.
    """
    buf = io.BytesIO()
    if bit_depth == 8:
        rgba = img if img.mode == "RGBA" else img.convert("RGBA")
        palette_img = rgba.quantize(colors=256)
        palette_img.save(buf, format="PNG")
    elif bit_depth == 24:
        # 24-bit PNG carries no alpha. A bare convert("RGB") would expose the raw
        # RGB of transparent pixels (usually black); composite onto white first so
        # transparency renders as white, matching converter._flatten_alpha. The
        # caller (converter) normally pre-flattens onto the configured background;
        # this keeps ico_writer correct on its own too.
        rgba = img if img.mode == "RGBA" else img.convert("RGBA")
        canvas = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        canvas.alpha_composite(rgba)
        rgb = canvas.convert("RGB")
        rgb.save(buf, format="PNG")
    else:  # 32
        rgba = img if img.mode == "RGBA" else img.convert("RGBA")
        rgba.save(buf, format="PNG")
    return buf.getvalue()


def _pack_entry(spec: SizeSpec, blob_size: int, offset: int) -> bytes:
    """Pack one ICONDIRENTRY.

    Width/height are stored as 0 when the dimension is 256 (ICO convention).
    ``bitCount`` reflects the actual PNG colour depth so the directory header
    is consistent with the embedded image data.
    """
    w = 0 if spec.width == 256 else spec.width
    h = 0 if spec.height == 256 else spec.height
    return _ICONDIRENTRY.pack(
        w,
        h,
        0,  # colorCount - 0 means more than 256 colours
        0,  # reserved
        1,  # planes
        spec.bit_depth,  # bitCount — matches the PNG mode written by _encode_png
        blob_size,
        offset,
    )
