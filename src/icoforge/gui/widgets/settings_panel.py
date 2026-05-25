"""Left-column settings panel with conversion options."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QPoint, Qt, Signal
from PySide6.QtGui import QColor, QDragEnterEvent, QDragMoveEvent, QDropEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QColorDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from icoforge.core.models import (
    TRANSPARENT,
    Background,
    Color,
    IcoConfig,
    ResampleAlgorithm,
    SizeSpec,
)

_ALL_SIZES: tuple[int, ...] = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)
_DEFAULT_SIZES: frozenset[int] = frozenset({16, 32, 48, 256})

_PRESETS: dict[str, frozenset[int] | None] = {
    "Custom": None,
    "Favicon (16/32/48)": frozenset({16, 32, 48}),
    "Windows App (all)": frozenset({16, 20, 24, 32, 40, 48, 64, 96, 128, 256}),
    "Web (16/32/64/128)": frozenset({16, 32, 64, 128}),
}

_RESAMPLE_TOOLTIPS: dict[ResampleAlgorithm, str] = {
    ResampleAlgorithm.LANCZOS: "Wysoka jakość, najlepszy dla zdjęć i grafiki",
    ResampleAlgorithm.BICUBIC: "Płynna interpolacja, dobry wybór ogólny",
    ResampleAlgorithm.BILINEAR: "Szybki, wystarczający dla małych ikon",
    ResampleAlgorithm.NEAREST: "Bez interpolacji, zachowuje ostre krawędzie (pixel art)",
    ResampleAlgorithm.BOX: "Szybki i ostry przy dużym zmniejszaniu",
}

_OVERRIDE_BG = QColor(200, 230, 255)  # light blue highlight for rows with override
_DIALOG_FILTER = (
    "Image files "
    "(*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tiff *.tif *.svg *.heic *.heif *.avif)"
    ";;All files (*)"
)
_SUPPORTED_SUFFIXES: frozenset[str] = frozenset(
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

_COL_CHECK = 0
_COL_SIZE = 1
_COL_SOURCE = 2
_COL_BTN = 3


class SizeTable(QTableWidget):
    """Per-size table: enable/disable each ICO size and assign a source override."""

    sizes_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(len(_ALL_SIZES), 4, parent)
        self._sizes: tuple[int, ...] = _ALL_SIZES
        self._overrides: dict[int, Path] = {}
        self._setup()
        self._populate()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _setup(self) -> None:
        self.setHorizontalHeaderLabels(["✓", "Rozmiar", "Źródło", ""])
        self.verticalHeader().setVisible(False)
        self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setShowGrid(False)

        hdr = self.horizontalHeader()
        hdr.setSectionResizeMode(_COL_CHECK, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(_COL_SIZE, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(_COL_SOURCE, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(_COL_BTN, QHeaderView.ResizeMode.ResizeToContents)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)

        # Route drops through the viewport widget, NOT the table itself.
        # setAcceptDrops(True) on QAbstractItemView activates Qt's internal
        # drag machinery which can steal the cursor on WSLg/XWayland.
        self.viewport().setAcceptDrops(True)
        self.viewport().installEventFilter(self)

    def _populate(self) -> None:
        for row, size in enumerate(self._sizes):
            # Column 0 — checkbox
            check = QTableWidgetItem()
            check.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            check.setCheckState(
                Qt.CheckState.Checked if size in _DEFAULT_SIZES else Qt.CheckState.Unchecked
            )
            check.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(row, _COL_CHECK, check)

            # Column 1 — size label
            size_item = QTableWidgetItem(f"{size}x{size}")
            size_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(row, _COL_SIZE, size_item)

            # Column 2 — source path (or default placeholder)
            src_item = QTableWidgetItem("(domyslne)")
            src_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            src_item.setForeground(QColor(150, 150, 150))
            self.setItem(row, _COL_SOURCE, src_item)

            # Column 3 — browse button
            btn = QPushButton("Wybierz…")
            btn.setFixedHeight(22)
            btn.clicked.connect(lambda _checked, s=size: self._on_browse(s))
            self.setCellWidget(row, _COL_BTN, btn)

            self.setRowHeight(row, 26)

        self.itemChanged.connect(self._on_item_changed)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _row_for_size(self, size: int) -> int:
        return self._sizes.index(size)

    def _set_override(self, size: int, path: Path) -> None:
        self._overrides[size] = path
        row = self._row_for_size(size)
        # Disconnect itemChanged so cosmetic updates don't cascade into
        # sizes_changed mid-method; emit once explicitly at the end.
        self.itemChanged.disconnect(self._on_item_changed)
        try:
            item = self.item(row, _COL_SOURCE)
            if item:
                item.setText(path.name)
                item.setToolTip(str(path))
                item.setForeground(QColor(0, 0, 0))
            self._set_row_highlight(row, active=True)
        finally:
            self.itemChanged.connect(self._on_item_changed)
        self.sizes_changed.emit()

    def _clear_override(self, size: int) -> None:
        self._overrides.pop(size, None)
        row = self._row_for_size(size)
        self.itemChanged.disconnect(self._on_item_changed)
        try:
            item = self.item(row, _COL_SOURCE)
            if item:
                item.setText("(domyslne)")
                item.setToolTip("")
                item.setForeground(QColor(150, 150, 150))
            self._set_row_highlight(row, active=False)
        finally:
            self.itemChanged.connect(self._on_item_changed)
        self.sizes_changed.emit()

    def _set_row_highlight(self, row: int, active: bool) -> None:
        color = _OVERRIDE_BG if active else QColor(Qt.GlobalColor.transparent)
        for col in (_COL_CHECK, _COL_SIZE, _COL_SOURCE):
            item = self.item(row, col)
            if item:
                item.setBackground(color)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if item.column() == _COL_CHECK:
            self.sizes_changed.emit()

    def _on_browse(self, size: int) -> None:
        # Parent to the top-level window so focus returns there after close.
        # Using self (a child widget) as parent can break focus on WSLg.
        path, _ = QFileDialog.getOpenFileName(
            self.window(), f"Zrodlo dla {size}x{size}", "", _DIALOG_FILTER
        )
        if path:
            self._set_override(size, Path(path))

    def _on_context_menu(self, pos: QPoint) -> None:
        row = self.rowAt(pos.y())
        col = self.columnAt(pos.x())
        if row < 0 or col != _COL_SOURCE:
            return
        size = self._sizes[row]
        if size not in self._overrides:
            return
        menu = QMenu(self)
        action = menu.addAction("Usuń override")
        if menu.exec(self.viewport().mapToGlobal(pos)) is action:
            self._clear_override(size)

    # ------------------------------------------------------------------
    # Drag & drop (handled via viewport event filter, not the table itself,
    # to avoid cursor interference from QAbstractItemView's drag machinery)
    # ------------------------------------------------------------------

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if obj is self.viewport():
            t = event.type()
            if t == QEvent.Type.DragEnter:
                de = event  # QDragEnterEvent
                assert isinstance(de, QDragEnterEvent)
                if de.mimeData().hasUrls():
                    urls = de.mimeData().urls()
                    if urls and Path(urls[0].toLocalFile()).suffix.lower() in _SUPPORTED_SUFFIXES:
                        de.acceptProposedAction()
                        return True
                de.ignore()
                return True
            if t == QEvent.Type.DragMove:
                dm = event  # QDragMoveEvent
                assert isinstance(dm, QDragMoveEvent)
                if dm.mimeData().hasUrls():
                    dm.acceptProposedAction()
                else:
                    dm.ignore()
                return True
            if t == QEvent.Type.Drop:
                drop = event  # QDropEvent
                assert isinstance(drop, QDropEvent)
                urls = drop.mimeData().urls()
                if urls:
                    path = Path(urls[0].toLocalFile())
                    row = self.rowAt(drop.position().toPoint().y())
                    if 0 <= row < len(self._sizes):
                        self._set_override(self._sizes[row], path)
                drop.acceptProposedAction()
                return True
        return bool(super().eventFilter(obj, event))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def checked_sizes(self) -> list[int]:
        result: list[int] = []
        for row, size in enumerate(self._sizes):
            item = self.item(row, _COL_CHECK)
            if item and item.checkState() == Qt.CheckState.Checked:
                result.append(size)
        return sorted(result)

    def set_checked_sizes(self, sizes: frozenset[int]) -> None:
        """Set which rows are checked without triggering the preset-reset logic."""
        self.itemChanged.disconnect(self._on_item_changed)
        for row, size in enumerate(self._sizes):
            item = self.item(row, _COL_CHECK)
            if item:
                item.setCheckState(
                    Qt.CheckState.Checked if size in sizes else Qt.CheckState.Unchecked
                )
        self.itemChanged.connect(self._on_item_changed)

    def get_size_specs(self) -> tuple[SizeSpec, ...]:
        """Return checked sizes as SizeSpec tuples, including any overrides."""
        specs: list[SizeSpec] = []
        for row, size in enumerate(self._sizes):
            item = self.item(row, _COL_CHECK)
            if item and item.checkState() == Qt.CheckState.Checked:
                override = self._overrides.get(size)
                specs.append(SizeSpec(size, size, source_override=override))
        return tuple(specs) if specs else (SizeSpec(32, 32),)


class SettingsPanel(QWidget):
    """Conversion settings: sizes, preset, resample algorithm, background."""

    settings_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._updating_preset: bool = False
        self._bg_color: Color = Color(255, 255, 255)

        self._size_table: SizeTable
        self._preset_buttons: dict[str, QRadioButton]
        self._resample_buttons: dict[ResampleAlgorithm, QRadioButton]
        self._radio_transparent: QRadioButton
        self._radio_color: QRadioButton
        self._color_btn: QPushButton
        self._auto_trim_check: QCheckBox
        self._trim_padding_spin: QSpinBox
        self._remove_bg_check: QCheckBox

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        layout.addWidget(self._make_sizes_group())
        layout.addWidget(self._make_preset_group())
        layout.addWidget(self._make_resample_group())
        layout.addWidget(self._make_background_group())
        layout.addWidget(self._make_trim_group())
        bg_group = self._make_bg_remove_group()
        if bg_group is not None:
            layout.addWidget(bg_group)
        layout.addStretch()

    # ------------------------------------------------------------------
    # Group builders
    # ------------------------------------------------------------------

    def _make_sizes_group(self) -> QGroupBox:
        group = QGroupBox("Rozmiary")
        vbox = QVBoxLayout(group)
        vbox.setContentsMargins(4, 4, 4, 4)
        vbox.setSpacing(0)

        self._size_table = SizeTable()
        self._size_table.sizes_changed.connect(self._on_size_table_changed)
        vbox.addWidget(self._size_table)

        return group

    def _make_preset_group(self) -> QGroupBox:
        group = QGroupBox("Preset")
        vbox = QVBoxLayout(group)
        vbox.setContentsMargins(8, 8, 8, 8)
        vbox.setSpacing(2)

        self._preset_buttons = {}
        for name in _PRESETS:
            rb = QRadioButton(name)
            rb.toggled.connect(
                lambda checked, n=name: self._on_preset_changed(n) if checked else None
            )
            self._preset_buttons[name] = rb
            vbox.addWidget(rb)
        self._preset_buttons["Custom"].setChecked(True)

        return group

    def _make_resample_group(self) -> QGroupBox:
        group = QGroupBox("Algorytm skalowania")
        vbox = QVBoxLayout(group)
        vbox.setContentsMargins(8, 8, 8, 8)
        vbox.setSpacing(2)

        self._resample_buttons = {}
        for algo in ResampleAlgorithm:
            rb = QRadioButton(algo.value.capitalize())
            rb.setToolTip(_RESAMPLE_TOOLTIPS[algo])
            rb.toggled.connect(
                lambda checked, a=algo: self._on_resample_changed(a) if checked else None
            )
            self._resample_buttons[algo] = rb
            vbox.addWidget(rb)
        self._resample_buttons[ResampleAlgorithm.LANCZOS].setChecked(True)

        return group

    def _make_background_group(self) -> QGroupBox:
        group = QGroupBox("Tło dla braku alpha")
        vbox = QVBoxLayout(group)
        vbox.setContentsMargins(8, 8, 8, 8)
        vbox.setSpacing(4)

        self._radio_transparent = QRadioButton("Przezroczyste")
        self._radio_transparent.setChecked(True)
        self._radio_transparent.toggled.connect(self._on_bg_radio_toggled)
        vbox.addWidget(self._radio_transparent)

        self._radio_color = QRadioButton("Kolor")
        self._radio_color.toggled.connect(self._on_bg_radio_toggled)

        self._color_btn = QPushButton()
        self._color_btn.setFixedWidth(32)
        self._color_btn.setEnabled(False)
        self._update_color_button()
        self._color_btn.clicked.connect(self._on_color_button_clicked)

        hbox = QHBoxLayout()
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.addWidget(self._radio_color)
        hbox.addWidget(self._color_btn)
        hbox.addStretch()
        vbox.addLayout(hbox)

        return group

    def _make_bg_remove_group(self) -> QGroupBox | None:
        """Return a group box for AI bg removal, or None if rembg is not installed."""
        from icoforge.core.bg_remover import MODEL_DOWNLOAD_WARNING, is_available

        if not is_available():
            return None

        group = QGroupBox("Usuwanie tla (AI)")
        vbox = QVBoxLayout(group)
        vbox.setContentsMargins(8, 8, 8, 8)
        vbox.setSpacing(4)

        self._remove_bg_check = QCheckBox("Usun tlo (U2-Net)")
        self._remove_bg_check.setToolTip(
            MODEL_DOWNLOAD_WARNING + "\n\nModel jest pobierany tylko raz i zapisywany w ~/.u2net/."
        )
        self._remove_bg_check.toggled.connect(self._on_remove_bg_toggled)
        vbox.addWidget(self._remove_bg_check)

        note = QLabel("<small><i>Pierwsze uzycie: pobieranie modelu ~170 MB</i></small>")
        note.setWordWrap(True)
        vbox.addWidget(note)

        return group

    def _make_trim_group(self) -> QGroupBox:
        group = QGroupBox("Przycinanie")
        vbox = QVBoxLayout(group)
        vbox.setContentsMargins(8, 8, 8, 8)
        vbox.setSpacing(4)

        self._auto_trim_check = QCheckBox("Auto-trim (usuń przezroczyste krawędzie)")
        self._auto_trim_check.setToolTip(
            "Automatycznie przycina przezroczyste obramowanie źródła przed skalowaniem."
        )
        self._auto_trim_check.toggled.connect(self._on_trim_toggled)
        vbox.addWidget(self._auto_trim_check)

        hbox = QHBoxLayout()
        hbox.setContentsMargins(0, 0, 0, 0)
        padding_label = QLabel("Padding:")
        self._trim_padding_spin = QSpinBox()
        self._trim_padding_spin.setRange(0, 128)
        self._trim_padding_spin.setValue(0)
        self._trim_padding_spin.setSuffix(" px")
        self._trim_padding_spin.setEnabled(False)
        self._trim_padding_spin.setToolTip(
            "Piksele przezroczystego marginesu dodawane po każdej stronie przyciętego obrazu."
        )
        self._trim_padding_spin.valueChanged.connect(self._on_trim_padding_changed)
        hbox.addWidget(padding_label)
        hbox.addWidget(self._trim_padding_spin)
        hbox.addStretch()
        vbox.addLayout(hbox)

        return group

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_config(self) -> IcoConfig:
        """Return IcoConfig built from the current panel state."""
        sizes = self._size_table.get_size_specs()

        resample = next(
            (algo for algo, rb in self._resample_buttons.items() if rb.isChecked()),
            ResampleAlgorithm.LANCZOS,
        )

        background: Background = (
            TRANSPARENT if self._radio_transparent.isChecked() else self._bg_color
        )

        auto_trim = self._auto_trim_check.isChecked()
        trim_padding = self._trim_padding_spin.value() if auto_trim else 0

        remove_bg = hasattr(self, "_remove_bg_check") and self._remove_bg_check.isChecked()

        return IcoConfig(
            sizes=sizes,
            resample=resample,
            background=background,
            auto_trim=auto_trim,
            auto_trim_padding=trim_padding,
            remove_bg=remove_bg,
        )

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_size_table_changed(self) -> None:
        if self._updating_preset:
            return
        self._updating_preset = True
        self._preset_buttons["Custom"].setChecked(True)
        self._updating_preset = False
        self.settings_changed.emit()

    def _on_preset_changed(self, name: str) -> None:
        if self._updating_preset:
            return
        sizes = _PRESETS.get(name)
        if sizes is None:
            self.settings_changed.emit()
            return
        self._updating_preset = True
        self._size_table.set_checked_sizes(sizes)
        self._updating_preset = False
        self.settings_changed.emit()

    def _on_resample_changed(self, _algo: ResampleAlgorithm) -> None:
        self.settings_changed.emit()

    def _on_remove_bg_toggled(self, _checked: bool) -> None:
        self.settings_changed.emit()

    def _on_trim_toggled(self, checked: bool) -> None:
        self._trim_padding_spin.setEnabled(checked)
        self.settings_changed.emit()

    def _on_trim_padding_changed(self, _value: int) -> None:
        self.settings_changed.emit()

    def _on_bg_radio_toggled(self, checked: bool) -> None:
        self._color_btn.setEnabled(self._radio_color.isChecked())
        if checked:
            self.settings_changed.emit()

    def _on_color_button_clicked(self) -> None:
        initial = QColor(self._bg_color.r, self._bg_color.g, self._bg_color.b)
        color = QColorDialog.getColor(initial, self, "Wybierz kolor tła")
        if color.isValid():
            self._bg_color = Color(color.red(), color.green(), color.blue())
            self._update_color_button()
            self.settings_changed.emit()

    def _update_color_button(self) -> None:
        c = self._bg_color
        self._color_btn.setStyleSheet(
            f"background-color: rgb({c.r}, {c.g}, {c.b}); border: 1px solid #888;"
        )
