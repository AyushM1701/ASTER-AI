"""Typed discovery registry. A catalog entry does not authorize ingestion."""

import hashlib
import re
from typing import Literal

from pydantic import Field

from research.data.governance import DatasetManifest

SourceClass = Literal["curriculum", "guideline_portal", "patient_education", "drug_label_service",
                      "drug_identity", "regulatory_catalogue", "terminology", "literature_metadata",
                      "article_repository", "imaging_dataset", "evaluation_dataset", "licensed_textbook"]
Action = Literal["read", "api_extract", "private_retrieval", "train", "redistribute_raw",
                 "redistribute_weights", "commercial"]
ROUTES = {
    "curriculum": {"curriculum_mapping"}, "guideline_portal": {"medical_explanation", "guideline_discovery"},
    "patient_education": {"medical_explanation", "patient_education"},
    "drug_label_service": {"medicine_explanation"}, "drug_identity": {"medicine_identity"},
    "regulatory_catalogue": {"medicine_identity"}, "terminology": {"term_resolution"},
    "literature_metadata": {"literature_discovery"}, "article_repository": {"research_evidence", "medical_explanation"},
    "imaging_dataset": {"imaging_research"}, "evaluation_dataset": {"evaluation"},
    "licensed_textbook": {"medical_explanation"},
}


class SourceItem(DatasetManifest):
    """One licensed item; inherited action check keeps research governance intact."""

    source_id: str
    source_class: SourceClass
    allowed_actions: list[Action] = Field(default_factory=list)
    jurisdiction: str | None = None
    item_version: str | None = None
    content_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    last_verified: str | None = None
    clinical_review_status: Literal["pending"] = "pending"
    patient_clinical_use_approved: Literal[False] = False

    def require_route(self, route, action):
        self.require_action(action)
        if route not in ROUTES[self.source_class]:
            raise ValueError("source class is not evidence for the requested route")


def classify(name, section):
    lower = name.casefold()
    if any(word in lower for word in ("mesh", "umls", "snomed", "icd-11", "glossary")):
        return "terminology"
    if "rxnorm" in lower:
        return "drug_identity"
    if any(word in lower for word in ("dailymed", "openfda", "drugs@fda")):
        return "drug_label_service"
    if section.startswith("8.") or "bookshelf" in lower:
        return "licensed_textbook"
    if section.startswith("7."):
        return "evaluation_dataset"
    if section.startswith(("5.1", "5.2")) and any(word in lower for word in ("dentex", "inredd", "toothfairy", "tl-pano", "chexpert", "mimic", "chestx", "rsna", "tcia", "medpix", "cancer imaging")):
        return "imaging_dataset"
    if "pmc" in lower and "pubmed /" not in lower:
        return "article_repository"
    if any(word in lower for word in ("pubmed", "crossref", "openalex", "doaj", "clinicaltrials", "cochrane")):
        return "literature_metadata"
    if any(word in lower for word in ("medlineplus", "nidcr", "mouthhealthy", "mayo", "nhs")):
        return "patient_education"
    if "regulation" in lower or "gazette" in lower or "syllabus" in lower:
        return "curriculum"
    if section.startswith("4."):
        return "regulatory_catalogue"
    if section.startswith("3.") and not section.startswith("3.1"):
        return "patient_education"
    return "guideline_portal"


def build_inventory(raw):
    """Retain repeated entries: the same portal may serve different specialties."""
    entries, specialties = [], []
    section = ""
    specialty = None
    for number, line in enumerate(raw.splitlines(), 1):
        if line.startswith(("## ", "### ")):
            section = line.lstrip("# ")
            specialty = section.split(" — ")[0] if re.match(r"S[1-9] — ", section) else None
            if specialty:
                specialties.append({"id": specialty, "name": section.split(" — ", 1)[1]})
        if not line.startswith("|") or not (section.startswith(tuple(f"{i}." for i in range(1, 9))) or specialty):
            continue
        cells = [part.strip() for part in line.strip("|").split("|")]
        if len(cells) < 3 or cells[0].startswith(("---", "Source", "Dataset", "Feed", "Major")):
            continue
        name = cells[0].replace("**", "")
        url = next((cell for cell in cells if cell.startswith("https://")), None)
        kind = classify(name, section)
        identity = hashlib.sha256((section + "\n" + line).encode()).hexdigest()[:16]
        manifest = DatasetManifest(name=name, source_url=url or "local:reference-to-resolve",
                                   not_acquired_reason="Discovery candidate; item-level rights and version not yet verified.")
        entries.append({"source_id": "inventory_" + identity, "name": name, "canonical_url": url,
                        "source_class": kind, "classification_status": "discovery_routing_only",
                        "specialty": specialty, "inventory_section": section, "inventory_line": number,
                        "original_cells": cells, "acquisition_state": "discovered", "acquired": False,
                        "clinical_review_status": "pending", "patient_clinical_use_approved": False,
                        "allowed_routes_after_item_clearance": sorted(ROUTES[kind]), "rights": manifest.model_dump()})
    return {"version": "aster-source-inventory-v1-2026-10-13",
            "inventory_sha256": hashlib.sha256(raw.encode()).hexdigest(),
            "national_curriculum_only": True, "entries": entries, "specialties": specialties,
            "meaning": "Discovery and acquisition routing only; no corpus, license or medical-readiness claim."}
