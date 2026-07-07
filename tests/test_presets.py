"""Tests for the preset save/load/manage system."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from icoforge.core.models import Color, IcoConfig, ResampleAlgorithm, SizeSpec
from icoforge.core.presets import (
    BUILTIN_PRESETS,
    config_from_dict,
    config_to_dict,
    delete_preset,
    export_preset,
    import_preset,
    list_user_presets,
    load_preset,
    rename_preset,
    save_preset,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SIMPLE_CONFIG = IcoConfig(
    sizes=(SizeSpec(16, 16), SizeSpec(32, 32, bit_depth=24)),
    resample=ResampleAlgorithm.BOX,
    background=Color(255, 0, 0),
    preserve_aspect=False,
    auto_trim=True,
    auto_trim_padding=4,
)

_TRANSPARENT_CONFIG = IcoConfig(
    sizes=(SizeSpec(48, 48),),
)


# ---------------------------------------------------------------------------
# config_to_dict / config_from_dict round-trip
# ---------------------------------------------------------------------------


def test_roundtrip_simple() -> None:
    d = config_to_dict(_SIMPLE_CONFIG)
    restored = config_from_dict(d)
    assert restored.resample == _SIMPLE_CONFIG.resample
    assert restored.preserve_aspect == _SIMPLE_CONFIG.preserve_aspect
    assert restored.auto_trim == _SIMPLE_CONFIG.auto_trim
    assert restored.auto_trim_padding == _SIMPLE_CONFIG.auto_trim_padding
    assert isinstance(restored.background, Color)
    assert restored.background.r == 255
    assert restored.background.g == 0
    assert len(restored.sizes) == 2
    assert restored.sizes[0].width == 16
    assert restored.sizes[1].bit_depth == 24


# Non-trivial values for every field that affects the conversion result.
_FULL_CONFIG = IcoConfig(
    sizes=(
        SizeSpec(16, 24, bit_depth=8, resample=ResampleAlgorithm.NEAREST),
        SizeSpec(
            32,
            32,
            bit_depth=24,
            resample=ResampleAlgorithm.BICUBIC,
            source_override=Path("/tmp/hand_drawn_32.png"),
        ),
    ),
    resample=ResampleAlgorithm.BOX,
    background=Color(10, 20, 30, 128),
    preserve_aspect=False,
    auto_trim=True,
    auto_trim_padding=7,
    remove_bg=True,
    cursor_hotspot=(3, 5),
)


def test_roundtrip_full_config_equal() -> None:
    """Every field survives a config_to_dict → config_from_dict round-trip."""
    restored = config_from_dict(config_to_dict(_FULL_CONFIG))
    assert restored == _FULL_CONFIG


def test_roundtrip_full_config_via_disk(preset_dir: Path) -> None:
    """save_preset → load_preset preserves the full configuration."""
    save_preset("Full", _FULL_CONFIG)
    assert load_preset("Full") == _FULL_CONFIG


def test_roundtrip_preserves_remove_bg(preset_dir: Path) -> None:
    """Regression: remove_bg must not be silently dropped on load."""
    save_preset("Bg", IcoConfig(sizes=(SizeSpec(32, 32),), remove_bg=True))
    assert load_preset("Bg").remove_bg is True


def test_load_v1_preset_defaults_new_fields(preset_dir: Path) -> None:
    """A legacy v1 preset (no new fields) loads with sensible defaults."""
    legacy = {
        "name": "Legacy",
        "version": 1,
        "config": {
            "sizes": [{"width": 16, "height": 16, "bit_depth": 32}],
            "resample": "lanczos",
            "background": "transparent",
            "preserve_aspect": True,
            "auto_trim": False,
            "auto_trim_padding": 0,
        },
    }
    (preset_dir / "Legacy.json").write_text(json.dumps(legacy))
    cfg = load_preset("Legacy")
    assert cfg.remove_bg is False
    assert cfg.cursor_hotspot is None
    assert cfg.sizes[0].source_override is None


def test_roundtrip_transparent() -> None:
    d = config_to_dict(_TRANSPARENT_CONFIG)
    assert d["background"] == "transparent"
    restored = config_from_dict(d)
    assert restored.background == "transparent"
    assert restored.sizes[0].width == 48


def test_roundtrip_rgba_background() -> None:
    config = IcoConfig(
        sizes=(SizeSpec(32, 32),),
        background=Color(0, 128, 255, 200),
    )
    d = config_to_dict(config)
    assert d["background"] == "#0080ffc8"
    restored = config_from_dict(d)
    assert isinstance(restored.background, Color)
    assert restored.background.a == 200


def test_roundtrip_per_size_resample() -> None:
    config = IcoConfig(
        sizes=(SizeSpec(16, 16, resample=ResampleAlgorithm.NEAREST), SizeSpec(256, 256)),
    )
    d = config_to_dict(config)
    assert d["sizes"][0]["resample"] == "nearest"
    assert "resample" not in d["sizes"][1]
    restored = config_from_dict(d)
    assert restored.sizes[0].resample == ResampleAlgorithm.NEAREST
    assert restored.sizes[1].resample is None


def test_config_from_dict_missing_sizes_raises() -> None:
    with pytest.raises(ValueError, match="sizes"):
        config_from_dict({"sizes": [], "resample": "lanczos", "background": "transparent"})


def test_config_from_dict_bad_background_raises() -> None:
    with pytest.raises(ValueError, match="background"):
        config_from_dict(
            {"sizes": [{"width": 32, "height": 32}], "resample": "lanczos", "background": "red"}
        )


def test_config_from_dict_bad_hex_raises() -> None:
    with pytest.raises(ValueError, match="hex"):
        config_from_dict(
            {
                "sizes": [{"width": 32, "height": 32}],
                "resample": "lanczos",
                "background": "#fff",
            }
        )


# ---------------------------------------------------------------------------
# File operations (use tmp_path to avoid touching real settings dir)
# ---------------------------------------------------------------------------


@pytest.fixture()
def preset_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect the preset storage to a tmp directory."""
    d = tmp_path / "presets"
    d.mkdir()
    from icoforge.core import presets as _mod

    monkeypatch.setattr(_mod, "get_presets_dir", lambda: d)
    return d


