"""Drag-and-drop / click-to-browse source file selector widget."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent, QMouseEvent
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

SUPPORTED_SUFFIXES: frozenset[str] = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".bmp",
        ".gif",
        ".webp",
        ".tiff",
        ".tif",
        ".svg",
        ".heic",
        ".heif",
        ".avif",
    }
)

_DIALOG_FILTER = (
    "Image files "
    "(*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tiff *.tif *.svg *.heic *.heif *.avif)"
    ";;All files (*)"
)


class FileDropZone(QFrame):
    """Large drop target that emits :attr:`file_loaded` when a file is chosen."""

    file_loaded = Signal(Path)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(120)

        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(12, 12, 12, 12)

        self._label = QLabel(self.tr("Przeciągnij plik PNG tutaj\nlub kliknij aby wybrać"))
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setWordWrap(True)
        vbox.addWidget(self._label)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def open_file_dialog(self) -> None:
        """Open the file-chooser dialog."""
        from chodzkos_gui_kit.qt.dialogs import open_file

        path = open_file(self, self.tr("Wybierz plik źródłowy"), "", _DIALOG_FILTER)
        if path:
            self.file_loaded.emit(Path(path))

    # ------------------------------------------------------------------
    # Drag-and-drop
    # ------------------------------------------------------------------

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        mime = event.mimeData()
        if mime.hasUrls():
            urls = mime.urls()
            if urls and Path(urls[0].toLocalFile()).suffix.lower() in SUPPORTED_SUFFIXES:
                event.acceptProposedAction()
                return
        event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        if urls:
            self.file_loaded.emit(Path(urls[0].toLocalFile()))

    # ------------------------------------------------------------------
    # Click
    # ------------------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.open_file_dialog()
        super().mousePressEvent(event)
