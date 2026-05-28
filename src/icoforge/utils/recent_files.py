"""Recent files persistence (last 10 opened/saved files)."""

from __future__ import annotations

import json
from pathlib import Path

from icoforge.utils.paths import get_settings_dir

MAX_RECENT = 10
_KEY = "recent_files"


def _settings_path() -> Path:
    return get_settings_dir() / "settings.json"


def _load_json() -> dict[str, object]:
    try:
        return dict(json.loads(_settings_path().read_text(encoding="utf-8")))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_json(data: dict[str, object]) -> None:
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_recent() -> list[Path]:
    """Return stored recent file paths (may include non-existent files)."""
    data = _load_json()
    raw = data.get(_KEY, [])
    if not isinstance(raw, list):
        return []
    return [Path(str(p)) for p in raw]


def save_recent(paths: list[Path]) -> None:
    """Persist the given list of recent file paths."""
    data = _load_json()
    data[_KEY] = [str(p) for p in paths]
    _save_json(data)


def add_recent(path: Path) -> list[Path]:
    """Prepend path, deduplicate, trim to MAX_RECENT. Returns the updated list."""
    existing = [p for p in load_recent() if p != path]
    updated = [path, *existing][:MAX_RECENT]
    save_recent(updated)
    return updated


def remove_missing(paths: list[Path]) -> list[Path]:
    """Return only paths that currently exist on disk."""
    return [p for p in paths if p.exists()]
