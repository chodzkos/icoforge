"""Data models for icoforge.

All configuration objects are frozen dataclasses. Pass them explicitly through
the pipeline; never read configuration from globals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Literal


class ResampleAlgorithm(str, Enum):
    """Resampling algorithms exposed by the converter.

    Maps to ``PIL.Image.Resampling`` values in ``core.resampling``.
    """

    LANCZOS = "lanczos"
    BICUBIC = "bicubic"
    BILINEAR = "bilinear"
    NEAREST = "nearest"
    BOX = "box"


BitDepth = Literal[8, 24, 32]


@dataclass(frozen=True)
class Color:
    """RGBA color, each channel 0-255."""

    r: int
    g: int
    b: int
    a: int = 255

    def as_tuple(self) -> tuple[int, int, int, int]:
        return (self.r, self.g, self.b, self.a)


TRANSPARENT: Literal["transparent"] = "transparent"
Background = Color | Literal["transparent"]


@dataclass(frozen=True)
class SizeSpec:
    """Specification for one image inside the ICO container."""

    width: int
    height: int
    bit_depth: BitDepth = 32
    resample: ResampleAlgorithm | None = None  # None = use global from IcoConfig
    source_override: Path | None = None  # Per-size source file (phase 2)

    def __post_init__(self) -> None:
        if not (1 <= self.width <= 256 and 1 <= self.height <= 256):
            raise ValueError(f"ICO sizes must be 1..256, got {self.width}x{self.height}")


@dataclass(frozen=True)
class IcoConfig:
    """Top-level configuration for an ICO conversion."""

    sizes: tuple[SizeSpec, ...]
    resample: ResampleAlgorithm = ResampleAlgorithm.LANCZOS
    background: Background = TRANSPARENT
    preserve_aspect: bool = True
    auto_trim: bool = False

    def __post_init__(self) -> None:
        if not self.sizes:
            raise ValueError("IcoConfig.sizes must contain at least one SizeSpec")


# Common presets - exposed for both CLI and GUI defaults.
WINDOWS_APP_SIZES: tuple[SizeSpec, ...] = tuple(
    SizeSpec(s, s) for s in (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)
)

FAVICON_SIZES: tuple[SizeSpec, ...] = tuple(SizeSpec(s, s) for s in (16, 32, 48))


@dataclass(frozen=True)
class OptimizationConfig:
    """Configuration for PNG optimization."""

    level: int = 4  # oxipng level 0-6
    strip_metadata: bool = True
    use_zopfli: bool = False  # slow but smaller
    preserve_color_profile: bool = False
    keep_chunks: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not (0 <= self.level <= 6):
            raise ValueError(f"oxipng level must be 0..6, got {self.level}")
