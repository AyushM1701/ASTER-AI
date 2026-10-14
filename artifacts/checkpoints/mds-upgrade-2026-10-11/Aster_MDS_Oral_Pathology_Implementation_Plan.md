# Aster — MDS Oral & Maxillofacial Pathology and Oral Microbiology
## Response audit and end-to-end implementation blueprint

**Prepared:** 11 October 2026  
**Basis:** Eleven user-supplied Aster responses in `Pasted text.txt`, the accompanying October 10 Aster audit, and external specialty references.  
**Scope:** Strengthening student-facing MDS coverage without removing the previously selected patient and research-paper workflows.  
**Status:** Implementation plan, not a code audit or a claim that repairs have been executed.

## Executive decision

Aster needs a **syllabus-aware, task-aware, evidence-supported answer generation pipeline**, not just more downloaded PDFs or another general chatbot model. Its present pipeline accepts lexically adjacent but irrelevant source passages, splits multipart questions into malformed context-free fragments, relies on long source-text copying, and treats absent prepared activities as inability to answer. It must instead be able to plan what an MDS answer requires, retrieve evidence for **every named facet**, synthesize a coherent response, verify both citations and task completion, and abstain clearly on genuinely unsupported facts.

**Non-negotiable:** “Answer any MDS major question” is a coverage aspiration, not a promise of universal accuracy. Public clinical-performance claims require appropriate independent review. Student education is not authorization to make definitive clinical diagnoses for real patients.

## 1. Observed baseline: 11 questions

| Test | Expected task | Observed result | Engineering implication |
|---|---|---|---|
| Oral epithelium, layers and functions | Define, enumerate histological layers, explain functions | Relevant histology, then unrelated pentose phosphate pathway and epidemiology | Subquestion loses subject; relevance filter absent |
| Keratinized vs non-keratinized epithelium | Compare with anatomical examples | Abstention | Comparison contract/content coverage missing |
| Oral, sulcular, junctional epithelium | Structured 3-way comparison | Psychiatric anatomy passages and one JE paragraph | Unsafe cross-topic retrieval; per-facet checks missing |
| Apoptosis and molecular/histological features | Definition, intrinsic/extrinsic pathways, microscopic features | Capability refusal | Overly narrow activity registry and content gaps |
| Apoptosis versus necrosis | Causes, cells, membrane, nucleus, inflammation, outcome | Periodontal pyroptosis/inflammation excerpts | Answer-shape validation absent |
| Tooth development and epithelial–mesenchymal interactions | Sequence and reciprocal induction | Partially related material, repeated paragraph, missing named facet | No deduplication or required-facet check |
| Oral leukoplakia | Definition, clinical, histology, dysplasia relation | Research snippets about cancer risk and biomarkers, missing core sections | Review outranks foundational reference and topic facets |
| OKC versus dentigerous cyst | Two entities × clinical, radiographic, histological axes | Abstention | Comparison assembly not implemented |
| Oral epithelial dysplasia | Architectural, cytological features, grading limits | Relevant grading material, missing systematic criteria | Partial topical retrieval but incomplete extraction and synthesis |
| Fictional white-patch differential | Differential, histology, investigations | Refusal | Student case workflow missing |
| Oral epithelial dysplasia viva | Ask, wait, rubric, follow-up | Practice unavailable | Stateful viva workflow missing |

**Observed completion:** 0/11 fully answered in this selected set under a strict task-coverage rubric. This is **not** a representative estimate of medical correctness. No independent medical evaluator scored the sample.

### Biomedical-content cautions found in the responses

- In the oral epithelium answer, an assertion that all oral lamina propria is mesodermal is too sweeping for oral and craniofacial embryology; trace the source and have a subject expert check the specific claim, particularly the contribution of cranial neural crest-derived ectomesenchyme.
- "Oral mucosa is divided incorrectly" and casual textbook commentary are unsuitable to elevate into factual authority without context.
- A paragraph on pyroptosis is not a substitute for a requested apoptosis–necrosis comparison.
- Material about brain structures in bipolar disorder/schizophrenia is irrelevant to the anatomy of oral/sulcular/junctional epithelium.
- A review written in 2021 should not implicitly be treated as establishing the latest classification in 2026. Version and date must appear on claims involving classifications.
- The oral dysplasia response discusses grading limitations plausibly but fails to list key architectural and cytological features.

