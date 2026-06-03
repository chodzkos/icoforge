"""Write macOS ICNS files from a sequence of PIL images.

ICNS binary layout
------------------
File header  : b"icns" + 4-byte big-endian total file length
Block header : 4-byte OSType tag + 4-byte big-endian block length (header + data)
Block data   : raw PNG bytes for the sizes that use PNG encoding (all modern tags)

Supported tags (PNG-encoded, introduced in macOS 10.7+):
    icp4  - 16x16
    icp5  - 32x32
    icp6  - 64x64
    ic07  - 128x128
    ic08  - 256x256
    ic09  - 512x512
    ic10  - 1024x1024
"""

from __future__ import annotations

import io
import struct
from collections.abc import Callable
from pathlib import Path

from PIL import Image

# Ordered from smallest to largest; only these sizes get PNG-encoded blocks.
_SIZE_TO_TAG: dict[int, bytes] = {
    16: b"icp4",
    32: b"icp5",
    64: b"icp6",
    128: b"ic07",
    256: b"ic08",
    512: b"ic09",
    1024: b"ic10",
}

_VALID_SIZES = frozenset(_SIZE_TO_TAG)


def write_icns(target: Path, images: list[Image.Image]) -> None:
    """Write *images* to a macOS ICNS file at *target*.

    Each image must be square and its width must be one of:
    16, 32, 64, 128, 256, 512, 1024.  Duplicate sizes are silently
    de-duplicated (last occurrence wins).  Images are converted to RGBA
    before encoding.

    Args:
        target: Destination path; parent directory is created automatically
            if it does not exist (consistent with :func:`write_ico` and
            :func:`write_cur`).
        images: PIL images to include.  At least one image is required.

    Raises:
        ValueError: If *images* is empty or contains an unsupported size.
    """
    if not images:
        raise ValueError("At least one image is required.")

    # De-duplicate: last occurrence of each size wins.
    by_size: dict[int, Image.Image] = {}
    for img in images:
        w, h = img.size
        if w != h:
            raise ValueError(f"ICNS images must be square, got {w}x{h}.")
        if w not in _VALID_SIZES:
            raise ValueError(f"Unsupported ICNS size {w}. Supported: {sorted(_VALID_SIZES)}.")
        by_size[w] = img

    # Build blocks in canonical size order.
    blocks: list[bytes] = []
    for size in sorted(by_size):
        img = by_size[size].convert("RGBA")
        tag = _SIZE_TO_TAG[size]
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        png_data = buf.getvalue()
        block_len = 8 + len(png_data)  # 4-byte tag + 4-byte length + data
        blocks.append(tag + struct.pack(">I", block_len) + png_data)

    payload = b"".join(blocks)
    total_len = 8 + len(payload)  # file header (8 bytes) + all blocks
    header = b"icns" + struct.pack(">I", total_len)

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(header + payload)


def render_and_write_icns(
    source: Path,
    target: Path,
    sizes: list[int],
    *,
    resample: Image.Resampling = Image.Resampling.LANCZOS,
    background: tuple[int, int, int, int] = (0, 0, 0, 0),
    preserve_aspect: bool = True,
    progress: Callable[[float], None] | None = None,
) -> None:
    """Open *source*, resize to each size in *sizes*, and write an ICNS file.

    Unlike :func:`write_icns` this function accepts sizes above 256 (e.g. 512,
    1024) which are valid for ICNS but not for the ICO format.

    Args:
        source: Source image path (any format Pillow can open).
        target: Destination .icns path.
        sizes: List of target pixel sizes (must all be in ``_VALID_SIZES``).
        resample: Pillow resampling filter (default: LANCZOS).
        background: RGBA fill for images without alpha (default: transparent).
        preserve_aspect: Letterbox source if its aspect ratio is not 1:1.
        progress: Optional callback called with values 0.0..1.0.

    Raises:
        ValueError: A size is not supported by ICNS.
        FileNotFoundError: *source* does not exist.
    """
    invalid = [s for s in sizes if s not in _VALID_SIZES]
    if invalid:
        raise ValueError(f"Unsupported ICNS size(s) {invalid}. Supported: {sorted(_VALID_SIZES)}.")

    with Image.open(source) as _src:
        src = _src.convert("RGBA")
    images: list[Image.Image] = []
    total = len(sizes)

    for i, size in enumerate(sorted(set(sizes))):
        if preserve_aspect:
            frame = Image.new("RGBA", (size, size), background)
            thumb = src.copy()
            thumb.thumbnail((size, size), resample)
            x = (size - thumb.width) // 2
            y = (size - thumb.height) // 2
            frame.paste(thumb, (x, y), thumb)
        else:
            frame = src.resize((size, size), resample=resample)

        images.append(frame)
        if progress is not None:
            progress((i + 1) / total)

    write_icns(target, images)
