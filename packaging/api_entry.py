"""Frozen API: no `sys.executable -m` and no uvicorn import-string workers."""
import multiprocessing
import sys


def run_worker():
    """Isolated helper processes (PDF parsing/rasterising) re-enter the frozen exe."""
    name = sys.argv[2]
    sys.argv = [sys.argv[0], *sys.argv[3:]]
    if name == "pdf_text":
        from backend.app.services.pdf_worker import main as worker
    elif name == "pdf_raster":
        from backend.app.services.pdf_raster_worker import main as worker
    else:
        return 2
    return worker()


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--worker":
        sys.exit(run_worker())
    import os

    from aster_release.release import verify_package
    from aster_release.runtime import release_settings
    from aster_release.v2 import is_v2, release_settings_v2, verify_installed
    from backend.app.paths import install_root
    root = install_root()
    if is_v2(root):
        # The controller already verified; a fast self-check guards direct launches.
        result = verify_installed(root)
        profile = result["profile"]
        settings = release_settings_v2(root, profile, os.environ.get("ASTER_PROFILE") or result["manifest"]["profile"],
                                       writable=os.environ.get("ASTER_WRITABLE_ROOT") or root.parent.parent / "writable",
                                       api_port=os.environ.get("ASTER_API_PORT", "8000"),
                                       ollama_port=os.environ.get("ASTER_OLLAMA_PORT", "11435"))
        from aster_release.shutdown import serve
        from backend.app.main import create_app
        app = create_app(settings)
        app.state.release_info = {"app_version": profile["app_version"], "edition": profile["edition"],
                                  "features": profile["features"], "profile": result["manifest"]["profile"]}
        serve(app, int(os.environ.get("ASTER_API_PORT", "8000")))
        return
    result = verify_package(root)
    settings = release_settings(root, result["manifest"])
    if sys.argv[1:] == ["--check-encoder"]:
        # Exercise lazy imports in the actual frozen interpreter, entirely offline.
        import transformers.modeling_utils  # noqa: F401
        from sentence_transformers import SentenceTransformer
        encoder = SentenceTransformer(str(settings.embedding_path), local_files_only=True, device="cpu")
        vector = encoder.encode(["epithelium"], convert_to_numpy=True)
        if vector.shape != (1, 384):
            raise RuntimeError("Included encoder returned an incompatible vector")
        print("Offline frozen encoder check passed: 384 dimensions")
        return
    from aster_release.shutdown import serve
    from backend.app.main import create_app
    app = create_app(settings)
    app.state.release_info = {k: result["manifest"][k] for k in ("app_version", "edition", "data", "features", "model")}
    serve(app, 8000)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    from aster_release.entry_guard import guarded

    guarded(main, "api")
