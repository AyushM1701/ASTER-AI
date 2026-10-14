# Secondary medicine data evaluation

Evaluated on 7 October 2026. Active release: **aster-secondary-v1-r2-2026-10-07**.

The user authorized both Indian datasets as unverified secondary AI evidence. The selected release contains **6,670 notes** linked to **3,408 Netmeds products**: 3,310 A-Z composition notes and 3,360 HF composition, use and side-effect notes. These counts measure admitted source sections; they do not establish medical accuracy or comprehensive drug coverage.

| Check | Observed result |
|---|---|
| Full project test suite | 160 passed, 1 existing dependency deprecation warning; 34.77 seconds |
| Live checks through the UI API bridge | 10/10 passed |
| Original field comparison | 6,670/6,670 complete note texts matched; zero failures |
| Secondary readiness | Enabled and available; 6,670 records, 3,408 linked products; no error |
| Source status | `unverified`, `clinical_review: false` |
| Ruff on changed Python files | Passed |
| JavaScript syntax | Passed |
| Installed dependency consistency | No broken requirements |
| Impeccable mechanical detector | Zero findings |
| Desktop interface | Caption, dataset citation and secondary link inspected at 1280 × 720 |
| Phone interface | Inspected at 390 × 844; document width 390, no page overflow; caption wrapped within its bounds |
| Clinical answer accuracy / equivalence | Not measured; no qualified clinical review |

The single test-suite warning concerns Starlette's deprecated `httpx` test-client integration. It did not fail a test.

## Live scenarios

| Question / scenario | Actual result |
|---|---|
| Abd 400mg Tablet purpose | One HF secondary citation; unverified caption; full source-text fallback |
| Abd 400mg Tablet side effects | One HF secondary citation; unverified caption; full source-text fallback |
| Augmentin 625 DUO Tablet 10'S ingredients | Mixed reference and secondary evidence; unverified caption; full source-text fallback |
| Augmentin tablet with added Injection form | Insufficient evidence; no secondary citation |
| Augmentin tablet with added 500mg qualifier | Insufficient evidence; no secondary citation |
| Augmentin tablet interactions | Existing Indian GSK label notes; no secondary citation or secondary notice |
| Ambiguous Ascoril LS Syrup | Insufficient evidence; no secondary citation |
| Personal Augmentin dose | Unsupported input |
| Crushing chest pain now | Urgent guidance |
| Anemia definition | Existing references; no secondary citation or secondary notice |

Every displayed claim in these live responses matched a complete cited section. The three secondary scenarios used the checked extractive fallback rather than serving unchecked model wording. This checks source fidelity, not the medical truth of the underlying datasets. The Augmentin interaction response supplies existing selected label notes and retains the limitation that comprehensive interaction checking is not established.

An initial smoke run incorrectly expected secondary-only answers for short Augmentin questions and abstention for its interaction question. Actual responses resolved an existing Indian manufacturer-label record directly. Those expectations were corrected after inspecting the citations; the primary retrieval and admission gates were not weakened. The initial responses remain saved separately.

## Provenance and remaining limits

Secondary citations preserve dataset URL, snapshot hash, original row numbers, matched product anchor, and unverified review status. The immutable manifest and records are checksum-pinned. Tests cover changed files/status, unknown source URLs, ambiguous links, strength/form/route/variant mismatches, personal dosing, source-text fallback, primary priority, and recalculation of crosswalk composition checks.

Only selected unique links with agreeing reported fields and no review flags enter this release. Excluded records remain in their source snapshots and crosswalk artifacts. Agreement does not establish independent corroboration, current product equivalence, a complete ingredient list or permission to substitute medicines. A-Z supplies composition fields only; secondary data cannot fill dosing, warning, contraindication or interaction sections. OCR confirmation remains separate.

The small notice appears only when secondary evidence is actually cited:

> Unverified secondary data · confirm with the product label.

## Evidence and reproduction

- [Live responses and readiness](artifacts/evaluation/secondary-v1/api-smoke.json)
- [Initial smoke expectations and responses](artifacts/evaluation/secondary-v1/api-smoke-initial-expectations.json)
- [Full test output](artifacts/evaluation/secondary-v1/pytest.log)
- [Original field audit](artifacts/evaluation/secondary-v1/source-text-audit.json)
- [Mechanical UI detector output](artifacts/evaluation/secondary-impeccable-detect.json)
- [Desktop screenshot](artifacts/evaluation/secondary-v1/chat-caption.jpg)
- [Phone screenshot](artifacts/evaluation/secondary-v1/chat-caption-mobile.jpg)
- [Active release manifest](data/references/secondary/aster-secondary-v1-r2-2026-10-07/manifest.json)
- [Activation and rollback guide](SECONDARY_MEDICINE_DATA.md)

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/audit_secondary_text.py
# With Aster running on its configured local ports:
.\.venv\Scripts\python.exe scripts/smoke_secondary_api.py
node --check frontend/web/app.js
```

The live script creates and deletes its own temporary session. Future model runs can choose different supported sections; rerun the live checks when model, corpus or retrieval behavior changes.
