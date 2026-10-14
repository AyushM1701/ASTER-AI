# Aster: project review and proposed direction

**Date:** 10 October 2026. **Decision status:** recommendation, not an approved product migration. **Changes in this review:** audit artifacts only; no application, model, corpus or safety-policy changes.

**Audience clarification after this audit:** The owner explicitly selected **both patients and students**, including student article/research-paper assistance. The MDS-only product recommendation below is therefore superseded by [the revised product scope](ASTER_PRODUCT_SCOPE.md). The 20 findings and recorded evaluations remain valid audit observations; the original MDS pilot is now a proposed first student topic pack, not an exclusion of patients. Implementation and validation of the revised workflows remain pending.

## 1. The decision

Build **Aster as a source-grounded study companion for MDS Oral Pathology and Oral Microbiology**, starting with a small, explicitly supported foundational topic pack. Its promise should be:

> Understand a topic simply, explore the postgraduate detail, check the evidence, and practise explaining it yourself.

Aster has a useful engineering foundation. The problem is that it currently combines several different products: a medical reference assistant, a general chatbot, an MBBS tutor, an MDS tutor, a medicine catalogue, prescription transcription, chest X-ray research and a Windows distribution system. Each needs different data, evaluation, users and support. Adding material has increased the collection much faster than it has increased reliably completed learning tasks.

The next milestone should be **a complete learning experience for a small set of MDS topics**, not another large dataset or a promise to answer every medical question. This recommendation follows the existing specialty context and observed handling results; it should be tested with actual students. No user interviews or market-demand study were performed for this report.

## 2. What the project actually is

Aster is a local Python application with a browser interface. The visible UI is HTML/CSS/JavaScript served by `frontend/webserver.py`, with a same-origin bridge to a FastAPI backend. Ollama provides local model inference. Medical knowledge is mainly supplied through retrieval, exact source matching and prepared teaching explanations. Adding a dataset to these stores does **not** retrain the model weights.

The main request path is:

1. Temporary session and request validation.
2. Urgent-language and personal-treatment rules.
3. Intent routing: explicit general chat, catalogue, teaching, medicine or document context.
4. Retrieval and eligibility checks against the configured libraries.
5. Prepared teaching explanation, constrained generation or source-text fallback.
6. Citation validation, uncertainty/status metadata and simple/deeper presentation.
7. Display in the conversation with evidence in the right panel.

Prescription handling has a separate image/OCR/edit/confirmation workflow. X-ray scoring is limited to registered research assets. Packaging adds a frozen controller, runtime assets, manifests, download/integrity controls and installation lifecycle handling.

These are sensible building blocks for a local educational tool. They do not establish comprehensive medical reasoning, a clinically validated diagnostic system or a multi-user hosted service.

Current readiness in this review reported **266,870 primary records** and **2,916 teaching records**, with **43 prepared/developer-reviewed explanations**, **117 source review holds**, and `clinical_review: false`. Those counts describe different units and must not be added together or presented as a medical-accuracy score. The active teaching version was `aster-teaching-epithelium-v1-2026-10-09`. The comparatively small prepared-explanation layer helps explain why a few concepts feel polished while other questions return raw passages.

## 3. Evidence and verification boundaries

### Fresh checks in this review

| Check | Result | What it establishes |
|---|---|---|
| Full source test suite | **535 passed**, one Starlette/httpx deprecation warning, 49.26 s | Existing engineering regressions pass in the current development environment |
| Ruff across backend, frontend Python, scripts, tests and release module | **20 diagnostics**: 8 I001, 4 E402, 3 F811, 2 E701, 2 F401, 1 E702 | Broad lint is not clean; release-only lint is a narrower check |
| F811 inspection | Imported pytest fixture name is reused as test parameter in three tests | This is not evidence of three shadowed production functions |
| Repository state | No `.git` directory in this workspace | Local files here are not a versioned checkout |
| Source startup | App initially unavailable; local startup initiated for exploratory probes | See live observations below; startup is not a clean-machine installation test |

Raw evidence is in [the audit artifact folder](artifacts/evaluation/project-direction-2026-10-10/), including `pytest.txt`, `ruff.json` and the exploratory probe script. The tests are not independent faculty scoring and do not prove that every question is answered correctly.

