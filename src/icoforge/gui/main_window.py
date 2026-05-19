"""Main application window."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from icoforge.gui.widgets.file_drop_zone import SUPPORTED_SUFFIXES, FileDropZone

_PREVIEW_MAX_PX = 480


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("IcoForge")
        self.resize(900, 600)

        self.source_path: Path | None = None
        self._drop_zone: FileDropZone
        self._preview_label: QLabel

        self._setup_menu()
        self._setup_central()
        self._setup_statusbar()

    # ------------------------------------------------------------------
    # Setup helpers
    # ------------------------------------------------------------------

    def _setup_menu(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        file_menu.addAction("&Open…", self._on_open)
        file_menu.addAction("Save &As…", self._on_save_as)
        file_menu.addSeparator()
        file_menu.addAction("E&xit", self.close)

        help_menu = menubar.addMenu("&Help")
        help_menu.addAction("&About", self._on_about)

    def _setup_central(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        layout.addWidget(self._make_settings_panel(), stretch=1)
        layout.addWidget(self._make_preview_panel(), stretch=2)

        self._drop_zone.file_loaded.connect(self.on_file_loaded)

    def _make_settings_panel(self) -> QWidget:
        panel = QFrame()
        panel.setFrameShape(QFrame.Shape.StyledPanel)

        vbox = QVBoxLayout(panel)
        vbox.setContentsMargins(8, 8, 8, 8)
        vbox.setSpacing(8)

        self._drop_zone = FileDropZone()
        vbox.addWidget(self._drop_zone)

        placeholder = QLabel("Settings\n(coming soon)")
        placeholder.setEnabled(False)
        vbox.addWidget(placeholder)
        vbox.addStretch()

        return panel

    def _make_preview_panel(self) -> QWidget:
        panel = QFrame()
        panel.setFrameShape(QFrame.Shape.StyledPanel)

        vbox = QVBoxLayout(panel)
        vbox.setContentsMargins(8, 8, 8, 8)

        self._preview_label = QLabel("Preview\n(load a file to see it here)")
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_label.setEnabled(False)
        vbox.addWidget(self._preview_label, stretch=1)

        return panel

    def _setup_statusbar(self) -> None:
        bar = QStatusBar()
        self.setStatusBar(bar)
        bar.showMessage("Ready")

    # ------------------------------------------------------------------
    # File loading
    # ------------------------------------------------------------------

    def on_file_loaded(self, path: Path) -> None:
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            QMessageBox.warning(
                self,
                "Unsupported format",
                f"Format pliku '{path.suffix}' nie jest obsługiwany.\n"
                "Obsługiwane formaty: PNG, JPG, BMP, GIF, WEBP, TIFF.",
            )
            return

        self.source_path = path
        self.statusBar().showMessage(f"Załadowano: {path.name}")

        pixmap = QPixmap(str(path))
        if not pixmap.isNull():
            scaled = pixmap.scaled(
                _PREVIEW_MAX_PX,
                _PREVIEW_MAX_PX,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._preview_label.setEnabled(True)
            self._preview_label.setPixmap(scaled)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_open(self) -> None:
        self._drop_zone.open_file_dialog()

    def _on_save_as(self) -> None:
        self.statusBar().showMessage("Save As… (not yet implemented)")

    def _on_about(self) -> None:
        QMessageBox.about(
            self,
            "About IcoForge",
            "<b>IcoForge</b><br>ICO converter, optimizer and pixel editor.",
        )


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
