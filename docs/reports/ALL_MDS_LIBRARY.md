# Aster: all-specialty MDS knowledge expansion

Built 10 October 2026.

Added **203 unique openly licensed journal reviews** and **4,857 research sections**. The composed teaching library contains **7,773 sections from 404 registered sources**. The prior MBBS material, 43 prepared explanations and 117 source review holds remain intact. One additional inherited dentin classification passage is withheld pending review, bringing the hold count to 118.

This is a retrieval-library expansion. Model weights have not been fine-tuned. It is a development educational collection, not evidence that Aster can answer every MDS question or has been clinically validated.

## Specialty material and developer checks

| Specialty | New associated articles | Topics with associated articles | Final guard accepts response |
|---|---:|---:|---:|
| Orthodontics and Dentofacial Orthopaedics | 29 | 13/14 | 14/14 |
| Conservative Dentistry and Endodontics | 18 | 12/14 | 14/14 |
| Oral and Maxillofacial Surgery | 33 | 14/14 | 14/14 |
| Prosthodontics and Crown & Bridge | 21 | 13/14 | 14/14 |
| Periodontology | 31 | 14/14 | 14/14 |
| Oral Medicine and Radiology | 24 | 11/14 | 14/14 |
| Paediatric and Preventive Dentistry | 24 | 13/14 | 14/14 |
| Oral Pathology and Microbiology | 18 | 9/14 | 14/14 |
| Public Health Dentistry | 18 | 9/14 | 10/14 |

Articles can be associated with multiple specialties, so the column totals are not additive. An association does not establish complete topic teaching. The 126-topic map is an editorial starting set, not the full official competency inventory.

## What was acquired

The recent pack contains 153 title-anchored reviews; the older pack contains 50 reviews with recorded publication dates through 2024. Full JATS XML, article-level licence evidence, authors, DOI, dates, complete paragraph extraction and snapshot hashes are retained. The corpus includes CC BY, CC BY-NC and CC BY-NC-SA 4.0 material. Source-specific noncommercial and share-alike obligations apply independently of Aster's MIT code licence.

The two passes each used 126 keyword searches, up to 30 candidate records per topic. The recent pass selected up to three articles per topic; the older pass selected up to one. Earlier broad selections were held out after title/date checks. This is a bounded search, not all free dental literature or a systematic review. Citation count was used only for discovery; it is not a quality score.

