import re

from backend.app.errors import SCOPE, AppError, envelope
from backend.app.services.explanation_layers import present_answer
from backend.app.services.policy import check_policy
from backend.app.services.secondary_references import SECONDARY_NOTICE


def explicit_nonmedical(question):
    return bool(
        re.fullmatch(
            r"(?:hello|hi|thanks|thank you|tell me a joke|write a poem(?: about nature)?|"
            r"(?:explain|what is|what are|tell me about) (?:quantum entanglement|"
            r"programming|python|javascript|html|css|arithmetic|algebra|grammar|"
            r"geography|computer science)|[\d\s+*/().=-]+)[.!?\s]*",
            question,
            re.I,
        )
    )


def validate_generated(answer, evidence, require_text_support=False):
    allowed = {r.chunk_id for r in evidence}
    for claim in answer.claims:
        from backend.app.services.output_validation import INSTRUCTIONS

        if check_policy(claim.text) or INSTRUCTIONS.search(claim.text):
            raise AppError(502, "error", "Answer failed the output policy check. No answer was displayed.", reason_code="safety_failed_generation")
        if not set(claim.citation_ids) <= allowed:
            raise AppError(502, "error", "Answer cited an unknown source. No answer was displayed.")
        if require_text_support:
            normalized = " ".join(claim.text.casefold().split())
            cited = [r for r in evidence if r.chunk_id in claim.citation_ids]
            # Reviewed sections are self-contained units. Keep all qualifications
            # in the section, including exceptions in neighbouring sentences.
            units = {" ".join(record.text.casefold().split()) for record in cited}
            if normalized not in units:
                raise AppError(
                    502, "error", "Generated claim adds wording beyond the cited reference."
                )
        if check_policy(claim.text) or re.search(
            r"\b(?:you should take|take \d|your diagnosis|you have|definitely normal|increase your|stop taking)\b",
            claim.text,
            re.I,
        ):
            raise AppError(
                502, "error", "Answer failed the output policy check. No answer was displayed."
            )
    return answer


def validate_conversation(text):
    personal_treatment = re.search(
        r"\b(?:your|for you|you need|you must|you should|i recommend)\b.{0,100}"
        r"\b(?:dose|dosage|taking|start|stop|begin|increase|decrease|switch|"
        r"\d+(?:\.\d+)?\s*(?:mg|mcg|ml|g))\b",
        text,
        re.I | re.S,
    )
    if (
        personal_treatment
        or check_policy(text)
        or re.search(
            r"\b(?:you should take|take \d|your diagnosis|definitely normal|increase your|stop taking)\b"
            r"|\byou have\b(?!\s+(?:(?:a|an|any|some|another|more|further)\s+)?questions?\b)",
            text,
            re.I,
        )
    ):
        raise AppError(
            502, "error", "Answer failed the output policy check. No answer was displayed."
        )
    return text


