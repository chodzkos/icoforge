"""Test complete editor workflow from main window."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from icoforge.core.converter import convert
from icoforge.core.models import IcoConfig, SizeSpec
from icoforge.gui.main_window import MainWindow


@pytest.fixture
def test_ico(tmp_path: Path) -> Path:
    """Create a test ICO file."""
    src = tmp_path / "source.png"
    ico_path = tmp_path / "editor_test.ico"

    img = Image.new("RGBA", (256, 256))
    pixels = img.load()
    for y in range(256):
        for x in range(256):
            pixels[x, y] = (x, y, (x + y) // 2, 255)
    img.save(src)

    config = IcoConfig(sizes=(SizeSpec(16, 16), SizeSpec(32, 32), SizeSpec(48, 48)))
    convert(src, ico_path, config)
    return ico_path


def test_full_editor_workflow(qtbot, test_ico: Path) -> None:
    """Test complete workflow: open main window → open editor."""
    # Create and show main window
    main = MainWindow()
    qtbot.addWidget(main)
    main.show()

    # Initially no editor window
    assert main._editor_window is None

    # Simulate opening editor via menu (calling handler directly)
    # In real app, this would be triggered by File → Edit &ICO menu
    from icoforge.gui.editor.editor_window import EditorWindow

    main._editor_window = EditorWindow(test_ico)
    main._editor_window.show()

    # Verify editor window is created and visible
    assert main._editor_window is not None
    assert main._editor_window.isVisible()
    assert main._editor_window.windowTitle().startswith("Editor")

    # Verify frames are loaded
    assert len(main._editor_window._frames) == 3

    # Verify canvas is functional
    assert main._editor_window._canvas is not None
    assert main._editor_window._canvas._current_image is not None

    # Verify toolbar exists
    assert main._editor_window._size_spinbox is not None


def test_editor_tool_integration_from_main(qtbot, test_ico: Path) -> None:
    """Test drawing tools are available in editor opened from main window."""
    from icoforge.gui.editor.editor_window import EditorWindow

    main = MainWindow()
    qtbot.addWidget(main)

    # Open editor from main window
    main._editor_window = EditorWindow(test_ico)

    # Verify tools can be selected
    main._editor_window._on_tool_pencil()
    assert main._editor_window._canvas._current_tool is not None

    # Verify drawing works
    image_before = main._editor_window._canvas._current_image.copy()
    pixel_before = image_before.getpixel((5, 5))

    tool = main._editor_window._tools["pencil"]
    tool.set_color((255, 0, 0, 255))
    tool.on_press(5, 5)

    image_after = main._editor_window._canvas._current_image
    pixel_after = image_after.getpixel((5, 5))

    # Verify pixel changed
    assert pixel_after == (255, 0, 0, 255)
    assert pixel_before != pixel_after
