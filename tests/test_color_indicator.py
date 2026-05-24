"""Tests for ColorIndicator widget and its integration with the editor."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image
from PySide6.QtGui import QColor

from icoforge.core.converter import convert
from icoforge.core.models import IcoConfig, SizeSpec
from icoforge.gui.editor.color_indicator import ColorIndicator
from icoforge.gui.editor.editor_window import EditorWindow


@pytest.fixture
def small_ico(tmp_path: Path) -> Path:
    src = tmp_path / "src.png"
    ico = tmp_path / "small.ico"
    Image.new("RGBA", (32, 32), (0, 128, 255, 255)).save(src)
    convert(src, ico, IcoConfig(sizes=(SizeSpec(16, 16), SizeSpec(32, 32))))
    return ico


# ---------------------------------------------------------------------------
# ColorIndicator unit tests
# ---------------------------------------------------------------------------


class TestColorIndicator:
    def test_default_colors(self, qtbot) -> None:
        w = ColorIndicator()
        qtbot.addWidget(w)
        assert w.foreground_color == QColor(0, 0, 0, 255)
        assert w.background_color == QColor(255, 255, 255, 255)

    def test_set_foreground_emits_signal(self, qtbot) -> None:
        w = ColorIndicator()
        qtbot.addWidget(w)
        received: list[tuple] = []
        w.color_changed.connect(lambda c, fg: received.append((c, fg)))

        w.set_foreground_color(QColor(255, 0, 0, 255))
        assert len(received) == 1
        color, is_fg = received[0]
        assert is_fg is True
        assert color == QColor(255, 0, 0, 255)

    def test_set_background_emits_signal(self, qtbot) -> None:
        w = ColorIndicator()
        qtbot.addWidget(w)
        received: list[tuple] = []
        w.color_changed.connect(lambda c, fg: received.append((c, fg)))

        w.set_background_color(QColor(0, 0, 255, 255))
        assert len(received) == 1
        _, is_fg = received[0]
        assert is_fg is False

    def test_same_color_does_not_emit(self, qtbot) -> None:
        w = ColorIndicator()
        qtbot.addWidget(w)
        received: list = []
        w.color_changed.connect(lambda c, fg: received.append(c))

        w.set_foreground_color(QColor(0, 0, 0, 255))  # same as default black
        assert len(received) == 0

    def test_swap_colors(self, qtbot) -> None:
        w = ColorIndicator()
        qtbot.addWidget(w)
        w.set_foreground_color(QColor(255, 0, 0, 255))
        w.set_background_color(QColor(0, 0, 255, 255))

        w.swap_colors()

        assert w.foreground_color == QColor(0, 0, 255, 255)
        assert w.background_color == QColor(255, 0, 0, 255)

    def test_swap_emits_foreground_signal(self, qtbot) -> None:
        w = ColorIndicator()
        qtbot.addWidget(w)
        w.set_background_color(QColor(100, 200, 50, 255))
        received: list[tuple] = []
        w.color_changed.connect(lambda c, fg: received.append((c, fg)))

        w.swap_colors()

        assert any(is_fg for _, is_fg in received)
        fg_events = [(c, fg) for c, fg in received if fg]
        assert fg_events[0][0] == QColor(100, 200, 50, 255)

    def test_reset_to_default(self, qtbot) -> None:
        w = ColorIndicator()
        qtbot.addWidget(w)
        w.set_foreground_color(QColor(200, 100, 50, 128))
        w.set_background_color(QColor(50, 50, 50, 255))

        w.reset_to_default()

        assert w.foreground_color == QColor(0, 0, 0, 255)
        assert w.background_color == QColor(255, 255, 255, 255)

    def test_hex_with_full_alpha(self, qtbot) -> None:
        w = ColorIndicator()
        qtbot.addWidget(w)
        w.set_foreground_color(QColor(255, 85, 0, 255))
        assert w._hex() == "#FF5500"

    def test_hex_with_partial_alpha(self, qtbot) -> None:
        w = ColorIndicator()
        qtbot.addWidget(w)
        w.set_foreground_color(QColor(255, 85, 0, 128))
        assert w._hex() == "#FF550080"

    def test_widget_has_fixed_size(self, qtbot) -> None:
        w = ColorIndicator()
        qtbot.addWidget(w)
        assert w.width() > 0
        assert w.height() > 0


# ---------------------------------------------------------------------------
# Integration with EditorWindow
# ---------------------------------------------------------------------------


class TestColorIndicatorIntegration:
    def test_editor_has_color_indicator(self, qtbot, small_ico: Path) -> None:
        window = EditorWindow(small_ico)
        qtbot.addWidget(window)
        assert hasattr(window, "_color_indicator")
        assert isinstance(window._color_indicator, ColorIndicator)

    def test_color_change_updates_pencil_tool(self, qtbot, small_ico: Path) -> None:
        window = EditorWindow(small_ico)
        qtbot.addWidget(window)
        window._on_tool_pencil()

        window._color_indicator.set_foreground_color(QColor(200, 100, 50, 255))

        from icoforge.gui.editor.tools import PixelTool

        tool = window._tools.get("pencil")
        assert isinstance(tool, PixelTool)
        assert tool.color == (200, 100, 50, 255)

    def test_eyedropper_updates_color_indicator(self, qtbot, small_ico: Path) -> None:
        """Color sampled by eyedropper must appear in the ColorIndicator."""
        window = EditorWindow(small_ico)
        qtbot.addWidget(window)

        # Draw a known-color pixel then pick it with eyedropper
        window._on_tool_pencil()
        pencil = window._tools["pencil"]
        from icoforge.gui.editor.tools import PixelTool

        assert isinstance(pencil, PixelTool)
        pencil.set_color((12, 34, 56, 255))
        pencil.on_press(2, 2)

        # Switch to eyedropper and sample
        window._on_tool_eyedropper()
        eyedropper = window._tools["eyedropper"]
        eyedropper.on_press(2, 2)
        # Simulate the canvas emitting color_sampled
        window._canvas.color_sampled.emit(12, 34, 56, 255)

        assert window._color_indicator.foreground_color == QColor(12, 34, 56, 255)

    def test_swap_shortcut_swaps_colors(self, qtbot, small_ico: Path) -> None:
        window = EditorWindow(small_ico)
        qtbot.addWidget(window)
        window.show()

        window._color_indicator.set_foreground_color(QColor(10, 20, 30, 255))
        window._color_indicator.set_background_color(QColor(40, 50, 60, 255))

        window._on_swap_colors()

        assert window._color_indicator.foreground_color == QColor(40, 50, 60, 255)
        assert window._color_indicator.background_color == QColor(10, 20, 30, 255)

    def test_pencil_uses_indicator_color_on_draw(self, qtbot, small_ico: Path) -> None:
        """Actual pixel drawn should match the color in ColorIndicator."""
        window = EditorWindow(small_ico)
        qtbot.addWidget(window)

        window._color_indicator.set_foreground_color(QColor(0, 200, 100, 255))
        window._on_tool_pencil()

        tool = window._tools["pencil"]
        from icoforge.gui.editor.tools import PixelTool

        assert isinstance(tool, PixelTool)
        tool.on_press(1, 1)

        pixel = window._canvas._current_image.getpixel((1, 1))
        assert pixel == (0, 200, 100, 255)
