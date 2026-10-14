"""Convert explicitly human-reviewed collector selections to an inactive pack.

No source approval is inferred from collection, rights screening or a template.
Only CC-BY-4.0 is supported here; other collector licenses fail preflight.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.config import Settings  # noqa: E402
from backend.app.services.retrieval import Reference, permitted_source  # noqa: E402
from backend.app.services.teaching import TeachingStore  # noqa: E402

ATTESTATION = "I personally reviewed the selected source text, extraction coordinates, rights evidence and editorial status and entered these assessments."
CATALOGUE = "manifests/catalogue.jsonl"
CHUNKS = "rag_chunks/staged_rag.jsonl"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def object_hash(row):
    return sha(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode())


def safe_path(root, name):
    if not isinstance(name, str) or not name or Path(name).is_absolute() or re.match(r"^[A-Za-z]:|^[/\\]", name):
        raise ValueError("unsafe collector path")
    path = (root / name.replace("\\", "/")).resolve()
    if not path.is_relative_to(root.resolve()) or path == root.resolve():
        raise ValueError("collector path escapes root")
    return path


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def bindings(root, doc):
    evidence = safe_path(root, doc["rights_evidence_path"])
    stored = safe_path(root, doc["stored_document_path"])
    extracted = safe_path(root, doc["extracted_path"])
    return {"document_id": doc["id"], "catalogue_row_sha256": object_hash(doc), "raw_sha256": doc["raw_sha256"],
            "stored_sha256": sha(stored.read_bytes()), "extracted_sha256": sha(extracted.read_bytes()),
            "rights_evidence_sha256": sha(evidence.read_bytes())}


def review_template(root):
    root = Path(root).resolve()
    documents = []
    for doc in rows(safe_path(root, CATALOGUE)):
        documents.append(bindings(root, doc) | {"title": doc["title"], "publication_date": doc.get("publication_date") or "",
            "publisher": "", "study_type": "", "study_context": "", "population_context": "", "limitations": [],
            "topic_names": [], "keywords": [], "rights_confirmed": False, "extraction_confirmed": False,
            "editorial_confirmed": False, "source_review_confirmed": False, "editorial_status": "",
            "editorial_checked_date": "", "editorial_reference_url": ""})
    return {"schema_version": 1, "catalogue_sha256": sha(safe_path(root, CATALOGUE).read_bytes()),
            "staged_rag_sha256": sha(safe_path(root, CHUNKS).read_bytes()), "reviewer_name": "", "reviewer_institution": "",
            "assessment_origin": "", "review_date": "", "attestation": "", "documents": documents,
            "notice": "Delete unreviewed selections; fill fields only after actual personal review. This blank template approves nothing. Clinical/F03 review remains pending."}


def valid_date(value):
    try:
        parsed = date.fromisoformat(value)
        return parsed <= date.today()
    except (ValueError, TypeError):
        return False


def stage(root, review, output):
    root, output = Path(root).resolve(), Path(output).resolve()
    if output.exists():
        raise FileExistsError("immutable pack output already exists")
    if output.is_relative_to(root) or output.is_relative_to(ROOT / "data/references"):
        raise ValueError("output must be outside collector and active reference releases")
    if (review.get("assessment_origin") != "human_entered" or review.get("attestation") != ATTESTATION
            or not valid_date(review.get("review_date")) or not all(str(review.get(k, "")).strip() for k in ("reviewer_name", "reviewer_institution"))
            or re.search(r"\b(?:ai|assistant|model|automated|pending|unknown)\b", str(review.get("reviewer_name", "")), re.I)):
        raise ValueError("explicit personal human review attestation is required")
    input_hashes = {CATALOGUE: review.get("catalogue_sha256"), CHUNKS: review.get("staged_rag_sha256")}
    for name, checksum in input_hashes.items():
        if sha(safe_path(root, name).read_bytes()) != checksum:
            raise ValueError("stale collector manifest hash: " + name)
    catalogue_rows = rows(safe_path(root, CATALOGUE))
    catalogue = {doc["id"]: doc for doc in catalogue_rows}
    if len(catalogue) != len(catalogue_rows):
        raise ValueError("duplicate catalogue document identity")
    selected = review.get("documents", [])
    if not selected:
        raise ValueError("no explicitly reviewed selections")
    chunks = rows(safe_path(root, CHUNKS))
    seen_docs, seen_families, seen_chunks = set(), set(), set()
    records, sources, metadata, omitted = [], [], {}, []
    for assessment in selected:
        doc = catalogue.get(assessment.get("document_id"))
        if not doc:
            raise ValueError("reviewed document absent from catalogue")
        if doc.get("split") != "training_candidate":
            raise ValueError("evaluation/validation/unknown split cannot enter retrieval")
        family = doc.get("version_family_id")
        if doc["id"] in seen_docs or not family or family in seen_families or doc.get("duplicate_of"):
            raise ValueError("duplicate document/version family")
        seen_docs.add(doc["id"])
        seen_families.add(family)
        if doc.get("license") != "CC-BY-4.0":
            raise ValueError("unsupported runtime license: " + str(doc.get("license")) + "; CC-BY-4.0 only")
        if doc.get("status") != "STAGED" or doc.get("quality_pass") is not True:
            raise ValueError("failed extraction quality or non-staged source")
        if any(str(f).casefold() in {"corrupted_extraction", "truncated_passage", "failed", "retracted", "superseded", "missing_table_headers", "untrusted_instruction"} for f in doc.get("quality_flags", [])):
            raise ValueError("failed quality/editorial source flag")
        current = bindings(root, doc)
        if any(assessment.get(k) != v for k, v in current.items()) or any(current[k] != doc.get(k) for k in ("raw_sha256", "stored_sha256", "extracted_sha256")):
            raise ValueError("reviewed document hash binding changed")
        if not re.fullmatch(r"[0-9a-f]{64}", doc["raw_sha256"]):
            raise ValueError("invalid raw source hash")
        if not all(assessment.get(k) is True for k in ("rights_confirmed", "extraction_confirmed", "editorial_confirmed", "source_review_confirmed")):
            raise ValueError("human rights/extraction/editorial confirmations missing")
        if assessment.get("editorial_status") != "not_retracted_not_superseded" or not valid_date(assessment.get("editorial_checked_date")):
            raise ValueError("editorial review unresolved or source stale")
        if urlsplit(assessment.get("editorial_reference_url", "")).scheme != "https":
            raise ValueError("editorial evidence URL missing")
        required = ("publisher", "study_type", "study_context", "population_context")
        if not all(isinstance(assessment.get(k), str) and assessment[k].strip() for k in required):
            raise ValueError("publisher/date/design/population appraisal missing")
        for name in ("limitations", "topic_names", "keywords"):
            if not isinstance(assessment.get(name), list) or not assessment[name] or not all(isinstance(v, str) and v.strip() for v in assessment[name]):
                raise ValueError("reviewed " + name + " missing")
        if not valid_date(assessment.get("publication_date")) or assessment["publication_date"] != doc.get("publication_date") or assessment.get("title") != doc.get("title"):
            raise ValueError("source title/date differs from catalogue")
        if doc.get("publisher") and assessment["publisher"] != doc["publisher"]:
            raise ValueError("publisher differs from catalogue")
        rights = json.loads(safe_path(root, doc["rights_evidence_path"]).read_text(encoding="utf-8"))
        license_url = "https://creativecommons.org/licenses/by/4.0/"
        if (rights.get("license") != doc["license"] or rights.get("article_sha256") != doc["raw_sha256"]
                or rights.get("source_url") != doc["canonical_url"] or not rights.get("exact_notice")
                or rights.get("attribution") != doc.get("attribution")
                or set(rights.get("omitted_assets", [])) != set(doc.get("exclusions", []))
                or str(rights.get("license_url", "")).replace("http://", "https://").rstrip("/") != license_url.rstrip("/")):
            raise ValueError("rights evidence is missing or inconsistent")
        if str(doc.get("license_url", "")).replace("http://", "https://").rstrip("/") != license_url.rstrip("/"):
            raise ValueError("rights license URL conflicts")
        if doc.get("original_retained"):
            if sha(safe_path(root, doc.get("original_path")).read_bytes()) != doc["raw_sha256"]:
                raise ValueError("retained original hash differs")
        basis = {"type": "open_license", "approved_host": urlsplit(doc["canonical_url"]).hostname,
                 "license": "CC-BY-4.0", "license_url": license_url, "snapshot_sha256": doc["raw_sha256"],
                 "clinical_review": False, "material_type": "research", "attribution": doc["attribution"]}
        source = {"source_id": "reviewed-" + doc["id"], "url": doc["canonical_url"], "approval": "user_attested",
                  "terms": "Explicit human rights/extraction/editorial review; CC-BY-4.0; preserve attribution and omissions",
                  "raw_sha256": doc["raw_sha256"], "permission_basis": basis, "clinical_review": False,
                  "record_checksums": [], "reviewer": review["reviewer_name"], "review_date": review["review_date"]}
        if not permitted_source(doc["canonical_url"], source):
            raise ValueError("runtime source permission/host preflight rejected")
        extracted = json.loads(safe_path(root, doc["extracted_path"]).read_text(encoding="utf-8"))
        if extracted.get("id") != doc["id"]:
            raise ValueError("extracted document identity changed")
        sections = {}
        for section in extracted.get("sections", []):
            if section["coordinate"] in sections:
                raise ValueError("duplicate extracted coordinate")
            sections[section["coordinate"]] = section
        selected_chunks = [c for c in chunks if c.get("document_id") == doc["id"]]
        if not selected_chunks:
            raise ValueError("reviewed source has no staged chunks")
        for chunk in selected_chunks:
            if chunk.get("split") != "training_candidate" or chunk.get("version_family_id") != family or chunk.get("status") != "STAGED":
                raise ValueError("chunk split/family/status mismatch")
            section = sections.get(chunk.get("coordinate"))
            start, end = chunk.get("source_char_start"), chunk.get("source_char_end")
            if (not section or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(section["text"])
                    or section["text"][start:end] != chunk.get("text") or chunk.get("section_id") != chunk.get("coordinate")
                    or chunk.get("heading_hierarchy") != section.get("heading") or chunk.get("page") != section.get("page")
                    or chunk.get("section") != " > ".join(section.get("heading", []))):
                raise ValueError("stale or forged chunk coordinate/text")
            if chunk.get("source_url") != doc["canonical_url"] or chunk.get("license") != doc["license"] or chunk.get("chunk_id") in seen_chunks:
                raise ValueError("chunk source identity/rights changed or duplicate chunk")
            seen_chunks.add(chunk["chunk_id"])
            context = f"[Research context: {assessment['study_type']}; population: {assessment['population_context']}; {assessment['study_context']}; limitations: {'; '.join(assessment['limitations'])}]"
            text = context + "\n" + chunk["text"]
            if len(text) > 4000 or len(text) < 10:
                omitted.append({"document_id": doc["id"], "chunk_id": chunk["chunk_id"], "reason": "runtime_text_length", "characters": len(text)})
                continue
            row = Reference(source_id=source["source_id"], title=doc["title"], url=doc["canonical_url"], publisher=assessment["publisher"],
                jurisdiction="Research context; not jurisdictional guidance", section=chunk["section"], section_id=chunk["coordinate"],
                source_date=assessment["publication_date"], retrieved_date=doc["retrieved_at"][:10], snapshot_id=doc["version"],
                text=text, topics=assessment["topic_names"], keywords=assessment["keywords"], source_type="teaching", permission_basis=basis)
            row.chunk_id = row.stable_id()
            if any(r.chunk_id == row.chunk_id for r in records):
                raise ValueError("duplicate runtime source coordinate identity")
            records.append(row)
            source["record_checksums"].append(row.content_hash())
            metadata[row.chunk_id] = {"subjects": doc.get("specialties", []), "material_type": "research", "study_type": assessment["study_type"],
                "study_context": context, "population_context": assessment["population_context"], "limitations": assessment["limitations"],
                "collector_document_id": doc["id"], "collector_coordinates": {"coordinate": chunk["coordinate"], "start": start, "end": end, "page": chunk.get("page"), "chunk_id": chunk["chunk_id"]},
                "collector_hashes": current, "attribution": doc["attribution"], "omissions": doc.get("exclusions", []),
                "source_review": "human_attested_not_credential_verified", "clinical_review": "pending", "faculty_review": "pending"}
        if source["record_checksums"]:
            sources.append(source)
    if not records:
        raise ValueError("no runtime-compatible source units; all selected units omitted")
    report = {"version": output.name, "records": len(records), "sources": len(sources), "omitted": omitted,
              "activation": "none", "index_built": False, "clinical_review": "pending_F03", "qualified_review_verified": False,
              "original_bytes_verification": "Only retained originals were verified; absent originals retain rights-manifest raw-hash provenance",
              "collector_bindings": input_hashes, "review_sha256": object_hash(review)}
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="mds-reviewed-stage-", dir=output.parent))
    (staging / "records.jsonl").write_text("\n".join(r.model_dump_json() for r in records) + "\n", encoding="utf-8")
    (staging / "sources.yaml").write_text(yaml.safe_dump({"sources": sources}, sort_keys=False, allow_unicode=True), encoding="utf-8")
    for name, value in (("metadata.json", {"chunks": metadata}), ("review-attestation.json", review), ("stage-report.json", report)):
        (staging / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    names = ("records.jsonl", "sources.yaml", "metadata.json", "review-attestation.json", "stage-report.json")
    manifest = {"schema_version": 1, "version": output.name, "records": len(records), "sources": len(sources),
                "files": {name: sha((staging / name).read_bytes()) for name in names}, "clinical_review": False, "faculty_review": "pending",
                "status": "inactive_human_attested_source_pack", "licenses": ["CC-BY-4.0"], "collector_bindings": input_hashes}
    (staging / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    store = TeachingStore(Settings(_env_file=None, enable_teaching=True, teaching_backend="lexical", teaching_release_path=staging, teaching_explanations_sha256=""))
    try:
        if store.error or len(store.records) != len(records):
            raise ValueError("existing TeachingStore rejected staged pack: " + str(store.error))
    finally:
        store.close()
    for name, checksum in input_hashes.items():
        if sha(safe_path(root, name).read_bytes()) != checksum:
            raise ValueError("collector changed during staging; temporary pack not activated")
    staging.rename(output)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["template", "stage"])
    parser.add_argument("--collector", type=Path, default=ROOT / "data/references/mds/open_corpus")
    parser.add_argument("--review", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "template":
        destination = args.output.resolve()
        if destination.is_relative_to(args.collector.resolve()) or destination.is_relative_to(ROOT / "data/references"):
            parser.error("template output must be outside collector and active reference releases")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as handle:
            json.dump(review_template(args.collector), handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    else:
        if args.review is None:
            parser.error("stage requires --review with real human attestations")
        try:
            print(json.dumps(stage(args.collector, json.loads(args.review.read_text(encoding="utf-8-sig")), args.output), indent=2))
        except (ValueError, OSError, KeyError, TypeError) as exc:
            print(json.dumps({"status": "preflight_rejected", "reason": str(exc), "activation": "none"}))
            raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
