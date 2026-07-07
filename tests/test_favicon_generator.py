"""Tests for favicon_generator.generate_favicon_set."""

from __future__ import annotations

import json
import struct
from pathlib import Path

import pytest
from PIL import Image

from icoforge.core.favicon_generator import generate_favicon_set


def _solid(size: int = 64, color: tuple[int, int, int, int] = (0, 128, 255, 255)) -> Image.Image:
    return Image.new("RGBA", (size, size), color)


@pytest.fixture()
def source_png(tmp_path: Path) -> Path:
    path = tmp_path / "source.png"
    _solid().save(path, format="PNG")
    return path


@pytest.fixture()
def source_rect_png(tmp_path: Path) -> Path:
    """Non-square source for letterboxing tests."""
    img = Image.new("RGBA", (200, 100), (255, 0, 0, 255))
    path = tmp_path / "wide.png"
    img.save(path, format="PNG")
    return path


# ---------------------------------------------------------------------------
# Output files existence
# ---------------------------------------------------------------------------


class TestOutputFiles:
    def test_all_five_files_created(self, source_png: Path, tmp_path: Path) -> None:
        out = tmp_path / "favicon_out"
        result = generate_favicon_set(source_png, out)
        names = {p.name for p in result}
        assert names == {
            "favicon.ico",
            "apple-touch-icon.png",
            "icon-192.png",
            "icon-512.png",
            "site.webmanifest",
        }

    def test_returns_five_paths(self, source_png: Path, tmp_path: Path) -> None:
        result = generate_favicon_set(source_png, tmp_path / "out")
        assert len(result) == 5

    def test_output_dir_created_automatically(self, source_png: Path, tmp_path: Path) -> None:
        out = tmp_path / "nested" / "deep" / "out"
        assert not out.exists()
        generate_favicon_set(source_png, out)
        assert out.is_dir()

    def test_all_files_on_disk(self, source_png: Path, tmp_path: Path) -> None:
        out = tmp_path / "out"
        result = generate_favicon_set(source_png, out)
        for path in result:
            assert path.exists(), f"{path.name} was not created"


# ---------------------------------------------------------------------------
# favicon.ico
# ---------------------------------------------------------------------------


class TestFaviconIco:
    def test_is_valid_ico(self, source_png: Path, tmp_path: Path) -> None:
        out = tmp_path / "out"
        generate_favicon_set(source_png, out)
        ico = out / "favicon.ico"
        data = ico.read_bytes()
        # ICO header: reserved=0, type=1, count>=1
        reserved, file_type, count = struct.unpack_from("<HHH", data, 0)
        assert reserved == 0
        assert file_type == 1
        assert count >= 1

    def test_has_three_sizes(self, source_png: Path, tmp_path: Path) -> None:
        out = tmp_path / "out"
        generate_favicon_set(source_png, out)
        ico = out / "favicon.ico"
        data = ico.read_bytes()
        _, _, count = struct.unpack_from("<HHH", data, 0)
        assert count == 3

    def test_contains_16_32_48(self, source_png: Path, tmp_path: Path) -> None:
        out = tmp_path / "out"
        generate_favicon_set(source_png, out)
        data = (out / "favicon.ico").read_bytes()
        sizes = set()
        _, _, count = struct.unpack_from("<HHH", data, 0)
        for i in range(count):
            w, _h = struct.unpack_from("<BB", data, 6 + i * 16)
            sizes.add(w if w != 0 else 256)
        assert sizes == {16, 32, 48}


# ---------------------------------------------------------------------------
# apple-touch-icon.png
# ---------------------------------------------------------------------------


class TestAppleTouchIcon:
    def test_is_180x180(self, source_png: Path, tmp_path: Path) -> None:
        out = tmp_path / "out"
        generate_favicon_set(source_png, out)
        img = Image.open(out / "apple-touch-icon.png")
        assert img.size == (180, 180)

    def test_no_transparency(self, source_png: Path, tmp_path: Path) -> None:
        """apple-touch-icon must have no alpha channel (saved as RGB)."""
        out = tmp_path / "out"
        generate_favicon_set(source_png, out)
        img = Image.open(out / "apple-touch-icon.png")
        assert img.mode == "RGB"

    def test_transparent_source_gets_white_background(self, tmp_path: Path) -> None:
        """A fully-transparent source should produce a white icon."""
        transparent = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        src = tmp_path / "transparent.png"
        transparent.save(src, format="PNG")
        out = tmp_path / "out"
        generate_favicon_set(src, out)
        img = Image.open(out / "apple-touch-icon.png").convert("RGB")
        # All pixels should be white (255, 255, 255)
        pixels = list(img.getdata())
        assert all(px == (255, 255, 255) for px in pixels)


# ---------------------------------------------------------------------------
# PWA icons
# ---------------------------------------------------------------------------


