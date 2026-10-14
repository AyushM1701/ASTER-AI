# Verified baseline architecture — 13 October 2026

The baseline preserves the existing FastAPI `/v1` API, plain HTML/CSS/JavaScript frontend, local Ollama adapters and exact NumPy retrieval. The workspace has no Git repository; `artifacts/baselines/master-2026-10-13/source-checkpoint` preserves 326 screened source/config/test files. Credentials, private stores, raw material, model weights and executable distributions are excluded.

## Routes and guard boundaries

`backend/app/main.py` constructs session/workspace/reference/secondary/teaching/model/OCR/answer/X-ray services. It exposes `/health/live` and `/health/ready` and includes chat, sessions, documents, attachments, education and X-ray routers. Session ownership is a dependency on user operations.

`/v1/chat` checks policy, session-owned attachment confirmation and viva state before ordinary answering. Its document route rechecks ownership and revision; symptom questions cannot substitute a prescription explanation. Context-free questions receive a typed plan and follow-up context. `AnswerService.answer` performs policy, patient, facet composition, report terminology, prepared operations and general/extractive/Ollama routes. Its finalizer calls `output_validation.finalize` with trusted prepared units, parent records, metadata and holds. Generated validation errors withhold output; transport fallbacks receive separate validation. Existing prepared text identity checks do not authorize generated paraphrases.

MDS composition joins `question_plan`, `evidence_plan`, `prepared_evidence`, `answer_composer`, `progression` and the terminal guard. The evidence predicate requires topical coherent text, explicit scope and facet markers or inspected bindings. These are engineering signals, not independent semantic/clinical truth. The viva handler has its own state/validation contracts; negative grading and all alternative routes require continued regression testing.

Education routes implement opt-in saved attempts and literature projects/search/export. These do not establish complete uploaded-PDF appraisal, independently graded viva or nine-specialty essay coverage. Current uploaded image/document routes are primarily confirmation-based prescription handling; do not advertise them as a research-paper parser.

The current UI displays source-bound sections, comparison cells, gaps and progressive explanations through safe DOM rendering. UI visibility must be measured in browser tests; backend completion cannot certify display by itself. OCR and registered chest imaging remain bounded research modules.

## Fresh baseline evidence

`.venv/Scripts/python.exe -m pytest -q`: 1,019 passed, one existing Starlette/httpx deprecation warning, 66.59 seconds. `.venv/Scripts/python.exe -m ruff check .`: clean. `node --check frontend/web/app.js` and `node --check frontend/web/ui-interactions.js`: exit zero. API live/ready and Ollama tags requests returned HTTP 200.

Historical supplied evaluation independently recounted: 107 cases, 111 turns, 16 substantive and 3 substantive complete, 62 prepared units/22 bound, 660 candidate rejects, 108 gap entries; response file hash matches the historical summary. This is verification of stored artifacts, not a fresh medical evaluation. Exact source file hashes and health metadata appear in `artifacts/baselines/master-2026-10-13/repo_state.json`.