## 2. Product architecture and responsibility separation

Preserve the current Python/FastAPI, Ollama, HTML/CSS/JS frontend, temporary sessions, source identity, safe rendering and local-first design. Do **not** replace everything with React, microservices, a multi-agent runtime or model fine-tuning.

Suggested request pipeline:

```
request + mode (patient / MDS student / research)
    -> safety + intent separation
    -> syllabus/topic entity resolver
    -> hierarchical QuestionPlan (task, entities, facets, marks)
    -> evidence retrieval per entity/facet
    -> topic/source applicability and ranking
    -> EvidencePlan (supported/missing/contradictory per facet)
    -> response-type composer (essay/compare/case/viva/etc.)
    -> claim-level evidence grounding
    -> final task/medical/safety/relevance validator
    -> complete | partial | insufficient | blocked
    -> answer + evidence panel + coverage status
```

Key rules: preserve the full original question; every facet inherits the relevant entity and scope; citations must directly support specific claims; if one facet fails, do not replace the whole answer with unrelated source passages; fallbacks run the **same** validations; never let a benign educational case invoke an unrelated real-patient diagnosis refusal.

## 3. Curriculum knowledge map

### Official scope

Build against the DCI 2017 MDS Oral & Maxillofacial Pathology and Oral Microbiology regulations, **after checking current amendments and the target university syllabus**. They include applied anatomy, cell biology, histology, general pathology, microbiology, immunology, dental development, histopathology, oral lesions, benign and malignant neoplasms, molecular diagnosis, laboratory methods, forensic odontology, case discussion and research methods. The regulations specify long-answer theory tasks and histopathological slide discussions.

A practical subject map:

1. Oral and dental histology; epithelial variants, salivary glands, tooth development, odontogenesis, eruption.
2. Cell and general pathology; apoptosis, necrosis, inflammation, repair, neoplasia, immunity, genetics.
3. Developmental abnormalities of teeth/jaws/craniofacial tissues.
4. Oral mucosal disorders: white/red lesions, autoimmune and vesiculobullous lesions, infections, OPMDs.
5. Oral cancer: OSCC, verrucous carcinoma, dysplasia, risk, biomarkers, invasion and grading.
6. Odontogenic cysts and tumours: OKC, dentigerous/radicular cysts, ameloblastoma and others.
7. Salivary-gland disorders and tumours.
8. Bone/fibro-osseous, giant cell, vascular, melanocytic and hematolymphoid lesions.
9. Dental caries, pulp/periapical disease, periodontal disease, oral microbiome and biofilms.
10. Oral systemic disease and orofacial pain relevant to pathology.
11. Histotechnology, stains, immunohistochemistry, immunofluorescence, molecular tests, cytology and lab diagnosis.
12. Forensic odontology; scientific methods, evidence, statistics, paper review and seminar/viva skills.

Avoid treating this list as an already completed capability inventory. Every topic needs a versioned record.

### Capability registry schema

A topic is ready only for declared tasks with adequate evidence:

```yaml
id: MDS-OP-OPMD-LEUKOPLAKIA
canonical_name: oral leukoplakia
synonyms: [oral leukoplakia, OL]
audience: mds_student
curriculum: {authority: DCI, base_year: 2017, local_overlay: pending}
facets:
  - definition
  - epidemiology_and_risk
  - clinical_features
  - differential_diagnosis
  - histopathology
  - epithelial_dysplasia_relationship
  - investigations
  - clinical_significance
supported_tasks: [short_note, essay, compare, viva, fictional_case]
source_set_version: pending
source_review: pending
qualified_clinical_review: pending
limitations: []
```

