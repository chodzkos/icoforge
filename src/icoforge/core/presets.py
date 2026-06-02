"""User preset system: save/load named IcoConfig configurations as JSON files."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from icoforge.core.models import (
    FAVICON_SIZES,
    TRANSPARENT,
    WINDOWS_APP_SIZES,
    Background,
    Color,
    IcoConfig,
    ResampleAlgorithm,
    SizeSpec,
)
from icoforge.utils.paths import get_settings_dir

_PRESET_FORMAT_VERSION = 1

BUILTIN_PRESETS: dict[str, IcoConfig] = {
    "Windows App Icon": IcoConfig(sizes=WINDOWS_APP_SIZES),
    "Favicon (16/32/48)": IcoConfig(sizes=FAVICON_SIZES),
    "Web (16/32/64/128)": IcoConfig(sizes=tuple(SizeSpec(s, s) for s in (16, 32, 64, 128))),
}


def get_presets_dir() -> Path:
    """Return (and create if needed) the user presets directory."""
    d = get_settings_dir() / "presets"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe_filename(name: str) -> str:
    """Convert a preset name to a filesystem-safe stem."""
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip().strip(".")
    return safe or "preset"


def config_to_dict(config: IcoConfig) -> dict[str, Any]:
    """Serialize *config* to a plain dict suitable for JSON.

    Args:
        config: The IcoConfig to serialize.

    Returns:
        Dict containing sizes, resample, background, preserve_aspect,
        auto_trim, and auto_trim_padding.
    """
    sizes: list[dict[str, Any]] = []
    for spec in config.sizes:
        entry: dict[str, Any] = {
            "width": spec.width,
            "height": spec.height,
            "bit_depth": spec.bit_depth,
        }
        if spec.resample is not None:
            entry["resample"] = spec.resample.value
        sizes.append(entry)

    if config.background is TRANSPARENT:
        bg: str = "transparent"
    else:
        assert isinstance(config.background, Color)
        c = config.background
        bg = (
            f"#{c.r:02x}{c.g:02x}{c.b:02x}"
            if c.a == 255
            else f"#{c.r:02x}{c.g:02x}{c.b:02x}{c.a:02x}"
        )

    return {
        "sizes": sizes,
        "resample": config.resample.value,
        "background": bg,
        "preserve_aspect": config.preserve_aspect,
        "auto_trim": config.auto_trim,
        "auto_trim_padding": config.auto_trim_padding,
    }


def config_from_dict(data: dict[str, Any]) -> IcoConfig:
    """Reconstruct IcoConfig from a plain dict.

    Args:
        data: Dict as produced by :func:`config_to_dict` (or read from JSON).

    Returns:
        Reconstructed IcoConfig.

    Raises:
        ValueError: If *data* is malformed or contains unsupported values.
    """
    try:
        raw_sizes = data["sizes"]
        if not isinstance(raw_sizes, list) or not raw_sizes:
            raise ValueError("'sizes' must be a non-empty list")

        specs: list[SizeSpec] = []
        for entry in raw_sizes:
            resample_raw: str | None = entry.get("resample")
            per_size_resample = ResampleAlgorithm(resample_raw) if resample_raw else None
            specs.append(
                SizeSpec(
                    width=int(entry["width"]),
                    height=int(entry["height"]),
                    bit_depth=int(entry.get("bit_depth", 32)),  # type: ignore[arg-type]
                    resample=per_size_resample,
                )
            )

        resample_algo = ResampleAlgorithm(data.get("resample", "lanczos"))

        bg_raw: str = data.get("background", "transparent")
        background: Background
        if bg_raw == "transparent":
            background = TRANSPARENT
        elif bg_raw.startswith("#"):
            h = bg_raw.lstrip("#")
            if len(h) == 6:
                background = Color(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
            elif len(h) == 8:
                background = Color(
                    int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), int(h[6:8], 16)
                )
            else:
                raise ValueError(f"Invalid background hex: {bg_raw!r}")
        else:
            raise ValueError(f"Unknown background value: {bg_raw!r}")

        return IcoConfig(
            sizes=tuple(specs),
            resample=resample_algo,
            background=background,
            preserve_aspect=bool(data.get("preserve_aspect", True)),
            auto_trim=bool(data.get("auto_trim", False)),
            auto_trim_padding=int(data.get("auto_trim_padding", 0)),
        )
    except (KeyError, TypeError) as exc:
        raise ValueError(f"Invalid preset data: {exc}") from exc


def list_user_presets() -> list[str]:
    """Return names of all saved user presets, sorted alphabetically.

    The name is taken from the ``name`` field inside each JSON file,
    not from the filename.
    """
    names: list[str] = []
    for p in sorted(get_presets_dir().glob("*.json")):
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
            names.append(str(raw.get("name", p.stem)))
        except (json.JSONDecodeError, OSError):
            names.append(p.stem)
    return names


def _preset_path(name: str) -> Path:
    return get_presets_dir() / f"{_safe_filename(name)}.json"


def save_preset(name: str, config: IcoConfig) -> Path:
    """Save a named preset to disk.

    Args:
        name: Human-readable preset name stored inside the file and used
            by :func:`list_user_presets`.
        config: Configuration to persist.

    Returns:
        Path to the written file.
    """
    payload: dict[str, Any] = {
        "name": name,
        "version": _PRESET_FORMAT_VERSION,
        "config": config_to_dict(config),
    }
    path = _preset_path(name)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def load_preset(name: str) -> IcoConfig:
    """Load a named preset from disk.

    Args:
        name: The preset name (as returned by :func:`list_user_presets`).

    Returns:
        Reconstructed IcoConfig.

    Raises:
        FileNotFoundError: If no preset file exists for *name*.
        ValueError: If the file is malformed.
    """
    path = _preset_path(name)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Preset file is not valid JSON: {exc}") from exc
    return config_from_dict(raw["config"])


def delete_preset(name: str) -> None:
    """Delete a user preset file.

    Args:
        name: Preset name to delete.
    """
    _preset_path(name).unlink(missing_ok=True)


def rename_preset(old_name: str, new_name: str) -> None:
    """Rename a user preset.

    Updates the embedded ``name`` field and moves to the new filename.

    Args:
        old_name: Current preset name.
        new_name: Desired new name.

    Raises:
        FileNotFoundError: If *old_name* does not exist.
    """
    old_path = _preset_path(old_name)
    if not old_path.exists():
        raise FileNotFoundError(f"Preset not found: {old_name!r}")
    raw = json.loads(old_path.read_text(encoding="utf-8"))
    raw["name"] = new_name
    new_path = _preset_path(new_name)
    new_path.write_text(json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8")
    if old_path != new_path:
        old_path.unlink()


def export_preset(name: str, dest: Path) -> None:
    """Copy a user preset file to *dest* for sharing.

    Args:
        name: Preset to export.
        dest: Target file path.

    Raises:
        FileNotFoundError: If *name* does not exist.
    """
    src = _preset_path(name)
    if not src.exists():
        raise FileNotFoundError(f"Preset not found: {name!r}")
    dest.write_bytes(src.read_bytes())


def import_preset(src: Path) -> str:
    """Import a preset from *src* into the user presets directory.

    Args:
        src: Source ``.json`` file.

    Returns:
        The imported preset name.

    Raises:
        ValueError: If the file is malformed.
    """
    try:
        raw = json.loads(src.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise ValueError(f"Cannot read preset file: {exc}") from exc
    config_from_dict(raw["config"])  # validate
    name: str = str(raw.get("name", src.stem))
    dest = _preset_path(name)
    dest.write_bytes(src.read_bytes())
    return name
