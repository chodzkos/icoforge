"""Tests for cur_writer.write_cur."""

from __future__ import annotations

import struct
from pathlib import Path

import pytest
from PIL import Image

from icoforge.core.cur_writer import write_cur
from icoforge.core.models import SizeSpec


def _solid(size: int, color: tuple[int, int, int, int] = (0, 0, 0, 255)) -> Image.Image:
    return Image.new("RGBA", (size, size), color)


def _pair(
    size: int, color: tuple[int, int, int, int] = (0, 0, 0, 255)
) -> tuple[Image.Image, SizeSpec]:
    return _solid(size, color), SizeSpec(size, size)


def _read_header(data: bytes) -> tuple[int, int, int]:
    """Return (reserved, type, count) from ICONDIR."""
    return struct.unpack_from("<HHH", data, 0)


def _read_entry(data: bytes, index: int) -> tuple[int, int, int, int, int, int, int, int]:
    """Return all 8 fields of ICONDIRENTRY at *index*."""
    offset = 6 + index * 16
    return struct.unpack_from("<BBBBHHII", data, offset)


# ---------------------------------------------------------------------------
# Header bytes
# ---------------------------------------------------------------------------


class TestHeader:
    def test_reserved_is_zero(self, tmp_path: Path) -> None:
        data = _write([_pair(32)], tmp_path)
        reserved, _, _ = _read_header(data)
        assert reserved == 0

    def test_type_is_2(self, tmp_path: Path) -> None:
        """Byte offset 2-3 must be 0x02 0x00 (little-endian type=2)."""
        data = _write([_pair(32)], tmp_path)
        assert data[2:4] == b"\x02\x00"

    def test_type_field_is_2_not_1(self, tmp_path: Path) -> None:
        _, file_type, _ = _read_header(_write([_pair(16)], tmp_path))
        assert file_type == 2

    def test_count_matches_number_of_images(self, tmp_path: Path) -> None:
        for n in [1, 2, 3]:
            data = _write([_pair(s) for s in [16, 32, 48][:n]], tmp_path)
            _, _, count = _read_header(data)
            assert count == n


# ---------------------------------------------------------------------------
# Hotspot in directory entries
# ---------------------------------------------------------------------------


class TestHotspot:
    def test_default_hotspot_is_0_0(self, tmp_path: Path) -> None:
        data = _write([_pair(32)], tmp_path)
        _, _, _, _, hx, hy, _, _ = _read_entry(data, 0)
        assert hx == 0 and hy == 0

    def test_custom_hotspot_stored_in_entry(self, tmp_path: Path) -> None:
        out = tmp_path / "test.cur"
        write_cur(out, [_pair(32)], hotspot=(5, 10))
        data = out.read_bytes()
        _, _, _, _, hx, hy, _, _ = _read_entry(data, 0)
        assert hx == 5 and hy == 10

    def test_hotspot_scaled_per_frame(self, tmp_path: Path) -> None:
        """C11: the hotspot is relative to the largest frame and scaled down."""
        out = tmp_path / "test.cur"
        write_cur(out, [_pair(16), _pair(32)], hotspot=(30, 20))
        data = out.read_bytes()
        # Entries are largest-first: index 0 = 32px (reference), index 1 = 16px.
        _, _, _, _, hx0, hy0, _, _ = _read_entry(data, 0)
        assert (hx0, hy0) == (30, 20)
        _, _, _, _, hx1, hy1, _, _ = _read_entry(data, 1)
        # 30*16/32 = 15, 20*16/32 = 10
        assert (hx1, hy1) == (15, 10)

    def test_hotspot_outside_largest_frame_raises(self, tmp_path: Path) -> None:
        """C11: a hotspot beyond the largest frame is a validation error."""
        out = tmp_path / "test.cur"
        with pytest.raises(ValueError, match="outside the largest frame"):
            write_cur(out, [_pair(16), _pair(32)], hotspot=(40, 5))

    def test_zero_zero_hotspot(self, tmp_path: Path) -> None:
        out = tmp_path / "test.cur"
        write_cur(out, [_pair(32)], hotspot=(0, 0))
        data = out.read_bytes()
        _, _, _, _, hx, hy, _, _ = _read_entry(data, 0)
        assert hx == 0 and hy == 0


# ---------------------------------------------------------------------------
# Entry dimensions
# ---------------------------------------------------------------------------


class TestEntryDimensions:
    def test_32px_stored_as_32(self, tmp_path: Path) -> None:
        data = _write([_pair(32)], tmp_path)
        w, h, *_ = _read_entry(data, 0)
        assert w == 32 and h == 32

    def test_256px_stored_as_0(self, tmp_path: Path) -> None:
        data = _write([_pair(256)], tmp_path)
        w, h, *_ = _read_entry(data, 0)
        assert w == 0 and h == 0

    def test_entries_sorted_largest_first(self, tmp_path: Path) -> None:
        data = _write([_pair(16), _pair(32)], tmp_path)
        w0, *_ = _read_entry(data, 0)
        w1, *_ = _read_entry(data, 1)
        assert w0 == 32 and w1 == 16


# ---------------------------------------------------------------------------
# Image payload
# ---------------------------------------------------------------------------


class TestPayload:
    def test_image_data_is_valid_png(self, tmp_path: Path) -> None:
        import io as _io

        out = tmp_path / "test.cur"
        write_cur(out, [_pair(32)], hotspot=(0, 0))
        data = out.read_bytes()
        _, _, _, _, _, _, blob_size, img_offset = _read_entry(data, 0)
        png_bytes = data[img_offset : img_offset + blob_size]
        assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"
        img = Image.open(_io.BytesIO(png_bytes))
        assert img.size == (32, 32)

    def test_rgb_image_converted_to_rgba(self, tmp_path: Path) -> None:
        import io as _io

        out = tmp_path / "test.cur"
        rgb = Image.new("RGB", (16, 16), (255, 0, 0))
        write_cur(out, [(rgb, SizeSpec(16, 16))], hotspot=(0, 0))
        data = out.read_bytes()
        _, _, _, _, _, _, blob_size, img_offset = _read_entry(data, 0)
        img = Image.open(_io.BytesIO(data[img_offset : img_offset + blob_size]))
        assert img.mode == "RGBA"


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


class TestValidation:
    def test_empty_list_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="no images"):
            write_cur(tmp_path / "x.cur", [])

    def test_size_mismatch_raises(self, tmp_path: Path) -> None:
        img = Image.new("RGBA", (16, 16), (0, 0, 0, 255))
        wrong_spec = SizeSpec(32, 32)
        with pytest.raises(ValueError, match="does not match"):
            write_cur(tmp_path / "x.cur", [(img, wrong_spec)])


# ---------------------------------------------------------------------------
# IcoConfig.cursor_hotspot integration
# ---------------------------------------------------------------------------


class TestIcoConfigHotspot:
    def test_cursor_hotspot_default_is_none(self) -> None:
        from icoforge.core.models import IcoConfig, SizeSpec

        cfg = IcoConfig(sizes=(SizeSpec(32, 32),))
        assert cfg.cursor_hotspot is None

    def test_cursor_hotspot_stored(self) -> None:
        from icoforge.core.models import IcoConfig, SizeSpec

        cfg = IcoConfig(sizes=(SizeSpec(32, 32),), cursor_hotspot=(5, 10))
        assert cfg.cursor_hotspot == (5, 10)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(pairs: list[tuple[Image.Image, SizeSpec]], tmp_path: Path) -> bytes:
    out = tmp_path / "test.cur"
    write_cur(out, pairs)
    return out.read_bytes()
