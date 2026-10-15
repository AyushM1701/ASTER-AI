# General MDS Question Support Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans task by task.

**Goal:** Support reusable MDS teaching operations and genuine source-bound explanations across the nine specialties represented in the user examples.

**Architecture:** Extend the existing question planner, source selector, facet composer and shared validator. Keep prepared explanations release-bound and distinct from exact-source quotations. Use a separate immutable supplied-question benchmark with variations and preserved conversations.

**Tech Stack:** Python/FastAPI, local Ollama, HTML/CSS/JavaScript, existing lexical/hybrid retrieval.

**Spec:** ../specs/2026-10-12-mds-question-generalization-design.md

## Global Constraints

Preserve patient policy, source identities/permissions, qualifications, temporary sessions, national-only curriculum and existingAPI compatibility. Never infer source readiness or clinical approval. Preserve old150pilot bytes/scorer. No active release/index/config mutation during development.

## Review Focus

Mixed known/provisional comparison entities; pronoun depth followups; personal symptoms mixed with technical vocabulary; fictional cases with unnamed diagnoses; forged prepared explanation bindings.

## Tasks

- [ ] Capture all supplied questions/turn sequences and immutable hashes; add varied task contracts in a new benchmark. Verify original attachments and oldpilot remain unchanged.
- [ ] Add failing planner tests for 3–6 entity comparisons, examiner viva, mixed multipart requests, explicit fictional cases and added facets. Implement bounded parser changes; run existing planning/safety regressions.
- [ ] Add failing source-grounded prepared explanation tests for correct bindings and forged text/IDs/source hashes. Extend the composer and shared terminal validator; retain exact-source fallback and visible gaps.
- [ ] Wire prepared composition into AnswerService and add facet retrieval support; test definition, mechanism, comparison and partial-answer behavior against actual verified source releases.
- [ ] Evaluate supplied and varied prompts plus multi-turn sequences against a frozen staged source version. Identify missing topic/facet explanation units; obtain only authorized original material and actually review units before admission.
- [ ] Run full regression suite, frontend checks if presentation changes, and fresh code review; document coverage and remaining source/clinical gates accurately.

No Git repository is present; preserve current files and use existing checkpoints plus immutable artifacts instead of commits.
