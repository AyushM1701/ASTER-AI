"""Quarantined Kaggle candidate lookup. Never used as clinical RAG evidence."""

import hashlib
import json
from functools import lru_cache

from backend.app.config import ROOT
from backend.app.errors import SCOPE, envelope


@lru_cache(maxsize=1)
def load_candidates():
    audit = json.loads(
        (ROOT / "data/knowledge_v2/kaggle_catalogue_audit.json").read_text(encoding="utf-8")
    )
    artifact = audit["candidate_index"]
    path = (ROOT / artifact["path"]).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError("Candidate index outside workspace")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != artifact["sha256"]:
        raise ValueError("Candidate catalogue hash mismatch")
    data = json.loads(raw)
    if data["review_status"] != "unverified" or data["clinical_review"]:
        raise ValueError("Candidate catalogue status changed")
    return data


def lookup(name):
    try:
        data = load_candidates()
        # Preserve exact original spelling, spaces, strength and dosage form.
        rows = data["candidates"].get(name, [])
    except (OSError, ValueError, KeyError):
        return envelope(
            "insufficient_evidence",
            "medicine_catalogue",
            "The unverified candidate catalogue is unavailable.",
        )
    if not rows:
        return envelope(
            "insufficient_evidence",
            "medicine_catalogue",
            "No exact catalogue name matched. Include the complete catalogue name, strength and form; no spelling or brand equivalence is inferred.",
        )
    compositions = {(row[1], row[2]) for row in rows}
    snippets = [f"Row {r[0]}: reported composition fields: {r[1]!r}; {r[2]!r}." for r in rows[:5]]
    return envelope(
        "insufficient_evidence",
        "medicine_catalogue",
        "Unverified Indian medicine catalogue match. This does not confirm the product's ingredients or provide clinical advice.",
        answer=name + "\n" + "\n".join(snippets),
        answer_method="quarantined_catalogue",
        catalogue={
            "name": name,
            "rows": len(rows),
            "conflicting_compositions": len(compositions) > 1,
            "dataset": data["dataset"],
            "review_status": "unverified",
        },
        warnings=[
            "Dataset version 1 is from November 2022; upstream provenance and current availability are unverified.",
            "Only two short composition fields exist. Additional ingredients may be missing.",
        ],
        limitations=[
            SCOPE,
            "No fuzzy matching, alias promotion, substitution, dosing or clinical citations are supplied.",
            "Check the original package and an authoritative Indian product label with a pharmacist.",
        ],
    )
