"""IcoForge core - GUI/CLI-independent logic."""

# Importing limits installs the global Pillow decompression-bomb pixel cap as a
# side effect; keep it first so the cap is active before any image is decoded.
from icoforge.core.limits import check_file_size
from icoforge.core.models import (
    FAVICON_SIZES,
    TRANSPARENT,
    WINDOWS_APP_SIZES,
    Background,
    BitDepth,
    Color,
    IcoConfig,
    OptimizationConfig,
    ResampleAlgorithm,
    SizeSpec,
)

__all__ = [
    "FAVICON_SIZES",
    "TRANSPARENT",
    "WINDOWS_APP_SIZES",
    "Background",
    "BitDepth",
    "Color",
    "IcoConfig",
    "OptimizationConfig",
    "ResampleAlgorithm",
    "SizeSpec",
    "check_file_size",
]
