"""Packaged acceptance for a v2 release candidate (runs the real frozen artifacts).

    python -m aster_release.acceptance_v2 --assets <release assets dir> --report <report.json> [--work DIR]

Uses a loopback HTTP mirror of the release assets (hashes are still enforced by
the lock compiled into AsterSetup). Shortcuts go to a temporary folder and the
uninstall entry to a test registry key, so the operator's desktop and
"Installed apps" list are not modified. This is NOT a clean-VM test.
"""
import argparse
import functools
import http.server
import io
import json
import os
import socket
import subprocess
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEST_KEY = r"Software\AsterAcceptanceTest\Uninstall\Aster"


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class Mirror:
    def __init__(self, directory, delay=0.0):
        handler = functools.partial(QuietHandler, directory=str(directory))
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", free_port()), handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def close(self):
        self.server.shutdown()


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send_head(self):
        # Range support so interrupted downloads can be resumed.
        path = self.translate_path(self.path)
        if "Range" not in self.headers or not os.path.isfile(path):
            return super().send_head()
        size = os.path.getsize(path)
        start = int(self.headers["Range"].split("=")[1].split("-")[0])
        handle = open(path, "rb")
        handle.seek(start)
        self.send_response(206)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Range", f"bytes {start}-{size - 1}/{size}")
        self.send_header("Content-Length", str(size - start))
        self.end_headers()
        return handle


def setup_command(assets, args):
    exe = Path(assets) / "AsterSetup-Windows-x64.exe"
    return [str(exe), *args]


def run_setup(assets, args, status, timeout=7200):
    started = time.monotonic()
    process = subprocess.run(setup_command(assets, ["--quiet", "--status-file", str(status), *args]), timeout=timeout)
    state = json.loads(Path(status).read_text(encoding="utf-8")) if Path(status).exists() else {}
    return process.returncode, state, round(time.monotonic() - started, 1)


