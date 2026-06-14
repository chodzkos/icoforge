"""Recolourable SVG icon provider for the Qt GUI."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QGuiApplication, QIcon, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from icoforge.utils.paths import get_resource_path

ICON_MAP: dict[str, str] = {
    "pencil": "pencil.svg",
    "eraser": "eraser.svg",
    "eyedropper": "pipette.svg",
    "fill": "paint-bucket.svg",
    "line": "minus.svg",
    "rectangle": "square.svg",
    "selection": "square-dashed.svg",
    "swap_colors": "arrow-left-right.svg",
    "reset_colors": "rotate-ccw.svg",
    "zoom_in": "zoom-in.svg",
    "zoom_out": "zoom-out.svg",
    "zoom_fit": "maximize.svg",
    "zoom_1to1": "scan.svg",
    "undo": "undo-2.svg",
    "redo": "redo-2.svg",
    "copy": "copy.svg",
    "cut": "scissors.svg",
    "paste": "clipboard-paste.svg",
    "save": "save.svg",
    "new_ico": "file-plus.svg",
    "open": "folder-open.svg",
}

_cache: dict[tuple[str, str, int], QIcon] = {}
_color_resolver: Callable[[str], str] | None = None


def set_color_resolver(resolver: Callable[[str], str] | None) -> None:
    """Connect a theme palette token resolver, e.g. ``lambda token: palette[token]``."""
    global _color_resolver
    _color_resolver = resolver


def _resolve_color(token: str) -> str:
    """Resolve a palette token to a hex colour, with a readable dark-theme fallback."""
    if _color_resolver is not None:
        try:
            return _color_resolver(token)
        except Exception:
            pass
    return "#dde1ec"


def _recolor_svg(svg_text: str, hex_color: str) -> str:
    return svg_text.replace("currentColor", hex_color)


def _load_recolored_svg(name: str, hex_color: str) -> str | None:
    svg_file = ICON_MAP.get(name)
    if svg_file is None:
        return None

    svg_path = get_resource_path(f"assets/icons/{svg_file}")
    try:
        svg_text = Path(svg_path).read_text(encoding="utf-8")
    except OSError:
        return None
    return _recolor_svg(svg_text, hex_color)


def get_icon(name: str, color: str = "fg", size: int = 20) -> QIcon:
    """Return a recoloured Lucide icon for a semantic action.

    Args:
        name: Key from :data:`ICON_MAP`, for example ``"pencil"``.
        color: Palette token, for example ``"fg"``, ``"red"``, or ``"accent"``.
        size: Logical icon size in pixels.
    """
    hex_color = _resolve_color(color)
    key = (name, hex_color, size)
    if key in _cache:
        return _cache[key]

    svg_text = _load_recolored_svg(name, hex_color)
    if svg_text is None:
        return QIcon()

    if QGuiApplication.instance() is None:
        return QIcon()

    screen = QGuiApplication.primaryScreen()
    dpr = screen.devicePixelRatio() if screen is not None else 1.0
    px_size = max(1, int(size * dpr))

    renderer = QSvgRenderer(QByteArray(svg_text.encode("utf-8")))
    if not renderer.isValid():
        return QIcon()

    image = QImage(px_size, px_size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)

    painter = QPainter(image)
    try:
        renderer.render(painter)
    finally:
        painter.end()

    pixmap = QPixmap.fromImage(image)
    pixmap.setDevicePixelRatio(dpr)
    icon = QIcon(pixmap)
    _cache[key] = icon
    return icon


def clear_cache() -> None:
    """Clear rendered icons after a runtime theme switch."""
    _cache.clear()
