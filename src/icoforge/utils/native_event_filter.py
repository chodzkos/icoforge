"""Windows native event filter that keeps the dark titlebar active-looking.

When a dialog opens, Windows sends WM_NCACTIVATE(wParam=0) to the main window
(deactivation), which triggers a non-client repaint in the default light
"inactive" style — ignoring our DWMWA_USE_IMMERSIVE_DARK_MODE attribute.

This filter intercepts that message and returns TRUE so Windows skips the
light-titlebar repaint and the bar stays dark.

On non-Windows platforms this module is a no-op.
"""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

from PySide6.QtCore import QAbstractNativeEventFilter, QByteArray

WM_NCACTIVATE = 0x0086


class _MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", wintypes.POINT),
    ]


class TitlebarEventFilter(QAbstractNativeEventFilter):
    """Intercepts WM_NCACTIVATE so the dark titlebar stays dark when inactive.

    Install once on the QApplication with ``app.installNativeEventFilter(f)``.
    Call :meth:`set_dark` whenever the application theme changes.
    """

    def __init__(self) -> None:
        super().__init__()
        self._dark: bool = False

    def set_dark(self, dark: bool) -> None:
        """Tell the filter whether dark mode is currently active."""
        self._dark = dark

    def nativeEventFilter(  # noqa: N802
        self,
        event_type: QByteArray | bytes | bytearray | memoryview[int],
        message: int,
    ) -> tuple[bool, int]:
        """Filter Windows messages.

        Returns ``(True, 1)`` for WM_NCACTIVATE(wParam=0) in dark mode so
        Windows skips painting the light "inactive" non-client area.
        """
        if not self._dark or sys.platform != "win32":
            return False, 0
        if event_type != b"windows_generic_MSG":
            return False, 0
        try:
            msg = ctypes.cast(message, ctypes.POINTER(_MSG)).contents
            if msg.message == WM_NCACTIVATE and msg.wParam == 0:
                return True, 1
        except Exception:
            pass
        return False, 0
