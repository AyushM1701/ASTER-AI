"""Temporary, authorized private paper excerpts with exact page/span identity."""

import hashlib
import json
import os
import re
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path

from backend.app.errors import AppError, envelope
from backend.app.services.evidence_plan import INJECTION, structural_reasons
from backend.app.services.policy import check_policy

SECTIONS = {
    "abstract": "Abstract", "methods": "Methods", "results": "Results", "limitations": "Limitations",
    "introduction": "Introduction", "discussion": "Discussion", "conclusions": "Conclusions",
}
HEADINGS = {"abstract": "abstract", "methods": "methods", "materials and methods": "methods",
            "methodology": "methods", "study design": "methods", "participants": "methods",
            "results": "results", "findings": "results", "limitations": "limitations",
            "study limitations": "limitations", "introduction": "introduction", "background": "introduction",
            "discussion": "discussion", "conclusion": "conclusions", "conclusions": "conclusions",
            "references": "excluded", "bibliography": "excluded", "acknowledgements": "excluded"}


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def extract_pdf(raw, settings):
    if not raw or len(raw) > settings.max_upload_bytes or not raw.startswith(b"%PDF-"):
        raise AppError(422, "unsupported_input", "Use a permitted PDF within the upload limit.")
    if getattr(sys, "frozen", False):
        raise AppError(503, "unsupported_input", "Private PDF parsing is unavailable in this packaged runtime; use the current source installation.")
    worker = Path(__file__).with_name("pdf_worker.py")
    try:
        result = subprocess.run([sys.executable, "-I", str(worker), str(settings.max_paper_pages), str(settings.max_paper_characters)],
                                input=raw, capture_output=True, timeout=settings.paper_parse_timeout_seconds,
                                check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0)
        if result.returncode or len(result.stdout) > 3_000_000:
            raise ValueError("parse_failed")
        parsed = json.loads(result.stdout)
        pages = parsed["pages"]
        if parsed.get("status") != "ok" or not isinstance(pages, list) or not pages or any(not isinstance(text, str) for text in pages):
            raise ValueError("invalid_parser_output")
        if len(pages) > settings.max_paper_pages or sum(map(len, pages)) > settings.max_paper_characters:
            raise ValueError("invalid_parser_output")
        return pages
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired):
        raise AppError(422, "quality_rejected", "The PDF could not be safely read within its limits. Use an unencrypted PDF with selectable text; no paper was saved.") from None


def requested_sections(question):
    selected = []
    patterns = {"abstract": r"\babstract\b", "methods": r"\b(?:methods?|methodology|participants?|population|study design|randomi[sz]ation)\b",
                "results": r"\b(?:results?|findings?|outcomes?|effect size|confidence intervals?)\b",
                "limitations": r"\b(?:limitations?|bias|biases|applicability|certainty)\b",
                "introduction": r"\b(?:introduction|background)\b", "discussion": r"\bdiscussion\b",
                "conclusions": r"\bconclusions?\b"}
    for name, pattern in patterns.items():
        if re.search(pattern, question, re.I):
            selected.append(name)
    if not selected and re.search(r"\b(?:apprais\w*|summari[sz]\w*|summary|review|paper|article)\b", question, re.I):
        selected = ["abstract", "methods", "results", "limitations"]
    return selected


