"""Read and parse ICO files into individual frames with metadata."""

from __future__ import annotations

import io
import struct
from pathlib import Path

from PIL import IcoImagePlugin, Image

from icoforge.core import limits
from icoforge.core.models import SizeSpec


def read_ico(path: Path) -> list[tuple[Image.Image, SizeSpec]]:
    """Read an ICO file and extract all frames as RGBA images.

    Supports any valid ICO file: entries may be PNG-compressed (modern,
    typically 256x256) or DIB/BMP-encoded (classic Windows format with XOR
    bitmap + AND mask and doubled biHeight in BITMAPINFOHEADER). Decoding is
    delegated to Pillow's IcoFile, which handles both formats correctly.

    Args:
        path: Path to the .ico file.

    Returns:
        List of (image, SizeSpec) tuples, one per ICO frame.
        Images are converted to RGBA mode.

    Raises:
        FileNotFoundError: ICO file does not exist.
        ValueError: File is not a valid ICO (wrong extension, bad signature,
            no frames, or corrupt frame data).
    """
    if not path.exists():
        raise FileNotFoundError(path)

    if path.suffix.lower() != ".ico":
        raise ValueError(f"Expected .ico file, got {path.suffix}")

    limits.check_file_size(path, limits.MAX_ICO_BYTES)

    data = path.read_bytes()

    if len(data) < 6:
        raise ValueError(f"File too small to be ICO: {path}")

    # Quick header check: reserved must be 0, type must be 1 (ICO, not cursor)
    _, ico_type, count = struct.unpack("<HHH", data[0:6])

    if ico_type != 1:
        raise ValueError(f"Invalid ICO type: {ico_type}")

    if count == 0:
        raise ValueError(f"No frames found in ICO file: {path}")

    # Delegate frame decoding to Pillow's IcoFile, which handles both
    # PNG-compressed entries and DIB entries (doubled biHeight + AND mask).
    try:
        ico = IcoImagePlugin.IcoFile(io.BytesIO(data))  # type: ignore[no-untyped-call]
    except Exception as exc:
        raise ValueError(f"Failed to parse ICO file: {exc}") from exc

    frames: list[tuple[Image.Image, SizeSpec]] = []
    for idx in range(len(ico.entry)):
        try:
            with limits.guard_decompression_bomb():
                img = ico.frame(idx)  # type: ignore[no-untyped-call]
                rgba = img.convert("RGBA")
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"Failed to decode image in ICO: {exc}") from exc
        w, h = rgba.size
        frames.append((rgba.copy(), SizeSpec(w, h)))

    if not frames:
        raise ValueError(f"No valid frames extracted from ICO: {path}")

    return frames
