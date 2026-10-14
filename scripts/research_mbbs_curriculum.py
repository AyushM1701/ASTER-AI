"""Pinned NMC curriculum inventory; curriculum metadata is not answer evidence."""

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

SUBJECTS = {
    "AN": "Anatomy", "PY": "Physiology", "BI": "Biochemistry", "BC": "Biochemistry",
    "PH": "Pharmacology", "PA": "Pathology", "MI": "Microbiology",
    "FM": "Forensic Medicine and Toxicology", "CM": "Community Medicine",
    "GM": "General Medicine", "IM": "General Medicine", "PE": "Paediatrics",
    "PS": "Psychiatry", "DR": "Dermatology, Venereology and Leprosy",
    "SU": "General Surgery", "OP": "Ophthalmology", "EN": "Otorhinolaryngology",
    "OG": "Obstetrics and Gynaecology", "OR": "Orthopaedics",
    "AS": "Anaesthesiology", "RD": "Radiodiagnosis", "RT": "Radiodiagnosis",
}
CODE = re.compile(r"^([A-Z]{2,3})(\d+)\.(\d+)$")
ROOT = Path(__file__).resolve().parents[1]


def normalized(text):
    return " ".join((text or "").split())


def normalize_code(value):
    code = re.sub(r"\s+", "", value or "").rstrip("*")
    code = re.sub(r"^([A-Z]{2,3})\.(\d+\.\d+)$", r"\1\2", code)
    return re.sub(r"^([A-Z]{2,3}\d+):(\d+)$", r"\1.\2", code)


def extract_competencies(pages):
    """Read ruled competency table cells, never inferred topic keyword matches.

    Input is (one-based PDF page, list of tables); descriptions retain their raw
    line breaks. Empty code cells can continue the preceding row across pages.
    Topic boundaries reset this association. Conflicts remain auditable.
    """
    rows, issues, by_code = [], [], {}
    current = None
    previous_page = None
    for page, tables in pages:
        if previous_page is not None and page != previous_page + 1:
            current = None
        previous_page = page
        found = False
        for table in tables:
            is_competency_table = any(
                len(row) > 1 and "COMPETENCY" in (row[1] or "").upper()
                and normalized(row[0]).lower() == "number" for row in table
            ) or any(len(row) >= 3 and CODE.fullmatch(normalize_code(row[0]))
                     and row[2] for row in table) or (
                         current is not None and any(len(row) >= 8 and not row[0]
                             and row[1] and not any(row[2:]) for row in table))
            if not is_competency_table:
                continue
            found = True
            for cells in table:
                if len(cells) < 2:
                    continue
                first, description = normalized(cells[0]), cells[1] or ""
                if first.lower() == "number":
                    continue
                code = normalize_code(first)
                match = CODE.fullmatch(code)
                if match:
                    subject = SUBJECTS.get(match[1], "Unknown")
                    if subject == "Unknown":
                        issues.append({"kind": "unknown_subject", "code": code, "page": page})
                    row = {"code": code, "raw_code": first,
                           "subject": subject, "text": normalized(description),
                           "raw_text": description, "page": page, "pages": [page],
                           "occurrences": [page], "extraction_status": "extracted_pending_review"}
                    if code in by_code:
                        existing = by_code[code]
                        if existing["text"] == row["text"]:
                            if page not in existing["occurrences"]:
                                existing["occurrences"].append(page)
                            current = existing
                        else:
                            existing["extraction_status"] = "conflict_requires_review"
                            issues.append({"kind": "conflicting_duplicate", "code": code,
                                           "page": page, "variant_text": row["text"],
                                           "variant_raw_text": description})
                            current = row
                    else:
                        rows.append(row)
                        by_code[code] = row
                        current = row
                    if not row["text"]:
                        issues.append({"kind": "empty_description", "code": code, "page": page})
                elif not first and normalized(description):
                    if current is None:
                        issues.append({"kind": "orphan_continuation", "page": page,
                                       "text": normalized(description)})
                    else:
                        current["raw_text"] += "\n" + description
                        current["text"] = normalized(current["raw_text"])
                        if page not in current["pages"]:
                            current["pages"].append(page)
                elif first:
                    current = None
                    if (re.match(r"^[A-Z]{2,3}[\d\s.:]", first)
                            or re.fullmatch(r"\d+\.\d+", first)) and normalized(description):
                        issues.append({"kind": "malformed_code", "page": page, "cell": first,
                                       "text": normalized(description), "raw_text": description,
                                       "cells": cells})
        if not found:
            current = None
    return rows, issues


def build_coverage(competencies, mappings=None):
    """Only supplied code-to-record mappings count as mapped, never as mastery."""
    mappings = mappings or {}
    competencies = [row for row in competencies if row.get("active", True)]
    counts = Counter(row["subject"] for row in competencies)
    subjects = {subject: {"extracted_competencies": count, "mapped_competencies": 0,
                           "unmapped_competencies": count,
                           "faculty_verified_competencies": None}
                for subject, count in sorted(counts.items())}
    rows = []
    for row in competencies:
        records = sorted(set(mappings.get(row["code"], [])))
        if records:
            subjects[row["subject"]]["mapped_competencies"] += 1
            subjects[row["subject"]]["unmapped_competencies"] -= 1
        rows.append({"code": row["code"], "subject": row["subject"], "record_ids": records,
                     "status": "mapped_material_pending_faculty_review" if records else "unmapped_gap",
                     "faculty_verified": None})
    return {"faculty_review": "not_performed", "competencies": rows, "subjects": subjects,
            "semantics": "Explicit material mapping is relevance only; not competency mastery."}


