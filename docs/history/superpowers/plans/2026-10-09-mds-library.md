# Aster MDS syllabus library implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Import source-backed material for the 89 photographed MDS topics and make it usable in Aster, with research context and measured gaps.

**Architecture:** Preserve the active MBBS teaching release and build a new combined release with independent source records, topic mappings and review notes. Research and foundational material remain distinguishable in metadata and responses.

**Tech Stack:** Existing Python/FastAPI, TeachingStore, MiniLM/NumPy, HTML/XML/PDF extraction and licensed publisher snapshots.

**Spec:** ../specs/2026-10-09-mds-library-design.md

## Global constraints

- Source-specific reuse permissions; no restricted textbook copies or images.
- Only photographed topic text; ignore assignee names; mark ambiguous handwriting.
- Preserve original MBBS source IDs and hashes, paired explanations and nine holds.
- Label research date, study design, human/animal/in-vitro context and limitations.
- Faculty correctness remains null/pending; topic association is not curriculum mastery.
- Immutable artifacts and reversible local activation; loopback only.

## Review focus

- Dental pulp must not retrieve unrelated fruit pulp; oral eruption differs from skin eruption.
- Research regeneration/animal results must not become a clinical recommendation.
- Missing/ND/third-party licenses produce link-only references, not imported prose.
- Statistical association is not causation; clinical diagnosis/dosing boundaries remain.
- MDS searches must preserve established MBBS and exact medicine routing.

## Tasks and ownership

1. Root: transcribe images into configs/mds_syllabus.json, preserve image hashes and ambiguities. Read existing integration; minimal runtime/release composition changes with regression tests.
2. Dental textbook implementer: acquire independently licensed dental histology/embryology teaching text, validate permissions, extract coherent sections and create component release. Own configs/mds_dental_sources.json, scripts/build_mds_dental.py, tests/test_mds_dental.py, data/references/mds/raw/dental and components/dental only.
3. Research implementer: acquire reusable reviews/original papers relevant to all 89 topics, plus permitted statistics/foundation material. Own configs/mds_research_sources.json, scripts/build_mds_research.py, tests/test_mds_research.py, data/references/mds/raw/research and components/research only. Preserve study context; produce bibliography for excluded material.
4. Root after acquisition: compose combined release, bind notes/holds, build index and detailed topic source register; evaluate actual topic questions and existing regressions. Request independent review, fix material findings.
5. Root: activate with profile backup, restart only owned processes, actual API/browser smoke, full tests/lint, MDS_LIBRARY_REPORT.md and documented remaining gaps.

6. Statistics follow-up: a dedicated statistics foundation component after evaluation exposed missing confidence-interval/regression teaching and a normal-distribution retrieval mismatch. Own configs/mds_statistics_sources.json, scripts/build_mds_statistics.py, tests/test_mds_statistics.py, raw/statistics and components/statistics. Rights must be verified independently; root composes the final release and validates new host/license gates.

## Progress

- [x] Photograph inventory and provenance.
- [x] Dental component acquisition and permissions.
- [x] Research component and bibliography.
- [x] Statistics foundation follow-up.
- [x] Combined release/index, context safeguards and topic benchmark.
- [x] Final review, activation, smoke and report.

User clarification: Oral Pathology and Oral Microbiology. Image four adds oral physiology, embryology, microbiology, immunology, genetics and twelve lab-technique topics. Full scope is 89 photographed entries.

Final release: aster-teaching-mbbs-mds-v2-final-2026-10-09, with 2,705 sections,
39 bounded explanations and 78 holds. Two foundation books and 27 licensed
articles acquired; three statistical papers quarantined. Independent developer
review findings and additional retrieval/boundary regressions were addressed.
Faculty completeness and correctness remain pending. Broad-topic handling is
72/89; every remaining gap is recorded, rather than treated as completed mastery.

Activation preserved the previous teaching profile and left .env unchanged.
Actual bridge checks passed 19/19 synthetic requests; the browser displayed the
new dental-pulp explanation and its linked source. Final software suite: 296
passed, one existing deprecation warning. Final focused MDS hybrid evaluation:
28/28 statuses and 22/22 bounded reference agreement. MBBS regression: 91/93
statuses, 69/81 complete bounded agreement; two retrieval gaps remain explicit.
Delivery: MDS_STUDY_MATERIALS.md and MDS_LIBRARY_REPORT.md with full artifacts.
