"""Frozen same-origin presentation; static files live outside _internal."""
import multiprocessing


def main():
    from aster_release.shutdown import serve
    from frontend.webserver import app
    serve(app, 8501)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
