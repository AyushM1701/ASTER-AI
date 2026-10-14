
import os
from pathlib import Path

import pytest

from aster_release.runtime import release_settings, sanitized_environment


def test_release_ignores_hostile_environment_and_dotenv(tmp_path, monkeypatch):
    monkeypatch.setenv("STRICT_SOURCE_GROUNDING", "false")
    monkeypatch.setenv("ENABLE_HANDWRITING_OCR", "true")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://evil.invalid")
    monkeypatch.setenv("MAX_ACTIVE_SESSIONS", "99")
    (tmp_path / ".env").write_text("ENABLE_XRAY=true\n")
    profile = {"model": None, "settings": {"ollama_base_url": "http://127.0.0.1:11435"}}
    settings = release_settings(tmp_path, profile)
    assert settings.strict_source_grounding and not settings.enable_handwriting_ocr and not settings.enable_xray
    assert settings.max_active_sessions == 20
    assert settings.corpus_path.is_relative_to(tmp_path)


def test_environment_is_allowlisted(tmp_path, monkeypatch):
    monkeypatch.setenv("HTTP_PROXY", "http://evil.invalid")
    monkeypatch.setenv("PYTHONPATH", "evil")
    monkeypatch.setenv("OLLAMA_MODELS", "wrong")
    env = sanitized_environment(tmp_path, tmp_path / "writable")
    assert "HTTP_PROXY" not in env and "PYTHONPATH" not in env
    assert env["OLLAMA_NO_CLOUD"] == "1"
    assert env["HF_HUB_OFFLINE"] == "1"
    assert env["OLLAMA_MODELS"] == str(tmp_path / "data/models/ollama-store")
    assert Path(env["USERPROFILE"]).is_relative_to(tmp_path / "writable")
    assert Path(env["TEMP"]).is_relative_to(tmp_path / "writable/cache/temp")


def test_packaged_ocr_never_uses_a_global_install(monkeypatch):
    from backend.app.adapters.ocr import OCRAdapter
    from backend.app.config import Settings
    monkeypatch.setattr("shutil.which", lambda executable: "C:/unexpected-global/tesseract.exe")
    adapter = OCRAdapter(Settings(_env_file=None, app_env="packaged", tesseract_cmd=""))
    assert adapter.executable is None


@pytest.mark.skipif(os.name != "nt", reason="Windows native path compatibility")
def test_unicode_install_and_scratch_have_ascii_native_ocr_paths(tmp_path):
    root = tmp_path / "Aster β's portable"
    data = root / "runtime/tesseract/tessdata"
    data.mkdir(parents=True)
    env = sanitized_environment(root, tmp_path / "writable β")
    assert env["TESSDATA_PREFIX"].isascii()
    assert env["TEMP"].isascii() and env["TMP"] == env["TEMP"]
    assert Path(env["TESSDATA_PREFIX"]).samefile(data)
    assert Path(env["TEMP"]).resolve().is_relative_to((tmp_path / "writable β/cache/temp").resolve())


def test_native_path_failure_removes_new_scratch(tmp_path, monkeypatch):
    from aster_release.release import ReleaseError
    def fail_scratch(path):
        if Path(path).name.startswith("aster-"):
            raise ReleaseError("No compatible short path")
        return str(path)
    monkeypatch.setattr("aster_release.runtime.native_ascii_path", fail_scratch)
    with pytest.raises(ReleaseError):
        sanitized_environment(tmp_path, tmp_path / "writable")
    assert not list((tmp_path / "writable/cache/temp").iterdir())


@pytest.mark.skipif(os.name != "nt", reason="Windows native path compatibility")
def test_native_path_without_ascii_alias_fails_closed(tmp_path, monkeypatch):
    import ctypes
    from types import SimpleNamespace

    from aster_release.release import ReleaseError
    from aster_release.runtime import native_ascii_path
    path = tmp_path / "Unicode β"
    path.mkdir()
    class NoShortName:
        def __call__(self, original, buffer, size):
            buffer.value = original
            return len(original)
    monkeypatch.setattr(ctypes, "WinDLL", lambda *args, **kwargs: SimpleNamespace(GetShortPathNameW=NoShortName()))
    with pytest.raises(ReleaseError, match="short names are unavailable"):
        native_ascii_path(path)
