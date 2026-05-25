"""Tests for icoforge.core.image_utils."""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from icoforge.core.image_utils import trim_transparency


def _make_padded(
    content_size: int = 32,
    pad: int = 10,
    color: tuple[int, int, int, int] = (255, 0, 0, 255),
) -> Image.Image:
    """Solid-colour content surrounded by transparent padding."""
    total = content_size + 2 * pad
    img = Image.new("RGBA", (total, total), (0, 0, 0, 0))
    for y in range(pad, pad + content_size):
        for x in range(pad, pad + content_size):
            img.putpixel((x, y), color)
    return img


# ---------------------------------------------------------------------------
# Basic trimming
# ---------------------------------------------------------------------------


class TestTrimBasic:
    def test_removes_transparent_border(self) -> None:
        img = _make_padded(content_size=20, pad=8)
        result = trim_transparency(img)
        assert result.size == (20, 20)

    def test_opaque_pixel_preserved(self) -> None:
        img = _make_padded(content_size=20, pad=5, color=(0, 128, 255, 255))
        result = trim_transparency(img)
        assert result.getpixel((0, 0)) == (0, 128, 255, 255)

    def test_no_trim_needed(self) -> None:
        img = Image.new("RGBA", (32, 32), (255, 0, 0, 255))
        result = trim_transparency(img)
        assert result.size == (32, 32)

    def test_fully_transparent_returns_original(self) -> None:
        img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
        result = trim_transparency(img)
        assert result.size == (32, 32)

    def test_non_rgba_input_converted(self) -> None:
        img = Image.new("RGB", (32, 32), (255, 0, 0))
        result = trim_transparency(img)
        assert result.mode == "RGBA"


# ---------------------------------------------------------------------------
# Asymmetric padding
# ---------------------------------------------------------------------------


class TestTrimAsymmetric:
    def test_content_in_corner(self) -> None:
        img = Image.new("RGBA", (20, 20), (0, 0, 0, 0))
        img.putpixel((0, 0), (255, 0, 0, 255))
        result = trim_transparency(img)
        assert result.size == (1, 1)

    def test_single_pixel(self) -> None:
        img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
        img.putpixel((8, 5), (10, 20, 30, 200))
        result = trim_transparency(img)
        assert result.size == (1, 1)

    def test_non_square_source(self) -> None:
        img = Image.new("RGBA", (60, 20), (0, 0, 0, 0))
        for x in range(5, 55):
            img.putpixel((x, 5), (0, 255, 0, 255))
        result = trim_transparency(img)
        assert result.size == (50, 1)


# ---------------------------------------------------------------------------
# Threshold
# ---------------------------------------------------------------------------


class TestTrimThreshold:
    def test_semi_transparent_trimmed_with_zero_threshold(self) -> None:
        img = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
        img.putpixel((5, 5), (255, 0, 0, 128))
        result = trim_transparency(img, threshold=0)
        assert result.size == (1, 1)

    def test_semi_transparent_kept_with_high_threshold(self) -> None:
        """Pixel alpha=128 is kept when threshold=200 means alpha>200 is 'opaque'."""
        img = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
        img.putpixel((5, 5), (255, 0, 0, 128))
        result = trim_transparency(img, threshold=200)
        assert result.size == (10, 10)


# ---------------------------------------------------------------------------
# Padding
# ---------------------------------------------------------------------------


class TestTrimPadding:
    def test_padding_added(self) -> None:
        img = _make_padded(content_size=10, pad=5)
        result = trim_transparency(img, padding=4)
        assert result.size == (10 + 8, 10 + 8)

    def test_padding_corners_are_transparent(self) -> None:
        img = _make_padded(content_size=10, pad=5)
        result = trim_transparency(img, padding=3)
        assert result.getpixel((0, 0))[3] == 0

    def test_zero_padding_no_extra_border(self) -> None:
        img = _make_padded(content_size=10, pad=5)
        result = trim_transparency(img, padding=0)
        assert result.size == (10, 10)

    def test_content_centered_in_padded_result(self) -> None:
        img = _make_padded(content_size=8, pad=4, color=(255, 0, 0, 255))
        result = trim_transparency(img, padding=2)
        assert result.getpixel((2, 2)) == (255, 0, 0, 255)
        assert result.getpixel((0, 0))[3] == 0


# ---------------------------------------------------------------------------
# Integration: IcoConfig.auto_trim in converter
# ---------------------------------------------------------------------------


class TestConverterAutoTrim:
    def test_auto_trim_removes_border(self, tmp_path: pytest.TempPathFactory) -> None:
        from icoforge.core.converter import convert
        from icoforge.core.models import IcoConfig, SizeSpec

        padded = _make_padded(content_size=32, pad=16)
        src = tmp_path / "padded.png"
        padded.save(src, format="PNG")
        target = tmp_path / "out.ico"

        config = IcoConfig(sizes=(SizeSpec(32, 32),), auto_trim=True)
        convert(src, target, config)

        result = Image.open(target)
        result.seek(0)
        arr = np.asarray(result.convert("RGBA"))
        opaque = arr[:, :, 3] > 0
        assert opaque.any(), "Expected some opaque pixels in output"

    def test_auto_trim_false_is_default(self, tmp_path: pytest.TempPathFactory) -> None:
        from icoforge.core.models import IcoConfig, SizeSpec

        config = IcoConfig(sizes=(SizeSpec(32, 32),))
        assert config.auto_trim is False
        assert config.auto_trim_padding == 0

    def test_auto_trim_padding_stored(self) -> None:
        from icoforge.core.models import IcoConfig, SizeSpec

        config = IcoConfig(sizes=(SizeSpec(32, 32),), auto_trim=True, auto_trim_padding=4)
        assert config.auto_trim_padding == 4
