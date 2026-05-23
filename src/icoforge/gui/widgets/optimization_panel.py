"""PNG optimization panel with file queue, options, and progress reporting."""

from __future__ import annotations

import csv
from pathlib import Path

from PySide6.QtCore import Qt, QThreadPool, Signal
from PySide6.QtGui import QColor, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from icoforge.core.models import OptimizationConfig
from icoforge.core.optimizer import OptimizationResult


class DropZoneFrame(QFrame):
    """Frame that accepts drag & drop for PNG files."""

    files_dropped = Signal(list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            "QFrame { border: 2px dashed #aaa; border-radius: 4px; background-color: #f9f9f9; }"
        )
        self.setAcceptDrops(True)
        self.setMinimumHeight(60)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Handle drag enter."""
        mime = event.mimeData()
        if mime.hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        """Handle drop."""
        mime = event.mimeData()
        paths = [Path(url.toLocalFile()) for url in mime.urls()]
        self.files_dropped.emit(paths)
        event.acceptProposedAction()


class OptimizationPanel(QWidget):
    """Panel for batch PNG optimization with file queue and reporting."""

    optimization_started = Signal()
    optimization_finished = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._file_queue: list[Path] = []
        self._results: list[OptimizationResult] = []
        self._thread_pool = QThreadPool.globalInstance()
        self._current_batch_worker: BatchOptimizationWorker | None = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the optimization panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Drop zone
        self._drop_area = DropZoneFrame()
        self._drop_area.files_dropped.connect(self._on_files_dropped)

        drop_layout = QVBoxLayout(self._drop_area)
        drop_label = QLabel("Przeciągnij pliki PNG lub folder\nlub kliknij aby wybrać")
        drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_layout.addWidget(drop_label)

        layout.addWidget(self._drop_area)

        # File queue list
        self._file_list = QListWidget()
        self._file_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self._file_list.setMaximumHeight(150)
        layout.addWidget(QLabel("Kolejka plików:"))
        layout.addWidget(self._file_list)

        # Options panel
        options_group = QGroupBox("Opcje optymalizacji")
        options_layout = QVBoxLayout()

        # Compression level
        level_layout = QHBoxLayout()
        level_layout.addWidget(QLabel("Poziom kompresji:"))
        level_layout.addWidget(QLabel("Szybszy"))
        self._level_slider = QSlider(Qt.Orientation.Horizontal)
        self._level_slider.setRange(0, 6)
        self._level_slider.setValue(4)
        self._level_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._level_slider.setTickInterval(1)
        level_layout.addWidget(self._level_slider)
        level_layout.addWidget(QLabel("Mniejszy"))
        options_layout.addLayout(level_layout)

        # Checkboxes
        self._zopfli_checkbox = QCheckBox("Tryb Zopfli (wolny, maksymalna kompresja)")
        self._strip_metadata_checkbox = QCheckBox("Usuń metadane (GPS, data, aparat)")
        self._strip_metadata_checkbox.setChecked(True)
        self._preserve_icc_checkbox = QCheckBox("Zachowaj profil kolorów ICC")

        options_layout.addWidget(self._zopfli_checkbox)
        options_layout.addWidget(self._strip_metadata_checkbox)
        options_layout.addWidget(self._preserve_icc_checkbox)

        # Save location
        save_layout = QHBoxLayout()
        self._inplace_radio = QRadioButton("Zapisz w miejscu")
        self._inplace_radio.setChecked(True)
        self._folder_radio = QRadioButton("Zapisz do folderu:")
        self._folder_button = QPushButton("Wybierz...")
        self._folder_button.setEnabled(False)
        self._folder_button.clicked.connect(self._on_choose_folder)
        self._folder_radio.toggled.connect(self._folder_button.setEnabled)
        self._selected_folder: Path | None = None

        save_layout.addWidget(self._inplace_radio)
        save_layout.addStretch()
        save_layout.addWidget(self._folder_radio)
        save_layout.addWidget(self._folder_button)
        options_layout.addLayout(save_layout)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # Optimize button
        button_layout = QHBoxLayout()
        self._optimize_button = QPushButton("Optymalizuj")
        self._optimize_button.setMinimumHeight(40)
        self._optimize_button.clicked.connect(self._on_optimize_clicked)
        button_layout.addStretch()
        button_layout.addWidget(self._optimize_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        # Progress bars
        self._global_progress = QProgressBar()
        self._global_progress.setVisible(False)
        layout.addWidget(QLabel("Postęp:"))
        layout.addWidget(self._global_progress)

        # Results table
        self._results_table = QTableWidget()
        self._results_table.setColumnCount(4)
        self._results_table.setHorizontalHeaderLabels(["Plik", "Przed", "Po", "Oszczędność %"])
        self._results_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self._results_table.setMaximumHeight(200)
        self._results_table.setVisible(False)
        layout.addWidget(self._results_table)

        # Export CSV button
        export_layout = QHBoxLayout()
        self._export_button = QPushButton("Eksportuj raport CSV")
        self._export_button.setVisible(False)
        self._export_button.clicked.connect(self._on_export_csv)
        export_layout.addStretch()
        export_layout.addWidget(self._export_button)
        layout.addLayout(export_layout)

        layout.addStretch()

    def _on_files_dropped(self, paths: list[Path]) -> None:
        """Handle files dropped on the drop zone."""
        for path in paths:
            if path.is_file() and path.suffix.lower() == ".png":
                self._add_file_to_queue(path)
            elif path.is_dir():
                self._add_folder_to_queue(path)

    def _add_file_to_queue(self, path: Path) -> None:
        """Add single PNG file to queue."""
        if path not in self._file_queue:
            self._file_queue.append(path)
            item = QListWidgetItem(f"{path.name} ({self._format_bytes(path.stat().st_size)})")
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            self._file_list.addItem(item)

    def _add_folder_to_queue(self, folder: Path) -> None:
        """Add all PNG files from folder to queue."""
        for png_file in sorted(folder.glob("**/*.png")):
            self._add_file_to_queue(png_file)

    def _on_choose_folder(self) -> None:
        """Open folder selection dialog."""
        folder = QFileDialog.getExistingDirectory(self, "Wybierz folder wyjściowy")
        if folder:
            self._selected_folder = Path(folder)
            self._folder_button.setText(f".../{self._selected_folder.name}")

    def _on_optimize_clicked(self) -> None:
        """Start batch optimization."""
        if not self._file_queue:
            QMessageBox.warning(self, "Brak plików", "Dodaj pliki PNG do optymalizacji")
            return

        self._optimize_button.setEnabled(False)
        self._global_progress.setVisible(True)
        self._global_progress.setValue(0)
        self._results.clear()
        self._results_table.setVisible(False)
        self._export_button.setVisible(False)

        config = OptimizationConfig(
            level=self._level_slider.value(),
            strip_metadata=self._strip_metadata_checkbox.isChecked(),
            use_zopfli=self._zopfli_checkbox.isChecked(),
            preserve_color_profile=self._preserve_icc_checkbox.isChecked(),
        )

        def progress_cb(ratio: float) -> None:
            self._global_progress.setValue(int(ratio * 100))

        from icoforge.core.optimizer import optimize_batch

        try:
            self._results = optimize_batch(self._file_queue, config=config, progress=progress_cb)
            self._show_results()
            QMessageBox.information(
                self, "Gotowe", f"Zoptymalizowano {len(self._results)} plik(ów)"
            )
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Błąd optymalizacji: {e}")
        finally:
            self._optimize_button.setEnabled(True)
            self._global_progress.setVisible(False)

    def _show_results(self) -> None:
        """Display optimization results in table."""
        self._results_table.setRowCount(len(self._results))

        total_before = 0
        total_after = 0

        for row, result in enumerate(self._results):
            total_before += result.bytes_before
            total_after += result.bytes_after

            file_item = QTableWidgetItem(result.source.name)
            before_item = QTableWidgetItem(self._format_bytes(result.bytes_before))
            after_item = QTableWidgetItem(self._format_bytes(result.bytes_after))
            ratio_item = QTableWidgetItem(f"{result.saved_ratio * 100:.1f}%")

            self._results_table.setItem(row, 0, file_item)
            self._results_table.setItem(row, 1, before_item)
            self._results_table.setItem(row, 2, after_item)
            self._results_table.setItem(row, 3, ratio_item)

        # Summary row
        summary_row = self._results_table.rowCount()
        self._results_table.insertRow(summary_row)
        total_ratio = (total_before - total_after) / total_before * 100 if total_before > 0 else 0

        summary_items = [
            QTableWidgetItem("RAZEM"),
            QTableWidgetItem(self._format_bytes(total_before)),
            QTableWidgetItem(self._format_bytes(total_after)),
            QTableWidgetItem(f"{total_ratio:.1f}%"),
        ]

        for col, item in enumerate(summary_items):
            item.setBackground(QColor(220, 220, 220))
            self._results_table.setItem(summary_row, col, item)

        self._results_table.setVisible(True)
        self._export_button.setVisible(True)

    def _on_export_csv(self) -> None:
        """Export results to CSV file."""
        path_str, _ = QFileDialog.getSaveFileName(self, "Zapisz raport", "", "CSV (*.csv)")
        if not path_str:
            return

        try:
            path = Path(path_str)
            with path.open("w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Plik", "Przed (B)", "Po (B)", "Oszczędność %"])
                for result in self._results:
                    writer.writerow(
                        [
                            result.source.name,
                            result.bytes_before,
                            result.bytes_after,
                            f"{result.saved_ratio * 100:.1f}",
                        ]
                    )
            QMessageBox.information(self, "Eksportowano", f"Raport zapisany: {path_str}")
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Błąd eksportu: {e}")

    @staticmethod
    def _format_bytes(size: int) -> str:
        """Format bytes to human-readable string."""
        size_float = float(size)
        for unit in ["B", "KB", "MB", "GB"]:
            if size_float < 1024:
                return f"{size_float:.1f} {unit}"
            size_float /= 1024
        return f"{size_float:.1f} TB"


class BatchOptimizationWorker:
    """Placeholder for future worker class if needed."""

    pass