[Europe PMC API](https://europepmc.org/RestfulWebService) provides the full-text acquisition route; [PMC text-mining guidance](https://pmc.ncbi.nlm.nih.gov/tools/textmining/) explains permitted bulk access. Individual article licences, rather than repository membership, determine ingestion eligibility.

Tables, figures, quotations, supplements and reference lists are excluded. Overlong sections that cannot preserve complete paragraphs are held out. Every research chunk repeats the source date, review scope and limitations. Population/model and synthesis quality are explicitly unappraised, rather than guessed. Old findings are not labelled current guidance.

## Curriculum and study materials

The [official 2017 MDS syllabus](https://dciindia.gov.in/Rule_Regulation/MDS_Course_Regulations_2017.pdf) includes all nine specialties. The project retains page-bound outlines for all nine in `data/references/mds/all-specialties/curriculum-reference-2017.json`. That file is a curriculum audit reference, not medical teaching content. Later amendments and university-specific requirements still need reconciliation.

[Study material register](MDS_STUDY_MATERIAL_REGISTER.md) lists the imported articles by topic, with links, dates and licences. `artifacts/evaluation/all-mds-2026-10-10/topic-gaps.json` records source associations and unanswered coverage questions. The existing foundational library remains important: specialist research reviews do not replace anatomy, physiology or textbook teaching.

## Evaluation and remaining gaps

The same 126 short questions produced 48/126 teaching responses in the old library and 121/126 in the expanded lexical library. The hybrid run, after the terminal output guard, has statuses {'ok': 122, 'not_handled': 4}. These measure response availability and engineering checks, not medical accuracy, completeness or postgraduate exam performance.

No teaching response was returned for: Public oral health India; Dental health economics; Dental biostatistics; Tobacco cessation dentistry. Hybrid retrieval additionally finds a passage about oral-health survey limitations; that passage does not constitute a complete survey-methods lesson.

All imported study designs/populations require critical appraisal. Independent medical scores remain blank. The faculty review pack includes the responses, evidence checks and scoring fields; no model or developer is presented as medical faculty.

Live response inspection identified a dentin classification passage equating development timing with tooth eruption and reactionary dentin with sclerotic dentin. Revision v3 excludes that entire source unit (`chunk_e9a8236cee2f5b0382dcd5fc`) pending independent review. The appraisal comparisons include [reactionary dentinogenesis](https://pubmed.ncbi.nlm.nih.gov/7626417/), [experimental dentine development definitions](https://pmc.ncbi.nlm.nih.gov/articles/PMC2100295/) and [tooth eruption](https://www.ncbi.nlm.nih.gov/books/NBK549878/). These links are appraisal references, not newly imported teaching evidence or a faculty decision.

Remaining work includes complete specialty competency mapping; verified plain-language introductions and deeper teaching notes; landmark articles absent under available reuse permissions; current guideline/version reconciliation; comparative and case-based answers; image/histology teaching; and independent scoring of factual correctness, applicability and completeness. Comparison requests currently abstain, and the generic viva workflow is not a complete exam tutor. Research-paper drafting and cross-paper critical appraisal are not complete workflows.

## Retrieval and safety changes

The retrieval service now stores source checks within each collection to avoid repeatedly re-scanning thousands of unchanged passages when global caches fill. A changed passage invalidates its stored checks. A direct-dose screening bug affecting multi-digit amounts was fixed. Indian/British spellings including dentine, paediatric and hypomineralisation now retrieve their corresponding concepts. Personal diagnosis/treatment boundaries and the final source-binding guard remain active.

## Reference portals for further checking

These portals were inspected but their complete documents have not been imported without individual rights/version review:

- [AAE clinical resources](https://www.aae.org/specialty/clinical-resources/) and [guidelines](https://www.aae.org/specialty/clinical-resources/guidelines-position-statements/): endodontic terminology, diagnosis and professional guidance. Some resources are explicitly under review.
- [AAPD reference manual](https://www.aapd.org/research/oral-health-policies--recommendations/overview/): paediatric policies, best practices and guidelines.
- [EFP guidelines](https://www.efp.org/education/continuing-education/clinical-guidelines/): periodontitis and peri-implant disease guidance.
- [WHO oral health status report](https://www.who.int/publications/i/item/9789240061484) and [strategy/action plan](https://www.who.int/publications/i/item/9789240090538): public-health context.

## Reproduction and activation

Search maps: `configs/all_mds_topics.json` and `configs/all_mds_established_searches.json`. Acquisition: `python -m scripts.acquire_all_mds --config PATH --output NEW_DIRECTORY`. The selected-title/date registries are the exact release inputs; raw search results include held candidates and must not be substituted blindly. Build with `scripts.build_mds_research --syllabus configs/all_mds_topics.json`, compose through `scripts.compose_mds_library`, and build the hybrid index through `scripts.build_teaching_index`. Use new versioned paths; preserve existing releases and review holds. No evaluation questions/answer keys enter teaching records.

Active release: `data/references/mds/releases/aster-teaching-all-mds-v3-2026-10-10`. Index: `data/indexes/all-mds-v2-2026-10-10`. Runtime activation evidence and previous teaching settings are retained in `artifacts/evaluation/all-mds-2026-10-10/activation-appraisal.json`. The v2 dense index is compatible because v3 preserves byte-identical source records and changes only the version-bound review holds. This collection has not been approved for redistribution in the Windows release bundle.

## Verified runtime

Automated tests: 565 passed. Ruff: passed. Live synthetic API checks: 15/15 expected statuses. Running teaching version: `aster-teaching-all-mds-v3-2026-10-10`. The synthetic session was deleted. These checks do not score medical correctness. The independent review pack is in `artifacts/evaluation/all-mds-2026-10-10/faculty-review-pack-appraisal`.
