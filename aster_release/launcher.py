"""Responsive desktop controller for immutable loopback-only Aster services."""
import argparse
import json
import logging
import logging.handlers
import os
import platform
import queue
import shutil
import socket
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

from aster_release.processes import OwnedProcesses
from aster_release.release import ReleaseError, contained, verify_package
from aster_release.runtime import sanitized_environment


def get_json(url, allow_unavailable=False, headers=None, timeout=4):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        response = opener.open(urllib.request.Request(url, headers=headers or {}), timeout=timeout)
    except urllib.error.HTTPError as exc:
        if not allow_unavailable or exc.code != 503:
            raise
        response = exc
    with response:
        return json.load(response)


def workspace_ready():
    return get_json("http://127.0.0.1:8501/api/health/ready", headers={"X-Aster-Client": "1"})["status"] == "ready"


def post_json(url, payload):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    with opener.open(request, timeout=300) as response:
        raw = response.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ReleaseError("Model readiness response exceeded the limit")
    return json.loads(raw)


def validate_inference(response, tag):
    if (response.get("model") != tag or response.get("done") is not True
            or not response.get("message", {}).get("content")):
        raise ReleaseError("Included model did not complete readiness inference")


def readiness_message(vision):
    message = {"role": "user", "content": "Reply with OK."}
    if vision:
        # Constant 64px RGB square, generated for this probe; no document or PHI.
        # Full-size prescription processing belongs to acceptance, not startup.
        message["images"] = ["iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAIAAAAlC+aJAAAAeElEQVR4nO3PQQkAMAzAwEqelEqeiD2OQSACLnN2v264oAEtaEALGtCCBrSgAS1oQAsa0IIGtKABLWhACxrQgga0oAEtaEALGtCCBrSgAS1oQAsa0IIGtKABLWhACxrQgga0oAEtaEALGtCCBrSgAS1oQAsa0ILHLokPAXjRU9cFAAAAAElFTkSuQmCC"]
    return message


def validate_loaded_data(health, manifest):
    for label, health_key, version_key in [("primary", "references", "library_version"),
                                           ("teaching", "teaching", "version"),
                                           ("secondary", "secondary_references", "library_version")]:
        if label == "teaching" and not manifest["settings"].get("enable_teaching"):
            continue
        if label == "secondary" and not manifest["settings"].get("enable_secondary_references"):
            continue
        actual, expected = health.get(health_key, {}), manifest["data"][label]
        if (actual.get("error") or actual.get("records") != expected["records"]
                or actual.get(version_key) != expected["release"]):
            raise ReleaseError(f"Included {label} library failed to load exactly. Close Aster and repair installation.")
        if label == "secondary" and not actual.get("available"):
            raise ReleaseError("Included secondary library is unavailable. Repair installation.")


def port_free(port):
    sock = socket.socket()
    try:
        if os.name == "nt":
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        sock.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def choose_ports(preferred=None):
    """Pick free loopback ports, preferring the defaults; never stop another program."""
    preferred = preferred or {"ollama": 11435, "api": 8000, "web": 8501}
    chosen, used = {}, set()
    for name, port in preferred.items():
        candidates = [port] + list(range(port + 100, port + 140))
        free = next((p for p in candidates if p not in used and port_free(p)), None)
        if free is None:
            raise ReleaseError(f"No free local port was found for the {name} service. Close some programs and retry.")
        chosen[name] = free
        used.add(free)
    return chosen


def reserve_ports(ports=(11435, 8000, 8501)):
    leases = {}
    try:
        for port in ports:
            sock = socket.socket()
            if os.name == "nt":
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            leases[port] = sock
            sock.bind(("127.0.0.1", port))
        return leases
    except OSError as exc:
        for sock in leases.values():
            sock.close()
        raise ReleaseError(f"Local port {port} is in use. Close that application and retry; Aster will not stop it.") from exc


