"""Canvas for pixel editing with zoom, pan, and grid overlay."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import Image
from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QWidget,
)

if TYPE_CHECKING:
    from icoforge.gui.editor.tools import Tool

ZOOM_LEVELS: list[float] = [1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0]


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
        pen.setWidth(0)
        painter.setPen(pen)

        for x in range(0, self.width + 1):
            painter.drawLine(x, 0, x, self.height)

        for y in range(0, self.height + 1):
            painter.drawLine(0, y, self.width, y)


class NavigationOverlay(QWidget):
    """Thumbnail navigator shown when zoomed into a large image."""

    scroll_requested = Signal(float, float)

    SIZE = 120

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self._thumbnail: QPixmap | None = None
        self._thumb_w = 0
        self._thumb_h = 0
        self._thumb_ox = 0
        self._thumb_oy = 0
        self._view_rect_norm: QRectF | None = None
        self._dragging = False
        self.hide()

    def update_state(self, image: Image.Image | None, view_rect_norm: QRectF | None) -> None:
        """Update thumbnail image and visible-area rect (normalized 0-1)."""
        if image is None:
            self.hide()
            return

        thumb_img = image.copy()
        thumb_img.thumbnail((self.SIZE, self.SIZE), Image.Resampling.NEAREST)
        w, h = thumb_img.size
        data = thumb_img.convert("RGBA").tobytes()
        qimg = QImage(data, w, h, 4 * w, QImage.Format.Format_RGBA8888)
        self._thumbnail = QPixmap.fromImage(qimg)
        self._thumb_w = w
        self._thumb_h = h
        self._thumb_ox = (self.SIZE - w) // 2
        self._thumb_oy = (self.SIZE - h) // 2
        self._view_rect_norm = view_rect_norm

        vr = view_rect_norm
        visible = vr is None or (vr.width() >= 0.99 and vr.height() >= 0.99)
        if visible:
            self.hide()
        else:
            self.show()
        self.update()

    def paintEvent(self, event: object) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(30, 30, 30, 210))

        if self._thumbnail:
            painter.drawPixmap(self._thumb_ox, self._thumb_oy, self._thumbnail)

            if self._view_rect_norm and self._thumb_w and self._thumb_h:
                vr = self._view_rect_norm
                rx = int(self._thumb_ox + vr.x() * self._thumb_w)
                ry = int(self._thumb_oy + vr.y() * self._thumb_h)
                rw = max(2, int(vr.width() * self._thumb_w))
                rh = max(2, int(vr.height() * self._thumb_h))
                pen = QPen(QColor(255, 60, 60), 1)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(rx, ry, rw, rh)

        painter.end()

    def mousePressEvent(self, event: object) -> None:
        from PySide6.QtGui import QMouseEvent

        if isinstance(event, QMouseEvent) and event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._emit_scroll(event.pos())
            event.accept()

    def mouseMoveEvent(self, event: object) -> None:
        from PySide6.QtGui import QMouseEvent

        if isinstance(event, QMouseEvent) and self._dragging:
            self._emit_scroll(event.pos())
            event.accept()

    def mouseReleaseEvent(self, event: object) -> None:
        from PySide6.QtGui import QMouseEvent

        if isinstance(event, QMouseEvent):
            self._dragging = False
            event.accept()

    def _emit_scroll(self, pos: QPoint) -> None:
        if not self._thumb_w or not self._thumb_h:
            return
        nx = (pos.x() - self._thumb_ox) / self._thumb_w
        ny = (pos.y() - self._thumb_oy) / self._thumb_h
        nx = max(0.0, min(1.0, nx))
        ny = max(0.0, min(1.0, ny))
        self.scroll_requested.emit(nx, ny)


class EditorCanvas(QGraphicsView):
    """Canvas for editing pixel art with zoom, pan, and grid."""

    zoom_changed = Signal(float)
    pixel_hovered = Signal(int, int)
    color_sampled = Signal(int, int, int, int)  # r, g, b, a — emitted by eyedropper

    MIN_ZOOM = 1.0
    MAX_ZOOM = 64.0

    def __init__(self, parent: object | None = None) -> None:
        super().__init__(parent)
        self.scene_obj = QGraphicsScene()
        self.setScene(self.scene_obj)

        self._current_image: Image.Image | None = None
        self._pixmap_item: QGraphicsPixmapItem | None = None
        self._checkerboard: CheckerboardBackground | None = None
        self._grid: GridOverlay | None = None
        self._zoom_level = 1.0
        self._pan_start: QPoint | None = None
        self._current_tool: Tool | None = None

        self.setBackgroundBrush(QBrush(QColor(50, 50, 50)))
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)

        self._nav = NavigationOverlay(self.viewport())
        self._nav.scroll_requested.connect(self._on_nav_scroll)

    # ------------------------------------------------------------------
    # Image loading
    # ------------------------------------------------------------------

    def load_image(self, image: Image.Image, auto_zoom: bool = True) -> None:
        """Load a new image to the canvas."""
        self._current_image = image.copy()

        self.scene_obj.clear()
        self._pixmap_item = None
        self._checkerboard = None
        self._grid = None

        width, height = image.size
        self._checkerboard = CheckerboardBackground(width, height)
        self.scene_obj.addItem(self._checkerboard)

        rgb_image = image.convert("RGBA")
        data = rgb_image.tobytes()
        qimage = QImage(data, width, height, 4 * width, QImage.Format.Format_RGBA8888)
        pixmap = QPixmap.fromImage(qimage)

        self._pixmap_item = self.scene_obj.addPixmap(pixmap)
        self._pixmap_item.setZValue(50)

        self._grid = GridOverlay(width, height)
        self.scene_obj.addItem(self._grid)

        if auto_zoom:
            self._auto_zoom()
        else:
            self.fit_to_window()

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
        self._pixmap_item.setPixmap(QPixmap.fromImage(qimage))

    # ------------------------------------------------------------------
    # Zoom API
    # ------------------------------------------------------------------

    def _apply_zoom(self, zoom: float) -> None:
        """Apply a specific zoom level."""
        self._zoom_level = max(self.MIN_ZOOM, min(zoom, self.MAX_ZOOM))
        self.resetTransform()
        self.scale(self._zoom_level, self._zoom_level)
        self._update_grid_visibility()
        self._update_nav_overlay()
        self.zoom_changed.emit(self._zoom_level)

    def zoom_in(self) -> None:
        """Step up to the next preset zoom level."""
        for level in ZOOM_LEVELS:
            if level > self._zoom_level * 1.05:
                self._apply_zoom(level)
                return

    def zoom_out(self) -> None:
        """Step down to the previous preset zoom level."""
        for level in reversed(ZOOM_LEVELS):
            if level < self._zoom_level * 0.95:
                self._apply_zoom(level)
                return

    def fit_to_window(self) -> None:
        """Fit the whole image into the visible viewport."""
        if self._current_image is None:
            return
        self.fitInView(
            self.scene_obj.itemsBoundingRect(),
            Qt.AspectRatioMode.KeepAspectRatio,
        )
        self._zoom_level = self.transform().m11()
        self._update_grid_visibility()
        self._update_nav_overlay()
        self.zoom_changed.emit(self._zoom_level)

    def zoom_1to1(self) -> None:
        """Set zoom to 1:1 (one image pixel = one screen pixel)."""
        self._apply_zoom(1.0)

    def get_fit_zoom(self) -> float:
        """Return the zoom level that would fit the image in the viewport."""
        if self._current_image is None:
            return 1.0
        w, h = self._current_image.size
        vw = self.viewport().width() or 400
        vh = self.viewport().height() or 400
        return min(vw / w, vh / h)

    def _auto_zoom(self) -> None:
        """Choose an appropriate initial zoom level for the loaded image."""
        if self._current_image is None:
            return
        w, h = self._current_image.size
        size = max(w, h)
        fit = self.get_fit_zoom()

        if size >= 128:
            self.fit_to_window()
        elif size >= 48:
            target = min(4.0, fit)
            target = max(1.0, target)
            self._apply_zoom(target)
        else:
            # 16x16, 32x32: at least 8x but cap at fit
            target = max(8.0, min(16.0, fit))
            self._apply_zoom(target)

    # ------------------------------------------------------------------
    # Navigation overlay
    # ------------------------------------------------------------------

    def _update_nav_overlay(self) -> None:
        """Refresh the navigation overlay position and content."""
        if self._current_image is None:
            self._nav.update_state(None, None)
            return

        w, h = self._current_image.size
        scene_rect = self.sceneRect()
        if scene_rect.width() == 0 or scene_rect.height() == 0:
            return

        visible = self.mapToScene(self.viewport().rect()).boundingRect()
        nx = (visible.x() - scene_rect.x()) / scene_rect.width()
        ny = (visible.y() - scene_rect.y()) / scene_rect.height()
        nw = visible.width() / scene_rect.width()
        nh = visible.height() / scene_rect.height()
        view_rect_norm = QRectF(nx, ny, nw, nh)

        only_large = max(w, h) >= 64
        if only_large:
            self._nav.update_state(self._current_image, view_rect_norm)
        else:
            self._nav.update_state(None, None)

        self._reposition_nav()

    def _reposition_nav(self) -> None:
        """Place nav overlay in the bottom-right corner of the viewport."""
        vp = self.viewport()
        margin = 6
        x = vp.width() - self._nav.width() - margin
        y = vp.height() - self._nav.height() - margin
        self._nav.move(max(0, x), max(0, y))

    def _on_nav_scroll(self, nx: float, ny: float) -> None:
        """Handle scroll request from navigation overlay."""
        sr = self.sceneRect()
        scene_x = sr.x() + nx * sr.width()
        scene_y = sr.y() + ny * sr.height()
        self.centerOn(QPointF(scene_x, scene_y))
        self._update_nav_overlay()

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def resizeEvent(self, event: object) -> None:
        super().resizeEvent(event)  # type: ignore[arg-type]
        self._reposition_nav()

    def scrollContentsBy(self, dx: int, dy: int) -> None:
        super().scrollContentsBy(dx, dy)
        self._update_nav_overlay()

    def wheelEvent(self, event: object) -> None:
        """Handle Ctrl+wheel for zoom."""
        from PySide6.QtGui import QWheelEvent

        if not isinstance(event, QWheelEvent):
            super().wheelEvent(event)
            return

        if not (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            super().wheelEvent(event)
            return

        delta = event.angleDelta().y()
        if delta > 0:
            self.zoom_in()
        else:
            self.zoom_out()
        event.accept()

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
            px, py = int(scene_pos.x()), int(scene_pos.y())
            self._current_tool.on_press(px, py)
            self._refresh_pixmap()
            self._maybe_emit_color_sampled()
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
            self._update_nav_overlay()
            event.accept()
        elif event.buttons() & Qt.MouseButton.LeftButton and self._current_tool is not None:
            scene_pos = self.mapToScene(event.pos())
            px, py = int(scene_pos.x()), int(scene_pos.y())
            self._current_tool.on_move(px, py)
            self._refresh_pixmap()
            self._maybe_emit_color_sampled()
            event.accept()
        else:
            scene_pos = self.mapToScene(event.pos())
            self.pixel_hovered.emit(int(scene_pos.x()), int(scene_pos.y()))
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
            px, py = int(scene_pos.x()), int(scene_pos.y())
            self._current_tool.on_release(px, py)
            self._refresh_pixmap()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _maybe_emit_color_sampled(self) -> None:
        """Emit color_sampled if the current tool has a picked_color attribute."""
        picked = getattr(self._current_tool, "picked_color", None)
        if picked is not None:
            r, g, b, a = picked
            self.color_sampled.emit(r, g, b, a)

    def _update_grid_visibility(self) -> None:
        """Show/hide grid based on zoom level."""
        if self._grid:
            self._grid.setVisible(self._zoom_level >= 8.0)

    def get_zoom_percentage(self) -> int:
        """Get current zoom as percentage."""
        return int(self._zoom_level * 100)
