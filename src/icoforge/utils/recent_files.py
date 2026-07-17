"""Recent files persistence (last 10 opened/saved files) — shared app Config."""

from __future__ import annotations

from pathlib import Path

from icoforge.utils.settings import get_config

MAX_RECENT = 10
_KEY = "recent_files"


def load_recent() -> list[Path]:
    """Return stored recent file paths (may include non-existent files)."""
    raw = get_config().get(_KEY, [])
    if not isinstance(raw, list):
        return []
    return [Path(str(p)) for p in raw]


def save_recent(paths: list[Path]) -> None:
    """Persist the given list of recent file paths."""
    cfg = get_config()
    cfg[_KEY] = [str(p) for p in paths]
    cfg.save_now()


def add_recent(path: Path) -> list[Path]:
    """Prepend path, deduplicate, trim to MAX_RECENT. Returns the updated list."""
    existing = [p for p in load_recent() if p != path]
    updated = [path, *existing][:MAX_RECENT]
    save_recent(updated)
    return updated


def remove_missing(paths: list[Path]) -> list[Path]:
    """Return only paths that currently exist on disk."""
    return [p for p in paths if p.exists()]
