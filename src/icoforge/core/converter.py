"""High-level conversion pipeline.

The single public entry point is :func:`convert`.  It handles:
- Loading the source into a normalised RGBA canvas (raster) or rasterizing
  the source per-size (SVG, via :mod:`icoforge.core.svg_loader`).
- Resizing to each requested size (letterboxing when ``preserve_aspect=True``).
- Writing the resulting ICO via :func:`~icoforge.core.ico_writer.write_ico`.

Supported source formats: PNG, JPEG, BMP, GIF, WEBP, TIFF, SVG.
HEIC support is planned for a later phase.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PIL import Image

from icoforge.core import resampling, svg_loader
from icoforge.core.ico_writer import write_ico
from icoforge.core.models import (
    TRANSPARENT,
    Background,
    Color,
    IcoConfig,
    SizeSpec,
)

_RASTER_SUFFIXES: frozenset[str] = frozenset(
    {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tiff", ".tif"}
)
_SVG_SUFFIXES: frozenset[str] = frozenset({".svg"})
_SUPPORTED_SUFFIXES: frozenset[str] = _RASTER_SUFFIXES | _SVG_SUFFIXES

ProgressCallback = Callable[[float], None]


def convert(
    source: Path,
    target: Path,
    config: IcoConfig,
    progress: ProgressCallback | None = None,
) -> None:
    """Convert a source image to a multi-size ICO file.

    Args:
        source: Path to the source image.  Format is detected by extension.
        target: Path where the resulting ``.ico`` will be written.
            Parent directories are created automatically.
        config: Conversion parameters (sizes, resampling, background, …).
        progress: Optional callback receiving monotonically increasing values
            in ``[0.0, 1.0]``.  Called at the start (0.0), after loading the
            source, after each resized frame, and at completion (1.0).

    Raises:
        FileNotFoundError: ``source`` does not exist.
        ValueError: ``source`` has an unsupported extension.
        SvgSupportMissingError: source is SVG but ``cairosvg`` is not installed.
    """
    _validate_source(source)
    _report(progress, 0.0)

    sized = _render_sized_frames(source, config, progress)
    write_ico(target, sized)
    _report(progress, 1.0)


def render_frames(
    source: Path,
    config: IcoConfig,
    progress: ProgressCallback | None = None,
) -> list[Image.Image]:
    """Render all ICO frames without writing to disk.

    Returns one RGBA image per size in ``config.sizes``, in the same order.
    Intended for GUI preview; heavy work should run in a background thread.

    Args:
        source: Path to the source image.
        config: Conversion parameters (sizes, resampling, background, …).
        progress: Optional progress callback (same contract as :func:`convert`).

    Raises:
        FileNotFoundError: ``source`` does not exist.
        ValueError: ``source`` has an unsupported extension.
        SvgSupportMissingError: source is SVG but ``cairosvg`` is not installed.
    """
    _validate_source(source)
    _report(progress, 0.0)
    sized = _render_sized_frames(source, config, progress)
    _report(progress, 1.0)
    return [frame for frame, _ in sized]


# ---------------------------------------------------------------------------
# Internal pipeline
# ---------------------------------------------------------------------------


def _validate_source(source: Path) -> None:
    if not source.exists():
        raise FileNotFoundError(source)
    suffix = source.suffix.lower()
    if suffix not in _SUPPORTED_SUFFIXES:
        raise ValueError(
            f"Unsupported source format: '{suffix}'. Supported: {sorted(_SUPPORTED_SUFFIXES)}"
        )


def _render_sized_frames(
    source: Path,
    config: IcoConfig,
    progress: ProgressCallback | None,
) -> list[tuple[Image.Image, SizeSpec]]:
    """Dispatch to raster or SVG pipeline and return ``[(frame, spec), …]``."""
    suffix = source.suffix.lower()
    if suffix in _SVG_SUFFIXES:
        return _render_svg_sized(source, config, progress)
    return _render_raster_sized(source, config, progress)


def _render_raster_sized(
    source: Path,
    config: IcoConfig,
    progress: ProgressCallback | None,
) -> list[tuple[Image.Image, SizeSpec]]:
    base = _load_rgba(source, config.background)
    _report(progress, 0.1)

    sized: list[tuple[Image.Image, SizeSpec]] = []
    total = len(config.sizes)
    for i, spec in enumerate(config.sizes):
        frame = _render_frame(base, spec, config)
        sized.append((frame, spec))
        _report(progress, 0.1 + 0.8 * (i + 1) / total)
    return sized


def _render_svg_sized(
    source: Path,
    config: IcoConfig,
    progress: ProgressCallback | None,
) -> list[tuple[Image.Image, SizeSpec]]:
    """Rasterize the SVG fresh for each requested size (vector advantage)."""
    _report(progress, 0.1)

    sized: list[tuple[Image.Image, SizeSpec]] = []
    total = len(config.sizes)
    for i, spec in enumerate(config.sizes):
        frame = svg_loader.rasterize_svg(source, spec.width, spec.height)
        if isinstance(config.background, Color):
            canvas = Image.new("RGBA", frame.size, config.background.as_tuple())
            canvas.alpha_composite(frame)
            frame = canvas
        sized.append((frame, spec))
        _report(progress, 0.1 + 0.8 * (i + 1) / total)
    return sized


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def _load_rgba(path: Path, background: Background) -> Image.Image:
    """Open ``path`` and return a normalised RGBA image.

    Images that already carry an alpha channel (RGBA, LA, P with transparency)
    are converted directly.  Opaque images (RGB, L, CMYK, …) are converted to
    RGBA — all pixels become fully opaque — and then optionally composited onto
    a solid ``background`` colour.  Compositing an opaque image onto a colour
    is a no-op for the image pixels themselves; the background colour becomes
    relevant in the padding areas added by :func:`_resize_with_padding`.

    Args:
        path: Source image file.
        background: Fill colour for padding or for pre-compositing.

    Returns:
        RGBA image ready for resizing.
    """
    img = Image.open(path)

    # Modes with native alpha.
    if img.mode in ("RGBA", "LA"):
        return img.convert("RGBA")

    # Palette mode — may embed a transparency index.
    if img.mode == "P":
        return img.convert("RGBA")

    # Everything else (RGB, L, CMYK, …): no alpha present.
    rgba = img.convert("RGBA")  # pixels become fully opaque (alpha = 255)

    if background == TRANSPARENT:
        return rgba

    # Composite the opaque source onto the chosen solid colour.  For fully
    # opaque sources this is a no-op on image pixels; it matters for padding.
    assert isinstance(background, Color)
    canvas = Image.new("RGBA", rgba.size, background.as_tuple())
    canvas.alpha_composite(rgba)
    return canvas


# ---------------------------------------------------------------------------
# Resizing
# ---------------------------------------------------------------------------


def _render_frame(
    source: Image.Image,
    spec: SizeSpec,
    config: IcoConfig,
) -> Image.Image:
    """Produce one resized frame according to ``spec`` and global ``config``.

    Respects ``spec.resample`` override and ``config.preserve_aspect``.

    Args:
        source: Normalised RGBA source image.
        spec: Target size (and optional per-size overrides).
        config: Global conversion configuration.

    Returns:
        RGBA image at ``(spec.width, spec.height)``.
    """
    algo = spec.resample if spec.resample is not None else config.resample
    pillow_algo = resampling.to_pillow(algo)

    src_w, src_h = source.size
    tgt_w, tgt_h = spec.width, spec.height

    if not config.preserve_aspect or src_w == src_h:
        return source.resize((tgt_w, tgt_h), pillow_algo)

    return _letterbox(source, tgt_w, tgt_h, pillow_algo, config.background)


def _letterbox(
    source: Image.Image,
    tgt_w: int,
    tgt_h: int,
    pillow_algo: Image.Resampling,
    background: Background,
) -> Image.Image:
    """Scale ``source`` to fit within ``tgt_w x tgt_h``, padding the rest.

    The image is scaled uniformly (no stretching) to the largest size that
    fits inside the target box, then centred on a canvas filled with
    ``background``.

    Args:
        source: Source RGBA image.
        tgt_w: Target canvas width.
        tgt_h: Target canvas height.
        pillow_algo: Pillow resampling filter to use.
        background: Colour for the padding area.

    Returns:
        RGBA image at exactly ``(tgt_w, tgt_h)``.
    """
    src_w, src_h = source.size
    scale = min(tgt_w / src_w, tgt_h / src_h)
    fit_w = max(1, round(src_w * scale))
    fit_h = max(1, round(src_h * scale))

    scaled = source.resize((fit_w, fit_h), pillow_algo)

    bg_color: tuple[int, int, int, int] = (
        background.as_tuple() if isinstance(background, Color) else (0, 0, 0, 0)
    )
    canvas = Image.new("RGBA", (tgt_w, tgt_h), bg_color)
    x = (tgt_w - fit_w) // 2
    y = (tgt_h - fit_h) // 2
    canvas.alpha_composite(scaled, dest=(x, y))
    return canvas


# ---------------------------------------------------------------------------
# Progress helper
# ---------------------------------------------------------------------------


def _report(cb: ProgressCallback | None, value: float) -> None:
    if cb is not None:
        cb(max(0.0, min(1.0, value)))
