"""Tests for the PNG -> ICO conversion pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from icoforge.core import IcoConfig, ResampleAlgorithm, SizeSpec
from icoforge.core.converter import convert, render_frames
from icoforge.core.models import Color

# ---------------------------------------------------------------------------
# Helpers / extra fixtures
# ---------------------------------------------------------------------------


def _ico_sizes(path: Path) -> set[tuple[int, int]]:
    with Image.open(path) as ico:
        return set(ico.info["sizes"])


def _make_jpeg(tmp_path: Path, size: tuple[int, int] = (200, 200)) -> Path:
    """Create an opaque RGB JPEG (no alpha channel)."""
    img = Image.new("RGB", size, (180, 90, 30))
    out = tmp_path / "input.jpg"
    img.save(out, format="JPEG")
    return out


def _make_wide_png(tmp_path: Path) -> Path:
    """Create a wide (2:1) RGBA PNG to test letterboxing."""
    img = Image.new("RGBA", (256, 128), (255, 0, 0, 255))
    out = tmp_path / "wide.png"
    img.save(out)
    return out


# ---------------------------------------------------------------------------
# Basic pipeline — sizes
# ---------------------------------------------------------------------------


def test_convert_produces_ico_with_requested_sizes(tmp_png: Path, tmp_path: Path) -> None:
    target = tmp_path / "out.ico"
    config = IcoConfig(
        sizes=(SizeSpec(16, 16), SizeSpec(32, 32), SizeSpec(256, 256)),
        resample=ResampleAlgorithm.LANCZOS,
    )

    convert(tmp_png, target, config)

    assert target.exists()
    assert _ico_sizes(target) == {(16, 16), (32, 32), (256, 256)}


def test_convert_creates_parent_directories(tmp_png: Path, tmp_path: Path) -> None:
    target = tmp_path / "deep" / "nested" / "out.ico"
    convert(tmp_png, target, IcoConfig(sizes=(SizeSpec(32, 32),)))
    assert target.exists()


# ---------------------------------------------------------------------------
# Alpha channel (PNG with transparency)
# ---------------------------------------------------------------------------


def test_convert_preserves_alpha(tmp_png: Path, tmp_path: Path) -> None:
    target = tmp_path / "out.ico"
    config = IcoConfig(sizes=(SizeSpec(64, 64),))

    convert(tmp_png, target, config)

    with Image.open(target) as ico:
        ico.size = (64, 64)  # type: ignore[misc]
        ico.load()
        rgba = ico.convert("RGBA")
    alpha = rgba.tobytes()[3::4]
    assert any(a == 0 for a in alpha), "Expected transparency to survive conversion"


def test_convert_rgba_source_has_alpha_in_output(tmp_png: Path, tmp_path: Path) -> None:
    target = tmp_path / "out.ico"
    convert(tmp_png, target, IcoConfig(sizes=(SizeSpec(32, 32),)))

    with Image.open(target) as ico:
        ico.load()
        assert ico.convert("RGBA").mode == "RGBA"


# ---------------------------------------------------------------------------
# No alpha — JPG source
# ---------------------------------------------------------------------------


def test_convert_jpg_without_alpha_produces_ico(tmp_path: Path) -> None:
    src = _make_jpeg(tmp_path)
    target = tmp_path / "out.ico"
    config = IcoConfig(sizes=(SizeSpec(32, 32),))

    convert(src, target, config)

    assert target.exists()
    assert _ico_sizes(target) == {(32, 32)}


def test_convert_jpg_pixels_are_fully_opaque(tmp_path: Path) -> None:
    """JPEG source has no alpha; all output pixels should be fully opaque."""
    src = _make_jpeg(tmp_path)
    target = tmp_path / "out.ico"
    convert(src, target, IcoConfig(sizes=(SizeSpec(32, 32),)))

    with Image.open(target) as ico:
        ico.load()
        rgba = ico.convert("RGBA")
    alpha = rgba.tobytes()[3::4]
    assert all(a == 255 for a in alpha), "JPEG output should be fully opaque"


def test_convert_jpg_with_background_color(tmp_path: Path) -> None:
    """Explicit background colour must be accepted without error for JPG input."""
    src = _make_jpeg(tmp_path)
    target = tmp_path / "out.ico"
    config = IcoConfig(
        sizes=(SizeSpec(32, 32),),
        background=Color(255, 255, 255),
    )
    convert(src, target, config)
    assert target.exists()


def test_convert_jpg_with_transparent_background(tmp_path: Path) -> None:
    src = _make_jpeg(tmp_path)
    target = tmp_path / "out.ico"
    config = IcoConfig(sizes=(SizeSpec(32, 32),), background="transparent")
    convert(src, target, config)
    assert target.exists()


def test_convert_multiple_sizes_from_jpg(tmp_path: Path) -> None:
    src = _make_jpeg(tmp_path)
    target = tmp_path / "out.ico"
    config = IcoConfig(sizes=(SizeSpec(16, 16), SizeSpec(32, 32), SizeSpec(48, 48)))
    convert(src, target, config)
    assert _ico_sizes(target) == {(16, 16), (32, 32), (48, 48)}


# ---------------------------------------------------------------------------
# Letterboxing (preserve_aspect=True, non-square source)
# ---------------------------------------------------------------------------


def test_convert_preserve_aspect_output_is_square(tmp_path: Path) -> None:
    """Wide image letterboxed to square must produce a square output frame."""
    src = _make_wide_png(tmp_path)
    target = tmp_path / "out.ico"
    config = IcoConfig(sizes=(SizeSpec(32, 32),), preserve_aspect=True)
    convert(src, target, config)
    assert _ico_sizes(target) == {(32, 32)}


def test_convert_preserve_aspect_adds_transparent_padding(tmp_path: Path) -> None:
    """Letterboxed output should have transparent rows on top/bottom."""
    src = _make_wide_png(tmp_path)  # 256x128, solid red
    target = tmp_path / "out.ico"
    config = IcoConfig(sizes=(SizeSpec(32, 32),), preserve_aspect=True, background="transparent")
    convert(src, target, config)

    with Image.open(target) as ico:
        ico.load()
        rgba = ico.convert("RGBA")

    top_row = [rgba.getpixel((x, 0)) for x in range(32)]  # type: ignore[call-overload]
    # Top row should be in the transparent padding area for a 2:1 wide image
    assert any(p[3] == 0 for p in top_row), "Letterbox padding should be transparent"


def test_convert_preserve_aspect_false_stretches(tmp_path: Path) -> None:
    """With preserve_aspect=False a non-square source is stretched to fill."""
    src = _make_wide_png(tmp_path)
    target = tmp_path / "out.ico"
    config = IcoConfig(sizes=(SizeSpec(32, 32),), preserve_aspect=False)
    convert(src, target, config)
    assert _ico_sizes(target) == {(32, 32)}


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_convert_rejects_missing_source(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        convert(
            tmp_path / "does-not-exist.png",
            tmp_path / "out.ico",
            IcoConfig(sizes=(SizeSpec(16, 16),)),
        )


def test_convert_rejects_unsupported_format(tmp_path: Path) -> None:
    bogus = tmp_path / "input.xyz"
    bogus.write_bytes(b"not an image")
    with pytest.raises(ValueError, match="Unsupported"):
        convert(bogus, tmp_path / "out.ico", IcoConfig(sizes=(SizeSpec(16, 16),)))


# ---------------------------------------------------------------------------
# Progress callback
# ---------------------------------------------------------------------------


def test_progress_callback_reaches_one(tmp_png: Path, tmp_path: Path) -> None:
    values: list[float] = []
    convert(
        tmp_png,
        tmp_path / "out.ico",
        IcoConfig(sizes=(SizeSpec(32, 32),)),
        progress=values.append,
    )
    assert values
    assert values[-1] == pytest.approx(1.0)
    assert all(0.0 <= v <= 1.0 for v in values)


def test_progress_callback_starts_at_zero(tmp_png: Path, tmp_path: Path) -> None:
    values: list[float] = []
    convert(
        tmp_png,
        tmp_path / "out.ico",
        IcoConfig(sizes=(SizeSpec(32, 32),)),
        progress=values.append,
    )
    assert values[0] == pytest.approx(0.0)


def test_progress_callback_is_monotonically_increasing(tmp_png: Path, tmp_path: Path) -> None:
    values: list[float] = []
    convert(
        tmp_png,
        tmp_path / "out.ico",
        IcoConfig(sizes=(SizeSpec(16, 16), SizeSpec(32, 32), SizeSpec(48, 48))),
        progress=values.append,
    )
    assert values == sorted(values)


def test_progress_callback_called_multiple_times_for_multiple_sizes(
    tmp_png: Path, tmp_path: Path
) -> None:
    values: list[float] = []
    convert(
        tmp_png,
        tmp_path / "out.ico",
        IcoConfig(sizes=(SizeSpec(16, 16), SizeSpec(32, 32), SizeSpec(48, 48))),
        progress=values.append,
    )
    # start + 3 sizes + finish = at least 5 calls
    assert len(values) >= 5


def test_convert_works_without_progress_callback(tmp_png: Path, tmp_path: Path) -> None:
    convert(tmp_png, tmp_path / "out.ico", IcoConfig(sizes=(SizeSpec(32, 32),)))


# ---------------------------------------------------------------------------
# render_frames
# ---------------------------------------------------------------------------


def test_render_frames_returns_one_frame_per_size(tmp_png: Path) -> None:
    config = IcoConfig(sizes=(SizeSpec(16, 16), SizeSpec(32, 32), SizeSpec(48, 48)))
    frames = render_frames(tmp_png, config)
    assert len(frames) == 3


def test_render_frames_sizes_match_spec(tmp_png: Path) -> None:
    config = IcoConfig(sizes=(SizeSpec(16, 16), SizeSpec(64, 64)))
    frames = render_frames(tmp_png, config)
    assert frames[0].size == (16, 16)
    assert frames[1].size == (64, 64)


def test_render_frames_all_rgba(tmp_png: Path) -> None:
    config = IcoConfig(sizes=(SizeSpec(32, 32),))
    frames = render_frames(tmp_png, config)
    assert all(f.mode == "RGBA" for f in frames)


def test_render_frames_rejects_missing_source(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        render_frames(tmp_path / "nope.png", IcoConfig(sizes=(SizeSpec(32, 32),)))


def test_render_frames_rejects_unsupported_format(tmp_path: Path) -> None:
    bogus = tmp_path / "input.xyz"
    bogus.write_bytes(b"not an image")
    with pytest.raises(ValueError, match="Unsupported"):
        render_frames(bogus, IcoConfig(sizes=(SizeSpec(32, 32),)))


def test_render_frames_progress_callback(tmp_png: Path) -> None:
    values: list[float] = []
    render_frames(
        tmp_png, IcoConfig(sizes=(SizeSpec(16, 16), SizeSpec(32, 32))), progress=values.append
    )
    assert values[0] == pytest.approx(0.0)
    assert values[-1] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Palette-mode PNG source
# ---------------------------------------------------------------------------


def _make_palette_png(tmp_path: Path) -> Path:
    img = Image.new("RGB", (64, 64), (0, 128, 255))
    palette_img = img.convert("P")
    out = tmp_path / "palette.png"
    palette_img.save(out)
    return out


def test_convert_palette_mode_source(tmp_path: Path) -> None:
    src = _make_palette_png(tmp_path)
    target = tmp_path / "out.ico"
    convert(src, target, IcoConfig(sizes=(SizeSpec(32, 32),)))
    assert target.exists()
    assert _ico_sizes(target) == {(32, 32)}
