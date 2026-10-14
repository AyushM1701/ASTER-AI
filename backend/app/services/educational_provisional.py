"""Separate model-memory education from verified claims and coverage accounting."""

import json
import re
from functools import lru_cache

from backend.app.paths import install_root
from backend.app.services.policy import check_policy

NOTICE = "General model knowledge — not source verified"
LIMITATION = ("This provisional explanation may contain errors or outdated information. "
              "Check an authoritative reference. It does not establish source coverage or clinical approval.")
EDUCATIONAL_OPERATIONS = set((
    "what is are does mean explain define describe discuss compare contrast differentiate between and or versus vs "
    "the a an of in for to with from on about including their its how why when "
    "basic basics general detailed detail simple simply concise briefly introduction overview understanding "
    "definition definitions mechanisms mechanism causes cause cellular nuclear changes features functions function "
    "structure histology histological classification classifications types differences similarities biology "
    "pathogenesis pathophysiology development stages role roles physiological physiology morphology "
    "inflammation inflammatory responses response membrane significance examples educational essay short long "
    "answer notes mds mbbs marks associated related compare explain"
).split())
# Concept names only: this vocabulary is not biomedical source evidence.
GENERAL_CONCEPTS = ("asthma", "diabetes", "anemia", "anaemia", "hypertension", "blood pressure",
                    "heart", "kidney", "liver", "lung", "lungs", "skin", "brain", "neuron",
                    "neurons", "immune system", "immunity", "homeostasis", "metabolism", "genetics",
                    "mitosis", "meiosis", "DNA", "RNA", "proteins", "enzymes", "gingival fibroblasts")


@lru_cache(maxsize=1)
def educational_names():
    from backend.app.services.mds_curriculum import TOPICS, aliases

    names = {*GENERAL_CONCEPTS, *(alias for topic in TOPICS for alias in aliases(topic))}
    path = install_root() / "configs/all_mds_topics.json"
    try:
        registry = json.loads(path.read_text(encoding="utf-8"))
        names.update(topic["title"] for specialty in registry["specialties"] for topic in specialty["topics"])
    except (OSError, ValueError, KeyError, TypeError):
        pass  # Missing optional vocabulary never expands eligibility.
    return tuple(sorted(names, key=len, reverse=True))


def educational_subjects_only(question):
    """Do not let one recognized concept hide an unknown brand or extra intent."""
    remainder = question.casefold()
    found = False
    for name in educational_names():
        remainder, count = re.subn(r"\b" + re.escape(name.casefold()) + r"\b", " ", remainder)
        found = found or count > 0
    return found and set(re.findall(r"[a-z]+", remainder)) <= EDUCATIONAL_OPERATIONS
# This route is intentionally narrower than source-backed education. In
# particular, a study label cannot turn a personal care question into education.
EXCLUDED = re.compile(
    r"\b(?:my|mine|our|your|his|her|their|I|me|we|you|patient|patients|child|baby|pregnan\w*|"
    r"dos(?:e|es|age|ing)|prescri\w*|medicines?|medications?|drugs?|brands?|tablets?|capsules?|"
    r"antibiotics?|contraindications?|interactions?|treatments?|treat|therap(?:y|ies)|management|"
    r"procedures?|operative|surgical|surger(?:y|ies)|protocols?|regimens?|diagnos\w*|"
    r"xrays?|radiographs?|CBCT|scans?|images?|reports?|papers?|study results|trials?|latest|current|"
    r"guidelines?|recommendations?|ignore|override|system|prompt|instructions|use|using|interpret)\b|x[ -]rays?|"
    r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|ml|kg)\b|https?://",
    re.I,
)


def eligible(question, plan, result):
    return bool(
        not check_policy(question) and not EXCLUDED.search(question)
        and not plan.individualized_advice_requested and not plan.needs_clarification
        and not plan.is_fictional_case and not plan.patient_context
        and plan.audience != "research"
        and plan.intent in {"concept_explanation", "mechanism", "comparison"}
        and plan.task in {"explain", "definition", "mechanism", "compare", "essay", "histology", "classification"}
        and educational_subjects_only(question)
        and result.get("status") in {"insufficient_evidence", "partial"}
        and result.get("route") == "medical_education"
        and not result.get("rejection_codes") and not result.get("model_failure")
        and not result.get("context_id")
    )


def checked_text(text):
    from backend.app.services.answers import validate_conversation
    from backend.app.services.output_validation import INSTRUCTIONS
    from backend.app.services.teaching import safe_source_text_uncached

    text = text.strip()
    # Model citations are never treated as references. Reject the entire draft,
    # rather than trimming qualifications or trying to repair medical content.
    if not 20 <= len(text) <= 6000 or INSTRUCTIONS.search(text) or not safe_source_text_uncached(text):
        return None
    if re.search(r"https?://|www\.|\b(?:PMID|PMCID|doi|references|citations|guidelines?|"
                 r"prescri\w*|dos(?:e|es|age|ing)|medications?|antibiotics?|tablets?|capsules?|"
                 r"regimen|treatments?|therapy|therapies|recommend|administer|inject|dispense)\b|"
                 r"\b\w+(?:cillin|cycline|mycin|statin|pril|sartan|mab)\b|"
                 r"\b(?:start|stop|take|give|continue|apply|use|avoid)\b.{0,65}\b(?:taking|medicine|drug|daily|pain|bleeding|wound)\b|"
                 r"\b(?:reviewed|validated|approved|verified|endorsed)\s+by\b|"
                 r"\b(?:according to|studies show|research proves|clinically proven)\b|"
                 r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|ml|tablets?|capsules?)\b|\[\d+\]|"
                 r"\b(?:no need to|do not need to|don't need to)\s+(?:see|consult|visit)|"
                 r"\b(?:ignore|override|reveal)\b.{0,60}\b(?:instructions|system|prompt)\b", text, re.I):
        return None
    validate_conversation(text)
    return text


def attach(result, text):
    # No claims, citation IDs, source-support or completion flags are added.
    result["provisional_explanation"] = {
        "text": text, "evidence_state": "model_unverified", "label": NOTICE,
        "limitations": LIMITATION, "clinical_review_status": "pending",
        "citation_ids": [], "counts_toward_source_coverage": False,
    }
    result["provisional_status"] = "displayed"
    result["message"] = ("The available sources do not cover every requested part. "
                         "A provisional educational explanation follows.")
    return result
