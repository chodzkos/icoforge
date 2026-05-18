"""Tests for the PNG -> ICO conversion pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from icoforge.core import IcoConfig, ResampleAlgorithm, SizeSpec
from icoforge.core.converter import convert


def test_convert_produces_ico_with_requested_sizes(tmp_png: Path, tmp_path: Path) -> None:
    target = tmp_path / "out.ico"
    config = IcoConfig(
        sizes=(SizeSpec(16, 16), SizeSpec(32, 32), SizeSpec(256, 256)),
        resample=ResampleAlgorithm.LANCZOS,
    )

    convert(tmp_png, target, config)

    assert target.exists()
    with Image.open(target) as ico:
        # Pillow exposes ICO sizes via `ico.ico.sizes()`. The container itself
        # decodes the first/largest entry as the main image.
        sizes = ico.ico.sizes()  # type: ignore[attr-defined]
        assert (16, 16) in sizes
        assert (32, 32) in sizes
        assert (256, 256) in sizes


def test_convert_preserves_alpha(tmp_png: Path, tmp_path: Path) -> None:
    target = tmp_path / "out.ico"
    config = IcoConfig(sizes=(SizeSpec(64, 64),))

    convert(tmp_png, target, config)

    with Image.open(target) as ico:
        ico.size = (64, 64)  # type: ignore[misc]  # ICO sub-image selection
        ico.load()
        rgba = ico.convert("RGBA")
    # Top-right corner of source was transparent; we expect at least one fully
    # transparent pixel after downscaling.
    pixels = list(rgba.getdata())
    assert any(p[3] == 0 for p in pixels), "Expected transparency to survive conversion"


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
