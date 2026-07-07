"""Favicon set generator.

Generates a complete set of web-ready favicon assets from a single source
image:
  - favicon.ico         — multi-size ICO (16, 32, 48 px)
  - apple-touch-icon.png — 180x180 on solid white (no transparency)
  - icon-192.png         — PWA icon, RGBA
  - icon-512.png         — PWA icon, RGBA
  - site.webmanifest     — JSON manifest template with icon entries
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from PIL import Image

from icoforge.core.models import IcoConfig, SizeSpec

ProgressCallback = Callable[[float], None]


def generate_favicon_set(
    source: Path,
    output_dir: Path,
    *,
    resample: Image.Resampling = Image.Resampling.LANCZOS,
    progress: ProgressCallback | None = None,
) -> list[Path]:
    """Generate a complete web favicon set from *source* into *output_dir*.

    Creates five files:
    ``favicon.ico``, ``apple-touch-icon.png``, ``icon-192.png``,
    ``icon-512.png``, and ``site.webmanifest``.

    Args:
        source: Path to the source image (PNG, JPG, SVG, WEBP, …).
        output_dir: Directory where all output files will be written.
            Created automatically if it does not exist.
        resample: PIL resampling filter used when resizing.
        progress: Optional callback receiving values in ``[0.0, 1.0]``.

    Returns:
        List of :class:`~pathlib.Path` objects for the five generated files,
        in the order listed above.

    Raises:
        FileNotFoundError: *source* does not exist.
        ValueError: *source* has an unsupported format.
    """
    if not source.exists():
        raise FileNotFoundError(source)

    output_dir.mkdir(parents=True, exist_ok=True)

    _report(progress, 0.0)

    # Load source once; keep it in memory for all derivative sizes.
    img = _load_rgba(source)

    _report(progress, 0.1)

    generated: list[Path] = []

    # 1. favicon.ico — 16, 32, 48 px
    ico_path = output_dir / "favicon.ico"
    _write_favicon_ico(img, ico_path, resample)
    generated.append(ico_path)
    _report(progress, 0.3)

    # 2. apple-touch-icon.png — 180x180, white background
    touch_path = output_dir / "apple-touch-icon.png"
    _write_png_on_white(img, touch_path, 180, resample)
    generated.append(touch_path)
    _report(progress, 0.5)

    # 3. icon-192.png — PWA, RGBA
    p192 = output_dir / "icon-192.png"
    _write_png_rgba(img, p192, 192, resample)
    generated.append(p192)
    _report(progress, 0.7)

    # 4. icon-512.png — PWA, RGBA
    p512 = output_dir / "icon-512.png"
    _write_png_rgba(img, p512, 512, resample)
    generated.append(p512)
    _report(progress, 0.85)

    # 5. site.webmanifest
    manifest_path = output_dir / "site.webmanifest"
    _write_webmanifest(manifest_path)
    generated.append(manifest_path)
    _report(progress, 1.0)

    return generated


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _report(progress: ProgressCallback | None, value: float) -> None:
    if progress is not None:
        progress(value)


def _load_rgba(source: Path) -> Image.Image:
    """Open *source* and normalise to RGBA."""
    suffix = source.suffix.lower()

    if suffix == ".svg":
        from icoforge.core.svg_loader import rasterize_svg_natural

        # Rasterize at the SVG's natural aspect ratio; _resize_cover then
        # letterboxes to square, preserving proportions (forcing 512x512 here
        # would stretch a non-square SVG).
        return rasterize_svg_natural(source)

    if suffix in {".heic", ".heif", ".avif"}:
        from icoforge.core.heic_loader import load_heic

        return load_heic(source)

    supported = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tiff", ".tif"}
    if suffix not in supported:
        raise ValueError(f"Unsupported source format: '{suffix}'. Supported: {sorted(supported)}")
    with Image.open(source) as _img:
        return _img.convert("RGBA")


def _resize_cover(img: Image.Image, size: int, resample: Image.Resampling) -> Image.Image:
    """Resize *img* to *size*x*size*, letterboxing to preserve aspect ratio."""
    target = (size, size)
    w, h = img.size
    if w == h:
        return img.resize(target, resample=resample)
    scale = size / max(w, h)
    new_w, new_h = max(1, round(w * scale)), max(1, round(h * scale))
    resized = img.resize((new_w, new_h), resample=resample)
    canvas = Image.new("RGBA", target, (0, 0, 0, 0))
    x = (size - new_w) // 2
    y = (size - new_h) // 2
    canvas.paste(resized, (x, y))
    return canvas


def _write_favicon_ico(img: Image.Image, target: Path, resample: Image.Resampling) -> None:
    """Write a 16/32/48 multi-size ICO to *target*."""
    # We have the image in memory; write it to a temp PNG so converter can read it.
    import tempfile

    from icoforge.core.converter import convert as run_convert
    from icoforge.core.resampling import from_pillow

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        img.save(tmp_path, format="PNG")
        config = IcoConfig(
            sizes=tuple(SizeSpec(s, s) for s in (16, 32, 48)),
            resample=from_pillow(resample),
        )
        run_convert(tmp_path, target, config)
    finally:
        tmp_path.unlink(missing_ok=True)


def _write_png_on_white(
    img: Image.Image, target: Path, size: int, resample: Image.Resampling
) -> None:
    """Write *img* resized to *size*x*size* onto a solid white background."""
    resized = _resize_cover(img, size, resample)
    canvas = Image.new("RGBA", (size, size), (255, 255, 255, 255))
    canvas.paste(resized, (0, 0), resized)
    canvas.convert("RGB").save(target, format="PNG", optimize=True)


def _write_png_rgba(img: Image.Image, target: Path, size: int, resample: Image.Resampling) -> None:
    """Write *img* resized to *size*x*size* as RGBA PNG."""
    resized = _resize_cover(img, size, resample)
    resized.save(target, format="PNG", optimize=True)


def _write_webmanifest(target: Path) -> None:
    """Write a minimal ``site.webmanifest`` JSON template."""
    manifest = {
        "name": "",
        "short_name": "",
        "icons": [
            {"src": "icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "icon-512.png", "sizes": "512x512", "type": "image/png"},
        ],
        "theme_color": "#ffffff",
        "background_color": "#ffffff",
        "display": "standalone",
    }
    target.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
