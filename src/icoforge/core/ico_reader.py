"""Read and parse ICO files into individual frames with metadata."""

from __future__ import annotations

import io
import struct
from pathlib import Path

from PIL import Image

from icoforge.core.models import SizeSpec


def read_ico(path: Path) -> list[tuple[Image.Image, SizeSpec]]:
    """Read an ICO file and extract all frames as RGBA images.

    ICO files contain multiple image formats. This reader:
    1. Parses the ICO header to find all embedded images
    2. Extracts PNG data (icoforge uses PNG for all entries)
    3. Decodes each PNG to RGBA

    Args:
        path: Path to the .ico file.

    Returns:
        List of (image, SizeSpec) tuples, one per ICO frame.
        Images are converted to RGBA mode.

    Raises:
        FileNotFoundError: ICO file does not exist.
        ValueError: File is not a valid ICO.
    """
    if not path.exists():
        raise FileNotFoundError(path)

    if path.suffix.lower() != ".ico":
        raise ValueError(f"Expected .ico file, got {path.suffix}")

    data = path.read_bytes()

    if len(data) < 6:
        raise ValueError(f"File too small to be ICO: {path}")

    # Parse ICONDIR header: reserved(H) type(H) count(H)
    reserved, ico_type, count = struct.unpack("<HHH", data[0:6])

    if ico_type != 1:
        raise ValueError(f"Invalid ICO type: {ico_type}")

    if count == 0:
        raise ValueError(f"No frames found in ICO file: {path}")

    frames: list[tuple[Image.Image, SizeSpec]] = []

    # Parse ICONDIRENTRY for each frame
    # Each entry: width(B) height(B) color_count(B) reserved(B) planes(H) bpp(H) size(I) offset(I)
    for i in range(count):
        entry_offset = 6 + i * 16
        if entry_offset + 16 > len(data):
            raise ValueError(f"Truncated ICO file: {path}")

        entry = data[entry_offset : entry_offset + 16]
        width, height, _, _, _, _, img_size, img_offset = struct.unpack("<BBBBHHII", entry)

        # Handle special case: width/height of 0 means 256
        if width == 0:
            width = 256
        if height == 0:
            height = 256

        # Extract image data
        if img_offset + img_size > len(data):
            raise ValueError(f"Invalid image offset in ICO: {path}")

        img_data = data[img_offset : img_offset + img_size]

        try:
            # Try to decode as PNG (icoforge uses PNG)
            frame = Image.open(io.BytesIO(img_data))
            rgba_frame = frame.convert("RGBA")
        except Exception as exc:
            raise ValueError(f"Failed to decode image in ICO: {exc}") from exc

        # Create SizeSpec
        spec = SizeSpec(width, height)

        # Store frame
        frames.append((rgba_frame.copy(), spec))

    if not frames:
        raise ValueError(f"No valid frames extracted from ICO: {path}")

    return frames
