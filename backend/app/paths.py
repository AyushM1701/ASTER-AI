"""Separate external install assets from frozen Python resources."""
import os
import sys
from pathlib import Path


def install_root():
    explicit = os.environ.get("ASTER_INSTALL_ROOT")
    if explicit:
        path = Path(explicit)
        if not path.is_absolute():
            raise ValueError("ASTER_INSTALL_ROOT must be absolute")
        return path.resolve()
    if getattr(sys, "frozen", False):
        exe = Path(sys.executable).resolve()
        if exe.parent.parent.name == "bin":
            return exe.parent.parent.parent
        return exe.parent.parent if exe.parent.name == "bin" else exe.parent
    return Path(__file__).resolve().parents[2]


def resource_path(relative):
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / relative
    return install_root() / relative
