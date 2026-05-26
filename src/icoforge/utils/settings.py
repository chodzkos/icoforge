"""Application settings (persistent key-value store)."""

from __future__ import annotations

import json
from pathlib import Path

_SETTINGS_PATH = Path.home() / ".config" / "icoforge" / "settings.json"


def _load() -> dict[str, object]:
    try:
        return dict(json.loads(_SETTINGS_PATH.read_text(encoding="utf-8")))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(data: dict[str, object]) -> None:
    _SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _SETTINGS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_language() -> str:
    """Return the configured UI language code ("pl" or "en"). Default: "pl"."""
    return str(_load().get("language", "pl"))


def set_language(lang: str) -> None:
    """Persist the UI language code."""
    data = _load()
    data["language"] = lang
    _save(data)