def apply_clarifications(rows, amendments):
    by_code = {row["code"]: row for row in rows}
    for row in rows:
        row["active"] = True
        row["curriculum_status"] = "base_curriculum"
    for amendment in amendments:
        if amendment["code"] not in by_code:
            raise ValueError(f"Clarification target missing: {amendment['code']}")
        row = by_code[amendment["code"]]
        row["clarification"] = amendment
        if amendment["action"] == "delete":
            row["active"] = False
            row["curriculum_status"] = "deleted_by_clarification"
        elif amendment["action"] == "replace":
            row["original_text"] = row["text"]
            row["text"] = amendment["text"]
            row["curriculum_status"] = "amended_by_clarification"
        else:
            raise ValueError("Unknown clarification action")
    return rows


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def research(config_path, download=False):
    from pypdf import PdfReader

    config = json.loads(config_path.read_text(encoding="utf-8"))
    raw = ROOT / "data/references/mbbs/raw"
    raw.mkdir(parents=True, exist_ok=True)
    snapshots = []
    for source in config["curriculum_sources"]:
        path = ROOT / source["path"]
        if not path.exists():
            if not download:
                raise FileNotFoundError(f"Missing pinned snapshot: {path}; use --download")
            import requests
            response = requests.get(source["url"], timeout=90)
            response.raise_for_status()
            if not response.content.startswith(b"%PDF"):
                raise ValueError("Source did not return a PDF")
            if hashlib.sha256(response.content).hexdigest() != source["sha256"]:
                raise ValueError("Official PDF differs from pinned snapshot; review required")
            path.write_bytes(response.content)
        if sha256(path) != source["sha256"]:
            raise ValueError(f"Pinned source integrity failed: {path}")
        reader = PdfReader(path)
        snapshots.append({**source, "pages": len(reader.pages), "bytes": path.stat().st_size})
    cache = raw / "curriculum-table-extraction.json"
    source_hash = config["curriculum_sources"][0]["sha256"]
    if cache.exists():
        payload = json.loads(cache.read_text(encoding="utf-8"))
        if payload["source_sha256"] != source_hash:
            raise ValueError("Table cache source mismatch")
    else:
        import pdfplumber
        pages = []
        with pdfplumber.open(ROOT / config["curriculum_sources"][0]["path"]) as pdf:
            for number, page in enumerate(pdf.pages, 1):
                # The curriculum tables begin on PDF page 108, and have vector rules.
                if number < 108:
                    continue
                pages.append([number, page.extract_tables()])
                if number % 50 == 0:
                    print(f"Extracted table cells through PDF page {number}", flush=True)
        payload = {"source_sha256": source_hash, "extractor": "pdfplumber ruled tables",
                   "pages": pages}
        cache.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    if config.get("table_extraction_sha256") and sha256(cache) != config["table_extraction_sha256"]:
        raise ValueError("Table extraction integrity failed; review or regenerate the pinned cache")
    allowed_pages = [entry for entry in payload["pages"] if any(
        start <= entry[0] <= end for start, end in config["competency_table_pdf_page_ranges"])]
    competencies, issues = extract_competencies(allowed_pages)
    competencies = apply_clarifications(competencies, config["clarifications"])
    competency_path = raw / "curriculum-competencies.jsonl"
    competency_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n"
                                      for row in competencies), encoding="utf-8")
    counts = Counter(row["subject"] for row in competencies)
    comparison = []
    for subject, expected in config["published_summary_counts"].items():
        comparison.append({"subject": subject, "published_summary_count": expected,
                           "extracted_unique_codes": counts[subject],
                           "difference": counts[subject] - expected,
                           "status": "count_matches_not_proof_of_completeness" if counts[subject] == expected
                           else "discrepancy_requires_review"})
    audit = {"schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
             "source_snapshots": snapshots, "unique_competencies": len(competencies),
             "table_extraction_sha256": sha256(cache),
             "competencies_sha256": sha256(competency_path),
             "competencies_path": str(competency_path.relative_to(ROOT)).replace("\\", "/"),
             "summary_count_comparison": comparison, "extraction_issues": issues,
             "active_competencies": sum(row["active"] for row in competencies),
             "coverage": build_coverage([row for row in competencies if row["active"]]),
             "source_candidates": config["source_candidates"],
             "source_observations": config.get("source_observations", []),
             "developer_source_spotcheck": config.get("developer_source_spotcheck"),
             "extraction_dependencies": config.get("extraction_dependencies", {}),
             "limitations": config["limitations"]}
    target = ROOT / "artifacts/evaluation/mbbs-v1/curriculum-audit.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"audit": str(target), "competencies": len(competencies),
                      "issues": len(issues)}, indent=2))
    return audit


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--config", type=Path, default=ROOT / "configs/mbbs_curriculum.json")
    args = parser.parse_args()
    research(args.config, args.download)
