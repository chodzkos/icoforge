"""Dark/light theme management.

The dark theme uses the qdarktheme library (PyPI: pyqtdarktheme). The light
theme deliberately restores the *native* Qt appearance captured at startup
rather than applying qdarktheme's flat light theme, so the light mode looks
identical to the application as it was before themes were introduced.

Provides a module-level singleton so canvas widgets can connect without
having to thread the manager through every constructor call.

Usage (startup)::

    from icoforge.utils.theme import init_theme_manager
    mgr = init_theme_manager(app)   # captures native look, creates singleton
    mgr.restore()                   # applies saved or auto theme

Usage (anywhere after init)::

    from icoforge.utils.theme import get_theme_manager
    mgr = get_theme_manager()       # may be None in unit tests
"""

from __future__ import annotations

import qdarktheme
from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication

from icoforge.utils.settings import get_setting, save_setting

THEMES: tuple[str, ...] = ("auto", "dark", "light")

_instance: ThemeManager | None = None


class ThemeManager(QObject):
    """Applies and persists the application colour theme.

    Emits ``theme_changed("dark" | "light")`` whenever the active resolved
    theme changes so widgets can update colours without polling.

    The native Qt style, palette and (empty) app-level stylesheet are captured
    in ``__init__`` *before* any qdarktheme call, so the light theme can restore
    the original appearance exactly.
    """

    theme_changed = Signal(str)  # emits the resolved "dark" or "light" value

    def __init__(self, app: QApplication) -> None:
        super().__init__()
        self._app = app
        # Capture the pristine native appearance before qdarktheme touches it.
        # Copy the palette — app.palette() returns a value that we must not alias.
        self._default_style = app.style().objectName()
        self._default_palette = QPalette(app.palette())
        self._default_stylesheet = app.styleSheet()

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
        if resolved == "dark":
            self._app.setStyleSheet(qdarktheme.load_stylesheet("dark"))
            self._app.setPalette(qdarktheme.load_palette("dark"))
        else:
            self._apply_native_light()
        self._force_refresh()

    def _apply_native_light(self) -> None:
        """Restore the original native Qt appearance (pre-qdarktheme state)."""
        # Clear the stylesheet qdarktheme may have applied (restore the original).
        self._app.setStyleSheet(self._default_stylesheet)
        # Restore the native style object and palette captured at startup.
        self._app.setStyle(self._default_style)
        self._app.setPalette(self._default_palette)

    def _force_refresh(self) -> None:
        """Force a full style repolish on every widget in the application.

        After a palette or stylesheet change Qt does not always propagate the
        new appearance to every child widget (QTableWidget viewport, items
        inside QScrollArea, etc.), leaving stale dark or light backgrounds.
        Calling unpolish + polish + update on each widget flushes those caches.
        """
        style = self._app.style()
        for widget in self._app.allWidgets():
            style.unpolish(widget)
            style.polish(widget)
            widget.update()


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
