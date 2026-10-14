# Aster Knowledge Library v2 implementation

The user approved the six-part expansion on 2026-10-07: acquire authoritative medical and product references, preserve provenance, import and review sections, version the library, improve retrieval, and evaluate grounded answers. This is an educational reference expansion, not clinical validation or model training.

## Delivery

1. Preserve the seed corpus and source register as v1. Acquire source snapshots for at least 40 medical topics, 25 product-specific US labels, and Indian workflow/product references. Keep the Indian essential-medicines catalogue separate from clinical monographs.
2. Extend record and source-register metadata with document versions, section checksums, product identities, routes, aliases, developer and clinical review status. Reject changed, unapproved, superseded or duplicated identities.
3. Add offline PDF, HTML, SPL XML and text section importers. Extraction creates pending drafts, never approved medical content. Build immutable releases only from explicitly reviewed sections.
4. Install and pin MiniLM/Chroma; compare lexical and hybrid retrieval. Keep exact medicine identity and formulation gates ahead of vector ranking, and enforce a semantic confidence floor for educational queries.
5. Reject unsupported medical/drug model-memory fallback. Validate generated medical claims against cited text, with conservative extractive fallback when strict support cannot be established. Keep personal diagnosis/dosing and prescription confirmation controls.
6. Run source-integrity, ingestion, retrieval, API and live-model evaluations; save raw evidence and an MD report. Activate only the tested release and retain rollback paths.

## Acceptance and practical limits

No universal drug coverage or clinical-review claim. Unknown brands and ambiguous prescription abbreviations remain unresolved. Foreign labels are identified by jurisdiction and cannot establish equivalence to Indian products. Catalogue membership supplies identity/listing evidence, not indication, contraindication or treatment instructions. Imported material requires source and rights review before release.
