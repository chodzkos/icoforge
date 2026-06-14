"""Tests for the editor's recolourable icon toolbars."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QAbstractButton, QToolBar, QToolButton

from icoforge.core.converter import convert
from icoforge.core.models import IcoConfig, SizeSpec
from icoforge.gui import icons
from icoforge.gui.editor.editor_window import EditorWindow


@pytest.fixture
def small_ico(tmp_path: Path) -> Path:
    src = tmp_path / "src.png"
    ico = tmp_path / "small.ico"
    Image.new("RGBA", (32, 32), (0, 128, 255, 255)).save(src)
    convert(src, ico, IcoConfig(sizes=(SizeSpec(16, 16), SizeSpec(32, 32))))
    return ico


def _toolbar(window: EditorWindow, object_name: str) -> QToolBar:
    toolbar = window.findChild(QToolBar, object_name)
    assert toolbar is not None
    return toolbar


def _toolbar_actions(toolbar: QToolBar) -> list[QAction]:
    actions: list[QAction] = []
    for action in toolbar.actions():
        if action.isSeparator():
            continue
        widget = toolbar.widgetForAction(action)
        if widget is not None and not isinstance(widget, QToolButton):
            continue
        actions.append(action)
    return actions


def test_editor_toolbars_are_icon_only(qtbot, small_ico: Path) -> None:
    window = EditorWindow(small_ico)
    qtbot.addWidget(window)

    for toolbar in (
        _toolbar(window, "editor_tools_toolbar"),
        _toolbar(window, "editor_zoom_toolbar"),
    ):
        assert toolbar.toolButtonStyle() == Qt.ToolButtonStyle.ToolButtonIconOnly
        assert toolbar.iconSize() == QSize(20, 20)


def test_editor_tool_actions_are_iconified_checkable_and_exclusive(qtbot, small_ico: Path) -> None:
    window = EditorWindow(small_ico)
    qtbot.addWidget(window)

    assert window._tool_action_group.isExclusive()
    assert set(window._tool_actions) == {
        "pencil",
        "eraser",
        "eyedropper",
        "fill",
        "line",
        "rect",
        "select",
    }

    expected_tooltips = {
        "pencil": "Ołówek (B)",
        "eraser": "Gumka (E)",
        "eyedropper": "Kroplomierz (I)",
        "fill": "Wypełnienie (G)",
        "line": "Linia (L)",
        "rect": "Prostokąt (R)",
        "select": "Zaznaczenie (S)",
    }
    for name, action in window._tool_actions.items():
        assert action.isCheckable()
        assert not action.icon().isNull()
        assert action.toolTip() == expected_tooltips[name]

    assert window._tool_actions["pencil"].isChecked()
    window._on_tool_eraser()
    assert window._tool_actions["eraser"].isChecked()
    assert not window._tool_actions["pencil"].isChecked()


def test_editor_tool_shortcuts_are_preserved(qtbot, small_ico: Path) -> None:
    window = EditorWindow(small_ico)
    qtbot.addWidget(window)

    expected = {
        "pencil": "B",
        "eraser": "E",
        "eyedropper": "I",
        "fill": "G",
        "line": "L",
        "rect": "R",
        "select": "S",
    }
    for name, shortcut in expected.items():
        assert window._tool_actions[name].shortcut() == QKeySequence(shortcut)


def test_editor_edit_color_and_zoom_actions_have_icons(qtbot, small_ico: Path) -> None:
    window = EditorWindow(small_ico)
    qtbot.addWidget(window)

    for action in (
        list(window._edit_actions.values())
        + list(window._color_actions.values())
        + list(window._zoom_actions.values())
    ):
        assert not action.isCheckable()
        assert not action.icon().isNull()
        assert action.toolTip()

    assert window._edit_actions["undo"].toolTip() == "Cofnij (Ctrl+Z)"
    assert window._edit_actions["redo"].toolTip() == "Ponów (Ctrl+Shift+Z)"
    assert window._color_actions["swap_colors"].toolTip() == "Zamień kolory (X)"
    assert window._color_actions["reset_colors"].toolTip() == "Domyślne kolory (D)"
    assert window._zoom_actions["zoom_in"].toolTip() == "Powiększ (+)"
    assert window._zoom_actions["zoom_out"].toolTip() == "Pomniejsz (-)"
    assert window._zoom_actions["zoom_fit"].toolTip() == "Dopasuj do okna (Ctrl+0)"
    assert window._zoom_actions["zoom_1to1"].toolTip() == "Rozmiar 1:1 (Ctrl+1)"


def test_all_editor_toolbar_actions_and_buttons_have_tooltips(qtbot, small_ico: Path) -> None:
    window = EditorWindow(small_ico)
    qtbot.addWidget(window)
    window.show()

    for toolbar in window.findChildren(QToolBar):
        for action in _toolbar_actions(toolbar):
            assert action.toolTip(), f"Brak tooltipa: {action.text()}"

        for button in toolbar.findChildren(QAbstractButton):
            if not isinstance(button, QToolButton):
                continue
            action = button.defaultAction()
            if action is None or action.isSeparator():
                continue
            assert button.toolTip() or action.toolTip(), f"Brak tooltipa: {action.text()}"


def test_editor_icons_refresh_after_theme_icon_cache_clear(qtbot, small_ico: Path) -> None:
    window = EditorWindow(small_ico)
    qtbot.addWidget(window)

    try:
        icons.set_color_resolver(lambda _token: "#111111")
        icons.clear_cache()
        window._refresh_icons()
        dark_key = window._tool_actions["pencil"].icon().cacheKey()

        icons.set_color_resolver(lambda _token: "#eeeeee")
        icons.clear_cache()
        window._refresh_icons()
        light_key = window._tool_actions["pencil"].icon().cacheKey()
    finally:
        icons.clear_cache()
        icons.set_color_resolver(None)

    assert dark_key != light_key
