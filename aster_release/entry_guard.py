"""Startup guard for windowed frozen services."""
import sys


def guarded(entry, name):
    """Windowed builds would show a hidden error dialog and hang; log and exit instead.

    Startup tracebacks contain code paths only, never questions or uploads."""
    import os
    import traceback
    from pathlib import Path

    try:
        entry()
    except SystemExit:
        raise
    except BaseException:
        root = Path(os.environ.get("ASTER_WRITABLE_ROOT") or Path.home() / "AppData/Local/Aster")
        try:
            (root / "logs").mkdir(parents=True, exist_ok=True)
            (root / "logs" / f"{name}-startup-error.log").write_text(traceback.format_exc(), encoding="utf-8")
        except OSError:
            pass
        sys.exit(3)
