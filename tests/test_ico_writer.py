"""Tests for ICO file writing."""

from __future__ import annotations

import io as _io
import struct as _struct
from pathlib import Path

import pytest
from PIL import Image

from icoforge.core.ico_writer import write_ico
from icoforge.core.models import SizeSpec

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _rgba_image(
    width: int, height: int, color: tuple[int, int, int, int] = (255, 0, 0, 255)
) -> Image.Image:
    return Image.new("RGBA", (width, height), color)


def _make_pairs(*sizes: int) -> list[tuple[Image.Image, SizeSpec]]:
    return [(_rgba_image(s, s), SizeSpec(s, s)) for s in sizes]


def _ico_sizes(path: Path) -> set[tuple[int, int]]:
    """Return the set of (width, height) tuples present in an ICO file."""
    with Image.open(path) as ico:
        return set(ico.info["sizes"])


# ---------------------------------------------------------------------------
# Basic behaviour
# ---------------------------------------------------------------------------


def test_write_ico_creates_file(tmp_path: Path) -> None:
    out = tmp_path / "out.ico"
    write_ico(out, _make_pairs(32))
    assert out.exists()


def test_write_ico_single_size(tmp_path: Path) -> None:
    out = tmp_path / "out.ico"
    write_ico(out, _make_pairs(32))
    assert _ico_sizes(out) == {(32, 32)}


def test_write_ico_multiple_sizes(tmp_path: Path) -> None:
    out = tmp_path / "out.ico"
    write_ico(out, _make_pairs(16, 32, 48))
    assert _ico_sizes(out) == {(16, 16), (32, 32), (48, 48)}


def test_write_ico_standard_windows_sizes(tmp_path: Path) -> None:
    out = tmp_path / "out.ico"
    sizes = (16, 32, 48, 256)
    write_ico(out, _make_pairs(*sizes))
    assert _ico_sizes(out) == {(s, s) for s in sizes}


def test_write_ico_entry_count_matches(tmp_path: Path) -> None:
    out = tmp_path / "out.ico"
    write_ico(out, _make_pairs(16, 32, 48))
    with Image.open(out) as ico:
        assert len(ico.info["sizes"]) == 3


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


