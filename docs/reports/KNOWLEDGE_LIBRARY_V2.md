# Aster Knowledge Library v2

Release: **aster-v2-2026-10-07**. This is a local retrieval library, not a newly trained medical model. Qwen's weights are unchanged. All source sections are developer curated; **qualified clinical review has not been performed**. Coverage is broad enough for development, but cannot answer every question about every medicine.

This guide describes the preserved original v2 release. The subsequent user-approved retailer expansion is documented in [Netmeds Clinical Library](NETMEDS_CLINICAL_LIBRARY.md), including its separate release, source-attestation basis and evaluation.

## What is included

| Collection | Actual coverage | Evidence boundary |
|---|---:|---|
| General education | 46 topics: 31 conditions, nine tests, five imaging terms and prescription-label terminology; 92 sections | Brief original summaries, not complete clinical guidelines |
| US medicines | 31 product-specific DailyMed labels covering 30 medicine entities; 124 sections | Exact product/formulation information and selected purposes, warnings and contraindications; US in-use labels, not a blanket FDA-approval claim |
| Indian clinical context | 12 ICMR Standard Treatment Workflows; 24 sections | Indian workflow context, including historical and 2026 editions where verified |
| Indian product information | Calpol, Augmentin Duo, Ceftum, Eltroxin and Zentel; ten sections | Manufacturer prescribing information for the specifically verified products |
| Indian essential medicines | All 384 NLEM 2022 names; exact-name formulation extraction for 358 names | Catalogue membership and source formulation strings only; not brand equivalence, indication, contraindication or a prescription |
| Kaggle candidate catalogue | 253,973 rows, 249,398 exact names | **Unverified**, separate from clinical retrieval; two short composition columns can omit ingredients |

The active release has **250 sections from 92 unique source documents**. Two pairs of imaging topics share a source page and were consolidated into one document each, without discarding topic sections. The source register preserves original document IDs.

## Authoritative sources and rights

