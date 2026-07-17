"""Application settings — jeden współdzielony kitowy Config (``config.json``).

Cały stan aplikacji (motyw, język, ostatnio otwarte, geometria okna) trzyma JEDNA
instancja :class:`chodzkos_gui_kit.config.Config`. Wspólny słownik w pamięci +
atomowy zapis kitu eliminują dawny wyścig trzech niezależnych pisarzy o ten sam
``settings.json`` (settings/recent/window_state pisały osobno przez read-modify-write).

Zapis jest natychmiastowy (``save_now``) — ustawienia zmieniają się rzadko, a kit
i tak pisze atomowo (tmp + ``os.replace``) i zachowuje uszkodzony plik jako
``config.json.broken-<ts>``.
"""

from __future__ import annotations

from chodzkos_gui_kit.config import Config

from icoforge.utils.paths import APP_NAME

_config: Config | None = None


def get_config() -> Config:
    """Zwraca współdzieloną instancję ``Config`` aplikacji (leniwie, singleton).

    Wszystkie moduły ustawień (settings/recent/window_state) oraz ``ThemeManager``
    (motyw) używają TEJ SAMEJ instancji — inaczej wracałby wyścig o ``config.json``.
    """
    global _config
    if _config is None:
        _config = Config(APP_NAME)
    return _config


def get_setting(key: str, default: str = "") -> str:
    """Return a string setting value, falling back to *default* if absent."""
    return str(get_config().get(key, default))


def save_setting(key: str, value: str) -> None:
    """Persist a single string setting (shared config, atomic write)."""
    cfg = get_config()
    cfg[key] = value
    cfg.save_now()


def get_language() -> str:
    """Return the configured UI language code ("pl" or "en"). Default: "pl"."""
    return str(get_config().get("language", "pl"))


def set_language(lang: str) -> None:
    """Persist the UI language code."""
    cfg = get_config()
    cfg["language"] = lang
    cfg.save_now()
