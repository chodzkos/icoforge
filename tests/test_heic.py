"""Tests for HEIC/HEIF/AVIF source support via :mod:`icoforge.core.heic_loader`.

Tests that require actual HEIC files are skipped when ``pillow-heif`` is not
installed.  The graceful-fallback path (missing-dependency error) is always
tested via monkeypatching, so this file runs cleanly in a minimal environment.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from icoforge.core import heic_loader
from icoforge.core.converter import convert, render_frames
from icoforge.core.heic_loader import HeicSupportMissingError, load_heic
from icoforge.core.models import IcoConfig, SizeSpec

requires_pillow_heif = pytest.mark.skipif(
    not heic_loader.HAS_PILLOW_HEIF,
    reason="pillow-heif not installed (optional 'heic' extra)",
)


@pytest.fixture
def heic_file(tmp_path: Path) -> Path:
    """Create a minimal HEIC file using pillow-heif.  Skips if unavailable."""
    if not heic_loader.HAS_PILLOW_HEIF:
        pytest.skip("pillow-heif not installed")

    import pillow_heif

    pillow_heif.register_heif_opener()

    img = Image.new("RGBA", (64, 64), (200, 100, 50, 255))
    out = tmp_path / "test.heic"
    img.save(out, format="HEIF")
    return out


@pytest.fixture
def avif_file(tmp_path: Path) -> Path:
    """Create a minimal AVIF file using pillow-heif.  Skips if unavailable."""
    if not heic_loader.HAS_PILLOW_HEIF:
        pytest.skip("pillow-heif not installed")

    import pillow_heif

    pillow_heif.register_heif_opener()

    img = Image.new("RGB", (64, 64), (50, 150, 200))
    out = tmp_path / "test.avif"
    img.save(out, format="AVIF")
    return out


# ---------------------------------------------------------------------------
# Graceful fallback when pillow-heif is missing
# ---------------------------------------------------------------------------


class TestMissingPillowHeif:
    """Verify the user-facing error path when pillow-heif is unavailable."""

    def test_load_heic_raises_descriptive_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(heic_loader, "_pillow_heif", None)
        monkeypatch.setattr(heic_loader, "HAS_PILLOW_HEIF", False)

        fake = tmp_path / "img.heic"
        fake.write_bytes(b"not real heic")

        with pytest.raises(HeicSupportMissingError) as exc_info:
            load_heic(fake)
        message = str(exc_info.value)
        assert "pillow-heif" in message
        assert "icoforge[heic]" in message

    def test_convert_heic_raises_when_pillow_heif_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(heic_loader, "_pillow_heif", None)
        monkeypatch.setattr(heic_loader, "HAS_PILLOW_HEIF", False)

        fake = tmp_path / "img.heic"
        fake.write_bytes(b"not real heic")

        with pytest.raises(HeicSupportMissingError):
            convert(fake, tmp_path / "out.ico", IcoConfig(sizes=(SizeSpec(32, 32),)))

    def test_render_frames_heic_raises_when_pillow_heif_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(heic_loader, "_pillow_heif", None)
        monkeypatch.setattr(heic_loader, "HAS_PILLOW_HEIF", False)

        fake = tmp_path / "img.heic"
        fake.write_bytes(b"not real heic")

        with pytest.raises(HeicSupportMissingError):
            render_frames(fake, IcoConfig(sizes=(SizeSpec(32, 32),)))

    def test_raster_pipeline_unaffected_when_pillow_heif_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Disabling pillow-heif must not break the raster pipeline."""
        monkeypatch.setattr(heic_loader, "_pillow_heif", None)
        monkeypatch.setattr(heic_loader, "HAS_PILLOW_HEIF", False)

        src = tmp_path / "in.png"
        Image.new("RGBA", (32, 32), (255, 0, 0, 255)).save(src)
        convert(src, tmp_path / "out.ico", IcoConfig(sizes=(SizeSpec(32, 32),)))
        assert (tmp_path / "out.ico").exists()

    def test_avif_raises_when_pillow_heif_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(heic_loader, "_pillow_heif", None)
        monkeypatch.setattr(heic_loader, "HAS_PILLOW_HEIF", False)

        fake = tmp_path / "img.avif"
        fake.write_bytes(b"not real avif")

        with pytest.raises(HeicSupportMissingError):
            convert(fake, tmp_path / "out.ico", IcoConfig(sizes=(SizeSpec(32, 32),)))


# ---------------------------------------------------------------------------
# Input validation (independent of pillow-heif)
# ---------------------------------------------------------------------------


