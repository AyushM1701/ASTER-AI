# Implementation ledger

- Specification read in full; current architecture inspected.
- Foundation already includes common output checks, subquestion handling, safe follow-up abstention and bounded patient symptoms (F21).
- Implemented: isolated persistent educational records and APIs; bounded public literature retrieval, permission/identity admission, exact quotation evidence, scaffold/BibTeX exports and revision-checked user drafts; 43-topic activity browser with ten-topic Oral Pathology pilot; topic/task continuity; optional progress/revisit/export/delete; two-term plain-text report glossary; inline browser workspace.
- Ruling: a bounded literature pilot will use Europe PMC, with public queries only and no automatic inclusion of patient attachments. Limited provider searches are never labelled systematic or exhaustive.
- Ruling: automated/source-based rubrics remain developer checked and clinically unreviewed. No invented human evaluation, broad accuracy score or universal competence claim.
- Tests first: missing-module/route/continuity/report/presentation cases observed failing, then passing. Live JATS failure traced to external DOCTYPE and nested license href; hardened parser and exact identity checks repaired with realistic fixtures.
- Fresh whole-change review: passage export omitted, unsaved editor overwrites, BibTeX author separators and retraction downgrade. Repaired; regression cases added. Real browser unsaved draft restoration and explicit saving verified.
- Initial full regression: 660 passed in 58.84s. New final regression includes review/presentation repairs.
- Initial live journey: 35 probes, 32 supported, 2 deliberate partial self-assessment activities, 1 medicine-monograph gap. Independent medical accuracy null.
- Public literature pilot: 10 papers, 3 permitted full texts; manual screening, synthesis and critical appraisal remain pending, with task completion false and stage progress explicit.
- Ruling: preserve unsupported metformin formulation result as a visible evidence gap rather than inventing or importing an unreviewed applicable monograph.

- Final full source regression: 664 passed in 58.96s. Following local-date revisit repair, 31 affected tests passed in 7.77s; whole-source Ruff and final JavaScript syntax checks passed. One existing Starlette/httpx deprecation warning remains.
- Browser proof: live ten-paper search, evidence panel, Markdown download with ten passage sections, draft restoration/save, study save and app-restart/page-reload persistence. Local revisit date fixed and verified as 2026-10-12. Research project reopening restores its task selector; startup workspace notice clears after session readiness. Mobile evidence at 390 × 844 has no horizontal overflow and no console errors. Captures and export saved under the evaluation artifact directory.
- Final services: API readiness confirmed, browser app listening on 8501. Test tab closed and original user tab preserved; temporary responsive viewport reset.
- Engineering delivery complete as a bounded development pilot. Qualified review/F03, full curriculum operation coverage, critical appraisal/synthesis, real-user evaluation, exact-release rights and clean-machine installation are explicitly pending. Implementation report maps each outstanding scope requirement; no universal competence or clinical completion claimed.
