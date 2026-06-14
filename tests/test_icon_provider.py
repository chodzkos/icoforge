"""Tests for recolourable SVG icons."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from icoforge.gui import icons
from icoforge.utils.paths import get_resource_path


@pytest.fixture(autouse=True)
def reset_icon_provider() -> None:
    icons.clear_cache()
    icons.set_color_resolver(lambda _token: "#dde1ec")
    yield
    icons.clear_cache()
    icons.set_color_resolver(None)


@pytest.mark.gui
def test_get_icon_returns_non_null_qicon(qapp: QApplication) -> None:
    icon = icons.get_icon("pencil")

    assert not icon.isNull()


@pytest.mark.gui
def test_get_icon_unknown_name_returns_empty_qicon(qapp: QApplication) -> None:
    icon = icons.get_icon("nieistnieje")

    assert icon.isNull()


@pytest.mark.gui
def test_clear_cache_empties_rendered_icon_cache(qapp: QApplication) -> None:
    icons.get_icon("pencil")
    assert icons._cache

    icons.clear_cache()

    assert not icons._cache


def test_recolored_svg_uses_current_theme_hex() -> None:
    dark_svg = icons._load_recolored_svg("pencil", "#dde1ec")
    light_svg = icons._load_recolored_svg("pencil", "#1d1d1f")

    assert dark_svg is not None
    assert light_svg is not None
    assert dark_svg != light_svg
    assert "#dde1ec" in dark_svg
    assert "#1d1d1f" in light_svg


def test_icon_assets_exist_for_every_mapped_action() -> None:
    missing = [
        svg_file
        for svg_file in icons.ICON_MAP.values()
        if not get_resource_path(f"assets/icons/{svg_file}").is_file()
    ]

    assert missing == []
