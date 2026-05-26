"""Application paths: settings directory, portable mode detection, resource lookup."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def get_resource_path(relative: str) -> Path:
    """Return the absolute path to a bundled resource.

    Works both in the development tree and in a PyInstaller frozen build.

    Args:
        relative: Path relative to the project root (e.g. ``"assets/logo.png"``).
                  In a frozen build the same path is resolved under ``sys._MEIPASS``.

    Returns:
        Absolute :class:`~pathlib.Path` to the resource.
    """
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative
    # Dev: this file lives at src/icoforge/utils/paths.py → parents[3] = repo root
    return Path(__file__).resolve().parents[3] / relative


def get_settings_dir() -> Path:
    """Return the directory used for all persistent application data.

    Portable mode: when a ``portable.txt`` file exists next to the executable
    (only meaningful for PyInstaller builds), data goes to a ``settings/``
    subfolder beside the executable.  Otherwise uses the platform config dir.
    """
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        if (exe_dir / "portable.txt").exists():
            return exe_dir / "settings"

    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            return Path(appdata) / "IcoForge"

    return Path.home() / ".config" / "icoforge"
