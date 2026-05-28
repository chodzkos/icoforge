"""Tests for window_state persistence."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from icoforge.utils.window_state import (
    _is_position_visible,
    restore_window_state,
    save_window_state,
)


@pytest.fixture(autouse=True)
def _isolated_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "icoforge.utils.window_state._settings_path", lambda: tmp_path / "settings.json"
    )


def _make_window(x: int = 100, y: int = 100, w: int = 900, h: int = 600) -> MagicMock:
    window = MagicMock()
    geo = MagicMock()
    geo.x.return_value = x
    geo.y.return_value = y
    geo.width.return_value = w
    geo.height.return_value = h
    window.geometry.return_value = geo
    return window


def test_save_window_state_writes_json(tmp_path: Path) -> None:
    window = _make_window(50, 80, 1024, 768)
    save_window_state(window)  # type: ignore[arg-type]

    data = json.loads((tmp_path / "settings.json").read_text(encoding="utf-8"))
    state = data["window_state"]
    assert state == {"x": 50, "y": 80, "width": 1024, "height": 768}


def test_save_preserves_other_keys(tmp_path: Path) -> None:
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(json.dumps({"language": "en"}), encoding="utf-8")

    save_window_state(_make_window())  # type: ignore[arg-type]

    data = json.loads(settings_file.read_text(encoding="utf-8"))
    assert data["language"] == "en"
    assert "window_state" in data


def test_restore_calls_set_geometry_when_visible(tmp_path: Path) -> None:
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(
        json.dumps({"window_state": {"x": 100, "y": 100, "width": 900, "height": 600}}),
        encoding="utf-8",
    )
    window = _make_window()

    with patch("icoforge.utils.window_state._is_position_visible", return_value=True):
        restore_window_state(window)  # type: ignore[arg-type]

    window.setGeometry.assert_called_once_with(100, 100, 900, 600)


def test_restore_uses_resize_when_off_screen(tmp_path: Path) -> None:
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(
        json.dumps({"window_state": {"x": -9999, "y": -9999, "width": 900, "height": 600}}),
        encoding="utf-8",
    )
    window = _make_window()

    with patch("icoforge.utils.window_state._is_position_visible", return_value=False):
        restore_window_state(window)  # type: ignore[arg-type]

    window.setGeometry.assert_not_called()
    window.resize.assert_called_once_with(900, 600)


def test_restore_enforces_minimum_size(tmp_path: Path) -> None:
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(
        json.dumps({"window_state": {"x": 100, "y": 100, "width": 200, "height": 100}}),
        encoding="utf-8",
    )
    window = _make_window()

    with patch("icoforge.utils.window_state._is_position_visible", return_value=True):
        restore_window_state(window)  # type: ignore[arg-type]

    window.setGeometry.assert_called_once_with(100, 100, 700, 500)


def test_restore_no_op_when_no_settings(tmp_path: Path) -> None:
    window = _make_window()
    restore_window_state(window)  # type: ignore[arg-type]
    window.setGeometry.assert_not_called()
    window.resize.assert_not_called()


def test_is_position_visible_returns_false_without_running_app() -> None:
    # No QApplication is running in this test process, so should return False.
    assert _is_position_visible(0, 0, 800, 600) is False
