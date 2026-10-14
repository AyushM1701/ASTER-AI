"""Validate a release, update only library settings, and retain rollback state."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.config import Settings  # noqa: E402
from backend.app.services.retrieval import ReferenceStore  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path)
    parser.add_argument("--index", type=Path)
    parser.add_argument("--v1", action="store_true")
    args = parser.parse_args()
    if args.v1:
        changes = {
            "CORPUS_PATH": "data/references/normalized/seed.jsonl",
            "SOURCE_REGISTER": "configs/sources.yaml",
            "RETRIEVAL_BACKEND": "lexical",
            "CHROMA_PATH": "data/indexes/reference_v1",
            "REFERENCE_COLLECTION": "medical_reference_v1",
        }
    else:
        if not args.release or not args.index:
            parser.error("Supply --release and --index, or --v1")
        changes = {
            "CORPUS_PATH": str(args.release / "records.jsonl"),
            "SOURCE_REGISTER": str(args.release / "sources.yaml"),
            "RETRIEVAL_BACKEND": "hybrid",
            "CHROMA_PATH": str(args.index),
            "REFERENCE_COLLECTION": "medical_reference_v2",
        }
    configuration = Settings(
        corpus_path=changes["CORPUS_PATH"],
        source_register=changes["SOURCE_REGISTER"],
        retrieval_backend=changes["RETRIEVAL_BACKEND"],
        chroma_path=changes["CHROMA_PATH"],
        reference_collection=changes["REFERENCE_COLLECTION"],
    )
    refs = ReferenceStore(configuration)
    if refs.error:
        parser.error(refs.error)
    manifest = refs.manifest()
    refs.close()
    env = ROOT / ".env"
    current = env.read_text(encoding="utf-8") if env.exists() else ""
    backup = ROOT / ".env.v1-knowledge-backup"
    if not backup.exists():
        backup.write_text(current, encoding="utf-8")
    changes["STRICT_SOURCE_GROUNDING"] = "true"
    retained = [line for line in current.splitlines() if line.split("=", 1)[0] not in changes]
    env.write_text(
        "\n".join([*retained, *(f"{key}={value}" for key, value in changes.items())]) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "activated_settings": manifest["library_version"],
                "records": manifest["records"],
                "backend": manifest["backend"],
                "restart_required": True,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
