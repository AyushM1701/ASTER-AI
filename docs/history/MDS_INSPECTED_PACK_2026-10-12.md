# MDS inspected source pack — 2026-10-12

The frozen development pilot improved from **0/150 to 38/150 complete tasks**. The requested all-task gate remains failed: **112 tasks are incomplete**. This pack does not establish qualification-complete national curriculum coverage or independent clinical accuracy.

The inactive pack `artifacts/source-packs/mds-foundations-candidate-v2-2026-10-12` contains **35 whole source units, 19 sources and 93 explicit AI-inspected facet bindings**. Four newly acquired article sources contributed five admitted units; existing licensed foundations and research supplied 30 units. Each annotation identifies exact topic/facet/scope, complete text/record/raw hashes and coordinates, actual support rationale, qualifications and original source context. Human clinical review remains pending. Original CC-BY, NC and SA conditions and attribution are retained for local noncommercial educational use.

Task planning now preserves subject boundaries, explicit histopathology/architecture/cytology requests, provisional extended entities, clinical scopes and clause-local pronouns. Explicit critical appraisal requests reach evidence retrieval; study definitions carry facet bindings when supported. Inspection bindings improve retrieval recall while the shared terminal guard still checks whole units, source identity, permissions, holds and display coverage. AI inspection is separately labelled and cannot masquerade as human review. Runtime exclusion holds cannot fall back to heuristic support.

Both pilot prompt files are byte-identical to the original locked bank. The new bank binds the new source version and its hashes. No scorer or question changes were made. The confirmed run recorded unchanged backend code throughout evaluation.

| Measure | Confirmed result |
| --- | --- |
| Complete developer tasks | 38/150 |
| Supported requested facets | 131/357 |
| Citation identity and exact excerpt resolution | 118/118 |
| Exact source-support flags | 0/118 |
| Sampled contamination | 0/6 |
| Sampled safety policy checks | 4/4 |
| CPU lexical API latency | p50 13.4 ms; p95 53.6 ms |

These are development and engineering signals, not independent biomedical quality measurements. Source-supported excerpts can remain too narrow for complete mechanisms, detailed histology, or 25-mark essays. Animal-model observations were not promoted to general human histopathology; source defects and inherited holds were retained. Reference-level editorial notices were distinguished from notices about the review itself. NoDerivatives and unsupported runtime-license candidates were not admitted. Additional rights-screened material remains unadmitted pending actual context review.

The explicit remaining 112 task contracts are recorded in `artifacts/evaluation/mds-upgrade-2026-10-11/cpu-inspected-v2-confirmed/remaining-task-gaps.json`. Completion requires further authorized, inspected evidence for those exact gaps; expanding topic tags or mechanically declaring facets supported would falsify the gate.

The pack is staged and evaluated, not activated. Production source/index files and `.env` remain unchanged. Full regression verification: **888 tests passed**, one existing Starlette/httpx deprecation warning; Ruff clean. Detailed output is recorded in `pytest-inspected-v2-confirmed.txt`.

Reproduction:

```powershell
.venv\Scripts\python.exe scripts/evaluate_mds_pipeline.py verify --release artifacts/source-packs/mds-foundations-candidate-v2-2026-10-12 --bank artifacts/evaluation/mds-upgrade-2026-10-11/inspected-v2-bank
.venv\Scripts\python.exe scripts/evaluate_mds_pipeline.py run --release artifacts/source-packs/mds-foundations-candidate-v2-2026-10-12 --bank artifacts/evaluation/mds-upgrade-2026-10-11/inspected-v2-bank --output artifacts/evaluation/mds-upgrade-2026-10-11/choose-new-immutable-run
```
