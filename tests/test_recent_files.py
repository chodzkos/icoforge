"""Tests for recent_files persistence."""

from __future__ import annotations

from pathlib import Path

import pytest
from chodzkos_gui_kit.config import Config

from icoforge.utils.recent_files import (
    MAX_RECENT,
    add_recent,
    load_recent,
    remove_missing,
    save_recent,
)


@pytest.fixture(autouse=True)
def _isolated_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Wstrzykuje współdzielony Config wskazujący plik w tmp — recent_files czyta go
    # przez utils.settings.get_config, więc to jedyny punkt izolacji.
    monkeypatch.setattr(
        "icoforge.utils.settings._config", Config("IcoForge", path=tmp_path / "config.json")
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
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text("not json", encoding="utf-8")
    # Kit Config zachowuje uszkodzony plik (.broken-<ts>) i startuje pusty → brak recent.
    monkeypatch.setattr("icoforge.utils.settings._config", Config("IcoForge", path=cfg_file))
    assert load_recent() == []


def test_add_recent_preserves_other_settings_keys(tmp_path: Path) -> None:
    # Klucz clobbera z audytu: recent i inne ustawienia dzielą jeden Config, więc
    # dopisanie recent nie kasuje języka (dawniej trzej niezależni pisarze mogli się nadpisać).
    from icoforge.utils.settings import get_config, set_language

    set_language("pl")
    add_recent(tmp_path / "a.png")

    cfg = get_config()
    assert cfg.get("language") == "pl"
    assert "recent_files" in cfg
