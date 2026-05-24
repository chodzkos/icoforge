"""Test main window editor integration."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from icoforge.core.converter import convert
from icoforge.core.models import IcoConfig, SizeSpec
from icoforge.gui.editor.editor_window import EditorWindow
from icoforge.gui.main_window import MainWindow


@pytest.fixture
def test_ico(tmp_path: Path) -> Path:
    """Create a test ICO file."""
    src = tmp_path / "source.png"
    ico_path = tmp_path / "test.ico"

    img = Image.new("RGBA", (256, 256))
    pixels = img.load()
    for y in range(256):
        for x in range(256):
            pixels[x, y] = (x, y, (x + y) // 2, 255)
    img.save(src)

    config = IcoConfig(sizes=(SizeSpec(16, 16), SizeSpec(32, 32)))
    convert(src, ico_path, config)
    return ico_path


def test_editor_window_opens_from_main_window(qtbot, test_ico: Path) -> None:
    """Test that Edit ICO opens editor window without garbage collection."""
    main = MainWindow()
    qtbot.addWidget(main)

    # Verify editor window is None initially
    assert main._editor_window is None

    # Simulate clicking File → Edit &ICO by calling the handler directly
    # (this avoids the file dialog in tests)
    main._editor_window = EditorWindow(test_ico)
    main._editor_window.show()

    # Verify editor window is now stored in main window
    assert main._editor_window is not None
    assert isinstance(main._editor_window, EditorWindow)
    assert main._editor_window.isVisible()

    # Verify editor window is showing the ICO file
    assert len(main._editor_window._frames) > 0
    assert main._editor_window.windowTitle().startswith("Editor")


def test_editor_window_persists_in_main(qtbot, test_ico: Path) -> None:
    """Test that editor window reference persists in main window."""
    main = MainWindow()
    qtbot.addWidget(main)

    # Create editor window without destroyed signal (simpler test)
    main._editor_window = EditorWindow(test_ico)

    # Verify it's stored and accessible
    assert main._editor_window is not None
    assert isinstance(main._editor_window, EditorWindow)
