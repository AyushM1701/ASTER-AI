# MDS evaluation and laptop measurements — 11 October 2026

The evaluation harness is implemented and has exercised the real FastAPI session → chat → answer → validation → response path with the installed local source release. The latest locked run (`cpu-release-gate`) returned **182/182 HTTP responses, 2/2 resolving citations, 4/4 expected safety behaviors, and 0/150 fully completed pilot tasks** under the strict rubric. Only 2/357 requested facets had observable validated bindings. This is a developer candidate/development evaluation. Independent medical correctness, appropriate abstention adjudication, and F03 remain pending. The 90% completion gate failed; useful source-backed MDS breadth has not been demonstrated.

## Locked bank and provenance

`configs/benchmarks/mds-pilot/v1-2026-10-11/manifest.json` binds the question files and every installed teaching-release manifest component by SHA-256. `lock` refuses to overwrite an existing directory; `verify` rejects changed question or source bytes. Create a new version directory for revised prompts or sources. `run` verifies before and after evaluation and writes to a fresh output directory. Evaluation files are outside production retrieval/training; no source index was changed.

The 150 candidate prompts are developer authored and inspected, using curriculum scope descriptors rather than medical reference answers. They were locked before running the candidate evaluation, while production code was still being developed. They therefore remain development data, including when results inform fixes. They are neither unseen nor independent validation. No authoritative answer key is bundled. The template-based sampling is a reproducible engineering pilot, not a representative specialty examination.

| Dimension | Predeclared distribution |
|---|---|
| Families | 15 each: oral/dental histology; general pathology; developmental abnormalities; mucosal disorders; oral cancer/dysplasia; odontogenic lesions; salivary disorders; bone/soft tissue; oral microbiology; laboratory diagnosis |
| Entities | Three per family, each with five requested operations |
| Operations | Definition 30; mechanism 30; comparison 30; essay 30; histology 27; research appraisal 3 |
| Difficulty | Basic 30; intermediate 60; advanced 60; labels are author judgements |
| Requested topic × facets | 357 total; topic names do not imply evidence readiness |
| Separate known regressions | 11 reconstructed tasks + 11 paraphrases; original verbatim questions unavailable |
| Separate other probes | 6 installed-source contamination term checks across 2 distinct question texts + 4 personal advice/urgent safety requests |

The pilot samples ten of the twelve national curriculum families; oral systemic disease and forensic/research methods require expanded sampling. `audit_overlap` detects families crossing splits, cross-split near duplicates, and prompt overlap with supplied source-derived examples. The existing source-bound developer benchmark contributed 28 known example questions; the check observed zero overlaps at the disclosed threshold. That result cannot prove independence or exclude medical conceptual overlap. A fresh independently authored holdout is still required. Keep entity/family clusters together when expanding to 300–500 prompts, run this checker against all development and source-derived banks, freeze source versions, and avoid tuning on the holdout.

## Actual measured comparison

Both runs used identical locked prompts and the same `aster-teaching-all-mds-v3-2026-10-10` source bytes (7,773 records, 404 registered sources). The baseline loads the untouched checkpoint backend in an isolated Python subprocess; it does not copy old code into the active project. Explicit settings select CPU lexical retrieval, extractive answers, teaching enabled, general inference disabled, research networking disabled, and a temporary education workspace. Each request gets and deletes a separate real API session.

| Metric | Untouched checkpoint | Preliminary current (superseded) | Final current |
|---|---:|---:|---:|
| HTTP requests | 182 | 182 | 182 |
| Citation records resolving to source version/section/text | 25/25 | 194/194 | 2/2 |
| Claims flagged by exact text + coordinate check | 0/25 | 0/194 | 0/2 |
| Exact topic-word relevance signal over displayed evidence | 18/25 | 170/194 | 1/2 |
| Observable required facet bindings | 0/357 | 105/357 | 2/357 |
| Complete with every predeclared facet binding and shape | 0/150 | 22/150 | 0/150 |
| Abstentions/blocked or unsupported results | 168/182 | 91/182 | 180/182 |
| Listed contamination strings in six trap checks | 0/6 | 0/6 | 0/6 |
| Safety policy expectations | 2/4 | 2/4 | 4/4 |

The checkpoint lacks the new canonical coverage and facet-binding contracts. Its 0/357 and 0/150 values mean this strict new contract was not observable; they do not establish zero biomedical coverage. Current completion requires actual claim-to-source bindings and does not count headings or the model's self-rating as support. Some legacy prepared definitions can lack these mappings despite returning material. Source applicability and facet semantics need independent expert assessment; topic-word relevance is a narrow deterministic signal. Exact quote fidelity cannot prove that a source claim is correct, suitable, or sufficient.

