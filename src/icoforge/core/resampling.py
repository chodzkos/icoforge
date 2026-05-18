"""Resampling algorithm mapping and helpers.

Pillow's Resampling enum is what we ultimately use, but we wrap it so the rest
of the codebase doesn't import Pillow types directly.
"""

from __future__ import annotations

from PIL import Image

from icoforge.core.models import ResampleAlgorithm

_PILLOW_RESAMPLE_MAP: dict[ResampleAlgorithm, Image.Resampling] = {
    ResampleAlgorithm.LANCZOS: Image.Resampling.LANCZOS,
    ResampleAlgorithm.BICUBIC: Image.Resampling.BICUBIC,
    ResampleAlgorithm.BILINEAR: Image.Resampling.BILINEAR,
    ResampleAlgorithm.NEAREST: Image.Resampling.NEAREST,
    ResampleAlgorithm.BOX: Image.Resampling.BOX,
}


def to_pillow(algo: ResampleAlgorithm) -> Image.Resampling:
    """Convert our algorithm enum to a Pillow Resampling value."""
    return _PILLOW_RESAMPLE_MAP[algo]


def recommend_for_size(target_size: int, is_pixel_art: bool = False) -> ResampleAlgorithm:
    """Pick a sensible default algorithm for a given target size.

    Args:
        target_size: Target dimension in pixels (width or height of square icon).
        is_pixel_art: True if the source is pixel art and sharp edges matter.

    Returns:
        Recommended algorithm.
    """
    if is_pixel_art:
        return ResampleAlgorithm.NEAREST
    if target_size <= 24:
        return ResampleAlgorithm.BOX  # Better for aggressive downscaling
    return ResampleAlgorithm.LANCZOS
