"""Application paths: settings directory (via gui-kit Config), resource lookup."""

from __future__ import annotations

import sys
from pathlib import Path

from chodzkos_gui_kit.config import config_dir

# Nazwa aplikacji dla platformdirs / wariantu portable (jedno źródło prawdy).
APP_NAME = "IcoForge"


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
    """Return the directory used for persistent application data.

    Delegates to the kit's :func:`chodzkos_gui_kit.config.config_dir`: portable
    variant (frozen ``.exe`` with a ``portable.flag`` marker beside it) → the exe
    directory; otherwise ``platformdirs`` config dir (``%APPDATA%/IcoForge`` on
    Windows, ``~/.config/IcoForge`` on Linux). Same directory that holds
    ``config.json`` — used here for the ``presets/`` subfolder.
    """
    return config_dir(APP_NAME)
