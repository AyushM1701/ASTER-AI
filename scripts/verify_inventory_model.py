"""Capture a small real local-model smoke test; never a clinical accuracy score."""

import argparse
import hashlib
import json
import tempfile
import time
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.main import create_app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory(prefix="aster-inventory-smoke-") as temporary:
        installed = Settings()
        settings = Settings(_env_file=None, answer_mode="ollama", text_model=installed.text_model,
                            enable_educational_model_knowledge=True, enable_teaching=False,
                            workspace_path=Path(temporary) / "education.sqlite3")
        with TestClient(create_app(settings)) as client:
            headers = {"Authorization": "Bearer " + client.post("/v1/sessions").json()["token"]}
            model = client.app.state.ollama.ready()
            captures = []
            for question in ("Explain apoptosis and necrosis causes and nuclear changes", "Explain asthma mechanisms",
                             "Explain apoptosis and aspirin", "What does this X-ray show?"):
                started = time.monotonic()
                response = client.post("/v1/chat", headers=headers, json={"question": question, "audience": "study"})
                result = response.json()
                captures.append({"question": question, "http_status": response.status_code,
                                 "seconds": round(time.monotonic() - started, 2), "result": result})
                print(json.dumps({"question": question, "provisional": bool(result.get("provisional_explanation")),
                                  "provisional_status": result.get("provisional_status"), "http_status": response.status_code}), flush=True)
            inventory = client.get("/v1/study/source-inventory", headers=headers).json()
    raw = json.dumps(captures, ensure_ascii=False, indent=2).encode("utf-8")
    (args.output / "responses.json").write_bytes(raw)
    manifest = {"model": model, "clinical_accuracy": "not_assessed", "source_coverage_gain": "not_claimed",
                "source_scope": "Installed seed references; teaching disabled to exercise missing-source path",
                "responses_sha256": hashlib.sha256(raw).hexdigest(), "source_inventory_entries": len(inventory.get("entries", []))}
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
