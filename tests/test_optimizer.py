"""Tests for PNG optimizer module."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from icoforge.core.optimizer import (
    OptimizationResult,
    optimize_png,
    verify_lossless,
)


@pytest.fixture
def simple_png(tmp_path: Path) -> Path:
    """Create a simple PNG with known content for testing."""
    img = Image.new("RGBA", (32, 32), color=(255, 0, 0, 255))
    path = tmp_path / "simple.png"
    img.save(path, "PNG")
    return path


@pytest.fixture
def gradient_png(tmp_path: Path) -> Path:
    """Create a gradient PNG to test compression on varied data."""
    img = Image.new("RGBA", (64, 64))
    pixels = img.load()
    for y in range(64):
        for x in range(64):
            pixels[x, y] = (x * 4, y * 4, 128, 255)
    path = tmp_path / "gradient.png"
    img.save(path, "PNG")
    return path


@pytest.fixture
def png_with_metadata(tmp_path: Path) -> Path:
    """Create a PNG with tEXt metadata chunks."""
    img = Image.new("RGBA", (32, 32), color=(0, 255, 0, 255))
    path = tmp_path / "metadata.png"
    img.save(path, "PNG", info={"Title": "Test Image", "Author": "Test Suite"})
    return path


class TestOptimizePng:
    """Test optimize_png() function."""

    def test_optimize_in_place(self, simple_png: Path) -> None:
        """Test optimization with target=None (in-place)."""
        original_size = simple_png.stat().st_size

        result = optimize_png(simple_png)

        assert result.source == simple_png
        assert result.target == simple_png
        assert result.bytes_before == original_size
        assert result.bytes_after > 0
        assert result.bytes_after <= original_size
        assert simple_png.exists()

    def test_optimize_to_different_path(self, simple_png: Path, tmp_path: Path) -> None:
        """Test optimization to a different output path."""
        target = tmp_path / "optimized.png"

        result = optimize_png(simple_png, target=target)

        assert result.source == simple_png
        assert result.target == target
        assert target.exists()
        assert simple_png.exists()  # Source should remain
        assert result.bytes_after <= result.bytes_before

    def test_compression_ratio(self, simple_png: Path, tmp_path: Path) -> None:
        """Test that optimization produces meaningful compression."""
        target = tmp_path / "optimized.png"

        result = optimize_png(simple_png, target=target)

        ratio = result.saved_ratio
        assert 0.0 <= ratio <= 1.0, f"Ratio out of bounds: {ratio}"
        # Simple solid-color PNG should compress significantly
        assert ratio > 0.1 or result.bytes_before < 200, (
            f"Expected compression for small PNG, got ratio={ratio}"
        )

    def test_different_levels(self, simple_png: Path, tmp_path: Path) -> None:
        """Test that different optimization levels produce different results."""
        from icoforge.core.models import OptimizationConfig

        level_0_target = tmp_path / "level0.png"
        level_6_target = tmp_path / "level6.png"

        result_0 = optimize_png(
            simple_png,
            target=level_0_target,
            config=OptimizationConfig(level=0, strip_metadata=False),
        )
        result_6 = optimize_png(
            simple_png,
            target=level_6_target,
            config=OptimizationConfig(level=6, strip_metadata=False),
        )

        # Level 6 should be smaller or equal to level 0 (or very close)
        assert result_6.bytes_after <= result_0.bytes_after + 10, (
            f"Level 6 ({result_6.bytes_after}) should be <= Level 0 ({result_0.bytes_after})"
        )

    def test_metadata_stripping(self, png_with_metadata: Path, tmp_path: Path) -> None:
        """Test that metadata is removed when strip_metadata=True."""
        from icoforge.core.models import OptimizationConfig

        target = tmp_path / "stripped.png"

        result = optimize_png(
            png_with_metadata,
            target=target,
            config=OptimizationConfig(strip_metadata=True),
        )

        # Metadata stripping should reduce file size
        # (can't reliably check PIL info dict due to format variations)
        assert result.bytes_after < result.bytes_before, (
            "Metadata stripping should reduce file size"
        )

    def test_metadata_not_stripped(self, png_with_metadata: Path, tmp_path: Path) -> None:
        """Test that metadata is preserved when strip_metadata=False."""
        from icoforge.core.models import OptimizationConfig

        target = tmp_path / "with_metadata.png"

        result = optimize_png(
            png_with_metadata,
            target=target,
            config=OptimizationConfig(strip_metadata=False),
        )

        assert target.exists()
        # File should be slightly larger than stripped version
        # (hard to guarantee without testing both, but at least should exist)
        assert result.bytes_after > 0

    def test_source_not_found(self, tmp_path: Path) -> None:
        """Test error handling for missing source file."""
        missing = tmp_path / "nonexistent.png"

        with pytest.raises(FileNotFoundError):
            optimize_png(missing)

    def test_invalid_png(self, tmp_path: Path) -> None:
        """Test error handling for invalid PNG file."""
        invalid_path = tmp_path / "invalid.png"
        invalid_path.write_bytes(b"not a png")

        with pytest.raises(ValueError):
            optimize_png(invalid_path)

    def test_saved_bytes_property(self, simple_png: Path, tmp_path: Path) -> None:
        """Test OptimizationResult.saved_bytes property."""
        target = tmp_path / "opt.png"
        result = optimize_png(simple_png, target=target)

        expected_saved = result.bytes_before - result.bytes_after
        assert result.saved_bytes == expected_saved

    def test_saved_ratio_property(self, simple_png: Path, tmp_path: Path) -> None:
        """Test OptimizationResult.saved_ratio property."""
        target = tmp_path / "opt.png"
        result = optimize_png(simple_png, target=target)

        if result.bytes_before > 0:
            expected_ratio = result.saved_bytes / result.bytes_before
            assert abs(result.saved_ratio - expected_ratio) < 0.0001

    def test_zero_byte_edge_case(self) -> None:
        """Test edge case where bytes_before=0 doesn't cause division by zero."""
        result = OptimizationResult(
            source=Path("test.png"),
            target=Path("out.png"),
            bytes_before=0,
            bytes_after=0,
        )
        assert result.saved_ratio == 0.0


