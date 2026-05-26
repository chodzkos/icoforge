"""Application paths: settings directory, portable mode detection."""

from __future__ import annotations

import os
import sys
from pathlib import Path


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
