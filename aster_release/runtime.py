"""Hermetic process settings for the verified release, never workstation .env."""
import os
import shutil
import tempfile
from pathlib import Path

from aster_release.release import ReleaseError, contained

PATH_FIELDS = {
    "corpus_path", "source_register", "chroma_path", "embedding_path",
    "teaching_release_path", "teaching_index_path", "teaching_explanations_path",
    "secondary_reference_path", "xray_manifest", "xray_weights_manifest",
}


def native_ascii_path(path):
    """The pinned Windows Tesseract build rejects non-ASCII filesystem paths."""
    path = Path(path).resolve()
    if os.name != "nt" or str(path).isascii():
        return str(path)
    import ctypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    get_short = kernel.GetShortPathNameW
    get_short.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32]
    get_short.restype = ctypes.c_uint32
    buffer = ctypes.create_unicode_buffer(32768)
    length = get_short(str(path), buffer, len(buffer))
    if (not length or length >= len(buffer) or not buffer.value.isascii()
            or Path(buffer.value).resolve() != path):
        raise ReleaseError("The included OCR runtime needs an ASCII-compatible path. "
                           "Windows short names are unavailable here; move the installation "
                           "to an ASCII path. For cache paths, launch with --writable "
                           "and an ASCII writable directory outside the installation.")
    return buffer.value


def ascii_tessdata(source):
    """Tesseract's Windows build cannot open non-ASCII data paths.

    Prefer the 8.3 short-name alias; if the volume has short names disabled, keep a
    verified copy of the (non-sensitive) language files in an ASCII public folder."""
    import hashlib

    try:
        return native_ascii_path(source)
    except ReleaseError:
        pass
    source = Path(source)
    files = sorted(p for p in source.iterdir() if p.is_file())
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.name.encode() + hashlib.sha256(path.read_bytes()).digest())
    public = Path(os.environ.get("PUBLIC") or "C:/Users/Public")
    target = public / "Aster" / ("tessdata-" + digest.hexdigest()[:16])
    if not str(target).isascii():
        raise ReleaseError("No ASCII folder is available for the text reader's language data. Install Aster in a folder "
                           "whose path uses only English letters.")
    if not all((target / p.name).is_file() and (target / p.name).stat().st_size == p.stat().st_size for p in files):
        staging = target.with_name(target.name + ".tmp")
        shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir(parents=True)
        for path in files:
            shutil.copy2(path, staging / path.name)
        shutil.rmtree(target, ignore_errors=True)
        os.replace(staging, target)
    for path in files:
        if hashlib.sha256((target / path.name).read_bytes()).hexdigest() != hashlib.sha256(path.read_bytes()).hexdigest():
            raise ReleaseError("The text reader's language data could not be prepared. Choose Repair Aster.")
    return str(target)


def sanitized_environment(root, writable):
    # Allowlist OS essentials rather than trying to enumerate every risky knob.
    allowed = {"SYSTEMROOT", "WINDIR", "COMSPEC", "TEMP", "TMP", "LOCALAPPDATA",
               "APPDATA", "USERPROFILE", "HOMEDRIVE", "HOMEPATH", "PATHEXT",
               "NUMBER_OF_PROCESSORS", "PROCESSOR_ARCHITECTURE", "PROCESSOR_IDENTIFIER"}
    env = {k: v for k, v in os.environ.items() if k.upper() in allowed}
    root, writable = Path(root).resolve(), Path(writable).resolve()
    writable.mkdir(parents=True, exist_ok=True)
    home = writable / "runtime-home"
    scratch_base = writable / "cache/temp"
    home.mkdir(parents=True, exist_ok=True)
    scratch_base.mkdir(parents=True, exist_ok=True)
    if not home.resolve().is_relative_to(writable) or not scratch_base.resolve().is_relative_to(writable):
        raise ReleaseError("Runtime cache directory escapes writable root")
    native_data = ascii_tessdata(root / "runtime/tesseract/tessdata")
    scratch = Path(tempfile.mkdtemp(prefix="aster-", dir=scratch_base))
    try:
        native_scratch = native_ascii_path(scratch)
    except ReleaseError:
        # OCR now runs through stdin/stdout, so a non-ASCII temp folder is acceptable.
        native_scratch = str(scratch)
    env.update({
        "PATH": str(Path(env.get("SYSTEMROOT", "C:/Windows")) / "System32"),
        "ASTER_INSTALL_ROOT": str(root), "ASTER_WRITABLE_ROOT": str(writable),
        "OLLAMA_HOST": "127.0.0.1:11435", "OLLAMA_NO_CLOUD": "1",
        "OLLAMA_MODELS": str(root / "data/models/ollama-store"),
        "OLLAMA_NUM_PARALLEL": "1", "OLLAMA_MAX_LOADED_MODELS": "1",
        "OLLAMA_NOPRUNE": "1", "HOME": str(home), "USERPROFILE": str(home),
        "HOMEDRIVE": home.drive, "HOMEPATH": str(home)[len(home.drive):],
        "TEMP": native_scratch, "TMP": native_scratch,
        "HF_HOME": str(writable / "cache/huggingface"), "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1", "ANONYMIZED_TELEMETRY": "False",
        "DO_NOT_TRACK": "1", "TORCH_HOME": str(writable / "cache/torch"),
        "TESSDATA_PREFIX": native_data,
        "PYTHONNOUSERSITE": "1", "PYTHONUTF8": "1",
    })
    return env


def release_settings(root, manifest):
    from backend.app.config import Settings
    # Explicitly supply EVERY field to prevent process-env/default .env drift.
    values = {key: field.get_default(call_default_factory=True) for key, field in Settings.model_fields.items()}
    overrides = manifest["settings"]
    if set(overrides) - set(values):
        raise ReleaseError("Unknown release setting")
    values.update(overrides)
    for key in PATH_FIELDS:
        value = str(overrides.get(key, "data/disabled/" + key))
        values[key] = contained(root, value)
    values["tesseract_cmd"] = str(contained(root, overrides["tesseract_cmd"])) if overrides.get("tesseract_cmd") else ""
    values["app_env"] = "packaged"
    if (values["ollama_base_url"] != "http://127.0.0.1:11435"
            or values["strict_source_grounding"] is not True
            or values["enable_handwriting_ocr"] is not False
            or values["enable_xray"] is not False):
        raise ReleaseError("Unsupported release safety profile")
    model = manifest.get("model")
    if model and (values["text_model"] != model["tag"] or values["vision_model"] != model["tag"]):
        raise ReleaseError("Model settings differ from release")
    return Settings(_env_file=None, **values)
