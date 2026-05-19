"""High-level conversion pipeline.

The single public entry point is :func:`convert`.  It handles:
- Loading the source into a normalised RGBA canvas.
- Resizing to each requested size (letterboxing when ``preserve_aspect=True``).
- Writing the resulting ICO via :func:`~icoforge.core.ico_writer.write_ico`.

Supported source formats (phase 1): PNG, JPEG, BMP, GIF, WEBP, TIFF.
SVG and HEIC support are added in phase 2.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PIL import Image

from icoforge.core import resampling
from icoforge.core.ico_writer import write_ico
from icoforge.core.models import (
    TRANSPARENT,
    Background,
    Color,
    IcoConfig,
    SizeSpec,
)

_SUPPORTED_SUFFIXES: frozenset[str] = frozenset(
    {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tiff", ".tif"}
)

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
    """
    if not source.exists():
        raise FileNotFoundError(source)

    suffix = source.suffix.lower()
    if suffix not in _SUPPORTED_SUFFIXES:
        raise ValueError(
            f"Unsupported source format: '{suffix}'. Supported: {sorted(_SUPPORTED_SUFFIXES)}"
        )

    _report(progress, 0.0)

    base = _load_rgba(source, config.background)
    _report(progress, 0.1)

    sized: list[tuple[Image.Image, SizeSpec]] = []
    total = len(config.sizes)
    for i, spec in enumerate(config.sizes):
        frame = _render_frame(base, spec, config)
        sized.append((frame, spec))
        _report(progress, 0.1 + 0.8 * (i + 1) / total)

    write_ico(target, sized)
    _report(progress, 1.0)


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
