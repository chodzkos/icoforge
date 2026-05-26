"""SVG rasterization for SVG → ICO conversion.

SVG sources are rasterized independently for each target size to preserve
vector quality (unlike raster sources which are loaded once and downscaled).

Two optional backends are supported, tried in order:

1. **resvg-py** (``pip install resvg-py``) - pure-Rust wheel, no external DLLs,
   works out-of-the-box on Windows.  Renders at original SVG size then resizes
   with Pillow.
2. **cairosvg** (``pip install 'icoforge[svg]'``) - requires ``libcairo-2.dll``
   on Windows (bundled in the official installer).  Renders natively at the
   requested pixel size.

If neither is available, :func:`rasterize_svg` raises
:class:`SvgSupportMissingError`.  The rest of :mod:`icoforge` continues to work
without SVG support.
"""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

# ---------------------------------------------------------------------------
# Backend detection - run once at import time
# ---------------------------------------------------------------------------

_ENGINE: str | None = None
_SVG_ERROR: str = ""
_resvg_py: object = None
_cairosvg: object = None

# 1. Try resvg-py (no external DLL on Windows)
try:
    import resvg_py as _resvg_py  # type: ignore[no-redef]

    _ENGINE = "resvg"
except ImportError:
    pass

# 2. Fall back to cairosvg (needs libcairo-2.dll bundled or system-installed)
if _ENGINE is None:
    try:
        import cairosvg as _cairosvg  # type: ignore[no-redef]

        _ENGINE = "cairosvg"
    except (ImportError, OSError) as _e:
        _SVG_ERROR = str(_e)

HAS_SVG: bool = _ENGINE is not None
# Keep legacy name for backward compatibility
HAS_CAIROSVG = HAS_SVG


class SvgSupportMissingError(RuntimeError):
    """Raised when an SVG source is requested but no SVG backend is available."""

    def __init__(self, detail: str = "") -> None:
        msg = (
            "SVG support requires an optional dependency.\n"
            "Install resvg-py:   pip install resvg-py\n"
            "  or cairosvg:      pip install 'icoforge[svg]'"
        )
        if detail:
            msg += f"\nDetails: {detail}"
        super().__init__(msg)


def rasterize_svg(source: Path, width: int, height: int) -> Image.Image:
    """Rasterize an SVG file to a PIL RGBA image at the requested size.

    Each call produces a fresh rasterization at the target dimensions.

    Args:
        source: Path to the SVG file.
        width: Target width in pixels (must be positive).
        height: Target height in pixels (must be positive).

    Returns:
        RGBA image at exactly ``(width, height)``.

    Raises:
        SvgSupportMissingError: No SVG backend is installed/loadable.
        FileNotFoundError: ``source`` does not exist.
        ValueError: ``width`` or ``height`` is not positive.
    """
    if _ENGINE is None:
        raise SvgSupportMissingError(_SVG_ERROR)

    if not source.exists():
        raise FileNotFoundError(source)

    if width <= 0 or height <= 0:
        raise ValueError(f"width and height must be positive, got {width}x{height}")

    if _ENGINE == "resvg":
        svg_bytes = source.read_bytes()
        png_bytes: bytes = _resvg_py.svg_to_png(svg_bytes)  # type: ignore[attr-defined]
        img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
        if img.size != (width, height):
            img = img.resize((width, height), Image.Resampling.LANCZOS)
        return img

    # cairosvg - renders natively at target size
    png_bytes = _cairosvg.svg2png(  # type: ignore[attr-defined]
        url=str(source.resolve()),
        output_width=width,
        output_height=height,
    )
    return Image.open(io.BytesIO(png_bytes)).convert("RGBA")
