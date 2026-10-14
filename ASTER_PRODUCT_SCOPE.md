# Aster product scope

**Updated:** 10 October 2026, following the owner's audience clarification.

**Implementation update — 11 October:** the remaining local workflow infrastructure has been added and tested as a bounded development pilot. See [implemented behavior, verification and outstanding scope requirements](docs/PRODUCT_SCOPE_IMPLEMENTATION_2026-10-11.md). This scope is still the requirements document; its qualified-review, real-user, full-coverage and distribution gates are not marked complete by engineering tests.

**User-selected audiences:** patients and students. Students should be supported in studying and writing articles/research papers. **Proposed implementation:** the workflows and sequence below. This document does not claim that these capabilities are already implemented or evaluated.

This scope supersedes the MDS-only direction recommended in the [project audit](ASTER_PROJECT_REVIEW_2026-10-10.md). Its confirmed defects, evaluation limitations and release gates still apply.

## Purpose

**Aster helps people understand medical information, learn it in depth and work with the evidence behind it.**

One shared evidence system can serve two audiences through three tasks: **Understand, Study and Research & Write**. The shared foundation is accurate source selection, applicable context, clear explanation and traceable claims. Different tasks need different outputs and evaluations.

Patients are a core audience. Following the owner's further request, the student content scope now spans all nine MDS specialties as well as MBBS. Oral Pathology and Oral Microbiology is the earlier content pack; the [all-specialty research expansion](ALL_MDS_LIBRARY.md) broadens the library. Coverage remains staged and incomplete, with independent medical review pending.

## Three workflows in one conversation

| Workflow | Typical request | Useful output | Completion means |
|---|---|---|---|
| Understand | “What does this term mean?” or “Help me understand this medicine reference.” | A brief, calm explanation; relevant deeper detail; limitations; useful questions to ask a clinician | The actual question is answered at an accessible level with appropriate evidence and uncertainty |
| Study | “Compare these concepts,” “Explain the mechanism,” or “Ask me a viva question.” | Simple introduction, subject-appropriate depth, comparisons, examples and supported practice | The requested learning activity is delivered, rather than replaced with related excerpts |
| Research & Write | “Find literature on this question,” “Compare these papers,” or “Help structure my review.” | Search strategy, verified source list, evidence table, critical appraisal, outline and source-linked drafting | The work is traceable to inspected sources; the search scope and missing evidence are explicit |

Keep the main chat and right-hand evidence panel. Offer a small optional task selector; infer the task when clear and let the user correct it. A patient should not have to navigate a postgraduate dashboard to ask a question, and a student should not have to repeat “for an exam” in every message.

Task selection changes presentation and workflow, not evidence standards or personal-care boundaries. The same person can move between tasks within a conversation. Carry forward an explicit topic/task context and ask clarification when switching would otherwise introduce ambiguous assumptions.

## Understand: patient experience

- Start with a direct plain-language explanation, in the calm doctor-to-patient style requested by the owner. Avoid implying that Aster is the user's doctor.
- Offer deeper information progressively. Explain unfamiliar terms before using them.
- Distinguish general information from conclusions that require the person's history, examination or clinician review.
- Support understanding of a specified medicine only when product identity, formulation and relevant reference scope are sufficiently clear; ask when ambiguous.
- Explain confirmed prescription text through the existing review workflow. Unclear handwriting remains unresolved; a guessed medicine must never silently become confirmed text.
- Treat plain-text report explanations as a separately tested capability. Image-based lab-report ingestion is a future extension, not an existing feature claim.
- Keep personal diagnosis, medication choice and dose changes outside the product's current scope. Source copying must not introduce unsolicited treatment instructions.
- Preserve temporary/private handling of patient attachments. A patient's document must not become teaching or research-library data automatically.

Patient education does not depend on general chest X-ray scoring or successful handwritten-prescription recovery. Those capabilities keep their separate research and validation requirements.

## Study: student experience

- Use the same understandable introduction, then add accurate subject-level terminology, mechanisms and qualifications.
- Support explicit operations: define, explain, compare, apply to a fictional case, practise a viva and review an answer.
- Build topic packs mapped to a versioned curriculum, showing which operations are supported for each topic.
- Add reviewed practice questions and rubrics. Initial self-assessment can use a rubric; validated automated grading is a separate capability.
- Make optional local progress records separate from patient documents: topics studied, attempts, weak areas and revisit prompts, with export/delete controls.
- Start the student pilot with a bounded Oral Pathology/Oral Microbiology pack. Expand related topics and MBBS subjects only after their own coverage and review checks.

