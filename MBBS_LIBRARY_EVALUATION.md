# Aster MBBS Knowledge Library — implementation and evaluation

Updated **9 October 2026, Asia/Calcutta**. The source release retains its acquisition date, 8 October 2026.

Aster now runs a separate curriculum teaching library alongside its existing medicine references. The active release contains **1,891 coherent source contexts from 135 publisher pages or selected document sections**, with hybrid search, 24 source-bound plain-language explanations and nine developer source-review holds. It is a substantial first expansion, **not a complete MBBS curriculum or a clinically validated tutor**. Qualified medical faculty review has not been performed.

The running workspace is [Aster](http://127.0.0.1:8501/). The installed text and vision model remains `qwen3-vl:2b-instruct`. A stronger model was downloaded and measured; its results did not justify changing the active model.

## What was implemented

| Requested work | Delivered | Remaining limit |
|---|---|---|
| Curriculum library | Official NMC curriculum and clarification snapshots; 2,626 active extracted competencies; subject and material review checklist | Extraction defects are recorded; a competency match does not prove coverage or skill acquisition |
| Educational sources | Licensed preclinical teaching books, original NIDDK/NIMH/MedlinePlus text, CDC epidemiology and WHO emergency-care overviews | Clinical specialties, practical skills and many advanced mechanisms remain incomplete |
| Connected retrieval | Separate teaching MiniLM index, lexical plus semantic ranking, comparison retrieval, alias support and contextual eligibility checks | Some multi-clause questions still omit required material |
| Clear explanations | 24 manually authored, developer source-compared explanations; exact source hashes, citation bindings and qualification checks | Other topics still use complete source excerpts; unrestricted generated paraphrases are not accepted |
| Stronger model comparison | Actual 13-prompt comparison for each of the installed 2B and downloaded 4B models, including output, timing, memory and manual observations | One small controlled run is not a clinical model evaluation |
| Medical tutor evaluation | 93 developer questions across 16 subject labels and seven educational forms, boundary checks, real API smoke and faculty review queue | Faculty correctness, exam performance and diagnostic reasoning remain unmeasured |

## Active assets and source lineage

- Release: [`aster-mbbs-v1-r3-final-2026-10-08`](data/references/mbbs/releases/aster-mbbs-v1-r3-final-2026-10-08/manifest.json).
- Source register: [`sources.yaml`](data/references/mbbs/releases/aster-mbbs-v1-r3-final-2026-10-08/sources.yaml); complete reference text is in the adjacent `records.jsonl`, with subject, level, edition and extraction context in `metadata.json`.
- Teaching index: [`data/indexes/mbbs-v1-r3-final/manifest.json`](data/indexes/mbbs-v1-r3-final/manifest.json). MiniLM revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`; 384-dimensional vectors. All source-unit tokens were encoded in 3,196 consecutive windows and pooled; source evidence is not silently shortened to the embedding limit.
- Plain explanations and holds: [`v1-r3-final.json`](data/references/mbbs/explanations/v1-r3-final.json). SHA-256 `1eceabe9f3dd7d03c9d14464f08762c9fa10042e26c04e6f160ad3955df495e8`.
- Active teaching profile: [`configs/teaching.env`](configs/teaching.env). Explicit `.env` or process settings can override it.

The final release manifest SHA-256 is `966003842e297e9b7697d5fd0b11b5b237eb72e19cc0cb6266e8b59b2bf4e9e0`. The semantic index is bound to reference snapshot `0e10300a6b827e7b446ec5b160cc2477ef379520da22529beec4fc624362eea5`; vector-file SHA-256 is `0a931bbfd595222a13f9181f929ed02dc67b84bb2021e08ef39b1a4764702571`.

Earlier releases and pilot indexes are retained, including the superseded intermediate r3. The active profile selects only the final release. The attempted `.env` replacement was denied by Windows permissions; it did not change the existing file. Activation uses the separate teaching profile and records its hashes and rollback action in [`activation-20261008T193935543116Z.json`](artifacts/evaluation/mbbs-v1/activation-20261008T193935543116Z.json).

### Material breadth

Counts below are subject tags on contexts, not independent topics. A context can have several tags.

| Subject tag | Contexts | Subject tag | Contexts |
|---|---:|---|---:|
| Anatomy | 148 | Histology | 27 |
| Embryology | 14 | Physiology | 248 |
| Biochemistry | 330 | Pathology | 184 |
| Microbiology | 518 | Immunology | 110 |
| Pharmacology | 270 | Medicine | 140 |
| Obstetrics and gynaecology | 40 | Paediatrics | 16 |
| Surgery | 17 | Psychiatry | 97 |
| Community medicine | 283 | Professionalism | 8 |

The existing medicine collection remains separate: 23,939 retailer products are not counted as foundational teaching. Its existing Indian reference material includes **24 sections from 12 ICMR Standard Treatment Workflows**, covering asthma, hypertension, type 2 diabetes, AKI/CKD, hypothyroidism, headache, common ENT conditions and selected paediatric conditions. Those were preserved; this release does not claim to have imported all current ICMR workflows. The [ICMR workflow catalogue](https://www.icmr.gov.in/standard-treatment-workflows-stws) was checked as the Indian clinical expansion source.

### Reuse and attribution

| Material | Source/version and permitted basis | Handling |
|---|---|---|
| Preclinical cell biology, genetics and biochemistry | Virginia Tech, 2021 first web edition; CC BY-NC-SA 4.0 | Edition and publisher license retained |
| Pulmonary and cardiovascular primers | Virginia Tech publisher editions, source-specific rights | Text-only source contexts, not figures or third-party media |
| Microbiology | Virginia Tech 2025 republication with independently retained 2016 CC BY 4.0 lineage | This is the licensed republication, not current OpenStax website ingestion |
| Human biology | TRU/Christine Miller and University of Minnesota editions; CC BY-NC 4.0 | Author and component attribution retained |
| Nursing pharmacology | BCcampus 2023, predominantly CC BY 4.0; specified component exceptions have NC-SA terms | Component restrictions kept separate |
| Epidemiology | CDC Principles of Epidemiology, third edition 2006, updated 2012; public-domain original text | Archived official HTML chapters; historical edition labelled, exercises and UI artifacts excluded |
| Psychiatry | Original NIMH publications | [NIMH permits reuse of original text](https://www.nimh.nih.gov/site-info/policies), with credit and no misleading adaptation/endorsement; images excluded |
| Kidney/diabetes education | Original NIDDK material | Publisher reuse policy preserved, source attribution retained |
| Genetics consent | Original MedlinePlus Genetics | Genetics-specific reuse basis, US context retained |
| Emergency concepts | WHO/ICRC Basic Emergency Care, 2018; CC BY-NC-SA 3.0 IGO | Four complete, visually checked module overviews; no quick-treatment cards imported |

This mixed-license collection is configured for **local noncommercial educational use**. Attribution and applicable share-alike terms must accompany redistribution or adapted material; the collection is not cleared for unrestricted commercial deployment. Public availability does not supply blanket reuse rights: [NCBI Bookshelf explicitly requires checking each book's permissions](https://www.ncbi.nlm.nih.gov/sites/books/NBK45610/). Current OpenStax AI-restricted material, StatPearls no-derivatives material, unclear-rights candidates and third-party images were excluded.

Some publisher pages rejected direct downloads. Their retained full-text Markdown snapshots came from the primary URL through the research connector; acquisition method, limits, rights evidence and hashes distinguish these from original HTML/PDF bytes. Four oversized microbiology contexts and one corrupt extraction were withheld rather than cut into misleading fragments.

## Curriculum mapping and medical review

The official [NMC curriculum index](https://nmc.org.in/page/rules-regulations-rules-regulations-nmc) supplied the pinned curriculum and clarification. The parser found 2,627 unique competency records; removal of PS9.2 by the clarification leaves **2,626 active records**. Clarified PY9.1 and PE6.4 retain original provenance.

[`curriculum-audit.json`](artifacts/evaluation/mbbs-v1/curriculum-audit.json) records hashes, rendered visual spot checks, malformed identifiers and source count discrepancies. Four publisher identifier defects were retained with their descriptions. Detailed paediatric table counts differ from the publisher summary; the parser does not manufacture missing rows or claim perfect extraction.

[`curriculum-material-mapping.json`](artifacts/evaluation/mbbs-v1/curriculum-material-mapping.json) contains every active competency. Sparse lexical matching nominated possible material for 2,275 competencies; these are **review candidates**, not covered competencies. Developer inspection produced 25 narrowly scoped partial material associations across 24 distinct competencies.

The [faculty review queue](artifacts/evaluation/mbbs-v1/teaching-faculty-review-queue-r3-final-2026-10-09.json) includes all 2,626 competency forms, the 24 explanation units and nine source wording concerns. Reviewer identity, qualification, decision, missing elements, currency and Indian applicability fields remain null. There has been no medical faculty review.

The nine holds concern wording about enzyme isoforms, oxidative phosphorylation, MHC exceptions, pyroptosis, a vomiting-centre location, drug bioavailability and innate immune memory. Runtime either excludes a passage or permits only its separately checked bounded explanation. Hash checks protect those selections; they do not prove medical truth. Additional source errors may remain undetected.

## Teaching evaluation on the active code

The frozen dataset has **93 questions: 81 supported variants over 27 inspected source passages, plus 12 boundary cases**. Supported questions include explanations, mechanisms, comparisons, MCQ facts, viva prompts, fictional cases and misleading premises. The subject allocation is deliberately documented; it is not evenly weighted or an independent medical examination.

The following fresh runs use the active source release, index, explanation hash and current runtime hashes:

- [Lexical final results](artifacts/evaluation/mbbs-v1/teaching-lexical-active-final-2026-10-09.json).
- [Hybrid final results](artifacts/evaluation/mbbs-v1/teaching-hybrid-active-final-2026-10-09.json).

| Measure | Lexical | Hybrid | Meaning |
|---|---:|---:|---|
| Expected response status | 90/93 — 96.8% | 92/93 — 98.9% | Supported response or boundary non-handling |
| Expected-source retrieval hit | 75/81 — 92.6% | 77/81 — 95.1% | An expected source appears among selected references |
| Strict required reference facts | 132/162 — 81.5% | 144/162 — 88.9% | Exact approved phrase matches; paraphrases may be missed |
| Complete bounded reference agreement | 61/81 — 75.3% | 69/81 — 85.2% | All selected facts, status, bindings and support checks pass |
| Supported cases answered | 78/81 | 80/81 | Not a correctness score |
| Citation integrity, supported-case denominator | 78/81 — 96.3% | 80/81 — 98.8% | Unanswered supported questions count as failures |
| Valid bindings among emitted answers | 78/78 | 80/80 | IDs and cited excerpts bind to the reference release |
| Exact-source or approved-unit support | 169/169 claims | 183/183 claims | Paired text/source integrity, not faculty validation |
| Boundary non-handling | 12/12 | 12/12 | Teaching layer declines product/personal/emergency/unknown inputs |
| Clinical correctness / faculty score | **Unmeasured** | **Unmeasured** | No qualified reviewer has scored the answers |

No listed forbidden contradiction occurred. The finite contradiction list is not exhaustive. Every required fact remains in the denominator when an answer is absent. MCQ tests check referenced facts rather than complete option-letter answers; fictional cases test conceptual material, not demonstrated differential-diagnosis competence.

Remaining failures include research-specific consent, some oxygen-transport clauses, protein-bound drug distribution, developing/impaired hepatic drug metabolism, surveillance scope and family-history qualifications in bipolar disorder. A source hit can coexist with an incomplete answer. The readable [developer report](artifacts/evaluation/mbbs-v1/teaching-developer-report-r3-reviewedfix-2026-10-09.md) and machine outputs distinguish conservative phrase misses from substantive question-fit gaps.

## Stronger local model comparison

The [full comparison](artifacts/evaluation/mbbs-v1/model-benchmark/20261008T155505252163Z/COMPARISON-final.md) preserves all 26 raw responses, model digests, government-source evidence, resource samples and developer observations.

| Measurement | Qwen3-VL 2B | Qwen3 4B Q4_K_M |
|---|---:|---:|
| Strict structured reference passes | 5/13 | 5/13 |
| API/decode/truncation errors | 0 | 0 |
| Median warm response time | 3.130 s | 6.304 s |
| Median generation throughput | 122.90 tokens/s | 59.96 tokens/s |
| Sampled peak process working set | 1.333 GiB | 1.706 GiB |
| Model GPU allocation | 1.620 GiB | 2.792 GiB |

The 4B model was fully offloaded on the RTX 4050 laptop GPU. These figures came from this computer, under a single fixed-order run with seed 42, temperature 0, a 2,048-token context and a 768-output-token ceiling. Working-set sampling is not a guaranteed peak-RAM measurement; allocated offload memory is not peak VRAM. Desktop workload and possible brief CPU embedding overlap limit timing comparisons.

**5/13 is not “38.5% medical accuracy.”** The strict scorer rejects incomplete fact lists, quotation changes and unsupported citation IDs, and it also has documented paraphrase/refutation false positives. Developer examination found a vaccine/passive-immunity mistake and contradictory antibiotic facts in the 2B output. The 4B output improved one immunity explanation but altered purported exact quotations and invented a citation ID in other answers. Faculty assessment is absent.

Decision: retain the existing text/vision model. The officially acquired `qwen3:4b-q4_K_M` remains installed for future controlled evaluation. Teaching facts currently use source text or paired approved explanations, so a larger model does not bypass evidence checks or turn unsupported medical questions into answers.

## Engineering and live verification

- **248 engineering tests passed**, with one existing Starlette TestClient deprecation warning: [`pytest-active-final.log`](artifacts/evaluation/mbbs-v1/pytest-active-final.log).
- Ruff passed: [`ruff-active-final.log`](artifacts/evaluation/mbbs-v1/ruff-active-final.log).
- Actual local browser bridge: **10/10 synthetic smoke checks passed**, with the temporary API session deleted afterward: [`live-api-20261008T194619880649Z.json`](artifacts/evaluation/mbbs-v1/live-api-20261008T194619880649Z.json).
- Browser inspection confirmed a visible plain-language osmosis answer, its publisher citation and expandable supporting passage in the existing dark workspace.
- Live readiness reports 1,891 teaching contexts, 24 approved explanation units, nine holds, hybrid search and no teaching initialization error. Existing product, English OCR and X-ray profiles remain active.

Independent code review found and reproduced two defects. The fictional-case prefix no longer suppresses explicit real/current emergencies in later clauses. Reviewed explanation selection no longer maps ST-segment/respiratory depression to a psychiatric note or diffusion tensor imaging to membrane diffusion. Generic connective words were also removed from raw topic matching after the reviewer found a remaining perinatal-depression fallback. Regression tests and actual application probes verify those fixes. Language-based policy checks remain unvalidated triage.

The respiratory-depression smoke response retrieves a relevant pulmonary chapter, but its long excerpt covers dyspnoea and treatment discussion rather than a complete receptor-level explanation. This check verifies contextual routing, not clinical completeness. The Ascoril catalogue probe remains explicitly unverified and incomplete; education references do not establish exact Indian product composition.

## Reproduce, rollback and continue expansion

From the project root, use `.venv\Scripts\python.exe` for the following scripts:

```powershell
.\.venv\Scripts\python.exe scripts\activate_teaching.py
# After validation, this authorized setup can be repeated with --activate.
.\.venv\Scripts\python.exe scripts\smoke_mbbs.py
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check backend scripts tests
```

`activate_teaching.py` checks the final release, matching semantic index and pinned explanation artifact. `--activate` writes only `configs/teaching.env` and records an exact rollback for any previous teaching profile. On this first activation, removing the new teaching profile and restarting restores the pre-teaching configuration; the installed medicine/model `.env` was unchanged. Keep the old releases, indexes and profiles rather than rewriting their manifests.

`build_teaching_index.py` and `build_teaching_explanations.py` require fresh output paths. `evaluate_mbbs.py` requires a fresh output filename; its JSON records dataset/source/index/explanation/runtime hashes. Source acquisition and curriculum tools are `build_mbbs_library.py` and `research_mbbs_curriculum.py`. Existing product ingestion/versioning remains separate.

The next reviewed release should close the documented question-fit failures, add faculty-approved clinical teaching and practical examination material, expand authoritative Indian references under verified rights, and broaden independent held-out questions. It should prioritise forensic medicine, ENT, ophthalmology, dermatology, anaesthesiology, radiology, deeper surgery/paediatrics/OBGYN and clinical reasoning. Complete curriculum coverage, current Indian prescribing applicability and readiness for medical decisions remain **unestablished**.
