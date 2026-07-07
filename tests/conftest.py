"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_png(tmp_path: Path) -> Path:
    """A small opaque RGBA PNG (64x64, solid blue)."""
    out = tmp_path / "sample.png"
    Image.new("RGBA", (64, 64), (0, 120, 255, 255)).save(out, format="PNG")
    return out


@pytest.fixture
def sample_jpg(tmp_path: Path) -> Path:
    """A small opaque RGB JPEG (64x64)."""
    out = tmp_path / "sample.jpg"
    Image.new("RGB", (64, 64), (200, 100, 50)).save(out, format="JPEG")
    return out


@pytest.fixture
def sample_gif(tmp_path: Path) -> Path:
    """A small palette GIF (64x64)."""
    out = tmp_path / "sample.gif"
    Image.new("P", (64, 64), 5).save(out, format="GIF")
    return out


@pytest.fixture
def tmp_png(tmp_path: Path) -> Path:
    """Create a small RGBA PNG with a gradient and a transparent corner."""
    img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    pixels = img.load()
    assert pixels is not None
    for y in range(256):
        for x in range(256):
            # Skip top-right quarter to leave transparency
            if x > 128 and y < 128:
                continue
            pixels[x, y] = (x, y, (x + y) % 256, 255)
    out = tmp_path / "input.png"
    img.save(out)
    return out
