"""Entry point for ``python -m icoforge`` and the ``icoforge`` console script."""

from __future__ import annotations


def run_gui() -> int:
    """Launch the PySide6 GUI."""
    from icoforge.gui.main_window import main as gui_main

    return gui_main()


if __name__ == "__main__":
    raise SystemExit(run_gui())
