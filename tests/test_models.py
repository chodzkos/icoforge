"""Tests for data model validation."""

from __future__ import annotations

import pytest

from icoforge.core.models import (
    IcoConfig,
    OptimizationConfig,
    ResampleAlgorithm,
    SizeSpec,
)


def test_sizespec_rejects_out_of_range() -> None:
    with pytest.raises(ValueError):
        SizeSpec(0, 16)
    with pytest.raises(ValueError):
        SizeSpec(16, 257)


def test_sizespec_accepts_valid() -> None:
    spec = SizeSpec(64, 64)
    assert spec.bit_depth == 32
    assert spec.resample is None


def test_icoconfig_rejects_empty_sizes() -> None:
    with pytest.raises(ValueError):
        IcoConfig(sizes=())


def test_icoconfig_is_hashable() -> None:
    a = IcoConfig(sizes=(SizeSpec(16, 16), SizeSpec(32, 32)))
    b = IcoConfig(sizes=(SizeSpec(16, 16), SizeSpec(32, 32)))
    assert hash(a) == hash(b)


def test_optimization_level_range() -> None:
    OptimizationConfig(level=0)
    OptimizationConfig(level=6)
    with pytest.raises(ValueError):
        OptimizationConfig(level=7)
    with pytest.raises(ValueError):
        OptimizationConfig(level=-1)


def test_resample_algorithm_values() -> None:
    # Just verify the enum has the expected members
    assert ResampleAlgorithm.LANCZOS.value == "lanczos"
    assert ResampleAlgorithm.NEAREST.value == "nearest"
