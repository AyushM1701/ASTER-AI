# Aster MBBS teaching library

User-authorized scope: the six-step curriculum/library/retrieval/explanation/model/evaluation proposal, with doctor-to-patient clarity and MBBS depth. Implement locally, preserve medicine identity protections and existing medicine/OCR/X-ray workflows. No claim of universal accuracy or faculty review without a qualified reviewer.

## Design

Publish a versioned teaching collection separate from the current product-heavy collection. Source acquisition snapshots permitted educational text and Indian clinical workflows, preserves licenses/editions/retrieval dates/hashes, and records developer versus clinical review. NMC competencies form a curriculum checklist, not medical answer evidence. Coverage distinguishes relevant retrieved material from verified competency mastery; unsupported subjects remain visible as gaps.

Teaching retrieval uses lexical and semantic relevance across multiple sections, with subject-aware metadata and source context. Exact medicine queries continue through the existing product store and cannot be resolved from generic teaching notes. Clinical case requests are explicitly educational and retain existing personal diagnosis/dosing boundaries.

Answers begin with plain-language teaching material. Reviewed source-linked explanation units may be selected in full, preserving qualifiers; a language model cannot silently replace them with unsupported claims. Existing unverified medicine notes keep their literal qualification. Meaningful paraphrase support is developer-reviewed paired source/teaching text, not an unvalidated second-model truth judgement. Detailed sections cover mechanisms and MBBS terminology when supported.

Create an educational benchmark with held-out developer-authored question variants across subjects and question types, including unavailable evidence and misleading premises. Report retrieval coverage, correctness against bounded reference answers, completeness against required facts, citation support, latency, resource use, and limitations separately. MCQs do not prove clinical correctness. Faculty review is an explicit external pending stage with a review queue.

Benchmark the installed 2B model against a stronger reputable local text model after checking machine RAM/disk and current publisher metadata. Acquire no paid cloud service. Change the active model only if supported by actual quality/latency evidence; preserve the vision model. Use immutable report artifacts and a configuration backup for rollback.

## Acceptance

- Aster answers supported teaching questions conversationally with traceable citations and requested academic detail.
- The collection has actual acquired records, reproducible integrity checks, a source register and honest curriculum gaps.
- Existing medicine identity, source-grounding, OCR, X-ray and emergency tests pass.
- A local model comparison and live API smoke test are recorded; expert medical evaluation is not fabricated.
- Deliver a Markdown report with coverage, scores, runtime/model decision, licenses, release version and remaining limitations.
