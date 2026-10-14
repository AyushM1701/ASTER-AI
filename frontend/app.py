import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from frontend.client import call  # noqa: E402

st.set_page_config(page_title="Aster · Chat", layout="wide", initial_sidebar_state="auto")
st.html("<style>" + (ROOT / "frontend/style.css").read_text(encoding="utf-8") + "</style>")


@st.cache_data(ttl=20, show_spinner=False)
def get_health():
    return call("GET", "/health/ready")


def api(method, path, **kwargs):
    result = call(method, path, st.session_state.get("token"), **kwargs)
    if result.get("_http_status") == 401:
        st.session_state["expired"] = True
    return result


def clear_local():
    for key in list(st.session_state):
        del st.session_state[key]


def start_session():
    result = call("POST", "/v1/sessions")
    if result.get("token"):
        clear_local()
        st.session_state.update(token=result["token"], messages=[], expired=False)
    else:
        st.error(result["message"])


def render_result(result, key):
    status, message = result.get("status", "error"), result.get("message", "")
    if status == "urgent_guidance":
        st.error(message)
    elif status in {"error", "busy", "unsupported_input", "quality_rejected"}:
        st.warning(message)
    elif status in {"insufficient_evidence", "needs_confirmation"}:
        st.info(message)
    elif message:
        st.caption(message)
    if result.get("answer"):
        st.text(result["answer"])
    citations = result.get("citations", [])
    numbers = {c["chunk_id"]: i for i, c in enumerate(citations, 1)}
    for claim in result.get("claims", []):
        st.text(claim["text"])
        st.caption(
            " · ".join(f"Source {numbers[c]}" for c in claim["citation_ids"] if c in numbers)
        )
    for warning in result.get("warnings", []):
        st.caption(warning)
    if result.get("findings"):
        st.dataframe(
            pd.DataFrame(result["findings"])[["name", "score"]], hide_index=True, width="stretch"
        )
        st.caption(result.get("score_semantics", "Research scores, not diagnostic probabilities."))
    if citations:
        with st.expander(f"Sources ({len(citations)})"):
            for i, source in enumerate(citations, 1):
                st.write(f"{i}. {source['title']}")
                st.caption(
                    f"{source['publisher']} · {source['section']} · {source['jurisdiction']}"
                )
                st.text(source["excerpt"])
                st.link_button("Read primary reference", source["url"], key=f"{key}_source_{i}")
    if result.get("limitations"):
        with st.expander("Scope and limitations"):
            for limitation in result["limitations"]:
                st.text(limitation)
    if result.get("claims") or result.get("findings") or result.get("answer"):
        export = {k: v for k, v in result.items() if not k.startswith("_")}
        st.download_button(
            "Export response",
            json.dumps(export, indent=2),
            "aster-response.json",
            "application/json",
            key=key + "_export",
        )


def send_question(question):
    question = question.strip()
    if not question:
        return
    messages = st.session_state.setdefault("messages", [])
    messages.append({"role": "user", "text": question})
    payload = {"question": question}
    document = st.session_state.get("active_document")
    if document and document.get("confirmed_revision") == document["revision"]:
        payload.update(context_id=document["document_id"], expected_revision=document["revision"])
    with st.spinner("Aster is thinking…"):
        result = api("POST", "/v1/chat", json=payload)
    messages.append({"role": "assistant", "result": result})
    messages[:] = messages[-40:]


def send_attachment(data, filename):
    messages = st.session_state.setdefault("messages", [])
    st.session_state.pop("active_document", None)
    messages.append({"role": "user", "text": "Attached " + filename, "preview": data})
    with st.spinner("Examining the attachment and choosing its workflow…"):
        result = api(
            "POST",
            "/v1/attachments",
            files={"file": ("attachment.png", data, "application/octet-stream")},
        )
    entry = {"role": "assistant", "result": result}
    if (result.get("classification") or {}).get("kind") == "prescription":
        entry["document"] = result
    messages.append(entry)
    messages[:] = messages[-40:]
    st.session_state["upload_generation"] = st.session_state.get("upload_generation", 0) + 1


