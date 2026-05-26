"""PyInstaller runtime hook: register the bundle dir as a Windows DLL search path.

cairocffi uses ctypes.CDLL to load libcairo-2.dll at import time.  In a frozen
onedir build all DLLs live in sys._MEIPASS (_internal/).  Python 3.8+ on Windows
no longer searches that directory automatically - os.add_dll_directory() is
required to make ctypes.util.find_library() / LoadLibrary find them.
"""

import os
import sys

if sys.platform == "win32" and hasattr(sys, "_MEIPASS"):
    os.add_dll_directory(sys._MEIPASS)