def test_save_and_load(preset_dir: Path) -> None:
    save_preset("MyTest", _SIMPLE_CONFIG)
    loaded = load_preset("MyTest")
    assert loaded.resample == _SIMPLE_CONFIG.resample
    assert loaded.auto_trim_padding == 4


def test_save_creates_file(preset_dir: Path) -> None:
    path = save_preset("Abc", _TRANSPARENT_CONFIG)
    assert path.exists()
    raw = json.loads(path.read_text())
    assert raw["name"] == "Abc"
    assert raw["version"] == 2


def test_list_user_presets_empty(preset_dir: Path) -> None:
    assert list_user_presets() == []


def test_list_user_presets(preset_dir: Path) -> None:
    save_preset("Beta", _SIMPLE_CONFIG)
    save_preset("Alpha", _TRANSPARENT_CONFIG)
    names = list_user_presets()
    assert "Alpha" in names
    assert "Beta" in names
    # list returns names from file content, but sorted by filename
    assert names.index("Alpha") < names.index("Beta")


def test_delete_preset(preset_dir: Path) -> None:
    save_preset("ToDelete", _SIMPLE_CONFIG)
    assert "ToDelete" in list_user_presets()
    delete_preset("ToDelete")
    assert "ToDelete" not in list_user_presets()


def test_delete_nonexistent_is_noop(preset_dir: Path) -> None:
    delete_preset("DoesNotExist")  # should not raise


