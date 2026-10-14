import socket
import sys
import time

import pytest

from aster_release.launcher import Controller, reserve_ports
from aster_release.processes import OwnedProcesses
from aster_release.release import ReleaseError
from aster_release.runtime import sanitized_environment


def test_occupied_port_is_not_stopped():
    with socket.socket() as unrelated:
        unrelated.bind(("127.0.0.1", 0))
        unrelated.listen()
        port = unrelated.getsockname()[1]
        with pytest.raises(ReleaseError, match="in use"):
            reserve_ports([port])
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            pass


def test_fatal_readiness_error_not_retried(tmp_path):
    class Processes:
        def healthy(self):
            return True
    c = Controller(tmp_path, tmp_path / "state")
    c.processes = Processes()
    def wrong_model():
        raise ReleaseError("digest differs")
    with pytest.raises(ReleaseError, match="digest differs"):
        c.wait(wrong_model, "startup", timeout=0.01)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows Job Object")
def test_owned_job_kills_descendants_without_touching_unrelated(tmp_path):
    import subprocess

    import psutil
    unrelated = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], creationflags=subprocess.CREATE_NO_WINDOW)
    owned = OwnedProcesses()
    pidfile = tmp_path / "grandchild.txt"
    script = "import subprocess,sys,time,pathlib; p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); pathlib.Path(sys.argv[1]).write_text(str(p.pid)); time.sleep(60)"
    try:
        pid = owned.start([sys.executable, "-c", script, str(pidfile)], tmp_path, sanitized_environment(tmp_path, tmp_path / "state"))
        deadline = time.monotonic() + 10
        while not pidfile.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        grandchild = int(pidfile.read_text())
        assert owned.healthy()
        owned.close()
        deadline = time.monotonic() + 5
        while any(psutil.pid_exists(p) for p in [pid, grandchild]) and time.monotonic() < deadline:
            time.sleep(0.05)
        assert not psutil.pid_exists(pid) and not psutil.pid_exists(grandchild)
        assert unrelated.poll() is None
    finally:
        owned.close()
        unrelated.terminate()
        unrelated.wait(timeout=10)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows short path cleanup")
def test_unicode_scratch_alias_is_cleaned_on_startup_failure(tmp_path, monkeypatch):
    from pathlib import Path
    root, writable = tmp_path / "package β", tmp_path / "state β"
    (root / "runtime/tesseract/tessdata").mkdir(parents=True)
    captured = {}
    def environment(*args):
        env = sanitized_environment(*args)
        captured["scratch"] = Path(env["TEMP"]).resolve()
        return env
    class Processes:
        def close(self):
            captured["closed"] = True
    def fail_cache(*args):
        raise ReleaseError("synthetic cache failure")
    monkeypatch.setattr("aster_release.launcher.verify_package", lambda root: {"manifest": {}})
    monkeypatch.setattr("aster_release.launcher.reserve_ports", lambda: {})
    monkeypatch.setattr("aster_release.launcher.OwnedProcesses", Processes)
    monkeypatch.setattr("aster_release.launcher.sanitized_environment", environment)
    monkeypatch.setattr("aster_release.model_cache.prepare_model_store", fail_cache)
    states = []
    Controller(root, writable, lambda state, detail: states.append(state)).run(False)
    assert states[-1] == "ERROR" and captured["closed"]
    assert not captured["scratch"].exists()
