"""HEIC / HEIF / AVIF loading via the optional ``pillow-heif`` library.

``pillow-heif`` integrates with Pillow by registering a plugin that makes
``Image.open()`` understand HEIC/HEIF/AVIF files.  The plugin must be
registered before the first ``Image.open()`` call for those formats.

Install the extra with::

    pip install 'icoforge[heic]'

If ``pillow-heif`` is not available, :func:`load_heic` raises
:class:`HeicSupportMissingError` with installation instructions.  The rest
of :mod:`icoforge` continues to work without it.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

try:
    import pillow_heif as _pillow_heif
except ImportError:
    _pillow_heif = None

HAS_PILLOW_HEIF: bool = _pillow_heif is not None

_opener_registered: bool = False


class HeicSupportMissingError(RuntimeError):
    """Raised when a HEIC/AVIF source is requested but ``pillow-heif`` is unavailable."""

    def __init__(self) -> None:
        super().__init__(
            "HEIC/AVIF support requires the optional 'pillow-heif' dependency. "
            "Install it with: pip install 'icoforge[heic]'"
        )


def register_heif_opener() -> None:
    """Register the pillow-heif Pillow plugin if the library is available.

    Safe to call multiple times — subsequent calls are no-ops.  Does nothing
    (and does not raise) when ``pillow-heif`` is not installed.
    """
    global _opener_registered
    if _pillow_heif is None or _opener_registered:
        return
    _pillow_heif.register_heif_opener()
    _opener_registered = True


def load_heic(source: Path) -> Image.Image:
    """Open a HEIC, HEIF, or AVIF file and return a normalised RGBA image.

    Registers the pillow-heif Pillow plugin on the first call so that
    ``Image.open()`` can handle the format.

    Args:
        source: Path to the HEIC/HEIF/AVIF file.

    Returns:
        RGBA image.

    Raises:
        HeicSupportMissingError: ``pillow-heif`` is not installed.
        FileNotFoundError: ``source`` does not exist.
    """
    if _pillow_heif is None:
        raise HeicSupportMissingError()

    if not source.exists():
        raise FileNotFoundError(source)

    register_heif_opener()
    with Image.open(source) as img:
        return img.convert("RGBA")
