"""Main editor window for editing ICO files."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from icoforge.core.ico_reader import read_ico
from icoforge.gui.editor.canvas import EditorCanvas


class EditorWindow(QMainWindow):
    """Main window for the pixel editor."""

    def __init__(self, ico_path: Path, parent: object | None = None) -> None:
        super().__init__(parent)
        self.ico_path = ico_path
        self.setWindowTitle(f"Editor - {ico_path.name}")
        self.resize(1000, 700)

        # Frames data: list of (Image, SizeSpec) tuples
        self._frames: list = []
        self._current_frame_index = 0

        # Create central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create splitter: left = size list, right = canvas
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # Left panel: size list
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(4, 4, 4, 4)

        left_layout.addWidget(QLabel("Rozmiary:"))

        self._size_list = QListWidget()
        self._size_list.itemClicked.connect(self._on_size_selected)
        left_layout.addWidget(self._size_list)

        splitter.addWidget(left_widget)
        splitter.setStretchFactor(0, 1)

        # Right panel: canvas
        self._canvas = EditorCanvas()
        self._canvas.zoom_changed.connect(self._on_zoom_changed)
        splitter.addWidget(self._canvas)
        splitter.setStretchFactor(1, 3)

        # Status bar
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Ready")

        # Load ICO file
        self._load_ico(ico_path)

    def _load_ico(self, path: Path) -> None:
        """Load an ICO file and populate the UI."""
        try:
            self._frames = read_ico(path)

            # Populate size list
            self._size_list.clear()
            for i, (_image, spec) in enumerate(self._frames):
                size_str = f"{spec.width}x{spec.height}"
                item = QListWidgetItem(size_str)
                item.setData(Qt.ItemDataRole.UserRole, i)
                # Make font monospace for alignment
                font = QFont("Courier")
                item.setFont(font)
                self._size_list.addItem(item)

            # Select first frame
            if self._frames:
                self._size_list.setCurrentRow(0)
                self._on_size_selected(self._size_list.item(0))

            self._status_bar.showMessage(f"Loaded ICO: {len(self._frames)} sizes")
        except Exception as e:
            self._status_bar.showMessage(f"Error loading ICO: {e}")

    def _on_size_selected(self, item: QListWidgetItem) -> None:
        """Handle size selection from list."""
        frame_index = item.data(Qt.ItemDataRole.UserRole)
        if frame_index is not None and 0 <= frame_index < len(self._frames):
            self._current_frame_index = frame_index
            image, spec = self._frames[frame_index]

            # Load image to canvas
            self._canvas.load_image(image)

            # Update window title
            self.setWindowTitle(f"Editor - {self.ico_path.name} [{spec.width}x{spec.height}]")

            self._status_bar.showMessage(
                f"Editing {spec.width}x{spec.height} ({frame_index + 1}/{len(self._frames)})"
            )

    def _on_zoom_changed(self, zoom: float) -> None:
        """Handle zoom level change."""
        percentage = int(zoom * 100)
        self._status_bar.showMessage(f"Zoom: {percentage}%")
