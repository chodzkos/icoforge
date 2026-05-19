"""Tests for SVG source support via :mod:`icoforge.core.svg_loader`.

Tests covering the actual cairosvg rasterization path are skipped when the
optional ``cairosvg`` dependency is not installed. The graceful-fallback path
(missing-dependency error) is always tested via monkeypatching.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from icoforge.core import svg_loader
from icoforge.core.converter import convert, render_frames
from icoforge.core.models import Color, IcoConfig, SizeSpec
from icoforge.core.svg_loader import SvgSupportMissingError, rasterize_svg

# Minimal valid SVG: red square with blue circle in the centre.
_SIMPLE_SVG = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <rect x="0" y="0" width="100" height="100" fill="red"/>
  <circle cx="50" cy="50" r="30" fill="blue"/>
</svg>
"""

# SVG with transparency (no background, just a coloured shape).
_TRANSPARENT_SVG = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="50" cy="50" r="40" fill="green"/>
</svg>
"""

requires_cairosvg = pytest.mark.skipif(
    not svg_loader.HAS_CAIROSVG,
    reason="cairosvg not installed (optional 'svg' extra)",
)


@pytest.fixture
def simple_svg(tmp_path: Path) -> Path:
    p = tmp_path / "simple.svg"
    p.write_text(_SIMPLE_SVG, encoding="utf-8")
    return p


@pytest.fixture
def transparent_svg(tmp_path: Path) -> Path:
    p = tmp_path / "transparent.svg"
    p.write_text(_TRANSPARENT_SVG, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Graceful fallback when cairosvg is missing
# ---------------------------------------------------------------------------


class TestMissingCairosvg:
    """Verify the user-facing error path when cairosvg is unavailable."""

    def test_rasterize_raises_descriptive_error(
        self, simple_svg: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(svg_loader, "cairosvg", None)
        with pytest.raises(SvgSupportMissingError) as exc_info:
            rasterize_svg(simple_svg, 32, 32)
        message = str(exc_info.value)
        assert "cairosvg" in message
        assert "icoforge[svg]" in message

    def test_convert_svg_raises_when_cairosvg_missing(
        self, simple_svg: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(svg_loader, "cairosvg", None)
        with pytest.raises(SvgSupportMissingError):
            convert(simple_svg, tmp_path / "out.ico", IcoConfig(sizes=(SizeSpec(32, 32),)))

    def test_render_frames_svg_raises_when_cairosvg_missing(
        self, simple_svg: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(svg_loader, "cairosvg", None)
        with pytest.raises(SvgSupportMissingError):
            render_frames(simple_svg, IcoConfig(sizes=(SizeSpec(32, 32),)))

    def test_raster_path_unaffected_when_cairosvg_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Disabling cairosvg must not break the raster pipeline."""
        from PIL import Image

        src = tmp_path / "in.png"
        Image.new("RGBA", (32, 32), (255, 0, 0, 255)).save(src)

        monkeypatch.setattr(svg_loader, "cairosvg", None)
        convert(src, tmp_path / "out.ico", IcoConfig(sizes=(SizeSpec(32, 32),)))
        assert (tmp_path / "out.ico").exists()


# ---------------------------------------------------------------------------
# Input validation (independent of cairosvg)
# ---------------------------------------------------------------------------


class TestSvgValidation:
    def test_rejects_missing_source(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            convert(
                tmp_path / "missing.svg",
                tmp_path / "out.ico",
                IcoConfig(sizes=(SizeSpec(16, 16),)),
            )

    def test_svg_in_supported_suffixes(self) -> None:
        from icoforge.core.converter import _SUPPORTED_SUFFIXES, _SVG_SUFFIXES

        assert ".svg" in _SUPPORTED_SUFFIXES
        assert frozenset([".svg"]) == _SVG_SUFFIXES

    @requires_cairosvg
    def test_rejects_nonpositive_size(self, simple_svg: Path) -> None:
        with pytest.raises(ValueError, match="positive"):
            rasterize_svg(simple_svg, 0, 32)

    def test_rasterize_missing_file_when_cairosvg_present(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        if not svg_loader.HAS_CAIROSVG:
            # Pretend cairosvg is available so the FileNotFoundError path runs.
            monkeypatch.setattr(svg_loader, "cairosvg", object())
        with pytest.raises(FileNotFoundError):
            rasterize_svg(tmp_path / "missing.svg", 32, 32)


# ---------------------------------------------------------------------------
# Real rasterization (requires cairosvg)
# ---------------------------------------------------------------------------


@requires_cairosvg
class TestSvgRasterization:
    def test_rasterize_returns_rgba(self, simple_svg: Path) -> None:
        img = rasterize_svg(simple_svg, 32, 32)
        assert img.mode == "RGBA"
        assert img.size == (32, 32)

    def test_rasterize_honours_requested_size(self, simple_svg: Path) -> None:
        img = rasterize_svg(simple_svg, 16, 16)
        assert img.size == (16, 16)

    def test_convert_produces_ico_with_requested_sizes(
        self, simple_svg: Path, tmp_path: Path
    ) -> None:
        target = tmp_path / "out.ico"
        config = IcoConfig(sizes=(SizeSpec(16, 16), SizeSpec(32, 32), SizeSpec(64, 64)))
        convert(simple_svg, target, config)
        assert target.exists()

        from PIL import Image

        with Image.open(target) as ico:
            assert set(ico.info["sizes"]) == {(16, 16), (32, 32), (64, 64)}

    def test_render_frames_returns_one_per_size(self, simple_svg: Path) -> None:
        config = IcoConfig(sizes=(SizeSpec(16, 16), SizeSpec(32, 32)))
        frames = render_frames(simple_svg, config)
        assert len(frames) == 2
        assert frames[0].size == (16, 16)
        assert frames[1].size == (32, 32)

    def test_each_size_rasterized_independently(self, simple_svg: Path) -> None:
        """The per-size advantage of SVG: each render is fresh, not a downscale."""
        small = rasterize_svg(simple_svg, 16, 16)
        big = rasterize_svg(simple_svg, 128, 128)
        assert small.size == (16, 16)
        assert big.size == (128, 128)

        def _unique_pixels(img: object) -> int:
            from PIL.Image import Image as PILImage

            assert isinstance(img, PILImage)
            return len({img.getpixel((x, y)) for y in range(img.height) for x in range(img.width)})

        assert _unique_pixels(big) > _unique_pixels(small)

    def test_transparent_svg_preserves_alpha(self, transparent_svg: Path, tmp_path: Path) -> None:
        target = tmp_path / "out.ico"
        convert(transparent_svg, target, IcoConfig(sizes=(SizeSpec(32, 32),)))

        from PIL import Image

        with Image.open(target) as ico:
            ico.load()
            rgba = ico.convert("RGBA")
        raw = rgba.tobytes()
        # Top-left pixel (outside the circle): alpha at byte index 3.
        assert raw[3] == 0

    def test_color_background_composited(self, transparent_svg: Path, tmp_path: Path) -> None:
        target = tmp_path / "out.ico"
        config = IcoConfig(
            sizes=(SizeSpec(32, 32),),
            background=Color(255, 0, 0),
        )
        convert(transparent_svg, target, config)

        from PIL import Image

        with Image.open(target) as ico:
            ico.load()
            rgba = ico.convert("RGBA")
        raw = rgba.tobytes()
        # Top-left corner: red channel (byte 0) high, alpha (byte 3) fully opaque.
        assert raw[3] == 255
        assert raw[0] > 200
