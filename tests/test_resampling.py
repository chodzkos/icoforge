"""Tests for resampling algorithm mapping and recommendations."""

from __future__ import annotations

import pytest
from PIL import Image

from icoforge.core.models import ResampleAlgorithm
from icoforge.core.resampling import recommend_for_size, to_pillow


# ---------------------------------------------------------------------------
# to_pillow – mapping coverage
# ---------------------------------------------------------------------------


def test_to_pillow_returns_image_resampling_instance() -> None:
    result = to_pillow(ResampleAlgorithm.LANCZOS)
    assert isinstance(result, Image.Resampling)


@pytest.mark.parametrize(
    ("algo", "expected"),
    [
        (ResampleAlgorithm.LANCZOS, Image.Resampling.LANCZOS),
        (ResampleAlgorithm.BICUBIC, Image.Resampling.BICUBIC),
        (ResampleAlgorithm.BILINEAR, Image.Resampling.BILINEAR),
        (ResampleAlgorithm.NEAREST, Image.Resampling.NEAREST),
        (ResampleAlgorithm.BOX, Image.Resampling.BOX),
    ],
)
def test_to_pillow_maps_every_algorithm(
    algo: ResampleAlgorithm, expected: Image.Resampling
) -> None:
    assert to_pillow(algo) is expected


def test_to_pillow_covers_all_enum_members() -> None:
    """Every ResampleAlgorithm member must have a Pillow mapping."""
    for algo in ResampleAlgorithm:
        result = to_pillow(algo)
        assert isinstance(result, Image.Resampling), f"no mapping for {algo}"


def test_to_pillow_mappings_are_distinct() -> None:
    """Two different algorithms must not map to the same Pillow value."""
    mapped = [to_pillow(a) for a in ResampleAlgorithm]
    assert len(mapped) == len(set(mapped))


# ---------------------------------------------------------------------------
# recommend_for_size – pixel art
# ---------------------------------------------------------------------------


def test_recommend_pixel_art_returns_nearest_regardless_of_size() -> None:
    for size in (1, 16, 24, 32, 48, 256):
        assert recommend_for_size(size, is_pixel_art=True) is ResampleAlgorithm.NEAREST


# ---------------------------------------------------------------------------
# recommend_for_size – small sizes (≤ 24) get BOX
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("size", [1, 16, 20, 24])
def test_recommend_small_size_returns_box(size: int) -> None:
    assert recommend_for_size(size) is ResampleAlgorithm.BOX


# ---------------------------------------------------------------------------
# recommend_for_size – larger sizes (≥ 25) get LANCZOS
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("size", [25, 32, 48, 64, 96, 128, 256])
def test_recommend_large_size_returns_lanczos(size: int) -> None:
    assert recommend_for_size(size) is ResampleAlgorithm.LANCZOS


# ---------------------------------------------------------------------------
# recommend_for_size – boundary conditions
# ---------------------------------------------------------------------------


def test_recommend_boundary_24_is_box() -> None:
    assert recommend_for_size(24) is ResampleAlgorithm.BOX


def test_recommend_boundary_25_is_lanczos() -> None:
    assert recommend_for_size(25) is ResampleAlgorithm.LANCZOS


def test_recommend_rejects_zero_size() -> None:
    with pytest.raises(ValueError):
        recommend_for_size(0)


def test_recommend_rejects_negative_size() -> None:
    with pytest.raises(ValueError):
        recommend_for_size(-1)
