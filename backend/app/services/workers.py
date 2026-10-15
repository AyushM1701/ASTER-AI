"""Launch isolated helper processes in source and frozen (PyInstaller) builds.

Source: ``python -I <module file> args``. Frozen: ``aster-api.exe --worker <name> args``
(handled in ``packaging/api_entry.py``). Children get no window and a minimal
environment; callers enforce timeouts and output bounds.
"""
import os
import subprocess
import sys
from pathlib import Path

WORKERS = {"pdf_text": "pdf_worker.py", "pdf_raster": "pdf_raster_worker.py"}


def command(name, *args):
    if name not in WORKERS:
        raise ValueError("unknown worker")
    if getattr(sys, "frozen", False):
        return [sys.executable, "--worker", name, *map(str, args)]
    return [sys.executable, "-I", str(Path(__file__).with_name(WORKERS[name])), *map(str, args)]


def run(name, data, *args, timeout=20, max_output=60_000_000):
    environment = {key: os.environ[key] for key in ("SYSTEMROOT", "TEMP", "TMP", "PATH") if key in os.environ}
    root = Path(__file__).resolve().parents[3]
    if not getattr(sys, "frozen", False):
        environment["PYTHONPATH"] = str(root)
    result = subprocess.run(command(name, *args), input=data, capture_output=True, timeout=timeout, check=False,
                            env=environment, cwd=str(root),
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0)
    if len(result.stdout) > max_output:
        raise ValueError("worker output too large")
    return result.returncode, result.stdout, result.stderr[:200].decode("ascii", "replace")
