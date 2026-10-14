# MDS implementation and operating report — 11 October 2026

The requested engineering changes and bounded open-material collection are implemented in the existing local Python/FastAPI, Ollama and HTML/CSS/JavaScript project. **MDS educational source readiness has not passed:** the locked 150-task candidate pilot completed 0/150 tasks with the installed source release under the new contract. Independent qualified clinical review (F03), complete official amendment reconciliation, and clean frozen Windows installation remain pending. The code must not be advertised as comprehensive MDS medical coverage.

The two supplied prompts and the referenced Oral Pathology implementation plan are retained in `artifacts/checkpoints/mds-upgrade-2026-10-11/`. They supplied requirements; the existing project supplied implementation conventions. The user's national-only curriculum choice is recorded. Original eleven verbatim questions/responses were unavailable; known regression fixtures are reconstructed and labelled accordingly.

## What changed

The real request path remains frontend same-origin bridge → session-owned `/v1/chat` → policy/audience/context routing → `AnswerService` → existing teaching/reference retrieval or local Ollama → common `output_validation.finalize` → response presentation. Patient information, confirmed document workflows and opt-in research storage remain separate. No hosted inference, new default model, model training, release publication or active corpus/index import was introduced.

Typed plans retain the original question, audience, canonical entities, facets, clinical scope, comparison axes, marks, fictional status and session context. Independent clauses keep their own facets; comparisons retrieve entities independently. Evidence is selected from the existing retrieval engines, with stale/held/extraction/injection checks, source diversity and exact source-span bindings. Coverage is computed from validated **displayed** cells/sections rather than model flags or hidden claims.

The terminal guard also protects existing single definitions, prepared notes, generated/extractive answers, separately validated outage fallback and error envelopes. Safety-failed generation cannot use an extractive escape path. Source identities, versions, permissions and reviewed annotation hashes are checked where the bound MDS contract applies. Clinical correctness is never inferred from citation existence or deterministic word matching.

Composition provides facet sections, symmetric comparison tables, specific missing-facet/conflict states and marks-bounded whole units. It does not truncate away qualifications. Reused paragraphs display once with cross-references. Synthesis is available only as an optional local **shadow** signal: drafts are discarded and never displayed. The existing simple/deeper reviewed presentation remains available without inventing new medical explanations.

Automatic applicability is deliberately conservative. Mixed units and contextual passages that it cannot establish are withheld. `reviewed_evidence.py` admits legitimate contextual/analogy-containing whole units only through explicit, hash-bound reviewer annotations with retained qualifications. No production annotations were fabricated. This explains much of the low measured completion and is a source-review dependency, not a reason to loosen matching to headings or article tags.

Viva state is temporary and session-owned. It asks one question, hides its answer before submission, returns provisional lexical reflection, and offers a qualification follow-up even with one admitted unit. Restart, exit, stale/foreign turn IDs, expiry, topic changes and ordinary patient questions are handled. Feedback is not semantic/faculty grading. Fictional educational cases receive only supported sections and uncertainty; a fictional label cannot bypass personal medical safeguards.

## Requirement-to-evidence tracker