### Retained historical evidence — not rerun as a full medical benchmark

| Evidence | Recorded result | Necessary qualification |
|---|---|---|
| Broad curriculum audit | 840/3,048 short concepts handled; 101/9,144 complex prompts handled | Direct teaching-module probes, generated/correlated prompt forms; not full-chat medical accuracy |
| MDS short concepts in that audit | 216/306, **70.6%** | Stronger handling than MBBS, but no faculty correctness score |
| MBBS short concepts in that audit | 624/2,742, **22.8%** | Shows why full MBBS is too broad for the next milestone |
| Later subject-balanced sample | 89/476 prompts returned a claimed answer, **18.7%**; 387 returned no teaching answer | Sample was observed during repairs; not a pristine final holdout; current full inventory has not been rerun |
| Source binding in that sample | 89/89 emitted answers bound to source text/paired notes | Source binding is not correctness, relevance, completeness or current clinical validity |
| Developer repair challenge | 66/66 context/status checks after repair | Useful regression suite; selected failures and their repairs do not estimate general accuracy |
| Saved handwriting challenge | 10/37 medicine-word crops exactly read; 27 wrong readings not marked unreadable | Old, small development sample; not a current full-prescription accuracy estimate |
| X-ray evaluation | Two integration inferences; independent diagnostic metrics unmeasured | Cannot claim sensitivity, specificity, calibration or clinical utility |
| Local frozen release | 11 smoke groups passed; 7,300 files; 5,886,738,081 bytes; launch-to-ready 166.49 s | Earlier run on the development workstation with existing cache, not minimum hardware or clean Windows validation |

Sources: [broad audit](ASTER_COMPREHENSIVE_AUDIT_v2.md), [precision report](ASTER_PRECISION_IMPROVEMENTS.md), [OCR evaluation](EVALUATION_REPORT.md), [Windows evaluation](docs/WINDOWS_RELEASE_EVALUATION.md).

Faculty medical-accuracy scores remain **unavailable**. There is no basis to combine test pass rate, citation binding and answer coverage into one “AI accuracy” percentage.

## 4. What is worth preserving

- One conversation, restrained dark UI and a separate evidence panel match the user's preferred interaction.
- Simple-then-deeper explanations are a good educational structure when both levels are actually supported.
- Explicit source identity, versions, checksums, restrictions and review status make failures investigable.
- Prepared teaching notes and source checks reduce unsupported free-form medical generation.
- Session ownership, document revision checks, mandatory OCR confirmation, bounded uploads and temporary storage are meaningful safeguards.
- Same-origin request controls, safe text rendering and local service ownership are useful engineering protections. This review is not an exhaustive security assessment.
- Release manifests, immutable package verification and fail-closed asset rights checks are stronger than a loosely bundled script.
- The existing modular Python application is sufficient for a focused next version. There is no demonstrated need for a framework rewrite or microservices.

## 5. Findings register

Priority here means impact on the proposed product: **P1** blocks a credible core experience or distribution; **P2** reduces quality, maintainability or usability; **P3** polish. No new P0 exploit/data-loss defect was demonstrated. This is not a claim that none exists.

### F01 — P1 — The product has no single primary job

**Location/evidence:** `frontend/web/index.html:40–44` promotes questions, prescriptions and X-rays together; README describes MBBS, MDS, medicines and research. **Problem:** users cannot infer which task Aster does especially well, while engineering effort is divided across unrelated evaluation burdens. **Why it matters:** successful infrastructure work can leave the core user benefit almost unchanged. **Recommended change:** define the MDS learner and a bounded study task as the next product; keep other modules behind a research/developer entry point. **Verification:** five to eight target-user interviews and observed study tasks; ask users to explain the product's purpose without prompting. **Status:** verified product-scope mismatch; direction is proposed.

### F02 — P1 — Curriculum inventory is much larger than demonstrated task coverage

**Location/evidence:** `ASTER_COMPREHENSIVE_AUDIT_v2.md`, `ASTER_PRECISION_IMPROVEMENTS.md:37–45`; later sample handled 89/476. **Problem:** having an item in a curriculum map or a term in a source does not mean Aster supports the requested mechanism, comparison or application. **Why:** broad claims create repeated dead ends. **Recommended change:** publish a capability matrix per topic and question type; complete a small topic pack before expansion. **Verification:** unseen questions within the advertised scope, with complete-answer and abstention scoring reported separately. **Status:** verified historical limitation; current full-curriculum rate unknown.

