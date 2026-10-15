# Supplied MDS question contracts

The two attachments contain 89 cases and 93 user turns: 30 Oral Pathology cases, six cases for each of nine MDS specialties, and five cross-specialty tests. The current bank is `configs/benchmarks/mds-supplied/v2-2026-10-12/`. It retains every supplied message, its SHA256, the original numbered source line, and byte-for-byte attachment copies. Eighteen developer paraphrases vary topic order and wording across all nine specialties; they are related development examples, with no independent holdout claim.

| Input | SHA256 of original bytes |
| --- | --- |
| Oral Pathology attachment | `e5a95584efcacc3bf5342c7fcb64607d4a5fc6df20c2aed60640c1e4147362cc` |
| Nine-specialty attachment | `8040c785c80feeaae3eab164711b786fd8fd8de8547797e22a12c84b32ac5439` |

`scripts/mds_supplied_contracts.py` owns the request annotations, and `scripts/evaluate_mds_supplied.py` verifies the locks, audits plans and source mentions, or captures actual local API responses. Neither module belongs in retrieval or runtime answer generation. Changing the bank requires a fresh version directory. The first version remains unchanged; version 2 adds content/interaction separation and subject-specific multipart contracts.

The annotations state what the question asks. They contain no medical answer key. A facet named `TP53` requires discussion of that requested subject; recognizing the token does not prove the discussion correct. Structured comparison presence, resolved citation coordinates and bound text spans similarly cannot establish clinical completeness. Both clinical accuracy and clinical completeness remain `null`.

## Existing evaluation gaps

`scripts/mds_pilot.py` provides 150 developer prompts across ten predominantly Oral Pathology families. Its reconstructed regression prompts say that the original questions were unavailable. The new attachments supply those exact messages and substantially extend the scope; this bank leaves the existing 150 prompts unchanged.

`scripts/evaluate_mds_pipeline.py` creates and deletes a session for each prompt. Its published `multi_turn_success` remains unknown, which is appropriate for that run. It cannot exercise either the two-turn apoptosis sequence or the four-turn osseointegration sequence. The separate runner keeps each supplied sequence in one isolated API session and records each response without treating an HTTP success or a parser match as teaching success.

The grading instruction in cross-specialty Test E says “After I answer”; the attachment supplies no learner answer. The fourth turn must therefore remain a conditional instruction. An optional, separately disclosed nonsense-answer probe can test whether the implementation refrains from awarding subject-knowledge credit. Rubric quality and difficult follow-ups still require human review. The bank separates interaction requirements from content-facet denominators, and the first simple apoptosis turn does not inherit the later postgraduate pathway requirements.

The attachment introduces Oral Pathology cases 21–25 as fictional postgraduate educational cases. Their individual messages do not repeat that context. The bank preserves both the exact messages and the introduction's instruction; `--attachment-context` adds it as an explicit preceding turn while retaining the original message unchanged. The default run sends the supplied messages verbatim.

## Provisional inspection and source facts

The first inspection is retained at `artifacts/evaluation/mds-supplied-2026-10-12/baseline-contract-audit/`. It covers all 89 supplied cases plus 18 variations. Runtime files changed during the inspection, so its planning counts are provisional and cannot serve as a stable untouched baseline. The JSON explicitly records `code_changed_during_audit: true`. Source files stayed unchanged.

The inspected `aster-teaching-all-mds-v3-2026-10-10` release contains 7,773 chunks. Independent literal subject-name searches found no mentions for 36 of 113 annotated subject names. Examples include sodium hypochlorite irrigation, vertical dimension at rest, and symptomatic apical periodontitis. Synonyms, hyphenation and narrower case descriptions can cause false negatives. A positive mention can come from unrelated prose; this search measures neither scientific adequacy nor facet support. `source-mention-audit.json` records counts, sample chunk IDs, and the limit of that signal for every subject.

Individual captured plans show why whole-question checks are necessary. One inspection parsed the oral submucous fibrosis etiopathogenesis question as `local:the`; it parsed the second apoptosis message as `local:now_explain_the`. A mixed mechanism/comparison prompt became one comparison operation. These rows are diagnostic observations from a changing code snapshot. The final runtime audit must use frozen source and code snapshots before drawing implementation conclusions.

The earlier implementation plan declares nine specialty mappings but describes the 150-prompt candidate evaluation as its delivery evidence. That demonstrates evaluation tooling, not coverage of all questions across all specialties. Source-pack staging, topic vocabulary, task planning, response structure, source-supported answers, and independent medical review need separate evidence.

The first actual API capture, `artifacts/evaluation/mds-supplied-2026-10-12/generalization-v1-api-initial/`, uses the 7,778-record staged generalization pack. It reached 111 turns across 107 cases with HTTP 200 throughout. Raw coverage fields reported 87 insufficient-evidence turns, 11 partial turns, six complete turns and seven omitted values. Five of the six complete turns started a viva and contained no answer claims; the other was the dental-caries mechanism question. Thirteen turns contained any claims. These counts show how transport and activity completion differ from answering the requested content.

