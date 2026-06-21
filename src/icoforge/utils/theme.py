"""Zarządzanie motywem dark/light — silnik z chodzkos-gui-kit (brand-Fusion).

Wygląd liczy wspólny kit: ``chodzkos_gui_kit.qt.theme.apply_theme`` (styl Fusion +
paleta marki + QSS na akcenty + repaint item-views). Zastąpił qdarktheme (dark)
oraz natywny restore (light) — od teraz oba motywy to brand-Fusion.

``ThemeManager`` zachowuje publiczne API i sygnał ``theme_changed("dark"|"light")``
(slots w całym GUI łączą się ze stringiem, nie z paletą). Tryb i jego trwałość:
``utils/settings`` (klucz ``"theme"``, string-only).

Singleton modułowy — widgety/dialogi łączą się bez przeciągania managera przez
każdy konstruktor.

Usage (startup)::

    from icoforge.utils.theme import init_theme_manager
    mgr = init_theme_manager(app)
    mgr.restore()                   # stosuje zapisany lub auto motyw

Usage (anywhere after init)::

    from icoforge.utils.theme import get_theme_manager
    mgr = get_theme_manager()       # może być None w testach jednostkowych
"""

from __future__ import annotations

from chodzkos_gui_kit.palette import DARK, LIGHT
from chodzkos_gui_kit.qt import icons as icon_provider
from chodzkos_gui_kit.qt.theme import apply_theme
from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import QApplication

from icoforge.utils.settings import get_setting, save_setting

THEMES: tuple[str, ...] = ("auto", "dark", "light")

_instance: ThemeManager | None = None


class ThemeManager(QObject):
    """Stosuje i persystuje kolorystyczny motyw aplikacji.

    Emituje ``theme_changed("dark" | "light")`` przy każdej zmianie rozwiązanego
    motywu, żeby widgety mogły odświeżyć kolory bez pollingu.
    """

    theme_changed = Signal(str)  # emituje rozwiązaną wartość "dark" / "light"

    def __init__(self, app: QApplication) -> None:
        super().__init__()
        self._app = app

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def apply(self, theme: str = "auto") -> None:
        """Stosuje *theme* i zapisuje wybór.

        Args:
            theme: ``"auto"``, ``"dark"`` albo ``"light"``. ``"auto"`` podąża za
                preferencją kolorów systemu.
        """
        if theme not in THEMES:
            theme = "auto"
        save_setting("theme", theme)
        resolved = self._resolve(theme)
        self._apply_resolved(resolved)
        self.theme_changed.emit(resolved)

    def restore(self) -> None:
        """Wczytuje zapisany motyw i stosuje go (wołane przy starcie)."""
        saved = get_setting("theme", default="auto")
        if saved not in THEMES:
            saved = "auto"
        self._apply_resolved(self._resolve(saved))

    def current_resolved(self) -> str:
        """Zwraca aktywny motyw: ``"dark"`` albo ``"light"``."""
        return self._resolve(get_setting("theme", default="auto"))

    def current_setting(self) -> str:
        """Zwraca zapisaną preferencję: ``"auto"``, ``"dark"`` albo ``"light"``."""
        saved = get_setting("theme", default="auto")
        return saved if saved in THEMES else "auto"

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _resolve(self, theme: str) -> str:
        """Rozwiązuje ustawienie na ``"dark"`` albo ``"light"``."""
        if theme == "dark":
            return "dark"
        if theme == "light":
            return "light"
        # "auto": zapytaj Qt o preferencję systemu (Qt 6.5+)
        scheme = self._app.styleHints().colorScheme()
        return "dark" if scheme == Qt.ColorScheme.Dark else "light"

    def _apply_resolved(self, resolved: str) -> None:
        """Stosuje motyw przez kit (Fusion + paleta marki + QSS + repaint item-views).

        ``apply_theme`` ustawia też bieżącą paletę kitu, więc ikony tylko czyścimy
        z cache — widgety przerysują je w slocie ``theme_changed`` (np.
        ``EditorWindow._refresh_icons``).
        """
        apply_theme(self._app, DARK if resolved == "dark" else LIGHT)
        icon_provider.clear_cache()


# ---------------------------------------------------------------------------
# Module-level singleton helpers
# ---------------------------------------------------------------------------


def init_theme_manager(app: QApplication) -> ThemeManager:
    """Tworzy singleton ThemeManager. Wywołaj raz przy starcie."""
    global _instance
    _instance = ThemeManager(app)
    return _instance


def get_theme_manager() -> ThemeManager | None:
    """Zwraca singleton ThemeManager albo ``None`` (przed inicjalizacją)."""
    return _instance
