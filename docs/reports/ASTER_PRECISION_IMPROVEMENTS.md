# Aster answer precision improvements — 9 October 2026

The active local chat now preserves more of the question's scope, selects more relevant teaching sources on the targeted checks, and explicitly reports unsupported parts. These are measured engineering improvements. **Qualified medical accuracy, full curriculum mastery and clinical suitability remain unestablished.**

The source collection and local Qwen3-VL 2B model are unchanged. This work repairs retrieval and answer routing; it does not retrain or fine-tune the model.

## Changes in the active application

- Separate explicit presentation requests from the medical concept. Politeness, plain-language requests and exact academic headings no longer replace the topic. Arbitrary `For …` prefixes retain diseases, populations and experimental context.
- Retrieve independently named topics and both sides of suitable comparisons. Missing parts appear in `unsupported_topics` and visible warnings. Shared qualifiers such as `in kidney failure`, `for children` or `under hypoxic conditions` stay attached to the whole request when their scope is ambiguous.
- Require support in actual source text/section. Broad topic keywords, unrelated homonyms and nonadjacent abbreviation matches cannot supply a missing concept. Direct concept phrases and foundational material receive preference over disconnected mentions or narrow research excerpts.
- Match paired explanations against meaningful requested terms. A definition note cannot be promoted merely because the question names its condition while requesting uncovered investigations, diagnostic assessment or management. Raw retrieval also retains named clinical aspects.
- Prevent an unsupported paired teaching concept from falling through to an unrelated primary note. Equivalent question forms retain this refusal. The statistical noun `mean` is distinguished from the ordinary question verb in `what does … mean`.
- Mark MCQ verdicts, fictional-case reasoning and additional curriculum tasks as unverified when the retrieved notes do not establish their completion. Preserve study setting, dates, source restrictions and qualifications.
- Cache pure query/content transformations and prepare the same focused query embeddings during evaluation. Caches depend on content; changed reference text invalidates the relevant keys.
- Retain warnings and limitations in the blinded faculty sheets. Reviewers see the uncertainty that accompanies the displayed answer.

Relevant implementation: [teaching.py](../../backend/app/services/teaching.py), [teaching_query.py](../../backend/app/services/teaching_query.py), [answers.py](../../backend/app/services/answers.py). Tests first reproduced the confirmed failures. The independent review raised scope/promotion/fallback problems; they were repaired and rechecked. Its final focused review found no remaining important confirmed issues, with 48/48 precision tests, 15 negative reproductions and nine positive/bypass checks. This is a software review, not faculty medical review.

## Fixed before/after source-context challenge

The same frozen 66-question developer challenge used the same source release and index in both arms. It includes ten concepts in five phrasings plus boundary, compound, homonym, context and research checks.

| Measure | Before | Active teaching module |
| --- | ---: | ---: |
| Question-context/status checks passed | 34/66 | 66/66 |
| Citation contexts passing developer relevance patterns | 47/68 (69.1%) | 68/68 (100.0%) |
| Emitted-answer source-binding failures | 0 | 0 |
| Qualified clinical accuracy | Not measured | Not measured |

The relevance checks require the requested topic patterns across sources, reject forbidden contexts and verify explicit missing-topic warnings. **A matching pattern and a source-bound claim do not establish medical truth, semantic entailment or complete answers.** These questions were selected for development and used to repair failures; 100% is not an independent medical accuracy result.

Evidence: [before](../../artifacts/evaluation/precision-v1/baseline-hybrid/summary.json), [after](../../artifacts/evaluation/precision-v1/delivery-challenge/summary.json), [full current answers](../../artifacts/evaluation/precision-v1/delivery-challenge/answers.json).

## Subject-balanced curriculum sample

The sample contains **476 prompts from 119 inventory items across 42 programme/subject groups**, using seed 20261011 and excluding the 278 items in two earlier inspected samples. It uses three curriculum prompt variants and a short concept question per item. After the first sampled comparison, aggregate results were observed and the final scope repair was applied; the final comparison is a follow-up on that fixed sample, not a wholly untouched final holdout.

The preserved pre-change teaching module and current module execute against identical questions, source IDs, source-release/index hashes and the same pinned embedding model. Neither arm changes active files. Batched versus individual embeddings differed by at most 8.2e-08 for the first five queries (tolerance 1e-5).

| Module result | Before | After |
| --- | ---: | ---: |
| Returned a claimed answer | 75/476 (15.8%) | 89/476 (18.7%) |
| Returned answers bound to source text/paired notes | 75/75 | 89/89 |
| No teaching answer | 401/476 | 387/476 |
| Faculty accuracy/completeness | Not measured | Not measured |

