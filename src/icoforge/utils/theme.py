"""Dark/light theme management.

Uses the qdarktheme library (PyPI: pyqtdarktheme) for stylesheet + palette.
Provides a module-level singleton so canvas widgets can connect without
having to thread the manager through every constructor call.

Usage (startup)::

    from icoforge.utils.theme import init_theme_manager
    mgr = init_theme_manager(app)   # creates singleton
    mgr.restore()                   # applies saved or auto theme

Usage (anywhere after init)::

    from icoforge.utils.theme import get_theme_manager
    mgr = get_theme_manager()       # may be None in unit tests
"""

from __future__ import annotations

import qdarktheme
from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import QApplication

from icoforge.utils.settings import get_setting, save_setting

THEMES: tuple[str, ...] = ("auto", "dark", "light")

_instance: ThemeManager | None = None


class ThemeManager(QObject):
    """Applies and persists the application colour theme.

    Emits ``theme_changed("dark" | "light")`` whenever the active resolved
    theme changes so widgets can update colours without polling.
    """

    theme_changed = Signal(str)  # emits the resolved "dark" or "light" value

    def __init__(self, app: QApplication) -> None:
        super().__init__()
        self._app = app

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def apply(self, theme: str = "auto") -> None:
        """Apply *theme* and persist the choice.

        Args:
            theme: One of ``"auto"``, ``"dark"``, or ``"light"``.
                ``"auto"`` follows the OS colour-scheme preference.
        """
        if theme not in THEMES:
            theme = "auto"
        save_setting("theme", theme)
        resolved = self._resolve(theme)
        self._apply_resolved(resolved)
        self.theme_changed.emit(resolved)

    def restore(self) -> None:
        """Load the saved theme preference and apply it (called at startup)."""
        saved = get_setting("theme", default="auto")
        if saved not in THEMES:
            saved = "auto"
        self._apply_resolved(self._resolve(saved))

    def current_resolved(self) -> str:
        """Return the currently active theme: ``"dark"`` or ``"light"``."""
        return self._resolve(get_setting("theme", default="auto"))

    def current_setting(self) -> str:
        """Return the stored preference: ``"auto"``, ``"dark"``, or ``"light"``."""
        saved = get_setting("theme", default="auto")
        return saved if saved in THEMES else "auto"

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _resolve(self, theme: str) -> str:
        """Resolve a setting string to ``"dark"`` or ``"light"``."""
        if theme == "dark":
            return "dark"
        if theme == "light":
            return "light"
        # "auto": ask Qt what the OS preference is (Qt 6.5+)
        scheme = self._app.styleHints().colorScheme()
        return "dark" if scheme == Qt.ColorScheme.Dark else "light"

    def _apply_resolved(self, resolved: str) -> None:
        self._app.setStyleSheet(qdarktheme.load_stylesheet(resolved))
        self._app.setPalette(qdarktheme.load_palette(resolved))


# ---------------------------------------------------------------------------
# Module-level singleton helpers
# ---------------------------------------------------------------------------


def init_theme_manager(app: QApplication) -> ThemeManager:
    """Create the module-level ThemeManager singleton. Call once at startup."""
    global _instance
    _instance = ThemeManager(app)
    return _instance


def get_theme_manager() -> ThemeManager | None:
    """Return the singleton ThemeManager, or *None* if not yet initialised."""
    return _instance
