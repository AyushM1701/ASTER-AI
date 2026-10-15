"""Shared paths, logging and provider registry (kept out of ``build`` so that
``python -m aster_library.build`` does not create a second registry copy)."""
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "data" / "library-work"
PROVIDERS = {}


def log(message):
    print(time.strftime("%H:%M:%S"), message, flush=True)


def register(name):
    def wrap(fn):
        PROVIDERS[name] = fn
        return fn
    return wrap