class TestHeicValidation:
    def test_rejects_missing_source(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            convert(
                tmp_path / "missing.heic",
                tmp_path / "out.ico",
                IcoConfig(sizes=(SizeSpec(16, 16),)),
            )

    def test_heic_in_supported_suffixes(self) -> None:
        from icoforge.core.converter import _HEIC_SUFFIXES, _SUPPORTED_SUFFIXES

        assert ".heic" in _SUPPORTED_SUFFIXES
        assert ".heif" in _SUPPORTED_SUFFIXES
        assert ".avif" in _SUPPORTED_SUFFIXES
        assert frozenset([".heic", ".heif", ".avif"]) == _HEIC_SUFFIXES

    def test_load_heic_missing_file_when_pillow_heif_present(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        if not heic_loader.HAS_PILLOW_HEIF:
            monkeypatch.setattr(heic_loader, "_pillow_heif", object())
            monkeypatch.setattr(heic_loader, "HAS_PILLOW_HEIF", True)
        with pytest.raises(FileNotFoundError):
            load_heic(tmp_path / "missing.heic")

    def test_heic_in_file_drop_zone_suffixes(self) -> None:
        from icoforge.gui.widgets.file_drop_zone import SUPPORTED_SUFFIXES

        assert ".heic" in SUPPORTED_SUFFIXES
        assert ".heif" in SUPPORTED_SUFFIXES
        assert ".avif" in SUPPORTED_SUFFIXES

    def test_register_heif_opener_noop_when_missing(self) -> None:
        """register_heif_opener() must not raise when pillow-heif is absent."""
        import importlib
        import sys

        original = sys.modules.get("pillow_heif")
        sys.modules["pillow_heif"] = None  # type: ignore[assignment]
        try:
            import importlib

            importlib.reload(heic_loader)
            heic_loader.register_heif_opener()
        finally:
            if original is None:
                sys.modules.pop("pillow_heif", None)
            else:
                sys.modules["pillow_heif"] = original
            importlib.reload(heic_loader)


# ---------------------------------------------------------------------------
# Real HEIC/AVIF loading (requires pillow-heif)
# ---------------------------------------------------------------------------


@requires_pillow_heif
class TestHeicLoading:
    def test_load_heic_returns_rgba(self, heic_file: Path) -> None:
        img = load_heic(heic_file)
        assert img.mode == "RGBA"
        assert img.size == (64, 64)

    def test_convert_heic_produces_ico(self, heic_file: Path, tmp_path: Path) -> None:
        target = tmp_path / "out.ico"
        config = IcoConfig(sizes=(SizeSpec(16, 16), SizeSpec(32, 32)))
        convert(heic_file, target, config)
        assert target.exists()

        with Image.open(target) as ico:
            sizes = set(ico.info["sizes"])
        assert sizes == {(16, 16), (32, 32)}

    def test_convert_heic_preserves_colour(self, heic_file: Path, tmp_path: Path) -> None:
        """Source colour must survive the HEIC → ICO round-trip (lossy, so approx)."""
        target = tmp_path / "out.ico"
        convert(heic_file, target, IcoConfig(sizes=(SizeSpec(32, 32),)))

        with Image.open(target) as ico:
            ico.load()
            rgba = ico.convert("RGBA")
        r, g, b, a = rgba.getpixel((16, 16))  # type: ignore[misc]
        assert a == 255
        # HEIC is lossy — allow ±20 per channel
        assert abs(r - 200) <= 20
        assert abs(g - 100) <= 20
        assert abs(b - 50) <= 20

    def test_render_frames_heic_returns_correct_count(self, heic_file: Path) -> None:
        config = IcoConfig(sizes=(SizeSpec(16, 16), SizeSpec(32, 32), SizeSpec(48, 48)))
        frames = render_frames(heic_file, config)
        assert len(frames) == 3
        assert frames[0].size == (16, 16)
        assert frames[2].size == (48, 48)

    def test_heic_cached_across_sizes(self, heic_file: Path, tmp_path: Path) -> None:
        """Multiple sizes from the same HEIC source must all succeed."""
        config = IcoConfig(sizes=(SizeSpec(16, 16), SizeSpec(32, 32), SizeSpec(64, 64)))
        frames = render_frames(heic_file, config)
        assert all(f.mode == "RGBA" for f in frames)

    def test_convert_avif_produces_ico(self, avif_file: Path, tmp_path: Path) -> None:
        target = tmp_path / "out.ico"
        config = IcoConfig(sizes=(SizeSpec(32, 32),))
        convert(avif_file, target, config)
        assert target.exists()
