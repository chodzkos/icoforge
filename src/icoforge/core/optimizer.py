"""PNG optimization.

Lossless only. The contract: pixel data identical before and after, only
encoding/metadata changes. Validated by hash comparison in tests.

Primary engine: ``pyoxipng``. Optional Zopfli pass for max compression.
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from pathlib import Path

import oxipng
from PIL import Image

from icoforge.core.models import OptimizationConfig


@dataclass(frozen=True)
class OptimizationResult:
    """Outcome of optimizing one file."""

    source: Path
    target: Path
    bytes_before: int
    bytes_after: int

    @property
    def saved_bytes(self) -> int:
        return self.bytes_before - self.bytes_after

    @property
    def saved_ratio(self) -> float:
        if self.bytes_before == 0:
            return 0.0
        return self.saved_bytes / self.bytes_before


def optimize_png(
    source: Path,
    target: Path | None = None,
    config: OptimizationConfig | None = None,
) -> OptimizationResult:
    """Optimize a PNG file losslessly.

    Args:
        source: Path to the input PNG.
        target: Output path. If ``None``, optimization is done in place.
        config: Optimization parameters. Uses defaults if ``None``.

    Returns:
        OptimizationResult with byte-level statistics.

    Raises:
        FileNotFoundError: Source does not exist.
        ValueError: Source is not a PNG.
    """
    if not source.exists():
        raise FileNotFoundError(source)
    if source.suffix.lower() != ".png":
        raise ValueError(f"Expected .png source, got {source.suffix}")

    cfg = config or OptimizationConfig()
    out_path = target or source
    bytes_before = source.stat().st_size

    # Validate it's a real PNG
    try:
        _ = Image.open(source)
    except OSError as exc:
        raise ValueError(f"Cannot open image: {exc}") from exc

    # Read, optimize with oxipng, strip metadata if requested
    data = source.read_bytes()
    if cfg.strip_metadata:
        if cfg.keep_chunks:
            strip_chunks = oxipng.StripChunks.keep([s.encode() for s in cfg.keep_chunks])
        else:
            strip_chunks = oxipng.StripChunks.all()
    else:
        strip_chunks = oxipng.StripChunks.none()

    deflate = (
        oxipng.Deflaters.zopfli(iterations=100)
        if cfg.use_zopfli
        else oxipng.Deflaters.libdeflater(cfg.level)
    )
    data = oxipng.optimize_from_memory(data, level=cfg.level, strip=strip_chunks, deflate=deflate)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(data)
    bytes_after = len(data)

    return OptimizationResult(source, out_path, bytes_before, bytes_after)


def _strip_png_chunks_from_bytes(data: bytes, keep: frozenset[str]) -> bytes:
    """Remove metadata chunks from PNG bytes.

    Args:
        data: PNG binary data.
        keep: Set of 4-char chunk type names to keep (e.g. ``{"iCCP"}``).

    Returns:
        PNG bytes with metadata chunks removed.
    """
    if len(data) < 8 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Invalid PNG signature")

    chunks = _parse_png_chunks(data)
    keep_bytes = {s.encode() for s in keep}
    kept = [(ct, cd) for ct, cd in chunks if ct in {b"IHDR", b"IDAT", b"IEND"} or ct in keep_bytes]
    return _write_png_chunks(kept)


def _parse_png_chunks(data: bytes) -> list[tuple[bytes, bytes]]:
    """Parse PNG chunks. Returns list of (type, data) tuples."""
    chunks: list[tuple[bytes, bytes]] = []
    pos = 8  # Skip signature
    while pos < len(data):
        if pos + 8 > len(data):
            break
        length = struct.unpack(">I", data[pos : pos + 4])[0]
        pos += 4
        chunk_type = data[pos : pos + 4]
        pos += 4
        chunk_data = data[pos : pos + length]
        pos += length
        pos += 4  # Skip CRC
        chunks.append((chunk_type, chunk_data))
    return chunks


def _write_png_chunks(chunks: list[tuple[bytes, bytes]]) -> bytes:
    """Reconstruct PNG from chunks."""
    result = bytearray(b"\x89PNG\r\n\x1a\n")
    for chunk_type, chunk_data in chunks:
        result.extend(struct.pack(">I", len(chunk_data)))
        chunk_with_type = chunk_type + chunk_data
        result.extend(chunk_with_type)
        crc = zlib.crc32(chunk_with_type) & 0xFFFFFFFF
        result.extend(struct.pack(">I", crc))
    return bytes(result)


def verify_lossless(original: Path, optimized: Path) -> bool:
    """Verify that two PNGs have identical pixel data.

    Args:
        original: First PNG.
        optimized: Second PNG.

    Returns:
        True if every pixel value matches.
    """
    img1 = Image.open(original).convert("RGBA")
    img2 = Image.open(optimized).convert("RGBA")
    # Compare images by converting to bytes
    return img1.tobytes() == img2.tobytes()