Index by entities and relationships: *oral mucosa -> oral epithelium -> keratinization*; *oral leukoplakia -> OPMD -> OED*; *OKC -> odontogenic cyst -> comparative features*. Do not build a large generative knowledge graph until simple curated IDs and links have shown measurable value.

## 4. Better, legally usable medical sources

Use an explicit hierarchy; do not mix basic definitions with speculative narrative papers indiscriminately:

- **Classification/standards:** WHO/IARC *Head and Neck Tumours*, fifth edition (2024 catalogue entry). Access only under its permitted terms; do not bundle the paid classification without redistribution rights. Use current primary guidance for date-sensitive pathology and clinical claims.
- **Foundational teaching:** Licensed or user-authorized oral histology/pathology and general pathology textbooks; curated lecture materials; institution-approved teaching packs. Track edition, chapter, page and license.
- **Clinical/guideline evidence:** Professional society guidance and high-quality relevant consensus, clearly separated from basic histology.
- **Recent research:** Systematic reviews, quality-assessed primary studies and specific methodological papers, explicitly labelled as research, not automatic clinical consensus.
- **NLM/PMC:** Only retrieve and redistribute materials where article-level rights and access terms allow. All of PMC is **not** public-domain or freely redistributable.

Prioritize **missing concepts and facets**, not raw record counts. A thousand paragraphs on apoptosis are useless if no source covers the comparison with necrosis and its histological features in a task-ready form.

### Source ingestion pipeline

```
document discovery -> license/permission check -> format/text/table extraction
-> OCR only if needed -> structural parsing (title/section/subheading/table)
-> medical topic/entity mapping -> hierarchical chunks with document coordinates
-> source authority/date/version labels -> quality checks -> lexical + vector indexes
-> spot validation of 20-50 randomly selected chunks per source family
```

Store: source_id, version, license, publisher, year, page/section, canonical entity, facet, evidence type, population/context, review status, source checksum and extracted passage. Detect extraction corruption, tables without headers, truncated sections, references incorrectly ingested as prose, duplicated paragraphs, quoted hypothesis text and mismatched headings. Review held sources before advertising coverage.

Keep a complete manifest; changes in a source should invalidate dependent concept cards, reference answers and evaluation snapshots as appropriate.

## 5. Question understanding — highest-payoff change

### Typed hierarchical request

Example question: `Define oral leukoplakia. Discuss its clinical presentation, histopathology, and relationship to oral epithelial dysplasia.`

```json
{
  "audience": "mds_student",
  "canonical_topics": ["oral_leukoplakia", "oral_epithelial_dysplasia"],
  "primary_topic": "oral_leukoplakia",
  "task": "essay",
  "requested_facets": [
    {"topic": "oral_leukoplakia", "facet": "definition"},
    {"topic": "oral_leukoplakia", "facet": "clinical_features"},
    {"topic": "oral_leukoplakia", "facet": "histopathology"},
    {"topic": "oral_leukoplakia", "facet": "relationship_to_dysplasia"}
  ],
  "is_fictional_case": false,
  "original_question": "..."
}
```

Critical invariant: no fragment like `Explain the structure, function` or `What is functions` may be sent for retrieval unless it carries its explicit original entity. Tests must inspect intermediate plans, not only final prose.

### Question types

- Definition / classify / enumerate.
- Mechanism / pathogenesis / stages.
- Histological features / diagnostic criteria.
- Comparison (two or more entities along identical requested axes).
- Short note (marks-aware compact answer).
- Long answer (10-, 25-, or 50-mark, user-selected or infer cautiously from explicit request).
- Fictional clinical reasoning (differential, why, investigation, uncertainty).
- Research critical appraisal.
- Viva (ask **one** question, wait, evaluate with rubric, follow-up).
- Histopathology slide discussion (first build text-based slide descriptions; image analysis remains a distinct validated capability).

Do not make the patient's mode inherit student-case behavior. Keep real patient diagnosis restrictions.

