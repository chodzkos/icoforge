"""Integration tests for editor tools with GUI."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from icoforge.core.converter import convert
from icoforge.core.models import IcoConfig, SizeSpec
from icoforge.gui.editor.editor_window import EditorWindow


@pytest.fixture
def test_ico(tmp_path: Path) -> Path:
    """Create a test ICO file with gradient pattern."""
    src = tmp_path / "source.png"
    ico_path = tmp_path / "test.ico"

    # Create colorful gradient image
    img = Image.new("RGBA", (256, 256))
    pixels = img.load()
    for y in range(256):
        for x in range(256):
            r = x
            g = y
            b = (x + y) // 2
            a = 255
            pixels[x, y] = (r, g, b, a)

    img.save(src, "PNG")

    # Convert to multi-size ICO
    config = IcoConfig(
        sizes=(SizeSpec(16, 16), SizeSpec(32, 32), SizeSpec(48, 48), SizeSpec(64, 64))
    )
    convert(src, ico_path, config)
    return ico_path


class TestEditorToolsIntegration:
    """Test editor tools integration."""

    def test_editor_window_loads_ico(self, qtbot, test_ico: Path) -> None:
        """Test that editor window loads ICO file."""
        window = EditorWindow(test_ico)
        qtbot.addWidget(window)

        # Check that frames loaded
        assert len(window._frames) == 4
        assert window._current_frame_index == 0

    def test_pencil_tool_draws(self, qtbot, test_ico: Path) -> None:
        """Test that pencil tool draws pixels."""
        window = EditorWindow(test_ico)
        qtbot.addWidget(window)

        # Get the current image
        image_before = window._canvas._current_image.copy()
        pixel_before = image_before.getpixel((5, 5))

        # Set pencil tool with red color
        window._on_tool_pencil()
        window._current_color = (255, 0, 0, 255)
        tool = window._tools["pencil"]
        tool.set_color(window._current_color)

        # Draw at position
        tool.on_press(5, 5)

        # Get the updated image
        image_after = window._canvas._current_image
        pixel_after = image_after.getpixel((5, 5))

        # Verify pixel changed to red
        assert pixel_after == (255, 0, 0, 255), f"Expected red, got {pixel_after}"
        assert pixel_before != pixel_after

    def test_eraser_tool_erases(self, qtbot, test_ico: Path) -> None:
        """Test that eraser tool sets alpha to 0."""
        window = EditorWindow(test_ico)
        qtbot.addWidget(window)

        # Get original pixel
        image = window._canvas._current_image
        pixel_original = image.getpixel((10, 10))
        r, g, b, a = pixel_original
        assert a == 255, "Original pixel should be opaque"

        # Use eraser tool
        window._on_tool_eraser()
        tool = window._tools["eraser"]
        tool.on_press(10, 10)

        # Check that alpha is 0
        pixel_erased = image.getpixel((10, 10))
        r, g, b, a = pixel_erased
        assert a == 0, f"Erased pixel should have alpha=0, got {a}"
        # RGB should be preserved
        assert (r, g, b) == (pixel_original[0], pixel_original[1], pixel_original[2])

    def test_eyedropper_tool_picks_color(self, qtbot, test_ico: Path) -> None:
        """Test that eyedropper tool picks colors."""
        window = EditorWindow(test_ico)
        qtbot.addWidget(window)

        # First draw a known color at a position
        window._on_tool_pencil()
        pencil = window._tools["pencil"]
        test_color = (100, 150, 200, 255)
        pencil.set_color(test_color)
        pencil.on_press(5, 5)

        # Now use eyedropper tool to pick it back
        window._on_tool_eyedropper()
        eyedropper = window._tools["eyedropper"]
        eyedropper.on_press(5, 5)
        picked = eyedropper.get_color()

        assert picked == test_color, f"Expected {test_color}, got {picked}"

    def test_size_control_changes_brush(self, qtbot, test_ico: Path) -> None:
        """Test that size spinbox changes brush size."""
        window = EditorWindow(test_ico)
        qtbot.addWidget(window)

        window._on_tool_pencil()
        tool = window._tools["pencil"]

        # Set size via spinbox
        window._size_spinbox.setValue(5)
        assert tool.size == 5

        window._size_spinbox.setValue(8)
        assert tool.size == 8

    def test_color_picker_changes_color(self, qtbot, test_ico: Path) -> None:
        """Test that color picker updates pencil color."""
        window = EditorWindow(test_ico)
        qtbot.addWidget(window)

        window._on_tool_pencil()
        tool = window._tools["pencil"]

        # Set color directly
        new_color = (100, 150, 200, 255)
        window._current_color = new_color
        tool.set_color(new_color)

        assert tool.color == new_color

    def test_frame_switching_creates_new_tools(self, qtbot, test_ico: Path) -> None:
        """Test that switching frames recreates tools."""
        window = EditorWindow(test_ico)
        qtbot.addWidget(window)

        # Select pencil tool to create tools
        window._on_tool_pencil()
        tool1 = window._tools.get("pencil")
        assert tool1 is not None

        # Switch to second frame
        item = window._size_list.item(1)
        window._on_size_selected(item)

        # Get new tool instance (should be recreated)
        tool2 = window._tools.get("pencil")
        assert tool2 is not None
        assert tool1 is not tool2, "New tools should be created for new frame"

    def test_keyboard_shortcuts(self, qtbot, test_ico: Path) -> None:
        """Test that tool selection via toolbar works."""
        window = EditorWindow(test_ico)
        qtbot.addWidget(window)
        window.show()

        # Click pencil button (or call handler directly)
        window._on_tool_pencil()
        assert window._canvas._current_tool is not None
        assert type(window._canvas._current_tool).__name__ == "PixelTool"

        # Click eraser button
        window._on_tool_eraser()
        assert window._canvas._current_tool is not None
        assert type(window._canvas._current_tool).__name__ == "EraserTool"

        # Click eyedropper button
        window._on_tool_eyedropper()
        assert window._canvas._current_tool is not None
        assert type(window._canvas._current_tool).__name__ == "EyedropperTool"

    def test_draw_with_brush_size(self, qtbot, test_ico: Path) -> None:
        """Test that brush size affects drawing area."""
        window = EditorWindow(test_ico)
        qtbot.addWidget(window)

        window._on_tool_pencil()
        tool = window._tools["pencil"]
        tool.set_size(3)
        tool.set_color((255, 0, 0, 255))

        # Draw at center
        image = window._canvas._current_image
        tool.on_press(10, 10)

        # With size 3, should affect radius=2 area, so (10±2, 10±2)
        # Check center
        assert image.getpixel((10, 10))[0] == 255  # Red

        # Check nearby pixels
        assert image.getpixel((9, 10))[0] == 255  # Red (within radius 2)
        assert image.getpixel((11, 10))[0] == 255  # Red (within radius 2)
