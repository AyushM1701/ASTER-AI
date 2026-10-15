# Aster MBBS Library Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ship a source-backed MBBS teaching collection and conversational answer path with measured coverage and a local model benchmark.

**Architecture:** Independent versioned teaching references beside existing product references. Reviewed explanation units are selected deterministically and retain source support. NMC metadata provides coverage mapping; clinical review remains separate.

**Tech Stack:** Existing Python/FastAPI/Ollama, MiniLM/NumPy, requests, BeautifulSoup and PDF extraction.

**Spec:** ../specs/2026-10-08-mbbs-library-design.md

## Global Constraints

- Local/free execution; no paid services, accounts or agreements accepted.
- Preserve existing product identity, personal dosing/diagnosis, OCR and X-ray boundaries.
- Immutable releases and configuration rollback; source and artifact hashes.
- Doctor-to-patient clarity with supported MBBS detail; no fabricated medical faculty review.

## Review Focus

- Generic pharmacology teaching must not assert exact Indian brand equivalence.
- Truncated chunks must not omit negation, exceptions or source context.
- Curriculum keyword matches must not be called full competency coverage.
- Teaching aliases must not swallow incompatible medicine queries or unsupported case advice.
- Faster/smaller model benchmarks must not be misreported as clinical correctness.

## Tasks

### 1. Curriculum/source acquisition

Files: scripts/research_mbbs_curriculum.py, configs/mbbs_curriculum.json, data/references/mbbs/raw/, tests/test_mbbs_curriculum.py.

Produces: pinned NMC PDF snapshots and extracted competency rows {code,subject,text,page}; permitted source candidates with license evidence and honest coverage labels.

- [x] Test competency extraction/deduplication and noncoverage labels, watch failure, implement and verify.
- [x] Acquire official NMC curriculum/clarification and source permissions; save hashes and extraction limitations.

### 2. Teaching collection acquisition/release

Files: scripts/build_mbbs_library.py, configs/mbbs_sources.json, data/references/mbbs/releases/, tests/test_mbbs_import.py.

Produces: immutable release records.jsonl, sources.yaml, metadata.json and manifest.json; records follow existing Reference schema with source_type=teaching. Developer-reviewed paired explanation units are stored separately with source hashes, qualifiers and review status.

- [x] Test source-license gating, source context/qualification preservation and immutable release integrity, then implement.
- [x] Acquire licensed text, extract complete coherent sections and build source/coverage records.

### 3. Runtime retrieval/explanations

Files: backend/app/services/teaching.py, backend/app/services/answers.py, backend/app/config.py, backend/app/main.py, tests/test_mbbs_teaching.py.

Consumes: teaching release; produces TeachingStore.search(question) -> cited Reference list and deterministic grounded teaching response. Uses separate local semantic vectors if needed, fails closed on changed artifacts. Limits unknown/ambiguous topics and preserves existing medicine path.

- [x] Write failing tests for multi-section concepts, grounded plain explanations, missing evidence and brand/dose isolation.
- [x] Implement source-bound teaching path and register runtime readiness metadata.
- [x] Verify focused tests and existing product/policy regressions.

### 4. Teaching/model evaluation

Files: scripts/evaluate_mbbs.py, data/evaluation/mbbs_v1.jsonl, artifacts/evaluation/mbbs-v1/, tests/test_mbbs_evaluation.py.

Consumes runtime collection/AnswerService. Produces developer benchmark rows with distinct retrieval/support/completeness/correctness fields and live stronger-model comparison with latency, RAM and version/digest. Clinical accuracy/expert review fields remain null/pending.

- [x] Pin metric semantics with hand-checkable fixtures; implement evaluation and a subject/question-type balanced dataset.
- [x] Check hardware, acquire reputable stronger text model, run same prompts and report actual evidence without unmeasured claims.

### 5. Integration and delivery

Files: MBBS_LIBRARY_EVALUATION.md, README.md, configuration backup/activation, artifacts/evaluation/mbbs-v1/pytest.log.

- [x] Review new code/source constraints; resolve material issues.
- [x] Run full test suite/lint, verify source hashes, activate reviewed release and restart only app-owned services as needed.
- [x] Run real API chat smoke tests and publish report with exact results, source links, limitations and medical review queue.

## Delivery evidence — 9 October 2026, Asia/Calcutta

Final source release: `aster-mbbs-v1-r3-final-2026-10-08`, 1,891 contexts/135 publisher pages or selected document units. Separate matching hybrid index, 24 paired explanations and nine source holds are active through `configs/teaching.env`; `.env` retains explicit override precedence and was unchanged. This separate profile replaced an attempted `.env` activation denied by Windows ACLs, without changing those protections.

Curriculum: 2,626 active extracted competencies; nominations and 25 inspected partial associations across 24 competencies remain separate from coverage. Faculty decisions and clinical correctness remain null. Source rights and curriculum extraction issues are retained.

Fresh active-code benchmark: 93 cases/81 supported; hybrid source hit77/81 and bounded reference agreement69/81; lexical hit75/81 and agreement61/81. Both12/12 teaching boundaries. Actual browser bridge10/10 checks, deleted synthetic API session, browser-rendered osmosis answer verified. Full engineering suite248 passed with one existing warning; Ruff passed. Independent review emergency-scope and topic-polysemy findings were reproduced, fixed and covered by regressions. Downloaded4B compared with2B on13 identical controlled prompts each; equal5 strict passes and slower4B, so active2B retained.

Full evidence and remaining gaps: `MBBS_LIBRARY_EVALUATION.md`. Faculty review, complete MBBS coverage, advanced clinical reasoning and current Indian prescribing applicability remain unestablished. No commit/PR was invented for this non-Git workspace.

## Execution rulings

The human explicitly requested all six proposed steps and necessary work. Repeated design/plan approval would conflict with that authorization and the developer's autonomy instructions, so execute without another permission gate. No Git repository exists; retain immutable artifacts rather than inventing commits. Qualified clinical review is external; deliver its queue and report it pending.
