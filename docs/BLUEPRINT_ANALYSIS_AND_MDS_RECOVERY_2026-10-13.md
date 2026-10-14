# Blueprint analysis and MDS coverage recovery

Date: 13 October 2026. This report evaluates `C:/Users/AYUSH/Downloads/ASTER_From_Scratch_Research_Architecture_Blueprint.md` against the existing workspace. The document is a design proposal, not an instruction to replace Aster. No application code, source release, index, model or private configuration changed during this analysis.

## Recommendation

Adapt the blueprint's evidence measurement, curriculum mapping and labelled failure analysis to the existing pipeline. Fix question planning and obtain complete source support for common topic/facet families before attempting a learned reliability controller or generator fine-tuning. Aster already has the backbone described in the proposal; rebuilding it would discard functioning infrastructure without resolving the present evidence gaps.

The target is useful, supported educational answers across nine specialties. A new reliability model can assess evidence more effectively, but cannot supply an absent foundation chapter, turn a study-specific observation into a general treatment principle, or establish independent medical correctness.

## What the blueprint contributes

| Proposal | Current Aster | Recommended adaptation |
| --- | --- | --- |
| Separate similarity, evidence support and task completeness | Existing facet planning, evidence checks and common terminal validator | Measure each stage independently and log concrete rejection causes |
| Topic/task capability declarations | National curriculum, editorial topic map and canonical runtime IDs; declaration does not establish source readiness | Release-bound capability matrix including depth, qualifiers, support IDs and review status |
| Facet-aware retrieval | Per-facet queries, topic aliases, lexical/dense retrieval and explicit inspected bindings | Fix entities first; benchmark hybrid fusion and a fixed reranker on annotated passage relevance |
| Evidence graph | Existing facet evidence and claim/citation bindings | Extend existing typed contracts with granular applicability/rejection diagnostics rather than introduce a second incompatible pipeline |
| Complete/partial/insufficient decisions | Already implemented | Measure inappropriate withholding as well as false-complete answers |
| FGRC relevance/relation/answerability heads | No trained FGRC | Experimental extension after labelled data and strong rule/reranker baselines exist |
| Constrained synthesis and one repair | Current frozen supplied pilot uses extractive answers; prepared explanations have exact identity checks | Add only through the shared guard, with independent claim-level support checks; arbitrary model prose cannot inherit prepared-unit approval |
| Independent grouped benchmarks | Preserved supplied bank, variations and frozen source/code hashes; unseen status explicitly false | Retain as development tests and create independently authored topic/source-grouped evaluation |
| Reviewer annotation protocol | AI/developer inspection and pending faculty review | Separate engineering checks, AI inspection and actual qualified review in all artifacts |
| Local hardware discipline | Local Windows, FastAPI, Ollama and bounded compute infrastructure | Measure cold/warm memory and latency before switching models or adding trainable components |

Keep current `/v1` APIs, service modules, exact NumPy indexes, frontend and release tooling unless an experiment demonstrates a benefit from replacing them. SQLite FTS5, FAISS, BGE and Qwen3-4B are candidate experiments in the document, not mandatory migrations. Retain the user's national-curriculum-only preference; a university overlay is optional future scope.

The blueprint excludes imaging/OCR from its primary MVP. Existing Aster already contains bounded research imaging and confirmation-based OCR. Their presence does not justify removing them; prioritize MDS coverage work without expanding their medical claims.

## What the frozen results actually establish

Source: `artifacts/evaluation/mds-supplied-2026-10-13/frozen-v3-api/summary.json`, `responses.jsonl` and `remaining-turn-gaps.json`.

| Observation | Recorded result |
| --- | --- |
| Cases / turns | 107 / 111 |
| Successful HTTP responses | 111 / 111 |
| Turns containing substantive claims | 16 / 111, approximately 14.4% |
| Complete turns containing substantive claims | 3 / 111, approximately 2.7% |
| Raw complete statuses without claims | 5; viva starts, not complete medical explanations |
| Evaluation source release | `mds-generalization-candidate-v3-2026-10-12` |
| Evaluation inference | `none`; extractive mode, network disabled |
| Prepared units in that release | 62 |
| Prepared units with explicit facet bindings | 22 |
| Turns returning exact trusted prepared claims | 6 |
| Distinct prepared IDs returned | 7 |
| Source/code changes during capture | None |
| Independent medical accuracy / unseen evaluation | Pending / false |

