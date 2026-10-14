# Developer MBBS teaching benchmark after review fixes

The unchanged 93-question dataset contains 81 supported educational variants and 12 unsupported, product, personal and emergency boundary cases across 16 subject labels. This run uses the frozen r3 release, final hybrid index and the same 24 developer-reviewed explanation units. It evaluates bounded reference agreement; clinical correctness and faculty competency verification remain unmeasured.

| Measure | Lexical | Hybrid | Denominator |
|---|---:|---:|---|
| Expected response status | 90/93 | 92/93 | All cases |
| Expected-source retrieval hit | 75/81 (92.6%) | 77/81 (95.1%) | Supported cases |
| Strict required-reference facts matched | 132/162 (81.5%) | 144/162 (88.9%) | Required facts |
| Complete bounded reference agreement | 61/81 (75.3%) | 69/81 (85.2%) | Supported cases |
| Boundary non-handling | 12/12 | 12/12 | Boundary cases |

Hybrid answered 80/81 supported cases; lexical answered 78/81. All 183 hybrid claims and all 169 lexical claims were exact source text or an exact validated developer unit. Every emitted answer had valid citation bindings. An unanswered supported case contributes a failure to status, completeness and supported-case citation integrity rather than being silently excluded. No listed forbidden contradiction was detected; the finite list is not an exhaustive correctness or safety test.

Compared with the prior final-verified run, bounded agreement improved from 56/81 to 69/81 in hybrid and 47/81 to 61/81 in lexical, with no case losing a previously passing agreement result. Strict fact matches increased from 120 to 144 in hybrid and 105 to 132 in lexical. Hybrid source retrieval was unchanged; lexical source retrieval rose from 73/81 to 75/81. The dataset, reference evidence, required facts and explanation artifact were unchanged.

The reviewed-note guard now requires the remaining query vocabulary to appear in the paired note, rather than accepting a matching topic phrase alone. More answers consequently use relevant original paragraphs. Filtration, contraction, fertilization, genetic-consent and some bipolar heredity questions improved. The guard is a vocabulary constraint, not a semantic or clinical proof, and can reject valid paraphrases. Clear conversational style was not scored by this benchmark.

Question-fit gaps remain. The bipolar mechanism and misleading-premise variants now pass in hybrid, but the direct family-history question still misses the qualification that a family history does not guarantee illness. All three research-consent variants still fail the research-specific fact requirements; genetic-testing consent material can rank ahead of the relevant research paragraph. Metabolism variants, some surveillance questions and selected distribution/epidemiology explanations remain incomplete under the required facts. Lexical lung-compliance variants remain gaps. Source-grounded statements can therefore still fail to answer the requested concept completely.

Strict phrase matching is conservative and does not assess semantic equivalence. MCQ variants test reference facts and listed contradictions; option-letter selection, complete examination answers and clinical reasoning are not measured. Fictional cases test conceptual teaching, not diagnostic competence. Boundary non-handling verifies TeachingStore only, not the full application route.

Three additional targeted regression tests passed outside the 93-case dataset: two fictional-prefix cases containing a later real emergency, and one reviewed-note requested-meaning/polysemy test. These regression tests are separate from the benchmark denominators. The curriculum/evaluator focused suite also passed 19 tests and Ruff passed. No Ollama calls were made.

The unchanged material mapping keeps all 2,626 active competencies in a review queue. Its 2,275 automatic material nominations are not covered or verified competencies. A developer inspected 25 partial associations across 24 distinct competency codes. Faculty decision fields remain null. The separate queue contains all 2,626 competencies, nine developer source holds and 24 explanation units; no faculty review has occurred.

Reproducibility: both reports pin dataset SHA-256, release manifest, explanation artifact, hybrid index manifest and evaluator/teaching/policy/retrieval/embedding source files. Both report runtime_files_unchanged_during_evaluation=true.

Artifacts:

- `teaching-lexical-r3-reviewedfix-2026-10-09.json`
- `teaching-hybrid-r3-reviewedfix-2026-10-09.json`
- `curriculum-material-mapping.json`
- `teaching-faculty-review-queue-r3-final-2026-10-09.json`
- `data/evaluation/mbbs_v1.jsonl`
