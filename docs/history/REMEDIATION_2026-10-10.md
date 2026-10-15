# Aster implementation and remediation — 10 October 2026

**Delivery status: implemented first remediation increment; full master request remains incomplete.** Both patients and students remain the product audiences. Research-paper assistance remains planned, not shipped by this increment. Qualified medical review remains pending.

## Implemented behavior

The browser still uses one conversation and a separate evidence panel. A task selector offers Understand and Study. Source-based practice responses show a real question and a collapsible self-assessment rubric/reference answer. The original architecture, local inference, temporary document ownership and confirmation requirements are preserved.

`AnswerService.answer` now plans bounded educational tasks and joins multipart responses deliberately. It passes generated, prepared and extractive answers through a terminal output check. Copied records containing treatment/dosing instructions are rejected wholesale; they are not truncated to hide exceptions. Claims must have valid attribution and either equal the complete cited passage or equal an existing validated prepared teaching note with the same source IDs. This conservative contract can reject legitimate paraphrases; evaluated synthesis remains future work.

The direct document-explanation service also applies the terminal guard. Existing generation validation still runs before the common guard. A 502/503 fallback cannot escape the terminal guard. These are deterministic safeguards, not complete semantic verification or calibrated clinical-risk detection.

For simple unqualified conjunctions, each requested part is retrieved separately. Covered and unsupported parts are returned explicitly. Population-qualified clauses and joined anatomical names are kept intact to avoid silently dropping context. General multipart reasoning, all ambiguity resolution and semantic contradictions are not solved by this planner.

Viva, quiz and revision requests can create a source-bound question and self-assessment reference from an eligible explanation. This initial activity asks the learner to explain the concept and its features; it is not a validated exam bank, adaptive quiz engine or automated grading system. Unsupported comparisons return insufficient evidence instead of a long excerpt labelled as a completed comparison.

Recognized “tell me more” follow-ups request detail and compare against the preceding claims. If the available answer repeats those claims, Aster explicitly says additional supported detail is unavailable. This repairs repetition but does not deliver every requested follow-up operation or guarantee increased depth.

The narrowly defined educational request “Explain what prescribe means” no longer triggers a personal-treatment refusal. Mixed requests that also ask for prescribing and personal diagnosis requests remain restricted. Actual glossary answer coverage is still limited by the available sources.

## Request flow and contracts

Browser → same-origin bridge → owned session → input policy → question plan → per-part/task retrieval → existing generation/source checks → terminal output validation → presentation → temporary session history.

Additive API fields:

- `ChatRequest.audience`: `understand` (default), `study`, or `research`. Research is accepted as planning metadata only; no research-paper endpoint is implemented. The UI exposes only shipped task choices.
- `question_plan`: version 1, original question, audience, topic, task, subquestions, qualifiers and requested depth.
- `status: partial`: supported material exists but named requested parts remain uncovered. Existing `ok` and failure states remain.
- `covered_parts`, `unsupported_parts`, `task_completion`, `outcome`, `validation` and terminal `rejection_codes`.
- `practice_item`: version, topic, question, source-bound expected concepts, rubric, source IDs and pending review state.

`StudyRecord` defines a bounded educational progress contract; persistent progress storage and UI are **not implemented**. TopicCapability, full EvidencePlan, full AnswerResult schemas and research-document contracts remain pending. These limitations are explicit rather than unused placeholders presented as features.

## Verification evidence

