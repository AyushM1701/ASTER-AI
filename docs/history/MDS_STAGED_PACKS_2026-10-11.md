# Reviewed inactive MDS source packs

`scripts/stage_mds_pack.py` converts explicitly reviewed selections from the collector's `data/references/mds/open_corpus` into an immutable pack that the existing `TeachingStore` can load. It does not approve automatically collected sources, change the installed release, build an index, train a model, upload data, or activate a pack. Source quality and clinical correctness remain separate gates.

The actual collector files are `manifests/catalogue.jsonl` and `rag_chunks/staged_rag.jsonl`. The adapter uses the catalogue's retained/sanitized document path, extracted JSON path, and rights-evidence path. It checks the exact retained and extracted bytes, the rights evidence, and each selected paragraph's original coordinate and character offsets. Where the original was discarded after rights screening, its raw hash is provenance from the rights record; the adapter does not claim to verify unavailable original bytes.

## Personal review workflow

Wait for collection/report generation to finish before reviewing a snapshot. Both whole input files and each selected document row/retained/extracted/rights file are checksum bound. Any changed manifest or selected source invalidates the review; regenerate a template and personally recheck affected material. Templates approve nothing, and no developer or model is silently substituted for a reviewer.

```powershell
.\.venv\Scripts\python.exe scripts/stage_mds_pack.py template --collector data/references/mds/open_corpus --output artifacts/source-review/review-template-v1.json
```

Keep only the document selections actually reviewed. A real human must enter their name, institution, review date, `assessment_origin=human_entered`, and the exact attestation specified by the script:

> I personally reviewed the selected source text, extraction coordinates, rights evidence and editorial status and entered these assessments.

For each selected source, record the publisher, publication date, study design, population, study context, limitations, topic names and search keywords. Confirm rights, extraction coordinates, source review, and editorial status only after checking them. Record the editorial-check date and a HTTPS publisher/editorial evidence URL, and use `editorial_status=not_retracted_not_superseded` only when supported by that check. Unresolved notices, retraction, supersession, failed extraction, missing rights, or stale coordinates must remain excluded. This attestation records personal source review; it is not independent clinical certification, and the adapter cannot authenticate identity or credentials from JSON.

Do not modify the template's checksum bindings to make changed source bytes appear reviewed. Do not put gold evaluation questions or answers into the pack. Only `training_candidate` source documents/chunks are eligible; `evaluation_holdout`, `eval_holdout`, `validation`, unknown splits, duplicate versions, and duplicate families are rejected even when a review is supplied.

After real review, write the completed attestation to a separate JSON file and stage to a new directory outside both the collector and `data/references`:

```powershell
.\.venv\Scripts\python.exe scripts/stage_mds_pack.py stage --collector data/references/mds/open_corpus --review artifacts/source-review/human-review-v1.json --output artifacts/source-packs/mds-reviewed-v1
```

Existing output directories cannot be overwritten. Preflight failures return `preflight_rejected` and a reason, with no activation. Runtime validation failures preserve the uniquely named temporary staging directory for diagnosis; nothing is installed. The accepted output contains `records.jsonl`, `sources.yaml`, `metadata.json`, `manifest.json`, `review-attestation.json`, and `stage-report.json`, with checksum-bound lineage. The script validates lexical `TeachingStore` loading before renaming the temporary pack to its requested output name. It never rewrites the corpus or `.env`.

The runtime register's compatibility approval is `user_attested`, with the supplied personal review bound to record checksums. It does not use implicit `developer_reviewed` approval. Runtime `clinical_review` remains false, faculty review remains pending, and F03 remains pending.

## Rights, research context and omissions

This adapter currently supports **CC-BY-4.0 only**, on source hosts already accepted by the existing runtime. It verifies the article-specific rights record and exact license URL, preserves attribution and recorded asset omissions, and canonicalizes the equivalent Creative Commons HTTP license link to HTTPS. It does not infer permission from accessibility. CC-BY-2.5 and CC0 sources may have valid source rights, but this adapter rejects them explicitly because this runtime contract has not been extended and tested for those licenses. NC, ND, unknown/conflicting, and unverified permissions are not admitted here.

Every accepted unit is labelled as research, with a prefix containing the human-entered design, population, study context, and limitations. It cannot claim foundational teaching or current clinical consensus merely from keyword association. The text is otherwise an exact selected source substring; original section identity and offsets are preserved separately in metadata. Units whose context plus excerpt exceed the existing 4,000-character limit are omitted intact and listed in `stage-report.json`; they are never silently truncated. A source with no remaining compatible units is not registered, and a completely empty pack fails preflight.

The source-pack adapter does not automatically populate `metadata.reviewed_facet_bindings`. The new reviewed-evidence mechanism requires a separate, explicit whole-unit applicability review of the final research-prefixed runtime text, binding the actual runtime chunk/snapshot/section/text hash to each topic, facet, scope and reviewer while preserving qualifications. Collector labels and this rights/extraction/editorial attestation are insufficient to infer those annotations. Record such annotations through the documented reviewed-evidence contract and generate a new immutable reviewed pack only after that additional human review. Do not lower source relevance thresholds or relabel a research paragraph as a definition to improve the pilot.

## Measured verification

The adapter test bank uses synthetic **nonmedical** data confined to pytest temporary directories. It demonstrates loader compatibility and provenance handling; it contributes no authoritative medical assertions or production sources.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_mds_pack.py -q
.\.venv\Scripts\python.exe -m ruff check scripts/stage_mds_pack.py tests/test_mds_pack.py
```

Tests-first evidence recorded 11 expected missing-adapter failures, followed by **14 passing tests** covering accepted loading, blank attestation rejection, holdout/validation rejection, stale hashes and coordinates, traversal, immutable output, missing rights, failed quality, duplicate families, unsupported CC-BY-2.5/CC0, and intact oversize omissions. Ruff reported all checks passed. Logs are in `artifacts/evaluation/mds-upgrade-2026-10-11/staged-pack-tests-*`.

A real collector-bound blank template was emitted at `artifacts/evaluation/mds-upgrade-2026-10-11/source-review-template.json`. Attempting to stage that blank template failed with `explicit personal human review attestation is required`; `artifacts/source-packs/mds-reviewed-v1` was not created. This expected rejection is retained in `source-review-preflight-rejection.txt`. No actual source pack was promoted or represented as clinically reviewed.

After an accepted future pack, use the existing release composition and index-building workflows with explicit review/activation authorization; this adapter stops at a validated inactive pack. Keep active and rollback releases intact. Re-run the locked API pilot against the newly versioned composed source set under a new evaluation snapshot, keep previously held-out source families excluded, and obtain independent qualified review before advertising evidence-ready topic/task coverage.