| Requirement | Implemented location and evidence | Remaining gate |
|---|---|---|
| Implementation §1–2: preserve project, inspect, checkpoint, trace | Existing README/configuration/path audited; 230-file checksum checkpoint; locked evaluation replays untouched checkpoint backend | No Git repository exists; checkpoint substitutes for branch/diff |
| F19 / §3: common final boundary, fallback/errors | `output_validation.py`, `answers.py`, `errors.py`, `main.py`; source/shape/injection/safety/outage tests | Deterministic support is not independent medical proof |
| F20 / §4: topic/facet/task coverage | `question_plan.py`, `evidence_plan.py`, `answer_composer.py`; clauses, scopes, entities, axes, marks and visible-coverage tests | Completion gate failed with installed material |
| F21: preserve patient relevance | Existing patient store retained; policy and viva routing tests, existing patient/session/document regressions pass | Patient reference expiry remains 17 October 2026; independent correctness pending |
| §5: twelve families, nine specialties, provenance | `mds_curriculum.py`, session-owned `/v1/study/curriculum`, web bridge and study disclosure; four cached national snapshots verified | Detailed/current amendment reconciliation pending; 25 canonical runtime topics are vocabulary, not complete specialty competency coverage |
| §5: source manifests/version dependencies | Existing TeachingStore/ReferenceStore manifests reused; full hashes invalidate changed releases, indexes, explanations and evaluation snapshots; reviewed whole-unit annotation contract | No actual source unit applicability attestations invented |
| §5–6: extraction, ranking, diversity, duplication | Structural/source checks; per-entity existing lexical/dense candidates; source-diverse selection; immutable collector hashes and family deduplication | No measured evidence justifies adding a reranker/FTS engine; optional components remain absent |
| §7: readable grounded responses | Sections/cells with exact claims, marks budget, paragraph cross-reference, source coordinates; renderer/browser tests | Mechanism order depends on the admitted source unit; no unsupported reordering or fabricated synthesis |
| §7: synthesis and rollback | `OllamaAdapter.synthesize`, `MDS_SYNTHESIS_MODE=off|shadow`, `ENABLE_MDS_PIPELINE`; bounded one-call shadow/outage tests | No real-model medical synthesis quality gate has passed; extraction remains default |
| §8: fictional cases and viva | Typed case facets, supported differential/investigation/histology sections, uncertainty; `viva.py`, session locks/state, chat API | Case evidence breadth and qualified assessment remain pending |
| §9: frontend/API | Existing safe DOM rendering; headings, mobile/keyboard table, source/version/character disclosure, first-turn viva hiding, curriculum scope; real browser check | Browser evidence uses isolated synthetic mechanics, not medical quality |
| §10: eleven tasks and adversarial behavior | Reconstructed/paraphrased fixtures; typed/evidence/API tests; forged hashes/coordinates/identities, mixed passages, stale sources, conflicts, injection, missing cells, patient/viva boundary | Original verbatim replays unavailable; unseen independent holdout required |
| §10: locked 150-prompt pilot, scoring, review pack | `mds_pilot.py`, `evaluate_mds_pipeline.py`, locked manifests; 182 API probes including 150 pilot tasks; source leakage audit and blinded review rows | Self-authored/inspected development data; F03 pending; 300–500 independent expansion is later work |
| §11: RTX 4050 / CPU / resource verification | Actual local GPU model probe and serial CPU API measurements; reports preserve initial nonresident/warm conditions and code hashes | Production buffered first-token timing unavailable; no forced cold-start or load-capacity claim |
| §11: source packs / distribution | `stage_mds_pack.py`, existing release/index builders, loader validation and bound human attestation | Actual pack approval not obtained; adapter currently supports CC BY 4.0, explicitly holds unsupported runtime license versions |
| §12: reports, commands, review | This tracker, evaluation report, collection report, pack operating guide; fresh reviewer findings corrected with red/green regressions | Clean frozen Windows installation/startup and publication readiness pending; nothing published |
| Collection §1–2: all specialties/national scope | Existing editorial taxonomy reused; collection matrix 144 topics / 1,728 topic-facet cells; all nine specialties plus foundations collected | 15 topics lack associations; associations do not establish competence |
| Collection §3: article-specific rights | Authoritative JATS permissions, attribution, separate eligibility decisions; CC BY 4.0/2.5 admitted; SA conditional metadata track; NC/ND/unknown excluded | Asset rights caused 119 originals to be withheld; 120 independent clinical reviews pending |
| Collection §4: discovery | Official Europe PMC REST metadata/OA retrieval, logged queries/cursors and search cache | Single-provider research supplement, not an exhaustive literature search or foundational textbook corpus |
| Collection §5: secure bounded access | HTTPS/host/public-DNS checks, redirects refused, per-file/request/byte/time caps, atomic immutable caches, retries/Retry-After, safe paths, defused XML | No continuing background collection; no unbounded scrape |
| Collection §6–7: organization/extraction/quality | Catalogue JSONL/CSV, retained derivatives, extracted paragraphs, rights evidence, section/character provenance, failure checkpoint and spot checks; all persisted spans checked | No actual PDF/OCR corpus or real eligible-table quality claim; publisher editorial notices/population/design appraisal unresolved |
| Collection §8: RAG/training separation | 110 staged RAG documents / 6,775 chunks; 10 held-out source families / 632 chunks; training-candidate label only | No training, generated gold answers, clinical derivative examples, active RAG import or upload |
| Collection §9–10: tooling/checkpoint/report | `mds_open_collect.py`, `mds_open_validate.py`, configuration, dry run/resume/stages, data card, reports and actual collection | Bounded milestone complete; further collection/appraisal needed for missing topics |
| F03: independent qualified review | Every runtime/source/evaluation path keeps pending review separate; blinded human-review output prepared | **Pending. No qualified reviewer, medical accuracy score or clinical certification obtained.** |

## Measured checks and readiness

Final full regression command: `.\.venv\Scripts\python.exe -m pytest -q --tb=short`. **838 passed, one existing Starlette/httpx deprecation warning, 53.77 seconds.** Log: `artifacts/checkpoints/mds-upgrade-2026-10-11/pytest-final-confirmed.txt`. The pre-existing scroll geometry test harness was repaired to supply its existing `scrollBehavior` dependency; production reduced-motion behavior was preserved.

`python -m ruff check backend frontend scripts tests` reports all checks passed. `node --check frontend/web/app.js` passes; `node tests/ui_interactions.cjs` passes five interaction checks. The isolated browser exercised comparison/source disclosure, national curriculum scope, hidden viva reference, feedback/follow-up and an explicit new task. At 390×844, the table remained horizontally scrollable and keyboard focus/ArrowRight changed its scroll position. Temporary servers on 8800/8851 and the test tab were stopped; production services were not restarted. The screenshot below contains **synthetic mechanics fixtures only**, isolated from production and medical evaluation.

