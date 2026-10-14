# Private Paper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. The owner has authorized execution of the full master plan; routine implementation decisions do not require renewed permission.

**Goal:** Let the owning local session upload an authorized text PDF, confirm its extraction and obtain exact document-bound research excerpts with honest appraisal gaps.

**Architecture:** A temporary paper collection shares existing session quotas. A bounded pypdf worker parses text; the common terminal finalizer validates every exact excerpt against trusted confirmed pages. Existing single-chat attachment controls display and confirm papers without shared storage or model migration.

**Tech Stack:** Existing Python/FastAPI, pypdf, subprocess, session locks, HTML/CSS/JavaScript.

**Spec:** `docs/implementation/private_paper_design.md`

## Global constraints

- Preserve existing `/v1` routes and source/personal-medical safeguards.
- Private text stays in its temporary session, outside shared indexes/training and educational export.
- Exact PDF/page/span hashes and current confirmation gate all analysis.
- No clinical validation or complete critical-appraisal claim; missing findings/labels remain unknown.
- No new model, automatic external request or active-pack promotion.

## Review focus

- Malformed/encrypted/textless PDFs must fail without parser details or invented OCR.
- Expiry/deletion during work must not revive or display cleared paper context.
- Foreign/stale/unconfirmed contexts and forged citations must fail without source leakage.
- Paper instructions must remain untrusted, and unsafe quotes cannot become a clinical fallback.
- Image workflows, shared session capacity, safe rendering and opt-in educational exports must retain their contracts.

### Task 1: Paper parsing, ownership and common guard

**Files:** Create `backend/app/services/papers.py`, `backend/app/services/pdf_worker.py`, `backend/app/api/papers.py`, `tests/test_private_papers.py`. Modify `sessions.py`, `main.py`, `api/chat.py`, `output_validation.py` and bounded configuration fields.

**Interfaces:** `extract_pdf(raw, settings) -> pages`; `Paper.confirm(expected_revision)`; `Paper.excerpts(question)`; `validate_paper_result(question, result, paper)` through the common finalizer. API consumes existing bearer-owned sessions and revision requests.

- [x] Add failing parser, ownership/confirmation, span-tamper, policy and lifecycle tests.
- [x] Observe failures before implementation.
- [x] Implement bounded worker, temporary paper state, additive API and trusted terminal validation.
- [x] Pass focused positive/negative/API tests and existing session/document/guard regressions.

### Task 2: Single-chat PDF review and follow-ups

**Files:** Modify `frontend/web/index.html`, `app.js` and existing styles only as needed; add meaningful UI interaction tests.

- [x] Pin PDF selection/permission, confirmation, detach/reopen and stale-response behaviour in tests.
- [x] Extend existing attachment and document rendering with safe paper controls.
- [x] Verify image workflows, JavaScript syntax, UI tests and actual browser/API flow.

### Task 3: Freeze verification and traceability

- [x] Run whole-project tests/Ruff and relevant browser/model-independent checks.
- [x] Inspect a real synthetic/licensed PDF upload → confirmation → excerpts → clear flow.
- [x] Obtain a fresh engineering review and fix reproduced findings.
- [x] Update FR-09/FR-13/FR-14, artifact hashes and reports with actual evidence and remaining appraisal/release gates.

No Git repository exists: use screened immutable source checkpoints rather than a Git commit or new worktree. Complete research/training and qualified-review gates remain open.