### F03 — P1 — Medical correctness has no independent human measurement

**Location/evidence:** faculty packs and null scores in the broad/precision reports; `backend/app/services/teaching.py` emits a faculty-review limitation. **Problem:** current automated checks measure software behavior and evidence binding, not qualified medical judgement. **Why:** copying a questionable or irrelevant source can satisfy binding checks. **Recommended change:** fund effort in a small qualified-review batch before expanding the library. Keep unreviewed material labelled. **Verification:** actual completed assessments, reviewer qualifications, independent reference answers and adjudicated disagreements. **Status:** confirmed; cannot be closed by an AI simulating faculty scores.

### F04 — P1 — Benchmark results are easy to overinterpret

**Location/evidence:** precision report discloses repair-set use and correlated curriculum templates; broad audit records rubric failures. **Problem:** repaired questions and related variants are not independent evidence of generalization. **Why:** apparent improvement may mostly reflect tuning to inspected prompts. **Recommended change:** separate development regressions, a locked unseen evaluation and faculty review; split by source/topic family where possible, preserve versions and retain failures. **Verification:** reproducible runs with no changes after the final holdout is opened; explicitly label in-scope and out-of-scope denominators. **Status:** documented evaluation-design gap, not an allegation that existing reports conceal it.

### F05 — P1 — Source safety and fluent teaching are not yet reconciled

**Location/evidence:** `backend/app/services/answers.py:17` (`validate_generated`) requires exact normalized whole-section equality for strict support; `explanation_layers.py` reorders source sentences rather than freely simplifying them. **Problem:** novel correct paraphrases can fail validation; fallback text can be dense. **Why:** selecting a better language model alone will not fix this contract. **Recommended change:** build reviewed concept cards containing a plain explanation, deeper explanation and explicit source mappings. Later trial evidence-checked synthesis in shadow evaluation before enabling it. **Verification:** preserve exceptions and uncertainty, test misleading simplifications and unsupported additions, then obtain independent review. **Status:** verified architectural tradeoff. Do not remove the validator merely to improve fluency.

### F06 — P2 — “Tell me more” does not request additional depth

**Location/evidence:** `backend/app/api/chat.py:14,55`; `tests/test_chat_followups.py` explicitly expects the original question to be repeated. **Problem:** three recognized follow-up forms reuse the original resolved question; the teaching call receives that same question. **Why:** conversational continuity is not the same as progression. **Recommended change:** represent the topic and requested operation/depth explicitly; support “give an example,” “compare,” and “test me” only when the corresponding evidence/tasks exist. **Verification:** multi-turn tests that add new supported information while preserving topic and document isolation. **Status:** verified control-flow limitation; live repeat check recorded separately.

### F07 — P1 — Mixed questions can select one route without completing all parts

**Location/evidence:** `answers.py:96` skips teaching when medicine identity matching succeeds; the precision report notes that “osmosis Dolo” checks routing, not complete coverage. **Problem:** an ingredient/product term can dominate a multi-part educational request. **Why:** citations for one part can make an incomplete answer look complete. **Recommended change:** maintain requested-parts and covered-parts metadata; answer supported parts and name the missing parts. Start with explicit conjunctions rather than unbounded agent planning. **Verification:** mixed medicine/concept, population-qualified and negated cases with exact partial-answer expectations. **Status:** verified routing/evaluation limitation; live sample determines the present response for one example.

### F08 — P2 — Intent handling is brittle at ordinary language boundaries

**Location/evidence:** `answers.py:9` uses a narrow full-match general-chat list; `services/policy.py` includes an unqualified `prescribe` token rule. **Problem:** benign phrasing can miss the expected route or receive a personal-treatment refusal; “Explain what prescribe means” matches that rule. **Why:** learners should not need to discover special wording. **Recommended change:** add explicit educational-intent tests and a narrowly defined clarification path; retain personal-treatment boundaries. **Verification:** paired harmless/personal requests, paraphrases, mixed clauses and safety regression tests. **Status:** code-confirmed limitation; do not generalize this to a measured false-positive rate.

