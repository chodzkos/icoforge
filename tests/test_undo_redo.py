"""Tests for undo/redo history via QUndoStack."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image
from PySide6.QtGui import QColor, QUndoStack

from icoforge.core.converter import convert
from icoforge.core.models import IcoConfig, SizeSpec
from icoforge.gui.editor.canvas import EditorCanvas
from icoforge.gui.editor.commands import DrawCommand, FillCommand, compute_pixel_diff
from icoforge.gui.editor.editor_window import EditorWindow


@pytest.fixture
def small_ico(tmp_path: Path) -> Path:
    src = tmp_path / "src.png"
    ico = tmp_path / "small.ico"
    Image.new("RGBA", (32, 32), (0, 128, 255, 255)).save(src)
    convert(src, ico, IcoConfig(sizes=(SizeSpec(16, 16), SizeSpec(32, 32))))
    return ico


# ---------------------------------------------------------------------------
# compute_pixel_diff unit tests
# ---------------------------------------------------------------------------


class TestComputePixelDiff:
    def test_no_change_returns_empty(self) -> None:
        img = Image.new("RGBA", (4, 4), (10, 20, 30, 255))
        assert compute_pixel_diff(img, img.copy()) == []

    def test_single_pixel_changed(self) -> None:
        old = Image.new("RGBA", (4, 4), (0, 0, 0, 255))
        new = old.copy()
        new.load()[2, 3] = (100, 200, 50, 128)
        diff = compute_pixel_diff(old, new)
        assert len(diff) == 1
        x, y, old_c, new_c = diff[0]
        assert (x, y) == (2, 3)
        assert old_c == (0, 0, 0, 255)
        assert new_c == (100, 200, 50, 128)

    def test_multiple_pixels_changed(self) -> None:
        old = Image.new("RGBA", (8, 8), (0, 0, 0, 255))
        new = old.copy()
        px = new.load()
        px[0, 0] = (1, 1, 1, 255)
        px[7, 7] = (2, 2, 2, 255)
        diff = compute_pixel_diff(old, new)
        assert len(diff) == 2


# ---------------------------------------------------------------------------
# DrawCommand unit tests
# ---------------------------------------------------------------------------


class TestDrawCommand:
    def _img(self, color: tuple = (0, 0, 0, 255)) -> Image.Image:
        return Image.new("RGBA", (10, 10), color)

    def test_text_uses_description(self) -> None:
        cmd = DrawCommand(self._img(), [], "Pencil stroke")
        assert cmd.text() == "Pencil stroke"

    def test_first_redo_is_noop(self) -> None:
        img = self._img()
        img.load()[5, 5] = (255, 0, 0, 255)
        changes = [(5, 5, (0, 0, 0, 255), (255, 0, 0, 255))]
        cmd = DrawCommand(img, changes)
        cmd.redo()
        assert img.getpixel((5, 5)) == (255, 0, 0, 255)

    def test_undo_restores_old_color(self) -> None:
        img = self._img()
        old = (0, 0, 0, 255)
        new = (200, 100, 50, 255)
        img.load()[3, 7] = new
        cmd = DrawCommand(img, [(3, 7, old, new)])
        cmd.redo()
        cmd.undo()
        assert img.getpixel((3, 7)) == old

    def test_redo_after_undo_reapplies(self) -> None:
        img = self._img()
        old = (0, 0, 0, 255)
        new = (50, 150, 250, 200)
        img.load()[1, 1] = new
        cmd = DrawCommand(img, [(1, 1, old, new)])
        cmd.redo()  # no-op
        cmd.undo()
        cmd.redo()  # reapplies
        assert img.getpixel((1, 1)) == new

    def test_multiple_pixels_undo(self) -> None:
        img = self._img()
        changes = [
            (0, 0, (0, 0, 0, 255), (10, 10, 10, 255)),
            (1, 0, (0, 0, 0, 255), (20, 20, 20, 255)),
            (0, 1, (0, 0, 0, 255), (30, 30, 30, 255)),
        ]
        px = img.load()
        for x, y, _, new_c in changes:
            px[x, y] = new_c

        cmd = DrawCommand(img, changes)
        cmd.redo()
        cmd.undo()

        for x, y, old_c, _ in changes:
            assert img.getpixel((x, y)) == old_c


class TestFillCommand:
    def test_fill_command_description(self) -> None:
        img = Image.new("RGBA", (4, 4), (0, 0, 0, 255))
        cmd = FillCommand(img, [])
        assert cmd.text() == "Fill"

    def test_fill_undo_restores(self) -> None:
        img = Image.new("RGBA", (4, 4), (0, 0, 0, 255))
        changes = [(0, 0, (0, 0, 0, 255), (255, 255, 255, 255))]
        img.load()[0, 0] = (255, 255, 255, 255)
        cmd = FillCommand(img, changes)
        cmd.redo()
        cmd.undo()
        assert img.getpixel((0, 0)) == (0, 0, 0, 255)


# ---------------------------------------------------------------------------
# EditorCanvas undo stack tests
# ---------------------------------------------------------------------------


class TestCanvasUndoStack:
    def test_undo_stack_is_qundostack(self, qtbot) -> None:
        canvas = EditorCanvas()
        qtbot.addWidget(canvas)
        assert isinstance(canvas.undo_stack, QUndoStack)

    def test_stack_initially_empty(self, qtbot) -> None:
        canvas = EditorCanvas()
        qtbot.addWidget(canvas)
        assert not canvas.undo_stack.canUndo()
        assert not canvas.undo_stack.canRedo()

    def test_stack_cleared_on_load_image(self, qtbot) -> None:
        canvas = EditorCanvas()
        qtbot.addWidget(canvas)
        img = Image.new("RGBA", (8, 8), (0, 0, 0, 255))
        canvas.load_image(img)

        canvas._pre_stroke_image = canvas._current_image.copy()
        canvas._current_image.load()[1, 1] = (255, 0, 0, 255)
        canvas._commit_stroke("Pencil stroke")
        assert canvas.undo_stack.canUndo()

        canvas.load_image(img)
        assert not canvas.undo_stack.canUndo()

    def test_commit_stroke_pushes_when_pixels_changed(self, qtbot) -> None:
        canvas = EditorCanvas()
        qtbot.addWidget(canvas)
        img = Image.new("RGBA", (8, 8), (0, 0, 0, 255))
        canvas.load_image(img)

        canvas._pre_stroke_image = canvas._current_image.copy()
        canvas._current_image.load()[2, 2] = (100, 150, 200, 255)
        canvas._commit_stroke("Pencil stroke")

        assert canvas.undo_stack.canUndo()

    def test_commit_stroke_noop_when_no_change(self, qtbot) -> None:
        canvas = EditorCanvas()
        qtbot.addWidget(canvas)
        img = Image.new("RGBA", (8, 8), (0, 0, 0, 255))
        canvas.load_image(img)

        canvas._pre_stroke_image = canvas._current_image.copy()
        canvas._commit_stroke("Pencil stroke")

        assert not canvas.undo_stack.canUndo()

    def test_undo_restores_pixel(self, qtbot) -> None:
        canvas = EditorCanvas()
        qtbot.addWidget(canvas)
        img = Image.new("RGBA", (8, 8), (0, 0, 0, 255))
        canvas.load_image(img)

        canvas._pre_stroke_image = canvas._current_image.copy()
        canvas._current_image.load()[3, 3] = (200, 100, 50, 255)
        canvas._commit_stroke("Pencil stroke")

        canvas.undo_stack.undo()
        assert canvas._current_image.getpixel((3, 3)) == (0, 0, 0, 255)

    def test_redo_reapplies_pixel(self, qtbot) -> None:
        canvas = EditorCanvas()
        qtbot.addWidget(canvas)
        img = Image.new("RGBA", (8, 8), (0, 0, 0, 255))
        canvas.load_image(img)

        canvas._pre_stroke_image = canvas._current_image.copy()
        canvas._current_image.load()[4, 4] = (10, 20, 30, 200)
        canvas._commit_stroke("Pencil stroke")
        canvas.undo_stack.undo()
        canvas.undo_stack.redo()

        assert canvas._current_image.getpixel((4, 4)) == (10, 20, 30, 200)

    def test_multiple_strokes_multiple_undos(self, qtbot) -> None:
        canvas = EditorCanvas()
        qtbot.addWidget(canvas)
        img = Image.new("RGBA", (8, 8), (0, 0, 0, 255))
        canvas.load_image(img)

        for i, color in enumerate([(255, 0, 0, 255), (0, 255, 0, 255)]):
            canvas._pre_stroke_image = canvas._current_image.copy()
            canvas._current_image.load()[i, i] = color
            canvas._commit_stroke("Pencil stroke")

        canvas.undo_stack.undo()
        assert canvas._current_image.getpixel((1, 1)) == (0, 0, 0, 255)
        assert canvas._current_image.getpixel((0, 0)) == (255, 0, 0, 255)

        canvas.undo_stack.undo()
        assert canvas._current_image.getpixel((0, 0)) == (0, 0, 0, 255)


# ---------------------------------------------------------------------------
# Integration with EditorWindow
# ---------------------------------------------------------------------------


class TestEditorWindowUndoRedo:
    def test_editor_has_edit_menu(self, qtbot, small_ico: Path) -> None:
        window = EditorWindow(small_ico)
        qtbot.addWidget(window)
        titles = [a.text() for a in window.menuBar().actions()]
        assert any("Edit" in t for t in titles)

    def test_draw_then_undo_restores_pixel(self, qtbot, small_ico: Path) -> None:
        window = EditorWindow(small_ico)
        qtbot.addWidget(window)
        window._on_tool_pencil()

        canvas = window._canvas
        img = canvas._current_image
        assert img is not None
        original = img.getpixel((5, 5))

        canvas._pre_stroke_image = img.copy()
        window._palette.set_foreground_color(QColor(200, 50, 10, 255))
        window._tools["pencil"].set_color((200, 50, 10, 255))
        window._tools["pencil"].on_press(5, 5)
        canvas._commit_stroke("Pencil stroke")

        assert img.getpixel((5, 5)) == (200, 50, 10, 255)
        canvas.undo_stack.undo()
        assert img.getpixel((5, 5)) == original

    def test_eraser_then_undo_restores_pixel(self, qtbot, small_ico: Path) -> None:
        window = EditorWindow(small_ico)
        qtbot.addWidget(window)

        canvas = window._canvas
        img = canvas._current_image
        assert img is not None

        # First draw a known pixel
        window._on_tool_pencil()
        canvas._pre_stroke_image = img.copy()
        window._tools["pencil"].set_color((255, 0, 0, 255))
        window._tools["pencil"].on_press(4, 4)
        canvas._commit_stroke("Pencil stroke")
        assert img.getpixel((4, 4)) == (255, 0, 0, 255)

        # Erase it
        window._on_tool_eraser()
        canvas._pre_stroke_image = img.copy()
        window._tools["eraser"].on_press(4, 4)
        canvas._commit_stroke("Eraser stroke")
        assert img.getpixel((4, 4))[3] == 0

        # Undo erase → pixel back
        canvas.undo_stack.undo()
        assert img.getpixel((4, 4)) == (255, 0, 0, 255)

    def test_undo_redo_via_canvas_stack(self, qtbot, small_ico: Path) -> None:
        window = EditorWindow(small_ico)
        qtbot.addWidget(window)
        window._on_tool_pencil()

        canvas = window._canvas
        img = canvas._current_image
        assert img is not None
        original = img.getpixel((6, 6))

        canvas._pre_stroke_image = img.copy()
        window._tools["pencil"].set_color((0, 255, 128, 255))
        window._tools["pencil"].on_press(6, 6)
        canvas._commit_stroke("Pencil stroke")

        canvas.undo_stack.undo()
        assert img.getpixel((6, 6)) == original

        canvas.undo_stack.redo()
        assert img.getpixel((6, 6)) == (0, 255, 128, 255)

    def test_eyedropper_does_not_push_undo(self, qtbot, small_ico: Path) -> None:
        window = EditorWindow(small_ico)
        qtbot.addWidget(window)
        window._on_tool_eyedropper()

        canvas = window._canvas
        canvas._pre_stroke_image = canvas._current_image.copy() if canvas._current_image else None
        window._tools["eyedropper"].on_press(0, 0)
        canvas._commit_stroke("Eyedropper stroke")

        assert not canvas.undo_stack.canUndo()
