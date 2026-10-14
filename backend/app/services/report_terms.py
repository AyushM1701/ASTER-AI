"""Two-term, separately tested plain-text glossary. No numerical interpretation.

Short quotations inspected on MedlinePlus 11 October 2026. No whole-page
reuse permission is asserted. These are not reviewed diagnostic instructions.
"""

import hashlib
import re

from backend.app.errors import envelope

GLOSSARY = {
    "hemoglobin": {
        "aliases": {"hemoglobin", "haemoglobin", "hb", "hgb"},
        "quote": "A hemoglobin test measures the levels of hemoglobin in your blood. Hemoglobin is an iron-rich protein in your red blood cells.",
        "url": "https://medlineplus.gov/lab-tests/hemoglobin-test/",
        "title": "Hemoglobin Test",
    },
    "glucose": {
        "aliases": {
            "glucose",
            "blood glucose",
            "blood sugar",
            "fasting blood sugar",
            "random blood sugar",
            "fbs",
            "rbs",
        },
        "quote": "A blood glucose test measures the glucose levels in your blood. Glucose is a type of sugar.",
        "url": "https://medlineplus.gov/lab-tests/blood-glucose-test/",
        "title": "Blood Glucose Test",
    },
}


def explain_report(question):
    match = re.fullmatch(
        r"(?:explain|help me understand) (?:this|my) (?:(?:blood|lab|laboratory) )?report:\s*(.+)",
        question,
        re.I | re.S,
    )
    if not match:
        return None
    lines = [line.strip() for line in re.split(r"[;\n]+", match[1]) if line.strip()]
    if len(lines) > 20:
        return envelope(
            "unsupported_input",
            "medical_education",
            "Use up to 20 report lines. Only hemoglobin and glucose terminology is covered.",
            task_completion=False,
        )
    claims, citations, terms, unsupported = [], [], [], []
    for line in lines:
        label = line.split(":", 1)[0].strip().casefold()
        item = next(
            ((key, note) for key, note in GLOSSARY.items() if label in note["aliases"]), None
        )
        if not item:
            unsupported.append(line)
            continue
        key, note = item
        source_id = "report-terms-v1:" + key
        index = next((i for i, c in enumerate(claims) if c["citation_ids"] == [source_id]), None)
        if index is None:
            index = len(claims)
            claims.append({"text": note["quote"], "citation_ids": [source_id]})
            citations.append(
                dict(
                    chunk_id=source_id,
                    title=note["title"],
                    url=note["url"],
                    excerpt=note["quote"],
                    publisher="NIH / NLM MedlinePlus",
                    jurisdiction="US",
                    source_type="education",
                    source_date=None,
                    retrieved_date="2026-10-11",
                    snapshot_id="report-terms-v1-2026-10-11",
                    text_sha256=hashlib.sha256(note["quote"].encode()).hexdigest(),
                    review_status="developer_source_compared_clinical_review_pending",
                    reuse="Short quotation only; no full-page reuse license asserted.",
                )
            )
        terms.append({"label": label, "claim_index": index})
    return envelope(
        "partial" if unsupported and claims else "ok" if claims else "insufficient_evidence",
        "medical_education",
        "I can explain these terms. The numbers and laboratory flags have not been interpreted.",
        claims=claims,
        citations=citations,
        unsupported_parts=unsupported,
        task_completion=bool(claims) and not unsupported,
        report_explanation={
            "scope": "terminology_only",
            "terms": terms,
            "values_interpreted": False,
            "limitations": "Interpreting your results needs the laboratory ranges, units, circumstances and a clinician. This glossary does not determine normality, diagnosis or treatment.",
        },
    )
