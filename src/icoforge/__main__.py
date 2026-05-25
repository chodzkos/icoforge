"""Entry point for ``python -m icoforge`` and the ``icoforge`` console script."""

from __future__ import annotations

from pathlib import Path


def _force_xcb_on_wsl() -> None:
    """Force X11 backend on WSL to avoid WSLg Wayland window-activation bugs."""
    import os

    if os.environ.get("QT_QPA_PLATFORM"):
        return  # user has set it explicitly, don't override
    try:
        if "microsoft" in Path("/proc/version").read_text().lower():
            os.environ["QT_QPA_PLATFORM"] = "xcb"
    except OSError:
        pass


def run_gui() -> int:
    """Launch the PySide6 GUI."""
    _force_xcb_on_wsl()

    from icoforge.core import heic_loader

    heic_loader.register_heif_opener()

    from icoforge.gui.main_window import main as gui_main

    return gui_main()


if __name__ == "__main__":
    raise SystemExit(run_gui())
