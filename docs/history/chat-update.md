# Presentation update

The original chat implementation notes below describe the earlier Streamlit UI.
The default presentation now follows the approved Figma redesign; see
[web redesign](web-redesign.md). The local inference and API workflows remain.

# Single-chat update

User requested a single chat with a link attachment control and automatic
prescription/X-ray classification. The interface now implements that conversation
flow using native accessible Streamlit widgets and preserves the dark ambient
palette. Text and model content render as plain text.

The attachment classifier consumes image pixels through a local Ollama vision
model, with a strict four-category schema. It does not use the filename or make
medical findings. Prescriptions proceed to Tesseract and explicit confirmation;
X-rays proceed to registered-image eligibility and research setup checks. Unclear
and unsupported images abstain; model outages offer retry on the same owned image.

General conversation can use pretrained model knowledge outside the nine-note
starter library, clearly marked with no verified local source citations. This
is not training a new model, nor evidence of universal or clinically accurate
answers. Model classification does not validate permissions, view, age or diagnosis.

Core regression checks cover pixel-based routing through the API boundary,
confirmation and ownership, other/uncertain routing, malformed output and retry,
uncited general chat, policy gates, visible message history and attachment context.
Model-level demonstrations and installed digests are recorded separately from
these deterministic engineering tests.

Actual local Qwen3-VL 2B Instruct demonstrations passed on 6 October 2026:
general conversation (3.92s), source-backed education (4.01s), synthetic medicine
document routing plus real OCR (5.25s), and one CC0 chest radiograph category
routing (4.88s). The prescription required confirmation before source-linked
explanation, with missing duration preserved. The X-ray correctly stayed outside
specialist scoring because it has no reviewed registration. These four timings
are single observations, not a latency benchmark or model accuracy estimate.
See `artifacts/evaluation/chat-live-smoke.json` and the installed digest in
`configs/models.yaml`. The synthetic sample was first rejected because of its
watermark; the routing prompt now explicitly distinguishes workflow category
from authenticity. Broader classification validation remains pending.

Review regressions cover edits during contextual generation, overlapping
classification/extraction, invalid imaging model outputs, and additional personal
dosing output patterns. These language checks are engineering defenses, not
medical triage validation or a proof against every unsafe wording.
