"""Left-column settings panel with conversion options."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QPushButton,
    QRadioButton,
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


class SettingsPanel(QWidget):
    """Conversion settings: sizes, preset, resample algorithm, background."""

    settings_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._updating_preset: bool = False
        self._bg_color: Color = Color(255, 255, 255)

        # Declared here; assigned in the _make_* helpers called below.
        self._size_checks: dict[int, QCheckBox]
        self._preset_combo: QComboBox
        self._resample_combo: QComboBox
        self._radio_transparent: QRadioButton
        self._radio_color: QRadioButton
        self._color_btn: QPushButton

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        layout.addWidget(self._make_sizes_group())
        layout.addWidget(self._make_preset_group())
        layout.addWidget(self._make_resample_group())
        layout.addWidget(self._make_background_group())
        layout.addStretch()

    # ------------------------------------------------------------------
    # Group builders
    # ------------------------------------------------------------------

    def _make_sizes_group(self) -> QGroupBox:
        group = QGroupBox("Rozmiary")
        grid = QGridLayout(group)
        grid.setSpacing(4)

        self._size_checks = {}
        for i, size in enumerate(_ALL_SIZES):
            cb = QCheckBox(str(size))
            cb.setChecked(size in _DEFAULT_SIZES)
            cb.toggled.connect(self._on_size_toggled)
            self._size_checks[size] = cb
            grid.addWidget(cb, i // 2, i % 2)

        return group

    def _make_preset_group(self) -> QGroupBox:
        group = QGroupBox("Preset")
        vbox = QVBoxLayout(group)
        vbox.setContentsMargins(8, 8, 8, 8)

        self._preset_combo = QComboBox()
        for name in _PRESETS:
            self._preset_combo.addItem(name)
        self._preset_combo.currentTextChanged.connect(self._on_preset_changed)
        vbox.addWidget(self._preset_combo)

        return group

    def _make_resample_group(self) -> QGroupBox:
        group = QGroupBox("Algorytm skalowania")
        vbox = QVBoxLayout(group)
        vbox.setContentsMargins(8, 8, 8, 8)

        self._resample_combo = QComboBox()
        for algo in ResampleAlgorithm:
            self._resample_combo.addItem(algo.value.capitalize(), userData=algo)
        idx = self._resample_combo.findData(ResampleAlgorithm.LANCZOS)
        if idx >= 0:
            self._resample_combo.setCurrentIndex(idx)
        self._resample_combo.setToolTip(_RESAMPLE_TOOLTIPS[ResampleAlgorithm.LANCZOS])
        self._resample_combo.currentIndexChanged.connect(self._on_resample_index_changed)
        vbox.addWidget(self._resample_combo)

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

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_config(self) -> IcoConfig:
        """Return IcoConfig built from the current panel state."""
        checked = sorted(s for s, cb in self._size_checks.items() if cb.isChecked())
        sizes = tuple(SizeSpec(s, s) for s in checked) or (SizeSpec(32, 32),)

        raw = self._resample_combo.currentData()
        resample = raw if isinstance(raw, ResampleAlgorithm) else ResampleAlgorithm.LANCZOS

        background: Background = (
            TRANSPARENT if self._radio_transparent.isChecked() else self._bg_color
        )

        return IcoConfig(sizes=sizes, resample=resample, background=background)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_size_toggled(self, _checked: bool) -> None:
        if self._updating_preset:
            return
        # Switch combo to Custom when user manually changes a checkbox.
        self._updating_preset = True
        idx = self._preset_combo.findText("Custom")
        if idx >= 0:
            self._preset_combo.setCurrentIndex(idx)
        self._updating_preset = False
        self.settings_changed.emit()

    def _on_preset_changed(self, name: str) -> None:
        if self._updating_preset:
            return
        sizes = _PRESETS.get(name)
        if sizes is None:
            # "Custom" selected — nothing to update.
            self.settings_changed.emit()
            return
        self._updating_preset = True
        for size, cb in self._size_checks.items():
            cb.setChecked(size in sizes)
        self._updating_preset = False
        self.settings_changed.emit()

    def _on_resample_index_changed(self, _index: int) -> None:
        raw = self._resample_combo.currentData()
        if isinstance(raw, ResampleAlgorithm):
            self._resample_combo.setToolTip(_RESAMPLE_TOOLTIPS.get(raw, ""))
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
