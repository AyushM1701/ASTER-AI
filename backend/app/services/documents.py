import re
import threading
from dataclasses import dataclass, field

from backend.app.errors import SCOPE, AppError, envelope
from backend.app.services.explanation_layers import present_answer
from backend.app.services.policy import check_policy

KINDS = [
    "medicine_name",
    "strength",
    "formulation",
    "route",
    "frequency",
    "duration",
    "instructions",
]
LABELS = {
    "medicine": "medicine_name",
    "medicine name": "medicine_name",
    "strength": "strength",
    "formulation": "formulation",
    "route": "route",
    "frequency": "frequency",
    "duration": "duration",
    "instructions": "instructions",
}


@dataclass
class Document:
    id: str
    image: object
    preview: bytes
    intent: str
    state: str = "uploaded"
    revision: int = 0
    confirmed_revision: int | None = None
    fields: list = field(default_factory=list)
    ocr: dict = field(default_factory=dict)
    explanation: dict | None = None
    source_sha256: str = ""
    classification: dict | None = None
    attachment_response: dict | None = None
    lock: threading.RLock = field(default_factory=threading.RLock)

    def response(self):
        return envelope(
            "needs_confirmation" if self.confirmed_revision is None else "ok",
            "document",
            "Compare every field with the original document.",
            document_id=self.id,
            state=self.state,
            revision=self.revision,
            confirmed_revision=self.confirmed_revision,
            fields=self.fields,
            raw_text=self.ocr.get("raw_text", ""),
            words=self.ocr.get("words", []),
            ocr_engine=self.ocr.get("engine"),
            handwriting_style=self.ocr.get("style"),
            intent=self.intent,
            warnings=self.ocr.get("warnings", [])
            + [
                "OCR can misread names, units and decimals. "
                "Leave anything you cannot verify unreadable."
            ],
        )


def parse_fields(raw_text, intent="prescription", *, provenance="tesseract"):
    if intent == "document":
        return [
            {
                "field_id": "document_text",
                "kind": "document_text",
                "raw_text": raw_text,
                "candidate_value": raw_text or None,
                "value": None,
                "status": "candidate" if raw_text else "unreadable",
                "provenance": provenance,
            }
        ]
    groups = []
    current = {}
    for line in raw_text.splitlines():
        match = re.match(r"\s*([A-Za-z ]+)\s*:\s*(.*)$", line)
        if match and match[1].strip().casefold() in LABELS:
            kind = LABELS[match[1].strip().casefold()]
            if kind == "medicine_name" and "medicine_name" in current:
                groups.append(current)
                current = {}
            value = match[2].strip()
            current[kind] = (
                None if re.search(r"\bunreadable\b", value, re.I) else value or None,
                line,
            )
        elif re.match(
            r"^\s*(?:[A-Za-z][A-Za-z -]{2,40})\s+\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml)\b", line, re.I
        ):
            match = re.match(
                r"^\s*([A-Za-z][A-Za-z -]{2,40}?)\s+(\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml))\b", line, re.I
            )
            if current:
                groups.append(current)
            current = {
                "medicine_name": (match[1], line),
                "strength": (match[2], line),
                "instructions": (line[match.end() :].strip() or None, line),
            }
    if current:
        groups.append(current)
    if not groups:
        groups = [{}]
    fields = []
    for index, group in enumerate(groups[:10], 1):
        for kind in KINDS:
            candidate, raw = group.get(kind, (None, ""))
            if candidate and re.search(r"\bunreadable\b", candidate, re.I):
                candidate = None
            fields.append(
                {
                    "field_id": f"medicine_{index}_{kind}",
                    "kind": kind,
                    "raw_text": raw,
                    "candidate_value": candidate,
                    "value": None,
                    "status": "candidate" if candidate else "unreadable",
                    "provenance": provenance,
                    "engine_score": None,
                    "bbox": None,
                }
            )
    return fields


def confirm(document, payload):
    if document.state not in {"needs_confirmation", "confirmed", "explained"}:
        raise AppError(409, "needs_confirmation", "Extract the document before confirmation.")
    if payload.expected_revision != document.revision:
        raise AppError(
            409,
            "needs_confirmation",
            "The document changed. Reload and confirm the current revision.",
        )
    provided = {f.field_id: f for f in payload.fields}
    expected = {f["field_id"] for f in document.fields}
    if len(provided) != len(payload.fields) or set(provided) != expected:
        raise AppError(422, "needs_confirmation", "Submit every current field exactly once.")
    for item in provided.values():
        if (
            item.status == "unreadable"
            and item.value is not None
            or item.status == "confirmed_by_user"
            and item.value is None
        ):
            raise AppError(
                422,
                "needs_confirmation",
                "Confirmed fields need a value; unreadable fields must be blank.",
            )
    for item in document.fields:
        correction = provided[item["field_id"]]
        item.update(
            value=correction.value, status=correction.status, provenance="user_confirmation"
        )
    document.revision += 1
    document.confirmed_revision = document.revision
    document.state = "confirmed"
    document.explanation = None
    return document.response()


def require_confirmation(document, expected_revision):
    if (
        document.confirmed_revision is None
        or document.confirmed_revision != document.revision
        or expected_revision != document.confirmed_revision
    ):
        raise AppError(
            409, "needs_confirmation", "Confirm the current document revision before explaining it."
        )


def explain(document, references):
    confirmed = [f for f in document.fields if f["status"] == "confirmed_by_user" and f["value"]]
    decision = check_policy(" ".join(f["value"] for f in confirmed))
    if decision:
        return decision
    evidence = []
    if document.intent == "document":
        text = " ".join(f["value"] for f in confirmed)
        evidence = references.search(text)
    else:
        groups = {}
        for f in confirmed:
            prefix = f["field_id"].rsplit("_" + f["kind"], 1)[0]
            groups.setdefault(prefix, {})[f["kind"]] = f["value"]
        for group in groups.values():
            name = group.get("medicine_name", "").casefold()
            matches = references.search(name, entity=name)
            # Require exact entity + applicable formulation and strength. Never
            # resolve aliases, brands, extended release, or unknown units by guessing.
            for ref in matches:
                formulation = group.get("formulation", "").casefold()
                strength = re.sub(r"\s+", "", group.get("strength", "").casefold())
                route = group.get("route", "").casefold()
                route = "oral" if route == "by mouth" else route
                if (
                    formulation
                    and strength
                    and route
                    and ref.applicable_product(name, formulation, strength, route)
                ):
                    evidence.append(ref)
    evidence = list({r.chunk_id: r for r in evidence}.values())[:5]
    fields = [
        {"field_id": f["field_id"], "kind": f["kind"], "value": f["value"], "status": f["status"]}
        for f in document.fields
    ]
    from backend.app.services.output_validation import finalize
    return present_answer(finalize("Explain the confirmed prescription without dosing instructions", envelope(
        "ok" if evidence else "insufficient_evidence",
        "document_explanation",
        "General reference information for the confirmed text."
        if evidence
        else "No exact applicable reference matched the confirmed fields. "
        "Ask a pharmacist or prescriber about missing or unclear information.",
        claims=[{"text": r.text, "citation_ids": [r.chunk_id]} for r in evidence],
        citations=[r.citation() for r in evidence],
        confirmed_fields=fields,
        document_id=document.id,
        revision=document.revision,
        answer_method="extractive",
        limitations=[
            SCOPE,
            "Confirmed text reflects your transcription, not medical approval.",
            "No timing, food requirements, duration, or dose changes are inferred.",
            "US reference labeling may not apply to a product in another jurisdiction.",
        ],
    )))
