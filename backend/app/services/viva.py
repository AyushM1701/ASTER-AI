"""One-question-at-a-time practice owned by a temporary Session.

The caller holds session/store locks. No model call, persistent educational
storage or hidden cross-session state is used. Feedback is lexical/provisional.
"""

import re
from uuid import uuid4

from backend.app.errors import envelope
from backend.app.services.output_validation import finalize
from backend.app.services.question_plan import plan_question
from backend.app.services.teaching import teaching_terms


def public_question(activity, feedback=None):
    output = {k: activity[k] for k in ("topic", "question_id", "question", "difficulty", "number", "stage")}
    if feedback:
        output["feedback"] = feedback
    return output


def new_question(activity):
    activity["question_id"] = "viva_" + uuid4().hex
    activity["stage"] = "await_answer"
    activity["question"] = (
        f"How would you explain {activity['topic']} using a precise source-supported definition?"
        if activity["number"] == 1
        else f"How would you retain the source’s qualifications when explaining {activity['topic']}?"
    )


def turn(session, question, service, question_id=None):
    """Return None for ordinary chat; incomplete/stale turns never reveal answers."""
    command = " ".join(question.casefold().strip(" .!?").split())
    active = session.viva
    if command in {"exit viva", "stop viva", "end viva", "exit practice"}:
        active.clear()
        return envelope("ok", "medical_education", "Viva ended.", viva={"stage": "exited"}, task_completion=True, coverage_status="complete")
    restart = command in {"restart viva", "restart practice"}
    plan = plan_question(question, "study")
    if plan.intent == "symptom_information":
        active.clear()
        return None
    starting = plan.task == "viva" and not restart
    if restart and not active:
        return envelope("insufficient_evidence", "medical_education", "Name a topic to start a viva.", task_completion=False)
    if starting or restart:
        topic = active["topic"] if restart else plan.topic
        # Source-only lookup: model outage cannot reveal an invented answer or
        # block an activity for which admitted evidence already exists.
        teacher = service.teaching
        base = teacher.answer("What is " + topic + "?") if teacher else None
        if not base:
            rows = service.references.search("What is " + topic + "?")
            base = envelope("ok" if rows else "insufficient_evidence", "medical_education", claims=[{"text": r.text, "citation_ids": [r.chunk_id]} for r in rows[:3]], citations=[r.citation() for r in rows[:3]])
        checked = finalize("What is " + topic + "?", base, getattr(teacher, "units", ()), source_metadata=getattr(teacher, "metadata", {}), review_flags=getattr(teacher, "review_flags", {}), source_records=getattr(getattr(teacher, "references", None), "id_records", {}))
        if not checked.get("claims") or checked.get("status") not in {"ok", "partial"}:
            active.clear()
            return envelope("insufficient_evidence", "medical_education", "A source-supported viva cannot be prepared for this topic and scope yet.", task_completion=False)
        active.clear()
        active.update(topic=topic, difficulty="foundation", number=1, candidates=checked["claims"][:3], citations=checked["citations"], prior_answer=None, source_set_version=checked.get("teaching_version"))
        if len(active["candidates"]) == 1:
            # A single admitted unit supports a second reflection question;
            # do not invent another medical point to keep practice running.
            active["candidates"].append(dict(active["candidates"][0]))
        new_question(active)
        return envelope("ok", "medical_education", "Answer this one question. Feedback follows after your response.", viva=public_question(active), task_completion=True, coverage_status="complete", clinical_review_status="pending")
    if question_id and (not active or active.get("stage") != "await_answer" or question_id != active.get("question_id")):
        return envelope("needs_confirmation", "medical_education", "This viva question is no longer active in this session. Reopen the current turn or start a new viva.", task_completion=False)
    if not active or active.get("stage") != "await_answer":
        return None
    if re.match(r"\s*(?:after i answer\b|(?:please )?(?:grade|assess|evaluate) (?:my answer|it)\b|use (?:a|an|the) .*rubric\b)", question, re.I):
        return envelope("needs_confirmation", "medical_education",
            "Send your answer to the current question first. Source-based feedback follows your response; faculty assessment remains separate.",
            viva=public_question(active), task_completion=False, coverage_status="partial")
    # An explicit new concept/task exits practice rather than scoring a new
    # question as a learner answer. Pronoun follow-ups are also normal chat.
    if re.match(r"\s*(?:explain|define|compare|what|why|how|find|search)\b", question, re.I) or (plan.needs_clarification and not question_id):
        active.clear()
        return None
    if len(question) > 2000:
        return envelope("unsupported_input", "medical_education", "Keep a viva response under 2,000 characters.", task_completion=False)
    claim = active["candidates"][active["number"] - 1]
    words = teaching_terms(claim["text"])
    matched = sorted(words & teaching_terms(question))
    missing = sorted(words - teaching_terms(question))
    feedback = {
        "review_status": "provisional_educational",
        "method": "lexical_source_reflection_not_semantic_or_faculty_grading",
        "matched_source_terms": matched[:12], "missed_source_terms": missing[:12],
        "rubric": ["Compare your definition with the source and retain its qualifications.", "Vocabulary overlap does not establish a correct answer; ask qualified faculty to assess reasoning."],
        "negation_review_needed": bool(re.search(r"\b(?:not|never|always|none)\b", question, re.I)),
        "score": None,
    }
    active["prior_answer"] = question
    used = set(claim["citation_ids"])
    result = finalize("What is " + active["topic"] + "?", envelope(
        "ok", "medical_education", "Provisional educational feedback; compare with the cited source.",
        claims=[claim], citations=[c for c in active["citations"] if c["chunk_id"] in used],
    ), getattr(service.teaching, "units", ()), source_metadata=getattr(service.teaching, "metadata", {}), review_flags=getattr(service.teaching, "review_flags", {}), source_records=getattr(getattr(service.teaching, "references", None), "id_records", {}))
    if result.get("status") not in {"ok", "partial"}:
        active.clear()
        return result
    if active["number"] < len(active["candidates"]):
        active["number"] += 1
        new_question(active)
    else:
        active["stage"] = "completed"
        active["question"] = ""
        active["question_id"] = ""
    result["viva"] = public_question(active, feedback)
    result["task_completion"] = True
    result["coverage_status"] = "complete"
    return result
