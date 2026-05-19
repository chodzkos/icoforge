"""PNG optimization.

Lossless only. The contract: pixel data identical before and after, only
encoding/metadata changes. Validated by hash comparison in tests.

Primary engine: ``pyoxipng``. Optional Zopfli pass for max compression.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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
        ValueError: Source is not a PNG (by extension check; deeper validation TODO).
    """
    if not source.exists():
        raise FileNotFoundError(source)
    if source.suffix.lower() != ".png":
        raise ValueError(f"Expected .png source, got {source.suffix}")

    # TODO(phase-3): wire pyoxipng here.
    # import pyoxipng
    # opts = pyoxipng.Options(level=cfg.level, ...)
    # pyoxipng.optimize(str(source), str(out_path), opts)
    raise NotImplementedError("Phase 3 implementation pending")

    # Pseudocode for the metadata strip (to be implemented):
    # if cfg.strip_metadata:
    #     _strip_png_chunks(out_path, keep=cfg.keep_chunks)

    # bytes_after = out_path.stat().st_size
    # return OptimizationResult(source, out_path, bytes_before, bytes_after)


def _strip_png_chunks(path: Path, keep: frozenset[str]) -> None:
    """Remove metadata chunks (tEXt, iTXt, zTXt, eXIf, tIME) from a PNG.

    Parses chunk-by-chunk because Pillow loses fidelity if we just resave.

    Args:
        path: PNG file to modify in place.
        keep: Set of 4-char chunk names to preserve (e.g. ``{"iCCP"}``).
    """
    # TODO(phase-3): implement chunk parser. PNG layout:
    #   signature (8 bytes) + chunks
    #   each chunk: length(4) + type(4) + data(length) + crc(4)
    # Skip chunks whose type is in the strip set and not in `keep`.
    raise NotImplementedError("Phase 3 implementation pending")


def verify_lossless(original: Path, optimized: Path) -> bool:
    """Verify that two PNGs have identical pixel data.

    Args:
        original: First PNG.
        optimized: Second PNG.

    Returns:
        True if every pixel value matches.
    """
    # TODO(phase-3): load both with Pillow, compare bytes of raw pixel arrays.
    raise NotImplementedError("Phase 3 implementation pending")
