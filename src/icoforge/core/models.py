"""Data models for icoforge.

All configuration objects are frozen dataclasses. Pass them explicitly through
the pipeline; never read configuration from globals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Literal


class ResampleAlgorithm(StrEnum):
    """Resampling algorithms exposed by the converter.

    Maps to ``PIL.Image.Resampling`` values in ``core.resampling``.

    Attributes:
        LANCZOS: High-quality downsampling filter. Best for photos.
        BICUBIC: Smooth interpolation. Good general-purpose choice.
        BILINEAR: Fast interpolation. Acceptable quality for small icons.
        NEAREST: No interpolation. Preserves hard pixel edges (pixel art).
        BOX: Uniform box filter. Fast and sharp for large downscales.
    """

    LANCZOS = "lanczos"
    BICUBIC = "bicubic"
    BILINEAR = "bilinear"
    NEAREST = "nearest"
    BOX = "box"


BitDepth = Literal[8, 24, 32]

_VALID_BIT_DEPTHS: frozenset[int] = frozenset({8, 24, 32})


@dataclass(frozen=True)
class Color:
    """RGBA color with each channel in the range 0-255.

    Attributes:
        r: Red channel (0-255).
        g: Green channel (0-255).
        b: Blue channel (0-255).
        a: Alpha channel (0-255). Defaults to 255 (fully opaque).
    """

    r: int
    g: int
    b: int
    a: int = 255

    def __post_init__(self) -> None:
        for name, value in (("r", self.r), ("g", self.g), ("b", self.b), ("a", self.a)):
            if not (0 <= value <= 255):
                raise ValueError(f"Color channel '{name}' must be 0..255, got {value}")

    def as_tuple(self) -> tuple[int, int, int, int]:
        """Return the color as an (r, g, b, a) tuple."""
        return (self.r, self.g, self.b, self.a)


TRANSPARENT: Literal["transparent"] = "transparent"
Background = Color | Literal["transparent"]


@dataclass(frozen=True)
class SizeSpec:
    """Specification for one image inside the ICO container.

    Attributes:
        width: Target width in pixels (1-256).
        height: Target height in pixels (1-256).
        bit_depth: Colour depth of this entry. Must be 8, 24, or 32.
        resample: Override the global resampling algorithm for this size.
            ``None`` means "inherit from :class:`IcoConfig`".
        source_override: Use a different source file for this size only.
            Intended for phase-2 per-size sources (e.g. a hand-drawn 16x16).
            ``None`` means "use the global source".
    """

    width: int
    height: int
    bit_depth: BitDepth = 32
    resample: ResampleAlgorithm | None = None
    source_override: Path | None = None

    def __post_init__(self) -> None:
        if not (1 <= self.width <= 256):
            raise ValueError(f"ICO width must be 1..256, got {self.width}")
        if not (1 <= self.height <= 256):
            raise ValueError(f"ICO height must be 1..256, got {self.height}")
        if self.bit_depth not in _VALID_BIT_DEPTHS:
            raise ValueError(
                f"bit_depth must be one of {sorted(_VALID_BIT_DEPTHS)}, got {self.bit_depth}"
            )


@dataclass(frozen=True)
class IcoConfig:
    """Top-level configuration for an ICO conversion.

    Attributes:
        sizes: Non-empty tuple of size specifications included in the output.
        resample: Default resampling algorithm used when a :class:`SizeSpec`
            does not override it.
        background: Background fill for source images without an alpha channel.
            Use ``"transparent"`` to keep pixels transparent, or a
            :class:`Color` to composite onto a solid background.
        preserve_aspect: When ``True``, the source is letterboxed/pillarboxed
            into the target canvas rather than stretched.
        auto_trim: When ``True``, transparent borders are cropped before
            resizing.
    """

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
    """Configuration for PNG optimization.

    Attributes:
        level: oxipng compression level (0 = fastest, 6 = smallest).
        strip_metadata: Remove metadata chunks (tEXt, iTXt, zTXt, eXIf,
            tIME) from the output.
        use_zopfli: Run an additional Zopfli pass for maximum compression.
            Significantly slower; rarely worth it above level 4.
        preserve_color_profile: Keep the ``iCCP`` chunk even when
            ``strip_metadata`` is ``True``.
        keep_chunks: Explicit set of 4-char chunk names to preserve regardless
            of ``strip_metadata``.
    """

    level: int = 4
    strip_metadata: bool = True
    use_zopfli: bool = False
    preserve_color_profile: bool = False
    keep_chunks: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not (0 <= self.level <= 6):
            raise ValueError(f"oxipng level must be 0..6, got {self.level}")
