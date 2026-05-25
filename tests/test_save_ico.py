"""Integration tests for ICO save functionality in the editor."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from icoforge.core.converter import convert
from icoforge.core.ico_reader import read_ico
from icoforge.core.models import IcoConfig, SizeSpec
from icoforge.gui.editor.editor_window import EditorWindow


@pytest.fixture
def two_size_ico(tmp_path: Path) -> Path:
    src = tmp_path / "src.png"
    ico = tmp_path / "test.ico"
    Image.new("RGBA", (32, 32), (0, 128, 255, 255)).save(src)
    convert(src, ico, IcoConfig(sizes=(SizeSpec(16, 16), SizeSpec(32, 32))))
    return ico


def _draw_pixel(window: EditorWindow, x: int, y: int, color: tuple[int, int, int, int]) -> None:
    """Helper: draw a single pixel via the canvas and commit the stroke."""
    canvas = window._canvas
    assert canvas._current_image is not None
    canvas._pre_stroke_image = canvas._current_image.copy()
    canvas._current_image.load()[x, y] = color
    canvas._commit_stroke("Pencil stroke")


# ---------------------------------------------------------------------------
# Dirty-flag tracking
# ---------------------------------------------------------------------------


class TestDirtyFlag:
    def test_initially_clean(self, qtbot, two_size_ico: Path) -> None:
        window = EditorWindow(two_size_ico)
        qtbot.addWidget(window)
        assert not window._unsaved_changes

    def test_dirty_after_draw(self, qtbot, two_size_ico: Path) -> None:
        window = EditorWindow(two_size_ico)
        qtbot.addWidget(window)
        _draw_pixel(window, 0, 0, (99, 99, 99, 255))
        assert window._unsaved_changes

    def test_clean_after_save(self, qtbot, two_size_ico: Path) -> None:
        window = EditorWindow(two_size_ico)
        qtbot.addWidget(window)
        _draw_pixel(window, 0, 0, (99, 99, 99, 255))
        window._on_save()
        assert not window._unsaved_changes

    def test_title_shows_asterisk_when_dirty(self, qtbot, two_size_ico: Path) -> None:
        window = EditorWindow(two_size_ico)
        qtbot.addWidget(window)
        _draw_pixel(window, 1, 1, (10, 20, 30, 255))
        assert " *" in window.windowTitle()

    def test_title_clean_after_save(self, qtbot, two_size_ico: Path) -> None:
        window = EditorWindow(two_size_ico)
        qtbot.addWidget(window)
        _draw_pixel(window, 1, 1, (10, 20, 30, 255))
        window._on_save()
        assert " *" not in window.windowTitle()


# ---------------------------------------------------------------------------
# Pixel round-trip
# ---------------------------------------------------------------------------


class TestSaveRoundTrip:
    def test_edited_pixel_persists_after_save_reload(self, qtbot, two_size_ico: Path) -> None:
        window = EditorWindow(two_size_ico)
        qtbot.addWidget(window)

        canvas = window._canvas
        edited_size = canvas._current_image.size  # type: ignore[union-attr]
        _draw_pixel(window, 5, 5, (200, 50, 10, 255))
        window._on_save()

        frames = read_ico(two_size_ico)
        matching = [img for img, _ in frames if img.size == edited_size]
        assert matching, "No frame with matching size found after reload"
        assert matching[0].getpixel((5, 5)) == (200, 50, 10, 255)

    def test_other_frames_unchanged(self, qtbot, two_size_ico: Path) -> None:
        original_frames = {spec: img.copy() for img, spec in read_ico(two_size_ico)}

        window = EditorWindow(two_size_ico)
        qtbot.addWidget(window)

        canvas = window._canvas
        current_size = canvas._current_image.size  # type: ignore[union-attr]
        _draw_pixel(window, 0, 0, (1, 2, 3, 255))
        window._on_save()

        for img, spec in read_ico(two_size_ico):
            if img.size == current_size:
                continue
            orig = original_frames.get(spec)
            if orig is not None:
                assert list(img.getdata()) == list(orig.getdata()), (
                    f"Frame {spec} was unexpectedly modified"
                )

    def test_undo_after_save_does_not_change_file(self, qtbot, two_size_ico: Path) -> None:
        window = EditorWindow(two_size_ico)
        qtbot.addWidget(window)

        canvas = window._canvas
        img = canvas._current_image
        assert img is not None
        edited_size = img.size

        _draw_pixel(window, 3, 3, (55, 66, 77, 255))
        window._on_save()

        # Undo reverts canvas but file must keep the saved state
        canvas.undo_stack.undo()
        assert img.getpixel((3, 3)) != (55, 66, 77, 255), "Undo did not revert canvas"

        frames = read_ico(two_size_ico)
        matching = [f for f, _ in frames if f.size == edited_size]
        assert matching[0].getpixel((3, 3)) == (55, 66, 77, 255), (
            "File was modified by undo — save should be permanent"
        )

    def test_switch_frame_preserves_first_frame_edits(self, qtbot, two_size_ico: Path) -> None:
        window = EditorWindow(two_size_ico)
        qtbot.addWidget(window)

        canvas = window._canvas
        first_size = canvas._current_image.size  # type: ignore[union-attr]
        _draw_pixel(window, 2, 2, (111, 222, 33, 255))

        # Switch to the other frame
        other_row = 1
        window._size_list.setCurrentRow(other_row)
        window._on_size_selected(window._size_list.item(other_row))  # type: ignore[arg-type]

        # Now save (both frames should be in _frames)
        window._on_save()

        frames = read_ico(two_size_ico)
        matching = [f for f, _ in frames if f.size == first_size]
        assert matching, "Could not find first frame after reload"
        assert matching[0].getpixel((2, 2)) == (111, 222, 33, 255), (
            "Edits in frame 1 were lost after switching to frame 2 and saving"
        )

    def test_save_as_writes_to_new_path(self, qtbot, two_size_ico: Path, tmp_path: Path) -> None:
        window = EditorWindow(two_size_ico)
        qtbot.addWidget(window)

        _draw_pixel(window, 7, 7, (88, 77, 66, 255))

        new_path = tmp_path / "copy.ico"
        window._save_path = new_path
        window._on_save()

        assert new_path.exists(), "save_as did not create the new file"
        frames = read_ico(new_path)
        canvas_size = window._canvas._current_image.size  # type: ignore[union-attr]
        matching = [f for f, _ in frames if f.size == canvas_size]
        assert matching[0].getpixel((7, 7)) == (88, 77, 66, 255)
        # Original file must be untouched
        orig_frames = read_ico(two_size_ico)
        for f, _ in orig_frames:
            if f.size == canvas_size:
                assert f.getpixel((7, 7)) != (88, 77, 66, 255)
                break
