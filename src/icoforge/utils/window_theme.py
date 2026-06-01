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

# SetWindowPos flags (winuser.h) used to force a non-client frame repaint.
_SWP_NOSIZE = 0x0001
_SWP_NOMOVE = 0x0002
_SWP_NOZORDER = 0x0004
_SWP_NOACTIVATE = 0x0010
_SWP_FRAMECHANGED = 0x0020


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
        from ctypes import wintypes

        # IMPORTANT: wrap the handle in wintypes.HWND (pointer-sized). Passing a
        # plain Python int lets ctypes marshal it as a 32-bit C int, which
        # TRUNCATES the 64-bit HWND on 64-bit Windows so DwmSetWindowAttribute
        # receives an invalid handle and silently fails — the classic cause of
        # "the titlebar never turns dark".
        hwnd = wintypes.HWND(int(window.winId()))
        value = ctypes.c_int(1 if dark else 0)

        dwm = ctypes.windll.dwmapi
        dwm.DwmSetWindowAttribute.argtypes = [
            wintypes.HWND,
            wintypes.DWORD,
            ctypes.c_void_p,
            wintypes.DWORD,
        ]
        dwm.DwmSetWindowAttribute.restype = ctypes.c_long

        # DWMWA_USE_IMMERSIVE_DARK_MODE = 20 (Windows 10 build 2004 / 20H1+)
        result = dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(value), ctypes.sizeof(value))
        if result != 0:
            # Fallback: attribute 19 was used in pre-release builds of 20H1
            dwm.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(value), ctypes.sizeof(value))

        # The DWM does not repaint the non-client frame of an already-visible
        # window until a frame change is signalled. Nudge it with SetWindowPos
        # (no move, no resize, no z-order change) so the new titlebar colour
        # shows immediately instead of only after the next move/resize.
        user32 = ctypes.windll.user32
        user32.SetWindowPos.argtypes = [
            wintypes.HWND,
            wintypes.HWND,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.UINT,
        ]
        user32.SetWindowPos(
            hwnd,
            None,
            0,
            0,
            0,
            0,
            _SWP_NOSIZE | _SWP_NOMOVE | _SWP_NOZORDER | _SWP_NOACTIVATE | _SWP_FRAMECHANGED,
        )
    except Exception:
        pass  # Wine, Windows 7, missing dwmapi — silently ignore