That capture also records changed runtime code and stays provisional. Its structured-comparison presence detector initially required legacy rows alongside axis cells; real Aster responses use axis cells with empty legacy rows. The detector now accepts the actual axis/cell schema, with a regression test, while preserving unknown clinical scores. Initial raw responses and original scoring artifacts remain unchanged. The frozen rerun below supplies the final engineering capture.

## Frozen version 2 result

The final captures are `artifacts/evaluation/mds-supplied-2026-10-12/frozen-v2-api/` and `frozen-v2-contract-audit/`. Both report unchanged runtime and source hashes throughout capture. The staged release contains 7,778 records and 58 prepared units; 18 prepared units have 34 explicit facet bindings. It also retains 118 source wording holds. The evaluator leaves the existing 150-prompt pilot and active release unchanged.

| Actual API observation | Count |
| --- | ---: |
| Supplied cases plus disclosed variations | 107 |
| Recorded conversation turns | 111 |
| HTTP 200 responses | 111 |
| Insufficient-evidence coverage fields | 86 |
| Partial coverage fields | 13 |
| Complete coverage fields | 5 |
| Omitted coverage fields | 7 |
| Turns containing any claims | 14 |
| Complete turns containing claims | 0 |
| Complete viva starts containing no claims | 5 |
| Recognizable comparison table structures | 19 |

The two-turn apoptosis sequence and four-turn osseointegration sequence returned no claims. The latter still exposed an overlong topic identity in the first turn and an unhelpful `local:go_deeper_into_the` identity in its second turn. Eleven separately recorded nonsense-answer probes produced five provisional viva feedback responses with `score: null`; the rest reported insufficient evidence. These observations do not demonstrate semantic assessment, difficult follow-ups, or successful progressive teaching.

For the six supplied questions in each specialty, the API returned some claims in the following number of cases. Every such response had partial coverage; a count of one means a source-supported fragment was returned, not that one full question passed.

| Specialty | Cases with any claims, out of six |
| --- | ---: |
| Conservative Dentistry and Endodontics | 1 |
| Orthodontics | 1 |
| Oral and Maxillofacial Surgery | 1 |
| Prosthodontics | 0 |
| Periodontology | 1 |
| Pediatric Dentistry | 0 |
| Oral Medicine and Radiology | 0 |
| Oral Pathology | 2 |
| Public Health Dentistry | 1 |

Three exact trusted prepared explanations appeared across two turns: sulcular epithelium and junctional epithelium in Oral Pathology question 3, and orthodontic mechanotransduction in the orthodontic mechanism question. All returned prepared pointers passed exact pinned-unit text/hash, parent-record identity, citation metadata, qualification and hold-exception checks. This records paired explanation availability separately from raw quotations. The evaluator does not call the runtime prepared-admission helper and does not infer paraphrase entailment or medical correctness from matching identities. The legacy quote-only signal remains separately labeled.

The frozen plan audit records 59 first turns with missing exact topic IDs and 90 with missing exact content-facet keys. Differences in synonym vocabulary, topic granularity and facet names can explain some mismatches; those counts require row-level adjudication. The literal source-name audit still reports 36 subjects without mentions. Neither signal can supply a clinical pass rate. One variation beginning “Trace periodontal bone loss” returned two quotations through the legacy teaching path without a coverage field; its requested-facet handling therefore remains unverified.

The general ability to answer all supplied questions across all nine specialties remains incomplete. The staged source pack and runtime routing improvements should not be described as postgraduate clinical completeness. The frozen raw responses expose the current evidence and conversation limits without turning parser recognition, HTTP success or citation identity into a clinical claim.

## Reuse and verification

Run these from the project root with the project's Python environment:

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_mds_supplied.py verify
.\.venv\Scripts\python.exe scripts/evaluate_mds_supplied.py audit --variations --release RELEASE_DIRECTORY --output NEW_AUDIT_DIRECTORY
.\.venv\Scripts\python.exe scripts/evaluate_mds_supplied.py run --variations --viva-probe --release RELEASE_DIRECTORY --output NEW_API_DIRECTORY
.\.venv\Scripts\python.exe scripts/evaluate_mds_supplied.py run --case oral-29 --case cross-E --release RELEASE_DIRECTORY --output NEW_SEQUENCE_DIRECTORY
```

Each output directory must be new. Runs use the actual FastAPI routes through `TestClient`, a temporary workspace database, separate sessions between cases, and shared sessions within a sequence. External research and model inference are disabled. The runner pins source file hashes and captures runtime hashes before and after the run so concurrent edits remain visible. It records raw responses and engineering signals; qualified review of evidence, completeness, uncertainty, conversation memory and teaching depth remains outstanding.

Eighteen integrity tests pass in `tests/test_mds_supplied_contracts.py`. They cover attachment identity, locked-byte tampering, refusing overwrites, all specialty/task distributions, turn-specific scope, multipart subject ownership, disclosed variation provenance, the actual comparison axis/cell schema, forged prepared text/parent hashes/scopes/citation coordinates, duplicate citations, output-only units, exact hold exceptions, and preserving unknown clinical scores despite a positive identity or structural signal. Ruff passes on both evaluation scripts and the test file.
