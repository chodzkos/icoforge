"""Resampling algorithm mapping and helpers.

Pillow's Resampling enum is what we ultimately use, but the rest of the
codebase should not import Pillow types directly — that would scatter a
third-party dependency across every module.  Import ``ResampleAlgorithm``
from ``models`` and call :func:`to_pillow` here, at the last moment before
Pillow needs it.

Threshold rationale for :func:`recommend_for_size`:
- BOX at ≤ 24 px: at that scale the downscaling ratio from a typical 256 px
  source is ≥ 10 : 1.  LANCZOS can produce ringing at such extremes; BOX
  averages the contributing pixels uniformly and gives cleaner small icons.
- LANCZOS at ≥ 25 px: best overall quality for moderate downscaling.
- NEAREST for pixel art: preserves hard edges regardless of size.
"""

from __future__ import annotations

from PIL import Image

from icoforge.core.models import ResampleAlgorithm

_PILLOW_MAP: dict[ResampleAlgorithm, Image.Resampling] = {
    ResampleAlgorithm.LANCZOS: Image.Resampling.LANCZOS,
    ResampleAlgorithm.BICUBIC: Image.Resampling.BICUBIC,
    ResampleAlgorithm.BILINEAR: Image.Resampling.BILINEAR,
    ResampleAlgorithm.NEAREST: Image.Resampling.NEAREST,
    ResampleAlgorithm.BOX: Image.Resampling.BOX,
}

# Fail at import time if a new enum member is added without updating the map.
_missing = set(ResampleAlgorithm) - _PILLOW_MAP.keys()
if _missing:
    raise RuntimeError(f"_PILLOW_MAP is missing entries for: {_missing}")


_ALGO_MAP: dict[Image.Resampling, ResampleAlgorithm] = {v: k for k, v in _PILLOW_MAP.items()}


def to_pillow(algo: ResampleAlgorithm) -> Image.Resampling:
    """Convert a :class:`~icoforge.core.models.ResampleAlgorithm` to a Pillow value.

    Args:
        algo: One of the supported resampling algorithms.

    Returns:
        The corresponding ``PIL.Image.Resampling`` constant.
    """
    return _PILLOW_MAP[algo]


def from_pillow(resampling: Image.Resampling) -> ResampleAlgorithm:
    """Convert a Pillow ``Resampling`` value back to a :class:`ResampleAlgorithm`.

    Args:
        resampling: A ``PIL.Image.Resampling`` constant.

    Returns:
        The corresponding :class:`~icoforge.core.models.ResampleAlgorithm`.

    Raises:
        KeyError: *resampling* is not one of the supported filters.
    """
    return _ALGO_MAP[resampling]


# Sizes at or below this threshold get BOX instead of LANCZOS.
_BOX_THRESHOLD = 24


def recommend_for_size(target_size: int, *, is_pixel_art: bool = False) -> ResampleAlgorithm:
    """Pick the best resampling algorithm for a given target icon size.

    Args:
        target_size: Target dimension in pixels (width or height of a square
            icon).  Must be positive.
        is_pixel_art: Pass ``True`` when the source is pixel art or any image
            where hard edges must be preserved exactly.

    Returns:
        - :attr:`~ResampleAlgorithm.NEAREST` when ``is_pixel_art`` is ``True``.
        - :attr:`~ResampleAlgorithm.BOX` when ``target_size`` ≤ 24 px.
        - :attr:`~ResampleAlgorithm.LANCZOS` otherwise.

    Raises:
        ValueError: ``target_size`` is not a positive integer.
    """
    if target_size < 1:
        raise ValueError(f"target_size must be ≥ 1, got {target_size}")
    if is_pixel_art:
        return ResampleAlgorithm.NEAREST
    if target_size <= _BOX_THRESHOLD:
        return ResampleAlgorithm.BOX
    return ResampleAlgorithm.LANCZOS
