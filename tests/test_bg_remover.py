"""Tests for icoforge.core.bg_remover."""

from __future__ import annotations

import base64
import io
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from icoforge.core.bg_remover import (
    BgRemoveError,
    is_available,
    is_rembg_available,
    remove_background,
)


def _png_b64(mode: str = "RGBA", size: tuple[int, int] = (4, 4), color: object = (0, 0, 0, 0)) -> bytes:
    """Encode a PIL image as base64 PNG bytes (simulates subprocess stdout)."""
    img = Image.new(mode, size, color)  # type: ignore[arg-type]
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue())


class TestIsAvailable:
    def test_true_when_rembg_importable(self) -> None:
        with patch("importlib.util.find_spec", return_value=MagicMock()):
            assert is_rembg_available() is True

    def test_false_when_rembg_missing(self) -> None:
        with patch("importlib.util.find_spec", return_value=None):
            assert is_rembg_available() is False

    def test_is_available_alias(self) -> None:
        with patch("icoforge.core.bg_remover.REMBG_AVAILABLE", True):
            assert is_available() is True
        with patch("icoforge.core.bg_remover.REMBG_AVAILABLE", False):
            assert is_available() is False


class TestRemoveBackground:
    def _mock_proc(self, returncode: int = 0, stdout: bytes = b"", stderr: bytes = b"") -> MagicMock:
        proc = MagicMock()
        proc.returncode = returncode
        proc.stdout = stdout
        proc.stderr = stderr
        return proc

    def test_returns_rgba_image(self) -> None:
        src = Image.new("RGB", (4, 4), (255, 0, 0))
        output = _png_b64("RGBA", (4, 4), (255, 0, 0, 128))

        with (
            patch("icoforge.core.bg_remover.REMBG_AVAILABLE", True),
            patch("icoforge.core.bg_remover._find_python", return_value=["python3"]),
            patch("icoforge.core.bg_remover.subprocess.run", return_value=self._mock_proc(stdout=output)),
        ):
            result = remove_background(src)

        assert result.mode == "RGBA"
        assert result.size == (4, 4)

    def test_converts_non_rgba_subprocess_output_to_rgba(self) -> None:
        src = Image.new("RGB", (2, 2), (0, 255, 0))
        output = _png_b64("RGB", (2, 2), (0, 255, 0))

        with (
            patch("icoforge.core.bg_remover.REMBG_AVAILABLE", True),
            patch("icoforge.core.bg_remover._find_python", return_value=["python3"]),
            patch("icoforge.core.bg_remover.subprocess.run", return_value=self._mock_proc(stdout=output)),
        ):
            result = remove_background(src)

        assert result.mode == "RGBA"

    def test_raises_when_rembg_not_installed(self) -> None:
        src = Image.new("RGB", (4, 4))
        with (
            patch("icoforge.core.bg_remover.REMBG_AVAILABLE", False),
            pytest.raises(BgRemoveError, match="rembg nie jest zainstalowane"),
        ):
            remove_background(src)

    def test_raises_on_inference_error(self) -> None:
        src = Image.new("RGB", (4, 4))
        proc = self._mock_proc(returncode=1, stderr=b"ONNX failure details")

        with (
            patch("icoforge.core.bg_remover.REMBG_AVAILABLE", True),
            patch("icoforge.core.bg_remover._find_python", return_value=["python3"]),
            patch("icoforge.core.bg_remover.subprocess.run", return_value=proc),
            pytest.raises(BgRemoveError, match="rembg subprocess"),
        ):
            remove_background(src)

    def test_raises_when_python_not_found(self) -> None:
        src = Image.new("RGB", (4, 4))
        with (
            patch("icoforge.core.bg_remover.REMBG_AVAILABLE", True),
            patch("icoforge.core.bg_remover._find_python", return_value=None),
            pytest.raises(BgRemoveError, match="Nie znaleziono Pythona"),
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

        rgba_result = Image.new("RGBA", (64, 64), (255, 100, 50, 255))
        config = IcoConfig(sizes=(SizeSpec(32, 32),), remove_bg=True)

        with (
            patch("icoforge.core.bg_remover.remove_background", return_value=rgba_result) as mock_rb,
            patch("icoforge.core.bg_remover.REMBG_AVAILABLE", True),
        ):
            convert(src, dst, config)

        mock_rb.assert_called_once()

    def test_remove_bg_false_skips_rembg(self, tmp_path: pytest.TempPathFactory) -> None:
        from icoforge.core.converter import convert
        from icoforge.core.models import IcoConfig, SizeSpec

        src = tmp_path / "photo.png"
        Image.new("RGB", (64, 64), (0, 128, 255)).save(src, format="PNG")
        dst = tmp_path / "out.ico"

        config = IcoConfig(sizes=(SizeSpec(32, 32),), remove_bg=False)

        with patch("icoforge.core.bg_remover.remove_background") as mock_rb:
            convert(src, dst, config)

        mock_rb.assert_not_called()
