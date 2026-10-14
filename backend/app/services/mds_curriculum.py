"""Versioned curriculum vocabulary; declared scope is distinct from readiness.

Names and relationships guide retrieval, never supply biomedical answer text.
National base references are scope-only; their full text is not bundled here.
"""

import hashlib
import json
import re
from functools import lru_cache

from backend.app.paths import install_root
from backend.app.services.retrieval import phrase_match

VERSION = "aster-mds-national-v1-2026-10-11"
NATIONAL_REGISTER = install_root() / "configs/mds_full_curriculum.json"
PROVENANCE = {
    "base": "https://dciindia.gov.in/Rule_Regulation/MDS_Course_Regulations_2017.pdf",
    "base_year": 2017,
    "base_status": "official_base_verified",
    "regulator_listing": "https://dciindia.gov.in/GazetteList.aspx",
    "listing_checked": "2026-10-11",
    "amendments": [
        {"year": 2018, "number": 1, "status": "listed_full_text_reconciliation_pending"},
        {"year": 2018, "number": 2, "status": "listed_full_text_reconciliation_pending"},
        {"year": 2019, "number": 3, "status": "listed_full_text_reconciliation_pending"},
    ],
    "current_consolidated_status": "pending_amendment_reconciliation",
    "university_overlay": "not_requested_national_only",
    "rights": "scope_and_citation_only_no_full_text_export",
}
FAMILIES = {
    "oral_dental_histology": "Oral and dental histology and development",
    "general_pathology": "Cell and general pathology",
    "developmental_abnormalities": "Developmental abnormalities",
    "mucosal_disorders": "Oral mucosal disorders and infections",
    "oral_cancer": "Oral cancer and epithelial dysplasia",
    "odontogenic_lesions": "Odontogenic cysts and tumours",
    "salivary_disorders": "Salivary gland disorders and tumours",
    "bone_soft_tissue": "Bone and soft tissue lesions",
    "oral_microbiology": "Dental disease and oral microbiology",
    "systemic_oral_disease": "Oral systemic disease and orofacial pain",
    "laboratory_diagnosis": "Histotechnology and laboratory diagnosis",
    "forensic_research": "Forensic odontology and research methods",
}
SPECIALTIES = {
    "oral_pathology": "Oral and Maxillofacial Pathology and Oral Microbiology",
    "oral_medicine": "Oral Medicine and Radiology",
    "oral_surgery": "Oral and Maxillofacial Surgery",
    "endodontics": "Conservative Dentistry and Endodontics",
    "prosthodontics": "Prosthodontics and Crown & Bridge",
    "periodontology": "Periodontology",
    "orthodontics": "Orthodontics and Dentofacial Orthopaedics",
    "pediatric_dentistry": "Pediatric and Preventive Dentistry",
    "public_health": "Public Health Dentistry",
}

# A vocabulary, not a prepared answer bank. Additional entities use scoped
# local IDs and remain provisional until added to this versioned registry.
TOPICS = {
    "oral_epithelium": ("oral epithelium", "oral_dental_histology", ["oral epithelial", "oral mucosal epithelium"]),
    "keratinized_epithelium": ("keratinized epithelium", "oral_dental_histology", ["keratinised epithelium"]),
    "nonkeratinized_epithelium": ("non-keratinized epithelium", "oral_dental_histology", ["nonkeratinized epithelium", "non-keratinised epithelium", "nonkeratinised epithelium"]),
    "sulcular_epithelium": ("sulcular epithelium", "oral_dental_histology", []),
    "junctional_epithelium": ("junctional epithelium", "oral_dental_histology", ["JE"]),
    "apoptosis": ("apoptosis", "general_pathology", ["apoptotic cell death", "apoptotic pathway", "apoptotic pathways"]),
    "necrosis": ("necrosis", "general_pathology", ["necrotic cell death"]),
    "tooth_development": ("tooth development", "oral_dental_histology", ["odontogenesis", "dental development"]),
    "oral_leukoplakia": ("oral leukoplakia", "mucosal_disorders", ["leukoplakia"]),
    "oral_epithelial_dysplasia": ("oral epithelial dysplasia", "oral_cancer", ["OED", "oral dysplasia", "epithelial dysplasia"]),
    "odontogenic_keratocyst": ("odontogenic keratocyst", "odontogenic_lesions", ["OKC", "keratocystic odontogenic tumour", "keratocystic odontogenic tumor"]),
    "dentigerous_cyst": ("dentigerous cyst", "odontogenic_lesions", []),
    "radicular_cyst": ("radicular cyst", "odontogenic_lesions", []),
    "ameloblastoma": ("ameloblastoma", "odontogenic_lesions", []),
    "amelogenesis": ("amelogenesis", "oral_dental_histology", []),
    "salivary_glands": ("salivary glands", "salivary_disorders", ["salivary gland"]),
    "pleomorphic_adenoma": ("pleomorphic adenoma", "salivary_disorders", []),
    "craniofacial_development": ("craniofacial development", "developmental_abnormalities", ["craniofacial abnormalities"]),
    "fibrous_dysplasia": ("fibrous dysplasia", "bone_soft_tissue", []),
    "dental_caries": ("dental caries", "oral_microbiology", ["tooth decay"]),
    "oral_biofilm": ("oral biofilm", "oral_microbiology", ["dental biofilm", "oral microbiome"]),
    "orofacial_pain": ("orofacial pain", "systemic_oral_disease", []),
    "immunohistochemistry": ("immunohistochemistry", "laboratory_diagnosis", ["IHC"]),
    "forensic_odontology": ("forensic odontology", "forensic_research", []),
    "biostatistics": ("biostatistics", "forensic_research", ["research methods"]),
}