Final source applicability checks conservatively withheld mixed-topic whole source units. The earlier 22/150 figure is superseded, not a final achievement. Final coverage statuses were 176 insufficient-evidence, 2 partial, and 4 blocked. There were zero HTTP transport failures, and the run's backend-file checksum comparison detected no code mutations during measurement. Latest raw responses and scores are in `cpu-release-gate`; the latest blinded human pack is `cpu-release-gate/faculty-review`. Intermediate `cpu-final`, `cpu-reviewed` and `cpu-final-verification` runs are preserved and superseded by this run after the final viva/marks corrections. The explicit reviewed whole-unit exception is wired into the runtime, but no production source annotations have been fabricated or inserted. The completion and source-readiness gates fail. Authoritative facet-ready sources and qualified review of source-unit granularity/applicability are needed before advertising these topic/task combinations as ready. This evaluation does not recommend weakening validation merely to raise completion.

The initial scorer incorrectly required `source_id`, which the published legacy citation schema omits. Its failed scorecards are retained in `cpu-current` and `cpu-checkpoint`. `cpu-current-scored-v2` and `cpu-checkpoint-scored-v2` transparently rescore the original raw response bytes against the schema's stable chunk identity, version/section/title/URL coordinates where present, and exact excerpt. No prompt, production output, or source bytes were changed to raise scores. Duplicate IDs cannot hide forged coordinates.

The initial safety failures were a personal definitive diagnosis request routed to generic insufficiency and a severe breathing difficulty request routed to generic insufficiency instead of urgent guidance. They occurred in the checkpoint too. Those failed probes are retained. The final post-fix run observed all four expected policy behaviors: personal diagnosis/medicine/dose requests were blocked and severe breathing difficulty received urgent guidance. This establishes these four engineering regressions, not comprehensive clinical safety. Zero observed trap contamination is six term checks over two distinct questions, without inserted adversarial source passages. It cannot establish rejection of every possible retrieved distractor. Dedicated synthetic hard-negative unit tests provide separate mechanics evidence.

## CPU and GPU observations

This machine reported Windows 11, Python 3.13.3, approximately 23.7 GiB physical RAM, and NVIDIA GeForce RTX 4050 Laptop GPU with 6,141 MiB VRAM and driver 581.86. The preliminary CPU current/checkpoint runs overlapped each other and the model probe; those timings are archived and cannot establish a controlled speed comparison. The following latest CPU runs were sequential evaluation subprocesses with no concurrent model probe from this harness. Other desktop/test processes were not stopped, and the pipelines perform different validation work, so the measurements remain descriptive.

| Measurement | Checkpoint CPU API | Current CPU API |
|---|---:|---:|
| Median / 95th percentile request latency | 2.14 / 27.83 ms | 54.01 / 205.96 ms |
| Maximum request latency | 49.64 ms | 400.39 ms |
| OS process peak working set | 738.1 MiB | 742.5 MiB |

The bounded real Ollama streaming probe used `qwen3-vl:2b-instruct`, digest `ea422f1e73652a95479954d8572d3c8c6022f628ce2d38a1a04aae1b7f2d5300`, one existing public teaching-source oral epithelial excerpt, maximum 120 predicted tokens, and 2,048 context tokens. It measured an initially nonresident request followed by the same-model warm request. It did not unload a user's model or load an alternative model.

| Probe | First content | Total response |
|---|---:|---:|
| Initial nonresident load, no forced unload | 7,325.69 ms | 8,179.63 ms |
| Warm requested | 24.15 ms | 855.85 ms |

Whole-device VRAM reached an observed sampled maximum of 5,548 MiB; it is not isolated model allocation and one-second samples can miss a peak. System RAM usage reached 21,283,676,160 bytes while other processes were active. Raw samples, Ollama load/prompt/generation durations, residency, source hash, and generated probe text are retained in `model-probe/performance.json`. The probe text is unvalidated evaluation output and is not inserted into production evidence. Production uses a buffered adapter, so production user-visible first-token time is unknown. A controlled forced-unload cold start and comprehensive long-essay GPU load test remain pending.

## Run and inspect

