# Aster MDS library and evaluation report

9 October 2026 · Oral Pathology and Oral Microbiology

## Active result

The combined local teaching release `aster-teaching-mbbs-mds-v2-final-2026-10-09` is active. It contains **2,705 sections from 181 source units**, with **39 source-bound plain-language explanations** and **78 source-review holds**. Source units are individual pages, chapters or articles, not 181 independent publications.

The 1,891 original MBBS sections and 24 original explanations were preserved. The expansion adds **814 sections**: 260 dental foundations, 447 research sections and 107 statistics foundations. Two new foundation books and 27 licensed research papers were acquired. Three of those papers remain quarantined; acquisition does not imply availability for answers. The books, article dates, study designs, permissions, excluded candidates and all 89 topics are listed in [the study-material register](<MDS_STUDY_MATERIALS.md>).

This is retrieval augmentation of Aster's existing local model, not weight training. The existing Qwen 2B text/vision configuration remains in use. Medicine identity routing, secondary-data caution, OCR and X-ray paths are preserved. This release does not supply new OCR or imaging validation.

The photographed checklist has 89 topic entries; images 2 and 3 duplicate a page. Assignee names were ignored. MDS-49 contains uncertain handwriting: inferential statistics was tested as an explicit, unconfirmed interpretation. The photographed pages do not establish a complete official MDS curriculum.

## Actual evaluation scores

These are developer-authored, bounded reference-agreement tests. Exact source wording and approved explanation bindings are checked. They do not measure faculty correctness, complete exam answers or clinical accuracy. The focused MDS benchmark is deliberately small and contains 22 supported questions plus six boundary cases.

| Measure | Focused MDS, hybrid | Existing MBBS, hybrid |
|---|---:|---:|
| Expected response status | 28/28 (100.0%) | 91/93 (97.8%) |
| Expected-source retrieval | 22/22 (100.0%) | 77/81 (95.1%) |
| Required reference facts | 61/61 (100.0%) | 143/162 (88.3%) |
| Complete bounded reference agreement | 22/22 (100.0%) | 69/81 (85.2%) |
| Citation integrity (unanswered questions count as failures) | 22/22 (100.0%) | 79/81 (97.5%) |
| Source or validated-unit support among emitted claims | 26/26 (100.0%) | 190/190 (100.0%) |
| Boundary non-handling | 6/6 (100.0%) | 12/12 (100.0%) |
| Clinical correctness / faculty review | Unmeasured | Unmeasured |

Full outputs preserve every prompt, answer, citation, missing fact, timing, source hash and runtime hash: [mds-hybrid-final-v3-2026-10-09.json](<../../artifacts/evaluation/mds-v1/mds-hybrid-final-v3-2026-10-09.json>) and [mbbs-regression-hybrid-final-v3-2026-10-09.json](<../../artifacts/evaluation/mds-v1/mbbs-regression-hybrid-final-v3-2026-10-09.json>). Earlier candidate runs remain available but are superseded by these final v3 files.

The final lexical MDS run also passed 28/28 expected statuses and 22/22 bounded reference-agreement cases before the last shared guard improvements. The deployed hybrid results above are the final activation evidence. [mds-lexical-final-v2-2026-10-09.json](<../../artifacts/evaluation/mds-v1/mds-lexical-final-v2-2026-10-09.json>).

The previous active MBBS hybrid benchmark measured 92/93 expected statuses, 77/81 expected-source hits, 144/162 required facts and 69/81 complete reference-agreement cases. The final results above retain the full denominators; changed source matches and unanswered comparisons remain visible. The developing versus impaired hepatic-metabolism comparison is an existing non-handled case. The free-drug/protein-binding viva prompt is now also declined: its previous response discussed antibacterial ribosomes and resistance rather than pharmacokinetic distribution. Refusing that mismatch reduces the status score by one. This remaining retrieval gap is not a new successful answer.

## Topic probes and remaining gaps

The same whole-topic probe method produced an educational response for **72/89** topics in this release, compared with **31/89** in the previous active collection. Corpus and runtime changes both contributed; this is not a controlled measure of corpus improvement alone. A response may cover only a small part of a topic. All 89 have related material associations, which remain developer/curator nominations rather than verified coverage.

The following broad prompts were not handled; focused questions can sometimes retrieve narrower material. These remain explicit retrieval or breadth gaps:

- MDS-07: Muscles of mastication and muscles of facial expression.
- MDS-08: Cranial nerves.
- MDS-10: Monocyte-macrophage system.
- MDS-14: Blood groups and blood grouping.
- MDS-16: Pain.
- MDS-20: Amyloid and amyloidosis.
- MDS-23: Degeneration and necrosis.
- MDS-24: Thrombosis and embolism.
- MDS-28: Haemostasis.
- MDS-29: Ischaemia, infarction, gangrene and post-mortem changes.
- MDS-41: Temporomandibular joint.
- MDS-44: Basic principles.
- MDS-56: Mastication, speech and deglutition.
- MDS-64: Basic mycology.
- MDS-65: Basic virology.
- MDS-66: Mycobacteria.
- MDS-78: Decalcification.

