"""Tests for icoforge.core.bg_remover."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from icoforge.core.bg_remover import BgRemoveError, is_available, remove_background


class TestIsAvailable:
    def test_true_when_rembg_importable(self) -> None:
        mock_rembg = MagicMock()
        with patch.dict("sys.modules", {"rembg": mock_rembg}):
            assert is_available() is True

    def test_false_when_rembg_missing(self) -> None:
        with patch.dict("sys.modules", {"rembg": None}):
            assert is_available() is False


class TestRemoveBackground:
    def test_returns_rgba_image(self) -> None:
        src = Image.new("RGB", (4, 4), (255, 0, 0))
        expected = Image.new("RGBA", (4, 4), (255, 0, 0, 0))

        mock_rembg = MagicMock()
        mock_rembg.remove.return_value = expected
        with patch.dict("sys.modules", {"rembg": mock_rembg}):
            result = remove_background(src)

        assert result.mode == "RGBA"
        mock_rembg.remove.assert_called_once_with(src)

    def test_converts_non_rgba_result_to_rgba(self) -> None:
        src = Image.new("RGB", (2, 2), (0, 255, 0))
        # rembg returns RGB instead of RGBA (edge case)
        mock_rembg = MagicMock()
        mock_rembg.remove.return_value = Image.new("RGB", (2, 2), (0, 255, 0))
        with patch.dict("sys.modules", {"rembg": mock_rembg}):
            result = remove_background(src)
        assert result.mode == "RGBA"

    def test_raises_when_rembg_not_installed(self) -> None:
        src = Image.new("RGB", (4, 4))
        with (
            patch.dict("sys.modules", {"rembg": None}),
            pytest.raises(BgRemoveError, match="rembg is not installed"),
        ):
            remove_background(src)

    def test_raises_on_inference_error(self) -> None:
        src = Image.new("RGB", (4, 4))
        mock_rembg = MagicMock()
        mock_rembg.remove.side_effect = RuntimeError("ONNX failure")
        with (
            patch.dict("sys.modules", {"rembg": mock_rembg}),
            pytest.raises(BgRemoveError, match="Background removal failed"),
        ):
            remove_background(src)


class TestIcoConfigRemoveBg:
    def test_default_is_false(self) -> None:
        from icoforge.core.models import IcoConfig, SizeSpec

        config = IcoConfig(sizes=(SizeSpec(32, 32),))
        assert config.remove_bg is False

    def test_can_be_set_true(self) -> None:
        from icoforge.core.models import IcoConfig, SizeSpec

        config = IcoConfig(sizes=(SizeSpec(32, 32),), remove_bg=True)
        assert config.remove_bg is True


class TestConverterIntegration:
    def test_remove_bg_called_during_convert(self, tmp_path: pytest.TempPathFactory) -> None:
        from icoforge.core.converter import convert
        from icoforge.core.models import IcoConfig, SizeSpec

        src = tmp_path / "photo.png"
        Image.new("RGB", (64, 64), (255, 100, 50)).save(src, format="PNG")
        dst = tmp_path / "out.ico"

        rgba_result = Image.new("RGBA", (64, 64), (255, 100, 50, 0))

        mock_rembg = MagicMock()
        mock_rembg.remove.return_value = rgba_result

        config = IcoConfig(sizes=(SizeSpec(32, 32),), remove_bg=True)
        with patch.dict("sys.modules", {"rembg": mock_rembg}):
            convert(src, dst, config)

        mock_rembg.remove.assert_called_once()

    def test_remove_bg_false_skips_rembg(self, tmp_path: pytest.TempPathFactory) -> None:
        from icoforge.core.converter import convert
        from icoforge.core.models import IcoConfig, SizeSpec

        src = tmp_path / "photo.png"
        Image.new("RGB", (64, 64), (0, 128, 255)).save(src, format="PNG")
        dst = tmp_path / "out.ico"

        mock_rembg = MagicMock()

        config = IcoConfig(sizes=(SizeSpec(32, 32),), remove_bg=False)
        with patch.dict("sys.modules", {"rembg": mock_rembg}):
            convert(src, dst, config)

        mock_rembg.remove.assert_not_called()
