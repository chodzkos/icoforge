"""Tests for icns_writer.write_icns."""

from __future__ import annotations

import struct
from pathlib import Path

import pytest
from PIL import Image

from icoforge.core.icns_writer import _SIZE_TO_TAG, _VALID_SIZES, write_icns


def _solid(size: int, color: tuple[int, int, int, int] = (10, 20, 30, 255)) -> Image.Image:
    return Image.new("RGBA", (size, size), color)


def _parse_blocks(data: bytes) -> list[tuple[bytes, bytes]]:
    """Return list of (tag, payload) from the blocks section of an ICNS file."""
    blocks = []
    offset = 8  # skip file header
    while offset < len(data):
        tag = data[offset : offset + 4]
        (block_len,) = struct.unpack(">I", data[offset + 4 : offset + 8])
        payload = data[offset + 8 : offset + block_len]
        blocks.append((tag, payload))
        offset += block_len
    return blocks


# ---------------------------------------------------------------------------
# Binary structure
# ---------------------------------------------------------------------------


class TestBinaryHeader:
    def test_magic_bytes(self, tmp_path: Path) -> None:
        out = tmp_path / "test.icns"
        write_icns(out, [_solid(16)])
        assert out.read_bytes()[:4] == b"icns"

    def test_total_length_field_matches_file_size(self, tmp_path: Path) -> None:
        out = tmp_path / "test.icns"
        write_icns(out, [_solid(32)])
        data = out.read_bytes()
        (declared,) = struct.unpack(">I", data[4:8])
        assert declared == len(data)

    def test_block_length_field_matches_block(self, tmp_path: Path) -> None:
        out = tmp_path / "test.icns"
        write_icns(out, [_solid(16)])
        data = out.read_bytes()
        blocks = _parse_blocks(data)
        assert len(blocks) == 1
        _tag, payload = blocks[0]
        # declared block_len = 8 (tag+len) + len(payload)
        (block_len,) = struct.unpack(">I", data[8 + 4 : 8 + 8])
        assert block_len == 8 + len(payload)


class TestBlockTags:
    @pytest.mark.parametrize("size,expected_tag", list(_SIZE_TO_TAG.items()))
    def test_correct_tag_for_size(self, tmp_path: Path, size: int, expected_tag: bytes) -> None:
        out = tmp_path / "test.icns"
        write_icns(out, [_solid(size)])
        data = out.read_bytes()
        blocks = _parse_blocks(data)
        assert blocks[0][0] == expected_tag

    def test_all_seven_sizes_produce_seven_blocks(self, tmp_path: Path) -> None:
        out = tmp_path / "all.icns"
        images = [_solid(s) for s in sorted(_VALID_SIZES)]
        write_icns(out, images)
        blocks = _parse_blocks(out.read_bytes())
        assert len(blocks) == 7

    def test_blocks_are_in_ascending_size_order(self, tmp_path: Path) -> None:
        out = tmp_path / "order.icns"
        # Pass in reverse order; output must still be sorted.
        images = [_solid(s) for s in sorted(_VALID_SIZES, reverse=True)]
        write_icns(out, images)
        blocks = _parse_blocks(out.read_bytes())
        tags = [tag for tag, _ in blocks]
        assert tags == [_SIZE_TO_TAG[s] for s in sorted(_VALID_SIZES)]


# ---------------------------------------------------------------------------
# PNG payload
# ---------------------------------------------------------------------------


class TestPngPayload:
    def test_block_payload_is_valid_png(self, tmp_path: Path) -> None:
        out = tmp_path / "test.icns"
        write_icns(out, [_solid(32)])
        _, payload = _parse_blocks(out.read_bytes())[0]
        assert payload[:8] == b"\x89PNG\r\n\x1a\n"

    def test_payload_decodes_to_original_size(self, tmp_path: Path) -> None:
        import io

        out = tmp_path / "test.icns"
        write_icns(out, [_solid(128)])
        _, payload = _parse_blocks(out.read_bytes())[0]
        img = Image.open(io.BytesIO(payload))
        assert img.size == (128, 128)

    def test_rgba_mode_preserved(self, tmp_path: Path) -> None:
        import io

        out = tmp_path / "test.icns"
        write_icns(out, [_solid(64)])
        _, payload = _parse_blocks(out.read_bytes())[0]
        img = Image.open(io.BytesIO(payload))
        assert img.mode == "RGBA"

    def test_rgb_image_converted_to_rgba(self, tmp_path: Path) -> None:
        import io

        out = tmp_path / "test.icns"
        rgb_img = Image.new("RGB", (32, 32), (255, 0, 0))
        write_icns(out, [rgb_img])
        _, payload = _parse_blocks(out.read_bytes())[0]
        img = Image.open(io.BytesIO(payload))
        assert img.mode == "RGBA"


# ---------------------------------------------------------------------------
# De-duplication
# ---------------------------------------------------------------------------


class TestDeduplicate:
    def test_duplicate_sizes_produce_single_block(self, tmp_path: Path) -> None:
        out = tmp_path / "dup.icns"
        write_icns(out, [_solid(32, (255, 0, 0, 255)), _solid(32, (0, 255, 0, 255))])
        blocks = _parse_blocks(out.read_bytes())
        assert len(blocks) == 1

    def test_last_duplicate_wins(self, tmp_path: Path) -> None:
        import io

        out = tmp_path / "dup.icns"
        write_icns(out, [_solid(32, (255, 0, 0, 255)), _solid(32, (0, 200, 0, 255))])
        _, payload = _parse_blocks(out.read_bytes())[0]
        img = Image.open(io.BytesIO(payload))
        r, g, _b, _ = img.getpixel((16, 16))
        assert g > 150 and r < 10  # green won


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


class TestValidation:
    def test_empty_list_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match=r"[Aa]t least one"):
            write_icns(tmp_path / "x.icns", [])

    def test_unsupported_size_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Unsupported ICNS size 48"):
            write_icns(tmp_path / "x.icns", [_solid(48)])

    def test_non_square_raises(self, tmp_path: Path) -> None:
        img = Image.new("RGBA", (32, 64), (0, 0, 0, 255))
        with pytest.raises(ValueError, match="square"):
            write_icns(tmp_path / "x.icns", [img])
