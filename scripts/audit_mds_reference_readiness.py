"""Offline, read-only preflight for Aster's nine-specialty MDS reference pack.

Produces a request/facet review queue and structural diagnostics. Neither a
passing checksum nor a topic association constitutes medical evidence or a
qualified faculty review. This module NEVER activates a pack or writes config.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

import yaml

PACK = "artifacts/source-packs/mds-master-evidence-candidate-v5-2026-10-13"
BANK = "configs/benchmarks/mds-supplied/v2-2026-10-12"
COLUMNS = ["case_id", "turn", "specialties", "task_shape", "question",
           "topic_id", "facet", "scope", "exact_passage_id", "qualification_text",
           "faculty_reviewer", "review_status"]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def safe_pack_file(directory: Path, name: str) -> Path:
    if Path(name).name != name or name in {".", ".."}:
        raise ValueError("pack manifest contains unsafe file path")
    return directory / name


def audit(root: Path):
    """Return (report, review_queue). No generated medical approval."""
    root = root.resolve()
    findings = []
    path = root / PACK
    if not path.is_dir():
        findings.append("candidate_v5_pack_not_present")
        manifest = {}
    else:
        manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
        for name, expected in manifest.get("files", {}).items():
            target = safe_pack_file(path, name)
            if not target.is_file() or digest(target) != expected:
                findings.append("pack_checksum_missing_or_mismatch:" + name)
        if manifest.get("faculty_review") != "approved" or manifest.get("clinical_review") is not True:
            findings.append("independent_clinical_review_not_verified")
        if (path / "records.jsonl").is_file():
            count = 0
            with (path / "records.jsonl").open(encoding="utf-8") as rows:
                for line in rows:
                    if line.strip():
                        item = json.loads(line)
                        if not item.get("chunk_id") or not item.get("source_id"):
                            findings.append("record_missing_provenance")
                            break
                        count += 1
            if count != manifest.get("records"):
                findings.append("pack_record_count_mismatch")
        else:
            findings.append("pack_records_not_present")
        if (path / "sources.yaml").is_file():
            source_doc = yaml.safe_load((path / "sources.yaml").read_text(encoding="utf-8"))
            if not isinstance(source_doc, dict) or len(source_doc.get("sources", [])) != manifest.get("sources"):
                findings.append("pack_source_count_mismatch")
        else:
            findings.append("pack_source_registry_not_present")

    raw_root = root / "data/references/mds"
    xmls = sorted(p for p in raw_root.rglob("*.xml") if not p.name.endswith(".license.xml")) if raw_root.exists() else []
    missing_licenses, invalid_licenses, license_modes = [], [], Counter()
    for source in xmls:
        license_path = source.with_name(source.stem + ".license.xml")
        if not license_path.is_file():
            missing_licenses.append(str(source.relative_to(root)))
            continue
        try:
            content = " ".join(ET.parse(license_path).getroot().itertext()).lower()
        except ET.ParseError:
            invalid_licenses.append(str(license_path.relative_to(root)))
            continue
        if "creativecommons.org/licenses/by-nc-sa" in content:
            license_modes["CC_BY_NC_SA_snapshot"] += 1
        elif "creativecommons.org/licenses/by-nc" in content:
            license_modes["CC_BY_NC_snapshot"] += 1
        elif "creativecommons.org/licenses/by-sa" in content:
            license_modes["CC_BY_SA_snapshot"] += 1
        elif "creativecommons.org/licenses/by" in content:
            license_modes["CC_BY_snapshot"] += 1
        else:
            license_modes["unclassified_snapshot"] += 1
    if missing_licenses or invalid_licenses:
        findings.append("research_source_license_snapshots_missing_or_invalid")
    # A license notice is not verification of third-party assets, medical validity,
    # retraction status, postgraduate adequacy or training/redistribution rights.
    curriculum_path = root / "configs/all_mds_topics.json"
    specialties = {}
    if curriculum_path.is_file():
        curriculum = json.loads(curriculum_path.read_text(encoding="utf-8"))
        specialties = {s["id"]: len(s.get("topics", [])) for s in curriculum["specialties"]}
        if len(specialties) != 9 or sum(specialties.values()) != 126:
            findings.append("editorial_topic_catalog_shape_changed_needs_review")
    else:
        findings.append("editorial_topic_catalog_missing")
    findings.append("topic_association_not_facet_or_qualification_approval")

    queue = []
    bank_root = root / BANK
    for name in ("supplied.jsonl", "variations.jsonl"):
        file = bank_root / name
        if not file.is_file():
            findings.append("benchmark_bank_missing:" + name)
            continue
        with file.open(encoding="utf-8") as stream:
            for line in stream:
                if not line.strip():
                    continue
                case = json.loads(line)
                turns = case.get("turns", [])
                contracts = case.get("turn_content_contracts", [])
                for i, turn in enumerate(turns):
                    facets = contracts[i] if i < len(contracts) else []
                    # Preserve nonmedical interaction-only turns without
                    # assigning artificial claims or counting them as complete.
                    for cell in facets or [{"topic_id": "", "facet": ""}]:
                        queue.append({
                            "case_id": case["case_id"], "turn": i + 1,
                            "specialties": ";".join(case.get("specialties", [])),
                            "task_shape": case.get("task_shape", ""),
                            "question": turn.get("question", case.get("question", "")),
                            "topic_id": cell.get("topic_id", ""),
                            "facet": cell.get("facet", ""),
                            "scope": cell.get("scope", ""),
                            "exact_passage_id": "", "qualification_text": "",
                            "faculty_reviewer": "", "review_status": "unreviewed",
                        })
    findings.append("unseen_independent_review_not_present")
    active_profile = root / "configs/teaching.env"
    settings = {}
    if active_profile.is_file():
        for line in active_profile.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                settings[k.strip()] = v.strip()
    for variable in ("TEACHING_RELEASE_PATH", "TEACHING_INDEX_PATH"):
        active = settings.get(variable, "")
        if not active or not (root / active).exists():
            findings.append("configured_asset_missing:" + variable)
    findings.append("no_index_to_pack_compatibility_or_runtime_acceptance_evidence")
    result = {
        "schema_version": 1, "report_type": "offline_preflight_not_medical_review",
        "candidate_pack_version": manifest.get("version"),
        "candidate_records_declared": manifest.get("records"),
        "candidate_sources_declared": manifest.get("sources"),
        "raw_mds_article_xml_files": len(xmls),
        "license_snapshots_classified": dict(license_modes),
        "missing_license_snapshots": missing_licenses,
        "invalid_license_snapshots": invalid_licenses,
        "editorial_specialty_topics": specialties,
        "requested_review_queue_rows": len(queue),
        "independently_reviewed_facets": 0,
        "qualified_medical_signoff": False,
        "pack_or_index_activated": False,
        "eligible_for_activation": False,
        "findings": list(dict.fromkeys(findings)),
    }
    return result, queue


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--allow-blocked", action="store_true", help="Diagnostic report only; does not release")
    args = parser.parse_args()
    try:
        report, queue = audit(args.repo_root)
        if args.output_dir:
            args.output_dir.mkdir(parents=True, exist_ok=True)
            (args.output_dir / "mds-readiness.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            with (args.output_dir / "facet-review-queue.csv").open("w", encoding="utf-8", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=COLUMNS)
                writer.writeheader()
                writer.writerows(queue)
        print(json.dumps(report, indent=2))
        return 0 if args.allow_blocked or report["eligible_for_activation"] else 2
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as exc:
        print(json.dumps({"eligible_for_activation": False, "preflight_error": str(exc)}))
        return 3


if __name__ == "__main__":
    sys.exit(main())
