"""Canvas for pixel editing with zoom, pan, and grid overlay."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import Image
from PySide6.QtCore import QPointF, QRect, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
)

if TYPE_CHECKING:
    from icoforge.gui.editor.tools import Tool


def _view_to_pixel_coords(pos: QPointF, zoom: float) -> tuple[int, int]:
    """Convert view coordinates to pixel coordinates."""
    x = int(pos.x() / zoom)
    y = int(pos.y() / zoom)
    return x, y


class CheckerboardBackground(QGraphicsItem):
    """Checkerboard pattern for transparent pixels."""

    def __init__(self, width: int, height: int, square_size: int = 8) -> None:
        super().__init__()
        self.width = width
        self.height = height
        self.square_size = square_size
        self.setZValue(-1)

    def boundingRect(self) -> QRect:
        return QRect(0, 0, self.width, self.height)

    def paint(self, painter: QPainter, option: object, widget: object | None = None) -> None:
        """Draw checkerboard pattern."""
        color1 = QColor(200, 200, 200)
        color2 = QColor(220, 220, 220)

        for y in range(0, self.height, self.square_size):
            for x in range(0, self.width, self.square_size):
                if ((x // self.square_size) + (y // self.square_size)) % 2 == 0:
                    painter.fillRect(x, y, self.square_size, self.square_size, color1)
                else:
                    painter.fillRect(x, y, self.square_size, self.square_size, color2)


class GridOverlay(QGraphicsItem):
    """Grid overlay for pixel-level editing."""

    def __init__(self, width: int, height: int) -> None:
        super().__init__()
        self.width = width
        self.height = height
        self.setZValue(100)

    def boundingRect(self) -> QRect:
        return QRect(0, 0, self.width, self.height)

    def paint(self, painter: QPainter, option: object, widget: object | None = None) -> None:
        """Draw grid lines."""
        pen = QPen(QColor(150, 150, 150, 100))
        pen.setWidth(0)  # Cosmetic pen - always 1 pixel wide
        painter.setPen(pen)

        # Vertical lines
        for x in range(0, self.width + 1):
            painter.drawLine(x, 0, x, self.height)

        # Horizontal lines
        for y in range(0, self.height + 1):
            painter.drawLine(0, y, self.width, y)


class EditorCanvas(QGraphicsView):
    """Canvas for editing pixel art with zoom, pan, and grid."""

    zoom_changed = Signal(float)
    pixel_hovered = Signal(int, int)  # x, y coordinates

    MIN_ZOOM = 1.0
    MAX_ZOOM = 64.0

    def __init__(self, parent: object | None = None) -> None:
        super().__init__(parent)
        self.scene_obj = QGraphicsScene()
        self.setScene(self.scene_obj)

        # Canvas state
        self._current_image: Image.Image | None = None
        self._pixmap_item: QGraphicsPixmapItem | None = None
        self._checkerboard: CheckerboardBackground | None = None
        self._grid: GridOverlay | None = None
        self._zoom_level = 1.0
        self._pan_start = None
        self._current_tool: Tool | None = None

        # Appearance
        self.setBackgroundBrush(QBrush(QColor(50, 50, 50)))
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)

    def load_image(self, image: Image.Image) -> None:
        """Load a new image to the canvas.

        Args:
            image: PIL Image in RGBA mode.
        """
        # Store original image
        self._current_image = image.copy()

        # Clear scene
        self.scene_obj.clear()
        self._pixmap_item = None
        self._checkerboard = None
        self._grid = None

        # Add checkerboard background
        width, height = image.size
        self._checkerboard = CheckerboardBackground(width, height)
        self.scene_obj.addItem(self._checkerboard)

        # Convert PIL Image to QPixmap
        # PIL to QImage conversion
        rgb_image = image.convert("RGBA")
        data = rgb_image.tobytes()
        qimage = QImage(data, width, height, 4 * width, QImage.Format.Format_RGBA8888)
        pixmap = QPixmap.fromImage(qimage)

        # Add pixmap to scene
        self._pixmap_item = self.scene_obj.addPixmap(pixmap)
        self._pixmap_item.setZValue(50)

        # Add grid overlay
        self._grid = GridOverlay(width, height)
        self.scene_obj.addItem(self._grid)

        # Fit in view
        self.fitInView(
            self.scene_obj.itemsBoundingRect(),
            Qt.AspectRatioMode.KeepAspectRatio,
        )
        self._zoom_level = 1.0
        self.zoom_changed.emit(self._zoom_level)

    def get_current_image(self) -> Image.Image | None:
        """Get the current image being edited."""
        return self._current_image.copy() if self._current_image else None

    def set_tool(self, tool: Tool) -> None:
        """Set the active drawing tool."""
        self._current_tool = tool

    def _refresh_pixmap(self) -> None:
        """Refresh the displayed pixmap from the current image."""
        if self._current_image is None or self._pixmap_item is None:
            return
        rgb_image = self._current_image.convert("RGBA")
        data = rgb_image.tobytes()
        width, height = self._current_image.size
        qimage = QImage(data, width, height, 4 * width, QImage.Format.Format_RGBA8888)
        pixmap = QPixmap.fromImage(qimage)
        self._pixmap_item.setPixmap(pixmap)

    def wheelEvent(self, event: object) -> None:
        """Handle Ctrl+wheel for zoom."""
        from PySide6.QtGui import QWheelEvent

        if not isinstance(event, QWheelEvent):
            super().wheelEvent(event)
            return

        if not (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            super().wheelEvent(event)
            return

        # Zoom based on wheel delta
        delta = event.angleDelta().y()
        if delta > 0:
            # Zoom in
            self._zoom_level = min(self._zoom_level * 1.2, self.MAX_ZOOM)
        else:
            # Zoom out
            self._zoom_level = max(self._zoom_level / 1.2, self.MIN_ZOOM)

        # Apply zoom
        self.setTransform(self.transform().scale(1.0 / self.transform().m11(), 1.0))
        self.scale(self._zoom_level, self._zoom_level)

        # Update grid visibility
        self._update_grid_visibility()
        self.zoom_changed.emit(self._zoom_level)

    def mousePressEvent(self, event: object) -> None:
        """Handle mouse press for drawing or panning."""
        from PySide6.QtGui import QMouseEvent

        if not isinstance(event, QMouseEvent):
            super().mousePressEvent(event)
            return

        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_start = event.pos()
            event.accept()
        elif event.button() == Qt.MouseButton.LeftButton and self._current_tool is not None:
            scene_pos = self.mapToScene(event.pos())
            px, py = _view_to_pixel_coords(scene_pos, self._zoom_level)
            self._current_tool.on_press(px, py)
            self._refresh_pixmap()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: object) -> None:
        """Handle mouse move for drawing or panning."""
        from PySide6.QtGui import QMouseEvent

        if not isinstance(event, QMouseEvent):
            super().mouseMoveEvent(event)
            return

        if self._pan_start is not None:
            delta = event.pos() - self._pan_start
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            self._pan_start = event.pos()
            event.accept()
        elif event.buttons() & Qt.MouseButton.LeftButton and self._current_tool is not None:
            scene_pos = self.mapToScene(event.pos())
            px, py = _view_to_pixel_coords(scene_pos, self._zoom_level)
            self._current_tool.on_move(px, py)
            self._refresh_pixmap()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: object) -> None:
        """Handle mouse release."""
        from PySide6.QtGui import QMouseEvent

        if not isinstance(event, QMouseEvent):
            super().mouseReleaseEvent(event)
            return

        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_start = None
            event.accept()
        elif event.button() == Qt.MouseButton.LeftButton and self._current_tool is not None:
            scene_pos = self.mapToScene(event.pos())
            px, py = _view_to_pixel_coords(scene_pos, self._zoom_level)
            self._current_tool.on_release(px, py)
            self._refresh_pixmap()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def _update_grid_visibility(self) -> None:
        """Show/hide grid based on zoom level."""
        if self._grid:
            self._grid.setVisible(self._zoom_level >= 8.0)

    def get_zoom_percentage(self) -> int:
        """Get current zoom as percentage."""
        return int(self._zoom_level * 100)
