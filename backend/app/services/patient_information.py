"""Bounded patient evidence contracts; these checks are not medical certification."""

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

from backend.app.errors import envelope
from backend.app.services.output_validation import INSTRUCTIONS
from backend.app.services.question_plan import plan_question
from backend.app.services.retrieval import Reference

ROLES = (
    "meaning",
    "possible_causes",
    "specific_context",
    "uncertainty",
    "professional_followup",
    "warning_signs",
)
OGL = "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/"


def utc_date():
    return datetime.now(timezone.utc).date()


class PatientInformationStore:
    """Small, separately permission-checked and versioned patient evidence set.

    Topic/operation/population gates replace score thresholds for this bounded
    collection. A metadata review is developer work, not independent medicine.
    """

    def __init__(self, path, enabled=True, clock=utc_date):
        self.root, self.enabled, self.clock = Path(path).resolve(), enabled, clock
        self.error, self.version, self.expires = None, None, None
        self.units, self.records, self.sources = [], {}, {}
        if not enabled:
            return
        try:
            manifest = json.loads((self.root / "manifest.json").read_text(encoding="utf-8"))
            required = {"records.jsonl", "sources.json", "units.json", "raw/terms.html"}
            if (
                not required <= set(manifest["files"])
                or manifest.get("clinical_review") is not False
            ):
                raise ValueError("Patient manifest incomplete or misleading review state")
            for name, checksum in manifest["files"].items():
                path = (self.root / name).resolve()
                if (
                    not path.is_relative_to(self.root)
                    or hashlib.sha256(path.read_bytes()).hexdigest() != checksum
                ):
                    raise ValueError("Patient artifact changed")
            terms = (self.root / "raw/terms.html").read_text(encoding="utf-8")
            if "Open Government Licence" not in terms:
                raise ValueError("Patient permission evidence missing")
            self.version = manifest["version"]
            copied = datetime.fromisoformat(manifest["copied_date"]).date()
            age = manifest["maximum_age_days"]
            if type(age) is not int or not 1 <= age <= 7 or copied > self.clock():
                raise ValueError("Invalid patient currency window")
            self.expires = copied + timedelta(days=age)
            sources = json.loads((self.root / "sources.json").read_text(encoding="utf-8"))[
                "sources"
            ]
            self.sources = {s["source_id"]: s for s in sources}
            if len(self.sources) != len(sources):
                raise ValueError("Duplicate patient source identity")
            for line in (self.root / "records.jsonl").read_text(encoding="utf-8").splitlines():
                record = Reference.model_validate_json(line)
                source = self.sources[record.source_id]
                basis = record.permission_basis
                raw = (self.root / source["raw_path"]).resolve()
                parsed = urlsplit(record.url)
                if (
                    record.chunk_id != record.stable_id()
                    or record.chunk_id in self.records
                    or record.source_type != "patient_information"
                    or record.clinical_review
                    or parsed.scheme != "https"
                    or parsed.hostname != "www.nhs.uk"
                    or not parsed.path.startswith(("/symptoms/", "/conditions/"))
                    or parsed.username
                    or parsed.password
                    or record.url != source["url"]
                    or not raw.is_relative_to(self.root)
                    or hashlib.sha256(raw.read_bytes()).hexdigest() != source["raw_sha256"]
                    or source["raw_path"] not in manifest["files"]
                    or basis != source["permission_basis"]
                    or basis.get("license") != "OGL-3.0"
                    or basis.get("type") != "open_license"
                    or basis.get("license_url") != OGL
                    or basis.get("snapshot_sha256") != source["raw_sha256"]
                    or basis.get("clinical_review") is not False
                    or source.get("clinical_review") is not False
                    or source["copied_date"] != manifest["copied_date"]
                ):
                    raise ValueError("Patient source identity/permission binding failed")
                self.records[record.chunk_id] = record
            document = json.loads((self.root / "units.json").read_text(encoding="utf-8"))
            seen = set()
            for unit in document["units"]:
                if (
                    unit["id"] in seen
                    or unit["audience"] != "patient"
                    or unit["intent"] != "symptom_information"
                    or unit["role"] not in ROLES
                    or unit["review_status"] != "developer_reviewed"
                    or unit["clinical_review"] is not False
                    or not unit["text"]
                    or len(unit["text"].split()) > 110
                    or INSTRUCTIONS.search(unit["text"])
                    or re.search(
                        r"\b(?:always harmless|never serious|definitely means|you have (?!questions))\b",
                        unit["text"],
                        re.I,
                    )
                    or unit["population"] not in {"all_ages", "adult", "child"}
                    or set(unit["citation_ids"]) != set(unit["source_hashes"])
                    or not unit["citation_ids"]
                ):
                    raise ValueError("Patient explanation review/contract invalid")
                for key, checksum in unit["source_hashes"].items():
                    if key not in self.records or self.records[key].content_hash() != checksum:
                        raise ValueError("Patient explanation source changed")
                unit["citation_bindings"] = {
                    key: self.records[key].citation() for key in unit["citation_ids"]
                }
                seen.add(unit["id"])
                self.units.append(unit)
        except (OSError, ValueError, KeyError, TypeError) as error:
            self.error = str(error)
            self.units, self.records, self.sources = [], {}, {}

    def current(self):
        return bool(
            self.enabled and not self.error and self.expires and self.clock() < self.expires
        )

    def manifest(self):
        return {
            "enabled": self.enabled,
            "version": self.version,
            "units": len(self.units),
            "sources": len(self.sources),
            "current": self.current(),
            "error": self.error,
            "expires": self.expires.isoformat() if self.expires else None,
            "clinical_review": False,
        }

    def applicable_units(self, plan):
        if not self.current():
            return []
        population = plan.patient_context.get("population")
        candidates = []
        for unit in self.units:
            if (
                unit["subject"] != plan.primary_subject
                or unit.get("conflict_status") != "clear"
                or unit["population"] not in {"all_ages", population}
            ):
                continue
            if unit["role"] == "specific_context" and (
                not plan.requested_information
                or not set(plan.requested_information) <= set(unit["facets"])
            ):
                continue
            candidates.append(unit)
        return candidates

    def answer(self, plan):
        if not self.current():
            return envelope(
                "insufficient_evidence",
                "medical_education",
                "Patient information is unavailable or needs a source refresh. I cannot substitute a teaching chapter for symptom guidance.",
                task_completion=False,
                missing_response_elements=plan.required_response_elements,
            )
        candidates = self.applicable_units(plan)
        selected = []
        for role in ROLES:
            if role == "specific_context" and not plan.requested_information:
                continue
            choices = [u for u in candidates if u["role"] == role]
            if choices:
                selected.append(choices[0])
        missing = set(plan.required_response_elements) - {u["role"] for u in selected}
        if not {"meaning", "uncertainty", "warning_signs"} <= {u["role"] for u in selected}:
            return envelope(
                "insufficient_evidence",
                "medical_education",
                "I do not have enough applicable patient information to explain this symptom safely. A qualified professional can assess it.",
                task_completion=False,
                missing_response_elements=sorted(missing),
            )
        # A general symptom card does not answer pregnancy/history-specific needs.
        special_context = [
            k
            for k in plan.patient_context
            if k not in {"explicit_statement", "population", "age_statement"}
        ]
        unsupported = ["Information specific to " + k.replace("_", " ") for k in special_context]
        claims = [{"text": u["text"], "citation_ids": u["citation_ids"]} for u in selected]
        used = {key for u in selected for key in u["citation_ids"]}
        citations, warnings = [], []
        for key in sorted(used):
            record = self.records[key]
            source = self.sources[record.source_id]
            citation = record.citation()
            citation.update(
                patient_subject=plan.primary_subject,
                original_publisher=record.publisher,
                copied_date=source["copied_date"],
                publisher_review_date=source["publisher_review_date"],
                original_attribution=source.get(
                    "original_attribution",
                    "Original source snapshot copied on " + source["copied_date"],
                ),
                next_review_due=source.get("next_review_due"),
                source_audience="patient",
                source_operation="symptom_information",
                formal_approval_of_adaptation=False,
                attribution="Contains public sector information licensed under the Open Government Licence v3.0.",
            )
            # Original, unchanged, dated source material remains separately
            # identified. Adapted Aster wording is not attributed as NHS advice.
            citations.append(citation)
            due = source.get("next_review_due")
            if due and datetime.fromisoformat(due).date() < self.clock():
                warnings.append(
                    "An original source is past its scheduled publisher review date; currency requires review."
                )
        return envelope(
            "partial" if missing or unsupported else "ok",
            "medical_education",
            "General symptom information",
            claims=claims,
            citations=citations,
            warnings=list(dict.fromkeys(warnings)),
            answer_method="prepared_patient_information",
            patient_version=self.version,
            patient_response={
                "version": "patient-symptom-v1",
                "subject": plan.primary_subject,
                "parts": [{"role": u["role"], "claim_index": i} for i, u in enumerate(selected)],
            },
            missing_response_elements=sorted(missing),
            unsupported_parts=unsupported,
            task_completion=not missing and not unsupported,
            clinical_review=False,
            limitations=[
                "General information cannot establish an individual diagnosis or choose treatment.",
                "Aster's adapted explanations have developer source comparison only; independent clinical review is pending.",
            ],
            reuse_notice="Contains public sector information licensed under the Open Government Licence v3.0.",
        )


