"""Tests for gui/editor/export_utils.py."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from icoforge.core.models import SizeSpec
from icoforge.gui.editor.export_utils import (
    export_icns,
    export_separate_pngs,
    export_spritesheet,
    icns_available,
)


def _frames(sizes: list[int]) -> list[tuple[Image.Image, SizeSpec]]:
    return [(Image.new("RGBA", (s, s), (s, 0, 0, 255)), SizeSpec(s, s)) for s in sizes]


class TestExportSeparatePngs:
    def test_creates_png_per_frame(self, tmp_path: Path) -> None:
        saved = export_separate_pngs(_frames([16, 32]), tmp_path)
        assert len(saved) == 2
        assert all(p.suffix == ".png" for p in saved)

    def test_file_names_encode_size(self, tmp_path: Path) -> None:
        saved = export_separate_pngs(_frames([16, 48]), tmp_path)
        names = {p.name for p in saved}
        assert "icon_16x16.png" in names
        assert "icon_48x48.png" in names

    def test_returns_sorted_by_size(self, tmp_path: Path) -> None:
        saved = export_separate_pngs(_frames([48, 16, 32]), tmp_path)
        widths = [int(p.stem.split("_")[1].split("x")[0]) for p in saved]
        assert widths == sorted(widths)

    def test_files_are_valid_pngs(self, tmp_path: Path) -> None:
        export_separate_pngs(_frames([16, 32]), tmp_path)
        for path in tmp_path.iterdir():
            img = Image.open(path)
            assert img.mode in ("RGBA", "RGB", "P")

    def test_creates_directory_if_missing(self, tmp_path: Path) -> None:
        subdir = tmp_path / "nested" / "dir"
        export_separate_pngs(_frames([16]), subdir)
        assert subdir.exists()

    def test_pixel_data_preserved(self, tmp_path: Path) -> None:
        frames = [(Image.new("RGBA", (16, 16), (10, 20, 30, 255)), SizeSpec(16, 16))]
        export_separate_pngs(frames, tmp_path)
        loaded = Image.open(tmp_path / "icon_16x16.png").convert("RGBA")
        assert loaded.getpixel((0, 0)) == (10, 20, 30, 255)


class TestExportSpritesheet:
    def test_output_file_created(self, tmp_path: Path) -> None:
        out = tmp_path / "sheet.png"
        export_spritesheet(_frames([16, 32, 48]), out)
        assert out.exists()
        with Image.open(out) as sheet:
            assert sheet.format == "PNG"
            assert sheet.mode in ("RGBA", "RGB")
            assert sheet.width > 0 and sheet.height > 0

    def test_width_equals_columns_times_cell(self, tmp_path: Path) -> None:
        out = tmp_path / "sheet.png"
        export_spritesheet(_frames([16, 32, 48, 64]), out, columns=2)
        img = Image.open(out)
        assert img.width == 64 * 2  # 2 columns, max cell = 64

    def test_height_equals_rows_times_cell(self, tmp_path: Path) -> None:
        out = tmp_path / "sheet.png"
        export_spritesheet(_frames([16, 32, 48, 64]), out, columns=2)
        img = Image.open(out)
        assert img.height == 64 * 2  # 2 rows

    def test_single_frame(self, tmp_path: Path) -> None:
        out = tmp_path / "sheet.png"
        export_spritesheet(_frames([32]), out)
        img = Image.open(out)
        assert img.size == (32, 32)

    def test_raises_on_empty_frames(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="No frames"):
            export_spritesheet([], tmp_path / "sheet.png")

    def test_returns_output_path(self, tmp_path: Path) -> None:
        out = tmp_path / "sheet.png"
        result = export_spritesheet(_frames([16]), out)
        assert result == out


class TestExportIcns:
    def test_creates_icns_file(self, tmp_path: Path) -> None:
        if not icns_available():
            pytest.skip("ICNS not supported on this platform")
        out = tmp_path / "icon.icns"
        export_icns(_frames([16, 32]), out)
        assert out.exists()
        assert out.stat().st_size > 0
        # Valid ICNS files start with the 'icns' magic.
        assert out.read_bytes()[:4] == b"icns"

    def test_raises_on_empty_frames(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="No frames"):
            export_icns([], tmp_path / "icon.icns")

    def test_returns_output_path(self, tmp_path: Path) -> None:
        if not icns_available():
            pytest.skip("ICNS not supported on this platform")
        out = tmp_path / "icon.icns"
        result = export_icns(_frames([16]), out)
        assert result == out


class TestIcnsAvailable:
    def test_returns_bool(self) -> None:
        result = icns_available()
        assert isinstance(result, bool)