## 6. Hybrid retrieval with medical applicability checks

**Start with** existing retrieval facilities, then evaluate improvements in an isolated benchmark; do not introduce a new dependency simply because it is fashionable.

Recommended candidate pipeline:

1. Entity and facet resolution with synonyms/medical dictionary.
2. Exact/canonical-topic match and section-field filtering.
3. BM25/SQLite FTS5 keyword retrieval for nomenclature and exact morphology terms.
4. Dense semantic retrieval for paraphrases.
5. Merge using reciprocal rank fusion or another tested fusion policy.
6. Optional small local reranker, evaluated for speed and memory.
7. Applicability filter for *topic*, *facet*, *evidence role*, *audience*, *population*, and *source tier*.
8. Diversity/deduplication so multiple paraphrases from one article do not crowd out foundational sources.
9. Return evidence grouped per required facet, not just one bag of top-k chunks.

Example hard negatives: an oral epithelium `function` facet should reject generic cellular function in schizophrenia, metabolic pathways, or unrelated epidemiology; an apoptosis vs necrosis comparison should not default to a periodontal pyroptosis review. A tooth-development answer must not duplicate the same paragraph twice.

When comparing A and B, retrieve A and B independently and then validate **parallel fields**; never rely on a single passage mentioning both terms.

## 7. Compose exam-ready answers instead of dumping passages

Create response contracts specific to requested tasks.

### Define/classify

Definition -> classification -> distinctive features -> examples -> clinical/pathological relevance where requested.

### Long MDS essay (25/50 marks)

1. Precise definition and terminology/classification edition.
2. Relevant epidemiology and etiopathogenesis.
3. Molecular/pathophysiological mechanism.
4. Clinical and gross findings.
5. Histopathological architecture and cytology.
6. Differential diagnosis and discriminating features.
7. Relevant investigations, special stains/IHC/molecular tests where applicable.
8. Prognosis or clinical significance (educational, evidence-qualified).
9. Controversies/new research and limitations, only if relevant.
10. Brief conclusion and verifiable sources.

The exact subsections **depend on the question**; do not pad irrelevant sections. A general cell-biology question does not automatically need radiology or a clinical treatment chapter.

### Comparison

Generate a real table with entity columns and requested comparison axes. Require supporting evidence for both cells. E.g., OKC vs dentigerous cyst must cover location/association, clinical behavior, radiographic pattern, epithelial lining, connective tissue and diagnostic nuances; avoid claiming radiology alone proves either lesion.

### Mechanism

Initial trigger -> molecular players -> sequential events -> morphological changes -> clinical/pathology implications. Answer should identify intrinsic/extrinsic apoptosis pathways and morphological hallmarks when requested.

### Fictional cases

Relevant findings -> differential diagnoses -> evidence for/against each -> investigation/biopsy rationale -> distinctive expected histology -> explicit uncertainty; **not** a definitive patient diagnosis.

### Viva

Stateful activity (topic, difficulty, selected question ID, expected points, rubric, current stage, prior answer). Ask one question, stop. On response, grade against a clearly labelled **provisional educational rubric**, disclose omitted concepts, and ask a follow-up. AI grading is not independently validated faculty grading.

### Synthesis

Allow controlled paraphrase and cross-source synthesis but require traceable claim-to-evidence mappings. The current whole-section exact-match validator can be retained as a strict fallback/baseline, not as the only way to produce a readable answer. Use claim-supported synthesis in shadow evaluation before enabling more widely.

If one requested facet cannot be supported, provide the supported parts and explicitly identify the missing facet. Do not put 'ok' on a generic passage that evades requested sections.

## 8. Shared output verification and safety (F19/F20/F21)

Every final output — prepared, generated, extractive, fallback, 502/503 and research — must run through the same relevant checks:

