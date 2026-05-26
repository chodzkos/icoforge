"""Application settings (persistent key-value store)."""

from __future__ import annotations

import json
from pathlib import Path

from icoforge.utils.paths import get_settings_dir


def _settings_path() -> Path:
    return get_settings_dir() / "settings.json"


def _load() -> dict[str, object]:
    try:
        return dict(json.loads(_settings_path().read_text(encoding="utf-8")))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(data: dict[str, object]) -> None:
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_language() -> str:
    """Return the configured UI language code ("pl" or "en"). Default: "pl"."""
    return str(_load().get("language", "pl"))


def set_language(lang: str) -> None:
    """Persist the UI language code."""
    data = _load()
    data["language"] = lang
    _save(data)