These percentages are content and contract-completion measures, not accuracy. Their denominators include interaction turns that need separate task-success measures. The expanded v3 candidate was already the source set used in this pilot. Activating it in the installed application would change availability there, but is not an explanation or remedy for its own low frozen-pilot score.

The historical 150-task pilot and the supplied 111-turn evaluation are different benchmarks. Preserve their results separately. Later inspected-pack improvements do not rewrite the original 0/150 baseline.

## Failure evidence found during this analysis

The capture contains 660 rejected candidate/facet entries. All carry `facet_not_supported`; 257 also carry `topic_not_in_supporting_text`, and 18 also carry `source_review_hold`. These occur in 67, 45 and 7 turns respectively. Counts overlap and are not independent causes. They do not show how many rejections are correct, because independent support labels are absent.

The gap file contains 108 entries. Its most frequent missing facets are definition (36), clinical features (36), histopathology (32), radiographic features (28), differential diagnosis (13) and investigations (12). This prioritizes foundational and diagnostic teaching evidence, rather than simply acquiring more recent molecular research articles.

Concrete planner failures:

- `oral-02`: “Differentiate between keratinized and non-keratinized oral epithelium with examples” becomes `local:keratinized`, `local:non_keratinized_oral_epithelium` and `local:examples`. The shared noun is lost on the first entity and the requested examples become a third topic. Correct planning should preserve both full epithelial entities and treat examples/sites as an answer facet.
- `oral-10`: an explicit oral submucous fibrosis question requests etiopathogenesis, histopathology and clinical significance, but the captured question plan has no canonical topics or facets.
- Fictional-case facets frequently use `local:fictional_case` (30 occurrences in gap facets). A fictional case is an operation/context; inspect whether the planner has bound the underlying findings/entities before treating this placeholder as a medical retrieval subject.

`supports_facet` currently requires coherent topicality across a whole quoted unit. Sentences must contain recognized topic vocabulary or a narrowly recognized inherited pronoun. Scope words must also match. This protects against mixed unrelated extracts, but can reject useful material written with synonyms or implicit subject continuity. Audit these as possible false negatives; do not globally disable the checks.

The oral-01 capture retrieves candidates, then rejects them. Inspection of candidates finds broad oral-mucosa teaching units and research introductions mixed with source limitations. This is not proof that all requested epithelial facets are answerable. It does show that “nothing exists” and “nothing passed the current applicability contract” are different diagnoses. Segment and inspect coherent units; retain parent context, qualifications and source hashes. Do not relabel whole mixed paragraphs as complete evidence merely because one sentence looks helpful.

Forty of the 62 prepared units lack explicit facet bindings. This is annotation debt, not automatic additional coverage: inspect each unit and bind only genuinely supported facets, topics, populations and depths. Some units may be too narrow for the tested tasks even after annotation. Existing bounded epithelial summaries do not establish complete layers, histology or comparative coverage.

## Ordered recovery work

### 1. Diagnose before expanding

Create one trace per requested facet through these stages: correct subject/task plan; eligible source exists in release; retrieved in candidate pool; passes applicable support checks; survives composition; survives final validation; visible in UI. Give each failure a primary engineering category and preserve additional reasons.

Use independently inspected evidence to distinguish missing sources, retrieval misses, planner errors, overly strict applicability checks, composition omissions and legitimate withholding. Add oracle-plan and oracle-evidence experiments: rerun the same questions with manually corrected plans, then with known supporting passages. The incremental gains reveal where to spend acquisition and implementation effort. Do not use the system's own final completeness declaration as the reference label.

Exit evidence: a categorized development failure ledger with source/code hashes, labelled examples and documented uncertainty. The current broad `facet_not_supported` reason alone cannot allocate all failures correctly.

### 2. Repair entities and make current evidence usable

Expand canonical IDs and clinically checked aliases to the actual national topic map. Handle coordinated noun inheritance, task phrases, anatomical examples, abbreviations and classification versions. Preserve distinct diseases rather than aggressively merging lexical variants. Restore explicit facets for failed named-topic questions. Test generic wording and multipart variations rather than adding exact-question answer branches.

Review the 40 units without explicit bindings. Preserve exact text/parent hashes and whole qualifications. Add bindings only after actual source comparison, recording AI versus qualified review accurately. For mixed parent records, create new coherent paragraph/section units with exact parent offsets and contextual qualifiers; keep originals immutable. Admit held material only through existing narrow permissions or a new documented source-review decision.

Exit evidence: corrected generic plans and exact provenance for any newly usable units; no new wrong-topic matches or expansion of source holds by implication.

### 3. Acquire coherent educational coverage