def validate_patient_response(plan, result, reviewed_units):
    """Reject even verbatim evidence when it does not fulfill a symptom task."""
    components = result.get("component_answers", [])
    if components:
        if any(c["question"] not in plan.subquestions for c in components):
            return ["patient_component_scope"]
        flattened = [claim for c in components for claim in c["response"].get("claims", [])]
        if flattened != result.get("claims", []):
            return ["patient_component_binding"]
        return [
            reason
            for c in components
            if c["response"].get("status") in {"ok", "partial"}
            and plan_question(c["question"]).intent == "symptom_information"
            for reason in validate_patient_response(
                plan_question(c["question"]), c["response"], reviewed_units
            )
        ]
    presentation = result.get("patient_response")
    if not presentation or presentation.get("subject") != plan.primary_subject:
        return ["patient_subject_or_audience"]
    reasons, roles = [], set()
    claims = result.get("claims", [])
    parts = presentation.get("parts", [])
    citations = {c["chunk_id"]: c for c in result.get("citations", [])}
    if len(parts) != len(claims):
        reasons.append("patient_component_binding")
    for index, claim in enumerate(claims):
        unit = next(
            (
                u
                for u in reviewed_units
                if u.get("subject") == plan.primary_subject
                and u.get("intent") == "symptom_information"
                and u.get("audience") == "patient"
                and u.get("conflict_status") == "clear"
                and u.get("population") in {"all_ages", plan.patient_context.get("population")}
                and (
                    u.get("role") != "specific_context"
                    or set(plan.requested_information) <= set(u.get("facets", []))
                )
                and u.get("text") == claim.get("text")
                and set(u.get("citation_ids", [])) == set(claim.get("citation_ids", []))
            ),
            None,
        )
        if not unit:
            reasons.append("patient_inapplicable_evidence")
            continue
        for key, expected in unit.get("citation_bindings", {}).items():
            if key not in citations or any(
                citations[key].get(field) != value for field, value in expected.items()
            ):
                reasons.append("patient_source_binding")
        role = unit["role"]
        if (
            index >= len(parts)
            or parts[index].get("role") != role
            or parts[index].get("claim_index") != index
        ):
            reasons.append("patient_component_binding")
        roles.add(role)
    missing = set(plan.required_response_elements) - roles
    if missing and (
        result.get("status") != "partial"
        or not missing <= set(result.get("missing_response_elements", []))
    ):
        reasons.append("patient_incomplete_answer")
    if not {"uncertainty", "warning_signs"} <= roles:
        reasons.append("patient_missing_safety")
    if result.get("status") == "partial" and result.get("task_completion") is not False:
        reasons.append("patient_completion_mislabelled")
    if (
        any(
            k not in {"explicit_statement", "population", "age_statement"}
            for k in plan.patient_context
        )
        and result.get("status") == "ok"
    ):
        reasons.append("patient_context_unanswered")
    if result.get("explanation_layers"):
        reasons.append("patient_inappropriate_presentation")
    return sorted(set(reasons))
