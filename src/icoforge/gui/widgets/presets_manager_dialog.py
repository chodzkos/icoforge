"""Dialog for managing user-defined conversion presets."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from icoforge.core.presets import (
    BUILTIN_PRESETS,
    delete_preset,
    export_preset,
    import_preset,
    list_user_presets,
    rename_preset,
)
from icoforge.utils.settings import get_setting, save_setting

_SETTINGS_KEY_DEFAULT_PRESET = "default_preset"
_BUILTIN_FLAG = Qt.ItemDataRole.UserRole  # bool: True = builtin


class PresetsManagerDialog(QDialog):
    """Dialog to rename, delete, set default, and import/export user presets."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Zarządzanie presetami"))
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        layout.addWidget(self._make_list_group())
        layout.addLayout(self._make_action_buttons())

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.accept)
        layout.addWidget(buttons)

        self._refresh_list()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        from icoforge.utils.theme import get_theme_manager
        from icoforge.utils.window_theme import apply_theme_to_dialog

        mgr = get_theme_manager()
        if mgr is not None:
            apply_theme_to_dialog(self, mgr)

    # ------------------------------------------------------------------
    # UI builders
    # ------------------------------------------------------------------

    def _make_list_group(self) -> QGroupBox:
        group = QGroupBox(self.tr("Presety"))
        v = QVBoxLayout(group)

        self._list = QListWidget()
        self._list.setAlternatingRowColors(True)
        self._list.currentRowChanged.connect(self._update_button_states)
        v.addWidget(self._list)

        note = QLabel(
            "<small><i>"
            + self.tr("Wbudowane presety (🔒) nie mogą być edytowane ani usunięte.")
            + "</i></small>"
        )
        note.setWordWrap(True)
        v.addWidget(note)

        return group

    def _make_action_buttons(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)

        self._rename_btn = QPushButton(self.tr("Zmień nazwę"))
        self._rename_btn.clicked.connect(self._on_rename)
        row.addWidget(self._rename_btn)

        self._delete_btn = QPushButton(self.tr("Usuń"))
        self._delete_btn.clicked.connect(self._on_delete)
        row.addWidget(self._delete_btn)

        self._default_btn = QPushButton(self.tr("Ustaw domyślny"))
        self._default_btn.clicked.connect(self._on_set_default)
        row.addWidget(self._default_btn)

        row.addStretch()

        import_btn = QPushButton(self.tr("Importuj…"))
        import_btn.clicked.connect(self._on_import)
        row.addWidget(import_btn)

        self._export_btn = QPushButton(self.tr("Eksportuj…"))
        self._export_btn.clicked.connect(self._on_export)
        row.addWidget(self._export_btn)

        return row

    # ------------------------------------------------------------------
    # List management
    # ------------------------------------------------------------------

    def _refresh_list(self) -> None:
        self._list.clear()
        default = get_setting(_SETTINGS_KEY_DEFAULT_PRESET, "")

        for name in BUILTIN_PRESETS:
            item = QListWidgetItem(f"🔒 {name}")
            item.setData(_BUILTIN_FLAG, True)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            from PySide6.QtGui import QPalette

            item.setForeground(self._list.palette().color(QPalette.ColorRole.PlaceholderText))
            self._list.addItem(item)

        for name in list_user_presets():
            label = name
            if name == default:
                label = f"{name}  ★"
            item = QListWidgetItem(label)
            item.setData(_BUILTIN_FLAG, False)
            item.setData(Qt.ItemDataRole.UserRole + 1, name)  # canonical name without star
            self._list.addItem(item)

        self._update_button_states()

    def _current_user_name(self) -> str | None:
        """Return the canonical name of the currently selected user preset, or None."""
        item = self._list.currentItem()
        if item is None or item.data(_BUILTIN_FLAG):
            return None
        return str(item.data(Qt.ItemDataRole.UserRole + 1))

    def _update_button_states(self) -> None:
        has_user = self._current_user_name() is not None
        self._rename_btn.setEnabled(has_user)
        self._delete_btn.setEnabled(has_user)
        self._default_btn.setEnabled(has_user)
        self._export_btn.setEnabled(has_user)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _themed_msgbox(
        self,
        title: str,
        text: str,
        buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
    ) -> int:
        """Show a QMessageBox with the correct dark/light titlebar."""
        from icoforge.utils.theme import get_theme_manager
        from icoforge.utils.window_theme import apply_theme_to_dialog

        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setStandardButtons(buttons)
        apply_theme_to_dialog(msg, get_theme_manager())
        return int(msg.exec())

    def _on_rename(self) -> None:
        old_name = self._current_user_name()
        if old_name is None:
            return
        from icoforge.utils.theme import get_theme_manager
        from icoforge.utils.window_theme import apply_theme_to_dialog

        input_dlg = QInputDialog(self)
        input_dlg.setWindowTitle(self.tr("Zmień nazwę"))
        input_dlg.setLabelText(self.tr("Nowa nazwa:"))
        input_dlg.setTextValue(old_name)
        apply_theme_to_dialog(input_dlg, get_theme_manager())
        if input_dlg.exec() != QInputDialog.DialogCode.Accepted:
            return
        new_name = input_dlg.textValue().strip()
        if not new_name or new_name == old_name:
            return
        if new_name in BUILTIN_PRESETS:
            self._themed_msgbox(
                self.tr("Nazwa zarezerwowana"),
                self.tr('Nazwa "%1" jest zarezerwowana dla wbudowanego presetu.').replace(
                    "%1", new_name
                ),
            )
            return
        if new_name in list_user_presets():
            reply = self._themed_msgbox(
                self.tr("Nadpisać?"),
                self.tr('Preset "%1" już istnieje. Nadpisać?').replace("%1", new_name),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        try:
            rename_preset(old_name, new_name)
        except (FileNotFoundError, OSError) as exc:
            self._themed_msgbox(self.tr("Błąd"), str(exc))
            return
        if get_setting(_SETTINGS_KEY_DEFAULT_PRESET, "") == old_name:
            save_setting(_SETTINGS_KEY_DEFAULT_PRESET, new_name)
        self._refresh_list()

    def _on_delete(self) -> None:
        name = self._current_user_name()
        if name is None:
            return
        reply = self._themed_msgbox(
            self.tr("Usuń preset"),
            self.tr('Usunąć preset "%1"?').replace("%1", name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        delete_preset(name)
        if get_setting(_SETTINGS_KEY_DEFAULT_PRESET, "") == name:
            save_setting(_SETTINGS_KEY_DEFAULT_PRESET, "")
        self._refresh_list()

    def _on_set_default(self) -> None:
        name = self._current_user_name()
        if name is None:
            return
        current_default = get_setting(_SETTINGS_KEY_DEFAULT_PRESET, "")
        if current_default == name:
            # Toggle off
            save_setting(_SETTINGS_KEY_DEFAULT_PRESET, "")
        else:
            save_setting(_SETTINGS_KEY_DEFAULT_PRESET, name)
        self._refresh_list()

    def _on_import(self) -> None:
        from chodzkos_gui_kit.qt.dialogs import open_file

        path = open_file(
            self,
            self.tr("Importuj preset"),
            "",
            self.tr("Preset IcoForge (*.json)") + ";;" + self.tr("Wszystkie pliki (*)"),
        )
        if not path:
            return
        try:
            name = import_preset(Path(path))
        except (ValueError, OSError) as exc:
            QMessageBox.critical(
                self,
                self.tr("Błąd importu"),
                self.tr("Nie można zaimportować pliku:\n%1").replace("%1", str(exc)),
            )
            return
        self._refresh_list()
        # Select the newly imported preset
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole + 1) == name:
                self._list.setCurrentRow(i)
                break

    def _on_export(self) -> None:
        name = self._current_user_name()
        if name is None:
            return
        from chodzkos_gui_kit.qt.dialogs import save_file

        path = save_file(
            self,
            self.tr("Eksportuj preset"),
            "",
            self.tr("Preset IcoForge (*.json)") + ";;" + self.tr("Wszystkie pliki (*)"),
            initial_name=f"{name}.json",
        )
        if not path:
            return
        try:
            export_preset(name, Path(path))
        except (FileNotFoundError, OSError) as exc:
            QMessageBox.critical(
                self,
                self.tr("Błąd eksportu"),
                self.tr("Nie można wyeksportować presetu:\n%1").replace("%1", str(exc)),
            )
