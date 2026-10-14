import threading
from contextlib import contextmanager

from backend.app.errors import AppError


class ComputeGate:
    def __init__(self, settings):
        self.slot = threading.Semaphore(1)
        self.lock = threading.Lock()
        self.waiting = 0
        self.settings = settings

    @contextmanager
    def enter(self):
        acquired = self.slot.acquire(blocking=False)
        if not acquired:
            with self.lock:
                if self.waiting >= self.settings.max_queue_size:
                    raise AppError(429, "busy", "Local compute is busy. Try again shortly.")
                self.waiting += 1
            try:
                acquired = self.slot.acquire(timeout=self.settings.inference_timeout_seconds)
            finally:
                with self.lock:
                    self.waiting -= 1
            if not acquired:
                raise AppError(503, "busy", "Local compute queue timed out. Try again shortly.")
        try:
            yield
        finally:
            # Keep held until the synchronous worker truly exits.
            self.slot.release()
