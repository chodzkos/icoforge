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
