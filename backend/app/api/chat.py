import json
import re

from fastapi import APIRouter, Depends, Request

from backend.app.api.dependencies import owned_session
from backend.app.errors import AppError, envelope
from backend.app.schemas import ChatRequest
from backend.app.services.documents import explain, require_confirmation
from backend.app.services.policy import check_policy

router = APIRouter(prefix="/v1/chat", tags=["education"])


def is_topic_followup(question: str) -> bool:
    return " ".join(question.casefold().split()).rstrip(".!?") in {
        "what does that mean",
        "explain that",
        "tell me more",
    }


def educational_exception(payload, decision):
    """Study-mode dose/medicine questions without first-person framing are
    educational (answered only from label/reference evidence). Urgent guidance
    and prompt-injection refusals are never relaxed."""
    from backend.app.services.grounded import first_person

    text = payload.question.casefold()
    return (decision.get("status") == "unsupported_input" and payload.audience == "study"
            and not first_person(payload.question)
            and not re.search(r"\b(?:ignore|override)\b.{0,40}\b(?:instructions|policy|system|prompt)\b", text)
            and not re.search(r"\b(?:my|our) (?:patient|child|son|daughter|baby)\b", text))


@router.post("")
def chat(request: Request, payload: ChatRequest, session=Depends(owned_session)):
    state = request.app.state
    grounded = getattr(state, "grounded", None)
    decision = check_policy(payload.question)
    if decision and grounded is not None and educational_exception(payload, decision):
        decision = None
    if decision:
        from backend.app.services.output_validation import finalize

        return finalize(payload.question, decision)
    from backend.app.services.question_plan import plan_question

    previous_message = session.messages[-1] if session.messages else {}
    prior_topic = previous_message.get("response", {}).get("question_plan", {}).get("topic")
    viva_question = payload.question
    if prior_topic and re.search(r"\b(?:this|that) topic\b", viva_question, re.I):
        viva_question = re.sub(r"\b(?:this|that) topic\b", prior_topic, viva_question, flags=re.I)
    viva_request = (
        payload.viva_question_id or getattr(session, "viva", {})
        or plan_question(viva_question, payload.audience).task == "viva"
        or re.fullmatch(r"(?:restart|exit|stop|end) (?:viva|practice)[.!?]*", payload.question, re.I)
    )
    if not payload.context_id and viva_request and getattr(getattr(state.answers, "settings", None), "enable_mds_pipeline", True):
        from backend.app.services.viva import turn

        with state.sessions.lock, session.lock:
            state.sessions.alive(session)
            viva_result = turn(session, viva_question, state.answers, payload.viva_question_id)
            if viva_result is not None:
                session.messages.append({"question": payload.question, "resolved_question": None,
                                         "audience": "study", "response": viva_result})
                session.messages[:] = session.messages[-20:]
                return viva_result
    context_document = None
    resolved_question = None
    audience = payload.audience
    if payload.context_id:
        if payload.context_id in session.papers:
            from backend.app.api.papers import owned_paper
            from backend.app.services.output_validation import finalize

            with state.sessions.lock, session.lock:
                state.sessions.alive(session)
                paper = owned_paper(session, payload.context_id)
                with paper.lock:
                    paper.require_confirmation(payload.expected_revision)
                    result = finalize(payload.question, paper.excerpts(payload.question), paper_context=paper)
                    session.messages.append({"question": payload.question, "resolved_question": None,
                                             "audience": "research", "response": result})
                    session.messages[:] = session.messages[-20:]
                    return result
        elif payload.context_id in session.documents:
            document = state.sessions.document(session, payload.context_id)
            context_document = document
            with document.lock:
                require_confirmation(document, payload.expected_revision)
                from backend.app.services.question_plan import plan_question

                if (
                    plan_question(payload.question, payload.audience).intent
                    == "symptom_information"
                ):
                    # Confirmation still gates document use. An attached
                    # prescription must not substitute its drug explanation
                    # for the patient's different symptom question.
                    context = None
                    result = state.answers.answer(
                        payload.question, list(session.messages), audience=payload.audience
                    )
                elif state.settings.enable_general_chat and state.settings.answer_mode == "ollama":
                    context = json.dumps(
                        [
                            {"kind": f["kind"], "value": f["value"], "status": f["status"]}
                            for f in document.fields
                        ]
                    )
                else:
                    context = None
                    result = explain(document, state.references)
                    result["message"] += (
                        " Follow-up instructions require professional clarification."
                    )
            if context is not None:
                result = state.answers.answer(payload.question, list(session.messages), context)
        elif payload.context_id in session.results:
            result = state.answers.answer(payload.question)
        else:
            raise AppError(404, "unsupported_input", "Context is not available in this session.")
    elif grounded is not None:
        result = grounded.answer(payload.question, list(session.messages), payload.audience)
        resolved_question = result.get("resolved_question") or payload.question
        audience = payload.audience
    else:
        question = payload.question
        from backend.app.services.question_plan import plan_question

        previous = session.messages[-1] if session.messages else {}
        previous_plan = previous.get("response", {}).get("question_plan", {})
        context_topic = previous_plan.get("topic") if previous.get("resolved_question") else None
        scoped_plan = plan_question(question, audience, context_topic=context_topic)
        from backend.app.services.progression import asks_for_depth

        if context_topic and asks_for_depth(question) and not scoped_plan.canonical_topics:
            detail = re.sub(r"^go deeper(?: into)?\s*", "", question, flags=re.I).strip()
            question = "Explain " + context_topic + " " + (detail or "in detail")
            if not payload.task_explicit:
                audience = previous.get("audience", audience)
            scoped_plan = plan_question(question, audience)
            scoped_plan.original_question = payload.question
            scoped_plan.context_topic = context_topic
        practice_followup = " ".join(question.casefold().split()).rstrip(".!?") in {
            "quiz me",
            "ask me a viva question",
            "test my understanding",
        }
        if is_topic_followup(question) or practice_followup:
            previous = session.messages[-1] if session.messages else {}
            question = previous.get("resolved_question")
            if not question:
                return envelope(
                    "insufficient_evidence",
                    "medical_education",
                    "Name the topic you want to understand.",
                )
            if not payload.task_explicit and payload.audience == "understand":
                audience = previous.get("audience", "understand")
            if practice_followup:
                topic = re.sub(
                    r"^(?:what is|what are|define|explain|quiz me on|ask me a viva question on)\s+",
                    "",
                    question,
                    flags=re.I,
                ).strip(" .?!")
                question = "quiz me on " + topic
        elif not payload.task_explicit and re.search(
            r"^(?:find|search)(?: .+)? (?:literature|papers|articles)\b|^help (?:me )?(?:write|structure) (?:a |my )?(?:review|paper)\b",
            question,
            re.I,
        ):
            audience = "research"
        resolved_question = question
        if scoped_plan.context_topic:
            if not payload.task_explicit:
                audience = previous.get("audience", audience)
            scoped_plan.audience = audience
            question = " ".join(f.query for f in scoped_plan.facets)
            resolved_question = question
            result = state.answers.answer(question, list(session.messages), audience=audience, question_plan=scoped_plan)
        elif is_topic_followup(payload.question):
            result = state.answers.answer(question, list(session.messages), "", "deeper", audience)
        elif audience != "understand":
            result = state.answers.answer(question, list(session.messages), "", None, audience)
        else:
            result = state.answers.answer(question, list(session.messages))
    with state.sessions.lock, session.lock:
        state.sessions.alive(session)
        if context_document is not None:
            with context_document.lock:
                require_confirmation(context_document, payload.expected_revision)
                result.update(
                    context_id=context_document.id, context_revision=context_document.revision
                )
        session.messages.append(
            {
                "question": payload.question,
                "resolved_question": resolved_question,
                "audience": audience,
                "response": result,
            }
        )
        session.messages[:] = session.messages[-20:]
    return result