[All 89 topic prompts and outputs](<../../artifacts/evaluation/mds-v1/topics-hybrid-final-2026-10-09.json>). Full-topic completeness, independent postgraduate examination performance and medical faculty correctness remain **unmeasured**. It cannot yet answer every MDS or MBBS question.

## Source quality and research safeguards

Rights were checked per source against publisher statements or article XML. CC BY, CC BY-SA, CC BY-NC and CC BY-NC-SA conditions, attribution and relevant version information are retained. NoDerivatives, unclear rights and unselected candidates are reading links. Third-party figures and unreviewed tables are excluded. This local collection includes noncommercial material; public or commercial reuse needs source-specific review.

The 78 holds comprise nine preserved MBBS holds, 19 dental passage holds and 50 sections from three quarantined statistical-method papers. Examples include misleading cell-cycle counts, tooth-resorption lineage, PTH/PTHrP wording, dentin dimensions, salivary-gland statements and statistics/extraction errors. Restricted passages can contribute only through specifically bound explanations where allowed; excluded passages cannot answer questions. Original files remain available for audit. A rights check does not establish factual correctness, and this was a bounded developer review rather than a full textbook audit.

Research claims and citations retain publication date, study design, population/model and limitations. Experimental tooth-regeneration findings remain research evidence. Missing study context or changed source/explanation hashes fail closed. Source cards display research context and source-review notices.

Regression checks prevent dental eruption from answering skin-eruption questions, invented syndromes from borrowing another syndrome, normal pulmonary distribution from substituting for a normal probability distribution, and antimicrobial resistance from substituting for pharmacokinetic free/protein-bound drug distribution. A shared guard now routes personal disease-exclusion or reassurance requests to professional review.

Plain doctor-to-patient style is available through 39 bounded explanations. Other questions may use longer source excerpts. Unrestricted model paraphrasing is not enabled because meaning and qualifications must remain supported. A faculty-reviewed explanation set and broader independent assessment are the next steps for consistent postgraduate teaching quality.

## Application and engineering checks

The actual frontend-to-backend chat bridge passed **19/19 synthetic requests** after activation and restart. These include MDS concepts, research, established MBBS questions, unknown content, personal dosing, personal X-ray reassurance, emergency escalation and the existing Ascoril catalogue route. Its temporary API session was deleted. [live-api-20261009T025711862794Z.json](<../../artifacts/evaluation/mds-v1/live-api-20261009T025711862794Z.json>).

The final full suite passed **296 tests** with one existing Starlette/httpx deprecation warning. Ruff checks passed for backend, scripts and tests. Dependency validation reported no broken requirements. [pytest-final-v3-2026-10-09.log](<../../artifacts/evaluation/mds-v1/pytest-final-v3-2026-10-09.log>); [ruff-final-2026-10-09.log](<../../artifacts/evaluation/mds-v1/ruff-final-2026-10-09.log>). These verify software behavior, not clinical safety or OCR/X-ray performance.

## Activation, rollback and reproducibility

The six-field profile is [mds_teaching_profile.json](<../../configs/mds_teaching_profile.json>). Activation writes `configs/teaching.env`, preserves the previous profile and leaves `.env` unchanged. The actual readiness response confirms 2,705 records, 39 explanations, 78 holds and no teaching-load error. All services remain bound to loopback.

Activation ledger: [activation-20261009T025527777387Z.json](<../../artifacts/evaluation/mds-v1/activation-20261009T025527777387Z.json>). Previous profile backup: [before-teaching-profile-20261009T025527777387Z.env](<../../data/private/config-backups/before-teaching-profile-20261009T025527777387Z.env>). To roll back, restore that saved profile to `configs/teaching.env` and restart the owned Aster application; preserve the release and index for comparison. The existing request guards remain in code.

Release manifest SHA-256: `70174a6d480ffa3fe52ecba1b5cb22f5e606c0f70ef9af68380ea86868c205d1`. Index and source hashes are recorded in the benchmark inputs and [manifest.json](<../../data/references/mds/releases/aster-teaching-mbbs-mds-v2-final-2026-10-09/manifest.json>). Raw snapshots, extraction scripts, component manifests and acquisition reports are linked from the study-material register.

Rebuild using the pinned source configurations with `scripts/build_mds_dental.py`, `scripts/build_mds_research.py` and `scripts/build_mds_statistics.py`; bind notes with `scripts/build_mds_notes.py`; compose a fresh release with `scripts/compose_mds_library.py`; then build its matching index with `scripts/build_teaching_index.py`. Immutable outputs require new destination names. `scripts/evaluate_mbbs.py`, `scripts/evaluate_mds_topics.py` and `scripts/smoke_mds.py` reproduce the checks against explicit release/index/notes inputs. `scripts/activate_teaching.py --profile configs/mds_teaching_profile.json --ledger-directory artifacts/evaluation/mds-v1 --activate` validates this profile before writing it.

No paid resources, accounts, access agreements or public deployment were created. The collected material is a substantial, finite expansion rather than all published literature.
