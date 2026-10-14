import hashlib
import importlib.metadata
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parents[1]


def sha_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def run_manifest(settings, references):
    try:
        git = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=3
        )
        commit = git.stdout.strip() if git.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        commit = None
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": commit,
        "python": platform.python_version(),
        "os": platform.platform(),
        "hardware": {
            "logical_cpus": psutil.cpu_count(),
            "ram_bytes": psutil.virtual_memory().total,
        },
        "dependency_lock_hash": sha_file(ROOT / "requirements.lock.txt"),
        "corpus_snapshot_hash": references.snapshot_hash,
        "source_register_hash": sha_file(settings.source_register),
        "knowledge_dependency_lock_hash": sha_file(ROOT / "requirements-knowledge-v2.lock.txt"),
        "policy_version": "research-policy-v1",
        "seed": 17,
        "answer_mode": settings.answer_mode,
        "retrieval_backend": settings.retrieval_backend,
        "model_manifest_hash": sha_file(ROOT / "configs/models.yaml"),
        "preprocessing_version": "xrv-8bit-center224-v1",
        "packages": {
            p: importlib.metadata.version(p) for p in ["fastapi", "streamlit", "pillow", "httpx"]
        },
    }