def test_rename_preset(preset_dir: Path) -> None:
    save_preset("OldName", _SIMPLE_CONFIG)
    rename_preset("OldName", "NewName")
    assert "NewName" in list_user_presets()
    assert "OldName" not in list_user_presets()
    # content should be preserved
    loaded = load_preset("NewName")
    assert loaded.auto_trim_padding == 4


def test_rename_updates_embedded_name(preset_dir: Path) -> None:
    save_preset("Original", _SIMPLE_CONFIG)
    rename_preset("Original", "Renamed")
    files = list(preset_dir.glob("*.json"))
    assert len(files) == 1
    raw = json.loads(files[0].read_text())
    assert raw["name"] == "Renamed"


def test_rename_missing_raises(preset_dir: Path) -> None:
    with pytest.raises(FileNotFoundError):
        rename_preset("Ghost", "Anything")


def test_export_import_roundtrip(preset_dir: Path, tmp_path: Path) -> None:
    save_preset("Exported", _SIMPLE_CONFIG)
    dest = tmp_path / "exported.json"
    export_preset("Exported", dest)
    assert dest.exists()

    # Delete the original and reimport
    delete_preset("Exported")
    assert "Exported" not in list_user_presets()

    name = import_preset(dest)
    assert name == "Exported"
    assert "Exported" in list_user_presets()
    loaded = load_preset("Exported")
    assert loaded.resample == _SIMPLE_CONFIG.resample


def test_import_bad_file_raises(preset_dir: Path, tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json")
    with pytest.raises(ValueError):
        import_preset(bad)


def test_import_missing_config_raises(preset_dir: Path, tmp_path: Path) -> None:
    bad = tmp_path / "noconfig.json"
    bad.write_text('{"name": "x", "version": 1}')
    with pytest.raises((ValueError, KeyError)):
        import_preset(bad)


# ---------------------------------------------------------------------------
# BUILTIN_PRESETS sanity checks
# ---------------------------------------------------------------------------


def test_builtin_presets_not_empty() -> None:
    assert len(BUILTIN_PRESETS) >= 3


def test_builtin_presets_are_valid_configs() -> None:
    for name, config in BUILTIN_PRESETS.items():
        assert isinstance(config, IcoConfig), f"Builtin preset {name!r} is not IcoConfig"
        assert config.sizes, f"Builtin preset {name!r} has empty sizes"


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------


def test_cli_presets_list() -> None:
    from click.testing import CliRunner

    from icoforge.cli import main

    result = CliRunner().invoke(main, ["presets", "list"])
    assert result.exit_code == 0
    for name in BUILTIN_PRESETS:
        assert name in result.output


def test_cli_presets_show() -> None:
    from click.testing import CliRunner

    from icoforge.cli import main

    first_builtin = next(iter(BUILTIN_PRESETS))
    result = CliRunner().invoke(main, ["presets", "show", first_builtin])
    assert result.exit_code == 0
    assert "Resample" in result.output


def test_cli_presets_show_unknown() -> None:
    from click.testing import CliRunner

    from icoforge.cli import main

    result = CliRunner().invoke(main, ["presets", "show", "DoesNotExist99"])
    assert result.exit_code != 0


def test_cli_convert_with_builtin_preset(tmp_path: Path, tmp_png: Path) -> None:
    from click.testing import CliRunner

    from icoforge.cli import main

    out = tmp_path / "out.ico"
    result = CliRunner().invoke(
        main,
        ["convert", str(tmp_png), str(out), "--preset", "Favicon (16/32/48)"],
    )
    assert result.exit_code == 0, result.output
    assert out.exists()


def test_cli_convert_preset_sizes_overridden(tmp_path: Path, tmp_png: Path) -> None:
    from click.testing import CliRunner

    from icoforge.cli import main

    out = tmp_path / "out.ico"
    result = CliRunner().invoke(
        main,
        [
            "convert",
            str(tmp_png),
            str(out),
            "--preset",
            "Favicon (16/32/48)",
            "--sizes",
            "16,32",
        ],
    )
    assert result.exit_code == 0, result.output
