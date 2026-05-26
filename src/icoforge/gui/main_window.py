"""Main application window."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QThreadPool, QUrl
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
    QScrollArea,
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


def _asset(name: str) -> Path:
    """Return the path to a bundled asset, works both frozen and in dev."""
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "assets" / name
    return Path(__file__).resolve().parents[3] / "assets" / name


class _ExeIconPickerDialog(QDialog):
    """Modal dialog showing a grid of extracted PE icons for the user to pick."""

    _THUMB_SIZE = 64

    def __init__(self, icons: list[bytes], filename: str, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Ikony w pliku: %1").replace("%1", filename))
        self.resize(480, 360)
        self._icons = icons

        layout = QVBoxLayout(self)

        info = QLabel(
            self.tr(
                "Znaleziono %1 grupę/grup ikon. Zaznacz ikony do zapisania (Ctrl+A - wszystkie)."
            ).replace("%1", str(len(icons)))
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

            item = QListWidgetItem(
                QIcon(pixmap),
                self.tr("Ikona %1").replace("%1", str(i + 1)),
            )
            item.setData(256, i)
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
        icon_path = _asset("icoforge.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

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
        self._lang_pl_action: QAction
        self._lang_en_action: QAction

        self._setup_menu()
        self._setup_toolbar()
        self._setup_central()
        self._setup_statusbar()

    # ------------------------------------------------------------------
    # Setup helpers
    # ------------------------------------------------------------------

    def _setup_menu(self) -> None:
        from icoforge.utils.settings import get_language

        menubar = self.menuBar()

        file_menu = menubar.addMenu(self.tr("&Plik"))
        file_menu.addAction(self.tr("&Nowe ICO…"), self._on_new_ico).setShortcut("Ctrl+N")
        file_menu.addSeparator()
        file_menu.addAction(self.tr("&Otwórz…"), self._on_open)
        file_menu.addAction(self.tr("Zapisz &jako…"), self._on_save_as)
        file_menu.addAction(self.tr("Edytuj &ICO…"), self._on_edit_ico)
        file_menu.addAction(self.tr("&Wyciągnij ikony z EXE/DLL…"), self._on_extract_exe)
        file_menu.addSeparator()
        file_menu.addAction(self.tr("Za&kończ"), self.close)

        help_menu = menubar.addMenu(self.tr("P&omoc"))
        help_menu.addAction(self.tr("&O programie"), self._on_about)
        help_menu.addSeparator()

        lang_menu = help_menu.addMenu(self.tr("Język / Language"))
        current_lang = get_language()

        self._lang_pl_action = QAction(("● " if current_lang == "pl" else "  ") + "Polski", self)
        self._lang_pl_action.triggered.connect(lambda: self._on_language_changed("pl"))
        lang_menu.addAction(self._lang_pl_action)

        self._lang_en_action = QAction(("● " if current_lang == "en" else "  ") + "English", self)
        self._lang_en_action.triggered.connect(lambda: self._on_language_changed("en"))
        lang_menu.addAction(self._lang_en_action)

    def _setup_toolbar(self) -> None:
        toolbar = QToolBar(self.tr("Akcje"))
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self._save_action = QAction(self.tr("Zapisz jako…"), self)
        self._save_action.setEnabled(False)
        self._save_action.triggered.connect(self._on_save_as)
        toolbar.addAction(self._save_action)

        self._cancel_action = QAction(self.tr("Anuluj"), self)
        self._cancel_action.setEnabled(False)
        self._cancel_action.triggered.connect(self._on_cancel)
        toolbar.addAction(self._cancel_action)

        toolbar.addSeparator()

        self._favicon_action = QAction(self.tr("Zestaw Favicon…"), self)
        self._favicon_action.setEnabled(False)
        self._favicon_action.setToolTip(
            self.tr(
                "Generuj kompletny zestaw favicon dla stron www"
                " (favicon.ico, ikony PWA, webmanifest)"
            )
        )
        self._favicon_action.triggered.connect(self._on_favicon_set)
        toolbar.addAction(self._favicon_action)

    def _setup_central(self) -> None:
        tabs = QTabWidget()
        self.setCentralWidget(tabs)

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

        tabs.addTab(conversion_widget, self.tr("Konwersja"))

        self._optimization_panel = OptimizationPanel()
        tabs.addTab(self._optimization_panel, self.tr("Optymalizacja"))

    def _make_settings_panel(self) -> QWidget:
        panel = QFrame()
        panel.setFrameShape(QFrame.Shape.StyledPanel)

        vbox = QVBoxLayout(panel)
        vbox.setContentsMargins(8, 8, 8, 8)
        vbox.setSpacing(8)

        self._drop_zone = FileDropZone()
        vbox.addWidget(self._drop_zone)

        self._settings_panel = SettingsPanel()

        scroll = QScrollArea()
        scroll.setWidget(self._settings_panel)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        vbox.addWidget(scroll)

        return panel

    def _setup_statusbar(self) -> None:
        bar = QStatusBar()
        self.setStatusBar(bar)
        bar.showMessage(self.tr("Gotowy"))

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
                self.tr("Nieobsługiwany format"),
                self.tr(
                    "Format pliku '%1' nie jest obsługiwany.\n"
                    "Obsługiwane formaty: PNG, JPG, BMP, GIF, WEBP, TIFF."
                ).replace("%1", path.suffix),
            )
            return

        self.source_path = path
        self.statusBar().showMessage(self.tr("Załadowano: %1").replace("%1", path.name))
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
            self.tr("Zapisz plik"),
            "",
            self.tr("Pliki ICO (*.ico);;Pliki ICNS (*.icns);;Pliki kursora CUR (*.cur)"),
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
        from icoforge.core.converter import render_frames
        from icoforge.core.icns_writer import _VALID_SIZES, write_icns

        config = self._settings_panel.get_config()
        valid_specs = tuple(s for s in config.sizes if s.width in _VALID_SIZES)
        if not valid_specs:
            QMessageBox.warning(
                self,
                "ICNS",
                self.tr(
                    "Żaden z wybranych rozmiarów nie jest obsługiwany przez ICNS.\n"
                    "Obsługiwane rozmiary: %1"
                ).replace("%1", str(sorted(_VALID_SIZES))),
            )
            return

        from dataclasses import replace

        icns_config = replace(config, sizes=valid_specs)
        try:
            images = render_frames(source, icns_config)
            write_icns(target, images)
            self.statusBar().showMessage(self.tr("Zapisano %1").replace("%1", target.name))
        except Exception as exc:
            QMessageBox.critical(self, self.tr("Błąd zapisu ICNS"), str(exc))

    def _save_cur(self, source: Path, target: Path) -> None:
        from icoforge.core.converter import render_frames
        from icoforge.core.cur_writer import write_cur

        config = self._settings_panel.get_config()

        dlg = QDialog(self)
        dlg.setWindowTitle(self.tr("Hotspot kursora"))
        layout = QVBoxLayout(dlg)

        info = QLabel(
            self.tr(
                "Podaj współrzędne aktywnego piksela (hotspot) kursora.\n"
                "Punkt (0, 0) to lewy górny róg obrazu."
            )
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
            self.statusBar().showMessage(
                self.tr("Zapisano %1  hotspot=%2")
                .replace("%1", target.name)
                .replace("%2", str(hotspot))
            )
        except Exception as exc:
            QMessageBox.critical(self, self.tr("Błąd zapisu CUR"), str(exc))

    # ------------------------------------------------------------------
    # Favicon set
    # ------------------------------------------------------------------

    def _on_favicon_set(self) -> None:
        source = self.source_path
        if source is None:
            return

        output_dir = QFileDialog.getExistingDirectory(
            self,
            self.tr("Wybierz folder wyjściowy dla Favicon Set"),
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
                self.tr("Zestaw Favicon zapisany do: %1  (%2 plików)")
                .replace("%1", output_dir)
                .replace("%2", str(len(generated)))
            )
            msg = QMessageBox(self)
            msg.setWindowTitle("Favicon Set")
            msg.setText(
                self.tr("Wygenerowano %1 pliki w:\n%2\n\n%3")
                .replace("%1", str(len(generated)))
                .replace("%2", output_dir)
                .replace("%3", "\n".join(p.name for p in generated))
            )
            msg.exec()
        except Exception as exc:
            QMessageBox.critical(self, self.tr("Błąd Favicon Set"), str(exc))

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
        self.statusBar().showMessage(self.tr("Konwersja anulowana"))

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
        self.statusBar().showMessage(self.tr("Zapisano: %1").replace("%1", path.name))

        msg = QMessageBox(self)
        msg.setWindowTitle(self.tr("Zapisano"))
        msg.setText(self.tr("Plik zapisany:\n%1").replace("%1", str(path)))
        open_btn = msg.addButton(self.tr("Otwórz folder"), QMessageBox.ButtonRole.ActionRole)
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
            self.tr("Błąd konwersji"),
            self.tr("Nie udało się zapisać pliku ICO:\n%1").replace("%1", message),
        )

    def _on_preview_error(self, message: str) -> None:
        self.statusBar().showMessage(self.tr("Błąd podglądu: %1").replace("%1", message))

    # ------------------------------------------------------------------
    # Other slots
    # ------------------------------------------------------------------

    def _on_open(self) -> None:
        self._drop_zone.open_file_dialog()

    def _on_new_ico(self) -> None:
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
            QMessageBox.critical(
                self,
                self.tr("Błąd"),
                self.tr("Nie można otworzyć edytora:\n%1").replace("%1", str(e)),
            )

    def _on_edit_ico(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Otwórz plik ICO do edycji"),
            "",
            self.tr("Pliki ICO (*.ico)"),
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
                    self.tr("Błąd"),
                    self.tr("Nie można otworzyć pliku ICO:\n%1").replace("%1", str(e)),
                )

    def _on_extract_exe(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Wybierz plik EXE/DLL/OCX"),
            "",
            self.tr("Pliki Windows PE (*.exe *.dll *.ocx);;Wszystkie pliki (*)"),
        )
        if not path:
            return

        try:
            from icoforge.core.exe_extractor import ExeExtractError, extract_icons_from_exe

            icons = extract_icons_from_exe(Path(path))
        except ImportError:
            QMessageBox.critical(
                self,
                self.tr("Brak biblioteki"),
                self.tr(
                    "Wyciąganie ikon wymaga biblioteki pefile.\n"
                    "Zainstaluj ją: pip install icoforge[exe]"
                ),
            )
            return
        except ExeExtractError as exc:
            QMessageBox.critical(self, self.tr("Błąd odczytu PE"), str(exc))
            return

        if not icons:
            QMessageBox.information(
                self,
                self.tr("Brak ikon"),
                self.tr("Plik '%1' nie zawiera zasobów RT_GROUP_ICON.").replace(
                    "%1", Path(path).name
                ),
            )
            return

        dlg = _ExeIconPickerDialog(icons, Path(path).name, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        selected = dlg.selected_icons()
        if not selected:
            return

        output_dir = QFileDialog.getExistingDirectory(self, self.tr("Wybierz folder zapisu"), "")
        if not output_dir:
            return

        stem = Path(path).stem
        saved = 0
        for idx, ico_bytes in selected:
            out = Path(output_dir) / f"{stem}_icon{idx + 1}.ico"
            out.write_bytes(ico_bytes)
            saved += 1

        self.statusBar().showMessage(
            self.tr("Zapisano %1 ikonę/ikon do: %2")
            .replace("%1", str(saved))
            .replace("%2", output_dir)
        )
        QMessageBox.information(
            self,
            self.tr("Zapisano"),
            self.tr("Zapisano %1 plik(ów) ICO do:\n%2")
            .replace("%1", str(saved))
            .replace("%2", output_dir),
        )

    def _on_about(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle(self.tr("O IcoForge"))
        dlg.setFixedWidth(320)
        layout = QVBoxLayout(dlg)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        logo_label = QLabel()
        logo_path = _asset("logo.png")
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path))
            logo_label.setPixmap(
                pixmap.scaledToWidth(200, Qt.TransformationMode.SmoothTransformation)
            )
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo_label)

        text_label = QLabel(
            self.tr("<b>IcoForge</b><br>Konwerter, optymalizator i edytor pikseli dla ikon ICO.")
        )
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_label.setWordWrap(True)
        layout.addWidget(text_label)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(dlg.accept)
        layout.addWidget(buttons)

        dlg.exec()

    def _on_language_changed(self, lang: str) -> None:
        from icoforge.utils.settings import set_language

        set_language(lang)

        self._lang_pl_action.setText(("● " if lang == "pl" else "  ") + "Polski")
        self._lang_en_action.setText(("● " if lang == "en" else "  ") + "English")

        QMessageBox.information(
            self,
            "Język / Language",
            self.tr("Zmiana zostanie zastosowana po restarcie aplikacji."),
        )


def main(app: QApplication | None = None) -> int:
    _app = app or QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.show()
    window.raise_()
    window.activateWindow()
    return int(_app.exec())