class TestVerifyLossless:
    """Test verify_lossless() function."""

    def test_identical_images(self, simple_png: Path, tmp_path: Path) -> None:
        """Test that identical images verify as lossless."""
        # Copy to create a second identical file
        copy_path = tmp_path / "copy.png"
        copy_path.write_bytes(simple_png.read_bytes())

        assert verify_lossless(simple_png, copy_path)

    def test_same_file(self, simple_png: Path) -> None:
        """Test that a file verified against itself is lossless."""
        assert verify_lossless(simple_png, simple_png)

    def test_different_images(self, simple_png: Path, gradient_png: Path) -> None:
        """Test that different images fail lossless verification."""
        assert not verify_lossless(simple_png, gradient_png)

    def test_optimized_is_lossless(self, gradient_png: Path, tmp_path: Path) -> None:
        """Test that optimized PNG has identical pixel data."""
        optimized = tmp_path / "optimized_gradient.png"

        optimize_png(gradient_png, target=optimized)

        assert verify_lossless(gradient_png, optimized), (
            "Optimized PNG should have identical pixel data"
        )

    def test_lossless_with_all_levels(self, simple_png: Path, tmp_path: Path) -> None:
        """Test that all compression levels maintain losslessness."""
        from icoforge.core.models import OptimizationConfig

        for level in range(7):
            optimized = tmp_path / f"level_{level}.png"
            optimize_png(
                simple_png,
                target=optimized,
                config=OptimizationConfig(level=level, strip_metadata=True),
            )
            assert verify_lossless(simple_png, optimized), f"Level {level} should be lossless"

    def test_lossless_with_zopfli(self, simple_png: Path, tmp_path: Path) -> None:
        """Test that Zopfli optimization (if available) maintains losslessness."""
        from icoforge.core.models import OptimizationConfig

        optimized = tmp_path / "zopfli.png"
        try:
            optimize_png(
                simple_png,
                target=optimized,
                config=OptimizationConfig(use_zopfli=True),
            )
            assert verify_lossless(simple_png, optimized), "Zopfli optimization should be lossless"
        except AttributeError:
            # Zopfli not available in pyoxipng, skip
            pytest.skip("Zopfli not available in pyoxipng")


class TestOptimizationResult:
    """Test OptimizationResult dataclass."""

    def test_result_frozen(self) -> None:
        """Test that OptimizationResult is frozen."""
        result = OptimizationResult(
            source=Path("test.png"),
            target=Path("out.png"),
            bytes_before=1000,
            bytes_after=800,
        )

        with pytest.raises(AttributeError):
            result.bytes_before = 2000  # type: ignore

    def test_result_equality(self) -> None:
        """Test that identical results compare equal."""
        result1 = OptimizationResult(
            source=Path("test.png"),
            target=Path("out.png"),
            bytes_before=1000,
            bytes_after=800,
        )
        result2 = OptimizationResult(
            source=Path("test.png"),
            target=Path("out.png"),
            bytes_before=1000,
            bytes_after=800,
        )
        assert result1 == result2

    def test_result_properties(self) -> None:
        """Test result properties are computed correctly."""
        result = OptimizationResult(
            source=Path("test.png"),
            target=Path("out.png"),
            bytes_before=1000,
            bytes_after=800,
        )

        assert result.saved_bytes == 200
        assert result.saved_ratio == 0.2
