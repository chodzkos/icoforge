"""Tests for zoom controls and auto-zoom behaviour."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from icoforge.core.converter import convert
from icoforge.core.models import IcoConfig, SizeSpec
from icoforge.gui.editor.canvas import ZOOM_LEVELS, EditorCanvas
from icoforge.gui.editor.editor_window import EditorWindow


@pytest.fixture
def full_ico(tmp_path: Path) -> Path:
    """ICO with 16, 32, 48, 64, 128 and 256 sizes."""
    src = tmp_path / "src.png"
    ico = tmp_path / "full.ico"
    Image.new("RGBA", (256, 256), (100, 150, 200, 255)).save(src)
    config = IcoConfig(
        sizes=(
            SizeSpec(16, 16),
            SizeSpec(32, 32),
            SizeSpec(48, 48),
            SizeSpec(64, 64),
            SizeSpec(128, 128),
            SizeSpec(256, 256),
        )
    )
    convert(src, ico, config)
    return ico


# ---------------------------------------------------------------------------
# Canvas unit tests
# ---------------------------------------------------------------------------


class TestZoomAPI:
    def test_zoom_in_steps_through_presets(self, qtbot) -> None:
        canvas = EditorCanvas()
        qtbot.addWidget(canvas)
        img = Image.new("RGBA", (32, 32), (0, 0, 0, 255))
        canvas.load_image(img)

        canvas._apply_zoom(1.0)
        canvas.zoom_in()
        assert canvas._zoom_level == pytest.approx(2.0, rel=0.05)

        canvas.zoom_in()
        assert canvas._zoom_level == pytest.approx(4.0, rel=0.05)

    def test_zoom_out_steps_through_presets(self, qtbot) -> None:
        canvas = EditorCanvas()
        qtbot.addWidget(canvas)
        img = Image.new("RGBA", (32, 32), (0, 0, 0, 255))
        canvas.load_image(img)

        canvas._apply_zoom(8.0)
        canvas.zoom_out()
        assert canvas._zoom_level == pytest.approx(4.0, rel=0.05)

    def test_zoom_1to1(self, qtbot) -> None:
        canvas = EditorCanvas()
        qtbot.addWidget(canvas)
        img = Image.new("RGBA", (32, 32), (0, 0, 0, 255))
        canvas.load_image(img)
        canvas._apply_zoom(16.0)
        canvas.zoom_1to1()
        assert canvas._zoom_level == pytest.approx(1.0, rel=0.05)

    def test_fit_to_window_zoom_is_positive(self, qtbot) -> None:
        canvas = EditorCanvas()
        qtbot.addWidget(canvas)
        canvas.resize(400, 400)
        img = Image.new("RGBA", (256, 256), (0, 0, 0, 255))
        canvas.load_image(img)
        canvas.fit_to_window()
        assert canvas._zoom_level > 0

    def test_zoom_levels_list_is_sorted(self) -> None:
        assert sorted(ZOOM_LEVELS) == ZOOM_LEVELS
        assert ZOOM_LEVELS[0] == 1.0
        assert ZOOM_LEVELS[-1] == 64.0

    def test_zoom_clamped_at_max(self, qtbot) -> None:
        canvas = EditorCanvas()
        qtbot.addWidget(canvas)
        img = Image.new("RGBA", (16, 16), (0, 0, 0, 255))
        canvas.load_image(img)
        canvas._apply_zoom(9999.0)
        assert canvas._zoom_level == canvas.MAX_ZOOM

    def test_zoom_clamped_at_min(self, qtbot) -> None:
        canvas = EditorCanvas()
        qtbot.addWidget(canvas)
        img = Image.new("RGBA", (16, 16), (0, 0, 0, 255))
        canvas.load_image(img)
        canvas._apply_zoom(0.001)
        assert canvas._zoom_level == canvas.MIN_ZOOM


# ---------------------------------------------------------------------------
# Auto-zoom: 256x256 must fit in window
# ---------------------------------------------------------------------------


class TestAutoZoom:
    def _switch_to_size(self, window: EditorWindow, w: int, h: int) -> bool:
        """Select a frame matching the given size; return True if found."""
        for row in range(window._size_list.count()):
            item = window._size_list.item(row)
            idx = item.data(0x0100)  # Qt.ItemDataRole.UserRole
            if idx is not None and 0 <= idx < len(window._frames):
                _, spec = window._frames[idx]
                if spec.width == w and spec.height == h:
                    window._size_list.setCurrentRow(row)
                    window._on_size_selected(item)
                    return True
        return False

    def test_256x256_auto_zoom_fits_in_window(self, qtbot, full_ico: Path) -> None:
        """After switching to 256x256, zoom must be <= fit-to-window zoom."""
        window = EditorWindow(full_ico)
        qtbot.addWidget(window)
        window.resize(800, 600)

        found = self._switch_to_size(window, 256, 256)
        assert found, "256x256 frame not found"

        fit_zoom = window._canvas.get_fit_zoom()
        actual_zoom = window._canvas._zoom_level
        assert actual_zoom <= fit_zoom * 1.05, (
            f"256x256 zoom {actual_zoom:.2f} exceeds fit zoom {fit_zoom:.2f}"
        )

    def test_128x128_auto_zoom_fits_in_window(self, qtbot, full_ico: Path) -> None:
        window = EditorWindow(full_ico)
        qtbot.addWidget(window)
        window.resize(800, 600)

        found = self._switch_to_size(window, 128, 128)
        assert found, "128x128 frame not found"

        fit_zoom = window._canvas.get_fit_zoom()
        actual_zoom = window._canvas._zoom_level
        assert actual_zoom <= fit_zoom * 1.05, (
            f"128x128 zoom {actual_zoom:.2f} exceeds fit zoom {fit_zoom:.2f}"
        )

    def test_16x16_auto_zoom_is_at_least_8x(self, qtbot, full_ico: Path) -> None:
        window = EditorWindow(full_ico)
        qtbot.addWidget(window)
        window.resize(800, 600)

        found = self._switch_to_size(window, 16, 16)
        assert found, "16x16 frame not found"

        assert window._canvas._zoom_level >= 8.0

    def test_32x32_auto_zoom_is_at_least_8x(self, qtbot, full_ico: Path) -> None:
        window = EditorWindow(full_ico)
        qtbot.addWidget(window)
        window.resize(800, 600)

        found = self._switch_to_size(window, 32, 32)
        assert found, "32x32 frame not found"

        assert window._canvas._zoom_level >= 8.0


# ---------------------------------------------------------------------------
# Zoom override (user zoom is remembered)
# ---------------------------------------------------------------------------


class TestZoomOverride:
    def test_user_zoom_remembered_per_size(self, qtbot, full_ico: Path) -> None:
        """After user manually sets zoom, switching away and back preserves it."""
        window = EditorWindow(full_ico)
        qtbot.addWidget(window)
        window.resize(800, 600)

        # Switch to 32x32, manually set 32x zoom
        for row in range(window._size_list.count()):
            item = window._size_list.item(row)
            idx = item.data(0x0100)
            if idx is not None and 0 <= idx < len(window._frames):
                _, spec = window._frames[idx]
                if spec.width == 32 and spec.height == 32:
                    window._size_list.setCurrentRow(row)
                    window._on_size_selected(item)
                    break

        window._user_set_zoom = True
        window._canvas._apply_zoom(32.0)
        # Emit the signal manually so _on_zoom_changed records it
        window._canvas.zoom_changed.emit(32.0)

        # Switch to 16x16
        for row in range(window._size_list.count()):
            item = window._size_list.item(row)
            idx = item.data(0x0100)
            if idx is not None and 0 <= idx < len(window._frames):
                _, spec = window._frames[idx]
                if spec.width == 16 and spec.height == 16:
                    window._size_list.setCurrentRow(row)
                    window._on_size_selected(item)
                    break

        # Switch back to 32x32 — should restore user zoom
        for row in range(window._size_list.count()):
            item = window._size_list.item(row)
            idx = item.data(0x0100)
            if idx is not None and 0 <= idx < len(window._frames):
                _, spec = window._frames[idx]
                if spec.width == 32 and spec.height == 32:
                    window._size_list.setCurrentRow(row)
                    window._on_size_selected(item)
                    break

        assert window._canvas._zoom_level == pytest.approx(32.0, rel=0.05)
