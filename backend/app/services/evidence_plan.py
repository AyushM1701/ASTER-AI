"""Bounded applicability and facet evidence over Aster's existing retrieval.

Deterministic checks establish engineering support signals, not medical truth.
Source tags and section headings alone never establish facet completion.
"""

import hashlib
import re
from typing import Literal

from pydantic import Field

from backend.app.schemas import StrictModel
from backend.app.services.mds_curriculum import aliases, has_topic, topic_name
from backend.app.services.question_plan import RequestedFacet
from backend.app.services.teaching import canonical_teaching_text, teaching_terms

INJECTION = re.compile(r"\b(?:ignore|override|disregard)\b.{0,60}\b(?:instructions?|system|prompt|policy)\b|\b(?:reveal|print|exfiltrate)\b.{0,60}\b(?:system prompt|secrets?|private patient)\b", re.I)
FACET_SUPPORT = {
    "definition": r"\b(?:is|are|defined as|refers to|definition|consists of)\b",
    "classification": r"\b(?:classified|classification|types|categories|divided)\b",
    "layers": r"\b(?:layers?|strata|stratum|basal|suprabasal|granular|spinous)\b",
    "functions": r"\b(?:functions?|barrier|protect\w*|permits?|prevent\w*|absorp\w*|roles?|secreti\w*)\b",
    "structure": r"\b(?:structure|architecture|layers?|lining|cells|epithelial|stratified)\b",
    "anatomical_examples": r"\b(?:gingiva|palate|buccal|tongue|floor of (?:the )?mouth|located|sites?|locations?)\b",
    "clinical_features": r"\b(?:clinical|presents?|presentation|lesion|patients?|swelling|symptom\w*|asymptomatic|white patch)\b",
    "clinical_significance": r"\b(?:clinical (?:significance|implications?|relevance)|prognosis|malignant transformation)\b",
    "radiographic_features": r"\b(?:radiograph\w*|radiolucen\w*|radiopac\w*|imaging|unilocular|multilocular)\b",
    "histopathology": r"\b(?:histolog\w*|histopatholog\w*|microscop\w*|morpholog\w*|epithelial lining|caspases?|pyknosis|chromatin)\b",
    "intrinsic_pathway": r"\b(?:intrinsic|mitochondrial)\b",
    "extrinsic_pathway": r"\b(?:extrinsic|death receptor)\b",
    "molecular_features": r"\b(?:molecular|caspases?|BCL[ -]?2|BAX|cytochrome|proteins?|signall?ing)\b",
    "stages": r"\b(?:stages?|bud|cap|bell|initiation|sequence|sequential|step)\b",
    "epithelial_mesenchymal_interactions": r"\b(?:mesenchym\w*|reciprocal induction)\b",
    "relationship_to_dysplasia": r"\bdysplasia\b",
    "architectural_features": r"\b(?:architectural|stratification|rete|polarity|architecture)\b",
    "cytological_features": r"\b(?:cytolog\w*|pleomorph\w*|hyperchrom\w*|nuclear|mitoses|mitotic)\b",
    "grading_limitations": r"\b(?:grading|grade)\b.*\b(?:limit\w*|variab\w*|reliab\w*|subjectiv\w*|predict\w*|uncertain\w*)\b",
    "differential_diagnosis": r"\b(?:differential|distinguish\w*|differentiat\w*|mimic\w*|in contrast|whereas)\b",
    "investigations": r"\b(?:investigat\w*|biopsy|biopsies|diagnostic tests?|special stains?|immunohistochem\w*)\b",
    "mechanism": r"\b(?:mechanism|pathogenesis|pathway|trigger\w*|activat\w*|signall?ing|sequence)\b",
    "cellular_features": r"\b(?:cells?|cellular|shrink\w*|swell\w*)\b",
    "membrane_changes": r"\bmembrane\w*\b",
    "nuclear_changes": r"\b(?:nuclear|nucleus|nuclei|chromatin|pyknosis|karyorrhexis|karyolysis)\b",
    "inflammation": r"\binflammat\w*\b",
    "outcome": r"\b(?:outcome|repair|resolv\w*|clearance|removed|phagocyto\w*|death)\b",
    "diagnostic_limitations": r"\b(?:sensitiv\w*|specific\w*|false[ -](?:positive|negative)|limitations?|confound\w*|sampling|interpretation|uncertain\w*)\b",
    "biological_behavior": r"\b(?:aggressiv\w*|recurr\w*|metasta\w*|invas\w*|benign|malignan\w*|progress\w*)\b",
    "invasion": r"\b(?:invas\w*|basement membrane|infiltrat\w*|stromal|perineural)\b",
    "materials": r"\b(?:materials?|zirconia|ceramic|lithium disilicate|resin|cement|membranes?)\b",
    "clinical_tests": r"\b(?:sensibility|vitality|percussion|palpation|probing|cold test|electric pulp|clinical examination)\b",
    "management": r"\b(?:management|treatment|therap\w*|prevent\w*|rehabilitation|restoration)\b",
}


