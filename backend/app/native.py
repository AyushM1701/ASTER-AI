"""Keep PyInstaller's DLL search directory out of native OCR subprocesses."""
import os
import sys
import threading
from contextlib import contextmanager

_lock = threading.RLock()


@contextmanager
def native_subprocess():
    if os.name != "nt" or not getattr(sys, "frozen", False):
        yield
        return
    import ctypes
    with _lock:
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.SetDllDirectoryW.argtypes = [ctypes.c_wchar_p]
        kernel.SetDllDirectoryW(None)
        try:
            yield
        finally:
            kernel.SetDllDirectoryW(sys._MEIPASS)
