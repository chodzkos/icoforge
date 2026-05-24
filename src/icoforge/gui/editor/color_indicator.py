"""Color indicator widget showing foreground/background colors."""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import QColorDialog, QWidget

# Geometry constants (all in widget-local coordinates)
_SQ = 36  # square side
_OFF = 12  # background square offset (right + down)

_BG_RECT = QRect(_OFF, _OFF, _SQ, _SQ)  # background (bottom layer)
_FG_RECT = QRect(0, 0, _SQ, _SQ)  # foreground (top layer)
_SWAP_RECT = QRect(_SQ + _OFF + 2, 0, 13, 13)  # ⇄ button
_DEF_RECT = QRect(0, _SQ + _OFF + 2, 13, 13)  # D button
_HEX_Y = _SQ + _OFF + 3  # y-start of hex label row
_WIDGET_W = _SQ + _OFF + 18
_WIDGET_H = _SQ + _OFF + 20


def _checkerboard(painter: QPainter, rect: QRect, sq: int = 5) -> None:
    """Fill *rect* with a checkerboard pattern."""
    c1 = QColor(195, 195, 195)
    c2 = QColor(155, 155, 155)
    for ry in range(rect.y(), rect.y() + rect.height(), sq):
        for rx in range(rect.x(), rect.x() + rect.width(), sq):
            clipped = QRect(rx, ry, sq, sq).intersected(rect)
            color = c1 if (((rx - rect.x()) // sq) + ((ry - rect.y()) // sq)) % 2 == 0 else c2
            painter.fillRect(clipped, color)


class ColorIndicator(QWidget):
    """Foreground/background color selector inspired by Photoshop's tool palette.

    Layout::

        [FG]
           [BG]   ⇄
        D
        #RRGGBB
    """

    color_changed = Signal(QColor, bool)  # (color, is_foreground)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._fg = QColor(0, 0, 0, 255)
        self._bg = QColor(255, 255, 255, 255)
        self.setFixedSize(_WIDGET_W, _WIDGET_H)
        self.setToolTip(
            "Foreground/background color\n"
            "Click foreground or background square to change\n"
            "⇄ = swap  |  D = reset to black/white  |  X = swap shortcut"
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
        """Set the foreground color and emit color_changed."""
        if color == self._fg:
            return
        self._fg = QColor(color)
        self.update()
        self.color_changed.emit(QColor(self._fg), True)

    def set_background_color(self, color: QColor) -> None:
        """Set the background color and emit color_changed."""
        if color == self._bg:
            return
        self._bg = QColor(color)
        self.update()
        self.color_changed.emit(QColor(self._bg), False)

    def swap_colors(self) -> None:
        """Swap foreground and background colors."""
        self._fg, self._bg = self._bg, self._fg
        self.update()
        self.color_changed.emit(QColor(self._fg), True)

    def reset_to_default(self) -> None:
        """Reset to black foreground, white background."""
        self._fg = QColor(0, 0, 0, 255)
        self._bg = QColor(255, 255, 255, 255)
        self.update()
        self.color_changed.emit(QColor(self._fg), True)

    # ------------------------------------------------------------------
    # Painting
    # ------------------------------------------------------------------

    def paintEvent(self, event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        # --- background square (drawn first, underneath) ---
        _checkerboard(painter, _BG_RECT)
        painter.fillRect(_BG_RECT, self._bg)
        painter.setPen(QPen(QColor(70, 70, 70), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(_BG_RECT)

        # --- foreground square (on top) ---
        _checkerboard(painter, _FG_RECT)
        painter.fillRect(_FG_RECT, self._fg)
        painter.setPen(QPen(QColor(70, 70, 70), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(_FG_RECT)

        # --- swap button ---
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        painter.setBrush(QBrush(QColor(230, 230, 230)))
        painter.drawRect(_SWAP_RECT)
        painter.setPen(Qt.GlobalColor.black)
        painter.drawText(_SWAP_RECT, Qt.AlignmentFlag.AlignCenter, "⇄")  # ⇄

        # --- default button ---
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        painter.setBrush(QBrush(QColor(230, 230, 230)))
        painter.drawRect(_DEF_RECT)
        painter.setPen(Qt.GlobalColor.black)
        painter.drawText(_DEF_RECT, Qt.AlignmentFlag.AlignCenter, "D")

        # --- hex label ---
        painter.setPen(Qt.GlobalColor.black)
        hex_rect = QRect(0, _HEX_Y, _WIDGET_W, _WIDGET_H - _HEX_Y)
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
            # FG checked before BG because FG is drawn on top
            self._pick_color(foreground=True)
        elif _BG_RECT.contains(pos):
            self._pick_color(foreground=False)

        event.accept()

    def _pick_color(self, *, foreground: bool) -> None:
        current = self._fg if foreground else self._bg
        label = "Kolor pierwszego planu" if foreground else "Kolor tła"
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

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _hex(self) -> str:
        r, g, b, a = self._fg.red(), self._fg.green(), self._fg.blue(), self._fg.alpha()
        if a < 255:
            return f"#{r:02X}{g:02X}{b:02X}{a:02X}"
        return f"#{r:02X}{g:02X}{b:02X}"
