"""Resilience tests: malformed / corrupt inputs must fail cleanly.

Every case here must produce a clear, catchable exception (a domain ``ValueError``
or Pillow's ``UnidentifiedImageError``) — never a silent success, and at the CLI
boundary never a raw traceback.
"""

from __future__ import annotations

import struct
from pathlib import Path

import pytest
from click.testing import CliRunner
from PIL import Image, UnidentifiedImageError

from icoforge.cli import main
from icoforge.core.converter import convert
from icoforge.core.ico_reader import read_ico
from icoforge.core.models import IcoConfig, SizeSpec
from icoforge.core.optimizer import optimize_png

_CFG = IcoConfig(sizes=(SizeSpec(32, 32),))
# A malformed raster surfaces either as Pillow's UnidentifiedImageError or as a
# domain ValueError — both are clear, catchable errors (not a raw crash).
_IMG_ERRORS = (UnidentifiedImageError, ValueError)


def _write(path: Path, data: bytes) -> Path:
    path.write_bytes(data)
    return path


# ---------------------------------------------------------------------------
# Truncated raster headers
# ---------------------------------------------------------------------------


def test_truncated_png_raises(tmp_path: Path) -> None:
    src = _write(tmp_path / "t.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 8)
    with pytest.raises(_IMG_ERRORS):
        convert(src, tmp_path / "o.ico", _CFG)


def test_truncated_gif_raises(tmp_path: Path) -> None:
    src = _write(tmp_path / "t.gif", b"GIF89a" + b"\x00" * 4)
    with pytest.raises(_IMG_ERRORS):
        convert(src, tmp_path / "o.ico", _CFG)


def test_truncated_jpeg_raises(tmp_path: Path) -> None:
    src = _write(tmp_path / "t.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 6)
    with pytest.raises(_IMG_ERRORS):
        convert(src, tmp_path / "o.ico", _CFG)


def test_empty_file_raises(tmp_path: Path) -> None:
    src = _write(tmp_path / "empty.png", b"")
    with pytest.raises(_IMG_ERRORS):
        convert(src, tmp_path / "o.ico", _CFG)


# ---------------------------------------------------------------------------
# Wrong format for the extension
# ---------------------------------------------------------------------------


def test_jpeg_named_png_rejected_by_optimizer(tmp_path: Path) -> None:
    """A real JPEG carrying a .png name must not be silently optimized."""
    fake = tmp_path / "fake.png"
    Image.new("RGB", (16, 16), (1, 2, 3)).save(fake, format="JPEG")
    with pytest.raises(ValueError, match="Expected a PNG image"):
        optimize_png(fake)


# ---------------------------------------------------------------------------
# Malformed ICO
# ---------------------------------------------------------------------------


def test_ico_count_zero_raises(tmp_path: Path) -> None:
    src = _write(tmp_path / "c0.ico", struct.pack("<HHH", 0, 1, 0))
    with pytest.raises(ValueError, match="No frames"):
        read_ico(src)


def test_ico_too_small_raises(tmp_path: Path) -> None:
    src = _write(tmp_path / "tiny.ico", b"\x00\x00")
    with pytest.raises(ValueError, match="too small"):
        read_ico(src)


def test_ico_wrong_type_raises(tmp_path: Path) -> None:
    # type=2 is a cursor, not an icon.
    src = _write(tmp_path / "cur.ico", struct.pack("<HHH", 0, 2, 1))
    with pytest.raises(ValueError, match="Invalid ICO type"):
        read_ico(src)


def test_ico_entry_out_of_range_raises(tmp_path: Path) -> None:
    """An ICONDIRENTRY that declares a size/offset past EOF must not decode."""
    entry = struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32, 10_000_000, 6 + 16)
    data = struct.pack("<HHH", 0, 1, 1) + entry
    src = _write(tmp_path / "oob.ico", data)
    with pytest.raises(ValueError):
        read_ico(src)


def test_ico_frame_declares_huge_dimensions_raises(tmp_path: Path) -> None:
    """A PNG-compressed ICO entry declaring enormous dimensions is a decode bomb."""
    import zlib

    def _chunk(tag: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + tag
            + payload
            + struct.pack(">I", zlib.crc32(tag + payload))
        )

    ihdr = struct.pack(">IIBBBBB", 30000, 30000, 8, 6, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(b"\x00" * 16))
        + _chunk(b"IEND", b"")
    )
    entry = struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32, len(png), 6 + 16)
    src = _write(tmp_path / "bomb.ico", struct.pack("<HHH", 0, 1, 1) + entry + png)
    with pytest.raises(ValueError):
        read_ico(src)


# ---------------------------------------------------------------------------
# CLI boundary: clean non-zero exit + error message, never a raw traceback
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name,data",
    [
        ("t.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 8),
        ("empty.gif", b""),
        ("t.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 6),
    ],
)
def test_cli_convert_malformed_exits_cleanly(tmp_path: Path, name: str, data: bytes) -> None:
    src = _write(tmp_path / name, data)
    out = tmp_path / "out.ico"
    result = CliRunner().invoke(main, ["convert", str(src), str(out)])
    assert result.exit_code != 0
    assert not out.exists()
    assert "Error" in result.output