- **Relevance:** is the passage answering the precise question, entity and facet?
- **Completeness:** did the answer satisfy each requested facet?
- **Shape:** is it actually a table/essay/viva question/clinical reasoning answer?
- **Support:** do claims map to suitable evidence (not just citation IDs)?
- **Applicability:** is evidence current, population-appropriate and not a speculative claim presented as consensus?
- **Safety:** does it avoid making unauthorized patient-specific diagnosis/treatment assertions or exposing unsolicited dosing?
- **Redundancy:** remove duplicates, uncontrolled dumps and irrelevant prefaces.
- **Status:** report complete/partial/insufficient/blocked truthfully.

Prefer deterministic validators for format, missing facets, citation identity, claims of unsupported doses and source/version consistency. An optional local LLM verifier can flag semantic issues but its approval is not medical certification. Re-run retrieval a bounded number of times when relevance fails; do not allow infinite retries or less safe extractive fallbacks.

## 9. Model strategy for a laptop with RTX 4050 6GB VRAM

**Do not change Ollama first.** Compare the existing model/prompt pipeline under identical content and test questions after fixing retrieval and output contracts.

- Start with an instruction-following 3B–4B class quantized model if the local machine can accommodate it; the actual model must be chosen from reproducible measured tests, not a promise of performance.
- Constrain prompts to only the needed passages and facets. Reduce raw copied context; preserve citation coordinates.
- Use a small CPU-resident lexical index and a reasonably lightweight embedding model; benchmark GPU and RAM allocation.
- Consider a local reranker only if retrieval evaluations justify its cost. Benchmark sequential residency to avoid concurrent VRAM pressure.
- Measure cold/warm latency, peak VRAM, RAM, first token, answer completion and answer-quality metrics on the same questions.
- Keep generation and verification passes bounded. For difficult 50-mark essays, prefer structured sectional generation with source-constrained facets and a final consolidation pass, rather than a one-shot 8,000-word hallucination-prone stream.
- Fine-tune/QLoRA **only after** identifying residual errors that cannot be corrected through source quality, retrieval, structured planning, or prompts. Do not train on held-out answers or copyrighted text without the necessary rights.

If hardware prevents a strong result, report the trade-off instead of asserting this can answer everything on 6GB.

## 10. Evaluation protocol and acceptance gates

### Tests derived from the 11 supplied failures

- Exact oral epithelium question: no NADPH/pentose phosphate/epidemiology spillover; sections on epithelium, layers, functions.
- Keratinization question: tabular or parallel contrast with anatomical examples, unless evidence genuinely missing.
- Three gingival epithelia: correct three-way table; reject psychiatric sources.
- Apoptosis: pathways, caspases and histological morphology; no capability-only refusal where source pack supports it.
- Apoptosis vs necrosis: side-by-side cellular and inflammatory distinctions; pyroptosis can be briefly contextualized only if relevant.
- Tooth development: ordered stages and reciprocal epithelial–mesenchymal signaling; no repeated excerpts.
- Leukoplakia: definition, clinical features, histology and dysplasia relationship; no substitution of recent-biomarker review for fundamentals.
- OKC vs dentigerous cyst: symmetric clinical/radiographic/histologic comparison.
- OED: actual architectural and cytological feature lists **plus** prognostic grading limitations.
- Fictional persistent tongue lesion: differential and investigation reasoning, no definitive diagnosis.
- Viva: actual one-at-a-time question, await answer, rubric and follow-up.

### Additional benchmarks

Create a **versioned, prospectively locked** bank rather than retesting only the 11 known samples:

- Baseline: original 11 regression tasks plus paraphrases/hard-negative source traps.
- Pilot: **150 unseen** in-scope prompts balanced across 10 representative topic families and 5+ operations (must disclose distribution and difficulty).
- Expansion: **300–500 unseen** questions sampled across the declared major syllabus segments, with long essays, viva, morphology comparisons, fictional cases and research questions. These are engineering sample-size targets, not formal evidence of universality.
- Safety/out-of-scope: separate educational-vs-personal scenarios, document isolation, drug-dose exposure, prompt-injected source material and model failures.
- Later specialist review: qualified reviewers grade a locked subset of representative answers independently. Keep F03 pending until this occurs; do not invent review scores.

