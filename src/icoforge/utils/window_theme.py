"""Pasek tytułu (DWM) dla custom-dialogów IcoForge — kitowy TitlebarSync.

File-pickery idą przez kitowe helpery ``chodzkos_gui_kit.qt.dialogs`` (one same
ustawiają belkę). Tu zostaje tylko ustawianie ciemnego/jasnego paska tytułu dla
WŁASNYCH dialogów aplikacji (Ustawienia, Presety, AI-installer, „O programie"…).

Belkę utrzymuje kitowy :class:`TitlebarSync` — filtr zdarzeń, dziecko dialogu,
który re-aplikuje DWM przy ``Show`` (pierwszy poprawny ``winId``) i
``ActivationChange``. Zastępuje dawny ``set_titlebar_dark`` + ``QTimer.singleShot``.
Motyw czytany leniwie z bieżącej palety kitu (``current_palette``), więc helper
nie potrzebuje ``ThemeManager``. Poza Windows DWM jest no-opem.

Okna długo żyjące (główne, edytor) NIE używają tego helpera — dołączają belkę raz
przez ``ThemeManager.attach_titlebar(window)`` (kit re-aplikuje DWM przy każdym
``apply()``, także gdy motyw zmienia się przy otwartym oknie).
"""

from __future__ import annotations

from chodzkos_gui_kit.qt.theme import current_palette, mode_of
from chodzkos_gui_kit.qt.titlebar import TitlebarSync
from PySide6.QtWidgets import QWidget


def apply_theme_to_dialog(dialog: QWidget, theme_manager: object = None) -> None:
    """Dołącza belkę tytułu *dialog* do bieżącego motywu (idempotentnie).

    Instaluje kitowy :class:`TitlebarSync` jako dziecko dialogu przy pierwszym
    wywołaniu i odświeża go przy kolejnych (bez dublowania filtrów). Bezpieczne
    przed ``show()``/``exec()`` — ``TitlebarSync`` re-aplikuje DWM na ``Show``.

    Args:
        dialog: dialog (albo dowolny top-level ``QWidget``) do ostylowania.
        theme_manager: ignorowany (zgodność wsteczna wywołań); motyw czytany
            leniwie z ``current_palette``.
    """
    existing = dialog.findChild(TitlebarSync)
    if existing is not None:
        existing.refresh()
        return
    TitlebarSync(dialog, lambda: mode_of(current_palette())).refresh()
