"""Frozen same-origin presentation; static files live outside _internal."""
import multiprocessing


def main():
    import os

    from aster_release.shutdown import serve
    from frontend.webserver import app
    serve(app, int(os.environ.get("ASTER_WEB_PORT", "8501")))


if __name__ == "__main__":
    multiprocessing.freeze_support()
    from aster_release.entry_guard import guarded

    guarded(main, "web")
