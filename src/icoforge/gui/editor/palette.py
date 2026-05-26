"""Color palette widget: FG/BG selector + 32-colour swatch grid."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QColorDialog,
    QFileDialog,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# Default 32-colour palette
# ---------------------------------------------------------------------------

_DEFAULT_PALETTE: list[tuple[int, int, int, int]] = [
    # Row 1 - grayscale + basic warm
    (0, 0, 0, 255),
    (64, 64, 64, 255),
    (128, 128, 128, 255),
    (192, 192, 192, 255),
    (255, 255, 255, 255),
    (128, 0, 0, 255),
    (255, 0, 0, 255),
    (255, 128, 0, 255),
    # Row 2 - warm / green
    (255, 200, 0, 255),
    (255, 255, 0, 255),
    (128, 64, 0, 255),
    (0, 128, 0, 255),
    (0, 255, 0, 255),
    (0, 128, 64, 255),
    (0, 255, 128, 255),
    (0, 128, 128, 255),
    # Row 3 - cool / blue / purple
    (0, 255, 255, 255),
    (0, 64, 128, 255),
    (0, 0, 255, 255),
    (0, 0, 128, 255),
    (128, 0, 255, 255),
    (255, 0, 255, 255),
    (255, 128, 192, 255),
    (255, 200, 200, 255),
    # Row 4 - pastels + semi-transparent + transparent
    (200, 255, 200, 255),
    (200, 200, 255, 255),
    (255, 200, 100, 255),
    (100, 200, 255, 255),
    (200, 100, 255, 255),
    (0, 0, 0, 128),
    (128, 128, 128, 128),
    (0, 0, 0, 0),
]

# ---------------------------------------------------------------------------
# Geometry - FG/BG indicator section
# ---------------------------------------------------------------------------

_SQ = 36  # square side
_OFF = 12  # BG square offset (right + down)
_BG_RECT = QRect(_OFF, _OFF, _SQ, _SQ)
_FG_RECT = QRect(0, 0, _SQ, _SQ)
_SWAP_RECT = QRect(_SQ + _OFF + 2, 0, 13, 13)
_DEF_RECT = QRect(0, _SQ + _OFF + 2, 13, 13)
_HEX_Y = _SQ + _OFF + 3
_BAR_W = _SQ + _OFF + 18
_BAR_H = _SQ + _OFF + 20

# Geometry - colour grid
_COLS = 8
_ROWS = 4
_CELL = 18  # px per cell


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _checkerboard(painter: QPainter, rect: QRect, sq: int = 4) -> None:
    c1 = QColor(195, 195, 195)
    c2 = QColor(155, 155, 155)
    for ry in range(rect.y(), rect.y() + rect.height(), sq):
        for rx in range(rect.x(), rect.x() + rect.width(), sq):
            clipped = QRect(rx, ry, sq, sq).intersected(rect)
            color = c1 if (((rx - rect.x()) // sq) + ((ry - rect.y()) // sq)) % 2 == 0 else c2
            painter.fillRect(clipped, color)


# ---------------------------------------------------------------------------
# _FGBGBar - foreground / background indicator (former ColorIndicator)
# ---------------------------------------------------------------------------


class _FGBGBar(QWidget):
    """Small widget showing FG/BG colour squares with swap and reset buttons."""

    color_changed = Signal(QColor, bool)  # (colour, is_foreground)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._fg = QColor(0, 0, 0, 255)
        self._bg = QColor(255, 255, 255, 255)
        self.setFixedSize(_BAR_W, _BAR_H)
        self.setToolTip(
            self.tr(
                "Kolor pierwszego/drugiego planu\nKliknij kwadrat aby zmienić · ⇄ zamień · D reset"
            )
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def foreground_color(self) -> QColor:
        return QColor(self._fg)

    @property
    def background_color(self) -> QColor:
        return QColor(self._bg)

    def set_foreground_color(self, color: QColor) -> None:
        if color == self._fg:
            return
        self._fg = QColor(color)
        self.update()
        self.color_changed.emit(QColor(self._fg), True)

    def set_background_color(self, color: QColor) -> None:
        if color == self._bg:
            return
        self._bg = QColor(color)
        self.update()
        self.color_changed.emit(QColor(self._bg), False)

    def swap_colors(self) -> None:
        self._fg, self._bg = self._bg, self._fg
        self.update()
        self.color_changed.emit(QColor(self._fg), True)

    def reset_to_default(self) -> None:
        self._fg = QColor(0, 0, 0, 255)
        self._bg = QColor(255, 255, 255, 255)
        self.update()
        self.color_changed.emit(QColor(self._fg), True)

    def _hex(self) -> str:
        r, g, b, a = self._fg.red(), self._fg.green(), self._fg.blue(), self._fg.alpha()
        if a < 255:
            return f"#{r:02X}{g:02X}{b:02X}{a:02X}"
        return f"#{r:02X}{g:02X}{b:02X}"

    # ------------------------------------------------------------------
    # Painting
    # ------------------------------------------------------------------

    def paintEvent(self, event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        _checkerboard(painter, _BG_RECT)
        painter.fillRect(_BG_RECT, self._bg)
        painter.setPen(QPen(QColor(70, 70, 70), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(_BG_RECT)

        _checkerboard(painter, _FG_RECT)
        painter.fillRect(_FG_RECT, self._fg)
        painter.setPen(QPen(QColor(70, 70, 70), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(_FG_RECT)

        painter.setPen(QPen(QColor(100, 100, 100), 1))
        painter.setBrush(QBrush(QColor(230, 230, 230)))
        painter.drawRect(_SWAP_RECT)
        painter.setPen(Qt.GlobalColor.black)
        painter.drawText(_SWAP_RECT, Qt.AlignmentFlag.AlignCenter, "⇄")

        painter.setPen(QPen(QColor(100, 100, 100), 1))
        painter.setBrush(QBrush(QColor(230, 230, 230)))
        painter.drawRect(_DEF_RECT)
        painter.setPen(Qt.GlobalColor.black)
        painter.drawText(_DEF_RECT, Qt.AlignmentFlag.AlignCenter, "D")

        painter.setPen(Qt.GlobalColor.black)
        hex_rect = QRect(0, _HEX_Y, _BAR_W, _BAR_H - _HEX_Y)
        painter.drawText(
            hex_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, self._hex()
        )
        painter.end()

    # ------------------------------------------------------------------
    # Interaction
    # ------------------------------------------------------------------

    def mousePressEvent(self, event: object) -> None:
        from PySide6.QtGui import QMouseEvent

        if not isinstance(event, QMouseEvent) or event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)  # type: ignore[arg-type]
            return

        pos: QPoint = event.pos()
        if _SWAP_RECT.contains(pos):
            self.swap_colors()
        elif _DEF_RECT.contains(pos):
            self.reset_to_default()
        elif _FG_RECT.contains(pos):
            self._pick_color(foreground=True)
        elif _BG_RECT.contains(pos):
            self._pick_color(foreground=False)
        event.accept()

    def _pick_color(self, *, foreground: bool) -> None:
        current = self._fg if foreground else self._bg
        label = self.tr("Kolor pierwszego planu") if foreground else self.tr("Kolor tła")
        color = QColorDialog.getColor(
            current,
            self,
            label,
            QColorDialog.ColorDialogOption.ShowAlphaChannel,
        )
        if color.isValid():
            if foreground:
                self.set_foreground_color(color)
            else:
                self.set_background_color(color)


# ---------------------------------------------------------------------------
# _ColorGrid - 8 x 4 editable colour swatches
# ---------------------------------------------------------------------------


class _ColorGrid(QWidget):
    """Compact grid of 32 clickable colour swatches."""

    color_set_fg = Signal(tuple)  # left-click  → (r, g, b, a)
    color_set_bg = Signal(tuple)  # middle-click / context menu
    color_edited = Signal(int, tuple)  # double-click/edit → (index, new_rgba)

    def __init__(
        self,
        colors: list[tuple[int, int, int, int]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._colors: list[tuple[int, int, int, int]] = self._normalise(colors)
        self.setFixedSize(_COLS * _CELL + 2, _ROWS * _CELL + 2)
        self._hovered = -1
        self.setMouseTracking(True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def colors(self) -> list[tuple[int, int, int, int]]:
        return list(self._colors)

    def set_colors(self, colors: list[tuple[int, int, int, int]]) -> None:
        self._colors = self._normalise(colors)
        self.update()

    # ------------------------------------------------------------------
    # Geometry helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise(colors: list[tuple[int, int, int, int]]) -> list[tuple[int, int, int, int]]:
        result = list(colors)[: _COLS * _ROWS]
        while len(result) < _COLS * _ROWS:
            result.append((0, 0, 0, 255))
        return result

    def _cell_at(self, pos: QPoint) -> int:
        x, y = pos.x() - 1, pos.y() - 1
        if x < 0 or y < 0:
            return -1
        col, row = x // _CELL, y // _CELL
        if col >= _COLS or row >= _ROWS:
            return -1
        return row * _COLS + col

    def _cell_rect(self, idx: int) -> QRect:
        row, col = divmod(idx, _COLS)
        return QRect(1 + col * _CELL, 1 + row * _CELL, _CELL, _CELL)

    # ------------------------------------------------------------------
    # Painting
    # ------------------------------------------------------------------

    def paintEvent(self, event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.fillRect(self.rect(), QColor(60, 60, 60))

        for i, color in enumerate(self._colors):
            r, g, b, a = color
            rect = self._cell_rect(i)
            if a < 255:
                _checkerboard(painter, rect)
            painter.fillRect(rect, QColor(r, g, b, a))
            if i == self._hovered:
                painter.setPen(QPen(QColor(255, 255, 255), 2))
            else:
                painter.setPen(QPen(QColor(40, 40, 40), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)

        painter.end()

    # ------------------------------------------------------------------
    # Mouse events
    # ------------------------------------------------------------------

    def mouseMoveEvent(self, event: object) -> None:
        from PySide6.QtGui import QMouseEvent

        if isinstance(event, QMouseEvent):
            idx = self._cell_at(event.pos())
            if idx != self._hovered:
                self._hovered = idx
                self.update()

    def leaveEvent(self, event: object) -> None:
        self._hovered = -1
        self.update()

    def mousePressEvent(self, event: object) -> None:
        from PySide6.QtGui import QMouseEvent

        if not isinstance(event, QMouseEvent):
            return
        idx = self._cell_at(event.pos())
        if idx < 0:
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self.color_set_fg.emit(self._colors[idx])
            event.accept()
        elif event.button() == Qt.MouseButton.MiddleButton:
            self.color_set_bg.emit(self._colors[idx])
            event.accept()

    def mouseDoubleClickEvent(self, event: object) -> None:
        from PySide6.QtGui import QMouseEvent

        if not isinstance(event, QMouseEvent) or event.button() != Qt.MouseButton.LeftButton:
            return
        idx = self._cell_at(event.pos())
        if idx >= 0:
            self._edit_color(idx)
            event.accept()

    def contextMenuEvent(self, event: object) -> None:
        from PySide6.QtGui import QContextMenuEvent

        if not isinstance(event, QContextMenuEvent):
            return
        idx = self._cell_at(event.pos())
        if idx < 0:
            return
        menu = QMenu(self)
        fg_act = menu.addAction(self.tr("Ustaw jako kolor podstawowy"))
        bg_act = menu.addAction(self.tr("Ustaw jako kolor zapasowy"))
        menu.addSeparator()
        edit_act = menu.addAction(self.tr("Edytuj kolor…"))

        chosen = menu.exec(event.globalPos())
        if chosen is fg_act:
            self.color_set_fg.emit(self._colors[idx])
        elif chosen is bg_act:
            self.color_set_bg.emit(self._colors[idx])
        elif chosen is edit_act:
            self._edit_color(idx)

    def _edit_color(self, idx: int) -> None:
        r, g, b, a = self._colors[idx]
        new_color = QColorDialog.getColor(
            QColor(r, g, b, a),
            self,
            self.tr("Edytuj kolor palety"),
            QColorDialog.ColorDialogOption.ShowAlphaChannel,
        )
        if new_color.isValid():
            self._colors[idx] = (
                new_color.red(),
                new_color.green(),
                new_color.blue(),
                new_color.alpha(),
            )
            self.color_edited.emit(idx, self._colors[idx])
            self.update()


# ---------------------------------------------------------------------------
# PaletteWidget - public API
# ---------------------------------------------------------------------------


class PaletteWidget(QWidget):
    """FG/BG colour selector combined with a 32-colour editable swatch grid.

    Public interface is a superset of the former ColorIndicator:
    - ``color_changed(QColor, bool)`` signal
    - ``foreground_color`` / ``background_color`` properties
    - ``set_foreground_color`` / ``set_background_color`` / ``swap_colors``
    - ``reset_to_default``
    - ``_hex()``

    Additionally:
    - ``set_colors`` / ``get_colors`` - manage the swatch grid
    - ``save_palette`` / ``load_palette`` - JSON persistence
    - ``extract_requested`` signal - emitted by the "extract from image" button
    """

    color_changed = Signal(QColor, bool)  # (colour, is_foreground)
    extract_requested = Signal()  # emitted when user clicks "Extract from image"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)

        self._fgbg = _FGBGBar()
        self._fgbg.color_changed.connect(self.color_changed)
        layout.addWidget(self._fgbg, alignment=Qt.AlignmentFlag.AlignHCenter)

        self._grid = _ColorGrid(list(_DEFAULT_PALETTE))
        self._grid.color_set_fg.connect(self._on_grid_set_fg)
        self._grid.color_set_bg.connect(self._on_grid_set_bg)
        layout.addWidget(self._grid, alignment=Qt.AlignmentFlag.AlignHCenter)

        extract_btn = QPushButton(self.tr("Pobierz paletę z obrazu"))
        extract_btn.clicked.connect(self._on_extract_clicked)
        layout.addWidget(extract_btn)

        self._menu_btn = QPushButton(self.tr("Paleta ▾"))
        self._menu_btn.clicked.connect(self._show_palette_menu)
        layout.addWidget(self._menu_btn)

    # ------------------------------------------------------------------
    # FG/BG API (same interface as former ColorIndicator)
    # ------------------------------------------------------------------

    @property
    def foreground_color(self) -> QColor:
        return self._fgbg.foreground_color

    @property
    def background_color(self) -> QColor:
        return self._fgbg.background_color

    def set_foreground_color(self, color: QColor) -> None:
        self._fgbg.set_foreground_color(color)

    def set_background_color(self, color: QColor) -> None:
        self._fgbg.set_background_color(color)

    def swap_colors(self) -> None:
        self._fgbg.swap_colors()

    def reset_to_default(self) -> None:
        self._fgbg.reset_to_default()

    def _hex(self) -> str:
        return self._fgbg._hex()

    # ------------------------------------------------------------------
    # Palette (grid) API
    # ------------------------------------------------------------------

    def set_colors(self, colors: list[tuple[int, int, int, int]]) -> None:
        """Replace the 32-colour grid with *colors* (padded / truncated to 32)."""
        self._grid.set_colors(colors)

    def get_colors(self) -> list[tuple[int, int, int, int]]:
        """Return a copy of the current 32-colour palette."""
        return self._grid.colors

    def save_palette(self, path: Path) -> None:
        """Write the colour grid to a JSON file."""
        data = {"version": 1, "colors": [list(c) for c in self._grid.colors]}
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def load_palette(self, path: Path) -> None:
        """Load a previously saved JSON palette file."""
        raw = json.loads(path.read_text(encoding="utf-8"))
        colors: list[tuple[int, int, int, int]] = [
            (int(c[0]), int(c[1]), int(c[2]), int(c[3]))
            for c in raw.get("colors", [])
            if len(c) >= 4
        ]
        self.set_colors(colors)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_grid_set_fg(self, color: tuple) -> None:  # type: ignore[type-arg]
        r, g, b, a = color
        self._fgbg.set_foreground_color(QColor(r, g, b, a))

    def _on_grid_set_bg(self, color: tuple) -> None:  # type: ignore[type-arg]
        r, g, b, a = color
        self._fgbg.set_background_color(QColor(r, g, b, a))

    def _on_extract_clicked(self) -> None:
        self.extract_requested.emit()

    def _show_palette_menu(self) -> None:
        menu = QMenu(self)
        save_act = menu.addAction(self.tr("Zapisz paletę…"))
        load_act = menu.addAction(self.tr("Wczytaj paletę…"))
        menu.addSeparator()
        reset_act = menu.addAction(self.tr("Resetuj do domyślnej"))

        pos = self._menu_btn.mapToGlobal(self._menu_btn.rect().bottomLeft())
        chosen = menu.exec(pos)
        if chosen is save_act:
            self._on_save_palette()
        elif chosen is load_act:
            self._on_load_palette()
        elif chosen is reset_act:
            self._on_reset_palette()

    def _on_save_palette(self) -> None:
        path_str, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Zapisz paletę"),
            "",
            self.tr("JSON (*.json);;Wszystkie pliki (*)"),
        )
        if path_str:
            self.save_palette(Path(path_str))

    def _on_load_palette(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Wczytaj paletę"),
            "",
            self.tr("JSON (*.json);;Wszystkie pliki (*)"),
        )
        if path_str:
            self.load_palette(Path(path_str))

    def _on_reset_palette(self) -> None:
        self.set_colors(list(_DEFAULT_PALETTE))