class Controller:
    def __init__(self, root, writable, notify=lambda state, detail: None):
        self.root, self.writable = Path(root).resolve(), Path(writable).resolve()
        self.notify, self.stop = notify, threading.Event()
        self.processes, self.leases, self.lock = None, {}, None
        self.shutdown_event = None
        self.scratch = None
        self.manifest = None
        self.logger = logging.getLogger("aster-launcher")
        logs = self.writable / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(logs / "launcher.log", maxBytes=200_000, backupCount=2, encoding="utf-8")
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def state(self, state, detail):
        self.logger.info("state=%s", state)  # never log prompts, tokens or image contents
        self.notify(state, detail)

    def wait(self, callback, description, timeout=600):
        deadline = time.monotonic() + timeout
        while not self.stop.is_set():
            if not self.processes.healthy():
                raise ReleaseError("An Aster service stopped. Repair installation or export diagnostics.")
            try:
                if callback():
                    return
            except ReleaseError:
                raise
            except (OSError, ValueError):
                pass
            if time.monotonic() > deadline:
                raise ReleaseError(description + " timed out. Close Aster and repair the installation.")
            self.stop.wait(1)
        raise ReleaseError("Startup cancelled")

    def run(self, open_browser=True):
        from aster_release.v2 import is_v2

        if is_v2(self.root):
            return self.run_v2(open_browser)
        return self.run_v1(open_browser)

    def acquire_instance(self):
        """Single instance per writable root. Returns False if another Aster owns it."""
        import msvcrt

        self.writable.mkdir(parents=True, exist_ok=True)
        self.lock = (self.writable / "instance.lock").open("a+b")
        self.lock.seek(0)
        self.lock.write(b"1")
        self.lock.flush()
        self.lock.seek(0)
        try:
            msvcrt.locking(self.lock.fileno(), msvcrt.LK_NBLCK, 1)
            return True
        except OSError:
            self.lock.close()
            self.lock = None
            return False

    def run_v2(self, open_browser=True):
        from aster_release.model_cache import prepare_model_stores
        from aster_release.v2 import read_current, verify_installed
        running = self.writable / "running.json"
        try:
            if not self.acquire_instance():
                info = json.loads(running.read_text(encoding="utf-8")) if running.exists() else {}
                if info.get("url") and open_browser:
                    webbrowser.open(info["url"])
                self.state("ALREADY_RUNNING", "Aster is already open. Its workspace was brought to your browser.")
                return
            if os.name != "nt" or platform.machine().upper() not in {"AMD64", "X86_64"}:
                raise ReleaseError("Aster requires 64-bit Windows.")
            self.state("VERIFY_PACKAGE", "Checking installed files…")
            report = verify_installed(self.root, progress=lambda done, total: self.state(
                "VERIFY_PACKAGE", f"Checking installed files ({done} of {total})…"))
            profile = report["profile"]
            current = read_current(self.root.parent.parent) or {}
            profile_name = current.get("profile") or report["manifest"]["profile"]
            selected = profile["profiles"][profile_name]
            ports = choose_ports()
            self.processes = OwnedProcesses()
            env = sanitized_environment(self.root, self.writable)
            self.scratch = Path(env["TEMP"]).resolve()
            env.update({"OLLAMA_HOST": f"127.0.0.1:{ports['ollama']}", "ASTER_OLLAMA_PORT": str(ports["ollama"]),
                        "ASTER_API_PORT": str(ports["api"]), "ASTER_WEB_PORT": str(ports["web"]),
                        "MEDICAL_API_URL": f"http://127.0.0.1:{ports['api']}", "ASTER_PROFILE": profile_name,
                        "OLLAMA_KEEP_ALIVE": "30m", "OLLAMA_MAX_LOADED_MODELS": str(len(selected["models"]))})
            self.state("LOADING_MODEL_CACHE", "Preparing the installed AI models (no download needed).")
            env["OLLAMA_MODELS"] = str(prepare_model_stores(self.root, self.writable, report["manifest"]))
            from aster_release.shutdown import ShutdownEvent
            self.shutdown_event = ShutdownEvent()
            env["ASTER_STOP_EVENT"] = self.shutdown_event.name

            def start(relative, *args):
                self.processes.start([contained(self.root, relative), *args], self.root, env)

            self.state("START_OLLAMA", "Starting the local AI runtime.")
            start("runtime/ollama/ollama.exe", "serve")
            base = f"http://127.0.0.1:{ports['ollama']}"
            expected = {m["name"]: m["manifest_digest"] for m in report["manifest"].get("models", [])}

            def models_ready():
                listed = {m["name"]: m["digest"] for m in get_json(base + "/api/tags")["models"]}
                for name in selected["models"]:
                    if name not in listed:
                        return False
                    if expected.get(name) and listed[name] != expected[name]:
                        raise ReleaseError(f"Installed model {name} differs from the release. Choose Repair Aster.")
                return True
            self.wait(models_ready, "AI runtime startup")
            self.state("LOADING_DATA", "Loading the medical library, search indexes and checkers.")
            start("bin/aster-api/aster-api.exe")
            api = f"http://127.0.0.1:{ports['api']}"
            self.wait(lambda: get_json(api + "/health/live")["status"] == "alive", "Service startup")
            self.wait(lambda: get_json(api + "/health/ready", allow_unavailable=True)["status"] == "ready", "Library loading")
            self.state("SELF_TEST", "Testing search, claim checking, text reading and X-ray checks.")
            selftest = get_json(api + "/health/selftest", allow_unavailable=True, timeout=600)
            if selftest.get("status") != "ok":
                failed = [k for k, v in selftest.get("checks", {}).items() if not v.get("ok")]
                # Check results hold only counts, flags and exception names, never user content.
                self.logger.info("selftest=%s", json.dumps(selftest.get("checks", {}), sort_keys=True))
                raise ReleaseError("Startup self-test failed for: " + ", ".join(failed) + ". Choose Repair Aster.")
            self.state("LOADING_AI", "Running the AI models once locally (first start can take a minute).")
            for name in dict.fromkeys([selected["text_model"], selected["vision_model"]]):
                outcome, finished = {}, threading.Event()

                def warmup(model=name, vision=name == selected["vision_model"]):
                    try:
                        response = post_json(base + "/api/chat", {"model": model, "messages": [readiness_message(vision)],
                                             "stream": False, "think": False, "keep_alive": "30m",
                                             "options": {"num_predict": 4, "num_ctx": 4096, "temperature": 0}})
                        validate_inference(response, model)
                    except Exception as exc:
                        outcome["error"] = exc
                    finally:
                        finished.set()
                threading.Thread(target=warmup, daemon=True).start()

                def inference_ready():
                    if not finished.is_set():
                        return False
                    if outcome.get("error"):
                        raise ReleaseError("The AI model could not run on this computer (" + str(outcome["error"])[:120] +
                                           "). Close other programs to free memory, or choose Repair Aster.")
                    return True
                self.wait(inference_ready, "AI model test", timeout=900)
            start("bin/aster-web/aster-web.exe")
            web = f"http://127.0.0.1:{ports['web']}"
            self.wait(lambda: get_json(web + "/api/health/ready", headers={"X-Aster-Client": "1"})["status"] == "ready", "Workspace")
            running.write_text(json.dumps({"url": web + "/", "pid": os.getpid()}), encoding="utf-8")
            self.state("READY", "Aster is ready. Keep this window open while you use the workspace.")
            if open_browser:
                webbrowser.open(web + "/")
            while not self.stop.wait(2):
                if not self.processes.healthy():
                    raise ReleaseError("An Aster service stopped unexpectedly. Close and reopen Aster; if it repeats, choose Repair Aster.")
        except Exception as exc:
            self.state("ERROR", str(exc))
        finally:
            if self.lock:
                running.unlink(missing_ok=True)
            self.teardown()

    def teardown(self):
        if self.shutdown_event:
            self.shutdown_event.signal()
            time.sleep(2)
            self.shutdown_event.close()
            self.shutdown_event = None
        if self.processes:
            self.processes.close()
            self.processes = None
        if self.scratch and self.scratch.resolve().is_relative_to((self.writable / "cache/temp").resolve()) \
                and self.scratch.name.startswith("aster-") and not self.scratch.is_symlink():
            shutil.rmtree(self.scratch, ignore_errors=True)
        for lease in self.leases.values():
            lease.close()
        self.leases.clear()
        if self.lock:
            self.lock.close()
            self.lock = None

    def run_v1(self, open_browser=True):
        try:
            self.state("VERIFY_PACKAGE", "Checking installation files. This can take a few minutes.")
            report = verify_package(self.root)
            self.manifest = report["manifest"]
            if os.name != "nt" or platform.machine().upper() not in {"AMD64", "X86_64"}:
                raise ReleaseError("This package requires 64-bit Windows.")
            import msvcrt
            self.lock = (self.writable / "instance.lock").open("a+b")
            self.lock.seek(0)
            self.lock.write(b"1")
            self.lock.flush()
            self.lock.seek(0)
            msvcrt.locking(self.lock.fileno(), msvcrt.LK_NBLCK, 1)
            self.leases = reserve_ports()
            self.processes = OwnedProcesses()
            env = sanitized_environment(self.root, self.writable)
            self.scratch = Path(env["TEMP"]).resolve()
            from aster_release.model_cache import prepare_model_store
            self.state("LOADING_MODEL_CACHE", "Preparing the included model for local use. No download is needed.")
            env["OLLAMA_MODELS"] = str(prepare_model_store(self.root, self.writable, self.manifest))
            from aster_release.shutdown import ShutdownEvent
            self.shutdown_event = ShutdownEvent()
            env["ASTER_STOP_EVENT"] = self.shutdown_event.name
            def start(port, relative, *args):
                self.leases.pop(port).close()
                self.processes.start([contained(self.root, relative), *args], self.root, env)
            self.state("START_OLLAMA", "Loading the included AI runtime.")
            start(11435, "runtime/ollama/ollama.exe", "serve")
            tag, digest = self.manifest["model"]["tag"], self.manifest["model"]["digest"]
            def model_ready():
                models = get_json("http://127.0.0.1:11435/api/tags")["models"]
                found = next((m for m in models if m["name"] == tag), None)
                if found and found["digest"] != digest:
                    raise ReleaseError("Model digest differs from release. Repair installation.")
                return bool(found)
            self.wait(model_ready, "AI runtime startup")
            self.state("LOADING_DATA", "Loading included references and checking search indexes.")
            start(8000, self.manifest.get("entrypoints", {}).get("api", "bin/aster-api.exe"))
            self.wait(lambda: get_json("http://127.0.0.1:8000/health/live")["status"] == "alive", "API startup")
            self.state("LOADING_AI", "Checking AI, OCR and included data readiness.")
            def api_ready():
                health = get_json("http://127.0.0.1:8000/health/ready", allow_unavailable=True)
                validate_loaded_data(health, self.manifest)
                release = health.get("release") or {}
                return (health["status"] == "ready" and release.get("data") == self.manifest["data"]
                        and release.get("features") == self.manifest["features"]
                        and (not self.manifest["features"].get("printed_ocr") or health["ocr"]["available"]))
            self.wait(api_ready, "AI readiness")
            self.state("LOADING_AI", "Running the included AI model locally before opening the workspace.")
            outcome, finished = {}, threading.Event()
            def warmup():
                try:
                    message = readiness_message(self.manifest["features"].get("vision_routing"))
                    response = post_json("http://127.0.0.1:11435/api/chat", {"model": tag, "messages": [message],
                        "stream": False, "think": False, "keep_alive": "5m", "options": {"num_predict": 4, "num_ctx": 8192, "temperature": 0}})
                    validate_inference(response, tag)
                except Exception as exc:
                    outcome["error"] = exc
                finally:
                    finished.set()
            threading.Thread(target=warmup, daemon=True).start()
            def inference_ready():
                if not finished.is_set():
                    return False
                if outcome.get("error"):
                    raise ReleaseError("Included model could not run. Check resources or repair installation: " + str(outcome["error"]))
                return True
            self.wait(inference_ready, "Included model inference")
            start(8501, self.manifest.get("entrypoints", {}).get("web", "bin/aster-web.exe"))
            self.wait(workspace_ready, "Workspace bridge")
            self.state("READY", "Aster is ready. Keep this window open while you use the workspace.")
            if open_browser:
                webbrowser.open("http://127.0.0.1:8501/")
            while not self.stop.wait(2):
                if not self.processes.healthy():
                    raise ReleaseError("An Aster service stopped. Close and relaunch, or repair installation.")
        except Exception as exc:
            self.state("ERROR", str(exc))
        finally:
            if self.shutdown_event:
                self.shutdown_event.signal()
                time.sleep(2)  # bounded grace for API/web lifespan cleanup
                self.shutdown_event.close()
            if self.processes:
                self.processes.close()
            if self.scratch and self.scratch.resolve().is_relative_to((self.writable / "cache/temp").resolve()) and self.scratch.name.startswith("aster-") and not self.scratch.is_symlink():
                shutil.rmtree(self.scratch, ignore_errors=True)
            for lease in self.leases.values():
                lease.close()
            self.leases.clear()
            if self.lock:
                self.lock.close()

    def diagnostics(self, destination):
        # Allowlisted summary only; never copy the source tree, environment or logs.
        import zipfile
        with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
            safe = {key: (self.manifest or {}).get(key) for key in ("app_version", "edition", "features", "data", "model")}
            safe["os"] = platform.platform()
            safe["clinical_validation"] = False
            archive.writestr("diagnostics.json", json.dumps(safe, indent=2))


