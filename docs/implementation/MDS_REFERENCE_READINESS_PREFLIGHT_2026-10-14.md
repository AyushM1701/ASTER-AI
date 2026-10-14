# Nine-specialty MDS readiness preflight — 14 October 2026

**Engineering diagnostics only; no medical approval or release activation.**

The current GitHub tree contains `artifacts/source-packs/mds-master-evidence-candidate-v5-2026-10-13` (manifest: 7,791 records, 411 sources, faculty review pending, clinical review false), 237 MDS research XML source files with 237 matching license snapshots, 144 MBBS Markdown foundation files, and nine specialty topic catalogs (126 editorial topic associations).

The checked-in `configs/teaching.env` points to `data/references/mds/releases/aster-teaching-all-mds-v3-2026-10-10` and `data/indexes/all-mds-v2-2026-10-10`, neither present in the Git tree. There is no claim that this checkout is a reproducible installed teaching release. A research article and its license snapshot do not establish chapter-level foundations, training permission, currency, medical correctness or per-facet applicability.

## Reproduce a read-only repository assessment

```powershell
python -m pytest -q tests/test_mds_reference_readiness.py
python scripts/audit_mds_reference_readiness.py --output-dir artifacts/evaluation/mds-reference-preflight --allow-blocked
# No --allow-blocked: exit nonzero until verifications have actually passed
python scripts/audit_mds_reference_readiness.py --output-dir artifacts/evaluation/mds-reference-preflight
```

Generated report: `mds-readiness.json`. Review queue: `facet-review-queue.csv`, extracted from exact request text and turn-specific facet contracts in the committed benchmark bank. Every candidate source mapping, qualification and medical reviewer field remains blank until externally reviewed. The script is read-only with respect to the repository and **always reports `eligible_for_activation=false`**: it is a blocker enumerator, *not* a promotion authority.

## Required external release evidence

1. Reconcile the complete national curriculum and current amendments across all nine MDS specialties. Acquire entire coherent and permitted foundational sections, preserve provenance, rights, version, exceptions, population/condition scope and item-specific exclusions.
2. Independently review exact source-passage bindings for every declared question subject, facet, comparison side and qualification. Adjudicate the 288 previously reported uncomposed diagnostic cells using their original worklist, rather than assuming that lexical matches prove support.
3. Produce medical explanations with traceable claims, source/context validity and complete requested facets. Verify contradiction and qualification behavior; report abstentions honestly. Do not treat unverified model-memory text as source coverage.
4. Evaluate unseen, independently authored, de-duplicated questions **per specialty**, and obtain separately verifiable dental faculty review and independent correctness, completeness, source-applicability and safety judgments.
5. Stage a new immutable source pack, build an index pinned to its content hash, compare against candidate-v5 using the fixed development bank and new holdout, verify actual hardware and clean installed startup, and retain a tested rollback. Switch runtime settings only after the complete independent signoff chain.

The latest owner report states 20 substantive and 5 complete source-backed responses out of 111 turns, not postgraduate educational readiness. This patch makes no runtime, model, pack or index changes and is not a medical certificate.