Run from the project root in PowerShell. The normal launcher and application profile remain documented in `README.md`; this harness never changes `.env` or builds indexes.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_mds_pilot.py -q
.\.venv\Scripts\python.exe -m ruff check scripts/mds_pilot.py scripts/evaluate_mds_pipeline.py tests/test_mds_pilot.py
.\.venv\Scripts\python.exe scripts/evaluate_mds_pipeline.py verify
.\.venv\Scripts\python.exe scripts/evaluate_mds_pipeline.py run --output artifacts/evaluation/mds-upgrade-2026-10-11/cpu-next --faculty-pack --source-examples artifacts/evaluation/mds-upgrade-2026-10-11/source-derived-known-examples.jsonl
.\.venv\Scripts\python.exe scripts/evaluate_mds_pipeline.py run --backend-root artifacts/checkpoints/mds-upgrade-2026-10-11 --output artifacts/evaluation/mds-upgrade-2026-10-11/checkpoint-next
.\.venv\Scripts\python.exe scripts/evaluate_mds_pipeline.py model-performance --output artifacts/evaluation/mds-upgrade-2026-10-11/model-next
```

For a new independently authored bank, create a fresh version directory and source lock rather than editing this bank. The current `lock` command generates the disclosed developer bank; independent holdout authors must provide separate reviewed questions. `--limit` is for smoke checks and does not establish pilot success. Preserve `responses.jsonl`, `scores.json`, `summary.json`, and their prompt/source checksums together. Inspect `missing_facets`, `evidence_plan` reason codes, and `claim_evidence` coordinates in raw responses for source gaps; do not turn those questions or generated outputs into source material.

The harness reuses `backend/app/services/medical_evaluation.py` for its legacy exact-passage signal alongside the stronger source-coordinate score. `--faculty-pack` reuses `scripts/curriculum_audit.py` to create blinded response/reference views, a private association key, blank human-review CSV, and the existing ordinal review rubric. No human scores are filled in. Reviewer credential verification and qualified independent review are still required; CSV attestations alone do not satisfy F03. Appropriate abstention, semantic claim support, contradictory-source adjudication, medical relevance, and clinical safety need that independent review. Multi-turn success remains null in this single-request pilot; dedicated viva integration tests provide separate engineering evidence.

The final measurements were produced by these exact commands; their output directories are now preserved, so choose a fresh name when repeating them:

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_mds_pipeline.py run --backend-root artifacts/checkpoints/mds-upgrade-2026-10-11 --output artifacts/evaluation/mds-upgrade-2026-10-11/cpu-checkpoint-serial --source-examples artifacts/evaluation/mds-upgrade-2026-10-11/source-derived-known-examples.jsonl
.\.venv\Scripts\python.exe scripts/evaluate_mds_pipeline.py run --output artifacts/evaluation/mds-upgrade-2026-10-11/cpu-release-gate --faculty-pack --source-examples artifacts/evaluation/mds-upgrade-2026-10-11/source-derived-known-examples.jsonl
.\.venv\Scripts\python.exe scripts/evaluate_mds_pipeline.py model-performance --output artifacts/evaluation/mds-upgrade-2026-10-11/model-probe
```

## Validation evidence and release gates

The initial tests-first run recorded six missing-tool failures and one passing real CPU API check. Separate duplicate-forged-coordinate and stale-span-hash tests failed before their fixes. The latest local evaluation test run recorded **10 passed**, with the existing FastAPI/Starlette `httpx` deprecation warning. Ruff reported **all checks passed** for the three owned files. Logs are saved under `artifacts/evaluation/mds-upgrade-2026-10-11`. The coordinating implementation run reports the repository-wide suite separately; this document does not extrapolate ten tests to a green full repository.

Citation resolution passes on the two latest displayed records and six contamination term checks observed no listed contamination. The >=90% declared core completion target fails at 0/150. Appropriate abstention is unscored; independent medical quality/F03 is pending; four final safety regressions pass, while comprehensive clinical safety remains unmeasured; multi-turn pilot scoring is pending; controlled GPU cold-start, clean Windows install verification, full amendment reconciliation, and permission/clinical review of expanded foundational packs are separate pending gates. Do not publish a clinically certified capability claim or a release based on this pilot. The reviewed inactive source-pack adapter and its separate manual review gate are documented in `MDS_STAGED_PACKS_2026-10-11.md`; no actual collected pack has been promoted without review.


Subsequent 2026-10-12 source-pack work: [inspected-pack report](MDS_INSPECTED_PACK_2026-10-12.md). The frozen candidate improved from 0/150 to 38/150 complete tasks; 112 remain incomplete. This supersedes the earlier current development result, while preserving its historical artifacts. Engineering verification: 888 tests passed, Ruff clean.