def test_write_ico_rejects_empty_list(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no images"):
        write_ico(tmp_path / "out.ico", [])


def test_write_ico_rejects_mismatched_size(tmp_path: Path) -> None:
    img = _rgba_image(64, 64)
    spec = SizeSpec(32, 32)
    with pytest.raises(ValueError, match="SizeSpec"):
        write_ico(tmp_path / "out.ico", [(img, spec)])


def test_write_ico_mismatch_message_contains_dimensions(tmp_path: Path) -> None:
    img = _rgba_image(48, 48)
    spec = SizeSpec(16, 16)
    with pytest.raises(ValueError, match="48"):
        write_ico(tmp_path / "out.ico", [(img, spec)])


# ---------------------------------------------------------------------------
# Parent directory creation
# ---------------------------------------------------------------------------


def test_write_ico_creates_parent_directories(tmp_path: Path) -> None:
    out = tmp_path / "deep" / "nested" / "out.ico"
    write_ico(out, _make_pairs(32))
    assert out.exists()


# ---------------------------------------------------------------------------
# Alpha preservation
# ---------------------------------------------------------------------------


def test_write_ico_preserves_alpha_channel(tmp_path: Path) -> None:
    """Pixel data read back from the ICO must retain the original alpha."""
    out = tmp_path / "out.ico"
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    img.putpixel((0, 0), (255, 0, 0, 128))
    write_ico(out, [(img, SizeSpec(32, 32))])

    with Image.open(out) as ico:
        ico.load()
        loaded = ico.convert("RGBA")
    assert loaded.getpixel((0, 0)) == (255, 0, 0, 128)


def test_write_ico_fully_transparent_image(tmp_path: Path) -> None:
    out = tmp_path / "out.ico"
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    write_ico(out, [(img, SizeSpec(16, 16))])
    assert _ico_sizes(out) == {(16, 16)}


# ---------------------------------------------------------------------------
# 256x256 special case (stored as 0x0 in ICONDIRENTRY)
# ---------------------------------------------------------------------------


def test_write_ico_256_size(tmp_path: Path) -> None:
    out = tmp_path / "out.ico"
    write_ico(out, _make_pairs(256))
    assert (256, 256) in _ico_sizes(out)


def test_write_ico_mixed_with_256(tmp_path: Path) -> None:
    out = tmp_path / "out.ico"
    write_ico(out, _make_pairs(16, 32, 256))
    assert _ico_sizes(out) == {(16, 16), (32, 32), (256, 256)}


# ---------------------------------------------------------------------------
# Input order independence
# ---------------------------------------------------------------------------


def test_write_ico_input_order_does_not_affect_output_sizes(tmp_path: Path) -> None:
    """Regardless of input order, all requested sizes appear in the output."""
    out1 = tmp_path / "a.ico"
    out2 = tmp_path / "b.ico"
    pairs_asc = _make_pairs(16, 32, 48)
    pairs_desc = list(reversed(_make_pairs(16, 32, 48)))
    write_ico(out1, pairs_asc)
    write_ico(out2, pairs_desc)
    assert _ico_sizes(out1) == _ico_sizes(out2)


# ---------------------------------------------------------------------------
# Bit-depth encoding: ICONDIRENTRY.bitCount and embedded PNG mode
# ---------------------------------------------------------------------------


def _entry_bitcount(path: Path, entry_index: int = 0) -> int:
    """Read bitCount from ICONDIRENTRY[entry_index] in raw ICO bytes."""
    data = path.read_bytes()
    # ICONDIRENTRY at offset 6 + entry_index * 16
    # layout: width(B) height(B) colorCount(B) reserved(B) planes(H) bitCount(H) size(I) offset(I)
    _, _, _, _, _, bit_count, _, _ = _struct.unpack_from("<BBBBHHII", data, 6 + entry_index * 16)
    return bit_count


def _embedded_png_mode(path: Path, entry_index: int = 0) -> str:
    """Extract the PNG blob from ICONDIRENTRY[entry_index] and return its Pillow mode."""
    data = path.read_bytes()
    _, _, _, _, _, _, img_size, img_offset = _struct.unpack_from(
        "<BBBBHHII", data, 6 + entry_index * 16
    )
    return Image.open(_io.BytesIO(data[img_offset : img_offset + img_size])).mode


def test_bit_depth_32_header_and_png_mode(tmp_path: Path) -> None:
    """Default 32-bit: bitCount == 32 and embedded PNG is RGBA."""
    out = tmp_path / "out.ico"
    write_ico(out, [(_rgba_image(16, 16), SizeSpec(16, 16, bit_depth=32))])
    assert _entry_bitcount(out) == 32
    assert _embedded_png_mode(out) == "RGBA"


def test_bit_depth_24_header_and_png_mode(tmp_path: Path) -> None:
    """24-bit: bitCount == 24 and embedded PNG is RGB (no alpha channel)."""
    out = tmp_path / "out.ico"
    write_ico(out, [(_rgba_image(16, 16), SizeSpec(16, 16, bit_depth=24))])
    assert _entry_bitcount(out) == 24
    assert _embedded_png_mode(out) == "RGB"


def test_bit_depth_8_header_and_png_mode(tmp_path: Path) -> None:
    """8-bit: bitCount == 8 and embedded PNG is palette mode (P)."""
    out = tmp_path / "out.ico"
    write_ico(out, [(_rgba_image(16, 16), SizeSpec(16, 16, bit_depth=8))])
    assert _entry_bitcount(out) == 8
    assert _embedded_png_mode(out) == "P"


def test_bit_depth_8_round_trip_via_read_ico(tmp_path: Path) -> None:
    """Writing 8-bit and reading back via read_ico must return frame of correct size."""
    from icoforge.core.ico_reader import read_ico

    out = tmp_path / "out.ico"
    write_ico(out, [(_rgba_image(16, 16), SizeSpec(16, 16, bit_depth=8))])
    frames = read_ico(out)
    assert len(frames) == 1
    img, spec = frames[0]
    assert img.size == (16, 16)
    assert spec.width == 16
    assert spec.height == 16
