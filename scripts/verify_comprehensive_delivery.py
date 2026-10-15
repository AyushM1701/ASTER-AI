"""Reconcile final evidence with current files and the running local application."""

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts/evaluation/comprehensive-v1"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    ledger = read(ART / "delivery-v2.json")
    for name, expected in {**ledger["files"], **ledger["runtime_hashes"]}.items():
        if digest(ROOT / name) != expected:
            raise ValueError(f"Changed delivery evidence: {name}")
    profile = read(ROOT / "configs/comprehensive_teaching_profile.json")
    release = ROOT / profile["TEACHING_RELEASE_PATH"]
    index = ROOT / profile["TEACHING_INDEX_PATH"]
    manifest = read(release / "manifest.json")
    for name, expected in manifest["files"].items():
        if digest(release / name) != expected:
            raise ValueError(f"Changed release file: {name}")
    if digest(release / "explanations.json") != profile["TEACHING_EXPLANATIONS_SHA256"]:
        raise ValueError("Profile notes identity changed")
    if digest(index / "vectors.npy") != read(index / "manifest.json")["vectors_sha256"]:
        raise ValueError("Index vectors changed")
    for folder in ("all-curricula-v3", "all-concepts-v1"):
        summary = read(ART / folder / "summary.json")
        inputs = summary["inputs"]
        if inputs["runtime_hashes"] != ledger["runtime_hashes"] or not summary["runtime_unchanged"]:
            raise ValueError("Evaluation runtime mismatch")
        if inputs["release_manifest_sha256"] != digest(release / "manifest.json"):
            raise ValueError("Evaluation release mismatch")
        if inputs["index_manifest_sha256"] != digest(index / "manifest.json"):
            raise ValueError("Evaluation index mismatch")
    for folder, count in (("faculty-curriculum-pack", 9144), ("faculty-concept-pack", 3048)):
        pack = ART / folder
        info = read(pack / "manifest.json")
        if info["qualified_human_accuracy"] is not None or info["review_status"] != "pending":
            raise ValueError("Unexpected human review claim")
        if digest(pack / "blinded-cases.json") != info["blinded_cases_sha256"]:
            raise ValueError("Changed blinded review cases")
        if digest(pack / "private-case-key.json") != info["private_key_sha256"]:
            raise ValueError("Changed private key")
        with (pack / "scores-blank.csv").open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        if len(rows) != count or len(read(pack / "blinded-cases.json")) != count:
            raise ValueError("Faculty pack count mismatch")
        if any(row["review_status"] != "pending" or any(row[field] for field in
               ("accuracy", "coverage", "reference_agreement", "safety")) for row in rows):
            raise ValueError("Blank faculty sheet has fabricated assessments")
    if digest(ROOT / ".env") != "5de372f436516c509a7ae792d42aaae9f20a9647a2a96d3405ee28ded4e77137":
        raise ValueError("Original environment changed")
    with urlopen("http://127.0.0.1:8000/health/ready", timeout=30) as response:
        health = json.load(response)
    teaching = health["teaching"]
    if health["status"] != "ready" or teaching["version"] != manifest["version"]:
        raise ValueError("Running app is not the evaluated ready release")
    if (teaching["records"], teaching["reviewed_explanations"], teaching["source_review_holds"]) != (2916, 41, 112):
        raise ValueError("Running teaching counts differ")
    with urlopen("http://127.0.0.1:8501/", timeout=10) as response:
        if response.status != 200:
            raise ValueError("Frontend unavailable")
    result = {
        "verified_utc": datetime.now(timezone.utc).isoformat(),
        "evidence_and_runtime_hashes_match": True,
        "release_and_index_hashes_match": True,
        "faculty_cases": 12192,
        "faculty_scores_blank": True,
        "faculty_accuracy": None,
        "original_environment_unchanged": True,
        "live_teaching": teaching,
        "frontend_http_status": 200,
        "all_gaps_closed": False,
        "documents": {name: digest(ROOT / name) for name in (
            "README.md", "docs/reports/ASTER_COMPREHENSIVE_AUDIT_v2.md",
            "docs/history/superpowers/plans/2026-10-09-aster-comprehensive-audit.md",
            "docs/history/superpowers/specs/2026-10-09-aster-comprehensive-audit-design.md")},
    }
    with (ART / "delivery-verification.json").open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    verify()
