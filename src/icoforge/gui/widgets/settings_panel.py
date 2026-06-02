"""Left-column settings panel with conversion options."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QPoint, Qt, Signal
from PySide6.QtGui import QColor, QDragEnterEvent, QDragMoveEvent, QDropEvent, QPalette
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMenu,
    QMessageBox,
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
from icoforge.core.presets import (
    BUILTIN_PRESETS,
    list_user_presets,
    load_preset,
    save_preset,
)
from icoforge.utils.settings import get_setting

_ALL_SIZES: tuple[int, ...] = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)
_DEFAULT_SIZES: frozenset[int] = frozenset({16, 32, 48, 256})
_CUSTOM_PRESET_NAME = "Niestandardowy"
_SETTINGS_KEY_DEFAULT_PRESET = "default_preset"

_RESAMPLE_TOOLTIPS: dict[ResampleAlgorithm, str] = {
    ResampleAlgorithm.LANCZOS: "Wysoka jakość, najlepszy dla zdjęć i grafiki",
    ResampleAlgorithm.BICUBIC: "Płynna interpolacja, dobry wybór ogólny",
    ResampleAlgorithm.BILINEAR: "Szybki, wystarczający dla małych ikon",
    ResampleAlgorithm.NEAREST: "Bez interpolacji, zachowuje ostre krawędzie (pixel art)",
    ResampleAlgorithm.BOX: "Szybki i ostry przy dużym zmniejszaniu",
}

_OVERRIDE_BG = QColor(200, 230, 255)
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

# Item data roles for the preset combo box
_ROLE_PRESET_TYPE = Qt.ItemDataRole.UserRole  # "builtin" | "user" | "custom"
_ROLE_PRESET_NAME = Qt.ItemDataRole.UserRole + 1  # str: canonical name


class SizeTable(QTableWidget):
    """Per-size table: enable/disable each ICO size and assign a source override."""

    sizes_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(len(_ALL_SIZES), 4, parent)
        self._sizes: tuple[int, ...] = _ALL_SIZES
        self._overrides: dict[int, Path] = {}
        self._setup()
        self._populate()
        from icoforge.utils.theme import get_theme_manager

        mgr = get_theme_manager()
        if mgr is not None:
            mgr.theme_changed.connect(self._refresh_source_foregrounds)

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _setup(self) -> None:
        self.setHorizontalHeaderLabels(["✓", self.tr("Rozmiar"), self.tr("Źródło"), ""])
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

        self.viewport().setAcceptDrops(True)
        self.viewport().installEventFilter(self)

    def _populate(self) -> None:
        for row, size in enumerate(self._sizes):
            check = QTableWidgetItem()
            check.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            check.setCheckState(
                Qt.CheckState.Checked if size in _DEFAULT_SIZES else Qt.CheckState.Unchecked
            )
            check.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(row, _COL_CHECK, check)

            size_item = QTableWidgetItem(f"{size}x{size}")
            size_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(row, _COL_SIZE, size_item)

            src_item = QTableWidgetItem(self.tr("(domyślne)"))
            src_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            src_item.setForeground(self.palette().color(QPalette.ColorRole.PlaceholderText))
            self.setItem(row, _COL_SOURCE, src_item)

            btn = QPushButton(self.tr("Wybierz…"))
            btn.setFixedHeight(22)
            btn.clicked.connect(lambda _checked, s=size: self._on_browse(s))
            self.setCellWidget(row, _COL_BTN, btn)

            self.setRowHeight(row, 26)

        self.itemChanged.connect(self._on_item_changed)

    def _refresh_source_foregrounds(self, _theme: str = "") -> None:
        placeholder_color = self.palette().color(QPalette.ColorRole.PlaceholderText)
        text_color = self.palette().color(QPalette.ColorRole.Text)
        for row in range(self.rowCount()):
            item = self.item(row, _COL_SOURCE)
            if item is None:
                continue
            if item.text() == self.tr("(domyślne)"):
                item.setForeground(placeholder_color)
            else:
                item.setForeground(text_color)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _row_for_size(self, size: int) -> int:
        return self._sizes.index(size)

    def _set_override(self, size: int, path: Path) -> None:
        self._overrides[size] = path
        row = self._row_for_size(size)
        self.itemChanged.disconnect(self._on_item_changed)
        try:
            item = self.item(row, _COL_SOURCE)
            if item:
                item.setText(path.name)
                item.setToolTip(str(path))
                item.setForeground(self.palette().color(QPalette.ColorRole.Text))
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
                item.setText(self.tr("(domyślne)"))
                item.setToolTip("")
                item.setForeground(self.palette().color(QPalette.ColorRole.PlaceholderText))
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
        from icoforge.utils.theme import get_theme_manager
        from icoforge.utils.window_theme import apply_theme_to_dialog

        dlg = QFileDialog(
            self.window(),
            self.tr("Źródło dla %1x%2").replace("%1", str(size)).replace("%2", str(size)),
        )
        dlg.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        dlg.setNameFilter(_DIALOG_FILTER)
        apply_theme_to_dialog(dlg, get_theme_manager())
        if dlg.exec() and dlg.selectedFiles():
            self._set_override(size, Path(dlg.selectedFiles()[0]))

    def _on_context_menu(self, pos: QPoint) -> None:
        row = self.rowAt(pos.y())
        col = self.columnAt(pos.x())
        if row < 0 or col != _COL_SOURCE:
            return
        size = self._sizes[row]
        if size not in self._overrides:
            return
        menu = QMenu(self)
        action = menu.addAction(self.tr("Usuń nadpisanie"))
        if menu.exec(self.viewport().mapToGlobal(pos)) is action:
            self._clear_override(size)

    # ------------------------------------------------------------------
    # Drag & drop
    # ------------------------------------------------------------------

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if obj is self.viewport():
            t = event.type()
            if t == QEvent.Type.DragEnter:
                de = event
                assert isinstance(de, QDragEnterEvent)
                if de.mimeData().hasUrls():
                    urls = de.mimeData().urls()
                    if urls and Path(urls[0].toLocalFile()).suffix.lower() in _SUPPORTED_SUFFIXES:
                        de.acceptProposedAction()
                        return True
                de.ignore()
                return True
            if t == QEvent.Type.DragMove:
                dm = event
                assert isinstance(dm, QDragMoveEvent)
                if dm.mimeData().hasUrls():
                    dm.acceptProposedAction()
                else:
                    dm.ignore()
                return True
            if t == QEvent.Type.Drop:
                drop = event
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
        self.itemChanged.disconnect(self._on_item_changed)
        for row, size in enumerate(self._sizes):
            item = self.item(row, _COL_CHECK)
            if item:
                item.setCheckState(
                    Qt.CheckState.Checked if size in sizes else Qt.CheckState.Unchecked
                )
        self.itemChanged.connect(self._on_item_changed)

    def get_size_specs(self) -> tuple[SizeSpec, ...]:
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

        self._loading_preset: bool = False
        self._bg_color: Color = Color(255, 255, 255)

        self._size_table: SizeTable
        self._preset_combo: QComboBox
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

        self._load_default_preset()

    # ------------------------------------------------------------------
    # Group builders
    # ------------------------------------------------------------------

    def _make_sizes_group(self) -> QGroupBox:
        group = QGroupBox(self.tr("Rozmiary"))
        vbox = QVBoxLayout(group)
        vbox.setContentsMargins(4, 4, 4, 4)
        vbox.setSpacing(0)

        self._size_table = SizeTable()
        self._size_table.sizes_changed.connect(self._on_size_table_changed)
        vbox.addWidget(self._size_table)

        return group

    def _make_preset_group(self) -> QGroupBox:
        group = QGroupBox(self.tr("Preset"))
        vbox = QVBoxLayout(group)
        vbox.setContentsMargins(8, 8, 8, 8)
        vbox.setSpacing(4)

        self._preset_combo = QComboBox()
        self._preset_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self._refresh_preset_combo(select_custom=True)
        self._preset_combo.currentIndexChanged.connect(self._on_preset_combo_changed)
        vbox.addWidget(self._preset_combo)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(4)

        save_btn = QPushButton(self.tr("Zapisz preset…"))
        save_btn.clicked.connect(self._save_preset_dialog)
        btn_row.addWidget(save_btn)

        manage_btn = QPushButton(self.tr("Zarządzaj…"))
        manage_btn.clicked.connect(self._manage_presets_dialog)
        btn_row.addWidget(manage_btn)

        vbox.addLayout(btn_row)
        return group

    def _make_resample_group(self) -> QGroupBox:
        group = QGroupBox(self.tr("Algorytm skalowania"))
        vbox = QVBoxLayout(group)
        vbox.setContentsMargins(8, 8, 8, 8)
        vbox.setSpacing(2)

        self._resample_buttons = {}
        for algo in ResampleAlgorithm:
            rb = QRadioButton(algo.value.capitalize())
            rb.setToolTip(self.tr(_RESAMPLE_TOOLTIPS[algo]))
            rb.toggled.connect(
                lambda checked, a=algo: self._on_resample_changed(a) if checked else None
            )
            self._resample_buttons[algo] = rb
            vbox.addWidget(rb)
        self._resample_buttons[ResampleAlgorithm.LANCZOS].setChecked(True)

        return group

    def _make_background_group(self) -> QGroupBox:
        group = QGroupBox(self.tr("Tło dla braku alpha"))
        vbox = QVBoxLayout(group)
        vbox.setContentsMargins(8, 8, 8, 8)
        vbox.setSpacing(4)

        self._radio_transparent = QRadioButton(self.tr("Przezroczyste"))
        self._radio_transparent.setChecked(True)
        self._radio_transparent.toggled.connect(self._on_bg_radio_toggled)
        vbox.addWidget(self._radio_transparent)

        self._radio_color = QRadioButton(self.tr("Kolor"))
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
        from icoforge.core.bg_remover import MODEL_DOWNLOAD_WARNING, is_available

        if not is_available():
            return None

        group = QGroupBox(self.tr("Usuwanie tła (AI)"))
        vbox = QVBoxLayout(group)
        vbox.setContentsMargins(8, 8, 8, 8)
        vbox.setSpacing(4)

        self._remove_bg_check = QCheckBox(self.tr("Usuń tło (U2-Net)"))
        self._remove_bg_check.setToolTip(
            self.tr(MODEL_DOWNLOAD_WARNING)
            + "\n\n"
            + self.tr("Model jest pobierany tylko raz i zapisywany w ~/.u2net/.")
        )
        self._remove_bg_check.toggled.connect(self._on_remove_bg_toggled)
        vbox.addWidget(self._remove_bg_check)

        note = QLabel(
            "<small><i>" + self.tr("Pierwsze użycie: pobieranie modelu ~170 MB") + "</i></small>"
        )
        note.setWordWrap(True)
        vbox.addWidget(note)

        return group

    def _make_trim_group(self) -> QGroupBox:
        group = QGroupBox(self.tr("Przycinanie"))
        vbox = QVBoxLayout(group)
        vbox.setContentsMargins(8, 8, 8, 8)
        vbox.setSpacing(4)

        self._auto_trim_check = QCheckBox(self.tr("Auto-trim (usuń przezroczyste krawędzie)"))
        self._auto_trim_check.setToolTip(
            self.tr("Automatycznie przycina przezroczyste obramowanie źródła przed skalowaniem.")
        )
        self._auto_trim_check.toggled.connect(self._on_trim_toggled)
        vbox.addWidget(self._auto_trim_check)

        hbox = QHBoxLayout()
        hbox.setContentsMargins(0, 0, 0, 0)
        padding_label = QLabel(self.tr("Padding:"))
        self._trim_padding_spin = QSpinBox()
        self._trim_padding_spin.setRange(0, 128)
        self._trim_padding_spin.setValue(0)
        self._trim_padding_spin.setSuffix(" px")
        self._trim_padding_spin.setEnabled(False)
        self._trim_padding_spin.setToolTip(
            self.tr(
                "Piksele przezroczystego marginesu dodawane po każdej stronie przyciętego obrazu."
            )
        )
        self._trim_padding_spin.valueChanged.connect(self._on_trim_padding_changed)
        hbox.addWidget(padding_label)
        hbox.addWidget(self._trim_padding_spin)
        hbox.addStretch()
        vbox.addLayout(hbox)

        return group

    # ------------------------------------------------------------------
    # Preset combo helpers
    # ------------------------------------------------------------------

    def _refresh_preset_combo(self, select_custom: bool = False) -> None:
        """Rebuild the preset combo box contents from builtins + user presets."""
        self._preset_combo.blockSignals(True)
        self._preset_combo.clear()

        # Index 0: custom
        self._preset_combo.addItem(self.tr(_CUSTOM_PRESET_NAME))
        model = self._preset_combo.model()
        assert model is not None
        model.setData(model.index(0, 0), "custom", _ROLE_PRESET_TYPE)
        model.setData(model.index(0, 0), _CUSTOM_PRESET_NAME, _ROLE_PRESET_NAME)

        # Separator + built-ins
        self._preset_combo.insertSeparator(1)
        for name, _config in BUILTIN_PRESETS.items():
            idx = self._preset_combo.count()
            self._preset_combo.addItem(f"🔒 {name}")
            model.setData(model.index(idx, 0), "builtin", _ROLE_PRESET_TYPE)
            model.setData(model.index(idx, 0), name, _ROLE_PRESET_NAME)

        # User presets (separator only if any exist)
        user = list_user_presets()
        if user:
            self._preset_combo.insertSeparator(self._preset_combo.count())
            for name in user:
                idx = self._preset_combo.count()
                self._preset_combo.addItem(name)
                model.setData(model.index(idx, 0), "user", _ROLE_PRESET_TYPE)
                model.setData(model.index(idx, 0), name, _ROLE_PRESET_NAME)

        if select_custom:
            self._preset_combo.setCurrentIndex(0)

        self._preset_combo.blockSignals(False)

    def _find_combo_index(self, preset_type: str, name: str) -> int:
        """Return the combo index for the given preset type+name, or 0 if not found."""
        model = self._preset_combo.model()
        assert model is not None
        for i in range(self._preset_combo.count()):
            if (
                model.data(model.index(i, 0), _ROLE_PRESET_TYPE) == preset_type
                and model.data(model.index(i, 0), _ROLE_PRESET_NAME) == name
            ):
                return i
        return 0

    def _select_preset_in_combo(self, preset_type: str, name: str) -> None:
        """Set the combo to the given preset without triggering load logic."""
        self._preset_combo.blockSignals(True)
        self._preset_combo.setCurrentIndex(self._find_combo_index(preset_type, name))
        self._preset_combo.blockSignals(False)

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

    def load_config(self, config: IcoConfig) -> None:
        """Populate all panel widgets from *config* without emitting settings_changed.

        Callers should set the preset combo themselves before or after this call.
        """
        self._loading_preset = True
        try:
            self._size_table.set_checked_sizes(frozenset(s.width for s in config.sizes))

            rb = self._resample_buttons.get(config.resample)
            if rb:
                rb.setChecked(True)

            if config.background is TRANSPARENT:
                self._radio_transparent.setChecked(True)
            else:
                self._radio_color.setChecked(True)
                bg = config.background
                assert isinstance(bg, Color)
                self._bg_color = bg
                self._update_color_button()
                self._color_btn.setEnabled(True)

            self._auto_trim_check.setChecked(config.auto_trim)
            self._trim_padding_spin.setValue(config.auto_trim_padding)
            self._trim_padding_spin.setEnabled(config.auto_trim)
        finally:
            self._loading_preset = False

        self.settings_changed.emit()

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_size_table_changed(self) -> None:
        if self._loading_preset:
            return
        self._select_preset_in_combo("custom", _CUSTOM_PRESET_NAME)
        self.settings_changed.emit()

    def _on_preset_combo_changed(self, index: int) -> None:
        if self._loading_preset:
            return
        model = self._preset_combo.model()
        assert model is not None
        preset_type = model.data(model.index(index, 0), _ROLE_PRESET_TYPE)
        preset_name = model.data(model.index(index, 0), _ROLE_PRESET_NAME)
        if preset_type is None:
            # Separator or invalid item — revert to custom
            self._preset_combo.blockSignals(True)
            self._preset_combo.setCurrentIndex(0)
            self._preset_combo.blockSignals(False)
            return
        if preset_type == "custom":
            self.settings_changed.emit()
            return
        if preset_type == "builtin":
            config = BUILTIN_PRESETS.get(preset_name)
            if config is not None:
                self.load_config(config)
                self._select_preset_in_combo("builtin", preset_name)
            return
        if preset_type == "user":
            try:
                config = load_preset(preset_name)
                self.load_config(config)
                self._select_preset_in_combo("user", preset_name)
            except (FileNotFoundError, ValueError) as exc:
                QMessageBox.warning(
                    self,
                    self.tr("Błąd wczytywania presetu"),
                    self.tr("Nie można wczytać presetu:\n%1").replace("%1", str(exc)),
                )
                self._select_preset_in_combo("custom", _CUSTOM_PRESET_NAME)

    def _on_resample_changed(self, _algo: ResampleAlgorithm) -> None:
        if not self._loading_preset:
            self._select_preset_in_combo("custom", _CUSTOM_PRESET_NAME)
        self.settings_changed.emit()

    def _on_remove_bg_toggled(self, _checked: bool) -> None:
        self.settings_changed.emit()

    def _on_trim_toggled(self, checked: bool) -> None:
        self._trim_padding_spin.setEnabled(checked)
        if not self._loading_preset:
            self._select_preset_in_combo("custom", _CUSTOM_PRESET_NAME)
        self.settings_changed.emit()

    def _on_trim_padding_changed(self, _value: int) -> None:
        if not self._loading_preset:
            self._select_preset_in_combo("custom", _CUSTOM_PRESET_NAME)
        self.settings_changed.emit()

    def _on_bg_radio_toggled(self, checked: bool) -> None:
        self._color_btn.setEnabled(self._radio_color.isChecked())
        if not self._loading_preset:
            self._select_preset_in_combo("custom", _CUSTOM_PRESET_NAME)
        if checked:
            self.settings_changed.emit()

    def _on_color_button_clicked(self) -> None:
        initial = QColor(self._bg_color.r, self._bg_color.g, self._bg_color.b)
        color = QColorDialog.getColor(initial, self, self.tr("Wybierz kolor tła"))
        if color.isValid():
            self._bg_color = Color(color.red(), color.green(), color.blue())
            self._update_color_button()
            self._select_preset_in_combo("custom", _CUSTOM_PRESET_NAME)
            self.settings_changed.emit()

    def _update_color_button(self) -> None:
        c = self._bg_color
        self._color_btn.setStyleSheet(
            f"background-color: rgb({c.r}, {c.g}, {c.b}); border: 1px solid #888;"
        )

    # ------------------------------------------------------------------
    # Preset dialogs
    # ------------------------------------------------------------------

    def _save_preset_dialog(self) -> None:
        """Show an input dialog and save the current config as a named preset."""
        from icoforge.utils.theme import get_theme_manager
        from icoforge.utils.window_theme import apply_theme_to_dialog

        mgr = get_theme_manager()

        input_dlg = QInputDialog(self)
        input_dlg.setWindowTitle(self.tr("Zapisz preset"))
        input_dlg.setLabelText(self.tr("Nazwa presetu:"))
        apply_theme_to_dialog(input_dlg, mgr)
        if input_dlg.exec() != QInputDialog.DialogCode.Accepted:
            return
        name = input_dlg.textValue().strip()
        if not name:
            return

        if name in BUILTIN_PRESETS:
            warn = QMessageBox(self)
            warn.setWindowTitle(self.tr("Nazwa zarezerwowana"))
            warn.setText(
                self.tr('Nie można nadpisać wbudowanego presetu "%1".').replace("%1", name)
            )
            apply_theme_to_dialog(warn, mgr)
            warn.exec()
            return

        user_presets = list_user_presets()
        if name in user_presets:
            confirm = QMessageBox(self)
            confirm.setWindowTitle(self.tr("Nadpisać?"))
            confirm.setText(self.tr('Preset "%1" już istnieje. Nadpisać?').replace("%1", name))
            confirm.setStandardButtons(
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            apply_theme_to_dialog(confirm, mgr)
            if confirm.exec() != QMessageBox.StandardButton.Yes:
                return

        save_preset(name, self.get_config())
        self._refresh_preset_combo()
        self._select_preset_in_combo("user", name)

    def _manage_presets_dialog(self) -> None:
        """Open the preset manager dialog."""
        from icoforge.gui.widgets.presets_manager_dialog import PresetsManagerDialog

        dlg = PresetsManagerDialog(self)
        dlg.exec()
        # Reload combo in case the user renamed/deleted/set default
        idx = self._preset_combo.currentIndex()
        combo_model = self._preset_combo.model()
        if combo_model is not None:
            midx = combo_model.index(idx, 0)
            current_type = combo_model.data(midx, _ROLE_PRESET_TYPE)
            current_name = combo_model.data(midx, _ROLE_PRESET_NAME)
        else:
            current_type = current_name = None
        self._refresh_preset_combo()
        if current_type and current_name:
            self._select_preset_in_combo(current_type, current_name)

    def _load_default_preset(self) -> None:
        """If a default preset is configured, load it into the panel."""
        default = get_setting(_SETTINGS_KEY_DEFAULT_PRESET, "")
        if not default:
            return
        if default in BUILTIN_PRESETS:
            config = BUILTIN_PRESETS[default]
            self.load_config(config)
            self._select_preset_in_combo("builtin", default)
        else:
            try:
                config = load_preset(default)
                self.load_config(config)
                self._select_preset_in_combo("user", default)
            except (FileNotFoundError, ValueError):
                pass  # stale default — ignore silently


# Re-export so callers that imported from here still work
__all__ = ["_SETTINGS_KEY_DEFAULT_PRESET", "SettingsPanel", "SizeTable"]
