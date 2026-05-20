"""Main application window."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QThreadPool, QTimer, QUrl
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from icoforge.gui.widgets.file_drop_zone import SUPPORTED_SUFFIXES, FileDropZone
from icoforge.gui.widgets.preview_panel import PreviewPanel
from icoforge.gui.widgets.settings_panel import SettingsPanel
from icoforge.gui.workers import ConversionWorker


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("IcoForge")
        self.resize(900, 600)

        self.source_path: Path | None = None
        self._current_worker: ConversionWorker | None = None
        self._live_workers: set[ConversionWorker] = set()
        self._drop_zone: FileDropZone
        self._settings_panel: SettingsPanel
        self._preview_panel: PreviewPanel
        self._save_action: QAction
        self._cancel_action: QAction
        self._progress_bar: QProgressBar

        self._setup_menu()
        self._setup_toolbar()
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

    def _setup_toolbar(self) -> None:
        toolbar = QToolBar("Actions")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self._save_action = QAction("Zapisz jako…", self)
        self._save_action.setEnabled(False)
        self._save_action.triggered.connect(self._on_save_as)
        toolbar.addAction(self._save_action)

        self._cancel_action = QAction("Anuluj", self)
        self._cancel_action.setEnabled(False)
        self._cancel_action.triggered.connect(self._on_cancel)
        toolbar.addAction(self._cancel_action)

    def _setup_central(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        layout.addWidget(self._make_settings_panel(), stretch=1)

        self._preview_panel = PreviewPanel()
        layout.addWidget(self._preview_panel, stretch=2)

        self._drop_zone.file_loaded.connect(self.on_file_loaded)
        self._settings_panel.settings_changed.connect(self._update_preview)
        self._preview_panel.render_error.connect(self._on_preview_error)

    def _make_settings_panel(self) -> QWidget:
        panel = QFrame()
        panel.setFrameShape(QFrame.Shape.StyledPanel)

        vbox = QVBoxLayout(panel)
        vbox.setContentsMargins(8, 8, 8, 8)
        vbox.setSpacing(8)

        self._drop_zone = FileDropZone()
        vbox.addWidget(self._drop_zone)

        self._settings_panel = SettingsPanel()
        vbox.addWidget(self._settings_panel)

        return panel

    def _setup_statusbar(self) -> None:
        bar = QStatusBar()
        self.setStatusBar(bar)
        bar.showMessage("Ready")

        self._progress_bar = QProgressBar()
        self._progress_bar.setMaximumWidth(200)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setVisible(False)
        bar.addPermanentWidget(self._progress_bar)

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
        self._save_action.setEnabled(True)
        self._update_preview()

    def _update_preview(self) -> None:
        if self.source_path is None:
            return
        config = self._settings_panel.get_config()
        self._preview_panel.update_preview(self.source_path, config)

    # ------------------------------------------------------------------
    # Save As
    # ------------------------------------------------------------------

    def _on_save_as(self) -> None:
        source = self.source_path
        if source is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Zapisz plik ICO",
            "",
            "ICO files (*.ico)",
            options=QFileDialog.Option.DontUseNativeDialog,
        )
        if not path:
            return
        if not path.lower().endswith(".ico"):
            path += ".ico"
        target = Path(path)
        config = self._settings_panel.get_config()

        worker = ConversionWorker(source, target, config)
        worker.signals.progress.connect(self._on_convert_progress)
        worker.signals.finished.connect(self._on_convert_finished)
        worker.signals.error.connect(self._on_convert_error)
        # Defer the discard one tick so _WorkerSignals isn't destroyed inside
        # its own `done` slot (PySide6 use-after-free in queued connections).
        worker.signals.done.connect(
            lambda w=worker: QTimer.singleShot(0, lambda: self._live_workers.discard(w))
        )
        self._current_worker = worker
        self._live_workers.add(worker)

        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(True)
        self._save_action.setEnabled(False)
        self._cancel_action.setEnabled(True)

        QThreadPool.globalInstance().start(worker)

    # ------------------------------------------------------------------
    # Cancellation
    # ------------------------------------------------------------------

    def _on_cancel(self) -> None:
        if self._current_worker is not None:
            self._current_worker.cancel()
            self._current_worker = None
        self._cancel_action.setEnabled(False)
        self._save_action.setEnabled(True)
        self._progress_bar.setVisible(False)
        self.statusBar().showMessage("Konwersja anulowana")

    # ------------------------------------------------------------------
    # Convert worker slots
    # ------------------------------------------------------------------

    def _on_convert_progress(self, value: float) -> None:
        self._progress_bar.setValue(int(value * 100))

    def _on_convert_finished(self, path: Path) -> None:
        self._current_worker = None
        self._progress_bar.setVisible(False)
        self._save_action.setEnabled(True)
        self._cancel_action.setEnabled(False)
        self.statusBar().showMessage(f"Zapisano: {path.name}")

        msg = QMessageBox(self)
        msg.setWindowTitle("Zapisano")
        msg.setText(f"Plik zapisany:\n{path}")
        open_btn = msg.addButton("Otwórz folder", QMessageBox.ButtonRole.ActionRole)
        msg.addButton(QMessageBox.StandardButton.Ok)
        msg.exec()
        if msg.clickedButton() is open_btn:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent)))

    def _on_convert_error(self, message: str) -> None:
        self._current_worker = None
        self._progress_bar.setVisible(False)
        self._save_action.setEnabled(True)
        self._cancel_action.setEnabled(False)
        QMessageBox.critical(
            self,
            "Błąd konwersji",
            f"Nie udało się zapisać pliku ICO:\n{message}",
        )

    def _on_preview_error(self, message: str) -> None:
        self.statusBar().showMessage(f"Błąd podglądu: {message}")

    # ------------------------------------------------------------------
    # Other slots
    # ------------------------------------------------------------------

    def _on_open(self) -> None:
        self._drop_zone.open_file_dialog()

    def _on_about(self) -> None:
        QMessageBox.about(
            self,
            "About IcoForge",
            "<b>IcoForge</b><br>ICO converter, optimizer and pixel editor.",
        )


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    # Clear any inherited minimized/maximized bit before showing so the
    # Wayland compositor maps the surface as a normal toplevel.
    window.setWindowState(Qt.WindowState.WindowNoState)
    window.show()
    window.raise_()
    window.activateWindow()
    return int(app.exec())
