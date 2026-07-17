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

Trwałość motywu: kitowy ``Config`` (``config.json``, klucz ``"theme"``). Reszta
ustawień aplikacji (język, recent, geometria okna) zostaje na razie w
``utils/settings`` — pełna migracja na ``Config`` to osobny krok (#12 audytu).

Usage (startup)::

    from icoforge.utils.theme import init_theme_manager
    mgr = init_theme_manager(app)
    mgr.apply(mgr.setting)          # zastosuj zapisany (lub auto) motyw

Usage (anywhere after init)::

    from icoforge.utils.theme import get_theme_manager
    mgr = get_theme_manager()       # może być None w testach jednostkowych
"""

from __future__ import annotations

from chodzkos_gui_kit.config import Config
from chodzkos_gui_kit.qt import icons as icon_provider
from chodzkos_gui_kit.qt.theme import ThemeManager
from PySide6.QtWidgets import QApplication

__all__ = ["ThemeManager", "get_theme_manager", "init_theme_manager"]

_APP_NAME = "IcoForge"

_instance: ThemeManager | None = None


def init_theme_manager(app: QApplication) -> ThemeManager:
    """Tworzy singleton kitowego ThemeManager. Wywołaj raz przy starcie.

    Kitowy ``Config`` (``config.json``) niesie na razie tylko klucz motywu —
    pozostałe ustawienia zostają w ``utils/settings`` do czasu pełnej migracji.
    """
    global _instance
    config = Config(_APP_NAME)
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
