"""SVG rasterization for SVG → ICO conversion.

SVG sources are rasterized independently for each target size to preserve
vector quality (unlike raster sources which are loaded once and downscaled).

``cairosvg`` is an optional dependency. Install it with::

    pip install 'icoforge[svg]'

If ``cairosvg`` is not available, :func:`rasterize_svg` raises
:class:`SvgSupportMissingError` with installation instructions. The rest of
:mod:`icoforge` continues to work without it.
"""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

try:
    import cairosvg
except ImportError:
    cairosvg = None


HAS_CAIROSVG: bool = cairosvg is not None


class SvgSupportMissingError(RuntimeError):
    """Raised when an SVG source is requested but ``cairosvg`` is unavailable."""

    def __init__(self) -> None:
        super().__init__(
            "SVG support requires the optional 'cairosvg' dependency. "
            "Install it with: pip install 'icoforge[svg]'"
        )


def rasterize_svg(source: Path, width: int, height: int) -> Image.Image:
    """Rasterize an SVG file to a PIL RGBA image at the requested size.

    Each call produces a fresh rasterization at the target dimensions, which
    is the point of using SVG — every ICO size gets its own crisp render
    rather than being downscaled from a single high-resolution bitmap.

    Args:
        source: Path to the SVG file.
        width: Target width in pixels (must be positive).
        height: Target height in pixels (must be positive).

    Returns:
        RGBA image at exactly ``(width, height)``.

    Raises:
        SvgSupportMissingError: ``cairosvg`` is not installed.
        FileNotFoundError: ``source`` does not exist.
        ValueError: ``width`` or ``height`` is not positive.
    """
    if cairosvg is None:
        raise SvgSupportMissingError()

    if not source.exists():
        raise FileNotFoundError(source)

    if width <= 0 or height <= 0:
        raise ValueError(f"width and height must be positive, got {width}x{height}")

    png_bytes = cairosvg.svg2png(
        url=str(source.resolve()),
        output_width=width,
        output_height=height,
    )
    return Image.open(io.BytesIO(png_bytes)).convert("RGBA")
