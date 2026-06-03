"""AI background removal via rembg, running in an isolated subprocess.

The main process never imports rembg or numpy — all work is delegated to a
separate system-Python process with access to ai_packages/.  This avoids
version conflicts between PyInstaller-bundled extensions (.pyd) and the
packages installed by the AI installer (numpy 2.x, Pillow 12.x, etc.).
"""

from __future__ import annotations

import base64
import io
import subprocess
import sys
from pathlib import Path

from PIL import Image

from icoforge.utils.python_finder import find_python as _find_python


def _get_ai_packages_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "ai_packages"
    return Path(__file__).resolve().parents[3] / "ai_packages"


def is_rembg_available() -> bool:
    """Return True if rembg is accessible, without importing it."""
    if not getattr(sys, "frozen", False):
        try:
            import importlib.util

            return importlib.util.find_spec("rembg") is not None
        except Exception:
            pass
    ai_dir = _get_ai_packages_dir()
    return (ai_dir / "rembg").exists() or bool(list(ai_dir.glob("rembg-*.dist-info")))


REMBG_AVAILABLE: bool = is_rembg_available()


class BgRemoveError(Exception):
    """Raised when background removal cannot proceed."""


MODEL_DOWNLOAD_WARNING = (
    "Pierwsze uruchomienie usuwania tla pobierze model AI U2-Net (~170 MB) "
    "do katalogu ~/.u2net/. Operacja moze chwile potrwac."
)

# Inline script executed by the isolated subprocess.
_REMBG_SCRIPT = """\
import sys, base64, io
ai_packages = sys.argv[1]
sys.path.insert(0, ai_packages)
from rembg import remove
from PIL import Image

raw = base64.b64decode(sys.stdin.buffer.read())
img = Image.open(io.BytesIO(raw)).convert("RGBA")
result = remove(img)
buf = io.BytesIO()
result.save(buf, format="PNG")
sys.stdout.buffer.write(base64.b64encode(buf.getvalue()))
"""


def is_available() -> bool:
    """Return REMBG_AVAILABLE (kept for backwards compatibility)."""
    return REMBG_AVAILABLE


def remove_background(image: Image.Image) -> Image.Image:
    """Remove the background using rembg in an isolated subprocess.

    Args:
        image: Source image (any PIL mode; converted to RGBA internally).

    Returns:
        RGBA image with background pixels made transparent.

    Raises:
        BgRemoveError: rembg not available, Python not found, or inference failed.
    """
    if not REMBG_AVAILABLE:
        raise BgRemoveError("rembg nie jest zainstalowane")

    python_parts = _find_python()
    if not python_parts:
        raise BgRemoveError("Nie znaleziono Pythona w systemie")

    buf_in = io.BytesIO()
    image.convert("RGBA").save(buf_in, format="PNG")
    img_b64 = base64.b64encode(buf_in.getvalue())

    cmd = [*python_parts, "-c", _REMBG_SCRIPT, str(_get_ai_packages_dir())]

    creationflags: int = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    try:
        proc_result = subprocess.run(
            cmd,
            input=img_b64,
            capture_output=True,
            timeout=120,
            creationflags=creationflags,
        )
    except subprocess.TimeoutExpired as exc:
        raise BgRemoveError("rembg subprocess: timeout (>120s)") from exc
    except Exception as exc:
        raise BgRemoveError(f"rembg subprocess nie mógł się uruchomić: {exc}") from exc

    if proc_result.returncode != 0:
        error = proc_result.stderr.decode("utf-8", errors="replace")
        raise BgRemoveError(f"rembg subprocess błąd:\n{error}")

    out_bytes = base64.b64decode(proc_result.stdout)
    return Image.open(io.BytesIO(out_bytes)).convert("RGBA")