@dataclass
class Paper:
    id: str
    pdf_sha256: str
    pages: list[str]
    authorized: bool = False
    revision: int = 1
    confirmed_revision: int | None = None
    cost: int = 0
    lock: threading.RLock = field(default_factory=threading.RLock)

    def wipe(self):
        self.pages.clear()
        self.authorized = False
        self.confirmed_revision = None

    def response(self):
        return envelope("ok" if self.confirmed_revision == self.revision else "needs_confirmation", "private_paper_review",
                        "Review extracted pages against your PDF. Confirmation records extraction, not medical approval.",
                        document_id=self.id, intent="paper", revision=self.revision, confirmed_revision=self.confirmed_revision,
                        pdf_sha256=self.pdf_sha256, pages=[{"page": number, "text": text, "text_sha256": sha(text)} for number, text in enumerate(self.pages, 1)],
                        permission="user_declared_private_analysis_only", shared_reuse=False,
                        warnings=["Reading order and tables can be wrong even in a text PDF. Missing text is not evidence of an absent study finding."])

    def require_confirmation(self, revision):
        if not self.authorized or not self.pages or self.confirmed_revision != self.revision or revision != self.revision:
            raise AppError(409, "needs_confirmation", "Review and confirm the current paper revision before analysis.")

    def confirm(self, revision):
        if revision != self.revision or not self.authorized or not self.pages:
            raise AppError(409, "needs_confirmation", "Reload the current paper revision.")
        self.revision += 1
        self.confirmed_revision = self.revision
        return self.response()

    def units(self):
        role = None
        for page, text in enumerate(self.pages, 1):
            started_on_page = False
            start = 0
            chunks = []
            for match in re.finditer(r"[^\n]+(?:\n|$)", text):
                line = match[0].strip()
                candidate = re.sub(r"^\d+(?:\.\d+)*[.\s]+", "", line).strip(" :.-").casefold()
                if candidate in HEADINGS:
                    if chunks and started_on_page:
                        end = match.start()
                        body = text[start:end].strip()
                        offset = start + len(text[start:end]) - len(text[start:end].lstrip())
                        yield page, role, offset, offset + len(body), body
                    chunks = []
                    role, start = HEADINGS[candidate], match.end()
                    started_on_page = True
                else:
                    if not chunks:
                        start = match.start()
                    chunks.append(line)
            # A section continuing onto another page can carry exceptions.
            # This first parser only exports sections closed on the same page,
            # or a final-page section beginning on that page; no fragments.
            if chunks and started_on_page and page == len(self.pages):
                body = text[start:].strip()
                offset = start + len(text[start:]) - len(text[start:].lstrip())
                yield page, role, offset, offset + len(body), body

    def excerpts(self, question):
        from backend.app.services.output_validation import INSTRUCTIONS
        from backend.app.services.teaching import safe_source_text_uncached

        self.require_confirmation(self.revision)
        decision = check_policy(question)
        if decision:
            return decision
        from backend.app.services.question_plan import plan_question

        if plan_question(question, "research").intent == "symptom_information":
            return envelope("unsupported_input", "private_paper_analysis", "Use general patient information outside paper analysis for symptom questions.", task_completion=False)
        requested = requested_sections(question)
        claims, citations, evidence, sections = [], [], [], []
        for name in requested:
            indices = []
            for page, role, start, end, body in self.units():
                if role != name or len(body.split()) < 8 or len(body) > 4000 or structural_reasons(body) or INJECTION.search(body) or INSTRUCTIONS.search(body) or not safe_source_text_uncached(body):
                    continue
                if len(claims) >= 12 or len(indices) >= 2:
                    break
                key = "paper_chunk_" + sha(f"{self.id}:{self.revision}:{page}:{start}:{end}:{body}")[:24]
                indices.append(len(claims))
                claims.append({"text": body, "citation_ids": [key]})
                citations.append({"chunk_id": key, "source_id": self.id, "title": f"Private paper — page {page}",
                                  "url": f"aster-private://{self.id}/page/{page}", "publisher": "User-provided private paper",
                                  "section": SECTIONS[name], "snapshot_id": f"{self.id}:revision:{self.revision}", "source_type": "private_paper",
                                  "pdf_sha256": self.pdf_sha256, "page_sha256": sha(self.pages[page - 1]), "page": page,
                                  "excerpt": body, "permission_basis": {"type": "user_declared_private_analysis", "shared_reuse": False}, "clinical_review": False})
                evidence.append({"claim_index": len(claims) - 1, "document_id": self.id, "revision": self.revision, "page": page,
                                 "start": start, "end": end, "text_sha256": sha(body), "page_sha256": sha(self.pages[page - 1]),
                                 "pdf_sha256": self.pdf_sha256, "requested_section": name})
            sections.append({"heading": SECTIONS[name] + " excerpt", "section": name, "claim_indices": indices,
                             "state": "excerpt_available" if indices else "not_extracted_or_unsafe"})
        return envelope("partial" if claims else "insufficient_evidence", "private_paper_analysis",
                        "Exact excerpts from your confirmed paper. Critical appraisal and missing findings still need source review." if claims else "No safe, bounded excerpt was extracted for the requested paper sections.",
                        claims=claims, citations=citations, paper_evidence=evidence, paper_sections=sections,
                        context_id=self.id, context_revision=self.revision, answer_method="private_document_exact_extraction",
                        coverage_status="partial" if claims else "insufficient_evidence", task_completion=False,
                        missing_response_elements=[part["section"] for part in sections if not part["claim_indices"]],
                        appraisal_checklist=["Check study design, allocation, confounding, attrition, precision and applicability in the original.",
                                             "A section excerpt does not establish study quality, causal inference or evidence certainty."],
                        clinical_review=False, clinical_review_status="pending", independent_appraisal="not_performed",
                        limitations=["Private analysis only; no shared index, model training or public literature request.",
                                     "Extraction can misorder columns or tables. No missing study finding is inferred.",
                                     "No model-generated medical paraphrase or complete critical-appraisal claim."])


def validate_paper_result(question, result, paper):
    """Out-of-band trusted pages authorize exact excerpts, never supplied flags."""
    paper.require_confirmation(paper.revision)
    expected = paper.excerpts(question)
    fields = ("claims", "citations", "paper_evidence", "paper_sections", "context_id", "context_revision")
    valid = all(result.get(name) == expected.get(name) for name in fields)
    valid = valid and not result.get("answer") and not result.get("deeper_explanation") and not result.get("findings")
    if not valid:
        return envelope("insufficient_evidence", "private_paper_analysis", "The paper answer did not pass exact document and source-span checks.",
                        rejection_codes=["private_paper_identity_or_span_changed"], task_completion=False, coverage_status="insufficient_evidence")
    checked = dict(expected)
    checked.update(clinical_review=False, clinical_review_status="pending", task_completion=False,
                   validation={"reference_integrity": "passed" if expected.get("claims") else "unknown",
                               "source_support": "exact_confirmed_document_excerpt; not_independently_measured",
                               "document_scope": "current_confirmed_revision", "clinical_review": "pending"},
                   facet_diagnostics=[])
    return checked