class EvidenceSpan(StrictModel):
    chunk_id: str
    snapshot_id: str
    section: str
    section_id: str | None = None
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    text_sha256: str
    source_sha256: str


class FacetEvidence(StrictModel):
    request: RequestedFacet
    state: Literal["supported", "missing", "contradictory"] = "missing"
    chunk_ids: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    evidence_role: str = "source_excerpt"
    candidate_count: int = Field(0, ge=0)


class EvidencePlan(StrictModel):
    version: Literal["1"] = "1"
    source_set_version: str | None = None
    facets: list[FacetEvidence] = Field(default_factory=list)
    rejected: list[dict] = Field(default_factory=list)
    clinical_review: Literal["pending"] = "pending"


def applicable_text(topic_id, text, section=""):
    from backend.app.services.retrieval import phrase_match

    body = canonical_teaching_text(re.sub(r"^\[Research context:.*?\]\s*", "", text, flags=re.S))
    if INJECTION.search(body):
        return False
    if any(phrase_match(canonical_teaching_text(alias), body) for alias in aliases(topic_id)):
        return True
    # A named section can resolve a repeated noun; global article keywords
    # cannot. Require entity vocabulary in the actual explanatory body too.
    vocabulary = teaching_terms(topic_name(topic_id))
    return has_topic(topic_id, canonical_teaching_text(section)) and bool(vocabulary & teaching_terms(body))


def supports_facet(facet, text, section=""):
    body = re.sub(r"^\[Research context:.*?\]\s*", "", text, flags=re.S)
    sentences = re.split(r"(?<=[.!?])\s+", body)
    topic_seen = False
    support = False
    coherent = True
    detail_pattern = r"[\s–—-]+".join(re.escape(word) for word in facet.facet.split("_"))
    pattern = FACET_SUPPORT.get(facet.facet, r"(?<!\w)" + detail_pattern + r"(?!\w)")
    for sentence in sentences:
        topical = applicable_text(facet.topic_id, sentence, section)
        inherited = topic_seen and bool(re.match(r"\s*(?:it|its|they|their|this|these|such)\b", sentence, re.I))
        # Whole-unit quotations must not export an unrelated sentence merely
        # because another sentence names the requested entity. Withhold mixed
        # units instead of cutting away possible qualifications or exceptions.
        if sentence.strip() and not (topical or inherited):
            coherent = False
        if (topical or inherited) and re.search(pattern, sentence, re.I | re.S):
            support = True
        topic_seen |= topical
    # No headings-as-proof: the facet marker and substantive text must be in
    # the body. An exact named entity or scoped section also has to apply.
    return (
        len(body.split()) >= 8
        and applicable_text(facet.topic_id, body, section)
        and support
        and coherent
        and (not facet.scope or all(word in teaching_terms(body + " " + section) for word in teaching_terms(facet.scope)))
    )


