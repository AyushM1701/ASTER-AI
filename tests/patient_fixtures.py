"""Synthetic, independently specified evidence for patient workflow tests."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from backend.app.services.retrieval import Reference

TEXTS = {
    "meaning": "Toothache means pain in or around a tooth.",
    "possible_causes": "Possible causes include decay, a cracked tooth, gum disease, infection or sensitivity.",
    "uncertainty": "The cause cannot be established from pain alone; this is general information, not a diagnosis.",
    "professional_followup": "Persistent tooth pain should be assessed by a dentist; pain when biting also needs dental assessment.",
    "warning_signs": "Swelling around the eye or neck, or mouth swelling with trouble breathing or swallowing, needs emergency assessment.",
    "specific_context": "Decay can cause sensitivity to hot or cold drinks; cold-triggered pain alone does not identify its cause.",
}


def patient_release(path, missing=(), conflict=False, population="all_ages"):
    path = Path(path)
    path.mkdir(parents=True)
    raw = path / "raw"
    raw.mkdir()
    today = datetime.now(timezone.utc).date().isoformat()
    text = "\n\n".join(TEXTS.values())
    (raw / "article.html").write_text("<main>" + text + "</main>", encoding="utf-8")
    (raw / "terms.html").write_text(
        "Open Government Licence v3.0, NHS website terms 3.3", encoding="utf-8"
    )
    raw_hash = hashlib.sha256((raw / "article.html").read_bytes()).hexdigest()
    record = Reference(
        source_id="synthetic-patient",
        title="Synthetic patient evidence fixture",
        url="https://www.nhs.uk/symptoms/toothache/",
        publisher="Synthetic engineering fixture",
        jurisdiction="UK",
        section="Patient symptom information",
        source_date=today,
        retrieved_date=today,
        snapshot_id="test-patient-v1",
        text=text,
        topics=["toothache"],
        keywords=["toothache", "pain"],
        source_type="patient_information",
        permission_basis={
            "type": "open_license",
            "license": "OGL-3.0",
            "license_url": "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/",
            "snapshot_sha256": raw_hash,
            "clinical_review": False,
        },
    )
    record.chunk_id = record.stable_id()
    (path / "records.jsonl").write_text(record.model_dump_json() + "\n", encoding="utf-8")
    units = [
        {
            "id": "test-" + role,
            "subject": "toothache",
            "audience": "patient",
            "intent": "symptom_information",
            "role": role,
            "text": content,
            "citation_ids": [record.chunk_id],
            "source_hashes": {record.chunk_id: record.content_hash()},
            "population": population,
            "facets": ["cold_trigger", "biting_pain", "gum_cause"]
            if role == "specific_context"
            else [],
            "review_status": "developer_reviewed",
            "clinical_review": False,
            "conflict_status": "unresolved" if conflict else "clear",
        }
        for role, content in TEXTS.items()
        if role not in missing
    ]
    (path / "units.json").write_text(json.dumps({"units": units}), encoding="utf-8")
    source = {
        "source_id": record.source_id,
        "url": record.url,
        "raw_path": "raw/article.html",
        "raw_sha256": raw_hash,
        "copied_date": today,
        "publisher_review_date": today,
        "next_review_due": None,
        "permission_basis": record.permission_basis,
        "authority": "synthetic fixture",
        "clinical_review": False,
    }
    (path / "sources.json").write_text(json.dumps({"sources": [source]}), encoding="utf-8")
    files = {
        str(p.relative_to(path)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in path.rglob("*")
        if p.is_file()
    }
    (path / "manifest.json").write_text(
        json.dumps(
            {
                "version": "test-patient-v1",
                "schema_version": 1,
                "files": files,
                "copied_date": today,
                "maximum_age_days": 7,
                "clinical_review": False,
            }
        ),
        encoding="utf-8",
    )
    return path
