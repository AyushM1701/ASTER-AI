# Aster Comprehensive Audit Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development or executing-plans.

**Goal:** Diagnose and fix curriculum/retrieval/evaluation gaps with auditable evidence.
**Architecture:** Independent curriculum and acquisition artifacts, root-owned runtime
fixes, immutable combined release and evaluations, separate qualified-review workflow.
**Tech Stack:** Python/FastAPI, TeachingStore, MiniLM/NumPy, official PDF and licensed XML/HTML.
**Spec:** ../specs/2026-10-09-aster-comprehensive-audit-design.md

## Constraints and review focus

No simulated faculty review. Preserve source licenses, research limits, old records,
holds and medicine identity boundaries. No global threshold reductions to manufacture
coverage. Evaluate aliases, composite topics, vague lab terms, source errors, dosing
and personal reassurance. Keep theory and practical assessment distinct.

## Tasks

- [x] Curriculum worker: verify official specialty scope and build a provenance-bound
  inventory at configs/mds_full_curriculum.json; implement all-topic test blueprint
  and blinded faculty pack/import workflow under scripts/curriculum_audit.py and
  tests/test_curriculum_audit.py. No edits to runtime or shared releases.
- [x] Acquisition worker: acquire licensed foundation material for documented gaps
  into raw/audit-foundations and components/audit-foundations; use a new source config
  and builder with rights/extraction tests. No edits to old sources or runtime.
- [x] Independent review worker: inspect source/answer quality across all existing
  topic outputs and architecture; write artifact findings with exact chunk/code
  evidence. Never fabricate faculty assessments; do not mutate production files.
- [x] Root: reproduce unanswered and misleading answers, add failing regressions,
  implement anchored query handling and policy/source safeguards; rerun focused tests.
- [x] Root: integrate approved new content, preserve notes/holds, build pinned release
  and index; evaluate curriculum and topic variants plus MBBS/medical routing.
- [x] Root: run full software checks and available OCR/X-ray evaluations, write all
  measured scores and unresolved external dependencies; locally activate and test
  actual chat bridge only if source/runtime checks pass. Preserve rollback.

## Measured delivery and open requirements

The listed engineering tasks produced artifacts and the corrected local release is
active. The source review is developer/AI-assisted; specialty review is partial.
Full extracted-inventory runs completed: 101/9,144 complex prompts and 840/3,048
short concept prompts were handled. These are not medical accuracy scores.
339 software tests and 34 local chat checks passed. Both faculty packs are ready.

- [ ] Qualified faculty medical accuracy and completeness assessment.
- [ ] Independently verified full curriculum extraction and reference answer keys.
- [ ] Full clinical content and composite question/case reasoning gaps.
- [ ] Observed practical, communication and laboratory competence assessment.
- [ ] Representative full-prescription handwriting and independent X-ray validation.

See `ASTER_COMPREHENSIVE_AUDIT_v2.md` and its per-item gap register. No claim that
all gaps are closed or that the full curriculum has been medically validated.
No Git repository is present; immutable file manifests replace commit checkpoints.
