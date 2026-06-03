"""Locate a system Python 3 interpreter.

Used by features that need to run code in an isolated process (e.g. rembg),
where sys.executable may point to a PyInstaller bundle rather than real Python.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def find_python() -> list[str] | None:
    """Return a command list for a working Python 3 interpreter.

    In a PyInstaller bundle sys.executable points to the app exe, not Python.
    Searches PATH and common Windows locations in that case.
    In development returns [sys.executable] directly.
    """
    if not getattr(sys, "frozen", False):
        return [sys.executable]

    candidates: list[list[str]] = []

    py_launcher = shutil.which("py")
    if py_launcher:
        candidates.append([py_launcher, "-3"])

    for name in ("python3.12", "python3.11", "python3.10", "python3", "python"):
        path = shutil.which(name)
        if path and "IcoForge" not in path and "icoforge" not in path.lower():
            candidates.append([path])

    local_app_data = os.environ.get("LOCALAPPDATA", "")
    static_paths = [
        Path(local_app_data) / "Programs/Python/Python312/python.exe",
        Path(local_app_data) / "Programs/Python/Python311/python.exe",
        Path(local_app_data) / "Programs/Python/Python310/python.exe",
        Path("C:/Python312/python.exe"),
        Path("C:/Python311/python.exe"),
        Path("C:/Python310/python.exe"),
    ]
    for p in static_paths:
        if p.exists():
            candidates.append([str(p)])

    for cmd in candidates:
        try:
            result = subprocess.run(
                [*cmd, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if "Python 3" in result.stdout + result.stderr:
                return cmd
        except Exception:
            continue

    return None
