# Aster's Indian retailer medicine library

Dataset: `drowsyng/medicines-dataset`, Kaggle version 1, `medicines.csv`. Integration date: **2026-10-07**. Release: **aster-v2-netmeds-r2-2026-10-07**.

The user explicitly confirmed verification/licensing and instructed Aster to use this dataset in its clinical reference library. That approval is preserved verbatim in the source metadata:

> it is verified and has the license, use it for aster's clinical library

This is recorded as **user-attested verification and licensing**, separately from developer ingestion checks. It does not claim an independent licence audit, manufacturer approval or qualified clinical validation. The uploader declares Apache 2.0 and identifies Netmeds as the scraped source. Citations identify the material as a secondary retailer monograph, with its source URL and source update date where recoverable.

## Included coverage

| Measure | Actual count |
|---|---:|
| Product documents | 23,939 |
| Imported sections, including identity | 266,620 |
| Clinical source text sections | 242,681 |
| Product identity sections | 23,939 |
| Products with an extracted product-name alias | 18,823 |
| Products with an explicit source update date | 19,872 |
| Identity-only products | 3,802 |
| Missing descriptions / generic-name fields | 183 / 370 |
| Rejected product rows | 0 |
| Combined release with original v2 | 266,870 sections / 24,031 documents |

All 23,939 products have an identity record. A product count is not a count of medicines with complete clinical descriptions, unique ingredients or verified formulations. For 3,802 products, only identity metadata can be served because the description was missing or could not be safely extracted within the source-boundary rules.

Recognized headings provide introduction, purposes, mechanisms, side effects, warnings, precautions, interactions and synopsis material. Every served source-text chunk is reproduced from recorded source spans, with whitespace normalization only. Spelling errors and source inconsistencies are preserved rather than silently corrected. Chunks contain at most 1,450 characters and retain subheading/qualification context.

Direct directions, personal-dose/self-treatment FAQs, side-effect management instructions, storage material, source bibliography and author boilerplate are excluded from clinical answers under Aster's existing scope. Nonstandard layouts and overly long unsplittable qualified units are explicitly audited, rather than cut mid-qualification. The complete CSV remains local audit material. The independent span check found **zero unaudited non-whitespace source gaps**: source text is either served verbatim or covered by an explicit exclusion.

## How to ask questions

Use a complete product name, including its formulation and strength. Full CSV names with pack sizes are supported. For example:

```text
What is Dolo 650 used for?
What are Dolo 650 warnings?
What is Ascoril LS Expectorant 100ml used for?
What are Atrest 25mg Tablet 10'S interactions?
```

Aliases come from matching source headings or product-name text. They are not fuzzy spelling corrections or generic-equivalence mappings. Shared aliases require product disambiguation; Aster abstains when more than one retailer product remains applicable. The dataset's Expectorant, Drops and Junior variants are distinct. **Ascoril LS Syrup is not automatically equated to Ascoril LS Expectorant.** The older `catalogue:` command still queries the separate 2022 candidate catalogue.

Exact identity matching removes the named product's pack-volume text before checking additional strength qualifiers. Explicit extra strengths, forms, routes and variants must match that same product. Unknown concentrations and unsupported prescription details stay unresolved. Retailer metadata never silently repairs handwritten OCR.

The library expands educational medical retrieval. It does not diagnose, prescribe, determine a personal dose, substitute medicines or establish whether a drug combination is safe for an individual. Requests for those actions retain the existing policy responses. Historical retailer descriptions are not current manufacturer prescribing information or comprehensive interaction checks.

## Retrieval and source integrity

Retailer medicines use an inverted exact-identity index and lexical section ranking. Purpose, warning, mechanism and interaction questions prioritize the corresponding source heading. If a requested clinical section is absent, Aster reports insufficient evidence. This avoids inferring medicine identity from semantic similarity. The original 250 curated reference sections retain the pinned local MiniLM semantic index.

The combined release is immutable. Its source register binds each product's URL, version, raw CSV SHA-256, user attestation and complete set of section checksums. Netmeds is admitted only for this explicitly attested collection; it is not globally declared an authoritative manufacturer source. Tampered or incomplete approval sets fail validation. Source cards display the retailer provenance and user-attested approval basis.

Files:

- [User-approved document records](data/knowledge_v2/netmeds_user_approved_documents.json)
- [Extraction audit and exclusions](data/knowledge_v2/netmeds_import_audit.json)
- [Independent source-span verification](data/knowledge_v2/netmeds_import_verification.json)
- [Combined release](data/references/releases/aster-v2-netmeds-r2-2026-10-07/manifest.json)
- [Combined index](data/indexes/aster-v2-netmeds-r2-2026-10-07/manifest.json)
- [Evaluation](NETMEDS_CLINICAL_LIBRARY_EVALUATION.md)

The initial `aster-v2-netmeds-2026-10-07` build is retained as unactivated historical evidence. The r2 release contains the final alias and extraction-audit fixes.

## Rebuild, evaluate and rollback

The import script requires the already authorized user statement explicitly and uses the existing downloaded CSV; see `scripts/import_netmeds_medicines.py --help`. New content requires a new reviewed release and a new index directory. Build never overwrites a release.

```powershell
.\.venv\Scripts\python.exe scripts/knowledge_library.py build data/knowledge_v2/reviewed_documents.json data/knowledge_v2/netmeds_user_approved_documents.json --catalogue data/knowledge_v2/india_catalog.json --output data/references/releases/NEW_RELEASE --reviewer "Named reviewer and user-attested basis" --reviewed
.\.venv\Scripts\python.exe scripts/ingest.py --sources data/references/releases/NEW_RELEASE/sources.yaml --corpus data/references/releases/NEW_RELEASE/records.jsonl --output data/indexes/NEW_INDEX --backend hybrid --collection medical_reference_v2 --exact-retailer-search
.\.venv\Scripts\python.exe scripts/evaluate_netmeds_library.py --release data/references/releases/NEW_RELEASE --index data/indexes/NEW_INDEX --output artifacts/evaluation/NEW_RUN --live
```

The exact-retailer flag excludes only retailer monographs from dense vectors; all combined sections still undergo provenance/checksum validation. The original semantic vectors cannot be omitted through that flag. Activation validates the selected release/index/model before updating library settings.

To return to the original 250-section v2 library:

```powershell
.\.venv\Scripts\python.exe scripts/activate_library.py --release data/references/releases/aster-v2-2026-10-07 --index data/indexes/aster-v2-numpy-2026-10-07
```

Restart the local app after changing versions. The existing v1 rollback is also available with `scripts/activate_library.py --v1`. The pre-expansion `.env` library profile is backed up separately; rollback selects data/indexes and does not undo matching or policy fixes.
