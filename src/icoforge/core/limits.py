"""Resource limits for handling untrusted input files.

IcoForge opens files that may originate from the internet (ICO/SVG/PE/raster
images).  Such input can be hostile in two ways this module defends against:

1. **Decompression bombs.**  A tiny compressed file can declare enormous pixel
   dimensions (e.g. a 30000x30000 PNG entry expands to ~3.6 GB of RGBA), which
   would exhaust memory.  Importing this module installs a global
   :data:`PIL.Image.MAX_IMAGE_PIXELS` cap, and :func:`guard_decompression_bomb`
   turns Pillow's bomb signals into a clean :class:`ValueError` at each decode
   site instead of crashing.

2. **Oversized files.**  :func:`check_file_size` rejects files that are larger
   than a per-format limit *before* they are read into memory.

The pixel cap is applied as an import side effect; :mod:`icoforge.core` imports
this module so the cap is in place for the whole package.  The limits are plain
module attributes so callers (and tests) can override them at runtime.
"""

from __future__ import annotations

import contextlib
import warnings
from collections.abc import Iterator
from pathlib import Path

from PIL import Image

# Maximum number of decoded pixels Pillow will accept for a single image.
# 64 MP is ~8000x8000 (~256 MB as RGBA) — comfortably above any real icon
# source while blocking 30000x30000-style bombs.
MAX_IMAGE_PIXELS: int = 64_000_000

# Per-format on-disk size caps, in bytes.  Generous enough for legitimate files
# but bounded so a hostile download cannot force an unbounded read.
_MB: int = 1024 * 1024
MAX_ICO_BYTES: int = 64 * _MB
MAX_SVG_BYTES: int = 64 * _MB
MAX_IMAGE_BYTES: int = 64 * _MB  # raster / HEIC source
MAX_PNG_BYTES: int = 64 * _MB  # optimizer input
MAX_PE_BYTES: int = 128 * _MB  # EXE / DLL / OCX


def _install_pillow_limits() -> None:
    """Install the global Pillow decompression-bomb pixel cap (idempotent)."""
    Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS


_install_pillow_limits()


def check_file_size(path: Path, max_bytes: int) -> None:
    """Raise :class:`ValueError` when *path* is larger than *max_bytes*.

    Call this before reading an untrusted file into memory.

    Args:
        path: File to measure.
        max_bytes: Inclusive maximum size in bytes.

    Raises:
        ValueError: The file exceeds *max_bytes*.
    """
    size = path.stat().st_size
    if size > max_bytes:
        raise ValueError(
            f"File too large: {path} is {size:,} bytes, which exceeds the {max_bytes:,}-byte limit."
        )


@contextlib.contextmanager
def guard_decompression_bomb() -> Iterator[None]:
    """Turn Pillow decompression-bomb signals into a clean :class:`ValueError`.

    Pillow raises :class:`PIL.Image.DecompressionBombError` for images whose
    pixel count exceeds twice :data:`PIL.Image.MAX_IMAGE_PIXELS`, and emits a
    :class:`PIL.Image.DecompressionBombWarning` between the limit and twice it.
    Inside this context the warning is promoted to an error (via
    :func:`warnings.simplefilter`) so neither can slip through, and both are
    re-raised as a :class:`ValueError` suitable for input-validation handling.

    Wrap any decode of untrusted image data (``Image.open`` + ``load``/``verify``
    /``convert``) in this context.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        try:
            yield
        except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
            raise ValueError(
                f"Image exceeds the safe decode limit of {Image.MAX_IMAGE_PIXELS:,} pixels: {exc}"
            ) from exc
