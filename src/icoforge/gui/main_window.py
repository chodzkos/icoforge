"""Main application window."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenuBar,
    QMessageBox,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("IcoForge")
        self.resize(900, 600)

        self._setup_menu()
        self._setup_central()
        self._setup_statusbar()

    # ------------------------------------------------------------------
    # Setup helpers
    # ------------------------------------------------------------------

    def _setup_menu(self) -> None:
        menubar: QMenuBar = self.menuBar()  # type: ignore[assignment]

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

    def _make_settings_panel(self) -> QWidget:
        panel = QFrame()
        panel.setFrameShape(QFrame.Shape.StyledPanel)

        vbox = QVBoxLayout(panel)
        vbox.setContentsMargins(8, 8, 8, 8)

        label = QLabel("Settings panel\n(coming soon)")
        label.setEnabled(False)
        vbox.addWidget(label)
        vbox.addStretch()

        return panel

    def _make_preview_panel(self) -> QWidget:
        panel = QFrame()
        panel.setFrameShape(QFrame.Shape.StyledPanel)

        vbox = QVBoxLayout(panel)
        vbox.setContentsMargins(8, 8, 8, 8)

        label = QLabel("Preview area\n(coming soon)")
        label.setEnabled(False)
        vbox.addWidget(label)
        vbox.addStretch()

        return panel

    def _setup_statusbar(self) -> None:
        bar = QStatusBar()
        self.setStatusBar(bar)
        bar.showMessage("Ready")

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_open(self) -> None:
        self.statusBar().showMessage("Open… (not yet implemented)")  # type: ignore[union-attr]

    def _on_save_as(self) -> None:
        self.statusBar().showMessage("Save As… (not yet implemented)")  # type: ignore[union-attr]

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
    return app.exec()  # type: ignore[union-attr]
