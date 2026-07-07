"""Tests for resource limits guarding against untrusted / hostile input files.

Covers the decompression-bomb pixel cap and the on-disk file-size checks wired
into the ICO reader, converter, SVG loader, optimizer and EXE extractor.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

import pytest
from PIL import Image

from icoforge.core import limits
from icoforge.core.converter import convert
from icoforge.core.ico_reader import read_ico
from icoforge.core.models import IcoConfig, SizeSpec
from icoforge.core.optimizer import optimize_png


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))


def _make_bomb_png(path: Path, width: int, height: int) -> Path:
    """Write a tiny PNG whose IHDR *declares* huge dimensions (a decode bomb)."""
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)  # 8-bit RGBA
    idat = _png_chunk(b"IDAT", zlib.compress(b"\x00" * 16))
    path.write_bytes(sig + _png_chunk(b"IHDR", ihdr) + idat + _png_chunk(b"IEND", b""))
    return path


def _make_real_png(path: Path, size: tuple[int, int] = (32, 32)) -> Path:
    Image.new("RGBA", size, (0, 128, 255, 255)).save(path)
    return path


# ---------------------------------------------------------------------------
# Global pixel cap
# ---------------------------------------------------------------------------


def test_max_image_pixels_installed() -> None:
    """Importing the core package must install the decompression-bomb cap."""
    assert Image.MAX_IMAGE_PIXELS == limits.MAX_IMAGE_PIXELS
    assert limits.MAX_IMAGE_PIXELS == 64_000_000


# ---------------------------------------------------------------------------
# check_file_size
# ---------------------------------------------------------------------------


def test_check_file_size_ok(tmp_path: Path) -> None:
    p = tmp_path / "small.bin"
    p.write_bytes(b"x" * 100)
    limits.check_file_size(p, max_bytes=1000)  # must not raise


def test_check_file_size_rejects_oversized(tmp_path: Path) -> None:
    p = tmp_path / "big.bin"
    p.write_bytes(b"x" * 100)
    with pytest.raises(ValueError, match="too large"):
        limits.check_file_size(p, max_bytes=99)


# ---------------------------------------------------------------------------
# guard_decompression_bomb
# ---------------------------------------------------------------------------


def test_guard_converts_bomb_to_value_error(tmp_path: Path) -> None:
    bomb = _make_bomb_png(tmp_path / "bomb.png", 30000, 30000)
    with pytest.raises(ValueError, match="safe decode limit"), limits.guard_decompression_bomb():
        Image.open(bomb).convert("RGBA")


# ---------------------------------------------------------------------------
# Decode paths reject a decompression bomb with a clean ValueError
# ---------------------------------------------------------------------------


def test_convert_rejects_bomb_source(tmp_path: Path) -> None:
    bomb = _make_bomb_png(tmp_path / "bomb.png", 30000, 30000)
    out = tmp_path / "out.ico"
    with pytest.raises(ValueError, match="safe decode limit"):
        convert(bomb, out, IcoConfig(sizes=(SizeSpec(32, 32),)))
    assert not out.exists()


# ---------------------------------------------------------------------------
# Decode paths reject oversized files (limits monkeypatched small)
# ---------------------------------------------------------------------------


def test_convert_rejects_oversized_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    src = _make_real_png(tmp_path / "in.png")
    monkeypatch.setattr(limits, "MAX_IMAGE_BYTES", 10)
    out = tmp_path / "out.ico"
    with pytest.raises(ValueError, match="too large"):
        convert(src, out, IcoConfig(sizes=(SizeSpec(16, 16),)))


def test_read_ico_rejects_oversized(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Produce a genuine ICO first, then shrink the limit below its size.
    src = _make_real_png(tmp_path / "in.png")
    ico = tmp_path / "icon.ico"
    convert(src, ico, IcoConfig(sizes=(SizeSpec(16, 16), SizeSpec(32, 32))))
    monkeypatch.setattr(limits, "MAX_ICO_BYTES", 10)
    with pytest.raises(ValueError, match="too large"):
        read_ico(ico)


def test_optimize_png_rejects_oversized(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    src = _make_real_png(tmp_path / "in.png")
    monkeypatch.setattr(limits, "MAX_PNG_BYTES", 10)
    with pytest.raises(ValueError, match="too large"):
        optimize_png(src)


def test_extract_icons_rejects_oversized(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # The size check runs before the optional pefile import, so this holds even
    # when pefile is not installed.
    from icoforge.core.exe_extractor import extract_icons_from_exe

    fake = tmp_path / "big.exe"
    fake.write_bytes(b"MZ" + b"\x00" * 200)
    monkeypatch.setattr(limits, "MAX_PE_BYTES", 10)
    with pytest.raises(ValueError, match="too large"):
        extract_icons_from_exe(fake)
