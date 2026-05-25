"""Dialog for creating a new blank ICO document."""

from __future__ import annotations

import io

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from icoforge.core.models import SizeSpec

AVAILABLE_SIZES: list[int] = [16, 20, 24, 32, 40, 48, 64, 96, 128, 256]
_DEFAULT_SIZES: frozenset[int] = frozenset({16, 32, 48, 256})


class NewIcoDialog(QDialog):
    """Dialog to configure and create a new ICO document."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Nowe ICO")
        self.setMinimumWidth(440)

        self._bg_color = QColor(255, 255, 255, 255)
        self._size_checkboxes: dict[int, QCheckBox] = {}

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addWidget(self._make_sizes_group())
        layout.addWidget(self._make_background_group())
        layout.addWidget(self._make_template_group())
        layout.addWidget(self._make_preview_group())

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        assert self._ok_btn is not None
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._update_preview()
        self._update_ok_state()

    # ------------------------------------------------------------------
    # UI builders
    # ------------------------------------------------------------------

    def _make_sizes_group(self) -> QGroupBox:
        box = QGroupBox("Rozmiary")
        grid = QGridLayout(box)
        grid.setSpacing(4)
        cols = 5
        for idx, size in enumerate(AVAILABLE_SIZES):
            cb = QCheckBox(f"{size}x{size}")
            cb.setChecked(size in _DEFAULT_SIZES)
            cb.toggled.connect(self._on_options_changed)
            self._size_checkboxes[size] = cb
            grid.addWidget(cb, idx // cols, idx % cols)
        return box

    def _make_background_group(self) -> QGroupBox:
        box = QGroupBox("Tło")
        h = QHBoxLayout(box)

        self._rb_transparent = QRadioButton("Przezroczyste")
        self._rb_transparent.setChecked(True)
        self._rb_transparent.toggled.connect(self._on_options_changed)

        self._rb_color_bg = QRadioButton("Kolor:")
        self._rb_color_bg.toggled.connect(self._on_options_changed)

        self._color_btn = QPushButton()
        self._color_btn.setFixedSize(28, 20)
        self._color_btn.setToolTip("Wybierz kolor tła")
        self._color_btn.clicked.connect(self._pick_color)
        self._refresh_color_button()

        h.addWidget(self._rb_transparent)
        h.addSpacing(12)
        h.addWidget(self._rb_color_bg)
        h.addWidget(self._color_btn)
        h.addStretch()
        return box

    def _make_template_group(self) -> QGroupBox:
        box = QGroupBox("Szablon")
        v = QVBoxLayout(box)

        self._rb_blank = QRadioButton("Pusty (przezroczysty)")
        self._rb_blank.setChecked(True)
        self._rb_blank.toggled.connect(self._on_options_changed)

        self._rb_filled = QRadioButton("Wypełniony kolorem tła")
        self._rb_filled.toggled.connect(self._on_options_changed)

        self._rb_clipboard = QRadioButton("Skopiuj ze schowka")
        self._rb_clipboard.toggled.connect(self._on_clipboard_toggled)

        v.addWidget(self._rb_blank)
        v.addWidget(self._rb_filled)
        v.addWidget(self._rb_clipboard)
        return box

    def _make_preview_group(self) -> QGroupBox:
        box = QGroupBox("Podgląd")
        v = QVBoxLayout(box)

        self._preview_list = QListWidget()
        self._preview_list.setMaximumHeight(110)
        self._preview_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        v.addWidget(self._preview_list)

        self._size_label = QLabel()
        self._size_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        v.addWidget(self._size_label)

        return box

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_options_changed(self) -> None:
        self._update_ok_state()
        self._update_preview()

    def _on_clipboard_toggled(self, checked: bool) -> None:
        if checked and QApplication.clipboard().image().isNull():
            QMessageBox.warning(
                self,
                "Schowek pusty",
                "Schowek nie zawiera obrazu.\nWybrano szablon 'Pusty'.",
            )
            self._rb_blank.setChecked(True)
            return
        self._on_options_changed()

    def _pick_color(self) -> None:
        color = QColorDialog.getColor(
            self._bg_color,
            self,
            "Kolor tła",
            QColorDialog.ColorDialogOption.ShowAlphaChannel,
        )
        if color.isValid():
            self._bg_color = color
            self._rb_color_bg.setChecked(True)
            self._refresh_color_button()
            self._on_options_changed()

    def _refresh_color_button(self) -> None:
        c = self._bg_color
        self._color_btn.setStyleSheet(
            f"background-color: rgba({c.red()},{c.green()},{c.blue()},{c.alpha()});"
            "border: 1px solid #888;"
        )

    def _update_ok_state(self) -> None:
        self._ok_btn.setEnabled(any(cb.isChecked() for cb in self._size_checkboxes.values()))

    def _update_preview(self) -> None:
        self._preview_list.clear()
        sizes = self._selected_sizes()
        description = self._frame_description()
        for s in sizes:
            self._preview_list.addItem(f"{s}x{s}  -  {description}")

        total = self._estimate_total_bytes(sizes)
        size_str = f"{total} B" if total < 1024 else f"{total / 1024:.1f} KB"

        n = len(sizes)
        if n == 0:
            noun = "rozmiarów"
        elif n == 1:
            noun = "rozmiar"
        elif n <= 4:
            noun = "rozmiary"
        else:
            noun = "rozmiarów"
        self._size_label.setText(f"{n} {noun}  ·  ~{size_str}")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _selected_sizes(self) -> list[int]:
        return sorted(s for s, cb in self._size_checkboxes.items() if cb.isChecked())

    def _frame_description(self) -> str:
        if self._rb_filled.isChecked():
            c = self._bg_color
            return f"kolor #{c.red():02x}{c.green():02x}{c.blue():02x}"
        if self._rb_clipboard.isChecked():
            return "ze schowka (przeskalowany)"
        return "przezroczysty"

    def _estimate_total_bytes(self, sizes: list[int]) -> int:
        total = 0
        for s in sizes:
            if self._rb_clipboard.isChecked():
                total += s * s * 2  # rough estimate for photo-like content
            else:
                img = self._build_frame(s)
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                total += len(buf.getvalue())
        return total

    def _build_frame(self, size: int) -> Image.Image:
        """Build a single PIL Image for the given size based on current settings."""
        if self._rb_filled.isChecked():
            c = self._bg_color
            return Image.new("RGBA", (size, size), (c.red(), c.green(), c.blue(), c.alpha()))
        if self._rb_clipboard.isChecked():
            from PySide6.QtCore import QBuffer, QIODeviceBase

            q_img = QApplication.clipboard().image()
            if not q_img.isNull():
                qt_buf = QBuffer()
                qt_buf.open(QIODeviceBase.OpenModeFlag.WriteOnly)
                q_img.save(qt_buf, b"PNG")
                qt_buf.close()
                pil = Image.open(io.BytesIO(bytes(qt_buf.data())))  # type: ignore[call-overload]
                return pil.convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
        return Image.new("RGBA", (size, size), (0, 0, 0, 0))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_frames(self) -> list[tuple[Image.Image, SizeSpec]]:
        """Build all ICO frames from current settings. Call after exec() returns Accepted."""
        return [(self._build_frame(s), SizeSpec(s, s)) for s in self._selected_sizes()]