class TestPwaIcons:
    def test_icon_192_size(self, source_png: Path, tmp_path: Path) -> None:
        out = tmp_path / "out"
        generate_favicon_set(source_png, out)
        img = Image.open(out / "icon-192.png")
        assert img.size == (192, 192)

    def test_icon_512_size(self, source_png: Path, tmp_path: Path) -> None:
        out = tmp_path / "out"
        generate_favicon_set(source_png, out)
        img = Image.open(out / "icon-512.png")
        assert img.size == (512, 512)

    def test_icon_192_is_rgba(self, source_png: Path, tmp_path: Path) -> None:
        out = tmp_path / "out"
        generate_favicon_set(source_png, out)
        img = Image.open(out / "icon-192.png")
        assert img.mode == "RGBA"

    def test_icon_512_is_rgba(self, source_png: Path, tmp_path: Path) -> None:
        out = tmp_path / "out"
        generate_favicon_set(source_png, out)
        img = Image.open(out / "icon-512.png")
        assert img.mode == "RGBA"

    def test_letterbox_preserves_aspect(self, source_rect_png: Path, tmp_path: Path) -> None:
        """Wide source (200x100) should be letterboxed, not stretched."""
        out = tmp_path / "out"
        generate_favicon_set(source_rect_png, out)
        img = Image.open(out / "icon-192.png")
        assert img.size == (192, 192)
        # Top/bottom rows should be transparent (letterbox padding)
        top_row = [img.getpixel((x, 0)) for x in range(192)]
        assert all(px[3] == 0 for px in top_row), "Expected transparent letterbox at top"


# ---------------------------------------------------------------------------
# site.webmanifest
# ---------------------------------------------------------------------------


class TestWebmanifest:
    def test_is_valid_json(self, source_png: Path, tmp_path: Path) -> None:
        out = tmp_path / "out"
        generate_favicon_set(source_png, out)
        text = (out / "site.webmanifest").read_text(encoding="utf-8")
        data = json.loads(text)
        assert isinstance(data, dict)

    def test_has_icons_array(self, source_png: Path, tmp_path: Path) -> None:
        out = tmp_path / "out"
        generate_favicon_set(source_png, out)
        data = json.loads((out / "site.webmanifest").read_text(encoding="utf-8"))
        assert "icons" in data
        assert isinstance(data["icons"], list)
        assert len(data["icons"]) >= 1

    def test_icons_reference_pwa_files(self, source_png: Path, tmp_path: Path) -> None:
        out = tmp_path / "out"
        generate_favicon_set(source_png, out)
        data = json.loads((out / "site.webmanifest").read_text(encoding="utf-8"))
        srcs = {icon["src"] for icon in data["icons"]}
        assert "icon-192.png" in srcs
        assert "icon-512.png" in srcs

    def test_has_display_field(self, source_png: Path, tmp_path: Path) -> None:
        out = tmp_path / "out"
        generate_favicon_set(source_png, out)
        data = json.loads((out / "site.webmanifest").read_text(encoding="utf-8"))
        assert "display" in data


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


class TestValidation:
    def test_missing_source_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            generate_favicon_set(tmp_path / "nonexistent.png", tmp_path / "out")

    def test_unsupported_format_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "file.xyz"
        bad.write_bytes(b"\x00\x01\x02")
        with pytest.raises(ValueError, match="Unsupported source format"):
            generate_favicon_set(bad, tmp_path / "out")


# ---------------------------------------------------------------------------
# Progress callback
# ---------------------------------------------------------------------------


class TestProgress:
    def test_progress_called_monotonically(self, source_png: Path, tmp_path: Path) -> None:
        values: list[float] = []
        generate_favicon_set(source_png, tmp_path / "out", progress=values.append)
        assert values, "progress was never called"
        assert values[0] == 0.0
        assert values[-1] == 1.0
        assert values == sorted(values), "progress values must be non-decreasing"

    def test_no_progress_doesnt_crash(self, source_png: Path, tmp_path: Path) -> None:
        generate_favicon_set(source_png, tmp_path / "out", progress=None)


def test_favicon_ico_honors_resample(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """C8: the resample argument must reach the favicon.ico IcoConfig."""
    from icoforge.core import converter, favicon_generator
    from icoforge.core.models import IcoConfig, ResampleAlgorithm

    captured: dict[str, object] = {}

    def _spy_convert(src: Path, tgt: Path, config: object, progress: object = None) -> None:
        captured["config"] = config

    monkeypatch.setattr(converter, "convert", _spy_convert)

    src = tmp_path / "in.png"
    _solid().save(src, format="PNG")
    favicon_generator.generate_favicon_set(src, tmp_path / "out", resample=Image.Resampling.NEAREST)

    config = captured["config"]
    assert isinstance(config, IcoConfig)
    assert config.resample == ResampleAlgorithm.NEAREST


def test_svg_source_rasterized_at_natural_aspect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C9: SVG must be rasterized at its natural aspect, not forced to 512x512."""
    from icoforge.core import favicon_generator, svg_loader

    fake_svg = tmp_path / "logo.svg"
    fake_svg.write_text("<svg/>", encoding="utf-8")
    natural = Image.new("RGBA", (100, 50), (0, 0, 255, 255))  # 2:1
    monkeypatch.setattr(svg_loader, "rasterize_svg_natural", lambda src: natural.copy())

    img = favicon_generator._load_rgba(fake_svg)
    assert img.size == (100, 50)
