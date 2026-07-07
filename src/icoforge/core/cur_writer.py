"""Windows cursor (.cur) file writing.

The CUR format is structurally identical to ICO with two differences:

1. ICONDIR type field is 2 (cursor) instead of 1 (icon).
2. Each ICONDIRENTRY stores the cursor hotspot in the ``planes`` (hotspot X)
   and ``bitCount`` (hotspot Y) fields instead of the planes/bit-depth values
   used by ICO entries.

Binary layout (all integers little-endian):
  ICONDIR        6 bytes  - reserved(H)=0  type(H)=2  count(H)=n
  ICONDIRENTRY  16 bytes  - width(B) height(B) colorCount(B) reserved(B)
                            hotspot_x(H) hotspot_y(H) bytesInRes(I) imageOffset(I)
  image data              - PNG per entry (same as modern ICO)
"""

from __future__ import annotations

import io
import struct
from pathlib import Path

from PIL import Image

from icoforge.core.models import SizeSpec

# --- struct formats (little-endian) -----------------------------------------

_ICONDIR = struct.Struct("<HHH")  # reserved, type, count
_ICONDIRENTRY = struct.Struct("<BBBBHHII")  # same 16-byte shape as ICO

_ICONDIR_SIZE = _ICONDIR.size  # 6
_ICONDIRENTRY_SIZE = _ICONDIRENTRY.size  # 16

_CUR_TYPE = 2  # distinguishes .cur from .ico (type=1)


def write_cur(
    target: Path,
    images: list[tuple[Image.Image, SizeSpec]],
    hotspot: tuple[int, int] = (0, 0),
) -> None:
    """Write a multi-size Windows cursor (.cur) file.

    Each image is embedded as a PNG chunk.  The hotspot is given relative to the
    largest frame and scaled proportionally for each smaller frame, so every
    size points at the same logical location.

    Args:
        target: Destination path for the ``.cur`` file.  Parent directories
            are created automatically.
        images: Pre-sized ``(image, spec)`` pairs.  Every image must already
            be at the dimensions stated in its :class:`~icoforge.core.models.SizeSpec`.
        hotspot: ``(x, y)`` pixel coordinates of the cursor hot point,
            relative to the top-left corner of the **largest** frame.  For every
            smaller frame the hotspot is scaled proportionally so it points at
            the same logical location.  Defaults to ``(0, 0)`` (top-left corner).

    Raises:
        ValueError: ``images`` is empty, an image's pixel dimensions do not
            match its ``SizeSpec``, or the hotspot lies outside the largest
            frame.
    """
    if not images:
        raise ValueError("Cannot write a CUR file with no images")

    _validate_sizes(images)

    hx, hy = hotspot
    ordered = sorted(images, key=lambda pair: pair[1].width * pair[1].height, reverse=True)
    ref_spec = ordered[0][1]
    _validate_hotspot(hx, hy, ref_spec.width, ref_spec.height)
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
        fh.write(_ICONDIR.pack(0, _CUR_TYPE, n))
        for (_, spec), blob, offset in zip(ordered, encoded, offsets, strict=False):
            fhx, fhy = _scale_hotspot(hx, hy, ref_spec, spec)
            fh.write(_pack_cur_entry(spec, blob_size=len(blob), offset=offset, hx=fhx, hy=fhy))
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


def _validate_hotspot(hx: int, hy: int, ref_w: int, ref_h: int) -> None:
    """Ensure the hotspot lies inside the largest (reference) frame."""
    if not (0 <= hx < ref_w) or not (0 <= hy < ref_h):
        raise ValueError(f"Hotspot ({hx}, {hy}) is outside the largest frame {ref_w}x{ref_h}.")


def _scale_hotspot(hx: int, hy: int, ref_spec: SizeSpec, spec: SizeSpec) -> tuple[int, int]:
    """Scale a reference-frame hotspot to *spec*'s dimensions.

    The reference frame keeps the hotspot verbatim; smaller frames scale it
    proportionally and clamp it inside their own bounds.
    """
    if spec.width == ref_spec.width and spec.height == ref_spec.height:
        return hx, hy
    fx = min(max(round(hx * spec.width / ref_spec.width), 0), spec.width - 1)
    fy = min(max(round(hy * spec.height / ref_spec.height), 0), spec.height - 1)
    return fx, fy


def _encode_png(img: Image.Image) -> bytes:
    rgba = img if img.mode == "RGBA" else img.convert("RGBA")
    buf = io.BytesIO()
    rgba.save(buf, format="PNG")
    return buf.getvalue()


def _pack_cur_entry(
    spec: SizeSpec,
    *,
    blob_size: int,
    offset: int,
    hx: int,
    hy: int,
) -> bytes:
    """Pack one ICONDIRENTRY for a cursor frame.

    Width/height stored as 0 when dimension is 256 (same ICO convention).
    The ``planes`` field carries hotspot X and ``bitCount`` carries hotspot Y.
    """
    w = 0 if spec.width == 256 else spec.width
    h = 0 if spec.height == 256 else spec.height
    return _ICONDIRENTRY.pack(
        w,
        h,
        0,  # colorCount
        0,  # reserved
        hx,  # hotspot X (reuses the planes field)
        hy,  # hotspot Y (reuses the bitCount field)
        blob_size,
        offset,
    )