## Research & Write: student scholarship

Start with a focused literature-review and writing-assistance workflow, rather than promising automatic publishable papers.

1. Clarify the research question, population/context, intended article type and scope.
2. Record the search queries, providers, dates and inclusion/exclusion criteria. Label a limited search as limited; do not call it an exhaustive or systematic review automatically.
3. Retrieve and deduplicate verifiable bibliographic records. Check identifiers, title, authors, year and publication status against the source. Track corrections/retractions where provider information is available.
4. Separate title/abstract-only access from inspected full text. Use permitted material; link to inaccessible papers rather than pretending their full text was reviewed.
5. Build an evidence table: question, study design, population/model, methods, findings, limitations, applicability and supporting passages. Keep individual findings separate from consensus or clinical recommendations.
6. Produce an outline and draft sections whose factual claims link back to the evidence table. Preserve contradictory findings and uncertainty.
7. Export editable writing and verified references, with unverified statements and missing evidence clearly marked.

For an original research paper, Aster can help plan a protocol, explain methods, organize user-supplied results and improve writing. It must not invent participants, measurements, analyses, statistical significance, ethics approval or citations. Any analysis of supplied data needs a reproducible method and checks. Authorship, AI-assistance disclosure, institutional requirements and journal policies must be checked for the actual submission; a generated draft is not evidence that those requirements are satisfied.

Do not add autonomous paper submission, outreach to authors or publication to the initial scope.

## Shared technical foundation

Retain the current local Python/backend/browser architecture. There is no demonstrated need to rewrite it to support this scope.

- Separate task identification from topic retrieval and audience presentation.
- Track every requested subquestion and label it answered, partly answered or unsupported.
- Apply common output checks to generated, prepared and extractive answers, including error fallbacks.
- Retrieve suitable material for each task: accessible educational sources for patient understanding, teaching references for study, primary literature and reviews for research. A research paper is not automatically a patient instruction.
- Maintain claim/source bindings and source version, jurisdiction, access and review metadata.
- Store research projects and optional study progress separately from temporary patient sessions. Make retention and deletion explicit.
- Keep a single evidence panel, but adapt its contents: explanation sources, learning references or a research evidence table.

## Delivery order

### 1. Repair the shared answer foundation

Address the audit's output-validation bypass, missing parts of mixed questions, false task completion, repeated follow-ups and benign-intent refusals. Fix contradictory documentation and establish a clean versioned source baseline. These defects affect both audiences and should precede new features.

### 2. Pilot patient understanding and student learning together

Choose approximately ten bounded patient-education questions/topics and ten student topics, with overlap where appropriate. Patient examples could include understanding a medical term, the purpose and limitations of a common test, and a clearly identified medicine's general purpose. This is a candidate selection strategy, not a claim of current supported coverage.

For both audiences, deliver the full journey: question → suitable explanation → meaningful follow-up → usable evidence. Add a small set of reviewed student practice tasks. Observe real users from both groups; do not evaluate one audience and assume the result transfers to the other.

### 3. Add a focused research-writing pilot

Choose one narrow Oral Pathology/Oral Microbiology literature question. Demonstrate a reproducible search, verified bibliography, evidence table and supported review outline/draft. Evaluate this complete workflow before advertising broad research-paper assistance.

### 4. Expand and distribute

Add topics and task types only when they meet their declared review criteria. Resolve required asset rights and complete clean-machine installation checks for the exact release. A working local app does not close these release gates.

## Separate evaluation for each workflow

| Workflow | Required checks |
|---|---|
| Understand | Question addressed; understandable wording; preserved qualifications; clinician-reviewed facts; no unsolicited personal treatment; appropriate uncertainty; patient comprehension/usability |
| Study | Correctness and depth; curriculum/task coverage; comparison/mechanism quality; valid practice questions and rubrics; meaningful follow-ups; qualified educator review |
| Research & Write | Bibliographic identity; search reproducibility; duplicate handling; source-access honesty; faithful study summaries; claim/citation support; contradictions and limitations; no fabricated results |
| Shared system | Regression tests; session/document isolation; privacy; failure-path output checks; latency/resource use; package and source integrity |

Report coverage, correctness, citation integrity and task completion separately. Passing software tests or verifying a DOI does not establish medical accuracy. Current faculty review remains pending, and the recorded audit findings remain open until repaired and retested.

## What this scope resolves

The audiences share one purpose—understanding and using medical evidence—but have different tasks. Aster can support both without making every feature equally prominent or claiming universal competence. The development priority is reliable shared answers, followed by complete audience-specific workflows and measured expansion.
