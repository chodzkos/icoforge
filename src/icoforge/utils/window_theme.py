"""Pasek tytułu (DWM) dla custom-dialogów IcoForge — helper specyficzny dla appki.

File-pickery idą przez kitowe helpery ``chodzkos_gui_kit.qt.dialogs`` (one same
ustawiają belkę). Tu zostaje tylko ustawianie ciemnego/jasnego paska tytułu dla
WŁASNYCH dialogów aplikacji (Ustawienia, Pomoc, Presety, AI-installer…). Sam DWM
liczy wspólny kit — ``chodzkos_gui_kit.qt.titlebar.set_titlebar_dark`` (poprawny
marshaling 64-bit HWND + repaint ramki Win10). Poza Windows: no-op.

Motyw odczytujemy przez ``theme_manager.current_resolved()`` — kontrakt z shellem
``icoforge.utils.theme.ThemeManager`` (zwraca ``"dark"`` albo ``"light"``).
"""

from __future__ import annotations

import sys

from chodzkos_gui_kit.qt.titlebar import set_titlebar_dark
from PySide6.QtWidgets import QWidget


def apply_theme_to_dialog(dialog: QWidget, theme_manager: object) -> None:
    """Ustawia pasek tytułu *dialog* wg motywu, gdy tylko uchwyt istnieje.

    Bezpieczne przed ``show()``/``exec()``: gdy natywny uchwyt jeszcze nie
    istnieje, używamy zerowego timera, by DWM odpalił w pierwszym ticku pętli
    zdarzeń po pokazaniu dialogu. Poza Windows: no-op.

    Args:
        dialog: dialog (albo dowolny top-level ``QWidget``) do ostylowania.
        theme_manager: ThemeManager aplikacji; ``None`` jest bezpieczne.
    """
    if sys.platform != "win32" or theme_manager is None:
        return
    dark: bool = getattr(theme_manager, "current_resolved", lambda: "light")() == "dark"
    if int(dialog.winId()) != 0:
        set_titlebar_dark(dialog, dark)
    else:
        from PySide6.QtCore import QTimer

        QTimer.singleShot(0, lambda: set_titlebar_dark(dialog, dark))