This is **handling**, not a validated coverage or correctness score. The remaining 387 unanswered prompts represent a substantial gap. Correlated prompt templates and curriculum descriptors are not medical answer keys. These measurements cover the teaching module; the actual chat handoff is checked separately below. Recorded module timings are diagnostic and include fixed execution order and shared prepared embeddings; they are not an unbiased latency benchmark.

Evidence: [sample](../../artifacts/evaluation/precision-v1/delivery-blueprint.json), [before](../../artifacts/evaluation/precision-v1/delivery-comparison/before/summary.json), [after](../../artifacts/evaluation/precision-v1/delivery-comparison/after/summary.json), [all current sample answers](../../artifacts/evaluation/precision-v1/delivery-comparison/after/answers.json).

## Existing MBBS/MDS benchmarks — losses retained

These older development fixtures have phrase-based answer expectations and bounded developer reference checks. The historical before artifacts have the same release manifest and baseline teaching-module hash as this comparison. They are useful regressions, but some old passing outputs were incomplete or irrelevant, so restoring a score by loosening the relevance checks would not establish improvement.

| Programme | Metric | Before | Current |
| --- | --- | ---: | ---: |
| MBBS | Expected routing/status | 100.0% (n=93) | 94.6% (n=93) |
| MBBS | Expected-source retrieval | 97.5% (n=81) | 92.6% (n=81) |
| MBBS | Mean expected phrase coverage | 85.8% (n=81) | 77.8% (n=81) |
| MBBS | Developer reference agreement | 79.0% (n=81) | 71.6% (n=81) |
| MBBS | Binding among emitted answers | 100.0% (n=81) | 100.0% (n=76) |
| MDS | Expected routing/status | 100.0% (n=28) | 100.0% (n=28) |
| MDS | Expected-source retrieval | 100.0% (n=22) | 95.5% (n=22) |
| MDS | Mean expected phrase coverage | 100.0% (n=22) | 97.0% (n=22) |
| MDS | Developer reference agreement | 100.0% (n=22) | 95.5% (n=22) |
| MDS | Binding among emitted answers | 100.0% (n=22) | 100.0% (n=22) |

Current MBBS routing is **88/93**. Five expected answers now receive no teaching answer:

- `bone-3`: For a viva contrast the roles of osteoblasts and osteoclasts in bone.
- `glut4-2`: Describe how insulin changes the location of GLUT4 to allow glucose uptake.
- `glut4-3`: In a fictional cell signaling example insulin binds its receptor in skeletal muscle. Explain GLUT4 glucose uptake.
- `metabolism-1`: Explain drug metabolism in the developing liver and the effect of liver damage, without dosing advice.
- `metabolism-3`: For a viva discuss microsomal enzymes in infant drug metabolism and liver damage, without personal doses.

These remain unresolved coverage/retrieval cases. Complete, context-matched material is needed before those questions can be treated as supported. Some other returned answers also miss expected phrases: MBBS developer reference agreement is 58/81; MDS is 21/22, with the oral-microbiome case missing two expected fixture phrases. The [full MBBS results](../../artifacts/evaluation/precision-v1/delivery-mbbs.json) and [MDS results](../../artifacts/evaluation/precision-v1/delivery-mds.json) retain every result, missing phrase and response.

The earlier [comprehensive audit](ASTER_COMPREHENSIVE_AUDIT_v2.md) remains an immutable historical baseline. Its 12,192 probes were not rerun with this patch. Neither the new subset results nor the earlier full-inventory handling counts establish comprehensive clinical accuracy.

## Actual chat and software verification

- **392/392 software tests passed**, with one existing Starlette/httpx deprecation warning. Ruff, dependency consistency and frontend JavaScript syntax checks passed.
- **115/115 live checks passed** through the frontend bridge at `http://127.0.0.1:8501`: 66 context/boundary probes, 34 existing routing probes and 15 scope/fallback probes.
- **74/74 emitted live answers** matched exact stored source excerpts or the existing developer-reviewed paired notes. All 38 cited source IDs resolved to the active teaching, primary or secondary records.
- The mixed `osmosis Dolo` fixture checks medicine routing only. It returns medicine notes, and does not establish coverage of osmosis or the relationship asked about; it must not be counted as a complete mixed-question answer.
- Temporary evaluation sessions were deleted. Only synthetic questions were used. The local backend and frontend were restarted after the final checks; readiness reports 2,916 teaching records, 41 explanations, 112 holds and no teaching error.

Evidence: [software log](../../artifacts/evaluation/precision-v1/pytest-final-delivery.log), [actual replies/checks](../../artifacts/evaluation/precision-v1/active-live.json), [live source binding](../../artifacts/evaluation/precision-v1/active-source-binding.json), [independent review](../../artifacts/evaluation/precision-v1/independent-code-review.md).