def structural_reasons(text, section=""):
    reasons = []
    if INJECTION.search(text):
        reasons.append("untrusted_instruction")
    if re.search(r"(?:^| / )(?:references|bibliography|acknowledgements?)(?:$| / )", section, re.I):
        reasons.append("bibliography_as_prose")
    if "\ufffd" in text or len(re.findall(r"[|~]", text)) > max(4, len(text) // 100):
        reasons.append("corrupted_extraction")
    if text.strip().endswith(("...", "…", "[truncated]")):
        reasons.append("truncated_passage")
    if re.search(r"\b(?:table \d+|comparison table)\b", text, re.I) and text.count("|") > 2 and not re.search(r"\b(?:feature|group|column|variable|parameter)\b", text, re.I):
        reasons.append("missing_table_headers")
    return reasons


def source_reasons(row, metadata):
    reasons = structural_reasons(row.text, row.section)
    if not isinstance(metadata, dict):
        return [*reasons, "invalid_source_metadata"]
    if metadata.get("runtime_policy") in {"exclude", "explanation_only"}:
        reasons.append("source_runtime_hold")
    for field, rejected in (("retraction_status", {"retracted", "expression_of_concern"}),
                            ("review_state", {"quarantined", "rejected"}),
                            ("extraction_quality", {"failed", "corrupted"})):
        value = metadata.get(field)
        if value is not None and not isinstance(value, str):
            reasons.append("invalid_source_metadata")
        elif value in rejected:
            reasons.append(field)
    if metadata.get("superseded_by") or metadata.get("stale"):
        reasons.append("stale_source_version")
    return reasons


def build_evidence_plan(plan, teacher, references, max_per_facet=2, *, candidate_limit=8):
    """Search entities independently; never run orphan facet queries."""
    if type(candidate_limit) is not int or not 1 <= candidate_limit <= 30:
        raise ValueError("Candidate retrieval limit must be between 1 and 30")
    evidence = EvidencePlan(source_set_version=getattr(teacher, "version", None))
    selected = {}
    metadata = getattr(teacher, "metadata", {})
    records_by_id = getattr(getattr(teacher, "references", None), "id_records", {})
    reviewed_candidates = {}
    for key, context in metadata.items():
        if not isinstance(context, dict) or key not in records_by_id:
            continue
        for field in ("reviewed_facet_bindings", "ai_inspected_facet_bindings"):
            entries = context.get(field, [])
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if isinstance(entry, dict) and all(isinstance(entry.get(k), str) for k in ("topic_id", "facet", "scope")):
                    signature = (entry["topic_id"], entry["facet"], entry["scope"])
                    reviewed_candidates.setdefault(signature, set()).add(key)
    for facet in plan.facets[:30]:
        found = FacetEvidence(request=facet)
        # Explicit bindings supply candidates, never approval: every candidate
        # still passes the same source, scope, integrity and hold checks below.
        candidates = [records_by_id[key] for key in sorted(reviewed_candidates.get((facet.topic_id, facet.facet, facet.scope), ()))]
        if teacher and getattr(teacher, "records", None):
            # Existing lexical/dense ranking stays responsible for candidate
            # retrieval. Phrase variants improve recall without adding a new
            # index or changing the installed collection.
            for alias in dict.fromkeys([facet.query, *aliases(facet.topic_id)]):
                for row in teacher.search(alias, limit=candidate_limit):
                    if row.chunk_id not in {r.chunk_id for r in candidates}:
                        candidates.append(row)
        elif references:
            candidates = references.search(topic_name(facet.topic_id))
        found.candidate_count = len({row.chunk_id for row in candidates})
        ranked = []
        seen = set()
        for row in candidates:
            context = metadata.get(row.chunk_id, {})
            from backend.app.services.reviewed_evidence import reviewed_support

            reviewed = reviewed_support(facet, row, context)
            reasons = source_reasons(row, context)
            if getattr(teacher, "review_flags", {}).get(row.chunk_id):
                reasons.append("source_review_hold")
            if not reviewed and not applicable_text(facet.topic_id, row.text, row.section):
                reasons.append("topic_not_in_supporting_text")
            if not reviewed and not supports_facet(facet, row.text, row.section):
                reasons.append("facet_not_supported")
            if len(row.text) > 4000:
                reasons.append("evidence_unit_exceeds_budget")
            if reasons:
                evidence.rejected.append({"chunk_id": row.chunk_id, "topic_id": facet.topic_id, "facet": facet.facet, "reason_codes": sorted(set(reasons))})
                continue
            signature = " ".join(row.text.casefold().split())
            if signature in seen:
                continue
            seen.add(signature)
            score = 2 if context.get("material_type") != "research" else 0
            score += 4 if reviewed else 0
            score += int(bool(re.search(FACET_SUPPORT.get(facet.facet, "(?!)"), row.section, re.I)))
            ranked.append((score, row))
        ranked.sort(key=lambda pair: (-pair[0], pair[1].chunk_id))
        ids = {r.chunk_id for _, r in ranked}
        conflict = any(set(metadata.get(key, {}).get("contradicts", [])) & ids for key in ids)
        if conflict:
            found.state = "contradictory"
            found.reason_codes = ["source_conflict_requires_review"]
            found.chunk_ids = sorted(ids)
        else:
            chosen = []
            # Diversity is by source/version, not only paragraph identity.
            for _, row in ranked:
                if len(chosen) >= max_per_facet:
                    break
                if row.source_id not in {r.source_id for r in chosen}:
                    chosen.append(row)
            if chosen:
                found.state = "supported"
                found.chunk_ids = [row.chunk_id for row in chosen]
                selected.update({row.chunk_id: row for row in chosen})
            else:
                found.reason_codes = ["no_applicable_source_span"]
        evidence.facets.append(found)
    return evidence, selected


def span_for(row):
    return EvidenceSpan(chunk_id=row.chunk_id, snapshot_id=row.snapshot_id, section=row.section,
                        section_id=row.section_id, start=0, end=len(row.text),
                        text_sha256=hashlib.sha256(row.text.encode()).hexdigest(),
                        source_sha256=hashlib.sha256(row.text.encode()).hexdigest()).model_dump()


def valid_span(mapping, claim, sources):
    span = mapping.get("span", {})
    source = sources.get(span.get("chunk_id"))
    if not source or span.get("chunk_id") not in claim.get("citation_ids", []):
        return False
    text = source.get("excerpt", "")
    start, end = span.get("start"), span.get("end")
    return (
        type(start) is int and type(end) is int and 0 <= start < end <= len(text)
        and text[start:end] == claim.get("text")
        and hashlib.sha256(text[start:end].encode()).hexdigest() == span.get("text_sha256")
        and hashlib.sha256(text.encode()).hexdigest() == span.get("source_sha256")
        and span.get("snapshot_id") == source.get("snapshot_id")
        and span.get("section") == source.get("section")
        and span.get("section_id") == source.get("section_id")
    )
