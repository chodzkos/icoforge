"""Tests for recent_files persistence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from icoforge.utils.recent_files import (
    MAX_RECENT,
    add_recent,
    load_recent,
    remove_missing,
    save_recent,
)


@pytest.fixture(autouse=True)
def _isolated_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "icoforge.utils.recent_files._settings_path", lambda: tmp_path / "settings.json"
    )


def test_load_recent_empty() -> None:
    assert load_recent() == []


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    paths = [tmp_path / "a.png", tmp_path / "b.ico"]
    save_recent(paths)
    assert load_recent() == paths


def test_add_recent_prepends(tmp_path: Path) -> None:
    a = tmp_path / "a.png"
    b = tmp_path / "b.png"
    add_recent(a)
    result = add_recent(b)
    assert result[0] == b
    assert result[1] == a


def test_add_recent_deduplicates(tmp_path: Path) -> None:
    a = tmp_path / "a.png"
    add_recent(a)
    add_recent(a)
    assert load_recent().count(a) == 1


def test_add_recent_trims_to_max(tmp_path: Path) -> None:
    for i in range(MAX_RECENT + 5):
        add_recent(tmp_path / f"file_{i}.png")
    assert len(load_recent()) == MAX_RECENT


def test_remove_missing_filters_nonexistent(tmp_path: Path) -> None:
    real = tmp_path / "real.png"
    real.write_bytes(b"")
    ghost = tmp_path / "ghost.png"
    result = remove_missing([real, ghost])
    assert result == [real]


def test_load_recent_handles_corrupt_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings_file = tmp_path / "corrupt.json"
    settings_file.write_text("not json", encoding="utf-8")
    monkeypatch.setattr("icoforge.utils.recent_files._settings_path", lambda: settings_file)
    assert load_recent() == []


def test_add_recent_preserves_other_settings_keys(tmp_path: Path) -> None:
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(json.dumps({"language": "pl"}), encoding="utf-8")

    a = tmp_path / "a.png"
    add_recent(a)

    data = json.loads(settings_file.read_text(encoding="utf-8"))
    assert data.get("language") == "pl"
    assert "recent_files" in data
