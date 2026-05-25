"""Tests for gui/editor/templates.py."""

from __future__ import annotations

import pytest

from icoforge.gui.editor.templates import (
    _TEMPLATE_SIZES,
    TEMPLATE_CURSOR,
    TEMPLATE_FAVICON,
    TEMPLATE_WINDOWS_APP,
    build_template_frames,
    template_label,
    template_sizes,
)


class TestBuildTemplateFrames:
    def test_windows_app_returns_all_sizes(self) -> None:
        frames = build_template_frames(TEMPLATE_WINDOWS_APP)
        widths = [spec.width for _, spec in frames]
        assert widths == sorted(_TEMPLATE_SIZES[TEMPLATE_WINDOWS_APP])

    def test_favicon_returns_three_sizes(self) -> None:
        frames = build_template_frames(TEMPLATE_FAVICON)
        widths = [spec.width for _, spec in frames]
        assert widths == [16, 32, 48]

    def test_cursor_returns_two_sizes(self) -> None:
        frames = build_template_frames(TEMPLATE_CURSOR)
        widths = [spec.width for _, spec in frames]
        assert widths == [16, 32]

    def test_frames_sorted_ascending(self) -> None:
        for tid in (TEMPLATE_WINDOWS_APP, TEMPLATE_FAVICON, TEMPLATE_CURSOR):
            frames = build_template_frames(tid)
            widths = [spec.width for _, spec in frames]
            assert widths == sorted(widths), f"sizes not sorted for {tid}"

    def test_images_are_rgba(self) -> None:
        for tid in (TEMPLATE_WINDOWS_APP, TEMPLATE_FAVICON, TEMPLATE_CURSOR):
            for img, spec in build_template_frames(tid):
                assert img.mode == "RGBA", f"mode wrong for {tid} size {spec.width}"
                assert img.size == (spec.width, spec.height)

    def test_spec_dimensions_match_image(self) -> None:
        for tid in (TEMPLATE_WINDOWS_APP, TEMPLATE_FAVICON, TEMPLATE_CURSOR):
            for img, spec in build_template_frames(tid):
                assert img.width == spec.width
                assert img.height == spec.height
                assert spec.width == spec.height  # square

    def test_windows_app_blue_gradient_not_uniform(self) -> None:
        frames = build_template_frames(TEMPLATE_WINDOWS_APP)
        img_256 = next(img for img, s in frames if s.width == 256)
        pixels = set(img_256.getdata())
        assert len(pixels) > 1, "Gradient must not be a uniform colour"

    def test_windows_app_is_opaque(self) -> None:
        frames = build_template_frames(TEMPLATE_WINDOWS_APP)
        img_32 = next(img for img, s in frames if s.width == 32)
        alphas = {p[3] for p in img_32.getdata()}
        assert alphas == {255}, "Windows App template must be fully opaque"

    def test_favicon_is_opaque(self) -> None:
        for img, _ in build_template_frames(TEMPLATE_FAVICON):
            alphas = {p[3] for p in img.getdata()}
            assert alphas == {255}

    def test_cursor_has_transparent_pixels(self) -> None:
        frames = build_template_frames(TEMPLATE_CURSOR)
        img_32 = next(img for img, s in frames if s.width == 32)
        alphas = {p[3] for p in img_32.getdata()}
        assert 0 in alphas, "Cursor must have transparent background pixels"

    def test_cursor_has_white_pixels(self) -> None:
        frames = build_template_frames(TEMPLATE_CURSOR)
        img_32 = next(img for img, s in frames if s.width == 32)
        pixels = set(img_32.getdata())
        assert any(p[0] >= 200 and p[3] == 255 for p in pixels), "Cursor must have white fill"

    def test_invalid_template_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown template"):
            build_template_frames("does_not_exist")


class TestTemplateHelpers:
    def test_template_label_windows(self) -> None:
        assert "Windows" in template_label(TEMPLATE_WINDOWS_APP)

    def test_template_label_favicon(self) -> None:
        assert "Favicon" in template_label(TEMPLATE_FAVICON)

    def test_template_sizes_returns_list(self) -> None:
        sizes = template_sizes(TEMPLATE_CURSOR)
        assert isinstance(sizes, list)
        assert set(sizes) == {16, 32}
