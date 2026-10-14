# Parser contract repair and audit

The preserved `cpu-reviewed` answers remain unchanged: 0/150 completion and 2/357 validated expected facets. The read-only audit found 72 cases with 146 expected topic/facet pairs missing from their recorded plans. `audit.json` and `audit.md` preserve every case's recorded failure reasons and input checksums.

The current parser now matches all 150 locked topic/facet descriptors: 357 expected pairs, zero missing pairs, zero extra pairs, and zero unintended pedagogic scopes. `current-parser-plans.json` contains every current plan, prompt/scorer/runtime checksums, and a no-input-change check. **This is planning agreement, not 150 completed answers or medical correctness.** The locked prompt bytes and scoring implementation were not changed.

`backend/app/services/question_plan.py` now extracts explicit entities across mechanism, essay, definition and appraisal grammar; stops comparisons before requested axes; preserves unresolved longer names such as amelogenesis imperfecta instead of mapping them to amelogenesis; distinguishes subject words from requested facets; retains explicitly requested histopathology with architectural/cytological features; and excludes output-cell/teaching instructions from clinical source scope. Actual population restrictions remain attached. Only the explicit subject occurrence is masked, so the same word can still be requested later as an axis. No curriculum registry edit was needed; unresolved identities remain provisional local IDs.

Tests use general task examples without importing the candidate bank or adding medical answer keys. Initial new regressions: 11 failed, 2 passed; one additional repeated subject/axis regression failed before its fix. The final checks were:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_mds_planning_boundaries.py tests/test_mds_planning.py tests/test_mds_safety_context.py tests/test_mds_evidence.py tests/test_mds_reviewed_evidence.py tests/test_mds_viva.py -q
# 99 passed; one existing Starlette/httpx deprecation warning
.\.venv\Scripts\python.exe -m pytest tests/test_patient_relevance.py tests/test_study_operations.py tests/test_mds_inspected_evidence.py -q
# 80 passed; one existing Starlette/httpx deprecation warning (before final subject-mask refinement)
.\.venv\Scripts\python.exe artifacts/evaluation/mds-upgrade-2026-10-11/coverage-audit-v2/audit_current_plans.py
# 150/150 contracts match; 357 pairs; no changed inputs
.\.venv\Scripts\python.exe -m ruff check backend/app/services/question_plan.py tests/test_mds_planning_boundaries.py artifacts/evaluation/mds-upgrade-2026-10-11/coverage-audit-v2/build_audit.py artifacts/evaluation/mds-upgrade-2026-10-11/coverage-audit-v2/audit_current_plans.py
# All checks passed
```

No full test suite or API pilot rerun was performed in this parser repair. The remaining answer-level gates require authentic sufficient source units, whole-unit applicability and final-output validation. Parent owns source-backed appraisal routing and source pack composition. The frozen histology 'where applicable' descriptor and appraisal diagnostic-limitations omission remain disclosed evaluation-contract limitations; they were not edited to improve results. Independent qualified review remains pending F03.