Track source retrieval relevance, facet coverage, in-scope task completion, appropriate abstention, citation integrity, false claim flags, cross-domain contaminations, multi-turn success, latency and peak memory. Predeclare scoring rubrics and report **separate** rates and denominators.

**Proposed, unachieved pilot targets:** 100% of citations resolve; 0 observed cross-domain contamination on the locked hard-negative set; >=90% complete answers for predeclared in-scope core tasks; no known severe safety policy regressions; major observed errors addressed and retested. A small zero-error sample does not establish zero real-world risk. No medical correctness threshold may be claimed satisfied without independent qualified assessment.

## 11. Code-level work packages aligned with current modules

Inspect exact repo symbols before editing. Use these **candidate** placements if the file structure remains as described in the audit:

| Candidate module | Work |
|---|---|
| `backend/app/api/chat.py` | Carry audience, task and session/follow-up state; serialize honest partial status |
| `backend/app/services/teaching_query.py` | Replace orphan string fragments with hierarchical QuestionPlan and canonical topic/facet resolution |
| `backend/app/services/teaching.py` | Match supported facets and task types; compose teaching answers and comparisons |
| `backend/app/services/answers.py` | Centralise final output validation; eliminate unsafe source dump and route domination |
| `backend/app/services/explanation_layers.py` | Controlled simple/deep explanation and evidence-bound synthesis |
| `backend/app/services/policy.py` | Student fictional case vs real patient boundary, dose/applicability rules |
| New `services/mds_curriculum.py` | Versioned DCI/university topic map and synonyms |
| New `services/question_plan.py` | Pydantic typed hierarchical task decomposition |
| New `services/evidence_plan.py` | Group evidence and missing facets per task/subject |
| New `services/retrieval_ranking.py` (or existing retrieval module) | Hybrid ranking and topical hard-negative filters |
| New `services/answer_composer.py` | Task-specific answer shape templates and section consolidation |
| New `services/final_validation.py` | Unified relevance, facet, citation and safety gates |
| New `services/viva.py` | Stateful viva and provisional rubric workflow |
| `frontend/web/app.js` + `index.html` | Essay/compare/viva responses, missing facets and right-panel source navigation |
| `tests/` | Module tests, full bridge tests, corrupted corpus tests, replay of the exact 11 questions |

A new file is justified only when it creates a clear abstraction. Avoid duplicate policy engines, diverging validators, schema drift or disrupting temporary session isolation.

### Data contract sample

```python
from typing import Literal
from pydantic import BaseModel, Field

TaskType = Literal["definition", "mechanism", "comparison", "essay", "fictional_case", "viva", "research"]
Status = Literal["complete", "partial", "insufficient_evidence", "blocked"]

class RequestedFacet(BaseModel):
    topic_id: str
    facet: str
    requested_by_user: bool = True

class QuestionPlan(BaseModel):
    original_question: str
    audience: Literal["patient", "mds_student", "research"]
    task: TaskType
    primary_topic_id: str | None = None
    facets: list[RequestedFacet] = Field(default_factory=list)
    marks: int | None = None
    is_fictional_case: bool = False

class AnswerResult(BaseModel):
    status: Status
    answer: str
    covered_facets: list[RequestedFacet]
    missing_facets: list[RequestedFacet]
    citation_ids: list[str]
    clinical_review_status: str
```

This is an **interface sketch**, not verified copy-paste code for the current repository. Adapt it to existing schemas and backwards compatibility.

## 12. Sequence and practical stopping rules

