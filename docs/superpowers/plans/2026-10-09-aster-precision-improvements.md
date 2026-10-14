# Aster retrieval precision improvements

**Goal:** Improve relevant source selection and preserve unsupported question scope,
without equating automatic source-fit scores with faculty medical accuracy.

**Design:** Bounded repairs to the existing teaching path. Separate explicit
presentation instructions from the requested medical concept. Keep the original
question for policy, medicine identity, jurisdiction and source-scope guards.
Retrieve explicit comparison and independently named topic parts separately;
display missing parts and unsupported requested answer types. Require candidate
support in source text/section rather than broad keywords alone. Prefer directly
relevant foundational material for general definitions, with research settings
retained whenever research evidence is used. Preserve all release holds and hashes.

The user has authorized accuracy improvements and previously authorized fixes and
reversible local activation. No new model, medical fine-tuning or external service
is required. Existing source rights and faculty-review status remain unchanged.

- [x] Freeze a source-fit challenge set and baseline before runtime changes.
- [x] Add failing tests for presentation wrappers, compound omissions, context
  modifiers, misleading homonyms, keyword-only matches and research preference.
- [x] Implement a conservative question plan and targeted relevance gates.
- [x] Run the same challenge set plus existing MBBS/MDS, policy and full software
  regressions; inspect any lost answers rather than relaxing thresholds.
- [x] Measure subject-balanced inventory samples; retain unanswered
  cases and distinguish answer handling from source relevance and medical accuracy.
- [x] Activate only after checks, verify actual chat, record rollback and publish
  before/after evidence. Human accuracy, handwriting and X-ray validation remain open.

Final evidence: `ASTER_PRECISION_IMPROVEMENTS.md` and
`artifacts/evaluation/precision-v1/delivery-manifest.json`. The fixed challenge
is development evidence; the final 476-prompt comparison is a follow-up on an
already sampled inventory set. Neither is an independent medical examination.
Independent software review confirmed scope/facet/fallback repairs. Full software
suite: 392 passing tests. Actual chat: 115 passing routing/context checks, 74
source-bound emitted answers. Faculty scores remain blank in the refreshed pack.
