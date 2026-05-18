"""High-level conversion pipeline.

The single public entry point is :func:`convert`. It dispatches by source
file extension and produces an ICO containing all sizes from the config.

This module is the orchestrator. Heavy lifting belongs in:
  - ``ico_writer`` for ICO encoding
  - ``resampling`` for picking resize algorithms
  - format-specific loaders (added in phase 2)
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image

from icoforge.core import resampling
from icoforge.core.models import (
    Background,
    IcoConfig,
    SizeSpec,
    TRANSPARENT,
)

if TYPE_CHECKING:
    ProgressCallback = Callable[[float], None]

# Formats we can load via Pillow directly. Phase 1 only formally supports PNG;
# phase 2 enables the rest.
_PILLOW_SUPPORTED = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tiff", ".tif"}


def convert(
    source: Path,
    target: Path,
    config: IcoConfig,
    progress: Callable[[float], None] | None = None,
) -> None:
    """Convert a source image to a multi-size ICO file.

    Args:
        source: Path to a source image. Format detected by extension.
        target: Path where the resulting ``.ico`` will be written.
        config: Conversion configuration.
        progress: Optional callback receiving values in ``[0.0, 1.0]``.

    Raises:
        FileNotFoundError: Source does not exist.
        ValueError: Unsupported source format or invalid config.
    """
    if not source.exists():
        raise FileNotFoundError(source)

    suffix = source.suffix.lower()
    if suffix not in _PILLOW_SUPPORTED:
        raise ValueError(f"Unsupported source format: {suffix}")

    _report(progress, 0.0)

    # Load source and prepare RGBA canvas. Per-size sources (phase 2) override this.
    base_image = _load_rgba(source, config.background)
    _report(progress, 0.2)

    sized_images = list(_render_sizes(base_image, config, progress=progress))
    _report(progress, 0.9)

    # ICO writer takes a list of (image, size) pairs. Implementation in ico_writer.py.
    from icoforge.core.ico_writer import write_ico  # local import to keep cycles away

    write_ico(target, sized_images)
    _report(progress, 1.0)


def _load_rgba(path: Path, background: Background) -> Image.Image:
    """Load any supported image as RGBA, filling background if needed."""
    img = Image.open(path)
    if img.mode == "RGBA":
        return img.convert("RGBA")
    if img.mode in ("LA", "P") and "transparency" in img.info:
        return img.convert("RGBA")
    # No alpha - decide based on background config
    rgba = img.convert("RGBA")
    if background == TRANSPARENT:
        return rgba
    # Composite onto solid background
    bg = Image.new("RGBA", rgba.size, background.as_tuple())
    bg.alpha_composite(rgba)
    return bg


def _render_sizes(
    source: Image.Image,
    config: IcoConfig,
    progress: Callable[[float], None] | None = None,
) -> list[tuple[Image.Image, SizeSpec]]:
    """Produce one resized image per SizeSpec in the config."""
    out: list[tuple[Image.Image, SizeSpec]] = []
    total = len(config.sizes)
    for i, spec in enumerate(config.sizes):
        algo = spec.resample or config.resample
        pillow_algo = resampling.to_pillow(algo)

        if config.preserve_aspect and source.width != source.height:
            resized = _resize_with_padding(source, spec, pillow_algo, config.background)
        else:
            resized = source.resize((spec.width, spec.height), pillow_algo)

        out.append((resized, spec))
        if progress is not None:
            # Map this phase to roughly 0.2 .. 0.9 of overall progress
            _report(progress, 0.2 + 0.7 * (i + 1) / total)
    return out


def _resize_with_padding(
    source: Image.Image,
    spec: SizeSpec,
    pillow_algo: Image.Resampling,
    background: Background,
) -> Image.Image:
    """Resize preserving aspect ratio, padding the rest with the background."""
    # TODO(phase-1): implement padding properly. For now, naive resize.
    return source.resize((spec.width, spec.height), pillow_algo)


def _report(cb: Callable[[float], None] | None, value: float) -> None:
    if cb is not None:
        cb(max(0.0, min(1.0, value)))