| Check | Actual result |
|---|---|
| Fresh baseline | 535 tests passed, one Starlette/httpx warning, 36.19 seconds |
| New initial regression tests before implementation | 9 failed, recording the missing guards/task behavior |
| Follow-up/evaluation regression additions before implementation | 3 failed; then repaired |
| Unsupported-claim terminal check before repair | 1 failed; then repaired |
| First integration run | 545 passed, 2 failed; comparison routing and legacy unsupported-topic metadata repaired |
| Final delivery source suite | **549 passed**, one existing Starlette/httpx warning, **54.45 seconds** (earlier source-support verification also passed in 50.77 seconds) |
| Whole-source Ruff | Passed; generated data and bundled/vendor artifacts are excluded explicitly |
| Frontend JavaScript syntax | `node --check frontend/web/app.js` passed |
| Published benchmark pilot | **14/20 correct**, accuracy 0.70, macro F1 0.5203, no unanswered predictions |
| Qualified human medical assessment | **Not measured** |
| Current live web bridge / browser | See acceptance evidence below; status finalized after execution |

The first unrestricted `ruff check .` also traversed vendored frozen-package code and returned 28,239 diagnostics; 20 were in project source. It is inappropriate to edit third-party frozen artifacts to satisfy application lint. The committed lint configuration now excludes generated `artifacts`, `data` and `.impeccable` directories; all project source, packaging, scripts and tests are checked. Existing import findings were repaired. Standalone script imports following the necessary repository-path bootstrap retain explicit E402 annotations. Pytest fixture discovery was preserved after fixing fixture import/redefinition findings.

Raw evidence: `artifacts/evaluation/remediation-2026-10-10/`. Tests isolate the developer environment. No published benchmark answer keys were placed in application retrieval.

## Automated medical evaluation

`backend/app/services/medical_evaluation.py` separately records attribution identity, exact-passage relationship, qualifier preservation for exact matches, task completion and pending clinical review. Exact matching is deliberately conservative: an ID match alone cannot validate a claim; paraphrases remain insufficient for this checker unless evaluated separately. Contradictions, external source truth, source currency and complete applicability are not automatically measured.

`scripts/evaluate_pubmedqa.py` downloads an isolated pinned repository snapshot, retains its licence, hashes the dataset, records the sample seed/IDs and model snapshot, and sends only questions and abstract contexts to local Ollama. Reference labels and long answers are excluded from prompts. Missing/invalid predictions count as unanswered and incorrect in the overall denominator. It reports accuracy, macro F1 and a confusion matrix.