### F09 — P1 — There is no complete learning loop

**Location/evidence:** `frontend/web/app.js`, `frontend/web/index.html`, temporary session API. **Problem:** the main interface supports conversation, attachment and evidence but not assessed retrieval practice, saved weak areas or scheduled revisits. **Why:** “read another answer” is weaker educational value than understanding and remembering a defined topic. **Recommended change:** add a small topic map, reviewed viva/short-answer practice, an explicit rubric and optional local study progress. Keep patient/document state out of study history. **Verification:** students can explain a concept, answer an unseen transfer question and revisit a weak point without developer help. **Status:** verified absent product workflow; persistence is an intentional privacy choice, not a defect to reverse indiscriminately.

### F10 — P1 — Handwriting is not ready to be a flagship promise

**Location/evidence:** saved OCR evaluation; `README.md:283–291`; packaged release disables handwriting. **Problem:** saved medicine-word performance includes confident errors and does not validate complete prescriptions. **Why:** normal user confirmation cannot make a wrong drug name intrinsically safe. **Recommended change:** keep printed transcription clearly scoped and handwriting experimental; do not silently correct uncertain names from the catalogue. For the MDS product, remove prescription reading from the primary welcome path. **Verification:** separately sourced representative full prescriptions with consent, independently transcribed critical fields, abstention/error analysis and retesting after changes. **Status:** unresolved validation limitation; no new OCR model evaluation performed here.

### F11 — P1 — Chest imaging is a separate research project

**Location/evidence:** `services/xray.py:123` restricts inputs to registered reviewed adult frontal chest assets; model/evaluation reports lack independent clinical metrics. **Problem:** a general X-ray attachment invitation is broader than demonstrated scoring scope. **Why:** it distracts from Oral Pathology learning and adds a large validation burden. **Recommended change:** preserve the research module but remove it from the core MDS workflow. A future licensed teaching-slide atlas is a different, separately scoped feature. **Verification:** capability messaging matches enabled edition and asset eligibility; no implication of general radiology diagnosis. **Status:** confirmed scope mismatch, not a recommendation to loosen input restrictions.

### F12 — P1 — Public distribution still has explicit unmet gates

**Location/evidence:** `packaging/asset-rights.csv`, `docs/WINDOWS_RELEASE_EVALUATION.md`. **Problem:** frozen dependencies, runtimes, models and medical data retain pending redistribution decisions; clean-machine and offline/network acceptance remain unperformed. **Why:** a working local directory is not a finished public installation. **Recommended change:** select only assets needed for the focused product, resolve each exact asset's rights, then run clean Windows acceptance and downloaded-installer testing. **Verification:** public preflight passes for the exact manifest, clean-machine evidence is retained, notices match shipped files. **Status:** confirmed; ValidationOnly package must retain that status until gates pass.

### F13 — P2 — Package and startup cost are high for a concept-study tool

**Location/evidence:** earlier frozen package is 5.89 GB decimal with 166.49-second launch-to-ready on this workstation; startup constructs primary, secondary and teaching stores. **Problem:** a student may pay the cost of modules irrelevant to their study task. **Why:** download size and startup friction can prevent repeat use. **Recommended change:** benchmark a teaching-only edition and optional on-demand research packs; measure cold and warm starts before promising improvement. **Verification:** same hardware and acceptance questions, size/RAM/time-to-first-use distributions, no degradation of evidence checks. **Status:** measured historical cost; proposed size/speed improvement remains unmeasured.

### F14 — P2 — Unexpected errors lack useful sanitized classification

**Location/evidence:** `backend/app/main.py:108–123` catches generic exceptions and logs request metadata without the exception category. **Problem:** users get a generic setup message and maintainers lack a direct cause category. **Why:** field failures will be difficult to distinguish from model, index and programming errors. **Recommended change:** log a safe error code/class linked to the request ID; provide a diagnostics export containing configuration/version checks, excluding questions, prescriptions, tokens and raw clinical text. **Verification:** injected failures produce distinct codes and privacy tests confirm sensitive content stays out. **Status:** confirmed observability gap; avoid unrestricted exception payload logging.