| Stage | Work | Exit evidence |
|---|---|---|
| 0 — Baseline | Inspect actual repo, record 11 failures, current tests/lint/latency/memory, make safe checkpoint | Reproducible failure fixtures; no secrets or private source committed |
| 1 — F19/F20/F21 | Shared final-output validator and reject irrelevant source dump | Oral mucosa question cannot retrieve psychiatric or biochemistry answer as success |
| 2 — Planning | Topic/facet contracts, comparison/case/essay planners | All 11 questions parse into correct entities, task and non-orphan facets |
| 3 — Evidence | Source inventory, rights, authoritative initial packs, source-level metadata, retrieval scoring | Pertinent evidence for each facet in first topic pack, measured recall/precision |
| 4 — Synthesis | Structured long-form explanations, parallel comparisons, morphology features, partial answers | Tasks actually have requested output shape; citations are claim-aligned |
| 5 — Viva/case | Educational fictional case and viva state machines | One question, wait, rubric, follow-up; safe diagnosis boundary |
| 6 — Evaluation | Locked 150-question test, hard negatives, correctness review workflow, regression automation | Transparent scorecards, measured improvements, F03 remains pending until qualified review |
| 7 — Scale | Expand packs to cysts, tumors, OPMDs, infections, salivary lesions, diagnostics, oral micro | Only advertise topics whose coverage gates pass |
| 8 — Distribution | CPU/GPU benchmark, on-demand packs, copyright preflight, clean Windows tests | Honest local-first release readiness, no premature public clinical claims |

Do not wait for a 100,000-page corpus to fix the obvious issue: *the question about oral epithelial function cannot be allowed to return NADPH and epidemiology passages*.

A one-developer engineering **prototype** may take multiple weeks; filling high-quality syllabus coverage and obtaining external specialist review can take significantly longer. Re-estimate after examining the real codebase, existing licensed materials and reviewer access.

## 13. What not to do

1. Do not hardcode the eleven answers or falsely increase benchmarks by memorizing the prompts.
2. Do not treat a cited paragraph as inherently relevant or medically correct.
3. Do not make a textbook narrative review the main source of every foundational definition.
4. Do not remove safety validation simply because strict extraction yields incomplete answers.
5. Do not train or reindex full copyrighted textbooks for redistribution without appropriate rights.
6. Do not route a fictional MDS case into a personal diagnosis refusal; do not leak that privilege into patient mode.
7. Do not label an AI judge as an independent faculty reviewer.
8. Do not claim a 6GB GPU can satisfy unbounded context/accuracy without measuring it.
9. Do not mix benchmark answers into ordinary RAG content.
10. Do not call this comprehensive medical correctness until independent qualified review exists.

## 14. Sources and reference provenance

Use these as scoping/reference **starting points**, not as authorization to bulk-copy their contents:

- DCI, *MDS Course Regulations, 2017*, especially specialty section, printed pp. 110–117: https://dciindia.gov.in/Rule_Regulation/MDS_Course_Regulations_2017.pdf
- WHO / IARC, *Classification of Head and Neck Tumours*, fifth edition, volume 9, 2024 catalogue: https://publications.iarc.who.int/Book-And-ReportSeries/Who-Classification-Of-Tumours
- NCBI Bookshelf, *Histology, Oral Mucosa*: https://www.ncbi.nlm.nih.gov/books/NBK572115/
- *Oral Mucosal Epithelial Cells* (2019): https://pmc.ncbi.nlm.nih.gov/articles/PMC6383680/
- *Demystifying oral epithelial dysplasia: a histological guide* (2024): https://www.pathologyjournal.rcpa.edu.au/article/S0031-3025%2823%2900287-8/fulltext
- *Clinical Management Update of Oral Leukoplakia* (2025 issue): https://onlinelibrary.wiley.com/doi/10.1002/hed.28013
- *Update from the 5th Edition WHO Classification: Tumours of the Oral Cavity and Mobile Tongue*: https://pmc.ncbi.nlm.nih.gov/articles/PMC9018914/
- NLM, PMC Open Access licensing FAQ: https://support.nlm.nih.gov/knowledgebase/article/KA-03253/en-us

**Bottom line:** Fix routing and relevance first, complete the question/facet/evidence contract second, prepare licensed authoritative source packs third, and scale with independent, reproducible evaluations. Better generation alone will not fix Aster's existing failures.