Earlier candidate artifacts remain intact. In particular, `delivery-live.json` recorded 105/109 checks before the final fallback repair and corrected medicine-routing rubric; `live-precision-and-regression.json` recorded 99/100. They are development evidence, superseded by `active-live.json`, and must not be combined into a final score.

## Faculty review pack and remaining accuracy work

The refreshed [476-answer review pack](../../artifacts/evaluation/precision-v1/delivery-faculty-pack/blinded-cases.json) contains current teaching-module answers, visible warnings/limitations, a [rubric](../../artifacts/evaluation/precision-v1/delivery-faculty-pack/rubric.md) and [blank score sheet](../../artifacts/evaluation/precision-v1/delivery-faculty-pack/scores-blank.csv). All accuracy, coverage, agreement and safety scores are blank. No faculty member has assessed them. Reviewer attestation alone does not verify credentials; the import workflow keeps qualified accuracy null pending verification.

Priority work still includes checking the unanswered topics, missed fixture facts, narrow experimental evidence and source exceptions against qualified medical review; adding permitted, current, context-specific material; validating new explanations; and then repeating independently chosen subject-balanced questions with medically verified answer keys. Retrieval thresholds are lexical/semantic heuristics and can still miss valid paraphrases or select incomplete passages.

The medicine catalogue remains a separate reference layer, with unverified secondary material labelled. Comprehensive interaction checking, equivalence between brands/formulations, and mixed medicine/teaching-question completeness remain unestablished. Handwritten prescription OCR and X-ray models were not changed by this patch; their prior results and limitations remain in the comprehensive audit. No improvement in handwriting recognition or diagnostic imaging accuracy is claimed.

## Provenance and rollback

Active source release: `aster-teaching-comprehensive-audit-v2-2026-10-09` — 2,916 sections, 201 publisher units, 41 paired explanations, 112 source restrictions. Its metadata still records no faculty clinical review.

| Artifact | SHA-256 |
| --- | --- |
| Before teaching module | `35c998b1a1c5c1474cda54a8bd685df080ef852c5f6d7db408a9f436ad2b651e` |
| Current teaching module | `cad8e8e3985932af741aa4a19ec4b1dba878ddff21a55a9c94564a07fc1ec466` |
| Current query planner | `862158c9f39339fe6e1b370afe5f2967dfe3a13e687c1d4418de3e7129742fd0` |
| Current answer service | `752828163d7c53b0962b6fe237639b388e41e5f9f9e5d6d2cfa140fe2b7a7baa` |
| Teaching release manifest | `e770896fa14fd1da17f417c79a4dde6cd2195a05d0fdcad7dc0f7bda4de651da` |
| Teaching index manifest | `388b047922fc5dd6e4db03dbd7c6b5d4f6930a6645fd5559498e920ec14872e6` |
| Fixed 66-question challenge | `761219b6dc0db2f36ae255116f123a14c5d89ac48ec1cfe62975ef68d3c4d87b` |
| Final 476-question sample | `8e14adaed6e4687f8c0a272d82494306029dd8991e7f34ddd63dc73547ba2873` |

The `.env` checksum is unchanged. Source files, release-bound review flags, the vector index, medicine collections and model weights were not changed. Runtime snapshots are in [runtime-before](../../artifacts/evaluation/precision-v1/runtime-before/) and [runtime-after](../../artifacts/evaluation/precision-v1/runtime-after/manifest.json). The pre-change answer-service backup was reconstructed by removing the isolated new block and verified against the exact checksum from the pre-change live run.

For rollback, stop the owned Aster services, restore the preserved `teaching.py` and `answers.py` to their respective service paths, restore the preserved evaluator if reproducing old module evaluation, and restart `start.ps1`. The new query-planner file can remain unused by the restored services. No source/index rebuild or `.env` edit is needed. Rollback reintroduces the documented relevance/fallback failures.

## Repeatable checks

Use fresh output paths to preserve old results. Run from the project root:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check backend scripts tests
.\.venv\Scripts\python.exe scripts/evaluate_teaching_precision.py --backend hybrid --output artifacts/evaluation/precision-repeat
.\.venv\Scripts\python.exe scripts/compare_teaching_precision.py --blueprint artifacts/evaluation/precision-v1/delivery-blueprint.json --baseline artifacts/evaluation/precision-v1/runtime-before/teaching.py --output artifacts/evaluation/precision-comparison-repeat
# With Aster running:
.\.venv\Scripts\python.exe scripts/evaluate_precision_live.py --output artifacts/evaluation/precision-live-repeat.json
```

The comparison rejects code that differs from its frozen sample hashes. A future code/source/model change requires a fresh frozen protocol and fresh output paths, rather than replacing these records.
