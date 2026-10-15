"""Named local event for graceful uvicorn shutdown before Job Object teardown."""
import ctypes
import os
import threading
import uuid
from ctypes import wintypes


class ShutdownEvent:
    def __init__(self, name=None):
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel.CreateEventW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
        self.kernel.CreateEventW.restype = wintypes.HANDLE
        self.kernel.SetEvent.argtypes = [wintypes.HANDLE]
        self.kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self.name = name or "Local\\Aster-" + uuid.uuid4().hex
        self.handle = self.kernel.CreateEventW(None, True, False, self.name)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())

    def signal(self):
        self.kernel.SetEvent(self.handle)

    def wait(self):
        self.kernel.WaitForSingleObject(self.handle, 0xFFFFFFFF)

    def close(self):
        self.kernel.CloseHandle(self.handle)


def serve(app, port):
    import sys

    import uvicorn
    # Windowed (no-console) builds have no standard streams; uvicorn's default
    # console logging would crash. Use null streams and no console log config.
    windowed = sys.stdout is None or sys.stderr is None
    if windowed:
        sys.stdout = sys.stderr = open(os.devnull, "w", encoding="utf-8")
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, workers=1, access_log=False, log_level="warning",
                                           log_config=None if windowed else uvicorn.config.LOGGING_CONFIG))
    name = os.environ.get("ASTER_STOP_EVENT")
    if name and os.name == "nt":
        event = ShutdownEvent(name)
        def stop():
            event.wait()
            server.should_exit = True
            event.close()
        threading.Thread(target=stop, daemon=True).start()
    server.run()
