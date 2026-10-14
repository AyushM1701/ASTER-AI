"""Offline corpus integrity, rights and span checks; never a faculty review."""
import argparse
import json
from collections import Counter
from pathlib import Path

from scripts.mds_open_collect import (
    ROOT,
    inspect_xml,
    json_write,
    license_id,
    now,
    safe_path,
    snapshot_valid,
)


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.is_file() else []


def validate_corpus(output):
    output = Path(output)
    state = json.loads((output / "manifests/state.json").read_text(encoding="utf-8"))
    issues, samples, spans = [], {}, {}
    checked = 0
    for doc in state["documents"].values():
        if not snapshot_valid(doc, output):
            issues.append(doc["id"] + ":snapshot_invalid")
            continue
        try:
            checked += 1
            inspection = inspect_xml(safe_path(output, doc["stored_document_path"]).read_bytes(), doc["pmcid"])
            extracted = json.loads(safe_path(output, doc["extracted_path"]).read_text(encoding="utf-8"))
            rights = json.loads(safe_path(output, doc["rights_evidence_path"]).read_text(encoding="utf-8"))
            if inspection["track"] != "default" or inspection["license"] != doc["license"] or license_id(rights["license_url"]) != doc["license"]:
                issues.append(doc["id"] + ":rights_mismatch")
            if [s["text"] for s in inspection["sections"]] != [s["text"] for s in extracted["sections"]]:
                issues.append(doc["id"] + ":paragraph_mismatch")
            if rights["article_sha256"] != doc["raw_sha256"]:
                issues.append(doc["id"] + ":source_provenance_mismatch")
            if not doc["original_retained"] and inspection["omitted_assets"]:
                issues.append(doc["id"] + ":unresolved_assets_in_derivative")
            spans[doc["id"]] = {s["coordinate"]: s["text"] for s in extracted["sections"]}
            for specialty in doc["specialties"]:
                key = specialty + ":" + doc["license"]
                if key not in samples:
                    section = extracted["sections"][0]
                    samples[key] = {"document_id": doc["id"], "specialty": specialty, "license": doc["license"], "title": doc["title"], "source_url": doc["canonical_url"], "coordinate": section["coordinate"], "sample_text": section["text"][:900], "original_retained": doc["original_retained"], "checks": "checksum, JATS license, body paragraph equality, provenance, assets, exact export span", "independent_clinical_review": "pending"}
        except (ValueError, OSError, KeyError) as exc:
            issues.append(doc["id"] + ":" + type(exc).__name__)
    rag = rows(output / "rag_chunks/staged_rag.jsonl")
    training = rows(output / "training_candidates/rights_screened_candidates.jsonl")
    holdout = rows(output / "evaluation_holdout/source_chunks.jsonl")
    held_ids = {r["document_id"] for r in holdout}
    rag_ids = {r["document_id"] for r in rag}
    training_ids = {r["document_id"] for r in training}
    if held_ids & (rag_ids | training_ids):
        issues.append("heldout_split_leakage")
    for row in rag + holdout:
        if row["document_id"] not in spans:
            issues.append(row["document_id"] + ":orphan_export")
            continue
        text = spans[row["document_id"]].get(row.get("coordinate"), "")
        start, end = row.get("source_char_start"), row.get("source_char_end")
        if not isinstance(start, int) or not isinstance(end, int) or not 0 <= start < end <= len(text) or text[start:end] != row["text"]:
            issues.append(row["document_id"] + ":export_span_mismatch")
    return {"checked_at": now(), "passed": not issues, "source_family": "EuropePMC_authorized_REST_OA", "file_format": "JATS_XML", "documents_checked": checked, "export_spans_checked": len(rag) + len(holdout), "samples": list(samples.values()), "sample_specialty_counts": dict(Counter(s["specialty"] for s in samples.values())), "issues": sorted(set(issues)), "faculty_reviewed": 0, "clinical_review": "pending", "tables": "All unresolved asset tables omitted; licensed explicit tables checked by collector fixtures. No real eligible-table validation claimed unless present.", "ocr": "No OCR/PDF files collected; no OCR quality claim", "source_review": "automated integrity/rights/extraction screen; excerpt inspection is not independent medical appraisal"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="data/references/mds/open_corpus")
    args = parser.parse_args()
    output = safe_path(ROOT, args.output)
    report = validate_corpus(output)
    json_write(output / "reports/quality_validation.json", report)
    print(json.dumps({k: v for k, v in report.items() if k != "samples"}, indent=2))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
