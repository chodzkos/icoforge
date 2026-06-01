"""Windows DWM titlebar colour helper.

On Windows 10 (build 2004+) and Windows 11, the DWM can be told to render
the non-client titlebar in dark or light style independently of the system
colour scheme.  This lets the app match its titlebar to the in-app theme
even when the OS is set to light mode.

On every other platform the public function is a no-op.
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QWidget


def set_titlebar_dark(window: QWidget, dark: bool) -> None:
    """Apply dark or light titlebar styling to *window* on Windows.

    Must be called after the window has a valid native handle (i.e. after
    ``window.show()`` or inside ``showEvent``).  On non-Windows platforms
    this function does nothing.

    Args:
        window: The top-level window whose titlebar to style.
        dark: ``True`` for a dark titlebar, ``False`` for the native light
            titlebar.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes

        hwnd = int(window.winId())
        value = ctypes.c_int(1 if dark else 0)

        # DWMWA_USE_IMMERSIVE_DARK_MODE = 20 (Windows 10 build 2004 / 20H1+)
        result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 20, ctypes.byref(value), ctypes.sizeof(value)
        )
        if result != 0:
            # Fallback: attribute 19 was used in pre-release builds of 20H1
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 19, ctypes.byref(value), ctypes.sizeof(value)
            )
    except Exception:
        pass  # Wine, Windows 7, missing dwmapi — silently ignore
