"""Main application window."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QSize, QThreadPool, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QSpinBox,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from icoforge.gui.editor.editor_window import EditorWindow
from icoforge.gui.widgets.file_drop_zone import SUPPORTED_SUFFIXES, FileDropZone
from icoforge.gui.widgets.optimization_panel import OptimizationPanel
from icoforge.gui.widgets.preview_panel import PreviewPanel
from icoforge.gui.widgets.settings_panel import SettingsPanel
from icoforge.gui.workers import ConversionWorker


class _ExeIconPickerDialog(QDialog):
    """Modal dialog showing a grid of extracted PE icons for the user to pick."""

    _THUMB_SIZE = 64

    def __init__(self, icons: list[bytes], filename: str, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Ikony w pliku: {filename}")
        self.resize(480, 360)
        self._icons = icons

        layout = QVBoxLayout(self)

        info = QLabel(
            f"Znaleziono {len(icons)} grupę/grup ikon. "
            "Zaznacz ikony do zapisania (Ctrl+A - wszystkie)."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self._list = QListWidget()
        self._list.setViewMode(QListWidget.ViewMode.IconMode)
        self._list.setIconSize(QSize(self._THUMB_SIZE, self._THUMB_SIZE))
        self._list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self._list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self._list.setSpacing(4)
        layout.addWidget(self._list)

        self._populate(icons)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Pre-select all items
        self._list.selectAll()

    def _populate(self, icons: list[bytes]) -> None:
        import io

        from PIL import Image

        for i, ico_bytes in enumerate(icons):
            try:
                img = Image.open(io.BytesIO(ico_bytes)).convert("RGBA")
                img.thumbnail((self._THUMB_SIZE, self._THUMB_SIZE), Image.LANCZOS)
                w, h = img.size
                data = img.tobytes("raw", "RGBA")
                pixmap = QPixmap.fromImage(QImage(data, w, h, w * 4, QImage.Format.Format_RGBA8888))
            except Exception:
                pixmap = QPixmap(self._THUMB_SIZE, self._THUMB_SIZE)
                pixmap.fill()

            item = QListWidgetItem(QIcon(pixmap), f"Ikona {i + 1}")
            item.setData(256, i)  # store original index in UserRole+0
            self._list.addItem(item)

    def selected_icons(self) -> list[tuple[int, bytes]]:
        result = []
        for item in self._list.selectedItems():
            idx: int = item.data(256)
            result.append((idx, self._icons[idx]))
        return result


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("IcoForge")
        self.resize(900, 600)

        self.source_path: Path | None = None
        self._current_worker: ConversionWorker | None = None
        self._editor_window: EditorWindow | None = None
        self._drop_zone: FileDropZone
        self._settings_panel: SettingsPanel
        self._preview_panel: PreviewPanel
        self._optimization_panel: OptimizationPanel
        self._save_action: QAction
        self._cancel_action: QAction
        self._favicon_action: QAction
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
        file_menu.addAction("&New ICO…\tCtrl+N", self._on_new_ico).setShortcut("Ctrl+N")
        file_menu.addSeparator()
        file_menu.addAction("&Open…", self._on_open)
        file_menu.addAction("Save &As…", self._on_save_as)
        file_menu.addAction("Edit &ICO…", self._on_edit_ico)
        file_menu.addAction("&Wyciągnij ikony z EXE/DLL…", self._on_extract_exe)
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

        toolbar.addSeparator()

        self._favicon_action = QAction("Favicon Set…", self)
        self._favicon_action.setEnabled(False)
        self._favicon_action.setToolTip(
            "Generate a complete web favicon set (favicon.ico, PWA icons, webmanifest)"
        )
        self._favicon_action.triggered.connect(self._on_favicon_set)
        toolbar.addAction(self._favicon_action)

    def _setup_central(self) -> None:
        tabs = QTabWidget()
        self.setCentralWidget(tabs)

        # Conversion tab
        conversion_widget = QWidget()
        layout = QHBoxLayout(conversion_widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        layout.addWidget(self._make_settings_panel(), stretch=1)

        self._preview_panel = PreviewPanel()
        layout.addWidget(self._preview_panel, stretch=2)

        self._drop_zone.file_loaded.connect(self.on_file_loaded)
        self._settings_panel.settings_changed.connect(self._update_preview)
        self._preview_panel.render_error.connect(self._on_preview_error)

        tabs.addTab(conversion_widget, "Konwersja")

        # Optimization tab
        self._optimization_panel = OptimizationPanel()
        tabs.addTab(self._optimization_panel, "Optymalizacja")

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
        self._favicon_action.setEnabled(True)
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
        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Zapisz plik",
            "",
            "ICO files (*.ico);;ICNS files (*.icns);;CUR cursor files (*.cur)",
        )
        if not path:
            return

        if "icns" in selected_filter.lower():
            if not path.lower().endswith(".icns"):
                path += ".icns"
            self._save_icns(source, Path(path))
            return

        if "cur" in selected_filter.lower():
            if not path.lower().endswith(".cur"):
                path += ".cur"
            self._save_cur(source, Path(path))
            return

        if not path.lower().endswith(".ico"):
            path += ".ico"
        target = Path(path)
        config = self._settings_panel.get_config()

        worker = ConversionWorker(source, target, config)
        worker.signals.progress.connect(self._on_convert_progress)
        worker.signals.finished.connect(self._on_convert_finished)
        worker.signals.error.connect(self._on_convert_error)
        self._current_worker = worker

        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(True)
        self._save_action.setEnabled(False)
        self._cancel_action.setEnabled(True)

        QThreadPool.globalInstance().start(worker)

    def _save_icns(self, source: Path, target: Path) -> None:
        """Render frames from *source* and save as ICNS using current settings."""
        from icoforge.core.converter import render_frames
        from icoforge.core.icns_writer import _VALID_SIZES, write_icns

        config = self._settings_panel.get_config()
        valid_specs = tuple(s for s in config.sizes if s.width in _VALID_SIZES)
        if not valid_specs:
            QMessageBox.warning(
                self,
                "ICNS",
                "Żaden z wybranych rozmiarów nie jest obsługiwany przez ICNS.\n"
                f"Obsługiwane rozmiary: {sorted(_VALID_SIZES)}",
            )
            return

        from dataclasses import replace

        icns_config = replace(config, sizes=valid_specs)
        try:
            images = render_frames(source, icns_config)
            write_icns(target, images)
            self.statusBar().showMessage(f"Zapisano {target.name}")
        except Exception as exc:
            QMessageBox.critical(self, "Błąd zapisu ICNS", str(exc))

    def _save_cur(self, source: Path, target: Path) -> None:
        """Ask for hotspot, then render frames and save as a Windows .cur file."""
        from icoforge.core.converter import render_frames
        from icoforge.core.cur_writer import write_cur

        config = self._settings_panel.get_config()

        # --- hotspot dialog ---
        dlg = QDialog(self)
        dlg.setWindowTitle("Hotspot kursora")
        layout = QVBoxLayout(dlg)

        info = QLabel(
            "Podaj współrzędne aktywnego piksela (hotspot) kursora.\n"
            "Punkt (0, 0) to lewy górny róg obrazu."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        form = QFormLayout()
        max_size = max(s.width for s in config.sizes)
        sb_x = QSpinBox()
        sb_x.setRange(0, max_size - 1)
        sb_x.setValue(0)
        sb_y = QSpinBox()
        sb_y.setRange(0, max_size - 1)
        sb_y.setValue(0)
        form.addRow("Hotspot X:", sb_x)
        form.addRow("Hotspot Y:", sb_y)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        hotspot = (sb_x.value(), sb_y.value())

        try:
            images = render_frames(source, config)
            pairs = list(zip(images, config.sizes, strict=False))
            write_cur(target, pairs, hotspot=hotspot)
            self.statusBar().showMessage(f"Zapisano {target.name}  hotspot={hotspot}")
        except Exception as exc:
            QMessageBox.critical(self, "Błąd zapisu CUR", str(exc))

    # ------------------------------------------------------------------
    # Favicon set
    # ------------------------------------------------------------------

    def _on_favicon_set(self) -> None:
        """Pick output folder, then generate a complete web favicon set."""
        source = self.source_path
        if source is None:
            return

        output_dir = QFileDialog.getExistingDirectory(
            self,
            "Wybierz folder wyjściowy dla Favicon Set",
            "",
        )
        if not output_dir:
            return

        from icoforge.core.favicon_generator import generate_favicon_set
        from icoforge.core.models import ResampleAlgorithm
        from icoforge.core.resampling import to_pillow

        try:
            generated = generate_favicon_set(
                source,
                Path(output_dir),
                resample=to_pillow(ResampleAlgorithm.LANCZOS),
            )
            self.statusBar().showMessage(
                f"Favicon set zapisany do: {output_dir}  ({len(generated)} plików)"
            )
            msg = QMessageBox(self)
            msg.setWindowTitle("Favicon Set")
            msg.setText(
                f"Wygenerowano {len(generated)} pliki w:\n{output_dir}\n\n"
                + "\n".join(p.name for p in generated)
            )
            msg.exec()
        except Exception as exc:
            QMessageBox.critical(self, "Błąd Favicon Set", str(exc))

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

    def _on_new_ico(self) -> None:
        """Open NewIcoDialog and launch EditorWindow with a blank document."""
        from PySide6.QtWidgets import QDialog

        from icoforge.gui.editor.new_ico_dialog import NewIcoDialog

        dlg = NewIcoDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        frames = dlg.get_frames()
        if not frames:
            return
        try:
            self._editor_window = EditorWindow(Path("nienazwany.ico"), frames=frames)
            self._editor_window.show()
            self._editor_window.raise_()
            self._editor_window.activateWindow()
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Nie można otworzyć edytora:\n{e}")

    def _on_edit_ico(self) -> None:
        """Open file dialog to select ICO for editing."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Otwórz plik ICO do edycji",
            "",
            "ICO files (*.ico)",
        )
        if path:
            try:
                self._editor_window = EditorWindow(Path(path))
                self._editor_window.show()
                self._editor_window.raise_()
                self._editor_window.activateWindow()
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Błąd",
                    f"Nie można otworzyć pliku ICO:\n{e}",
                )

    def _on_extract_exe(self) -> None:
        """Pick an EXE/DLL, extract icons, show a selection grid, save chosen files."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Wybierz plik EXE/DLL/OCX",
            "",
            "Windows PE files (*.exe *.dll *.ocx);;All files (*)",
        )
        if not path:
            return

        try:
            from icoforge.core.exe_extractor import ExeExtractError, extract_icons_from_exe

            icons = extract_icons_from_exe(Path(path))
        except ImportError:
            QMessageBox.critical(
                self,
                "Brak biblioteki",
                "Wyciąganie ikon wymaga biblioteki pefile.\n"
                "Zainstaluj ją: pip install icoforge[exe]",
            )
            return
        except ExeExtractError as exc:
            QMessageBox.critical(self, "Błąd odczytu PE", str(exc))
            return

        if not icons:
            QMessageBox.information(
                self,
                "Brak ikon",
                f"Plik '{Path(path).name}' nie zawiera zasobów RT_GROUP_ICON.",
            )
            return

        dlg = _ExeIconPickerDialog(icons, Path(path).name, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        selected = dlg.selected_icons()
        if not selected:
            return

        output_dir = QFileDialog.getExistingDirectory(self, "Wybierz folder zapisu", "")
        if not output_dir:
            return

        stem = Path(path).stem
        saved = 0
        for idx, ico_bytes in selected:
            out = Path(output_dir) / f"{stem}_icon{idx + 1}.ico"
            out.write_bytes(ico_bytes)
            saved += 1

        self.statusBar().showMessage(f"Zapisano {saved} ikonę/ikon do: {output_dir}")
        QMessageBox.information(
            self,
            "Zapisano",
            f"Zapisano {saved} plik(ów) ICO do:\n{output_dir}",
        )

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
    window.raise_()
    window.activateWindow()
    return int(app.exec())
