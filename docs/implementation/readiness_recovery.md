# Aster readiness recovery — 14 October 2026

Aster is not yet ready as a broad, source-backed all-MDS teaching assistant. The frozen inventory-phase pilot returned substantive claims in 18 of 111 turns and complete substantive answers in 4. This measures the extractive source pipeline, not model-assisted answering or clinical accuracy. Five other complete responses were activities without medical claims and must not inflate the answer count.

## Diagnosis

The 288 facet checks not included in composition contain 286 insufficient-evidence flags and two unsupported-claim flags. Of these, 214 have retrieval candidates but no admitted evidence; 74 have no candidates. These automated flags need adjudication: candidates can be irrelevant, incomplete, incorrectly planned, or missing required qualifiers. They do not justify disabling admission checks.

The library has 7,791 records from 411 sources but only 65 prepared units, 56 bound. Counts of articles and discovery sources do not establish a coherent teaching library. For example, the malocclusion question retrieves fusion and craniofacial-syndrome material instead of foundational classification content. The 17 staged MedlinePlus summaries are not advanced MDS coverage.

Two reproduced planner defects were repaired: a coordinated role request swallowed epithelial–mesenchymal interactions into the tooth-development subject; clause-level pronoun resolution left DMFT marked as needing clarification. A third regression check ensures an unresolved first clause is not hidden by a named subject in a later clause. Detailed DMFT facets and dysplasia-grading subject inheritance still need work.

## Release sequence

1. Audit every supplied request against its independent content contract. Preserve all requested facets and scope, including comparisons, mechanisms and follow-ups. Fix generic parsing errors rather than adding question-specific answers.
2. Build coherent, authorized foundational sections across all nine specialties, following the national curriculum. Review whole sections for exact applicable facets, populations, exceptions and provenance. Record permission and source versions. Research papers supplement foundations; terminology, imaging datasets and exam questions have different roles.
3. Retrieve by subject, requested facet and applicability. Evaluate relevant-source recall separately from answer generation. A useful source that cannot be found is a retrieval failure; an irrelevant source is not a reason to loosen support checks.
4. Add source-grounded explanation generation with explicit claim-to-evidence support and completeness checks. Retain deterministic provenance validation. Evaluate a stronger text model against the installed model on the actual hardware; the current 2B model's observed oversimplification means displayed text alone cannot establish quality. Model-memory explanations remain separately labelled and cannot count as source coverage.
5. Freeze a new source pack and compatible index, then compare against candidate-v5 on the same supplied cases and variations. Add unseen questions per specialty to detect overfitting. Review answers for correctness, qualifiers and completeness independently of exact citation matching.
6. Activate a tested pack/model combination, verify normal startup and end-to-end user workflows, and retain rollback. Report educational readiness separately from personalized clinical decisions and imaging validation.

## Acceptance evidence still required

- Every declared core task has actual applicable source coverage, not just a catalog entry or a generated explanation.
- Every answerable benchmark request receives a substantive explanation covering its independently specified parts; ambiguous, unsupported and clinical requests have explicitly adjudicated expected behavior.
- Unseen questions pass per-specialty review; no aggregate score hides an unserved specialty.
- Claims resolve to evidence and preserve material qualifications; qualified review measures medical correctness separately.
- Normal installed operation passes startup, retrieval/index compatibility, conversational follow-up, failure handling and hardware latency/memory checks.

These are release criteria, not achieved results. Engineering tests establish regression behavior, not qualification-complete medical knowledge. No source pack was promoted by the planner corrections.

## First recovery measurement

The same candidate-v5 source pack, 107 cases and 111 turns (including variations), rerun after these planner fixes produced **20 substantive answers and 5 complete substantive answers**. Source and code hashes remained stable during capture. The source-only capture is `artifacts/evaluation/readiness-2026-10-14/planner-v1`; its responses SHA-256 is `72746468a0ff6d50a69dd3ad2181bf5cf52a6d18899ded9f1353a1ebeaef390b`. This is a modest engineering coverage improvement, not clinical validation or full readiness. The tooth-development request now reaches existing source evidence; the DMFT request no longer asks unnecessary clarification but remains evidence-insufficient.

`artifacts/evaluation/readiness-2026-10-14/coverage-worklist.csv` preserves each uncomposed diagnostic facet with its question, candidates and automated failure reasons. Sanitized topic/detail identifiers are diagnostic placeholders; source mapping must use the original request and independent content contract. The worklist is an investigation queue, not a medical review or complete curriculum inventory.

Validation: 1,145 Python tests passed in 133.09 seconds, with two existing deprecation warnings; Ruff passed for the changed planner and test module. The three new regressions were observed failing before the fixes. Full test output is preserved in `artifacts/evaluation/readiness-2026-10-14/pytest.log`.
