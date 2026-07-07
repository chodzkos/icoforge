"""Per-format acceptance tests for the conversion pipeline.

Each test opens a real fixture file from tests/fixtures/ and converts it to
ICO, verifying that the output is structurally valid and that per-format
properties (alpha channel, opaqueness, size) are preserved correctly.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from icoforge.core.converter import convert, render_frames
from icoforge.core.models import TRANSPARENT, Color, IcoConfig, SizeSpec

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ico_sizes(path: Path) -> set[tuple[int, int]]:
    with Image.open(path) as ico:
        return set(ico.info["sizes"])


def _all_pixels_opaque(ico_path: Path, size: int) -> bool:
    with Image.open(ico_path) as ico:
        ico.load()
        rgba = ico.convert("RGBA")
    return all(b == 255 for b in rgba.tobytes()[3::4])


def _any_pixel_transparent(ico_path: Path) -> bool:
    with Image.open(ico_path) as ico:
        ico.load()
        rgba = ico.convert("RGBA")
    return any(b == 0 for b in rgba.tobytes()[3::4])


_SINGLE_32 = IcoConfig(sizes=(SizeSpec(32, 32),))
_MULTI = IcoConfig(sizes=(SizeSpec(16, 16), SizeSpec(32, 32), SizeSpec(48, 48)))


# ---------------------------------------------------------------------------
# JPEG
# ---------------------------------------------------------------------------


class TestJpeg:
    def test_produces_valid_ico(self, fixtures_dir: Path, tmp_path: Path) -> None:
        src = fixtures_dir / "photo.jpg"
        target = tmp_path / "out.ico"
        convert(src, target, _SINGLE_32)
        assert target.exists()
        assert _ico_sizes(target) == {(32, 32)}

    def test_multi_size(self, fixtures_dir: Path, tmp_path: Path) -> None:
        src = fixtures_dir / "photo.jpg"
        target = tmp_path / "out.ico"
        convert(src, target, _MULTI)
        assert _ico_sizes(target) == {(16, 16), (32, 32), (48, 48)}

    def test_output_is_fully_opaque(self, fixtures_dir: Path, tmp_path: Path) -> None:
        src = fixtures_dir / "photo.jpg"
        target = tmp_path / "out.ico"
        convert(src, target, _SINGLE_32)
        assert _all_pixels_opaque(target, 32)

    def test_transparent_background_still_opaque(self, fixtures_dir: Path, tmp_path: Path) -> None:
        """JPEG has no alpha; background=TRANSPARENT leaves pixels opaque."""
        src = fixtures_dir / "photo.jpg"
        target = tmp_path / "out.ico"
        config = IcoConfig(sizes=(SizeSpec(32, 32),), background=TRANSPARENT)
        convert(src, target, config)
        assert _all_pixels_opaque(target, 32)

    def test_color_background_accepted(self, fixtures_dir: Path, tmp_path: Path) -> None:
        src = fixtures_dir / "photo.jpg"
        target = tmp_path / "out.ico"
        config = IcoConfig(sizes=(SizeSpec(32, 32),), background=Color(255, 255, 255))
        convert(src, target, config)
        assert target.exists()
        assert _ico_sizes(target) == {(32, 32)}
        assert _all_pixels_opaque(target, 32)

    def test_render_frames(self, fixtures_dir: Path) -> None:
        src = fixtures_dir / "photo.jpg"
        frames = render_frames(src, _SINGLE_32)
        assert len(frames) == 1
        assert frames[0].size == (32, 32)
        assert frames[0].mode == "RGBA"


# ---------------------------------------------------------------------------
# BMP
# ---------------------------------------------------------------------------


class TestBmp:
    def test_produces_valid_ico(self, fixtures_dir: Path, tmp_path: Path) -> None:
        src = fixtures_dir / "photo.bmp"
        target = tmp_path / "out.ico"
        convert(src, target, _SINGLE_32)
        assert target.exists()
        assert _ico_sizes(target) == {(32, 32)}

    def test_multi_size(self, fixtures_dir: Path, tmp_path: Path) -> None:
        src = fixtures_dir / "photo.bmp"
        target = tmp_path / "out.ico"
        convert(src, target, _MULTI)
        assert _ico_sizes(target) == {(16, 16), (32, 32), (48, 48)}

    def test_output_is_fully_opaque(self, fixtures_dir: Path, tmp_path: Path) -> None:
        src = fixtures_dir / "photo.bmp"
        target = tmp_path / "out.ico"
        convert(src, target, _SINGLE_32)
        assert _all_pixels_opaque(target, 32)

    def test_transparent_background_still_opaque(self, fixtures_dir: Path, tmp_path: Path) -> None:
        src = fixtures_dir / "photo.bmp"
        target = tmp_path / "out.ico"
        config = IcoConfig(sizes=(SizeSpec(32, 32),), background=TRANSPARENT)
        convert(src, target, config)
        assert _all_pixels_opaque(target, 32)

    def test_color_background_accepted(self, fixtures_dir: Path, tmp_path: Path) -> None:
        src = fixtures_dir / "photo.bmp"
        target = tmp_path / "out.ico"
        config = IcoConfig(sizes=(SizeSpec(32, 32),), background=Color(0, 0, 0))
        convert(src, target, config)
        assert target.exists()
        assert _ico_sizes(target) == {(32, 32)}
        assert _all_pixels_opaque(target, 32)

    def test_render_frames(self, fixtures_dir: Path) -> None:
        src = fixtures_dir / "photo.bmp"
        frames = render_frames(src, _SINGLE_32)
        assert len(frames) == 1
        assert frames[0].mode == "RGBA"


# ---------------------------------------------------------------------------
# GIF
# ---------------------------------------------------------------------------


class TestGif:
    def test_produces_valid_ico(self, fixtures_dir: Path, tmp_path: Path) -> None:
        src = fixtures_dir / "photo.gif"
        target = tmp_path / "out.ico"
        convert(src, target, _SINGLE_32)
        assert target.exists()
        assert _ico_sizes(target) == {(32, 32)}

    def test_multi_size(self, fixtures_dir: Path, tmp_path: Path) -> None:
        src = fixtures_dir / "photo.gif"
        target = tmp_path / "out.ico"
        convert(src, target, _MULTI)
        assert _ico_sizes(target) == {(16, 16), (32, 32), (48, 48)}

    def test_palette_transparency_preserved(self, fixtures_dir: Path, tmp_path: Path) -> None:
        """GIF palette transparency index must survive conversion to ICO."""
        src = fixtures_dir / "photo.gif"
        target = tmp_path / "out.ico"
        convert(src, target, _SINGLE_32)
        assert _any_pixel_transparent(target)

    def test_render_frames_mode(self, fixtures_dir: Path) -> None:
        src = fixtures_dir / "photo.gif"
        frames = render_frames(src, _SINGLE_32)
        assert frames[0].mode == "RGBA"


# ---------------------------------------------------------------------------
# WEBP (opaque)
# ---------------------------------------------------------------------------


class TestWebpOpaque:
    def test_produces_valid_ico(self, fixtures_dir: Path, tmp_path: Path) -> None:
        src = fixtures_dir / "photo.webp"
        target = tmp_path / "out.ico"
        convert(src, target, _SINGLE_32)
        assert target.exists()
        assert _ico_sizes(target) == {(32, 32)}

    def test_multi_size(self, fixtures_dir: Path, tmp_path: Path) -> None:
        src = fixtures_dir / "photo.webp"
        target = tmp_path / "out.ico"
        convert(src, target, _MULTI)
        assert _ico_sizes(target) == {(16, 16), (32, 32), (48, 48)}

    def test_output_is_fully_opaque(self, fixtures_dir: Path, tmp_path: Path) -> None:
        src = fixtures_dir / "photo.webp"
        target = tmp_path / "out.ico"
        convert(src, target, _SINGLE_32)
        assert _all_pixels_opaque(target, 32)

    def test_color_background_accepted(self, fixtures_dir: Path, tmp_path: Path) -> None:
        src = fixtures_dir / "photo.webp"
        target = tmp_path / "out.ico"
        config = IcoConfig(sizes=(SizeSpec(32, 32),), background=Color(128, 128, 128))
        convert(src, target, config)
        assert target.exists()
        assert _ico_sizes(target) == {(32, 32)}
        assert _all_pixels_opaque(target, 32)

    def test_render_frames(self, fixtures_dir: Path) -> None:
        src = fixtures_dir / "photo.webp"
        frames = render_frames(src, _SINGLE_32)
        assert frames[0].mode == "RGBA"


# ---------------------------------------------------------------------------
# WEBP (with alpha)
# ---------------------------------------------------------------------------


class TestWebpAlpha:
    def test_produces_valid_ico(self, fixtures_dir: Path, tmp_path: Path) -> None:
        src = fixtures_dir / "alpha.webp"
        target = tmp_path / "out.ico"
        convert(src, target, _SINGLE_32)
        assert target.exists()
        assert _ico_sizes(target) == {(32, 32)}

    def test_alpha_preserved(self, fixtures_dir: Path, tmp_path: Path) -> None:
        src = fixtures_dir / "alpha.webp"
        target = tmp_path / "out.ico"
        convert(src, target, _SINGLE_32)
        assert _any_pixel_transparent(target)

    def test_render_frames_has_transparency(self, fixtures_dir: Path) -> None:
        src = fixtures_dir / "alpha.webp"
        frames = render_frames(src, _SINGLE_32)
        assert frames[0].mode == "RGBA"
        alpha_bytes = frames[0].tobytes()[3::4]
        assert any(a == 0 for a in alpha_bytes)


# ---------------------------------------------------------------------------
# TIFF
# ---------------------------------------------------------------------------


class TestTiff:
    def test_produces_valid_ico(self, fixtures_dir: Path, tmp_path: Path) -> None:
        src = fixtures_dir / "photo.tiff"
        target = tmp_path / "out.ico"
        convert(src, target, _SINGLE_32)
        assert target.exists()
        assert _ico_sizes(target) == {(32, 32)}

    def test_multi_size(self, fixtures_dir: Path, tmp_path: Path) -> None:
        src = fixtures_dir / "photo.tiff"
        target = tmp_path / "out.ico"
        convert(src, target, _MULTI)
        assert _ico_sizes(target) == {(16, 16), (32, 32), (48, 48)}

    def test_output_is_fully_opaque(self, fixtures_dir: Path, tmp_path: Path) -> None:
        src = fixtures_dir / "photo.tiff"
        target = tmp_path / "out.ico"
        convert(src, target, _SINGLE_32)
        assert _all_pixels_opaque(target, 32)

    def test_transparent_background_still_opaque(self, fixtures_dir: Path, tmp_path: Path) -> None:
        src = fixtures_dir / "photo.tiff"
        target = tmp_path / "out.ico"
        config = IcoConfig(sizes=(SizeSpec(32, 32),), background=TRANSPARENT)
        convert(src, target, config)
        assert _all_pixels_opaque(target, 32)

    def test_color_background_accepted(self, fixtures_dir: Path, tmp_path: Path) -> None:
        src = fixtures_dir / "photo.tiff"
        target = tmp_path / "out.ico"
        config = IcoConfig(sizes=(SizeSpec(32, 32),), background=Color(255, 0, 0))
        convert(src, target, config)
        assert target.exists()
        assert _ico_sizes(target) == {(32, 32)}
        assert _all_pixels_opaque(target, 32)

    def test_render_frames(self, fixtures_dir: Path) -> None:
        src = fixtures_dir / "photo.tiff"
        frames = render_frames(src, _SINGLE_32)
        assert frames[0].mode == "RGBA"

    def test_tif_extension_also_accepted(self, tmp_path: Path) -> None:
        img = Image.new("RGB", (32, 32), (80, 160, 40))
        src = tmp_path / "photo.tif"
        img.save(src)
        target = tmp_path / "out.ico"
        convert(src, target, _SINGLE_32)
        assert target.exists()
        assert _ico_sizes(target) == {(32, 32)}
