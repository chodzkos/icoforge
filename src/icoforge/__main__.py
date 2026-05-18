"""Entry point for ``python -m icoforge`` and the ``icoforge`` console script."""

from __future__ import annotations

import sys


def run_gui() -> int:
    """Launch the PySide6 GUI."""
    # TODO(phase-1): import inside the function to avoid loading Qt for `--help`
    # from icoforge.gui.main_window import main as gui_main
    # return gui_main()
    print("GUI not yet implemented. Use icoforge-cli for now.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(run_gui())
