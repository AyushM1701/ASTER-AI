# MDS evidence upgrade implementation plan

Goal: implement the two authorized prompts within the existing local FastAPI/Ollama/HTML project, keeping corpus collection staged for review.

Spec: the three Aster documents retained in `artifacts/checkpoints/mds-upgrade-2026-10-11/`. The third, referenced plan was located in Downloads. User selected official national curriculum only. Original eleven verbatim responses/questions are unavailable; regression fixtures are reconstructed.

Architecture: extend `question_plan.py`, use existing teaching retrieval with per-entity/facet applicability checks, and extend `output_validation.finalize` as the only terminal answer guard. Add bound source-span composition, temporary viva state and frontend views. Keep source collection independent of production ingestion and reuse existing manifest conventions in a reviewed import adapter.

Constraints: preserve APIs, patient/research workflows, safe DOM rendering, session expiry, current models and local inference. No training, external upload, release publication or active-index modification. CC0/CC BY only in default new corpus; share-alike conditional; NC/ND excluded. F03 remains pending independent qualified review. No Git repository exists: file checkpoint replaces commits/worktree. Existing `.env` remains untouched.

Review focus: forged span/coordinates, topic tags attached to unrelated prose, stale sources, out-of-order or concurrent viva submissions, corpus license exceptions and hostile URLs.

Execution: native implementation in this chat, red/green tests for meaningful behavior; requirement tracker records external gates separately.

- [x] 1. Baseline and checkpoint. Record existing tests/hardware/source inventory and actual API path.
- [x] 2. Planning and curriculum. Extend `QuestionPlan` with typed facets, canonical entities, axes, marks and fictional status; preserve existing patient contract. Create national registry with twelve families and nine specialty mappings. Test context retention, comparisons, paraphrases and personal requests.
- [x] 3. Evidence and validation. Add `evidence_plan.py` and `answer_composer.py`; use existing search, bound exact spans, deduplicate, reject inapplicable/stale/unsafe evidence. Compute coverage at terminal boundary, validate shape and support. Test missing evidence, contamination, forged citations, contradictions, outage and safety fallback.
- [x] 4. Viva and frontend. Add state scoped to `Session`, optional turn ID, restart/exit/topic-change handling; hide rubric until submission. Render bound headings/cells, missing facets and provisional feedback with safe DOM APIs. Test real API lifecycle, ownership, expiry and rendering.
- [x] 5. Collection. Add bounded staged collector using authorized Europe PMC API, strict rights, atomic caches, secure URLs, extraction checks, family-level splits, exports, curriculum matrix, data card and checkpoint. Test rejection/limits/resume/unsafe input/leakage; actually collect a cross-specialty batch without modifying active assets.
- [x] 6. Evaluation and operations. Lock a 150-prompt candidate bank with disclosed distribution, run source-backed development evaluation and isolated hard negatives, record real local hardware/performance where feasible; provide reviewed source-pack import/rebuild and rollback commands.
- [x] 7. Verify and review. Full pytest, scoped/full lint and JS behavior checks; fresh code review of final patch, fix material findings. Publish accurate requirement-to-evidence report; source gaps, independent review and unmeasured gates remain explicit.

Baseline: full pytest found one pre-existing failure in `test_answer_scroll_uses_visible_geometry_without_offset_parent_assumptions`; the isolated JS fragment omitted the now-required `scrollBehavior` helper. Preserve production reduced-motion behavior and repair the test harness when frontend checks are updated.

Engineering/tooling phases delivered and verified. Checkboxes do not assert source or clinical readiness: the 150-task completion gate failed, amendment reconciliation and F03 remain pending. See docs/MDS_IMPLEMENTATION_2026-10-11.md and cpu-release-gate for final evidence.

