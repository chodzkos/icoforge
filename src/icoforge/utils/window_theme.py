"""Windows DWM titlebar colour helper.

On Windows 10 (build 2004+) and Windows 11, the DWM can be told to render
the non-client titlebar in dark or light style independently of the system
colour scheme.  This lets the app match its titlebar to the in-app theme
even when the OS is set to light mode.

On every other platform the public function is a no-op.
"""

from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QWidget

logger = logging.getLogger(__name__)

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
        logger.debug("set_titlebar_dark: no-op (not win32)")
        return
    try:
        import ctypes
        import platform
        from ctypes import wintypes

        raw_id = int(window.winId())
        logger.info(
            "set_titlebar_dark: dark=%s  winId=%d  window=%s  Windows=%s",
            dark,
            raw_id,
            type(window).__name__,
            platform.version(),
        )

        if raw_id == 0:
            logger.warning("set_titlebar_dark: winId() == 0 — window has no native handle yet")
            return

        # IMPORTANT: wrap the handle in wintypes.HWND (pointer-sized). Passing a
        # plain Python int lets ctypes marshal it as a 32-bit C int, which
        # TRUNCATES the 64-bit HWND on 64-bit Windows so DwmSetWindowAttribute
        # receives an invalid handle and silently fails.
        hwnd = wintypes.HWND(raw_id)
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
        hr20 = dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(value), ctypes.sizeof(value))
        logger.info(
            "  DwmSetWindowAttribute(attr=20) -> HRESULT=0x%08X (%s)",
            hr20,
            "OK" if hr20 == 0 else "FAIL",
        )

        if hr20 != 0:
            # Fallback: attribute 19 was used in pre-release builds of 20H1
            hr19 = dwm.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(value), ctypes.sizeof(value))
            logger.info(
                "  DwmSetWindowAttribute(attr=19) -> HRESULT=0x%08X (%s)",
                hr19,
                "OK" if hr19 == 0 else "FAIL",
            )

        user32 = ctypes.windll.user32

        # Step 1: SetWindowPos with SWP_FRAMECHANGED — signals a frame-metrics
        # change to the DWM so it updates the DWMWA attribute we just set.
        user32.SetWindowPos.argtypes = [
            wintypes.HWND,
            wintypes.HWND,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.UINT,
        ]
        swp_result = user32.SetWindowPos(
            hwnd,
            None,
            0,
            0,
            0,
            0,
            _SWP_NOSIZE | _SWP_NOMOVE | _SWP_NOZORDER | _SWP_NOACTIVATE | _SWP_FRAMECHANGED,
        )
        logger.info("  SetWindowPos(SWP_FRAMECHANGED) -> %s", "OK" if swp_result else "FAIL")

        # Wymuś przemalowanie paska - fix dla Windows 10:
        # 1. WM_NCACTIVATE: rozwiązuje problem braku odświeżenia przy
        #    przełączeniu dark→light (pasek zostawał ciemny)
        # 2. RedrawWindow: niweluje jasne tło pod tekstem tytułu okna
        #    (artefakt Windows 10 przy DWMWA_USE_IMMERSIVE_DARK_MODE)
        WM_NCACTIVATE = 0x0086
        RDW_FRAME = 0x0400
        RDW_INVALIDATE = 0x0001
        RDW_UPDATENOW = 0x0100
        RDW_NOCHILDREN = 0x0040

        user32.SendMessageW.argtypes = [
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        ]
        user32.SendMessageW.restype = wintypes.LPARAM
        user32.SendMessageW(hwnd, WM_NCACTIVATE, 0, 0)
        user32.SendMessageW(hwnd, WM_NCACTIVATE, 1, 0)
        logger.info("  WM_NCACTIVATE -> OK")

        user32.RedrawWindow.argtypes = [
            wintypes.HWND,
            ctypes.c_void_p,
            ctypes.c_void_p,
            wintypes.UINT,
        ]
        user32.RedrawWindow.restype = wintypes.BOOL
        user32.RedrawWindow(
            hwnd, None, None, RDW_FRAME | RDW_INVALIDATE | RDW_UPDATENOW | RDW_NOCHILDREN
        )
        logger.info("  RedrawWindow(RDW_FRAME) -> OK")

    except Exception as exc:
        logger.exception("set_titlebar_dark FAILED with exception: %s", exc)
