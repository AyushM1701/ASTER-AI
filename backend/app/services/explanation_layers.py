"""Progressive explanation without relaxing source checks or dropping caveats."""

import hashlib
import json
import re
from functools import lru_cache

from backend.app.paths import install_root

LAYOUTS = install_root() / "configs/explanation_layouts.json"


def valid_layout(plan):
    """A layout may reorder whole sentences, never add or omit source text."""
    try:
        original = plan["original"]
        match = re.match(r"^(\[Research context:.*?\])\s*", original, re.S)
        context = match.group(1) if match else ""
        body = original[match.end() :] if match else original
        sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", body.strip())
        selected = plan["simple_sentence_indices"]
        return (
            bool(selected)
            and all(type(i) is int and 0 <= i < len(sentences) for i in selected)
            and len(set(selected)) == len(selected)
            and plan["text_sha256"] == hashlib.sha256(original.encode()).hexdigest()
            and plan["simple"] == " ".join(sentences[i] for i in selected)
            and plan["deeper"] == " ".join(s for i, s in enumerate(sentences) if i not in selected)
            and plan["context"] == context
        )
    except (KeyError, TypeError, ValueError, AttributeError):
        return False


@lru_cache(maxsize=1)
def load_layouts():
    try:
        data = json.loads(LAYOUTS.read_text(encoding="utf-8"))
        return {
            p["text_sha256"]: p
            for p in data["plans"]
            if p.get("review_status") == "developer_reviewed_presentation"
            and p.get("clinical_review") is False
            and valid_layout(p)
        }
    except (OSError, ValueError, KeyError, TypeError):
        return {}


def present_answer(result):
    """Add view metadata; preserve original claims, citations and warnings."""
    if result.get("patient_response") or result.get("component_answers") or result.get('comparison') or result.get('answer_review') or result.get('report_explanation'):
        return result
    if result.get("status") != "ok" or result.get("explanation_layers"):
        return result
    if result.get("route") not in {"medical_education", "document_explanation", "conversation"}:
        return result
    claims = result.get("claims", [])
    simple, deeper, context = [], [], []
    plans = load_layouts()
    sources = {c["chunk_id"]: c for c in result.get("citations", [])}
    for i, claim in enumerate(claims):
        body = claim["text"]
        plan = plans.get(hashlib.sha256(body.encode()).hexdigest())
        bound = (
            plan
            and plan["original"] == body
            and set(plan["citation_ids"]) == set(claim["citation_ids"])
        )

        def part(text):
            return {"text": text, "citation_ids": claim["citation_ids"], "claim_index": i}

        if bound:
            simple.append(part(plan["simple"]))
            if plan["deeper"]:
                deeper.append(part(plan["deeper"]))
            if plan["context"]:
                context.append(part(plan["context"]))
        else:
            # Existing brief patient-facing notes can be shown whole. Never
            # truncate a source to manufacture a simpler medical claim.
            brief = (
                len(body.split()) <= 90
                and claim["citation_ids"]
                and all(
                    sources.get(key, {}).get("source_type") in {"education", "drug_label"}
                    for key in claim["citation_ids"]
                )
                and not body.startswith("[Research context:")
            )
            (simple if brief else deeper).append(part(body))
    if not claims and result.get("answer"):
        # Uncited general responses remain explicitly unverified. Model fields
        # are policy-checked by AnswerService before reaching this presenter.
        simple.append({"text": result["answer"], "citation_ids": []})
        if result.get("deeper_explanation"):
            deeper.append({"text": result["deeper_explanation"], "citation_ids": []})
    if not simple and not deeper:
        return result
    return {
        **result,
        "explanation_layers": {
            "version": "simple-to-deep-v1",
            "simple": simple,
            "deeper": deeper,
            "context": context,
            "simple_notice": ""
            if simple
            else "A checked plain-language explanation is not available for this question yet. The supported reference detail follows.",
            "deeper_notice": ""
            if deeper
            else (
                "No further detail was returned for this answer."
                if result.get("route") == "conversation"
                else "That is the full supported explanation currently available. More detail would need additional checked material."
            ),
        },
    }