Sources include [NLM MedlinePlus](https://medlineplus.gov/healthtopics.html), NHLBI, FDA, [DailyMed](https://dailymed.nlm.nih.gov/), [ICMR workflows](https://www.icmr.gov.in/standard-treatment-workflows-stws), [GSK India's product information](https://india-pharma.gsk.com/en-in/products/), and the [official NHSRC copy of NLEM 2022](https://qps.nhsrcindia.org/sites/default/files/2022-09/nlem2022.pdf).

Each source has its publisher, jurisdiction, source date where known, retrieval date, version, usage basis, raw snapshot SHA-256 and section approval hashes. Uncertain dates remain null. Attribution is preserved; copyrighted source documents remain ignored local audit material. No open licence is claimed for ICMR or GSK content. Brief original paraphrases are retained rather than reproducing full guidelines or labels. NLM's [reuse policy](https://medlineplus.gov/about/using/usingcontent/) distinguishes its public-domain summaries/test information from third-party material. Six restricted A.D.A.M. encyclopedia sources were excluded. NICE has not been imported; its reuse conditions would need review before a future release.

DailyMed's in-use labels can differ from the latest FDA-approved labeling. The registered product and source version matter. A US label does not establish how an Indian brand is formulated or should be prescribed. Manufacturer labels and workflow editions may be historical; retrieval date does not imply a new clinical review.

## How answers work

1. Existing emergency, diagnosis, prescription-selection and personal-dosing policy checks run first.
2. The library identifies exact registered medicine entities/verified aliases and checks explicit routes, forms and strengths before ranking. Form and strength must belong to one product tuple, not arbitrary combinations of flattened arrays. Unknown variants such as **Calpol T** remain unresolved. Solid unit strengths are matched; unhandled concentrations and liquid/inhaler prescription strengths are left unresolved.
3. Educational search combines specific lexical terms with pinned **MiniLM-L6-v2** embeddings. Vector-only educational matches need an eligibility check and similarity floor. Medicine identity is never inferred from vector similarity or spelling correction.
4. The active vector store is a normalized 250×384 NumPy matrix with a checksum. Retrieval computes cosine scores locally. Chroma was benchmarked, then removed after a dependency audit found unpatched server advisories. A Chroma service was never exposed. The historical `CHROMA_PATH` setting now points to the offline NumPy index.
5. Qwen may select complete reference sections. Output must preserve the **entire cited section**, including negation and neighbouring qualifications. Shortened, paraphrased or unsupported generated claims are rejected and replaced by reviewed extractive notes. The response labels this fallback explicitly.
6. Unsupported medical questions receive insufficient evidence; they do not fall back to unverified model memory. Uncited general chat is limited to explicitly recognized nonmedical requests. Source jurisdictions, versions and limitations accompany responses.

This measures text support, not clinical truth or complete answer relevance. Sources can be incomplete or outdated. Conflicting jurisdictions are shown separately, not silently harmonized. Medicine notes cover selected information; comprehensive mechanisms, interactions, pregnancy guidance and all formulations are not established.

## Prescription and OCR boundaries

The library does not improve or validate handwriting recognition. English handwriting OCR remains experimental with the limitations in `EVALUATION_REPORT.md`. Every extracted prescription must still be checked and confirmed against the original. Medicine name, formulation, strength and route must match an applicable registered product before a prescription explanation is returned. Ambiguous abbreviations and unreadable fields stay unresolved; reference knowledge and the Kaggle catalogue never silently repair OCR or invent a prescription.

The Indian source collection consists of prescribing-information documents and treatment workflows, not private patient prescriptions.

## Use the unverified Kaggle catalogue

In Aster's existing chat, use an explicit exact-name request:

```text
catalogue: Ascoril LS Syrup
```

Or from the project terminal:

```powershell
.\.venv\Scripts\python.exe scripts/medicine_catalogue.py "Ascoril LS Syrup"
```

Only raw reported composition strings are displayed, labelled unverified, with the 2022 date and missing-ingredient warning. No clinical citations, treatment instructions or generic-equivalence mapping are supplied. Include the complete original CSV name, including strength/form; no fuzzy matching is performed. There are **467 names with conflicting composition strings**, so no row is chosen as correct. The source and uploader-declared CC BY-SA 4.0 attribution are preserved in `data/knowledge_v2/KAGGLE_ATTRIBUTION.md`; upstream rights and clinical provenance remain unverified.

The subsequently proposed `drowsyng/medicines-dataset` was downloaded and audited separately. Following the user's explicit confirmation of verification/licensing and instruction to import it, a separate [retailer expansion](NETMEDS_CLINICAL_LIBRARY.md) includes all 23,939 product identities and 242,681 clinical source-text sections. It does not mutate this original immutable v2 release or its historical evaluation scores. The [earlier acquisition audit](DROWSYNG_MEDICINES_DATASET_AUDIT.md) records the initial pre-authorization assessment.

## Files and review workflow

- `data/knowledge_v2/`: acquired editorial datasets, prepared reviewed sections and catalogue audits.
- `data/references/raw/v2/`: ignored HTML/PDF/SPL/CSV snapshots, hashes, source acquisition evidence and exclusions.
- `data/references/releases/aster-v2-2026-10-07/`: immutable `records.jsonl`, `sources.yaml`, `india_catalog.json` and release manifest.
- `data/indexes/aster-v2-numpy-2026-10-07/`: offline vectors, records and index manifest.
- `data/models/minilm/aster-model-manifest.json`: official model revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` and individual file hashes.
- `requirements-knowledge-v2.lock.txt`: installed dependency snapshot. PyTorch/torchvision are the existing matched CPU pair; acquire those wheels from the official PyTorch CPU index when recreating the environment.

HTML, PDF, SPL XML, text and Markdown importers preserve heading/page boundaries. Extraction creates **pending drafts**, not dependable medical sections. PDF extraction is page-level and can miss columns/tables; it is not a replacement for source review. A reviewer must check rights, source version, medicine identity, qualifications, section text and retrieval topics. Clinician/pharmacist review would require a separate process; the developer release command never claims it.

Example extraction, using a local JSON metadata file with document ID, URL, publisher, jurisdiction, dates, version and terms:

```powershell
.\.venv\Scripts\python.exe scripts/knowledge_library.py extract data/references/raw/v2/new-source.pdf --metadata data/knowledge_v2/new-source-metadata.json --output data/knowledge_v2/new-source-draft.json
```

Inspect and edit the draft into short self-contained sections with `topics` and `keywords`. Preserve relevant exceptions. The build checks snapshots, complete approved section sets, duplicates and superseded/conflicting versions. A changed source requires a new reviewed version. One source URL cannot have two simultaneously active versions; consolidate sections sharing one source snapshot explicitly.

For a future reviewed release, create new directory names:

```powershell
.\.venv\Scripts\python.exe scripts/knowledge_library.py build data/knowledge_v2/reviewed_documents.json --catalogue data/knowledge_v2/india_catalog.json --output data/references/releases/NEW_RELEASE --reviewer "Named developer reviewer" --reviewed
.\.venv\Scripts\python.exe scripts/ingest.py --sources data/references/releases/NEW_RELEASE/sources.yaml --corpus data/references/releases/NEW_RELEASE/records.jsonl --output data/indexes/NEW_INDEX --backend hybrid --collection medical_reference_v2
```

Build never overwrites an existing release/index. Embedding token overflow is rejected instead of dropping qualifications. Activation validates the index and model checksums before changing only library settings in `.env`; restart the app afterwards.

Official US product discovery for an uncovered ingredient is available as an explicit developer acquisition step:

```powershell
.\.venv\Scripts\python.exe scripts/source_lookup.py --ingredient "fexofenadine" --output data/references/raw/v2/fexofenadine-candidates.json
```

This sends only the ingredient name to DailyMed, saves pending candidates, and does not approve or activate them. Select and acquire the correct SPL product snapshot, then review sections through the same workflow. Indian brands require authoritative Indian product evidence; Kaggle strings cannot substitute for it. Chat itself does not fetch sources or transmit patient questions to these websites.

## Evaluation and rollback

Read `KNOWLEDGE_LIBRARY_V2_EVALUATION.md` for measured scores, misses, model fallbacks, audits and limitations. Reproduce:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/evaluate_knowledge_v2.py --output artifacts/evaluation/knowledge-v2-rerun
.\.venv\Scripts\python.exe scripts/evaluate_knowledge_v2.py --live --output artifacts/evaluation/knowledge-v2-rerun
```

The live run needs local Ollama with the configured Qwen model. The active app is available at `http://127.0.0.1:8501/` after `start.ps1`. V1's seed corpus and source register remain unchanged, and the original `.env` is retained in the ignored `.env.v1-knowledge-backup`.

Switch back to v1:

```powershell
.\.venv\Scripts\python.exe scripts/activate_library.py --v1
```

Stop the current local app instance and run `start.ps1` again to load the selected version. No clinical approval or medical dependability threshold is implied by any release size or test score.
