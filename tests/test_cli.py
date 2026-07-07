"""Tests for the CLI (icoforge-cli convert)."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner
from PIL import Image

from icoforge.cli import main

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ico_sizes(path: Path) -> set[tuple[int, int]]:
    with Image.open(path) as ico:
        return set(ico.info["sizes"])


def _make_png(tmp_path: Path, mode: str = "RGBA", size: tuple[int, int] = (64, 64)) -> Path:
    img = Image.new(mode, size, (255, 0, 0, 255) if mode == "RGBA" else (255, 0, 0))
    p = tmp_path / f"src_{mode}.png"
    img.save(p)
    return p


def _make_jpeg(tmp_path: Path) -> Path:
    img = Image.new("RGB", (64, 64), (100, 150, 200))
    p = tmp_path / "src.jpg"
    img.save(p, format="JPEG")
    return p


# ---------------------------------------------------------------------------
# Basic conversion
# ---------------------------------------------------------------------------


def test_convert_default_sizes(tmp_path: Path) -> None:
    src = _make_png(tmp_path)
    out = tmp_path / "out.ico"
    result = CliRunner().invoke(main, ["convert", str(src), str(out)])
    assert result.exit_code == 0, result.output
    assert out.exists()
    assert _ico_sizes(out) == {(16, 16), (32, 32), (48, 48), (256, 256)}


def test_convert_explicit_sizes(tmp_path: Path) -> None:
    src = _make_png(tmp_path)
    out = tmp_path / "out.ico"
    result = CliRunner().invoke(main, ["convert", str(src), str(out), "--sizes", "32,64"])
    assert result.exit_code == 0, result.output
    assert _ico_sizes(out) == {(32, 32), (64, 64)}


# ---------------------------------------------------------------------------
# Presets
# ---------------------------------------------------------------------------


def test_convert_preset_windows(tmp_path: Path) -> None:
    src = _make_png(tmp_path)
    out = tmp_path / "out.ico"
    result = CliRunner().invoke(main, ["convert", str(src), str(out), "--sizes", "windows"])
    assert result.exit_code == 0, result.output
    sizes = _ico_sizes(out)
    assert (16, 16) in sizes
    assert (256, 256) in sizes
    assert len(sizes) == 10


def test_convert_preset_favicon(tmp_path: Path) -> None:
    src = _make_png(tmp_path)
    out = tmp_path / "out.ico"
    result = CliRunner().invoke(main, ["convert", str(src), str(out), "--sizes", "favicon"])
    assert result.exit_code == 0, result.output
    assert _ico_sizes(out) == {(16, 16), (32, 32), (48, 48)}


# ---------------------------------------------------------------------------
# --resample flag
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("algo", ["lanczos", "bicubic", "bilinear", "nearest", "box"])
def test_convert_resample_algorithms(algo: str, tmp_path: Path) -> None:
    src = _make_png(tmp_path)
    out = tmp_path / f"out_{algo}.ico"
    result = CliRunner().invoke(
        main, ["convert", str(src), str(out), "--sizes", "32", "--resample", algo]
    )
    assert result.exit_code == 0, result.output
    assert out.exists()


# ---------------------------------------------------------------------------
# --background flag
# ---------------------------------------------------------------------------


def test_convert_background_transparent(tmp_path: Path) -> None:
    src = _make_jpeg(tmp_path)
    out = tmp_path / "out.ico"
    result = CliRunner().invoke(
        main, ["convert", str(src), str(out), "--sizes", "32", "--background", "transparent"]
    )
    assert result.exit_code == 0, result.output


def test_convert_background_hex_rgb(tmp_path: Path) -> None:
    src = _make_jpeg(tmp_path)
    out = tmp_path / "out.ico"
    result = CliRunner().invoke(
        main, ["convert", str(src), str(out), "--sizes", "32", "--background", "#ffffff"]
    )
    assert result.exit_code == 0, result.output


def test_convert_background_hex_rgba(tmp_path: Path) -> None:
    src = _make_jpeg(tmp_path)
    out = tmp_path / "out.ico"
    result = CliRunner().invoke(
        main, ["convert", str(src), str(out), "--sizes", "32", "--background", "#ffffffff"]
    )
    assert result.exit_code == 0, result.output


def test_convert_background_without_hash(tmp_path: Path) -> None:
    src = _make_jpeg(tmp_path)
    out = tmp_path / "out.ico"
    result = CliRunner().invoke(
        main, ["convert", str(src), str(out), "--sizes", "32", "--background", "ff0000"]
    )
    assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# --bit-depth flag
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("depth", ["8", "24", "32"])
def test_convert_bit_depth(depth: str, tmp_path: Path) -> None:
    src = _make_png(tmp_path)
    out = tmp_path / f"out_{depth}.ico"
    result = CliRunner().invoke(
        main, ["convert", str(src), str(out), "--sizes", "32", "--bit-depth", depth]
    )
    assert result.exit_code == 0, result.output
    assert out.exists()


def test_convert_bit_depth_default_is_32(tmp_path: Path) -> None:
    src = _make_png(tmp_path)
    out = tmp_path / "out.ico"
    result = CliRunner().invoke(main, ["convert", str(src), str(out), "--sizes", "32"])
    assert result.exit_code == 0, result.output


def test_convert_bad_bit_depth_exits_nonzero(tmp_path: Path) -> None:
    src = _make_png(tmp_path)
    result = CliRunner().invoke(
        main, ["convert", str(src), str(tmp_path / "out.ico"), "--bit-depth", "16"]
    )
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# --keep-aspect / --no-keep-aspect flag
# ---------------------------------------------------------------------------


def _make_wide_png(tmp_path: Path) -> Path:
    from PIL import Image as _Image

    img = _Image.new("RGBA", (256, 128), (255, 0, 0, 255))
    p = tmp_path / "wide.png"
    img.save(p)
    return p


def test_convert_keep_aspect_default(tmp_path: Path) -> None:
    src = _make_wide_png(tmp_path)
    out = tmp_path / "out.ico"
    result = CliRunner().invoke(main, ["convert", str(src), str(out), "--sizes", "32"])
    assert result.exit_code == 0, result.output
    assert _ico_sizes(out) == {(32, 32)}


def test_convert_no_keep_aspect(tmp_path: Path) -> None:
    src = _make_wide_png(tmp_path)
    out = tmp_path / "out.ico"
    result = CliRunner().invoke(
        main, ["convert", str(src), str(out), "--sizes", "32", "--no-keep-aspect"]
    )
    assert result.exit_code == 0, result.output
    assert _ico_sizes(out) == {(32, 32)}


def test_convert_keep_aspect_explicit(tmp_path: Path) -> None:
    src = _make_wide_png(tmp_path)
    out = tmp_path / "out.ico"
    result = CliRunner().invoke(
        main, ["convert", str(src), str(out), "--sizes", "32", "--keep-aspect"]
    )
    assert result.exit_code == 0, result.output
    assert _ico_sizes(out) == {(32, 32)}


# ---------------------------------------------------------------------------
# Progress bar
# ---------------------------------------------------------------------------


def test_convert_progress_output_contains_bar(tmp_path: Path) -> None:
    src = _make_png(tmp_path)
    out = tmp_path / "out.ico"
    result = CliRunner().invoke(main, ["convert", str(src), str(out), "--sizes", "32"])
    assert "[" in result.output
    assert "#" in result.output or "-" in result.output
    assert "100.0%" in result.output


def test_convert_output_contains_wrote_line(tmp_path: Path) -> None:
    src = _make_png(tmp_path)
    out = tmp_path / "out.ico"
    result = CliRunner().invoke(main, ["convert", str(src), str(out), "--sizes", "32"])
    assert "Wrote" in result.output


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_convert_missing_source_exits_nonzero(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        main, ["convert", str(tmp_path / "no-such-file.png"), str(tmp_path / "out.ico")]
    )
    assert result.exit_code != 0


def test_convert_bad_sizes_integer_exits_nonzero(tmp_path: Path) -> None:
    src = _make_png(tmp_path)
    result = CliRunner().invoke(
        main, ["convert", str(src), str(tmp_path / "out.ico"), "--sizes", "abc"]
    )
    assert result.exit_code != 0


def test_convert_bad_sizes_out_of_range_exits_nonzero(tmp_path: Path) -> None:
    src = _make_png(tmp_path)
    result = CliRunner().invoke(
        main, ["convert", str(src), str(tmp_path / "out.ico"), "--sizes", "0"]
    )
    assert result.exit_code != 0


def test_convert_bad_background_exits_nonzero(tmp_path: Path) -> None:
    src = _make_png(tmp_path)
    result = CliRunner().invoke(
        main, ["convert", str(src), str(tmp_path / "out.ico"), "--background", "notacolor"]
    )
    assert result.exit_code != 0


def test_convert_bad_background_error_message(tmp_path: Path) -> None:
    src = _make_png(tmp_path)
    result = CliRunner().invoke(
        main, ["convert", str(src), str(tmp_path / "out.ico"), "--background", "zzz"]
    )
    assert result.exit_code != 0
    assert "--background" in result.output


def test_convert_bad_sizes_error_mentions_param(tmp_path: Path) -> None:
    src = _make_png(tmp_path)
    result = CliRunner().invoke(
        main, ["convert", str(src), str(tmp_path / "out.ico"), "--sizes", "bad"]
    )
    assert result.exit_code != 0
    assert "--sizes" in result.output


def test_convert_unsupported_format_exits_nonzero(tmp_path: Path) -> None:
    bogus = tmp_path / "file.xyz"
    bogus.write_bytes(b"data")
    result = CliRunner().invoke(
        main,
        ["convert", str(bogus), str(tmp_path / "out.ico")],
        catch_exceptions=False,
    )
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# --source-N (per-size source overrides)
# ---------------------------------------------------------------------------


def _solid_png(tmp_path: Path, name: str, rgba: tuple[int, int, int, int]) -> Path:
    img = Image.new("RGBA", (256, 256), rgba)
    p = tmp_path / name
    img.save(p)
    return p


def test_convert_source_override_16(tmp_path: Path) -> None:
    main_src = _solid_png(tmp_path, "main.png", (255, 0, 0, 255))
    src_16 = _solid_png(tmp_path, "f16.png", (0, 0, 255, 255))
    out = tmp_path / "out.ico"

    result = CliRunner().invoke(
        main,
        [
            "convert",
            str(main_src),
            str(out),
            "--sizes",
            "16,32",
            "--source-16",
            str(src_16),
        ],
    )
    assert result.exit_code == 0, result.output
    with Image.open(out) as ico:
        ico.size = (16, 16)  # type: ignore[misc]
        ico.load()
        assert ico.convert("RGBA").getpixel((8, 8)) == (0, 0, 255, 255)
    with Image.open(out) as ico:
        ico.size = (32, 32)  # type: ignore[misc]
        ico.load()
        assert ico.convert("RGBA").getpixel((16, 16)) == (255, 0, 0, 255)


def test_convert_source_override_16_and_256(tmp_path: Path) -> None:
    main_src = _solid_png(tmp_path, "main.png", (10, 10, 10, 255))
    src_16 = _solid_png(tmp_path, "f16.png", (255, 0, 0, 255))
    src_256 = _solid_png(tmp_path, "f256.png", (0, 255, 0, 255))
    out = tmp_path / "out.ico"

    result = CliRunner().invoke(
        main,
        [
            "convert",
            str(main_src),
            str(out),
            "--sizes",
            "16,256",
            "--source-16",
            str(src_16),
            "--source-256",
            str(src_256),
        ],
    )
    assert result.exit_code == 0, result.output
    with Image.open(out) as ico:
        ico.size = (16, 16)  # type: ignore[misc]
        ico.load()
        assert ico.convert("RGBA").getpixel((8, 8)) == (255, 0, 0, 255)
    with Image.open(out) as ico:
        ico.size = (256, 256)  # type: ignore[misc]
        ico.load()
        assert ico.convert("RGBA").getpixel((128, 128)) == (0, 255, 0, 255)


def test_convert_source_override_missing_file_exits_nonzero(tmp_path: Path) -> None:
    main_src = _make_png(tmp_path)
    result = CliRunner().invoke(
        main,
        [
            "convert",
            str(main_src),
            str(tmp_path / "out.ico"),
            "--sizes",
            "16,32",
            "--source-16",
            str(tmp_path / "does-not-exist.png"),
        ],
    )
    assert result.exit_code != 0


def test_convert_source_override_for_unrequested_size_exits_nonzero(tmp_path: Path) -> None:
    """--source-128 should fail when 128 is not in --sizes."""
    main_src = _make_png(tmp_path)
    src_128 = _solid_png(tmp_path, "f128.png", (0, 255, 0, 255))
    result = CliRunner().invoke(
        main,
        [
            "convert",
            str(main_src),
            str(tmp_path / "out.ico"),
            "--sizes",
            "16,32",
            "--source-128",
            str(src_128),
        ],
    )
    assert result.exit_code != 0
    assert "--source-128" in result.output


def test_convert_no_source_overrides_unchanged(tmp_path: Path) -> None:
    """Sanity: omitting all --source-N flags behaves exactly like before."""
    src = _make_png(tmp_path)
    out = tmp_path / "out.ico"
    result = CliRunner().invoke(main, ["convert", str(src), str(out), "--sizes", "16,32"])
    assert result.exit_code == 0, result.output
    assert _ico_sizes(out) == {(16, 16), (32, 32)}


# ---------------------------------------------------------------------------
# optimize command — safe-default behaviour
# ---------------------------------------------------------------------------


def _make_opt_png(tmp_path: Path, name: str = "src.png") -> Path:
    img = Image.new("RGBA", (32, 32), (0, 128, 255, 255))
    p = tmp_path / name
    img.save(p, "PNG")
    return p


class TestOptimizeCli:
    def test_default_creates_min_png_source_untouched(self, tmp_path: Path) -> None:
        """No flags: writes <stem>.min.png; source bytes unchanged."""
        src = _make_opt_png(tmp_path)
        original_bytes = src.read_bytes()

        result = CliRunner().invoke(main, ["optimize", str(src)])

        assert result.exit_code == 0, result.output
        min_png = tmp_path / "src.min.png"
        assert min_png.exists(), ".min.png must be created in default mode"
        assert src.read_bytes() == original_bytes, "source must not be modified"

    def test_in_place_modifies_source_no_min_png(self, tmp_path: Path) -> None:
        """--in-place overwrites source; no .min.png created."""
        src = _make_opt_png(tmp_path)
        original_bytes = src.read_bytes()

        result = CliRunner().invoke(main, ["optimize", "--in-place", str(src)])

        assert result.exit_code == 0, result.output
        # oxipng should produce something smaller (solid-colour PNG compresses well)
        assert len(src.read_bytes()) <= len(original_bytes)
        assert not (tmp_path / "src.min.png").exists()

    def test_output_flag_writes_to_given_path(self, tmp_path: Path) -> None:
        """--output writes to the given path; source unchanged."""
        src = _make_opt_png(tmp_path)
        out = tmp_path / "result.png"
        original_bytes = src.read_bytes()

        result = CliRunner().invoke(main, ["optimize", "--output", str(out), str(src)])

        assert result.exit_code == 0, result.output
        assert out.exists()
        assert src.read_bytes() == original_bytes

    def test_in_place_and_output_conflict(self, tmp_path: Path) -> None:
        """--in-place together with --output must exit non-zero."""
        src = _make_opt_png(tmp_path)
        out = tmp_path / "result.png"

        result = CliRunner().invoke(
            main, ["optimize", "--in-place", "--output", str(out), str(src)]
        )

        assert result.exit_code != 0

    def test_default_target_exists_without_force_exits_nonzero(self, tmp_path: Path) -> None:
        """If <stem>.min.png already exists, error without --force."""
        src = _make_opt_png(tmp_path)
        existing = tmp_path / "src.min.png"
        existing.write_bytes(b"existing")

        result = CliRunner().invoke(main, ["optimize", str(src)])

        assert result.exit_code != 0
        assert existing.read_bytes() == b"existing", "existing file must not be overwritten"

    def test_default_force_overwrites_existing_min_png(self, tmp_path: Path) -> None:
        """--force allows overwriting an existing <stem>.min.png."""
        src = _make_opt_png(tmp_path)
        existing = tmp_path / "src.min.png"
        existing.write_bytes(b"old")

        result = CliRunner().invoke(main, ["optimize", "--force", str(src)])

        assert result.exit_code == 0, result.output
        assert existing.read_bytes() != b"old", "--force must overwrite the existing file"

    def test_multiple_files_without_in_place_exits_nonzero(self, tmp_path: Path) -> None:
        """Multiple files without --in-place must refuse with exit code != 0."""
        a = _make_opt_png(tmp_path, "a.png")
        b = _make_opt_png(tmp_path, "b.png")
        bytes_a = a.read_bytes()
        bytes_b = b.read_bytes()

        result = CliRunner().invoke(main, ["optimize", str(a), str(b)])

        assert result.exit_code != 0
        assert a.read_bytes() == bytes_a, "file a must not be touched"
        assert b.read_bytes() == bytes_b, "file b must not be touched"

    def test_multiple_files_with_in_place(self, tmp_path: Path) -> None:
        """Multiple files with --in-place optimizes all in-place."""
        a = _make_opt_png(tmp_path, "a.png")
        b = _make_opt_png(tmp_path, "b.png")
        size_a_before = a.stat().st_size
        size_b_before = b.stat().st_size

        result = CliRunner().invoke(main, ["optimize", "--in-place", str(a), str(b)])

        assert result.exit_code == 0, result.output
        assert a.stat().st_size <= size_a_before
        assert b.stat().st_size <= size_b_before


# ---------------------------------------------------------------------------
# .cur hotspot validation
# ---------------------------------------------------------------------------


class TestCurHotspotValidation:
    """Hotspot must lie inside every frame; out-of-bounds → non-zero exit, no file."""

    def test_hotspot_outside_smallest_frame_fails(self, tmp_path: Path) -> None:
        src = _make_png(tmp_path)
        out = tmp_path / "out.cur"
        result = CliRunner().invoke(
            main,
            ["convert", str(src), str(out), "--sizes", "16", "--hotspot", "64,64"],
        )
        assert result.exit_code != 0
        assert not out.exists(), "Output .cur must NOT be created for invalid hotspot"
        assert "hotspot" in result.output.lower() or "hotspot" in (result.stderr or "").lower()

    def test_hotspot_equals_frame_size_fails(self, tmp_path: Path) -> None:
        """Hotspot at exactly (size, size) is out of bounds (0-indexed)."""
        src = _make_png(tmp_path)
        out = tmp_path / "out.cur"
        result = CliRunner().invoke(
            main,
            ["convert", str(src), str(out), "--sizes", "32", "--hotspot", "32,32"],
        )
        assert result.exit_code != 0
        assert not out.exists()

    def test_hotspot_outside_smaller_of_two_frames_fails(self, tmp_path: Path) -> None:
        """Hotspot valid for large frame but outside the small one → reject."""
        src = _make_png(tmp_path)
        out = tmp_path / "out.cur"
        result = CliRunner().invoke(
            main,
            ["convert", str(src), str(out), "--sizes", "16,32", "--hotspot", "20,20"],
        )
        assert result.exit_code != 0
        assert not out.exists()

    def test_hotspot_0_0_always_valid(self, tmp_path: Path) -> None:
        src = _make_png(tmp_path)
        out = tmp_path / "out.cur"
        result = CliRunner().invoke(
            main,
            ["convert", str(src), str(out), "--sizes", "32", "--hotspot", "0,0"],
        )
        assert result.exit_code == 0, result.output
        assert out.exists()

    def test_hotspot_at_max_valid_coordinate(self, tmp_path: Path) -> None:
        """Hotspot at (size-1, size-1) is the last valid pixel."""
        src = _make_png(tmp_path)
        out = tmp_path / "out.cur"
        result = CliRunner().invoke(
            main,
            ["convert", str(src), str(out), "--sizes", "32", "--hotspot", "31,31"],
        )
        assert result.exit_code == 0, result.output
        assert out.exists()


# ---------------------------------------------------------------------------
# ICNS default sizes
# ---------------------------------------------------------------------------


def _icns_block_tags(path: Path) -> set[bytes]:
    """Return the set of 4-byte block tags present in an ICNS file."""
    import struct

    data = path.read_bytes()
    tags: set[bytes] = set()
    offset = 8  # skip the 8-byte file header (magic + total length)
    while offset < len(data):
        tag = data[offset : offset + 4]
        (block_len,) = struct.unpack(">I", data[offset + 4 : offset + 8])
        if block_len < 8:
            break
        tags.add(tag)
        offset += block_len
    return tags


class TestIcnsDefaultSizes:
    def test_convert_icns_without_sizes_succeeds(self, tmp_path: Path) -> None:
        """`convert x.icns` without --sizes must pick ICNS-valid defaults (no 48)."""
        from icoforge.core.icns_writer import _SIZE_TO_TAG

        src = _make_png(tmp_path, size=(256, 256))
        out = tmp_path / "out.icns"
        result = CliRunner().invoke(main, ["convert", str(src), str(out)])

        assert result.exit_code == 0, result.output
        assert out.exists()
        assert out.read_bytes()[:4] == b"icns"

        expected = {_SIZE_TO_TAG[s] for s in (16, 32, 64, 128, 256, 512)}
        assert _icns_block_tags(out) == expected

    def test_convert_icns_explicit_invalid_size_fails(self, tmp_path: Path) -> None:
        """Explicit --sizes with an ICNS-invalid value (48) must still error out."""
        src = _make_png(tmp_path)
        out = tmp_path / "out.icns"
        result = CliRunner().invoke(
            main, ["convert", str(src), str(out), "--sizes", "48"]
        )

        assert result.exit_code != 0
        assert "ICNS" in result.output
        assert "48" in result.output
        assert not out.exists()

    def test_convert_icns_explicit_valid_sizes_ok(self, tmp_path: Path) -> None:
        """Explicit ICNS-valid sizes are honoured unchanged."""
        from icoforge.core.icns_writer import _SIZE_TO_TAG

        src = _make_png(tmp_path, size=(128, 128))
        out = tmp_path / "out.icns"
        result = CliRunner().invoke(
            main, ["convert", str(src), str(out), "--sizes", "16,32"]
        )

        assert result.exit_code == 0, result.output
        assert _icns_block_tags(out) == {_SIZE_TO_TAG[16], _SIZE_TO_TAG[32]}

    def test_convert_ico_without_sizes_still_includes_48(self, tmp_path: Path) -> None:
        """The ICNS default must not change ICO/CUR behaviour (48 stays)."""
        src = _make_png(tmp_path)
        out = tmp_path / "out.ico"
        result = CliRunner().invoke(main, ["convert", str(src), str(out)])

        assert result.exit_code == 0, result.output
        assert _ico_sizes(out) == {(16, 16), (32, 32), (48, 48), (256, 256)}

    def test_convert_icns_preset_with_invalid_sizes_maps(self, tmp_path: Path) -> None:
        """A preset aimed at ICNS drops unsupported sizes with a warning."""
        from icoforge.core.icns_writer import _SIZE_TO_TAG

        src = _make_png(tmp_path, size=(256, 256))
        out = tmp_path / "out.icns"
        result = CliRunner().invoke(
            main,
            ["convert", str(src), str(out), "--preset", "Windows App Icon"],
        )

        assert result.exit_code == 0, result.output
        assert "unsupported by ICNS" in result.output
        # Windows App Icon = 16/20/24/32/40/48/64/96/128/256 → only ICNS-valid remain.
        expected = {_SIZE_TO_TAG[s] for s in (16, 32, 64, 128, 256)}
        assert _icns_block_tags(out) == expected
