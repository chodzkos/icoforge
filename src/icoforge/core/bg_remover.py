"""AI background removal via rembg (optional dependency).

Requires the ``bgremove`` extra::

    pip install icoforge[bgremove]

On the first call, rembg downloads the U2-Net ONNX model (~170 MB) to
``~/.u2net/``.  Subsequent calls reuse the cached model.
"""

from __future__ import annotations

from PIL import Image


class BgRemoveError(Exception):
    """Raised when background removal cannot proceed."""


MODEL_DOWNLOAD_WARNING = (
    "Pierwsze uruchomienie usuwania tla pobierze model AI U2-Net (~170 MB) "
    "do katalogu ~/.u2net/. Operacja moze chwile potrwac."
)


def is_available() -> bool:
    """Return True if rembg is installed and importable."""
    try:
        import rembg  # noqa: F401

        return True
    except ImportError:
        return False


def remove_background(image: Image.Image) -> Image.Image:
    """Remove the background from *image* using the U2-Net AI model.

    Args:
        image: Source image (any PIL mode; converted to RGBA internally).

    Returns:
        RGBA image with background pixels made transparent.

    Raises:
        BgRemoveError: rembg is not installed, or model inference failed.
    """
    try:
        import rembg
    except ImportError as exc:
        raise BgRemoveError("rembg is not installed. Run: pip install icoforge[bgremove]") from exc

    try:
        result: Image.Image = rembg.remove(image)
        return result.convert("RGBA")
    except Exception as exc:
        raise BgRemoveError(f"Background removal failed: {exc}") from exc
