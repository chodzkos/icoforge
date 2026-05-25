"""Tests for NewIcoDialog and EditorWindow new-document workflow."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from icoforge.core.models import SizeSpec
from icoforge.gui.editor.editor_window import EditorWindow
from icoforge.gui.editor.new_ico_dialog import AVAILABLE_SIZES, NewIcoDialog
from icoforge.gui.editor.templates import (
    _TEMPLATE_SIZES,
    TEMPLATE_CURSOR,
    TEMPLATE_WINDOWS_APP,
)

# ---------------------------------------------------------------------------
# NewIcoDialog - unit tests
# ---------------------------------------------------------------------------


class TestNewIcoDialogDefaults:
    def test_default_sizes_are_checked(self, qtbot) -> None:
        dlg = NewIcoDialog()
        qtbot.addWidget(dlg)
        checked = {s for s, cb in dlg._size_checkboxes.items() if cb.isChecked()}
        assert checked == {16, 32, 48, 256}

    def test_all_available_sizes_present(self, qtbot) -> None:
        dlg = NewIcoDialog()
        qtbot.addWidget(dlg)
        assert set(dlg._size_checkboxes.keys()) == set(AVAILABLE_SIZES)

    def test_ok_enabled_by_default(self, qtbot) -> None:
        dlg = NewIcoDialog()
        qtbot.addWidget(dlg)
        assert dlg._ok_btn.isEnabled()

    def test_ok_disabled_when_no_size_selected(self, qtbot) -> None:
        dlg = NewIcoDialog()
        qtbot.addWidget(dlg)
        for cb in dlg._size_checkboxes.values():
            cb.setChecked(False)
        assert not dlg._ok_btn.isEnabled()

    def test_ok_re_enabled_when_size_rechecked(self, qtbot) -> None:
        dlg = NewIcoDialog()
        qtbot.addWidget(dlg)
        for cb in dlg._size_checkboxes.values():
            cb.setChecked(False)
        dlg._size_checkboxes[32].setChecked(True)
        assert dlg._ok_btn.isEnabled()

    def test_blank_template_selected_by_default(self, qtbot) -> None:
        dlg = NewIcoDialog()
        qtbot.addWidget(dlg)
        assert dlg._rb_blank.isChecked()
        assert not dlg._rb_filled.isChecked()
        assert not dlg._rb_clipboard.isChecked()

    def test_transparent_background_selected_by_default(self, qtbot) -> None:
        dlg = NewIcoDialog()
        qtbot.addWidget(dlg)
        assert dlg._rb_transparent.isChecked()


class TestNewIcoDialogGetFrames:
    def _select_only(self, dlg: NewIcoDialog, sizes: set[int]) -> None:
        for s, cb in dlg._size_checkboxes.items():
            cb.setChecked(s in sizes)

    def test_blank_frames_are_fully_transparent(self, qtbot) -> None:
        dlg = NewIcoDialog()
        qtbot.addWidget(dlg)
        self._select_only(dlg, {16, 32})
        dlg._rb_blank.setChecked(True)

        frames = dlg.get_frames()
        assert len(frames) == 2
        for img, spec in frames:
            assert img.mode == "RGBA"
            assert img.size == (spec.width, spec.height)
            pixels = list(img.getdata())
            assert all(p[3] == 0 for p in pixels), "Blank frame must be fully transparent"

    def test_filled_frames_have_correct_color(self, qtbot) -> None:
        from PySide6.QtGui import QColor

        dlg = NewIcoDialog()
        qtbot.addWidget(dlg)
        self._select_only(dlg, {16})
        dlg._bg_color = QColor(255, 0, 128, 255)
        dlg._rb_filled.setChecked(True)

        frames = dlg.get_frames()
        assert len(frames) == 1
        img, _spec = frames[0]
        assert img.size == (16, 16)
        unique = set(img.getdata())
        assert len(unique) == 1
        assert unique.pop() == (255, 0, 128, 255)

    def test_frame_sizes_match_specs(self, qtbot) -> None:
        dlg = NewIcoDialog()
        qtbot.addWidget(dlg)
        self._select_only(dlg, {16, 48, 256})

        frames = dlg.get_frames()
        sizes = [(img.width, img.height) for img, _ in frames]
        assert sizes == [(16, 16), (48, 48), (256, 256)]

    def test_frames_sorted_by_size(self, qtbot) -> None:
        dlg = NewIcoDialog()
        qtbot.addWidget(dlg)
        # Check 256 first, then 16 — get_frames should return sorted
        dlg._size_checkboxes[256].setChecked(True)
        dlg._size_checkboxes[16].setChecked(True)
        for s in [20, 24, 32, 40, 48, 64, 96, 128]:
            dlg._size_checkboxes[s].setChecked(False)

        frames = dlg.get_frames()
        widths = [img.width for img, _ in frames]
        assert widths == sorted(widths)

    def test_specs_use_bit_depth_32(self, qtbot) -> None:
        dlg = NewIcoDialog()
        qtbot.addWidget(dlg)
        self._select_only(dlg, {32})

        _, spec = dlg.get_frames()[0]
        assert spec.bit_depth == 32

    def test_preview_list_matches_selected_sizes(self, qtbot) -> None:
        dlg = NewIcoDialog()
        qtbot.addWidget(dlg)
        self._select_only(dlg, {16, 32, 48})
        dlg._update_preview()

        assert dlg._preview_list.count() == 3


class TestNewIcoDialogStartupTemplates:
    def test_windows_template_checks_all_sizes(self, qtbot) -> None:
        dlg = NewIcoDialog()
        qtbot.addWidget(dlg)
        dlg._rb_tmpl_windows.setChecked(True)
        checked = {s for s, cb in dlg._size_checkboxes.items() if cb.isChecked()}
        assert checked == set(_TEMPLATE_SIZES[TEMPLATE_WINDOWS_APP])

    def test_favicon_template_checks_three_sizes(self, qtbot) -> None:
        dlg = NewIcoDialog()
        qtbot.addWidget(dlg)
        dlg._rb_tmpl_favicon.setChecked(True)
        checked = {s for s, cb in dlg._size_checkboxes.items() if cb.isChecked()}
        assert checked == {16, 32, 48}

    def test_cursor_template_checks_two_sizes(self, qtbot) -> None:
        dlg = NewIcoDialog()
        qtbot.addWidget(dlg)
        dlg._rb_tmpl_cursor.setChecked(True)
        checked = {s for s, cb in dlg._size_checkboxes.items() if cb.isChecked()}
        assert checked == {16, 32}

    def test_get_frames_returns_template_frames(self, qtbot) -> None:
        dlg = NewIcoDialog()
        qtbot.addWidget(dlg)
        dlg._rb_tmpl_favicon.setChecked(True)
        frames = dlg.get_frames()
        widths = [spec.width for _, spec in frames]
        assert widths == [16, 32, 48]

    def test_template_frames_are_opaque(self, qtbot) -> None:
        dlg = NewIcoDialog()
        qtbot.addWidget(dlg)
        dlg._rb_tmpl_windows.setChecked(True)
        frames = dlg.get_frames()
        for img, _ in frames:
            alphas = {p[3] for p in img.getdata()}
            assert alphas == {255}

    def test_ok_enabled_for_startup_template(self, qtbot) -> None:
        dlg = NewIcoDialog()
        qtbot.addWidget(dlg)
        # Deselect all sizes first
        for cb in dlg._size_checkboxes.values():
            cb.setChecked(False)
        # Selecting a startup template re-enables OK
        dlg._rb_tmpl_favicon.setChecked(True)
        assert dlg._ok_btn.isEnabled()

    def test_preview_count_matches_template_sizes(self, qtbot) -> None:
        dlg = NewIcoDialog()
        qtbot.addWidget(dlg)
        dlg._rb_tmpl_cursor.setChecked(True)
        dlg._update_preview()
        assert dlg._preview_list.count() == len(_TEMPLATE_SIZES[TEMPLATE_CURSOR])

    def test_active_startup_template_none_by_default(self, qtbot) -> None:
        dlg = NewIcoDialog()
        qtbot.addWidget(dlg)
        assert dlg._active_startup_template() is None

    def test_active_startup_template_detects_selection(self, qtbot) -> None:
        dlg = NewIcoDialog()
        qtbot.addWidget(dlg)
        dlg._rb_tmpl_windows.setChecked(True)
        assert dlg._active_startup_template() == TEMPLATE_WINDOWS_APP


# ---------------------------------------------------------------------------
# EditorWindow - new document workflow
# ---------------------------------------------------------------------------


def _make_frames(sizes: list[int]) -> list[tuple[Image.Image, SizeSpec]]:
    return [(Image.new("RGBA", (s, s), (0, 0, 0, 0)), SizeSpec(s, s)) for s in sizes]


class TestEditorWindowNewDocument:
    def test_is_new_file_true_when_frames_passed(self, qtbot) -> None:
        window = EditorWindow(Path("nienazwany.ico"), frames=_make_frames([16, 32]))
        qtbot.addWidget(window)
        assert window._is_new_file

    def test_is_new_file_false_for_existing_ico(self, qtbot, tmp_path) -> None:
        from PIL import Image as PILImage

        from icoforge.core.converter import convert
        from icoforge.core.models import IcoConfig

        src = tmp_path / "s.png"
        ico = tmp_path / "t.ico"
        PILImage.new("RGBA", (32, 32), (0, 0, 0, 255)).save(src)
        convert(src, ico, IcoConfig(sizes=(SizeSpec(32, 32),)))

        window = EditorWindow(ico)
        qtbot.addWidget(window)
        assert not window._is_new_file

    def test_unsaved_changes_true_for_new_document(self, qtbot) -> None:
        window = EditorWindow(Path("nienazwany.ico"), frames=_make_frames([16]))
        qtbot.addWidget(window)
        assert window._unsaved_changes

    def test_title_shows_asterisk_for_new_document(self, qtbot) -> None:
        window = EditorWindow(Path("nienazwany.ico"), frames=_make_frames([32]))
        qtbot.addWidget(window)
        assert " *" in window.windowTitle()

    def test_size_list_populated_from_frames(self, qtbot) -> None:
        window = EditorWindow(Path("nienazwany.ico"), frames=_make_frames([16, 32, 48]))
        qtbot.addWidget(window)
        assert window._size_list.count() == 3

    def test_canvas_loaded_with_first_frame(self, qtbot) -> None:
        frames = _make_frames([16, 32])
        window = EditorWindow(Path("nienazwany.ico"), frames=frames)
        qtbot.addWidget(window)
        assert window._canvas._current_image is not None
        assert window._canvas._current_image.size == (16, 16)

    def test_save_redirects_to_save_as_for_new_document(self, qtbot, tmp_path) -> None:
        """_on_save on a new document should call _on_save_as (no crash, no write)."""
        window = EditorWindow(Path("nienazwany.ico"), frames=_make_frames([16]))
        qtbot.addWidget(window)

        called = []

        def mock_save_as() -> None:
            called.append(True)

        window._on_save_as = mock_save_as  # type: ignore[method-assign]
        window._on_save()
        assert called, "_on_save_as was not called for a new document"

    def test_is_new_file_cleared_after_real_save(self, qtbot, tmp_path) -> None:
        window = EditorWindow(Path("nienazwany.ico"), frames=_make_frames([16, 32]))
        qtbot.addWidget(window)

        real_path = tmp_path / "output.ico"
        window._save_path = real_path
        window._is_new_file = False  # simulate user having chosen path via Save As
        window._on_save()

        assert real_path.exists()
        assert not window._is_new_file
        assert not window._unsaved_changes
