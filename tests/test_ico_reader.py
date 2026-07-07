"""Tests for ICO file reading."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from icoforge.core.ico_reader import read_ico
from icoforge.core.models import SizeSpec


@pytest.fixture
def sample_ico(tmp_path: Path) -> Path:
    """Create a sample ICO file with multiple sizes for testing."""
    from icoforge.core.converter import convert
    from icoforge.core.models import IcoConfig, SizeSpec

    # Use icoforge's own converter to create a proper multi-size ICO
    src = tmp_path / "source.png"
    ico_path = tmp_path / "sample.ico"

    # Create source PNG
    source_img = Image.new("RGBA", (64, 64))
    pixels = source_img.load()
    for y in range(64):
        for x in range(64):
            r = (x * 255) // 64
            g = (y * 255) // 64
            b = 128
            a = 255
            pixels[x, y] = (r, g, b, a)
    source_img.save(src, "PNG")

    # Convert to ICO with multiple sizes
    config = IcoConfig(
        sizes=(SizeSpec(16, 16), SizeSpec(32, 32), SizeSpec(48, 48), SizeSpec(64, 64))
    )
    convert(src, ico_path, config)

    return ico_path


class TestReadIco:
    """Test read_ico() function."""

    def test_read_ico_returns_list(self, sample_ico: Path) -> None:
        """Test that read_ico returns a list of frames."""
        frames = read_ico(sample_ico)
        assert isinstance(frames, list)
        assert len(frames) > 0

    def test_read_ico_tuple_structure(self, sample_ico: Path) -> None:
        """Test that each frame is a (Image, SizeSpec) tuple."""
        frames = read_ico(sample_ico)
        for frame_tuple in frames:
            assert isinstance(frame_tuple, tuple)
            assert len(frame_tuple) == 2
            image, spec = frame_tuple
            assert isinstance(image, Image.Image)
            assert isinstance(spec, SizeSpec)

    def test_read_ico_image_is_rgba(self, sample_ico: Path) -> None:
        """Test that returned images are in RGBA mode."""
        frames = read_ico(sample_ico)
        for image, _ in frames:
            assert image.mode == "RGBA"

    def test_read_ico_dimensions_match(self, sample_ico: Path) -> None:
        """Test that image dimensions match SizeSpec."""
        frames = read_ico(sample_ico)
        for image, spec in frames:
            width, height = image.size
            assert width == spec.width
            assert height == spec.height

    def test_read_ico_expected_sizes(self, sample_ico: Path) -> None:
        """Test that ICO contains expected number and sizes."""
        frames = read_ico(sample_ico)
        assert len(frames) == 4
        sizes = sorted([(spec.width, spec.height) for _, spec in frames])
        assert sizes == [(16, 16), (32, 32), (48, 48), (64, 64)]

    def test_read_ico_file_not_found(self, tmp_path: Path) -> None:
        """Test error handling for missing file."""
        missing = tmp_path / "nonexistent.ico"
        with pytest.raises(FileNotFoundError, match="nonexistent"):
            read_ico(missing)

    def test_read_ico_invalid_format(self, tmp_path: Path) -> None:
        """Test error handling for non-ICO file."""
        import re

        invalid_path = tmp_path / "invalid.txt"
        invalid_path.write_text("not an ico")
        with pytest.raises(ValueError, match=re.escape("Expected .ico")):
            read_ico(invalid_path)

    def test_read_ico_pixel_data_preserved(self, sample_ico: Path) -> None:
        """Test that pixel data is correctly read."""
        frames = read_ico(sample_ico)
        # Find the 16x16 frame
        frame_16 = None
        for image, spec in frames:
            if spec.width == 16 and spec.height == 16:
                frame_16 = (image, spec)
                break

        assert frame_16 is not None
        image, spec = frame_16
        assert image.size == (16, 16)
        assert spec.width == 16
        assert spec.height == 16

    def test_read_ico_frames_are_independent(self, sample_ico: Path) -> None:
        """Test that modifying one frame doesn't affect others."""
        frames = read_ico(sample_ico)
        first_image, _ = frames[0]
        original_pixel = first_image.getpixel((0, 0))

        # Modify first frame
        first_image.putpixel((0, 0), (255, 0, 0, 255))

        # Re-read and verify original is unchanged
        frames_again = read_ico(sample_ico)
        first_image_again, _ = frames_again[0]
        assert first_image_again.getpixel((0, 0)) == original_pixel


def test_read_ico_dib_frame(tmp_path: Path) -> None:
    """ICO with a DIB (BMP) frame must decode to the correct size and RGBA mode.

    Classic Windows ICO files (and icons extracted from EXE/DLL) store frames
    as DIBs where BITMAPINFOHEADER.biHeight is doubled (XOR bitmap + AND mask).
    The reader must return a frame of the *real* size, not the doubled height.
    """
    import struct as _s

    width, height, bpp = 4, 4, 32

    # BITMAPINFOHEADER (40 bytes) - biHeight doubled as per ICO DIB convention
    bih = _s.pack(
        "<IiiHHIIiiII",
        40,  # biSize
        width,  # biWidth
        height * 2,  # biHeight doubled (XOR + AND bitmaps stacked)
        1,  # biPlanes
        bpp,  # biBitCount
        0,  # biCompression (BI_RGB)
        0,  # biSizeImage (0 allowed for BI_RGB)
        0,
        0,  # biXPelsPerMeter, biYPelsPerMeter
        0,
        0,  # biClrUsed, biClrImportant
    )

    # XOR bitmap: 32bpp BGRA, bottom-up, 4x4 solid blue, fully opaque
    pixel_bgra = _s.pack("BBBB", 255, 0, 0, 255)
    xor_bitmap = pixel_bgra * (width * height)

    # AND mask: 1bpp, bottom-up; 4 px wide → 1 byte padded to 4 bytes per row
    and_mask = b"\x00" * (4 * height)  # all zeros = fully visible

    dib = bih + xor_bitmap + and_mask

    # ICONDIR (6 bytes): reserved=0, type=1 (ICO), count=1
    icondir = _s.pack("<HHH", 0, 1, 1)
    # ICONDIRENTRY (16 bytes): image data follows immediately at offset 22
    img_offset = 6 + 16
    entry = _s.pack("<BBBBHHII", width, height, 0, 0, 1, bpp, len(dib), img_offset)

    ico_path = tmp_path / "dib_4x4.ico"
    ico_path.write_bytes(icondir + entry + dib)

    frames = read_ico(ico_path)

    assert len(frames) == 1
    img, spec = frames[0]
    assert img.mode == "RGBA"
    assert img.size == (width, height)
    assert spec.width == width
    assert spec.height == height
