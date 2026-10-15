# Epithelium answer correction

9 October 2026. User-reported question: “What is epithelium?”

## What was wrong

Aster returned a description of sulcular epithelium, a specific gingival region, instead of a general tissue definition. The reproduced response also included a book-coverage notice as if it were teaching content. This was a relevance failure despite valid citations.

The source library already contained a general “Epithelial Tissue” section. Missing equivalent terminology and topic tags shared by specialised sections made the narrower passage eligible. The previous definition filter checked whether a heading contained the term; it did not distinguish the parent concept from a subtype.

## Changes

- Treat epithelium, epithelia and epithelial tissue as equivalent search terminology, while retaining modifiers such as sulcular, junctional and clinical context.
- Preserve “simple” when it qualifies epithelium or a named epithelial shape; do not confuse this structural term with a request for simple language.
- Prefer an eligible whole section heading matching the requested concept over a subtype heading containing that concept. This applies beyond epithelium; cartilage versus elastic cartilage has a regression test.
- Add a bounded general explanation and a separate sulcular explanation. Introductory notes marked `exact_topic` cannot take over a question about a subtype mentioned only as an example.
- Preserve every original source passage and prior release. The new immutable release is `aster-teaching-epithelium-v1-2026-10-09`, containing 2,916 source records, 43 developer-reviewed explanations and 117 review holds. Medical faculty review remains pending.
- Keep full citations and review notices in the existing right-hand source panel; the UI was not changed.

## Medical wording

The user's general explanation is broadly consistent with standard histology: epithelium covers surfaces, lines spaces and forms glands; its functions depend on location and type. In stratified squamous epithelium, “squamous” describes the superficial cells, not every cell in every layer. [OpenStax, Epithelial Tissue](https://openstax.org/books/anatomy-and-physiology-2e/pages/4-2-epithelial-tissue).

Sulcular epithelium lines the gum-facing wall of the sulcus. Junctional epithelium is the distinct region attached to the tooth. The bounded answer no longer says the sulcular lining “creates” the space. [Published review of junctional epithelium](https://pmc.ncbi.nlm.nih.gov/articles/PMC11595533/), [gingivo-dental sulcus anatomy](https://pubmed.ncbi.nlm.nih.gov/341307/).

Keratinization should not be presented as an unqualified either/or statement. Conventional descriptions call sulcular epithelium nonkeratinized, while keratinization potential and experimental changes are separate considerations. This patch does not generate a keratinization or permeability explanation from the questionable original wording. [Keratinization review](https://pubmed.ncbi.nlm.nih.gov/6167706/), [experimental study](https://pubmed.ncbi.nlm.nih.gov/402465/).

## New source holds

| Passage | Runtime treatment | Reason |
|---|---|---|
| General epithelial tissue, `chunk_12cd61937831159f068be326` | Bounded explanations only | Original conflates mucous membrane with epithelium alone and describes transitional layering imprecisely |
| Epithelia are thin, `chunk_3fbce5758f2b9605b90ec58c` | Bounded explanations only | Original overgeneralises surface-cell death from avascularity; supported gland information remains usable |
| Sulcular epithelium, `chunk_445b03532f31ab4dbd17806e` | Bounded explanations only | Misleading “creates” wording and ambiguous keratinization wording |
| Pseudo-stratified epithelia, `chunk_05e61b1642dcc05016d971b8` | Excluded | Incorrectly describes pseudostratified epithelium as genuinely multilayered |
| Book-coverage notice, `chunk_e881e58dc6f32f05894b728a` | Excluded | Says tissues do not appear in the book; supplies no teaching explanation |

These are developer source-comparison decisions, not faculty judgments. The new notes cite supported portions of existing permitted material; external cross-check links are retained in the release notes. No raw source text was silently corrected or overwritten.

## Evaluation and limits

Ten targeted unit cases include general terminology variants, specific subtypes, comparisons, context preservation, the structural meaning of “simple” and preventing introductory notes from answering subtype questions. Five cases reproduced the previous relevance failure before the fix. The complete suite subsequently passed **409 tests** with one existing FastAPI/Starlette test-client deprecation warning.

Twelve real-library cases passed using the new release, and all 12 passed through the activated API. The broader 115-case live regression benchmark also passed: **127/127 live checks** in total. Results are recorded under `artifacts/evaluation/epithelium-v1`; their final counts and release hashes are in `delivery-manifest.json`.

These are software, topic-fit and source-handling checks, not a measured medical-accuracy percentage. They do not validate the whole medical library. The five additional holds demonstrate why citations alone are insufficient and why qualified faculty review is still necessary. Some detailed subtype questions will now abstain until an adequate reviewed explanation is available.

The previous configuration is backed up privately for rollback. Local services were restarted to activate the correction. Start a new conversation to test the new answer; historical responses already displayed in an old tab are not rewritten.
