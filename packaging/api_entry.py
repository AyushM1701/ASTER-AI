"""Frozen API: no `sys.executable -m` and no uvicorn import-string workers."""
import multiprocessing
import sys


def main():
    from aster_release.release import verify_package
    from aster_release.runtime import release_settings
    from backend.app.paths import install_root
    root = install_root()
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
    main()