def topic_name(identity):
    return TOPICS[identity][0] if identity in TOPICS else identity.removeprefix("local:").replace("_", " ")


def aliases(identity):
    if identity in TOPICS:
        name, _, synonyms = TOPICS[identity]
        return [name, *synonyms]
    return [topic_name(identity)]


@lru_cache(maxsize=4096)
def resolve_topics(text):
    hits = []
    for identity in TOPICS:
        for alias in aliases(identity):
            for match in re.finditer(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", text, re.I):
                hits.append((match.start(), match.end(), identity))
    hits.sort(key=lambda h: (h[0], -(h[1] - h[0])))
    selected = []
    for hit in hits:
        if any(start <= hit[0] and hit[1] <= end for start, end, _ in selected):
            continue
        selected.append(hit)
    return list(dict.fromkeys(identity for _, _, identity in selected))


def registry():
    register = national_scope()
    family_facets = {
        "oral_dental_histology": ["definition", "structure", "layers", "functions", "stages", "anatomical_examples"],
        "general_pathology": ["definition", "classification", "mechanism", "histopathology"],
        "laboratory_diagnosis": ["definition", "investigations", "mechanism", "grading_limitations"],
        "forensic_research": ["definition", "classification", "investigations", "grading_limitations"],
    }
    return {
        "version": VERSION,
        "curriculum": PROVENANCE,
        "specialties": SPECIALTIES,
        "families": FAMILIES,
        "mapping_status": "provisional_family_map_over_verified_national_base",
        "national_assessment_register": {k: v for k, v in register.items() if k != "items"},
        "topics": [
            {"id": identity, "canonical_name": name, "synonyms": synonyms,
             "family": family, "audience": "mds_student",
             "facets": family_facets.get(family, ["definition", "classification", "clinical_features", "histopathology", "differential_diagnosis", "investigations"]),
             "curriculum_topic_ids": curriculum_ids(identity, register["items"]),
             "curriculum_mapping_status": "scope_association_not_competence",
             "relationships": [family], "source_set_version": None,
             "source_review": "pending", "qualified_clinical_review": "pending",
             "ready_tasks": [], "declared_tasks": ["definition", "mechanism", "compare", "essay", "histology", "viva", "fictional_case", "research"],
             "limitations": ["A registry name does not establish evidence coverage."]}
            for identity, (name, family, synonyms) in TOPICS.items()
        ],
    }


def national_scope():
    """Reuse and integrity-check the project's existing amendment register."""
    root = install_root().resolve()
    try:
        raw = NATIONAL_REGISTER.read_bytes()
        document = json.loads(raw)
        checks = []
        for source in document["sources"]:
            if not source["id"].startswith("dci-mds"):
                continue
            path = (root / source["path"]).resolve()
            valid = path.is_relative_to(root) and path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"]
            checks.append({"id": source["id"], "url": source["url"], "sha256": source["sha256"], "snapshot_valid": valid, "role": source.get("role"), "retrieved_on": source.get("retrieved_on")})
        verified = sum(c["snapshot_valid"] for c in checks)
        return {"version": document["version"], "manifest_sha256": hashlib.sha256(raw).hexdigest(),
                "verified_snapshot_count": verified, "sources": checks,
                "integrity_status": "verified_snapshots" if checks and verified == len(checks) else "unavailable_or_changed",
                "assessment_item_count": len(document["items"]),
                "current_currency": "2026_listing_checked_complete_amendment_reconciliation_pending",
                "items": document["items"] if checks and verified == len(checks) else []}
    except (OSError, ValueError, KeyError, TypeError):
        return {"verified_snapshot_count": 0, "integrity_status": "unavailable_or_changed", "items": [], "sources": []}


def curriculum_ids(identity, items):
    matches = [item["id"] for item in items if any(phrase_match(alias, item.get("title", "")) for alias in aliases(identity))]
    if not matches:
        # Broad official syllabus headings are associated explicitly, without
        # inventing a one-to-one competency or an updated official topic ID.
        family = TOPICS[identity][1]
        section = {"oral_dental_histology": "histology", "general_pathology": "general pathology",
                   "odontogenic_lesions": "cysts", "oral_microbiology": "microbiology",
                   "oral_cancer": "neoplas", "laboratory_diagnosis": "laboratory",
                   "forensic_research": "research", "mucosal_disorders": "mucosal"}.get(family, "oral")
        matches = [item["id"] for item in items if section in (item.get("subject", "") + " " + item.get("title", "")).casefold()][:8]
    return matches


def has_topic(identity, text):
    return any(phrase_match(alias, text) for alias in aliases(identity))