Build units for complete topic families rather than isolated benchmark answers. A capability cell should identify specialty, topic, task, requested depth, required facets, permitted source units, currentness and review status. Prioritize the observed missing foundational/diagnostic facets and units reusable across many prompts.

Start with epithelial structure/function and keratinization comparisons; apoptosis versus necrosis; odontogenic cyst comparisons; dysplasia versus carcinoma; then representative pulp diagnosis, periodontology, orthodontic biomechanics, restorative materials, pediatric pulp therapy, fracture patterns, oral-medicine differentials and public-health measures. These are work packages, not assertions that evidence is already complete.

A unit should retain terminology, definition, applicable mechanisms/features, qualifications, source limitations and comparison distinctions where supported. Topic packs should include source-backed rubrics for comparisons, essays, fictional-case reasoning and viva. A suitable foundation may be an open educational chapter or authorized teaching material; a research introduction cannot be assumed to supply a whole postgraduate chapter. One source may support a narrow facet; multiple citations alone do not establish independent agreement.

For each acquisition, verify rights and downstream permitted actions, source quality, revision, clinical scope and actual relevant text before adding it to a pack. Preserve all attribution and NC/SA restrictions. Prefer sources whose rights fit the intended edition; do not assume that all publicly readable textbooks or PMC articles are reusable.

Exit evidence: at least one complete supported educational journey per specialty, followed by a measured topic/task/depth expansion. Fix reusable evidence families until both existing development banks improve. No promised 100% rate or fabricated faculty status.

### 4. Improve ranking, composition and release measurement

Use inspected query/facet/passage labels to compare existing retrieval against lexical+dense fusion and a fixed cross-encoder reranker. Keep the source set, generator and candidate budget constant. Score Recall@k, facet coverage and wrong-topic intrusion; reranker relevance is not entailment or clinical correctness.

The current frozen capture uses no model inference. A larger generator cannot change that experiment until the composition route changes. First improve exact source-bound prepared composition. Then, if justified, evaluate constrained synthesis in shadow mode. It must pass the same terminal guard with separate claim-level support validation; prepared-text hashes cannot approve paraphrases or newly generated claims. Allow at most one bounded repair from the same verified evidence, then partial/withhold unsupported sections.

Stage a numbered pack with frozen source/explanation/index/code identities, run development evaluations, and review new supported and unsupported outputs. Promote only after demonstrated coverage gains and regression checks. Keep rollback and preserve baseline reports. Running the same questions with a new pack must explicitly record the new version.

Track substantive-answer rate, all-essential-facet completion, false-complete rate, inappropriate withholding, claim attribution, per-specialty/per-task results and cold/warm performance separately. Score viva interaction separately from medical explanations. Create independently authored held-out questions grouped by topic/source family; supplied questions and edited variations are development material.

### 5. Consider training after the baseline improves

The FGRC proposal is useful as a research hypothesis: train relevance, support/contradiction/insufficiency and answerability on genuinely annotated facet/passage examples, including audited hard negatives. Compare it with the same retrieval pool and a strong rule-based gate, using held-out calibration and matched answer coverage. Deterministic safety and source permissions stay outside learned acceptance scores.

Do not start with 5,400 allegedly reviewed essays. The blueprint's 90-case pilot then roughly 540-case expansion is a planning target; Aster's existing supplied cases provide development prompts, not independent annotated medical answer keys. Generator LoRA and new attention mechanisms come later, only if controlled experiments justify them and actual hardware measurements permit them.

## Limits of the proposal and current evidence

The blueprint's source counts, model choices, training settings and target metrics are proposals or external dataset descriptions. None prove all-MDS capability. MedMCQA and related benchmarks can provide auxiliary tests, but do not replace postgraduate open-answer facets, complete specialty evidence or qualified reviewer judgement. No new medical accuracy percentage is available from this analysis.

Two primary references checked during analysis:

- [PMC Open Access Subset](https://pmc.ncbi.nlm.nih.gov/tools/openftlist/): article licences vary; current automated acquisition must use the listed authorized services. Refresh the blueprint's acquisition-service references against current official guidance.
- [BAAI reranker model card](https://huggingface.co/BAAI/bge-reranker-base): query/passage cross-encoding is an available baseline. Its availability does not establish dental recall, calibrated support probability or a speed/memory fit on this laptop.

The fastest credible improvement is a measured loop: correct plan, applicable complete evidence, successful retrieval, supported composition, unchanged validation, independent evaluation. A learned gate should improve this loop after the baseline works; it should not replace the missing educational material.