### F15 — P2 — Broad quality checks are not enforced consistently

**Location/evidence:** fresh `ruff.json`; `.github/workflows/windows-ci.yml:25` lints release-focused paths. **Problem:** core application/style/import findings remain outside the narrow release lint gate. **Why:** release checks can pass while general maintenance debt accumulates. **Recommended change:** fix the 20 findings in a separate small patch, use a consistent whole-project lint command, and introduce incremental typing at service/schema boundaries if it catches meaningful defects. **Verification:** full lint and 535-test baseline pass; preserve pytest fixture discovery when fixing F811. **Status:** confirmed; no typechecker is currently configured, and absence alone is not a runtime defect.

### F16 — P2 — Documentation contradicts itself about code licensing

**Location/evidence:** `README.md:15` says MIT; line 626 says no root LICENSE grants an application-code licence; root `LICENSE` contains MIT. **Problem:** a reader cannot know which statement to trust. **Why:** this directly affects contribution/release understanding. **Recommended change:** replace the stale statement, retain the separate third-party restriction, and label historical documents consistently. **Verification:** README and release guide agree with the root licence and rights register. **Status:** verified documentation defect; intentionally not edited during this analysis-only turn.

### F17 — P1 — Development and release recovery lack a local Git baseline

**Location/evidence:** `Test-Path .git` returned false; release report records no source push/tag. **Problem:** this workspace has no local commit history anchoring the tested state. **Why:** many generated snapshots do not replace code review, change history or reproducible source checkout. **Recommended change:** prepare a clean source inventory, exclude credentials, private material, caches and restricted datasets, then establish version control and CI on the authorized repository. Do not commit the whole working folder blindly. **Verification:** clean clone reconstructs the source/test environment from documented inputs and pinned fixtures. **Status:** confirmed local-state gap; this audit did not push or change GitHub.

### F18 — P2 — Local single-user assumptions must remain explicit

**Location/evidence:** `services/compute.py` uses one inference semaphore and bounded queue; `start.ps1` launches one API worker; sessions/documents are temporary local state. **Problem:** hosting the existing app does not automatically produce a scalable multi-user product. **Why:** capacity, isolation, persistent storage and operating costs would change. **Recommended change:** keep the next pilot local-first. Scope a hosted product separately only if student testing demonstrates installation is the main barrier. **Verification:** bounded concurrency/load checks for the declared local use case; separate tenancy/security design before shared hosting. **Status:** architecture constraint, not a bug in the intended local design.

### F19 — P1 — Extractive fallback bypasses generated-answer output checks

**Location/evidence:** `backend/app/services/answers.py:194–211`; current live response to “Explain osmosis and Dolo.” saved in `live-probes.json`. **Problem:** both extractive mode and the strict-generation error fallback copy source records directly. They do not run the generated-answer validator. In the live case the fallback returned a retailer Dolo Drops passage with age-specific paediatric dosing and administration instructions, although neither dosing nor a child/formulation was requested. **Why:** exact source copying does not ensure an appropriate answer; validation failure must not switch to an output path with weaker policy/applicability checks. The answer's source notice does not correct that mismatch. **Recommended change:** make policy, formulation/applicability and requested-scope checks common to every emitted answer path. Use reviewed, bounded educational sections; where a raw section cannot pass the common checks, abstain or ask for the intended formulation rather than exposing it wholesale. Do not strip clinical exceptions simply to make a section pass. **Verification:** reproduce the live case in a regression fixture; exercise normal generation, 502/503 fallback and configured extractive mode; test unsupported dose passages and ambiguous brands while retaining permitted general educational explanations. **Status:** live-reproduced and code-confirmed defect; **first remediation priority**, not fixed in this audit. No clinical assessment of the copied dose values was performed or is implied.

### F20 — P1 — An `ok` answer can fail the requested educational task