def review_document(entry, key):
    document = entry["document"]
    confirmed = document.get("confirmed_revision") == document["revision"]
    with st.expander(
        "Confirmed transcription" if confirmed else "Review transcription", expanded=not confirmed
    ):
        st.caption(
            f"Revision {document['revision']} · Blank fields stay unreadable or unspecified."
        )
        with st.expander("Raw OCR text"):
            st.text(document.get("raw_text") or "No readable text found.")
        if not confirmed:
            with st.form(f"{key}_confirm_{document['revision']}"):
                values = []
                columns = st.columns(2)
                for index, field in enumerate(document["fields"]):
                    with columns[index % 2]:
                        values.append(
                            st.text_input(
                                field["kind"].replace("_", " ").title(),
                                value=field.get("value") or field.get("candidate_value") or "",
                                max_chars=500,
                                key=f"{key}_{document['revision']}_{field['field_id']}",
                            )
                        )
                acknowledge = st.checkbox(
                    "I compared every field with the original. Blank fields remain unresolved."
                )
                confirm = st.form_submit_button(
                    "Confirm and explain", type="primary", disabled=not active
                )
            if confirm:
                if not acknowledge:
                    st.info("Compare the text with the original and check the confirmation box.")
                else:
                    result = api(
                        "PUT",
                        f"/v1/documents/{document['document_id']}/confirm",
                        json={
                            "expected_revision": document["revision"],
                            "confirmation_acknowledged": True,
                            "fields": [
                                {
                                    "field_id": f["field_id"],
                                    "value": value.strip() or None,
                                    "status": "confirmed_by_user"
                                    if value.strip()
                                    else "unreadable",
                                }
                                for f, value in zip(document["fields"], values, strict=True)
                            ],
                        },
                    )
                    if result.get("confirmed_revision") is not None:
                        entry["document"] = result
                        entry["result"]["status"] = "ok"
                        entry["result"]["message"] = "Prescription transcription confirmed."
                        st.session_state["active_document"] = result
                        with st.spinner("Explaining the confirmed text…"):
                            entry["explanation"] = api(
                                "POST",
                                f"/v1/documents/{document['document_id']}/explain",
                                json={"expected_revision": result["revision"]},
                            )
                        st.rerun()
                    else:
                        st.warning(result["message"])
        else:
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "Field": f["kind"].replace("_", " ").title(),
                            "Confirmed text": f["value"] or "Unreadable / unspecified",
                        }
                        for f in document["fields"]
                    ]
                ),
                hide_index=True,
                width="stretch",
            )
            if st.button("Edit transcription", key=key + "_edit", disabled=not active):
                result = api(
                    "POST",
                    f"/v1/documents/{document['document_id']}/edit",
                    json={"expected_revision": document["revision"]},
                )
                if result.get("document_id"):
                    entry["document"] = result
                    entry.pop("explanation", None)
                    entry["result"].update(
                        status="needs_confirmation",
                        message="Transcription edited. Review and confirm the current revision.",
                    )
                    if (
                        st.session_state.get("active_document", {}).get("document_id")
                        == document["document_id"]
                    ):
                        st.session_state.pop("active_document", None)
                    st.rerun()
                else:
                    st.warning(result["message"])
    if entry.get("explanation"):
        render_result(entry["explanation"], key + "_explanation")


health = get_health()
connected = health.get("status") == "ready" or bool(health.get("references", {}).get("records"))
if "token" not in st.session_state and connected and not st.session_state.get("cleared"):
    start_session()
active = bool(st.session_state.get("token")) and not st.session_state.get("expired", False)

with st.sidebar:
    st.html('<div class="aster-brand">aster<span>.</span></div>')
    st.caption("One conversation. Text and images.")
    st.divider()
    st.write("Your session")
    st.caption("Active · temporary" if active else "No active session")
    if active:
        if st.button("Clear conversation", width="stretch"):
            result = api("DELETE", "/v1/sessions/current")
            if result.get("status") == "ok":
                clear_local()
                st.session_state["cleared"] = True
                st.rerun()
            else:
                st.error(result["message"])
    elif st.button("Start conversation", type="primary", disabled=not connected, width="stretch"):
        start_session()
        st.rerun()
    st.caption("Expires after 30 minutes of inactivity. Images stay in temporary memory.")
    st.divider()
    with st.expander("Local model and services"):
        st.caption("Chat · " + health.get("answer_mode", "Unavailable"))
        classifier = health.get("attachment_classifier", {})
        st.caption(
            "Image routing · " + ("Ready" if classifier.get("available") else "Setup required")
        )
        st.caption(
            "OCR · " + ("Ready" if health.get("ocr", {}).get("available") else "Setup required")
        )
        st.caption(
            "Research scoring · "
            + ("Ready" if health.get("xray", {}).get("available") else "Setup required")
        )
        if st.button("Refresh services", width="stretch"):
            get_health.clear()
            st.rerun()
    sample = ROOT / "data/samples/synthetic_prescription.png"
    if st.button(
        "Try a sample prescription", disabled=not active or not sample.is_file(), width="stretch"
    ):
        send_attachment(sample.read_bytes(), "synthetic-prescription.png")
        st.rerun()
    with st.expander("About Aster"):
        st.text(
            "General information and medical education. Source-backed responses show citations; other responses use pretrained model knowledge and may be wrong. Image routing is experimental. No diagnosis, personal dosing or X-ray normality verdict."
        )
    st.caption("Local processing · no cloud fallback")