def main():
    import sys
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--root", type=Path)
    parser.add_argument("--writable", type=Path, help="Writable cache/log directory outside the installation")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--status-file", type=Path, help="QA state report outside the installation")
    args = parser.parse_args()
    root = args.root or (Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1])
    if args.verify_only:
        from aster_release.v2 import INSTALLED_MANIFEST, verify_installed

        if (Path(root) / INSTALLED_MANIFEST).exists():  # current (v2) installations: hash every file
            result = verify_installed(root, full=True)
        else:
            result = verify_package(root)
        print(json.dumps({k: v for k, v in result.items() if k not in {"manifest", "profile"}}, indent=2, default=str))
        return
    portable_marker = Path(root).resolve().parent.parent / "portable.json"
    if args.writable:
        writable = args.writable
    elif portable_marker.exists():
        writable = portable_marker.parent / "UserData"  # portable copy keeps everything in its own folder
    else:
        writable = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Aster"
    if writable.resolve().is_relative_to(root.resolve()):
        raise ReleaseError("Writable cache/log directory must be outside the immutable installation")
    if args.headless:
        def notify(state, detail):
            if args.status_file:
                if args.status_file.resolve().is_relative_to(root.resolve()):
                    raise ReleaseError("QA report must be outside the immutable install folder")
                args.status_file.parent.mkdir(parents=True, exist_ok=True)
                args.status_file.write_text(json.dumps({"state": state, "detail": detail}), encoding="utf-8")
            elif sys.stdout is not None:
                print(state, detail, flush=True)
        controller = Controller(root, writable, notify)
        try:
            controller.run(False)
        except KeyboardInterrupt:
            controller.stop.set()
        return
    import tkinter as tk
    from tkinter import filedialog
    ui = tk.Tk()
    ui.title("Aster")
    ui.geometry("540x320")
    ui.configure(bg="#0d141a")
    messages = queue.Queue()
    controller = Controller(root, writable, lambda state, detail: messages.put((state, detail)))
    tk.Label(ui, text="Aster", bg="#0d141a", fg="#79d9c6", font=("Segoe UI", 22)).pack(anchor="w", padx=28, pady=(24, 10))
    status = tk.Label(ui, text="Starting…", bg="#0d141a", fg="#f0f4f5", font=("Segoe UI", 15))
    status.pack(anchor="w", padx=28)
    detail = tk.Label(ui, text="", wraplength=475, justify="left", bg="#0d141a", fg="#b4c1cc", font=("Segoe UI", 11))
    detail.pack(anchor="w", padx=28, pady=14)
    def export():
        path = filedialog.asksaveasfilename(defaultextension=".zip", initialfile="Aster-diagnostics.zip")
        if path:
            controller.diagnostics(path)
    tk.Button(ui, text="Export diagnostics", command=export).pack(side="left", padx=28, pady=20)
    for child in ui.winfo_children():
        if isinstance(child, tk.Button):
            child.configure(bg="#192530", fg="#e8edf2", activebackground="#16332d", activeforeground="#e8edf2", relief="flat", padx=14, pady=8, font=("Segoe UI", 11))
    worker = threading.Thread(target=controller.run, daemon=False)
    def close():
        controller.stop.set()
        status.configure(text="Closing Aster…")
        if worker.is_alive():
            ui.after(150, close)
        else:
            ui.destroy()
    ui.protocol("WM_DELETE_WINDOW", close)
    def update():
        while not messages.empty():
            state, message = messages.get()
            status.configure(text=state.replace("_", " ").title())
            detail.configure(text=message)
        ui.after(100, update)
    worker.start()
    update()
    ui.mainloop()
