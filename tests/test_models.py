"""Tests for data model validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from icoforge.core.models import (
    FAVICON_SIZES,
    TRANSPARENT,
    WINDOWS_APP_SIZES,
    Color,
    IcoConfig,
    OptimizationConfig,
    ResampleAlgorithm,
    SizeSpec,
)

# ---------------------------------------------------------------------------
# Color
# ---------------------------------------------------------------------------


def test_color_accepts_valid_rgb() -> None:
    c = Color(0, 128, 255)
    assert c.r == 0 and c.g == 128 and c.b == 255
    assert c.a == 255


def test_color_accepts_valid_rgba() -> None:
    c = Color(10, 20, 30, 0)
    assert c.a == 0


def test_color_rejects_channel_below_zero() -> None:
    with pytest.raises(ValueError, match="'r'"):
        Color(-1, 0, 0)
    with pytest.raises(ValueError, match="'g'"):
        Color(0, -1, 0)
    with pytest.raises(ValueError, match="'b'"):
        Color(0, 0, -1)
    with pytest.raises(ValueError, match="'a'"):
        Color(0, 0, 0, -1)


def test_color_rejects_channel_above_255() -> None:
    with pytest.raises(ValueError):
        Color(256, 0, 0)
    with pytest.raises(ValueError):
        Color(0, 0, 0, 256)


def test_color_as_tuple() -> None:
    assert Color(1, 2, 3, 4).as_tuple() == (1, 2, 3, 4)
    assert Color(255, 0, 0).as_tuple() == (255, 0, 0, 255)


def test_color_is_hashable() -> None:
    assert hash(Color(1, 2, 3)) == hash(Color(1, 2, 3))
    assert hash(Color(1, 2, 3)) != hash(Color(3, 2, 1))


# ---------------------------------------------------------------------------
# SizeSpec
# ---------------------------------------------------------------------------


def test_sizespec_accepts_valid() -> None:
    spec = SizeSpec(64, 64)
    assert spec.bit_depth == 32
    assert spec.resample is None
    assert spec.source_override is None


def test_sizespec_rejects_out_of_range() -> None:
    with pytest.raises(ValueError):
        SizeSpec(0, 16)
    with pytest.raises(ValueError):
        SizeSpec(16, 257)
    with pytest.raises(ValueError):
        SizeSpec(257, 16)
    with pytest.raises(ValueError):
        SizeSpec(1, 0)


def test_sizespec_rejects_invalid_bit_depth() -> None:
    with pytest.raises(ValueError, match="bit_depth"):
        SizeSpec(32, 32, bit_depth=16)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        SizeSpec(32, 32, bit_depth=4)  # type: ignore[arg-type]


def test_sizespec_accepts_valid_bit_depths() -> None:
    for depth in (8, 24, 32):
        spec = SizeSpec(16, 16, bit_depth=depth)  # type: ignore[arg-type]
        assert spec.bit_depth == depth


def test_sizespec_accepts_source_override() -> None:
    p = Path("/some/image.png")
    spec = SizeSpec(16, 16, source_override=p)
    assert spec.source_override == p


def test_sizespec_accepts_resample_override() -> None:
    spec = SizeSpec(16, 16, resample=ResampleAlgorithm.NEAREST)
    assert spec.resample is ResampleAlgorithm.NEAREST


def test_sizespec_is_hashable() -> None:
    a = SizeSpec(32, 32)
    b = SizeSpec(32, 32)
    assert hash(a) == hash(b)


# ---------------------------------------------------------------------------
# IcoConfig
# ---------------------------------------------------------------------------


def test_icoconfig_rejects_empty_sizes() -> None:
    with pytest.raises(ValueError):
        IcoConfig(sizes=())


def test_icoconfig_defaults() -> None:
    cfg = IcoConfig(sizes=(SizeSpec(32, 32),))
    assert cfg.resample is ResampleAlgorithm.LANCZOS
    assert cfg.background is TRANSPARENT
    assert cfg.preserve_aspect is True
    assert cfg.auto_trim is False


def test_icoconfig_accepts_color_background() -> None:
    bg = Color(255, 255, 255)
    cfg = IcoConfig(sizes=(SizeSpec(32, 32),), background=bg)
    assert cfg.background == bg


def test_icoconfig_is_hashable() -> None:
    a = IcoConfig(sizes=(SizeSpec(16, 16), SizeSpec(32, 32)))
    b = IcoConfig(sizes=(SizeSpec(16, 16), SizeSpec(32, 32)))
    assert hash(a) == hash(b)


# ---------------------------------------------------------------------------
# OptimizationConfig
# ---------------------------------------------------------------------------


def test_optimization_level_range() -> None:
    OptimizationConfig(level=0)
    OptimizationConfig(level=6)
    with pytest.raises(ValueError):
        OptimizationConfig(level=7)
    with pytest.raises(ValueError):
        OptimizationConfig(level=-1)


def test_optimization_config_defaults() -> None:
    cfg = OptimizationConfig()
    assert cfg.level == 4
    assert cfg.strip_metadata is True
    assert cfg.use_zopfli is False
    assert cfg.preserve_color_profile is False
    assert cfg.keep_chunks == frozenset()


def test_optimization_config_keep_chunks() -> None:
    cfg = OptimizationConfig(keep_chunks=frozenset({"iCCP", "pHYs"}))
    assert "iCCP" in cfg.keep_chunks
    assert "pHYs" in cfg.keep_chunks


# ---------------------------------------------------------------------------
# ResampleAlgorithm
# ---------------------------------------------------------------------------


def test_resample_algorithm_values() -> None:
    assert ResampleAlgorithm.LANCZOS.value == "lanczos"
    assert ResampleAlgorithm.NEAREST.value == "nearest"


def test_resample_algorithm_all_members() -> None:
    expected = {"lanczos", "bicubic", "bilinear", "nearest", "box"}
    actual = {a.value for a in ResampleAlgorithm}
    assert actual == expected


# ---------------------------------------------------------------------------
# Presets
# ---------------------------------------------------------------------------


def test_windows_app_sizes_preset() -> None:
    assert len(WINDOWS_APP_SIZES) == 10
    widths = [s.width for s in WINDOWS_APP_SIZES]
    assert widths[0] == 16
    assert widths[-1] == 256
    assert widths == sorted(widths)


def test_favicon_sizes_preset() -> None:
    assert len(FAVICON_SIZES) == 3
    widths = [s.width for s in FAVICON_SIZES]
    assert widths == [16, 32, 48]


def test_presets_are_square() -> None:
    for spec in (*WINDOWS_APP_SIZES, *FAVICON_SIZES):
        assert spec.width == spec.height
