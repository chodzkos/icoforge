"""Zarządzanie motywem — kanoniczny ThemeManager z chodzkos-gui-kit.

IcoForge importuje kitowy ``ThemeManager`` (paleta marki + sekwencja ``apply``,
DWM belek przez ``attach_titlebar``, tryb auto przez ``colorScheme`` — kit sam
subskrybuje ``colorSchemeChanged``). Ten moduł trzyma tylko singleton modułowy
(widgety/dialogi łączą się bez przeciągania managera przez każdy konstruktor) i
wiąże czyszczenie cache przebarwialnych ikon z sygnałem motywu.

Kontrakt kitu (zmiana względem dawnego własnego managera):

* sygnał ``theme_changed(Palette)`` (nie ``str``) — sloty, które potrzebują tylko
  „przemaluj się", mogą argument zignorować;
* zmiana trybu: ``apply("auto" | "dark" | "light")``;
* aktualny tryb: property ``setting``; rozwiązany motyw: ``resolved_name()``;
* belka tytułu okna: ``attach_titlebar(window)`` (DWM = motyw app przy każdym apply).

Trwałość motywu: WSPÓLNY kitowy ``Config`` (``config.json``, klucz ``"theme"``) —
ta sama instancja, której używają ``utils/settings`` (język), ``recent_files`` i
``window_state`` (``utils.settings.get_config``).

Usage (startup)::

    from icoforge.utils.theme import init_theme_manager
    mgr = init_theme_manager(app)
    mgr.apply(mgr.setting)          # zastosuj zapisany (lub auto) motyw

Usage (anywhere after init)::

    from icoforge.utils.theme import get_theme_manager
    mgr = get_theme_manager()       # może być None w testach jednostkowych
"""

from __future__ import annotations

from chodzkos_gui_kit.qt import icons as icon_provider
from chodzkos_gui_kit.qt.theme import ThemeManager
from PySide6.QtWidgets import QApplication

from icoforge.utils.settings import get_config

__all__ = ["ThemeManager", "get_theme_manager", "init_theme_manager"]

_instance: ThemeManager | None = None


def init_theme_manager(app: QApplication) -> ThemeManager:
    """Tworzy singleton kitowego ThemeManager. Wywołaj raz przy starcie.

    Motyw persystuje we WSPÓLNYM ``Config`` aplikacji (ten sam, którego używają
    settings/recent/window_state) — klucz ``"theme"`` obok reszty ustawień.
    """
    global _instance
    config = get_config()
    mgr = ThemeManager(app, config)

    def _on_theme_changed(_palette: object) -> None:
        # Kit ThemeManager NIE czyści cache ikon — robi to konsument, żeby przebarwialne
        # SVG (get_icon) podążały za paletą. Podłączone PRZED utworzeniem okien, więc
        # clear_cache leci przed slotami re-setującymi ikony (EditorWindow._refresh_icons).
        icon_provider.clear_cache()
        # Kit ``apply()`` zapisuje wybór do Config (mark_dirty), ale NIE flushuje —
        # motyw zmienia się rzadko, więc utrwalamy od razu (inaczej ginie po restarcie).
        config.save_now()

    mgr.theme_changed.connect(_on_theme_changed)
    _instance = mgr
    return mgr


def get_theme_manager() -> ThemeManager | None:
    """Zwraca singleton ThemeManager albo ``None`` (przed inicjalizacją)."""
    return _instance