class AnswerService:
    def __init__(
        self, settings, references, ollama, compute, secondary=None, teaching=None, patient=None
    ):
        self.settings, self.references = settings, references
        self.ollama, self.compute = ollama, compute
        self.secondary = secondary
        self.teaching = teaching
        from backend.app.services.patient_information import PatientInformationStore

        self.patient = patient or PatientInformationStore(
            settings.patient_release_path, settings.enable_patient_information
        )

    def answer(self, question, history=(), context="", followup=None, audience="understand", *, question_plan=None):
        from backend.app.services.educational_provisional import attach, checked_text, eligible
        from backend.app.services.question_plan import plan_question

        checked = self._source_answer(question, history, context, followup, audience, question_plan=question_plan)
        if (not context and self.settings.enable_educational_model_knowledge
                and self.settings.answer_mode == "ollama"
                and not getattr(self.references, "error", None)
                and not getattr(self.teaching, "error", None)
                and eligible(question, question_plan or plan_question(question, audience), checked)):
            try:
                with self.compute.enter():
                    draft = self.ollama.educational(question)
                text = checked_text(draft.answer + ("\n\n" + draft.deeper_explanation if draft.deeper_explanation else ""))
                if text:
                    attach(checked, text)
                else:
                    checked["provisional_status"] = "draft_rejected"
            except AppError as error:
                checked["provisional_status"] = "model_unavailable" if error.code == 503 else "draft_rejected"
        return checked

    def _source_answer(self, question, history=(), context="", followup=None, audience="understand", *, question_plan=None):
        from backend.app.services.output_validation import finalize as terminal_guard
        from backend.app.services.question_plan import plan_question

        def finalize(q, result):
            units = [*getattr(self.teaching, "units", ()), *self.patient.units]
            task = question_plan or plan_question(q, audience)
            checked = terminal_guard(q, result, units, task, getattr(self.teaching, "metadata", {}), getattr(self.teaching, "review_flags", {}), getattr(getattr(self.teaching, "references", None), "id_records", {}))
            if task.intent == "symptom_information" and any(
                code.startswith("patient_") for code in checked.get("rejection_codes", [])
            ):
                # Exactly one recovery lookup in the patient collection. Do
                # not recursively invoke the teacher, model or this closure.
                recovered = terminal_guard(q, self.patient.answer(task), units, task)
                recovered["relevance_recovery"] = "bounded_patient_applicability_lookup"
                return recovered
            return checked

        decision = check_policy(question)
        if decision:
            return finalize(question, decision)
        plan = question_plan or plan_question(question, audience)
        if plan.needs_clarification and not context:
            return finalize(question, envelope("insufficient_evidence", "medical_education", "Name the topic for this follow-up so I can retrieve the correct evidence.", task_completion=False))
        if (
            self.settings.enable_mds_pipeline and plan.facets and not context
            and plan.intent != "symptom_information"
            and (audience != "research" or re.search(r"\b(?:critically appraise|critical appraisal)\b", question, re.I))
            and plan.task not in {"viva", "quiz", "revise", "review_answer"}
            and (plan.marks is not None or len(plan.facets) > 1 or plan.task in {"compare", "mechanism", "essay", "fictional_case", "histology", "classification", "slide_discussion"}
                 or plan.facets[0].facet != "definition" or audience == "study")
        ):
            from backend.app.services.answer_composer import compose
            from backend.app.services.evidence_plan import build_evidence_plan

            evidence, records = build_evidence_plan(plan, self.teaching, self.references)
            prepared_units = getattr(self.teaching, "units", ())
            parent_records = getattr(getattr(self.teaching, "references", None), "id_records", {})
            requested = {(f.topic_id, f.facet, f.scope) for f in plan.facets}
            for unit in prepared_units:
                if any(isinstance(binding, dict) and (binding.get("topic_id"), binding.get("facet"), binding.get("scope")) in requested for binding in unit.get("facet_bindings", [])):
                    for key in unit.get("citation_ids", []):
                        if key in parent_records:
                            records[key] = parent_records[key]
            result = compose(plan, evidence, records, prepared_units=prepared_units,
                source_metadata=getattr(self.teaching, "metadata", {}), review_flags=getattr(self.teaching, "review_flags", {}))
            from backend.app.services.progression import asks_for_depth, remove_previous_claims

            if history and (followup == "deeper" or asks_for_depth(plan.original_question)):
                result = remove_previous_claims(result, history)
            result = finalize(question, result)
            used_ids = {key for claim in result.get("claims", []) for key in claim.get("citation_ids", [])}
            inspected_ids = [key for key in used_ids if getattr(self.teaching, "metadata", {}).get(key, {}).get("ai_inspected_facet_bindings")]
            if inspected_ids:
                result["evidence_review_origin"] = "ai_source_inspection"
                result["limitations"].append("Facet applicability includes AI source inspection; this is development evidence, not human clinical review.")
            if self.settings.mds_synthesis_mode == "shadow" and result.get("claims"):
                result["shadow_evaluation"] = self._shadow_synthesis(plan, records)
            # Preserve the established prepared-definition route when the new
            # facet route has no admitted evidence for a simple definition.
            if records or len(plan.facets) != 1 or plan.facets[0].facet != "definition":
                return result
        from backend.app.services.report_terms import explain_report

        report = explain_report(question) if not context else None
        if report is not None:
            checked = finalize(question, report)
            checked['question_plan'] = plan.model_dump()
            return checked
        if audience == 'research' and plan.intent != 'symptom_information' and not context:
            return finalize(question, envelope(
                'insufficient_evidence', 'research_assistance',
                'Define a public research question, population, article type and search scope in Research & Write. Confirm the query before searching; no search has run yet.',
                research_setup={'question': question}, task_completion=False,
            ))
        from backend.app.services.study_operations import operation_answer

        operation = operation_answer(plan, self.teaching) if not context else None
        if operation is not None and followup is None:
            checked = finalize(question, operation)
            checked['question_plan'] = plan.model_dump()
            return present_answer(checked)
        if plan.task == 'mechanism' and operation is None and not context:
            return finalize(question, envelope(
                'insufficient_evidence', 'medical_education',
                'A checked mechanism activity is not declared for this exact topic and context. Browse the topic pack or ask for its definition.',
                task_completion=False, unsupported_parts=[question],
            ))
        if followup == "deeper" and not context:
            result = finalize(question, self._answer(question + " in detail", history, context))
            previous = history[-1].get("response", {}) if history else {}
            old_text = {c["text"] for c in previous.get("claims", [])}
            if not result.get("claims") or all(c["text"] in old_text for c in result["claims"]):
                return finalize(
                    question,
                    envelope(
                        "insufficient_evidence",
                        "medical_education",
                        "I do not have additional supported detail beyond the preceding answer. Ask about a specific mechanism or related concept.",
                        task_completion=False,
                        followup_operation="deeper",
                    ),
                )
            return present_answer(result)
        if plan.task in {"viva", "quiz", "revise"} and not context:
            base = finalize(
                plan.topic, self._answer("What is " + plan.topic + "?", history, context)
            )
            if base.get("status") == "ok" and base.get("claims"):
                from backend.app.services.study import practice

                result = practice(plan, base)
            else:
                result = envelope(
                    "insufficient_evidence",
                    "medical_education",
                    "No supported practice material is available for this topic.",
                    task_completion=False,
                )
        elif plan.task == "compare":
            result = envelope(
                "insufficient_evidence",
                "medical_education",
                "A source-supported comparison is not available for this request. Ask about each concept separately.",
                task_completion=False,
                unsupported_parts=[question],
                unsupported_topics=[question],
            )
        elif len(plan.subquestions) > 1 and not context:
            results = [
                (part, finalize(part, self._answer(part, history, context)))
                for part in plan.subquestions
            ]
            supported = [
                (part, value)
                for part, value in results
                if value.get("status") in {"ok", "partial"} and value.get("claims")
            ]
            missing = [part for part, value in results if (part, value) not in supported]
            citations = {
                c["chunk_id"]: c for _, value in supported for c in value.get("citations", [])
            }
            result = envelope(
                "partial"
                if supported and (missing or any(v["status"] == "partial" for _, v in supported))
                else "ok"
                if supported
                else "insufficient_evidence",
                "medical_education",
                "Supported parts of your question." if missing else "Source-backed explanation",
                claims=[c for _, value in supported for c in value["claims"]],
                citations=list(citations.values()),
                covered_parts=[part for part, _ in supported],
                unsupported_parts=missing,
                task_completion=not missing
                and all(v.get("task_completion") is True for _, v in supported),
                component_answers=[
                    {"question": part, "response": value} for part, value in supported
                ],
                warnings=list(
                    dict.fromkeys(w for _, value in supported for w in value.get("warnings", []))
                ),
            )
        elif re.fullmatch(
            r"(?:hi|hello)[,!\s]+(?:can you |could you )?help me study[.!?\s]*", question, re.I
        ):
            result = envelope(
                "ok",
                "conversation",
                "Choose a topic or ask a question. I can explain supported concepts and offer source-based practice.",
            )
        else:
            result = self._answer(question, history, context)
        result = finalize(question, result)
        result["question_plan"] = plan.model_dump()
        if re.fullmatch(r"(?:hi|hello|thanks|thank you)[.!?\s]*", question, re.I):
            return result
        return present_answer(result)

    def _answer(self, question, history=(), context=""):
        decision = check_policy(question)
        if decision:
            return decision
        from backend.app.services.question_plan import plan_question

        patient_plan = plan_question(question)
        if patient_plan.intent == "symptom_information":
            return self.patient.answer(patient_plan)
        if question.casefold().startswith(("catalogue:", "catalog:")):
            from backend.app.services.brand_catalogue import lookup

            return lookup(question.split(":", 1)[1].strip())
        # Explicit general questions must not match incidental words inside a
        # medical chapter, such as immune-cell 'programming'. Document context
        # still uses the medical evidence/confirmation path.
        if explicit_nonmedical(question) and not context:
            if self.settings.answer_mode == "ollama" and self.settings.enable_general_chat:
                return self._conversation(question, history, context)
            return envelope(
                "insufficient_evidence",
                "conversation",
                "General chat is unavailable in this configuration.",
            )
        if self.teaching and not context and not self.references.matched_identities(question):
            taught = self.teaching.answer(question)
            if taught:
                return taught
            from backend.app.services.retrieval import phrase_match
            from backend.app.services.teaching import canonical_teaching_text
            from backend.app.services.teaching_query import plan_question

            focus = canonical_teaching_text(plan_question(question).focus)
            mean_verb = len(re.findall(r"\bmean\b", focus, re.I)) == 1 and re.search(
                r"\bwhat\s+(?:do|does|did|would|could|can)\b[^.!?]{0,160}\bmean[.!?\s]*$",
                focus,
                re.I,
            )
            named = [
                topic
                for unit in getattr(self.teaching, "units", [])
                for topic in unit.get("topics", [])
                if phrase_match(canonical_teaching_text(topic), focus)
                # 'Mean' is also a common question verb. Do not route
                # 'what does blood pressure mean' as a statistics request.
                and (topic.casefold() != "mean" or not mean_verb)
            ]
            if named:
                # A recognised teaching concept with unsupported scope must not
                # silently become an unrelated primary-library excerpt.
                return envelope(
                    "insufficient_evidence",
                    "medical_education",
                    "I recognise the teaching topic, but the available material does not support the full question and its context.",
                    unsupported_topics=[question],
                    warnings=[
                        "Try asking about the general concept separately; the additional context remains unsupported."
                    ],
                )
        catalogue_ref = self.references.catalogue_match(question)
        if catalogue_ref and re.search(
            r"\b(?:nlem|essential medicines|essential medicine)\b", question, re.I
        ):
            return envelope(
                "ok",
                "medical_education",
                "Indian essential-medicines catalogue entry",
                claims=[{"text": catalogue_ref.text, "citation_ids": [catalogue_ref.chunk_id]}],
                citations=[catalogue_ref.citation()],
                answer_method="extractive",
                limitations=[
                    SCOPE,
                    "Catalogue evidence only; no clinical monograph or brand equivalence is established.",
                ],
            )
        evidence = self.references.search(question)
        if self.secondary and not getattr(self.references, "error", None):
            anchors = evidence
            if not anchors:
                linked_question = self.secondary.resolve_question(question)
                if linked_question:
                    # The link validates eligibility for secondary notes only;
                    # it must not manufacture a primary clinical brand alias.
                    anchors = self.references.search(
                        linked_question, require_requested_section=False
                    )
                else:
                    anchors = self.references.search(question, require_requested_section=False)
            evidence = [*evidence, *self.secondary.search(question, anchors)][:5]
        if not evidence:
            if catalogue_ref:
                return envelope(
                    "insufficient_evidence",
                    "medical_education",
                    "This medicine appears in the Indian essential-medicines catalogue, but no applicable clinical monograph covers your question.",
                    claims=[{"text": catalogue_ref.text, "citation_ids": [catalogue_ref.chunk_id]}],
                    citations=[catalogue_ref.citation()],
                    answer_method="extractive",
                    limitations=[
                        SCOPE,
                        "Catalogue membership cannot answer purpose, interactions, contraindications or personal dosing.",
                    ],
                )
            medical_query = bool(
                re.search(
                    r"\b(?:medical|medicine|medication|drug|prescription|tablet|capsule|dose|dosage|"
                    r"contraindication|contraindications|side effect|disease|syndrome|symptom|"
                    r"diagnosis|treatment|infection|blood test|x-ray|xray|ecg|hemoglobin|haemoglobin)\b"
                    r"|\b\w+(?:mab|cillin|pril|sartan|statin|gliptin)\b",
                    question,
                    re.I,
                )
            )
            known_topic = self.references.has_known_topic(question)
            # Unknown entities and ambiguous health questions fail closed. Only
            # explicit nonmedical intents may use uncited model knowledge.
            nonmedical = explicit_nonmedical(question)
            if (
                self.settings.answer_mode == "ollama"
                and self.settings.enable_general_chat
                and not (medical_query or known_topic or context)
                and nonmedical
            ):
                return self._conversation(question, history, context)
            return envelope(
                "insufficient_evidence",
                "medical_education",
                "The local reference library does not cover this question. "
                "Try a supported topic or ask a qualified professional.",
            )
        retailer_material = any(r.source_type == "retailer_monograph" for r in evidence)
        secondary_material = any(r.source_type == "unverified_secondary" for r in evidence)
        model_failure = None
        # Extractive mode returns only curated source notes; it does not synthesize
        # a personalized answer. No invisible model-memory fallback.
        if self.settings.answer_mode == "extractive":
            claims = [{"text": r.text, "citation_ids": [r.chunk_id]} for r in evidence]
            method = "extractive"
        else:
            try:
                with self.compute.enter():
                    generated = validate_generated(
                        self.ollama.generate(question, evidence),
                        evidence,
                        require_text_support=self.settings.strict_source_grounding
                        or secondary_material,
                    )
                claims = [claim.model_dump() for claim in generated.claims]
                method = "ollama"
            except AppError as error:
                if error.reason_code == "safety_failed_generation":
                    return envelope("insufficient_evidence", "medical_education", "The generated answer failed safety checks; no answer or fallback was displayed.", rejection_codes=[error.reason_code], task_completion=False)
                if not (
                    self.settings.strict_source_grounding or secondary_material
                ) or error.code not in {502, 503}:
                    raise
                claims = [{"text": r.text, "citation_ids": [r.chunk_id]} for r in evidence]
                method = "extractive_verified_fallback"
                model_failure = {"kind": "transport_error" if error.code == 503 else "generation_validation_error", "upstream_status_code": error.code, "fallback_validated_separately": True}
        used = {key for claim in claims for key in claim["citation_ids"]}
        retailer_material = any(
            r.source_type == "retailer_monograph" and r.chunk_id in used for r in evidence
        )
        secondary_used = any(
            r.source_type == "unverified_secondary" and r.chunk_id in used for r in evidence
        )
        if secondary_used and method == "extractive_verified_fallback":
            method = "extractive_secondary_fallback"
        notices = []
        if retailer_material:
            notices.append(
                "Includes secondary retailer information imported under the user's verification/licensing attestation; not independently validated as manufacturer prescribing information."
            )
        if secondary_used:
            notices.append(SECONDARY_NOTICE)
        return envelope(
            "ok",
            "medical_education",
            "Relevant reference notes"
            if method.startswith("extractive")
            else "Source-backed explanation",
            claims=claims,
            citations=[r.citation() for r in evidence if r.chunk_id in used],
            answer_method=method,
            **({"model_failure": model_failure} if model_failure else {}),
            warnings=notices,
            evidence_tier=(
                "mixed_with_unverified_secondary"
                if any(
                    r.source_type != "unverified_secondary" and r.chunk_id in used for r in evidence
                )
                else "secondary_unverified"
            )
            if secondary_used
            else "reference",
            limitations=[
                SCOPE,
                "Only the supported parts of your question are covered. "
                "Source jurisdictions: "
                + ", ".join(sorted({r.jurisdiction for r in evidence}))
                + ". "
                "Product labels apply to their named formulation and jurisdiction; they are not a personal care plan.",
                "Source support requires review; citation validity alone does not prove correctness.",
                "Selected notes are incomplete; comprehensive drug coverage and interaction checking are not established.",
                *(
                    [
                        "Secondary datasets are unverified, may overlap, and do not independently establish product equivalence or complete ingredient lists."
                    ]
                    if secondary_used
                    else []
                ),
                *(
                    [
                        "Retailer descriptions may be historical or incomplete. Qualified clinical review of this imported dataset has not been performed."
                    ]
                    if retailer_material
                    else []
                ),
            ],
        )

    def _shadow_synthesis(self, plan, records):
        """One optional local call; drafts are discarded and never emitted."""
        try:
            with self.compute.enter():
                draft = self.ollama.synthesize(plan, records)
            units = list(draft.claims)
            known = sum(bool(c.citation_ids) and set(c.citation_ids) <= records.keys() for c in units)
            return {"mode": "shadow", "displayed": False, "model_calls": 1,
                    "draft_claim_count": len(units), "resolving_citation_claim_count": known,
                    "semantic_claim_support": "pending_independent_evaluation",
                    "clinical_review": "pending"}
        except AppError as error:
            return {"mode": "shadow", "displayed": False, "model_calls": 1,
                    "status": "transport_error" if error.code == 503 else "draft_rejected",
                    "semantic_claim_support": "not_assessed"}

    def _conversation(self, question, history, context):
        with self.compute.enter():
            safe_history = [
                item for item in history if item.get("response", {}).get("route") == "conversation"
            ]
            generated = self.ollama.converse(question, safe_history, context)
            text = validate_conversation(generated.answer)
            greeting = re.fullmatch(r"(?:hi|hello|thanks|thank you)[.!?\s]*", question, re.I)
            deeper = (
                ""
                if greeting
                else validate_conversation(getattr(generated, "deeper_explanation", ""))
            )
        return envelope(
            "ok",
            "conversation",
            "",
            answer=text,
            deeper_explanation=deeper,
            answer_method="ollama_model_knowledge",
            warnings=[
                "Generated from the model's pretrained knowledge; not verified against local sources."
            ],
            limitations=[
                SCOPE,
                "This response has no local source citations. Model knowledge may be inaccurate or outdated.",
            ],
        )
