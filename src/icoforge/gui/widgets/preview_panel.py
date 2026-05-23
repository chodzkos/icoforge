"""Scrollable grid of per-size ICO thumbnails rendered in a background thread."""

from __future__ import annotations

from pathlib import Path

from PIL import Image
from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from icoforge.core.converter import render_frames
from icoforge.core.models import IcoConfig

_GRID_COLS = 4


# ---------------------------------------------------------------------------
# PIL → QImage helper
# ---------------------------------------------------------------------------


def _pil_to_qimage(img: Image.Image) -> QImage:
    """Convert a PIL RGBA image to a QImage that owns its own data."""
    rgba = img.convert("RGBA")
    data = rgba.tobytes("raw", "RGBA")
    qimg = QImage(data, rgba.width, rgba.height, QImage.Format.Format_RGBA8888)
    return qimg.copy()  # detach from Python buffer before `data` is freed


# ---------------------------------------------------------------------------
# Background render worker
# ---------------------------------------------------------------------------


class _RenderDone:
    """Typed payload emitted when a render task completes."""

    __slots__ = ("frames",)

    def __init__(self, frames: list[tuple[int, QImage]]) -> None:
        self.frames = frames


class _RenderSignals(QObject):
    finished = Signal(object)  # _RenderDone
    error = Signal(str)
    done = Signal()


class _RenderTask(QRunnable):
    def __init__(self, source_path: Path, config: IcoConfig) -> None:
        super().__init__()
        self.signals = _RenderSignals()
        self._source = source_path
        self._config = config
        self._cancelled = False
        self.setAutoDelete(False)

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            pil_frames = render_frames(self._source, self._config)
            if self._cancelled:
                return
            results: list[tuple[int, QImage]] = []
            for spec, frame in zip(self._config.sizes, pil_frames, strict=False):
                if self._cancelled:
                    return
                results.append((spec.width, _pil_to_qimage(frame)))
            self.signals.finished.emit(_RenderDone(results))
        except Exception as exc:
            if not self._cancelled:
                self.signals.error.emit(str(exc))
        finally:
            self.signals.done.emit()


# ---------------------------------------------------------------------------
# Widget
# ---------------------------------------------------------------------------


class PreviewPanel(QScrollArea):
    """Displays a thumbnail grid; updates asynchronously via QThreadPool."""

    render_error = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)

        self._container = QWidget()
        self._grid = QGridLayout(self._container)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._grid.setSpacing(12)
        self.setWidget(self._container)

        self._current_task: _RenderTask | None = None
        self._live_tasks: set[_RenderTask] = set()
        self._show_placeholder()

    def update_preview(self, source_path: Path, config: IcoConfig) -> None:
        """Trigger a background re-render for *source_path* with *config*."""
        if self._current_task is not None:
            self._current_task.cancel()

        task = _RenderTask(source_path, config)
        task.signals.finished.connect(self._on_render_done)
        task.signals.error.connect(self._on_render_error)
        task.signals.done.connect(lambda t=task: self._live_tasks.discard(t))
        self._live_tasks.add(task)
        self._current_task = task
        QThreadPool.globalInstance().start(task)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _show_placeholder(self) -> None:
        self._clear_grid()
        lbl = QLabel("Załaduj plik, aby zobaczyć podgląd")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setEnabled(False)
        self._grid.addWidget(lbl, 0, 0)

    def _clear_grid(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()

    def _on_render_done(self, payload: object) -> None:
        if not isinstance(payload, _RenderDone):
            return
        self._clear_grid()
        for i, (size, qimage) in enumerate(payload.frames):
            pixmap = QPixmap.fromImage(qimage)

            pix_lbl = QLabel()
            pix_lbl.setPixmap(pixmap)
            pix_lbl.setFixedSize(size, size)
            pix_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

            txt_lbl = QLabel(f"{size}x{size}")
            txt_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

            cell = QWidget()
            cell.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            vbox = QVBoxLayout(cell)
            vbox.setContentsMargins(4, 4, 4, 4)
            vbox.setSpacing(2)
            vbox.addWidget(pix_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
            vbox.addWidget(txt_lbl)

            row, col = divmod(i, _GRID_COLS)
            self._grid.addWidget(cell, row, col)

    def _on_render_error(self, message: str) -> None:
        self.render_error.emit(message)
