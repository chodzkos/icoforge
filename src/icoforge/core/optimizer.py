"""PNG optimization.

Lossless only. The contract: pixel data identical before and after, only
encoding/metadata changes. Validated by hash comparison in tests.

Primary engine: ``pyoxipng``. Optional Zopfli pass for max compression.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import oxipng
from PIL import Image

from icoforge.core.models import OptimizationConfig

# Chunk types that carry color-reproduction metadata.
_COLOR_PROFILE_CHUNKS: frozenset[str] = frozenset({"iCCP", "sRGB", "gAMA", "cHRM"})


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


def optimize_batch(
    paths: list[Path],
    config: OptimizationConfig | None = None,
    progress: Callable[[float], None] | None = None,
) -> list[OptimizationResult]:
    """Optimize multiple PNG files in batch.

    Args:
        paths: List of PNG file paths to optimize.
        config: Optimization parameters. Uses defaults if ``None``.
        progress: Optional callback ``progress(ratio)`` where ratio is 0..1
            indicating overall batch progress.

    Returns:
        List of OptimizationResult for each input file.

    Raises:
        ValueError: If paths list is empty.
    """
    if not paths:
        raise ValueError("paths list cannot be empty")

    results: list[OptimizationResult] = []
    for i, source in enumerate(paths):
        result = optimize_png(source, target=source, config=config)
        results.append(result)
        if progress is not None:
            progress((i + 1) / len(paths))

    return results


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

    # Validate it's a real PNG; use a context manager so the file handle is
    # released immediately — critical on Windows where an open handle blocks
    # a subsequent in-place write to the same path.
    try:
        with Image.open(source) as img:
            img.verify()
    except OSError as exc:
        raise ValueError(f"Cannot open image: {exc}") from exc

    # Build the set of chunks to keep when stripping metadata.
    # keep_chunks (explicit) union color-profile chunks (when preserve_color_profile=True).
    data = source.read_bytes()
    if cfg.strip_metadata:
        chunks_to_keep = set(cfg.keep_chunks)
        if cfg.preserve_color_profile:
            chunks_to_keep |= _COLOR_PROFILE_CHUNKS
        strip_chunks = (
            oxipng.StripChunks.keep([s.encode() for s in chunks_to_keep])
            if chunks_to_keep
            else oxipng.StripChunks.all()
        )
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