st.title("Aster")
st.caption("Ask a question. Attach an image. Keep the conversation together.")
if not connected:
    st.warning(
        health.get(
            "message", "Local services are unavailable. Start the model and refresh services."
        )
    )
elif health.get("status") != "ready":
    st.warning(
        "The local model is unavailable. Conversation requests can still reach the policy checks. Start Ollama and refresh services to restore model answers."
    )
if st.session_state.get("expired"):
    st.warning("This session expired. Start a new conversation in the sidebar.")

messages = st.session_state.setdefault("messages", [])
if not messages:
    with st.container(key="chat_welcome"):
        st.subheader("What would you like to understand?")
        st.write(
            "Ask about a health topic, review a prescription, or attach an X-ray image. Aster examines the attachment and brings the next step into this chat."
        )
        examples = ["What is asthma?", "Explain blood pressure", "What can you help with?"]
        for index, column in enumerate(st.columns(3)):
            with column:
                if st.button(
                    examples[index], key=f"example_{index}", width="stretch", disabled=not active
                ):
                    send_question(examples[index])
                    st.rerun()

for index, entry in enumerate(messages):
    key = f"message_{index}"
    with st.chat_message(entry["role"]):
        st.caption("You" if entry["role"] == "user" else "Aster")
        if entry.get("text"):
            st.text(entry["text"])
        if entry.get("preview"):
            with st.expander("View attached image"):
                st.image(entry["preview"], width=350)
        if entry.get("result"):
            result = entry["result"]
            classification = result.get("classification")
            if classification:
                st.caption(
                    "Attachment · "
                    + {
                        "prescription": "Prescription",
                        "xray": "X-ray",
                        "other": "Other image",
                        "uncertain": "Unclear image",
                    }[classification["kind"]]
                )
            render_result(result, key)
            if result.get("imaging_result"):
                render_result(result["imaging_result"], key + "_imaging")
            if result.get("document_id") and not classification and not entry.get("document"):
                if st.button(
                    "Retry attachment classification", key=key + "_retry", disabled=not active
                ):
                    with st.spinner("Examining the attachment…"):
                        result = api("POST", f"/v1/attachments/{result['document_id']}/classify")
                    entry["result"] = result
                    if (result.get("classification") or {}).get("kind") == "prescription":
                        entry["document"] = result
                    st.rerun()
        if entry.get("document"):
            review_document(entry, key)

# Use Streamlit's own bottom layout so the attachment button and input stay
# aligned with the conversation when the sidebar opens or the page scrolls.
with st.bottom.container(key="chat_composer"):
    attach_column, message_column = st.columns([1, 10], gap="small")
    with attach_column:
        with st.popover(
            "Attach image",
            icon=":material/link:",
            help="Attach a prescription or X-ray image",
            disabled=not active,
            width="stretch",
        ):
            st.write("Attach to this conversation")
            st.caption("PNG or JPEG · up to 10 MB. Aster identifies the image type automatically.")
            uploaded = st.file_uploader(
                "Prescription or X-ray image",
                type=["png", "jpg", "jpeg"],
                key=f"attachment_{st.session_state.get('upload_generation', 0)}",
            )
            if st.button(
                "Attach image",
                type="primary",
                disabled=not active or uploaded is None,
                width="stretch",
            ):
                send_attachment(uploaded.getvalue(), uploaded.name)
                st.rerun()
    with message_column:
        question = st.chat_input("Message Aster…", max_chars=4000, disabled=not active)
        if question:
            send_question(question)
            st.rerun()
    st.caption(
        "For information and research. Aster cannot diagnose, prescribe or calculate a personal dose."
    )
    document = st.session_state.get("active_document")
    if document:
        st.caption("Follow-ups use your confirmed transcription.")
        if st.button("Remove document context", key="detach_context"):
            st.session_state.pop("active_document", None)
            st.rerun()
