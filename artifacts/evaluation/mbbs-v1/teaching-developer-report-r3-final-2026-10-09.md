# Developer MBBS teaching benchmark

93 developer-authored questions: 81 supported educational variants over 27 source passages and all 16 subject labels, plus 12 unsupported/product/personal/emergency boundaries. The frozen r3 release, hybrid index and 24 hash-bound developer explanation units were used. Clinical correctness and faculty verification remain unmeasured.

| Measure | Lexical | Hybrid | Denominator |
|---|---:|---:|---|
| Expected response status | 94.6% | 98.9% | 93 cases |
| Expected-source retrieval hit | 90.1% | 95.1% | 81 supported cases |
| Strict reference-phrase fact completeness | 64.8% | 74.1% | 162 required facts |
| Complete bounded reference agreement | 58.0% | 69.1% | 81 supported cases |

All 12 boundary cases were left unhandled by teaching retrieval in both modes. This verifies TeachingStore non-handling; it does not verify the complete application emergency or product route. Hybrid emitted answers for 80/81 supported cases; lexical for 76/81. Every emitted answer had valid citation bindings and every emitted claim was exact source text or an exact validated developer unit. Unanswered cases are included as failures in supported-case completeness and citation-integrity denominators, rather than disappearing from those scores.

The final style/selection refinement left source retrieval unchanged but reduced strict bounded agreement from 58/81 to 56/81 in hybrid and 49/81 to 47/81 in lexical. Required facts and dataset evidence were unchanged. Concise explanations expose fewer source phrases, which can reduce these conservative scores.

The scorer checks explicit reference phrases, not semantic equivalence. For example, the final filtration unit correctly uses “water and small dissolved substances” rather than the benchmark phrase “water and solutes”; the fertilization unit says “an egg and a sperm” rather than “egg and sperm”. Such paraphrases can produce false missing-fact flags. Other gaps are substantive: the bipolar genetic-risk questions can return a general mood-episode explanation without addressing the required heredity qualification. Research-consent questions can return genetic-testing consent text instead of the research-specific facts. No clinical correctness conclusion is drawn from either kind of result.

MCQ variants test referenced facts and listed contradictions. Option-letter selection, examination scoring, complete answers to all question clauses, diagnostic reasoning and faculty clinical assessment are not measured. Fictional cases are conceptual reference tests. No listed forbidden contradiction was detected; that finite list is not an exhaustive safety or medical accuracy test.

The curriculum mapping contains all 2,626 active competency texts and source-page provenance. Independent sparse lexical ranking nominated material for 2,275 competencies; these are candidates awaiting review, not covered competencies. A developer inspected 25 partial associations across 24 distinct competencies, recording the actual evidence paragraph and a narrow contribution scope. Each competency has an explicit faculty decision form with null reviewer, decision, missing elements, currency and Indian-context fields. The separate faculty queue also contains the 9 developer source holds and all 24 explanation units. Faculty review has not occurred.

Focused verification: 19 tests passed (10 evaluator/mapping tests and 9 curriculum extraction tests); Ruff passed. No Ollama calls were made. Runtime/corpus/source files were not edited by this task.

Artifacts:

- `teaching-lexical-r3-final-verified-2026-10-09.json`
- `teaching-hybrid-r3-final-verified-2026-10-09.json`
- `curriculum-material-mapping.json`
- `teaching-faculty-review-queue-r3-final-2026-10-09.json`
- `data/evaluation/mbbs_v1.jsonl`