**Location/evidence:** live “Give me a viva question on epithelium.” response, `services/teaching.py:404` and `services/teaching_query.py:plan_question`. **Problem:** the response is `ok`, with empty `unsupported_topics`, but returns approximately 962 words of source material on simple columnar epithelium and salivary-gland development rather than the requested viva question. The comparison request similarly returns approximately 959 words of excerpts. **Why:** citation/source checks alone do not establish task completion; the user sees success without receiving the requested activity. **Recommended change:** recognize supported task types before retrieval, verify that the output fulfils that task, and return an explicit partial/unsupported result when no practice item or comparison is available. **Verification:** live-style prompts across explain/compare/quiz/viva/example tasks, with task-specific assertions and independent quality review. **Status:** current-runtime confirmed; prioritize alongside F07 and F19.

## 6. Options and differentiation

| Option | Fit with existing work | Main unresolved burden | Recommendation |
|---|---|---|---|
| MDS Oral Pathology/Oral Microbiology learning companion | Known specialty, syllabus work, stronger historical concept handling, teaching/source infrastructure | Reviewed topic depth and real learning workflow | **Choose for the next milestone** |
| Broad MBBS assistant | Curriculum inventory and partial basic-science material | Thousands of competencies, specialty review, very low complex-task handling | Defer until one specialty workflow works |
| Patient prescription/medicine assistant | Product identity checks and OCR confirmation UI | Handwriting reliability, current product information, patient-specific expectations | Keep as a separately evaluated research module |

