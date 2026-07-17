"""Window position/size persistence — shared app Config."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication, QMainWindow

from icoforge.utils.settings import get_config

_KEY = "window_state"
_MIN_W = 700
_MIN_H = 500


def save_window_state(window: QMainWindow) -> None:
    """Save window geometry (x, y, width, height) to the shared config."""
    geo = window.geometry()
    cfg = get_config()
    cfg[_KEY] = {
        "x": geo.x(),
        "y": geo.y(),
        "width": geo.width(),
        "height": geo.height(),
    }
    cfg.save_now()


def restore_window_state(window: QMainWindow) -> None:
    """Restore window geometry from config; falls back silently if missing or off-screen."""
    raw = get_config().get(_KEY)
    if not isinstance(raw, dict):
        return
    x = raw.get("x")
    y = raw.get("y")
    w = raw.get("width")
    h = raw.get("height")
    if not (
        isinstance(x, int) and isinstance(y, int) and isinstance(w, int) and isinstance(h, int)
    ):
        return
    w = max(w, _MIN_W)
    h = max(h, _MIN_H)
    if _is_position_visible(x, y, w, h):
        window.setGeometry(x, y, w, h)
    else:
        window.resize(w, h)


def _is_position_visible(x: int, y: int, w: int, h: int) -> bool:
    """Return True if at least 100x100 px of the window rect overlaps any available screen."""
    app = QApplication.instance()
    if not isinstance(app, QApplication):
        return False
    for screen in app.screens():
        avail = screen.availableGeometry()
        overlap_x = min(x + w, avail.x() + avail.width()) - max(x, avail.x())
        overlap_y = min(y + h, avail.y() + avail.height()) - max(y, avail.y())
        if overlap_x >= 100 and overlap_y >= 100:
            return True
    return False
