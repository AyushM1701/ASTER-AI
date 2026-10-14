# MDS open corpus checkpoint — 11 October 2026

The authorized collection ran and stopped at its 120-document milestone. Everything remains **STAGED**. No active index was changed, and no corpus was imported, uploaded, published or used for training. National curriculum scope only; no university overlay.

The collection is a research supplement, not a complete MDS teaching library. Every document awaits independent qualified clinical and faculty review.

## Actual collection

| Measure | Count |
| --- | ---: |
| Discovered candidate records, including repeated search hits | 3,047 |
| Authoritative JATS rights inspections, including one repeat verification | 149 |
| Rights-screened, extracted, unique documents | 120 |
| Complete original XML files retained | 1 |
| Original XML files withheld because asset rights were unresolved | 119 |
| Staged RAG documents | 110 |
| Staged RAG chunks | 6,775 |
| Separately labelled training-candidate documents | 110 |
| Evaluation holdout documents / chunks | 10 / 632 |
| Metadata-only rejected or quarantined candidate decisions | 463 |
| CC BY-SA conditional records | 0 |
| Recorded collection failures | 6 |
| Clinical review pending / faculty reviewed | 120 / 0 |

The 119 affected originals were not retained. Their eligible prose and asset-stripped JATS derivatives are stored, with original hashes, attribution, exclusion notices and authoritative rights evidence. Derivatives are labelled separately from originals. The retained original is *Advancing oral immunology for improving oral health*, [PMC11747000](https://europepmc.org/articles/PMC11747000), CC BY 4.0.

Observed licenses: 117 documents under CC BY 4.0 and three under CC BY 2.5. NC, ND, unspecified licenses and unresolved conflicts never enter default exports. CC BY-SA is a conditional, metadata-only track. No government/public-domain status was assumed.

| Specialty label | Documents |
| --- | ---: |
| Oral and Maxillofacial Pathology and Oral Microbiology | 11 |
| Oral Medicine and Radiology | 13 |
| Oral and Maxillofacial Surgery | 11 |
| Conservative Dentistry and Endodontics | 12 |
| Prosthodontics and Crown & Bridge | 12 |
| Periodontology | 12 |
| Orthodontics and Dentofacial Orthopaedics | 14 |
| Pediatric and Preventive Dentistry | 13 |
| Public Health Dentistry | 11 |
| Shared foundations | 16 |

Labels overlap. A document is stored once and can contribute to several specialties. Searches began across all specialties and foundations, then used narrower title anchors to fill the largest gaps. No recent-year cutoff was imposed.

Resource types are title-indicated, not clinical quality grades: 42 systematic reviews, seven umbrella reviews, seven narrative reviews, two consensus statements, four primary studies and 58 documents with unresolved design. The discovery review filter is not a guarantee of study design; some repository records label cohort or observational studies as review articles. The original publication-type metadata remains available for appraisal.

## Budgets, access and failures

The default configuration caps collection at 120 admitted documents, 200 MiB of response-body data, 1,000 requests, 1,200 seconds, one sequential host worker and 8 MiB per file. Follow-up configurations allocated remaining request/byte/time capacity; every invocation was bounded. Documents and source versions count toward the accumulated 120-document cap.

Completed collection and verification runs made 320 API requests, read 42,291,432 bytes and used 537.85 seconds of recorded collection time. An interrupted initial run made 18 additional requests across six searches that returned 503 because of an unsupported sort parameter. Its elapsed time was not recoverable. Three diagnostic requests read another 93,146 bytes. Known total requests including those diagnostics: 341. No background collection continues.

Disk usage at the final checkpoint was approximately 74.7 MB, including originals/derivatives, search metadata caches, extraction outputs, catalogues, training candidates and RAG exports. The checkpoint records the measured byte count and reporting time; subsequent report regeneration can change it slightly.

Only the official Europe PMC REST OA endpoint was used for article retrieval. Current developer/copyright guidance permits that route and requires item-level license checks: [REST service](https://europepmc.org/RestfulWebService), [copyright guidance](https://europepmc.org/Copyright), [OA subset](https://europepmc.org/downloads/openaccess). The policy evidence file records these sources. Main-site article scraping was not used.

URLs require HTTPS, approved hosts and public DNS destinations. Redirects are validated and refused so they cannot escape request accounting. Downloads enforce media types, size limits, bounded retries, Retry-After handling and time/request/host/byte budgets. Storage paths reject traversal. Caches use atomic writes and checksums; originals and versioned derivatives are immutable. Interrupted items restart bounded retrieval without retaining partial originals. XML uses the existing pinned `defusedxml==0.7.1`, with depth/node caps and no entity expansion. No archives, macros or document scripts are processed.

## Validation and limits

The final real validation checked all 120 document checksums, authoritative license identifiers, provenance, extracted paragraph equality and all 7,407 RAG/holdout character spans. It reported zero issues and no held-out source leakage. A separate excerpt spot-check file contains samples across all nine specialties, foundations, both observed license versions and the original XML. These are source/extraction checks, not independent medical review.

The collector/validator test suite passed 52 tests, including license rejection/conflicts, third-party omissions, identifier mismatch, XML corruption/entities/depth, URL/DNS/redirect/path safety, cache immutability, interruption/size/rate limits, duplicate versions, missing DOI, metadata-only discovery resume and holdout leakage. Ruff passed for both scripts and their tests. The root task runs the integrated project test suite separately.

Unresolved asset tables, figures, photographs, captions and supplements are omitted. Explicit compatible table licenses are handled by the collector and tested for headers, cells, units and coordinates, but no real eligible table or OCR/PDF validation is claimed in this source pack. Citation markers can merge into prose without spacing; this is documented rather than silently altering medical source claims.

Publisher-level retraction/correction/supersession review remains unresolved beyond the screened Europe PMC core fields and JATS notices. Detected editorial notices were excluded. Publication age is not an endorsement of current guidance. Methods, populations, conflicts, limitations, applicability and medical truth require individual clinical appraisal.

## Curriculum coverage and next collection

The [official 2017 national MDS base](https://dciindia.gov.in/Rule_Regulation/MDS_Course_Regulations_2017.pdf) is cited for scope only; its full text is not exported. Current amendment consolidation and detailed section mapping remain pending. The existing editorial taxonomy is reused with canonical national specialty names and explicitly provisional topic/facet associations.

Of 144 specialty/foundation topics, 129 have a source association and 15 remain without one. The 1,728 topic/facet cells contain 1,102 partial-material cells awaiting review and 626 missing-material cells. Those counts describe automated text mentions, not syllabus mastery or verified competence.

Priority missing topics include dental epidemiology, midface fractures, orthognathic surgery, cleft lip/palate, oral health surveys, oral histopathology, root-canal irrigation/obturation, orofacial pain, temporomandibular disorders, dental/general biostatistics, overdentures, oral viral infections and mucogingival surgery. Cross-topic related material does not close a missing topic automatically.

Next source work should prioritize licensed foundation chapters and textbooks, current official standards/guidelines, atlases and eligible tables, laboratory protocols and balanced primary evidence. The present pack uses one repository/source family; it does not claim broad OER or publisher coverage. Independent clinical/faculty review and current national amendment reconciliation are separate outstanding work.

## Files and commands

The corpus root is `data/references/mds/open_corpus/`:

- `manifests/catalogue.jsonl` and `catalogue.csv`: searchable document records, source links, licenses, paths, decisions and review states.
- `rights_evidence/`: exact article permissions, authoritative URL/date, source hash and attribution.
- `raw/`: the one eligible complete original; `extracted/rights_screened_jats/`: eligible asset-stripped derivatives.
- `extracted/`: exact normalized source paragraphs, original section coordinates and separate references.
- `rag_chunks/staged_rag.jsonl`: the 110-document staged RAG export.
- `training_candidates/rights_screened_candidates.jsonl`: candidate material, not a validated training dataset.
- `evaluation_holdout/source_chunks.jsonl`: sources withheld from both RAG and training candidates.
- `metadata_only_exclusions/exclusions.jsonl`: rejection/quarantine reasons without excluded originals.
- `curriculum/topic_facet_matrix.jsonl`: partial/missing coverage and pending review.
- `reports/checkpoint.json`, `quality_validation.json`, `excerpt_spot_checks.json`, `first_batch_validation.json`, `coordinate_repair.json` and `data_card.md`: measured counts, actual checks, usage and limits.
- `config/`: the default snapshot, first-batch, expansion and gap-fill configurations used.

Run from the project root, using the existing virtual environment:

```powershell
.venv/Scripts/python.exe -m scripts.mds_open_collect --dry-run
.venv/Scripts/python.exe -m scripts.mds_open_collect --config data/references/mds/open_corpus/config/first_batch.json
.venv/Scripts/python.exe -m scripts.mds_open_collect --config data/references/mds/open_corpus/config/expansion.json
.venv/Scripts/python.exe -m scripts.mds_open_collect --config data/references/mds/open_corpus/config/gap_fill.json
.venv/Scripts/python.exe -m scripts.mds_open_collect --stage report
.venv/Scripts/python.exe -m scripts.mds_open_validate
.venv/Scripts/python.exe -m pytest tests/test_mds_open_collection.py tests/test_mds_open_validation.py -q
.venv/Scripts/python.exe -m ruff check scripts/mds_open_collect.py scripts/mds_open_validate.py tests/test_mds_open_collection.py tests/test_mds_open_validation.py
```

The milestone configurations were run, not merely suggested. Resuming the final corpus stops immediately at the document cap. Stage selectors expose metadata discovery, gated rights/download/extraction and offline deduplication/quality/export/report; verification, download and extraction remain joined behind the rights gate. The dry run performs no network requests or writes. No new dependencies were required.

The root-owned `scripts/stage_mds_pack.py` adapter performs separate staged preflight and review-attestation checks before any future approved integration. This corpus does not imply that those clinical/source attestations have been obtained. No synthetic examples, benchmark answers or public archives were generated.
