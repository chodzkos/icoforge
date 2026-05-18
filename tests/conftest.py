"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


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