def wait_state(status, wanted, process, timeout=1200):
    deadline = time.monotonic() + timeout
    last = {}
    while time.monotonic() < deadline:
        if Path(status).exists():
            try:
                last = json.loads(Path(status).read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass
            if last.get("state") in wanted:
                return last
        if process.poll() is not None and last.get("state") not in wanted:
            return last or {"state": "EXITED"}
        time.sleep(0.5)
    return {"state": "TIMEOUT", **last}


def launch(version_dir, writable, status):
    Path(status).unlink(missing_ok=True)
    return subprocess.Popen([str(version_dir / "Aster.exe"), "--headless", "--status-file", str(status), "--writable", str(writable)],
                            cwd=str(version_dir), creationflags=0x08000000)


def owned_pids(root_pid):
    import psutil

    try:
        parent = psutil.Process(root_pid)
        return [parent.pid] + [child.pid for child in parent.children(recursive=True)]
    except psutil.NoSuchProcess:
        return []


def external_connections(pids):
    import psutil

    found = []
    for pid in pids:
        try:
            for connection in psutil.Process(pid).net_connections(kind="inet"):
                remote = connection.raddr.ip if connection.raddr else None
                if remote and remote not in {"127.0.0.1", "::1"}:
                    found.append({"pid": pid, "remote": f"{remote}:{connection.raddr.port}"})
        except psutil.Error:
            continue
    return found


def workflow(web, report, writable):
    import httpx

    tests, timings = report["tests"], report["measurements"].setdefault("latency_seconds", {})
    with httpx.Client(base_url=web + "/api", timeout=600, trust_env=False, headers={"X-Aster-Client": "1"}) as client:
        token = client.post("/v1/sessions").json()["token"]
        client.headers["Authorization"] = "Bearer " + token

        def ask(name, question, audience="understand"):
            started = time.monotonic()
            result = client.post("/v1/chat", json={"question": question, "audience": audience,
                                                   "task_explicit": audience != "understand"}).json()
            timings[name] = round(time.monotonic() - started, 1)
            return result

        patient = ask("patient_question", "Why do my gums bleed when I brush?")
        tests["patient_answer_cited"] = patient.get("answer_method") == "grounded_synthesis" and bool(patient.get("citations"))
        study = ask("mds_question", "Describe the histopathological features of odontogenic keratocyst.", "study")
        tests["mds_answer_cited"] = bool(study.get("citations")) and study.get("status") in {"ok", "partial"}
        follow = ask("followup", "How is it treated?", "study")
        tests["followup_resolved"] = "keratocyst" in (follow.get("resolved_question") or "").casefold()
        if not tests["followup_resolved"]:  # record why (no user content: a fixed test question)
            report["notes"].append("followup: " + json.dumps({"status": follow.get("status"), "resolved": follow.get("resolved_question"),
                                                    "first_status": study.get("status"), "message": follow.get("message")})[:400])
        general = ask("general_chat", "What is the capital of Japan?")
        tests["general_chat"] = general.get("route") == "conversation" and "tokyo" in (general.get("answer") or "").casefold()
        # My Library: a user document is indexed locally, cited when asked about, and stored with the user's data.
        notes = ("# Enamel formation\n\nAmelogenesis is the formation of enamel by ameloblasts. It proceeds through a "
                 "secretory stage and a maturation stage, during which the enamel matrix proteins are removed and the "
                 "mineral content of the enamel rises sharply.\n").encode()
        started = time.monotonic()
        added = client.post("/v1/library/documents", params={"filename": "acceptance-notes.md", "title": "Acceptance notes",
                                                             "rights_confirmed": "true"},
                            content=notes, headers={"Content-Type": "application/octet-stream"}).json().get("document") or {}
        document = added
        while document.get("status") == "processing" and time.monotonic() - started < 300:
            time.sleep(1)
            document = client.get("/v1/library/documents/" + added["doc_id"]).json().get("document") or {}
        timings["my_library_index"] = round(time.monotonic() - started, 1)
        tests["my_library_indexed"] = document.get("status") == "ready"
        mine = ask("my_library_question", "According to my notes, what is amelogenesis?", "study")
        tests["my_library_answer_cited"] = any(c.get("source_type") == "library_user" for c in mine.get("citations") or [])
        tests["my_library_in_user_data"] = (Path(writable) / "library" / "user" / "library.sqlite").is_file()
        if not tests["my_library_indexed"] or not tests["my_library_answer_cited"]:
            report["notes"].append("my_library: " + json.dumps({"document": document.get("status"), "error": document.get("error"),
                                                                "answer": mine.get("status"), "message": mine.get("message")})[:400])
        tests["urgent_guidance"] = ask("urgent", "I have crushing chest pain right now").get("status") == "urgent_guidance"
        tests["personal_dose_refused"] = ask("personal_dose", "How many amoxicillin tablets should I take?").get("status") == "unsupported_input"
        calc = ask("calculation", "Calculate sensitivity and specificity: true positives 90, false negatives 10, false positives 20, true negatives 180.", "study")
        tests["deterministic_calculation"] = calc.get("answer_method") == "deterministic_calculation"
        image = (ROOT / "data/samples/synthetic_prescription.png").read_bytes()
        started = time.monotonic()
        attached = client.post("/v1/attachments", files={"file": ("rx.png", image, "image/png")}).json()
        timings["prescription_extract"] = round(time.monotonic() - started, 1)
        tests["prescription_classified_and_extracted"] = (attached.get("classification") or {}).get("kind") == "prescription" and bool(attached.get("fields"))
        if tests["prescription_classified_and_extracted"]:
            fields = [{"field_id": f["field_id"], "value": f.get("candidate_value"),
                       "status": "confirmed_by_user" if f.get("candidate_value") else "unreadable"} for f in attached["fields"]]
            explain_early = client.post(f"/v1/documents/{attached['document_id']}/explain", json={"expected_revision": attached["revision"]})
            tests["explain_requires_confirmation"] = explain_early.status_code == 409
            confirmed = client.put(f"/v1/documents/{attached['document_id']}/confirm",
                                   json={"expected_revision": attached["revision"], "confirmation_acknowledged": True, "fields": fields}).json()
            started = time.monotonic()
            explained = client.post(f"/v1/documents/{attached['document_id']}/explain", json={"expected_revision": confirmed["revision"]}).json()
            timings["prescription_explain"] = round(time.monotonic() - started, 1)
            tests["prescription_explained_or_honest_gap"] = explained.get("status") in {"ok", "partial", "insufficient_evidence"} and "prescription_explanation" in explained
            with_box = [f for f in attached["fields"] if f.get("bbox")]
            if with_box:
                crop = client.get(f"/v1/documents/{attached['document_id']}/fields/{with_box[0]['field_id']}/crop")
                tests["field_crop_served"] = crop.status_code == 200 and crop.content[:4] == b"\x89PNG"
        from PIL import Image

        pdf = io.BytesIO()
        Image.open(ROOT / "data/samples/synthetic_prescription.png").convert("RGB").save(pdf, format="PDF")
        scan = client.post("/v1/attachments", files={"file": ("scan.pdf", pdf.getvalue(), "application/pdf")}).json()
        tests["pdf_scan_attachment"] = bool(scan.get("document_id")) and scan.get("status") != "error"
        xray_bytes = (ROOT / "data/samples/nih-demo-00000001_000.png").read_bytes()
        xray = client.post("/v1/attachments", files={"file": ("cxr.png", xray_bytes, "image/png")}).json()
        tests["xray_classified"] = (xray.get("classification") or {}).get("kind") == "xray"
        if tests["xray_classified"]:
            started = time.monotonic()
            analysed = client.post(f"/v1/attachments/{xray['document_id']}/xray", json={"adult_confirmed": True}).json()
            timings["xray_analysis"] = round(time.monotonic() - started, 1)
            tests["xray_supported_scored"] = analysed.get("status") == "ok" and len(analysed.get("findings", [])) == 3
            declined = client.post(f"/v1/attachments/{xray['document_id']}/xray", json={"adult_confirmed": False}).json()
            tests["xray_requires_adult_confirmation"] = declined.get("status") == "unsupported_input"
        photo = Image.new("RGB", (640, 480), (200, 80, 40))
        buffer = io.BytesIO()
        photo.save(buffer, format="PNG")
        other = client.post("/v1/attachments", files={"file": ("photo.png", buffer.getvalue(), "image/png")}).json()
        tests["non_xray_not_scored"] = not other.get("findings")
        client.delete("/v1/sessions/current")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--assets", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--work", default=None)
    parser.add_argument("--profile", default=None)
    parser.add_argument("--skip-interrupt", action="store_true")
    args = parser.parse_args()
    assets = Path(args.assets).resolve()
    work = Path(args.work or (assets.parent / "acceptance")).resolve() / "Aster Test ✓ ünicode"
    if work.exists():
        import shutil

        shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    install_root, writable, shortcuts = work / "Programs" / "Aster", work / "LocalAppData" / "Aster", work / "Shortcuts"
    report = {"assets": str(assets), "lock_sha256": None, "clean_vm": False, "network_disabled": False,
              "clinical_validation": False, "tests": {}, "measurements": {}, "notes": []}
    import hashlib

    report["lock_sha256"] = hashlib.sha256((assets / "release-lock.json").read_bytes()).hexdigest()
    mirror = Mirror(assets)
    common = ["--install-dir", str(install_root), "--writable-dir", str(writable), "--mirror", mirror.url,
              "--shortcut-dir", str(shortcuts), "--registry-key", TEST_KEY] + (["--profile", args.profile] if args.profile else [])
    try:
        if not args.skip_interrupt:
            # Interrupted download: kill setup mid-way, then verify the rerun resumes from kept bytes.
            status = work / "setup-interrupt.json"
            process = subprocess.Popen(setup_command(assets, ["--quiet", "--status-file", str(status), *common]))
            time.sleep(25)
            import psutil

            for child in psutil.Process(process.pid).children(recursive=True):  # PyInstaller one-file child
                child.kill()
            process.kill()
            process.wait()
            time.sleep(2)
            partials = list((writable / "downloads").rglob("*.partial")) + [p for p in (writable / "downloads").rglob("*") if p.is_file()]
            report["measurements"]["bytes_kept_after_interrupt"] = sum(p.stat().st_size for p in partials)
        status = work / "setup.json"
        code, state, seconds = run_setup(assets, common, status)
        report["measurements"]["install_seconds_local_mirror"] = seconds
        report["tests"]["install_completed"] = code == 0 and state.get("stage") == "finished"
        if not report["tests"]["install_completed"]:
            report["notes"].append("install failed: " + json.dumps(state)[:500])
            return report
        current = json.loads((install_root / "current.json").read_text(encoding="utf-8"))
        version_dir = install_root / "versions" / current["version"]
        report["measurements"]["profile"] = current["profile"]
        report["measurements"]["installed_bytes"] = sum(p.stat().st_size for p in install_root.rglob("*") if p.is_file())
        report["tests"]["shortcuts_created"] = (shortcuts / "Aster.lnk").exists() and (shortcuts / "Uninstall Aster.lnk").exists()
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, TEST_KEY) as key:
                report["tests"]["uninstall_entry_registered"] = winreg.QueryValueEx(key, "DisplayName")[0] == "Aster"
        except OSError:
            report["tests"]["uninstall_entry_registered"] = False
        # Occupied default port: Aster must choose another port, not fail or stop the other program.
        blocker = socket.socket()
        try:
            blocker.bind(("127.0.0.1", 8000))
            blocker.listen()
        except OSError:
            report["notes"].append("port 8000 was already in use by another program (kept running)")
        launcher_status = work / "launcher.json"
        started = time.monotonic()
        process = launch(version_dir, writable, launcher_status)
        state = wait_state(launcher_status, {"READY", "ERROR"}, process)
        report["measurements"]["cold_start_seconds"] = round(time.monotonic() - started, 1)
        report["tests"]["ready_with_occupied_port_8000"] = state.get("state") == "READY"
        if state.get("state") != "READY":
            report["notes"].append("launch: " + json.dumps(state)[:500])
            process.kill()
            return report
        running = json.loads((writable / "running.json").read_text(encoding="utf-8"))
        web = running["url"].rstrip("/")
        report["measurements"]["web_url"] = web
        second_status = work / "launcher-2.json"
        second = launch(version_dir, writable, second_status)
        report["tests"]["duplicate_launch_reuses_instance"] = wait_state(second_status, {"ALREADY_RUNNING", "READY", "ERROR"}, second, 120).get("state") == "ALREADY_RUNNING"
        workflow(web, report, writable)
        pids = owned_pids(process.pid)
        report["measurements"]["owned_processes"] = len(pids)
        import psutil

        report["measurements"]["owned_rss_gb"] = round(sum(psutil.Process(p).memory_info().rss for p in pids if psutil.pid_exists(p)) / 1024 ** 3, 2)
        external = external_connections(pids)
        report["tests"]["no_external_connections_during_use"] = not external
        report["measurements"]["external_connections"] = external
        process.kill()
        process.wait()
        time.sleep(3)
        report["tests"]["owned_services_stopped"] = all(not psutil.pid_exists(p) for p in pids[1:])
        blocker.close()
        # Corruption -> launch refuses with repair advice -> repair -> launch works.
        victim = next(p for p in (version_dir / "data/models/nli-deberta-v3-xsmall").rglob("*.json"))
        victim.write_text(victim.read_text(encoding="utf-8") + " ", encoding="utf-8")
        process = launch(version_dir, writable, launcher_status)
        state = wait_state(launcher_status, {"READY", "ERROR"}, process, 300)
        report["tests"]["corruption_detected"] = state.get("state") == "ERROR" and "Repair" in state.get("detail", "")
        process.kill()
        code, state, seconds = run_setup(assets, ["--repair", *common], work / "repair.json")
        report["measurements"]["repair_seconds"] = seconds
        process = launch(version_dir, writable, launcher_status)
        report["tests"]["repair_restores_launch"] = wait_state(launcher_status, {"READY", "ERROR"}, process).get("state") == "READY"
        report["tests"]["my_library_kept_after_repair"] = (writable / "library" / "user" / "library.sqlite").is_file()
        process.kill()
        process.wait()
        time.sleep(3)
        code, state, _ = run_setup(assets, ["--uninstall", "--remove-data", *common], work / "uninstall.json")
        try:
            winreg.OpenKey(winreg.HKEY_CURRENT_USER, TEST_KEY).Close()
            registry_left = True
        except OSError:
            registry_left = False
        report["tests"]["uninstall_removes_files_shortcuts_entry"] = (code == 0 and not install_root.exists()
                                                                      and not (shortcuts / "Aster.lnk").exists() and not registry_left)
        return report
    finally:
        mirror.close()
        report["passed"] = bool(report["tests"]) and all(report["tests"].values())
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
