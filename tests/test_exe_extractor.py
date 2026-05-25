"""Tests for icoforge.core.exe_extractor."""

from __future__ import annotations

import io
import struct
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from icoforge.core.exe_extractor import ExeExtractError, extract_icons_from_exe

FIXTURE = Path(__file__).parent / "fixtures" / "minimal_with_icon.exe"


class TestExtractFromFixture:
    def test_returns_list(self) -> None:
        icons = extract_icons_from_exe(FIXTURE)
        assert isinstance(icons, list)

    def test_finds_one_icon_group(self) -> None:
        icons = extract_icons_from_exe(FIXTURE)
        assert len(icons) == 1

    def test_result_is_valid_ico(self) -> None:
        ico_bytes = extract_icons_from_exe(FIXTURE)[0]
        # ICO magic: reserved=0, type=1
        reserved, ico_type = struct.unpack_from("<HH", ico_bytes, 0)
        assert reserved == 0
        assert ico_type == 1

    def test_pillow_can_open_result(self) -> None:
        ico_bytes = extract_icons_from_exe(FIXTURE)[0]
        img = Image.open(io.BytesIO(ico_bytes))
        assert img.size == (1, 1)


class TestErrorHandling:
    def test_missing_file_raises_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            extract_icons_from_exe(tmp_path / "nope.exe")

    def test_non_pe_file_raises_extract_error(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.exe"
        bad.write_bytes(b"This is not a PE file at all.")
        with pytest.raises(ExeExtractError):
            extract_icons_from_exe(bad)

    def test_pe_without_resources_returns_empty(self, tmp_path: Path) -> None:
        with patch("pefile.PE") as mock_pe_cls:
            mock_pe = MagicMock()
            del mock_pe.DIRECTORY_ENTRY_RESOURCE
            mock_pe_cls.return_value = mock_pe
            dummy = tmp_path / "no_rsrc.exe"
            dummy.write_bytes(b"x")
            # patch exists() so it passes the FileNotFoundError check
            with patch.object(Path, "exists", return_value=True):
                result = extract_icons_from_exe(dummy)
            assert result == []

    def test_pefile_not_installed_raises_extract_error(self, tmp_path: Path) -> None:
        dummy = tmp_path / "test.exe"
        dummy.write_bytes(b"x")
        with (
            patch.dict("sys.modules", {"pefile": None}),
            pytest.raises(ExeExtractError, match="pefile is not installed"),
        ):
            extract_icons_from_exe(dummy)