The executed 20-item sample used PubMedQA revision `1cbae8e92f72f20c8d3747cbb3bf5bc53554d997`, dataset SHA-256 `8b3276be8942ebbd77f3ddcda12c1749bf0e490045a736fd8438ee40cf37a41d`, seed 20261010. This is a **development benchmark pilot**, not the official full test split, a locked final holdout or a medical-accuracy estimate. Training contamination is unknown. PubMedQA is a biomedical abstract-conditioned yes/no/maybe task with an expert-labelled subset, not a patient conversation assessment. [Official dataset description](https://pubmedqa.github.io/), [repository and licence](https://github.com/pubmedqa/pubmedqa).

MedHELM was inspected as a candidate framework, but task/dataset adapters and individual permission decisions are not implemented. WHO governance guidance was read as background; it is not a scoring instrument. TRIPOD-LLM full-text access was unavailable in this browsing attempt; no compliance claim is made. [MedHELM](https://crfm.stanford.edu/helm/medhelm/latest/), [WHO guidance announcement](https://www.who.int/news/item/18-01-2024-who-releases-ai-ethics-and-governance-guidance-for-large-multi-modal-models).

`scripts/evaluate_answer_evidence.py` exports per-claim findings and a small blank reviewer CSV for saved synthetic responses. It does not invent credentials or scores. The existing curriculum audit's blinded packs and credential-sensitive import workflow remain available for their compatible schemas. The new small CSV has no automatic score-import/qualification/adjudication system; completing that integration remains pending.

## F01–F21 remediation matrix

| Finding | Status | Implemented files / solution | Verification and remaining work |
|---|---|---|---|
| F01 product focus | Partially fixed | Scope retained; `index.html`, `schemas.py`, `question_plan.py` expose patient understanding/student study | Task UI available; research workflow and user validation pending |
| F02 curriculum coverage | Not started | Existing corpus preserved | No claim of new full-curriculum coverage; topic capability audit pending |
| F03 independent correctness | Blocked on external review; automation partially implemented | `medical_evaluation.py`, benchmark/evidence scripts | PubMedQA pilot executed; qualified review not measured, full benchmark integration pending |
| F04 evaluation independence | Partially fixed | Isolated benchmark snapshot, hash/seed/model evidence | Pilot explicitly labelled; independent locked patient/student/research suites pending |
| F05 safe fluent teaching | Partially fixed | `output_validation.py`, existing prepared notes | Exact passage/prepared-note guards; new reviewed cards and evaluated synthesis pending |
| F06 follow-up repetition | Partially fixed | `answers.py`, `api/chat.py` request depth and detect repetition | Regression passes; extra detail may abstain, broader operations pending |
| F07 multipart completion | Partially fixed | `question_plan.py`, `answers.py`, frontend coverage display | Explicit simple parts/partial results; complex/contextual decomposition pending |
| F08 brittle intent | Partially fixed | `policy.py`, study greeting branch | Narrow benign definition/greeting fixes; broad intent policy and glossary coverage pending |
| F09 learning loop | Partially fixed | `study.py`, practice rendering | Source-bound question/rubric delivered; topic browser, persistence and revisits pending |
| F10 handwriting | Not started | Existing confirmation/experimental boundaries retained | No new handwriting performance measurements |
| F11 imaging scope | Not started | Registered-asset restrictions preserved | Welcome text improved, existing research starter remains; imaging validation pending |
| F12 distribution gates | Blocked on rights/acceptance | Existing release safeguards retained | No frozen rebuild/public release; third-party rights and clean-machine tests pending |
| F13 size/startup | Not started | Existing runtime preserved | No measured size/startup improvement; teaching-only edition pending |
| F14 diagnostics | Not started | Existing request correlation retained | Sanitized category/export improvements pending |
| F15 broad lint | Fixed for current source tree | Ruff cleanup, `pyproject.toml`, whole-source CI lint | Full check passes; intentional standalone bootstrap annotations documented |
| F16 licence contradiction | Fixed | README now agrees with root MIT licence | Third-party restrictions preserved |
| F17 Git baseline | Not started | Workspace not initialized or pushed | Clean source inventory/secret review and safe initialization pending |
| F18 local assumptions | Partially fixed through preservation | Bounded local concurrency/session design retained | Multi-user hosting not implemented or claimed |
| F19 terminal safeguards | Partially fixed | `output_validation.py`, `answers.py`, `documents.py` | Four output-mode regressions pass; deterministic dosing/source guards, complete semantic applicability/ambiguity and future research outputs still pending |
| F20 task honesty | Partially fixed | Practice generation, unsupported comparisons, task/coverage fields | Viva task delivered; comparisons refused rather than completed; mechanism/research task validation pending |
| F21 patient answer relevance · P1 | Scoped engineering fix; independent clinical review pending | Typed intent/context contract, patient applicability store, shared terminal guard and bounded recovery, symptom presentation | Separate symptom evidence and patient/student regression evaluation; details and acceptance limits in [F21 report](F21_PATIENT_RELEVANCE.md) |

“Fixed” describes the scoped source change and engineering verification, not clinical validation. F03 remains open.

## Commands actually used

```powershell
& .venv/Scripts/python.exe -m pytest -q
& .venv/Scripts/python.exe -m pytest tests/test_remediation_core.py -q
& .venv/Scripts/python.exe -m pytest tests/test_teaching_precision.py tests/test_remediation_core.py -q
& .venv/Scripts/python.exe -m ruff check .
& .venv/Scripts/python.exe -m scripts.evaluate_pubmedqa --output artifacts/evaluation/remediation-2026-10-10/pubmedqa-pilot --count 20
```

The benchmark output directory must be new: the runner refuses to overwrite an existing result. It uses only local Ollama for inference; fetching the public dataset is inbound network traffic. No patient data is sent externally.

For a saved synthetic acceptance file:

```powershell
& .venv/Scripts/python.exe -m scripts.evaluate_answer_evidence artifacts/evaluation/remediation-2026-10-10/live-probes.json artifacts/evaluation/remediation-2026-10-10/evidence-pack
```

Python support declared by the project remains `>=3.11,<3.14`; these checks ran in the existing Python 3.13 environment. No dependency was added, model fine-tuned, snapshot replaced, repository pushed or public deployment performed.

## Remaining implementation order

1. Complete terminal applicability/product/population checks and comprehensive task contracts; preserve conservative abstentions.
2. Add evidence-backed comparisons, mechanism cards and explicit supported follow-up operations.
3. Complete locked patient/student/research evaluation sets, reviewer import/adjudication and benchmark permission/task adapters.
4. Implement session-isolated authorized paper ingestion, metadata provenance, summaries, comparisons, evidence tables and source-linked writing.
5. Add topic capabilities/browser and opt-in educational progress/export/delete without retaining patient documents.
6. Finish sanitized diagnostics, user-facing capability messaging and responsive/accessibility verification.
7. Benchmark focused startup/package changes, resolve exact asset rights and perform clean Windows/offline acceptance.

## Run the updated application

From `<repo>/`:

```powershell
.\start.ps1
```

Open `http://127.0.0.1:8501/`. Use the existing virtual environment and configured local assets; do not run a second copy while ports 8000/8501 are occupied. The frozen ValidationOnly artifact predates these source edits and is not an updated redistributable build.

## Current live acceptance

The updated source app was restarted and exercised through the same-origin browser bridge with ten synthetic questions and one follow-up, each independent sequence using a temporary session that the probe deleted. No real patient document was used.

| Journey | Actual result |
|---|---|
| Patient/general concept: epithelium | `ok`, prepared explanation with sources |
| Specific sulcular concept | `ok`, prepared explanation |
| Mixed osmosis/Dolo | `partial`, osmosis material retained, `Explain Dolo` explicitly uncovered; no dosing instruction emitted |
| Epithelium viva | `ok`, real practice question and source-bound rubric/reference answer |
| Oral epithelium quiz | `ok`, self-assessment activity |
| Revision help for apoptosis | `ok`, self-assessment activity |
| Comparison of apoptosis/necrosis | `insufficient_evidence`; not represented as completed comparison |
| Tell me more after epithelium | `insufficient_evidence`, explicit no-additional-detail explanation; no repeated claims |
| Study greeting | `ok`, practical topic invitation |
| Definition of prescribe | `insufficient_evidence`, rather than inappropriate personal-prescribing refusal; glossary coverage still absent |
| Personal oral-cancer question | `unsupported_input`, personal-diagnosis boundary retained |
| Research-paper flow | Not implemented; no runtime acceptance claimed |

Actual browser interaction selected Study, submitted the viva request and opened the rubric; sources remained in the right panel. Saved screenshot: `artifacts/evaluation/remediation-2026-10-10/viva-browser.jpg`. Actual JSON responses, readiness, acceptance assertions, evidence report and blank review batch are retained in the same artifact directory. Browser study/practice rendering was verified on the observed desktop viewport; comprehensive mobile, keyboard, screen-reader and contrast acceptance is not yet performed. The Impeccable detector reported the existing initially-empty preview image and incomplete linked-style resolution; it is not an accessibility certificate.

Observed live question times ranged from 0.01 to 8.98 seconds (the first concept query took 5.69 seconds). This small, mixed, nonrandom run is not a performance distribution. A current process working-set snapshot is retained in `runtime-memory.json`; peak memory and controlled cold/warm startup remain unmeasured. No frozen rebuild was performed, so no package size/startup improvement is claimed.

The running source app is available at `http://127.0.0.1:8501/`. The complete master scope remains open, with the implementation order above preserved for continued work.
