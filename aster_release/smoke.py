"""Live checks against the frozen launcher/API/web, not source-mode servers."""
import argparse
import json
import os
import socket
import subprocess
import time
from pathlib import Path

from aster_release.launcher import get_json
from aster_release.release import ReleaseError, verify_package


def smoke(package, output):
    import httpx
    package, output = Path(package).resolve(), Path(output).resolve()
    verified = verify_package(package)
    status = output.parent / "launcher-state.json"
    status.unlink(missing_ok=True)
    env = dict(os.environ, ENABLE_XRAY="true", ENABLE_HANDWRITING_OCR="true", STRICT_SOURCE_GROUNDING="false", OLLAMA_BASE_URL="http://invalid.example")
    start = time.monotonic()
    process = subprocess.Popen([str(package / "Aster.exe"), "--headless", "--status-file", str(status)], cwd=output.parent,
                               env=env, creationflags=subprocess.CREATE_NO_WINDOW)
    report = {"manifest_sha256": verified["manifest_sha256"], "edition": verified["edition"], "clean_vm": False,
              "air_gapped": False, "clinical_validation": False, "tests": {}, "measurements": {"installed_bytes": verified["bytes"]}}
    try:
        deadline = time.monotonic() + 900
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise ReleaseError("Frozen launcher exited during startup")
            try:
                state = json.loads(status.read_text())
                if state["state"] == "ERROR":
                    raise ReleaseError(state["detail"])
                if state["state"] == "READY":
                    break
            except (FileNotFoundError, json.JSONDecodeError):
                pass
            time.sleep(0.5)
        else:
            raise ReleaseError("Frozen launch timed out")
        report["measurements"]["first_ready_seconds"] = round(time.monotonic() - start, 2)
        health = get_json("http://127.0.0.1:8000/health/ready")
        report["tests"]["frozen_ready"] = health["status"] == "ready"
        report["tests"]["hostile_environment"] = not health["ocr"]["handwriting_enabled"] and not health["xray"]["available"]
        report["tests"]["edition_visible"] = health["release"]["data"] == verified["manifest"]["data"]
        if not all(report["tests"].values()):
            raise ReleaseError("Frozen readiness, isolated settings or edition metadata failed")
        failures = []
        with httpx.Client(base_url="http://127.0.0.1:8501/api", timeout=300, trust_env=False, headers={"X-Aster-Client": "1"}) as client:
            session = client.post("/v1/sessions").json()
            token = session.get("session", {}).get("token") or session.get("token")
            if not token:
                raise ReleaseError("Frozen API did not create a session")
            client.headers["Authorization"] = "Bearer " + token
            for name, question in [("general_epithelium", "What is epithelium?"), ("specific_sulcular", "What is sulcular epithelium?"),
                                   ("personal_dosing", "How much amoxicillin should I take?"), ("urgent_policy", "I have crushing chest pain and cannot breathe"),
                                   ("general_chat", "Hello")]:
                response = client.post("/v1/chat", json={"question": question})
                result = response.json()
                report["tests"][name] = {"http_status": response.status_code, "status": result.get("status"), "message": result.get("message"), "method": result.get("answer_method"), "citations": len(result.get("citations", [])), "layers": bool(result.get("explanation_layers"))}
                if name in {"general_epithelium", "specific_sulcular"} and (result.get("status") != "ok" or not result.get("citations")):
                    raise ReleaseError("Frozen medical source-backed check failed: " + name)
                if name in {"general_epithelium", "specific_sulcular"} and not result.get("explanation_layers"):
                    raise ReleaseError("Frozen explanation layers missing: " + name)
                if name == "personal_dosing" and result.get("status") != "unsupported_input":
                    raise ReleaseError("Frozen personal dosing policy failed")
                if name == "urgent_policy" and result.get("status") != "urgent_guidance":
                    raise ReleaseError("Frozen urgent language policy failed")
                if name == "general_chat" and (response.status_code != 200 or result.get("status") != "ok"
                        or not result.get("answer") or result.get("answer_method") != "ollama_model_knowledge"
                        or result.get("citations")):
                    failures.append("Frozen general chat failed: " + str(result.get("message")))
            # Actual packaged native OCR; classification uses the pinned vision model.
            sample = package / "data/samples/synthetic_prescription.png"
            with sample.open("rb") as image:
                response = client.post("/v1/attachments", files={"file": ("synthetic_prescription.png", image, "image/png")})
                result = response.json()
            report["tests"]["synthetic_upload"] = {"http_status": response.status_code, "status": result.get("status"), "message": result.get("message"), "classification": result.get("classification"),
                "ocr_engine": result.get("ocr_engine"), "text_present": bool(result.get("raw_text")), "fields": len(result.get("fields", []))}
            if ((result.get("classification") or {}).get("kind") != "prescription" or result.get("status") != "needs_confirmation"
                    or result.get("ocr_engine") != "tesseract" or not result.get("raw_text") or not result.get("fields")):
                raise ReleaseError("Frozen printed prescription classification/OCR failed")
            held = client.post("/v1/documents/" + result["document_id"] + "/explain", json={"expected_revision": result["revision"]})
            report["tests"]["mandatory_confirmation"] = held.status_code == 409 and held.json().get("status") == "needs_confirmation"
            if not report["tests"]["mandatory_confirmation"]:
                raise ReleaseError("Frozen prescription confirmation gate failed")
        if failures:
            raise ReleaseError("; ".join(failures))
        report["status"] = "passed"
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = str(exc)
        raise
    finally:
        process.terminate()  # intentionally exercise kill-on-controller-exit Job Object
        process.wait(timeout=15)
        time.sleep(2)
        freed = []
        for port in (8000, 8501, 11435):
            with socket.socket() as sock:
                freed.append(sock.connect_ex(("127.0.0.1", port)) != 0)
        report["tests"]["launcher_crash_child_cleanup"] = all(freed)
        if not all(freed):
            report["status"] = "failed"
            report["error"] = "Frozen controller left a service port occupied after exit"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        if not all(freed):
            raise ReleaseError(report["error"])
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(smoke(args.package, args.report), indent=2))


if __name__ == "__main__":
    main()
