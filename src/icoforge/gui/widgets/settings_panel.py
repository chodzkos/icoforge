"""Left-column settings panel with conversion options."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
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
        self._preset_buttons: dict[str, QRadioButton]
        self._resample_buttons: dict[ResampleAlgorithm, QRadioButton]
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

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_config(self) -> IcoConfig:
        """Return IcoConfig built from the current panel state."""
        checked = sorted(s for s, cb in self._size_checks.items() if cb.isChecked())
        sizes = tuple(SizeSpec(s, s) for s in checked) or (SizeSpec(32, 32),)

        resample = next(
            (algo for algo, rb in self._resample_buttons.items() if rb.isChecked()),
            ResampleAlgorithm.LANCZOS,
        )

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
        for size, cb in self._size_checks.items():
            cb.setChecked(size in sizes)
        self._updating_preset = False
        self.settings_changed.emit()

    def _on_resample_changed(self, _algo: ResampleAlgorithm) -> None:
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