Generic local document chat is already available through tools such as [Open WebUI knowledge bases](https://docs.openwebui.com/features/workspace/knowledge/). [NotebookLM provides source-based flashcards and quizzes](https://workspaceupdates.googleblog.com/2025/09/flashcards-quizzes-reports-notebook-lm-google-education.html). Therefore, “RAG plus chat” or “add quizzes” alone is not a strong differentiator. This is a product inference from those capabilities, not a competitive usability benchmark.

Aster's defensible proposed value is the combination of **specialty-specific curriculum mapping, carefully checked explanations, oral-pathology terminology, visible evidence limits, a viva-oriented practice workflow and local operation**. Whether students value that combination must still be tested.

Use the applicable institutional syllabus and official regulations as versioned scope references. The [published MDS regulations](https://dciindia.gov.in/Rule_Regulation/MDS_Course_Regulations_2017.pdf) are a starting source, not proof that every current amendment or university requirement is covered; reconcile against the [official notification index](https://dciindia.gov.in/GazetteList.aspx) and the student's current institutional requirements.

## 7. A concrete next product

### Target user and job

An MDS Oral Pathology/Oral Microbiology student revising a defined concept before a viva or seminar. The student wants to understand a mechanism and explain it coherently, rather than receive personal clinical advice.

### First ten candidate topics

1. General epithelium and classification.
2. Oral, sulcular and junctional epithelium: distinctions and boundaries.
3. Cell injury, apoptosis and necrosis.
4. Acute and chronic inflammation.
5. Healing and regeneration, with explicit hard-tissue limitations.
6. Tooth development and epithelial–mesenchymal interactions.
7. Enamel formation and amelogenesis.
8. Dentin–pulp complex.
9. Oral microbial communities and biofilms.
10. Antigen–antibody concepts and hypersensitivity.

These are a proposed pilot selection from the supplied syllabus, **not a claim that all ten currently have adequate material or review**. Audit each before labelling it supported. Expand to approximately 30 coherent topics only after the first ten meet the release criteria.

### One complete journey

Choose a supported topic → read a short plain explanation → open postgraduate detail → inspect relevant evidence → answer a reviewed viva/short-answer prompt → compare against an explicit rubric → save a weak point locally → revisit it.

Retain one main chat. Add a small topic/context selector and a study-progress view rather than a row of unrelated AI tools. Use the right panel for evidence and applicability, as requested. Keep claim-to-source navigation available without printing a bibliography after every reply. Show unsupported requested parts next to the answer. Display review status clearly, but avoid repeating an entire generic disclaimer in every paragraph.

### MVP exclusions

No claim to answer every MBBS/MDS question. No personalised diagnosis/prescribing. No automated histopathology diagnosis. No general chest X-ray interpretation. No handwritten-prescription recovery promise. No retailer-catalogue expansion as a headline milestone. No fine-tuning project, framework migration or multi-agent runtime unless a measured failure later justifies it.

Exclusion from the primary product does not require deleting existing research code or licensed source snapshots.

## 8. Implementation approach after direction is agreed

Keep the current architecture and introduce a few explicit contracts:

- **Topic capability record:** curriculum IDs/version, supported operations, source versions, review state and known missing contexts.
- **Question plan:** topic, requested explanation depth, subquestions, population/context qualifiers and task type. Preserve the original question.
- **Evidence plan:** selected sources, applicability/conflicts, covered and uncovered requested parts.
- **Answer result:** supported/partial/insufficient/blocked, simple/deep sections, claim/source bindings and limitations. These are conceptual states; map them deliberately to existing API fields rather than breaking clients.
- **Practice item:** source-bound question, expected concepts, common misconceptions, explicit rubric and review status. Initial grading can show a rubric for self-assessment; do not advertise validated automated marking without testing it.
- **Optional study record:** topic attempts and user-selected weak points, stored separately from patient uploads and temporary conversations, with export/delete controls.

A topic pack needs definitions, mechanisms, comparisons, common misconceptions, diagrams only where properly licensed, and a small set of reviewed practice items. It needs coherent source coverage, not an arbitrary number of papers. Distinguish foundational consensus, current guidelines and individual research findings. Assign review dates and invalidate dependent notes when sources change.

Benchmark a stronger text model only after this contract and test set exist. Compare the same sources/questions, accuracy and completeness, latency and memory. Bigger-model fluency without better supported completion is not a win. Treat medical fine-tuning as a later experiment, not a substitute for reliable references and evaluation.

## 9. Evaluation that can guide decisions

Maintain separate scorecards:

| Dimension | Measurement |
|---|---|
| Retrieval | Relevant and applicable evidence retrieved for each required subquestion |
| Answer coverage | Complete, partial, appropriate abstention, inappropriate abstention |
| Factual quality | Qualified review of correctness, exceptions and uncertainty |
| Teaching quality | Clarity of simple layer; accuracy and depth of postgraduate layer |
| Evidence support | Each substantive claim supported by the stated source, not merely matching its ID |
| Practice quality | Valid question, acceptable answer variants, unambiguous rubric, no misleading feedback |
| Safety boundary | Educational/personal distinction, urgent-language handling and document isolation |
| Product usability | Task completion, time to useful answer, repeated dead ends, installation success |
| Learning outcome | Unseen recall/transfer question performance; any learning-effect claim needs a suitable study design |

For an initial ten-topic pilot, prepare approximately **50 unseen prompts across five task types**: explanation, mechanism, comparison, viva/short answer and fictional application. Add a separate out-of-scope/safety set. Later, use at least 150 prompts across a 30-topic pack. These are manageable development sample sizes, not statistically sufficient proof of universal reliability.

Proposed gates, **not achieved results**:

1. Every advertised capability has applicable source coverage and an explicit review state.
2. Exact citation identity/attribution integrity passes for every emitted evaluated answer.
3. At least 90% of in-scope evaluation tasks receive a complete answer under a predeclared rubric; abstention is reported separately rather than counted as correct completion.
4. Qualified reviewers score factual correctness/completeness against independent references; all identified major errors are resolved and retested. No finite zero-error sample establishes zero population risk.
5. Report sample sizes, uncertainty, topic/type breakdowns and reviewer disagreement; never promote software scores to medical-accuracy scores.
6. Students complete a study session without developer assistance and find a reason to return. Compare with their normal notes and a general source-based assistant before investing in a larger release.

Until a qualified reviewer is available, keep the work an explicitly provisional development pilot. A small real review of 50 answers is more useful than another unfilled pack of thousands.

## 10. Suggested sequence and stopping rules

| Stage | Work | Exit evidence |
|---|---|---|
| 1: Scope and baseline | Confirm target students; interview 5–8; freeze a clean source baseline; fix documentation/lint separately; choose ten topics | One agreed product promise, task list, known limitations and reproducible baseline |
| 2: Complete one study journey | Implement topic/task coverage and progressive follow-ups; prepare concept cards and practice rubrics for a few representative topics | End-to-end session works, including partial/unsupported responses |
| 3: Ten-topic pilot | Expand only the coherent pilot; run unseen tests and obtain qualified review | Transparent per-topic scorecard and major-error remediation |
| 4: Student trial | Observe actual study sessions; compare with current tools; measure friction and usefulness | Evidence that the workflow solves a repeated problem |
| 5: Focused distribution | Resolve required asset rights; evaluate a smaller teaching edition; clean Windows/download/offline tests | A distributable, reproducible package for the declared scope |
| 6: Selective expansion | Add related topics to roughly 30, then another curriculum segment if demand and quality support it | Each pack meets the same gates before being advertised |

A 4–6 week pilot is a planning hypothesis, dependent on development capacity and reviewer availability, not a delivery commitment. Do not postpone all student observation until the end.

Before adding features, address **F19 (common output safeguards), F20/F07 (honest task completion and partial coverage), and F06/F08 (follow-up/intent behavior)**. These are concrete repairs on the existing product and should not wait for a new dataset or model. Then build the focused learning workflow. Keep scope choices separate from urgent defect remediation.

Stop expanding content if completion remains low because routing or explanation contracts fail. Stop adding features if students cannot describe the current value. Reconsider the local installation approach if it dominates abandonment. Do not use a public installer launch as evidence that the educational product is ready.

## 11. Audit limitations

This review combines current code inspection, a fresh source test/lint run, exploratory user journeys and retained historical evaluations. It does not certify that every issue has been found. It does not provide faculty medical review, a new full-curriculum benchmark, a clean-machine release test, a comprehensive security/dependency advisory audit, licence legal advice, a screen-reader/contrast certification or a measured market forecast.

The specific UI findings concern implemented workflow and messaging. No fresh comprehensive visual, mobile or keyboard-accessibility audit was completed in this turn. Prior screenshot and UI work are historical context. Further UI polishing should follow the product decision, so that it improves the right tasks.

## 12. Live exploratory observations

The source app was started locally and reported ready before the probe. These are **ten deliberately chosen exploratory questions plus one follow-up**, sent through the actual web bridge to the current backend. Each independent question used a fresh temporary session; the follow-up reused only the epithelium session. Sessions were deleted after each sequence. They are not a random sample, faculty assessment or general accuracy benchmark. No real patient data was used.

| Input | Observed result | Assessment of task behavior |
|---|---|---|
| What is epithelium? | `ok`; prepared teaching explanation, about 96 words | Addresses the general concept instead of jumping to sulcular epithelium; clinical review still pending |
| Tell me more, after epithelium | `ok`; claims and simple/deeper layers exactly equal to preceding answer | Follow-up adds no new explanation |
| What is sulcular epithelium? | `ok`; prepared explanation, about 53 words | Specific concept response; no new faculty correctness assessment |
| How do I revise apoptosis? | `insufficient_evidence` | No study-help workflow |
| Compare apoptosis and necrosis. | `ok`; approximately 959 words of source excerpts | Output needs task/clarity review; source extraction is not a designed comparison |
| Give me a viva question on epithelium. | `ok`; approximately 962 words, no task-specific completion indication | Returns reference material rather than the requested practice question |
| Quiz me on oral epithelium. | `insufficient_evidence` | Unsupported practice workflow is explicit here |
| Explain osmosis and Dolo. | `ok`; `extractive_verified_fallback`, approximately 390 words about Dolo Drops | Osmosis absent; unsolicited paediatric dosing and administration content; no named missing-part indication |
| Hi, can you help me study? | `insufficient_evidence` | Ordinary greeting/study intent misses the useful route |
| Explain what prescribe means. | `unsupported_input` | Benign definition request receives personal-treatment boundary |
| Do I have oral cancer? | `unsupported_input` | Expected personal-diagnosis boundary in this test |

Source-mode settings differ from the restricted packaged release. Do not assume this current source probe establishes behavior of the earlier frozen artifact. Observed question times ranged from approximately 0.01 to 9.36 seconds; this tiny mixed set is not a latency benchmark. Startup was not timed as a controlled experiment in this review.

Raw current evidence: [responses](artifacts/evaluation/project-direction-2026-10-10/live-probes.json), [readiness](artifacts/evaluation/project-direction-2026-10-10/readiness.json), [reproduction script](artifacts/evaluation/project-direction-2026-10-10/probe.py). The probe saves supplied-source excerpts for developer inspection; these are not independently reviewed answer keys.

The development app was left running at `http://127.0.0.1:8501/`. No source publication, release publication or application-code change was made.