![Synthetic interface mechanics verification](../artifacts/evaluation/mds-upgrade-2026-10-11/ui-synthetic-comparison.png)

The source-backed pilot uses the unchanged `aster-teaching-all-mds-v3-2026-10-10` release: 7,773 sections, 404 source units, existing prepared explanations/holds and current model configuration preserved. Latest exact scorecard is linked in [the evaluation report](MDS_EVALUATION_2026-10-11.md). Observed core completion **0/150**, bound facets **2/357**, citation resolution **2/2**, safety probes **4/4**, contamination checks **0/6** over only two distinct question texts, and abstention **180/182**. These denominators do not prove correctness, appropriate abstention or comprehensive safety. Earlier 22/150 completion was superseded by stricter review fixes and is not a final success claim. Baseline's absent facet contract is unobservable, not clinical zero coverage.

The actual RTX 4050 probe used the existing `qwen3-vl:2b-instruct`: initial nonresident total 8.18 seconds, warm total 0.86 seconds; whole-device peak 5,548/6,141 MiB. GPU timing is a small real-model transport probe, not validated medical synthesis. CPU API evaluation and GPU inference are reported separately. Clean frozen installer acceptance is still pending; this workspace smoke/test run is not a new distributable release.

The [collection report](MDS_OPEN_CORPUS_2026-10-11.md) records 120 unique documents, 117 CC BY 4.0 / three CC BY 2.5, one complete original and 119 clearly labelled asset-stripped derivatives. Final integrity validation checked all 120 retained documents and 7,407 exported spans with zero reported issues. Forty-two MB were downloaded in bounded completed runs; failures/diagnostics are itemized. Rights/extraction checks do not supply faculty appraisal. The collection is separate from the active library.

## Run, inspect and roll back

Use the existing Windows development launcher from the project root. Restart Aster through its existing launcher to load new code; an already running process retains its earlier imports. The project configuration and current local model were preserved.

```powershell
.\start.ps1 -NoBrowser
.\.venv\Scripts\python.exe -m pytest -q --tb=short
.\.venv\Scripts\python.exe -m ruff check backend frontend scripts tests
node --check frontend/web/app.js
node tests/ui_interactions.cjs
.\.venv\Scripts\python.exe -m scripts.mds_open_validate
.\.venv\Scripts\python.exe scripts/evaluate_mds_pipeline.py verify
```

`ENABLE_MDS_PIPELINE=true` enables facet composition and session viva. Set it to `false` in an explicitly selected local profile and restart to use the prior composition/activity path; the shared safety/evidence terminal checks remain. `MDS_SYNTHESIS_MODE=off` is the default; `shadow` runs a bounded local draft comparison and never displays the draft. Unsupported mode values fail configuration validation. Do not change the default model to compensate for missing source evidence.

Inspect response `question_plan`, `evidence_plan`, `claim_evidence`, `coverage_status`, `covered_facets`, `missing_facets`, `rejection_codes`, `model_failure` and `validation`. An `error`/`transport_error` differs from evidence insufficiency. Source disclosure shows the actual cited snapshot, section and character bounds in the session response; shared article keywords are not support.

The [inactive pack guide](MDS_STAGED_PACKS_2026-10-11.md) provides exact template/staging commands and the required real review fields. The real blank template intentionally fails attestation preflight and no pack was activated. Human whole-unit facet annotations follow the explicit contract in `reviewed_evidence.py`, require qualification preservation, and must be bound to a new immutable metadata/pack manifest. Do not edit a checksum just to make changed text appear reviewed.

For an accepted future inactive pack, rebuild into a **new** index directory using the existing command; never overwrite the active index:

```powershell
.\.venv\Scripts\python.exe scripts/build_teaching_index.py --release artifacts/source-packs/mds-reviewed-v1 --output artifacts/source-packs/mds-reviewed-v1-index
```

This requires the existing local embedding assets and does not activate the pack. Test a separate profile first. Preserve its previous release/index/explanation paths and hashes for rollback. Source activation, installer publication, training and external upload were outside this implementation and have not happened.

For code rollback, preserve newer work first and restore only the listed changed existing files from the checksum checkpoint; remove or archive newly added modules only after restoring their callers. `change-inventory.json` records old/new hashes and new artifact paths. Do not overwrite `.env`, production sources, active indexes or unrelated later changes. No Git history was fabricated.

The next source-readiness action is to obtain authorized foundational, qualification-complete units for the reconstructed core topics, annotate their exact applicable facets with actual source review, stage a new pack, rerun the development pilot against its frozen source version, and obtain a fresh independent holdout and qualified F03 assessment. Until those gates pass, declared curriculum entries remain scope only and missing content stays explicit.


Subsequent 2026-10-12 source-pack work: [inspected-pack report](MDS_INSPECTED_PACK_2026-10-12.md). The frozen candidate improved from 0/150 to 38/150 complete tasks; 112 remain incomplete. This supersedes the earlier current development result, while preserving its historical artifacts. Engineering verification: 888 tests passed, Ruff clean.
