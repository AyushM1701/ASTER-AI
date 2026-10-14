# Aster Indian retailer library — evaluation

Release **aster-v2-netmeds-r2-2026-10-07**, report date **2026-10-07**. The user confirmed verification/licensing and explicitly authorized clinical-library use. Source metadata preserves this as user attestation, distinct from developer integrity checks and qualified clinical review. **Clinical accuracy is not measured; qualified clinical review has not been performed.**

## Coverage and source preservation

| Measure | Recorded value |
|---|---:|
| Combined reference sections | 266,870 |
| Combined source documents | 24,031 |
| Retailer products | 23,939 |
| Retailer sections | 266,620 |
| Clinical retailer source-text chunks | 242,681 |
| Identity-only products | 3,802 |
| Missing description / generic field | 183 / 370 |
| Maximum section characters | 1450 |
| Verbatim source-span / identity checks | Passed / passed |
| Unaudited non-whitespace source gaps | 0 |

Product counts include retailer products, not necessarily distinct drugs. Section counts do not establish complete clinical coverage. All 23,939 rows have identities; 3,802 only have identity evidence because description extraction could not safely produce clinical sections. Retailer purposes/mechanisms/warnings/side effects/interactions are secondary source information, not manufacturer-approved Indian labeling. Source errors, spelling corruption and historical update dates are preserved. Prices and current availability are not served as facts.

Excluded source units are explicitly recorded. Directions/self-treatment, management/storage, source bibliography/author boilerplate, diagnostic lists, unrecognized layouts and unsplittable qualified units are not silently truncated into clinical claims. The complete CSV remains local audit material. Recorded exclusions:

- `direct_directions_or_self_treatment`: 47,705
- `storage_or_product_management`: 17,460
- `bibliography_not_independent_source_verification`: 18,402
- `author_metadata_not_clinical_approval`: 19,767
- `diagnostic_test_list_not_independent_guidance`: 12,268
- `unrecognized_source_layout`: 3,343
- `unsplittable_qualified_unit_over_limit`: 4,748
- `source_header_without_served_body`: 788

## Retrieval development benchmark

Deterministic sampling selected 60 product rows. Product fixtures use exact released identities and available source sections. A top-three source hit is separate from retrieving the expected section. These are development fixtures, not held-out clinical validation.

| Group | Lexical | Active hybrid |
|---|---:|---:|
| product — expected source/abstention | 185/185 | 185/185 |
| Product expected-section hits | 125/125 | 125/125 |
| Median product retrieval latency | 2.80 ms | 8.77 ms |
| common brand — expected source/abstention | 12/12 | 12/12 |
| regression — expected source/abstention | 96/107 | 105/107 |
| identity gates — expected source/abstention | 4/4 | 4/4 |

Common-brand fixtures include appropriate insufficient-evidence cases for unsupported formulations, so their hit count is not universal drug coverage. Shared retailer aliases abstain unless an applicable exact product is resolved. Retailer records are deliberately excluded from semantic identity inference: they use an inverted identity index and lexical source-section ranking. The original 250 curated sections retain the pinned MiniLM vectors; all combined records are still checksum/provenance validated.

### Compared with original v2 retrieval

- lexical: 97/107 prior hits → 96/107 current hits; lost ['india-gsk-zentel']; gained [].
- hybrid: 105/107 prior hits → 105/107 current hits; lost []; gained [].

Raw retrieval results record remaining misses and expected-section failures. Scores describe retrieval behavior, not medical correctness or completeness.

## Live Qwen and application checks

| Check | Recorded value |
|---|---:|
| Offline expected response statuses | 8/8 |
| Live expected response statuses | 15/15 |
| Complete served source-section support | 7/7 cited cases |
| Actual model calls / generation-call errors | 7 / 2 |
| Running UI → API checks | 8/8 |
| Automated tests | 142 passed, 0 failed |
| Ruff / pip dependency consistency / JavaScript syntax | Passed |

Live answer methods: `{"extractive_verified_fallback": 7, "none": 8}`. Generation failures and unsupported wording can trigger source-bound extractive fallback. Full-section support requires the complete cited text, not just a matching citation ID. It is a deterministic text-preservation check, not a medical entailment or clinical-accuracy measure. Uncited abstentions are not counted as source-backed successes.

Live failures: `[]`. Automated tests took 36.43 seconds and emitted one existing Starlette/httpx deprecation warning. The actual-app smoke checked Dolo 650 purpose, Ascoril LS Expectorant purpose, Ketocip Shampoo purpose and missing warnings, ambiguous Cyclopam, missing Dolo interaction evidence, Dolo 500-milligram mismatch and personal dosing. Its session was deleted after testing.

## Review fixes and historical pilot

Review reproduced wrong-form/route evidence, shared aliases mixing products, pack volume mistaken for drug strength, and ignored spelled-out units. These were fixed with failing-then-passing regression tests. The focused reviewer rechecked 16 real CSV products and 172 chunks; all 11 assertions passed with no remaining blocker in those findings. Full names containing several form words were also fixed: qualifiers are checked outside the exact matched identity. Unknown concentrations and incompatible extra routes/forms/strengths still abstain.
A subsequent missing-section check found Dolo interaction questions retrieving unrelated purpose text. A dedicated regression test now requires insufficient evidence when the requested clinical section is absent. Retrieval scores above use a fresh run after that fix; the live model evaluation predates it, and the actual-app smoke checks the corrected behavior.

The initial r2 pilot is retained in `artifacts/evaluation/netmeds-v2-r2/`: 119/185 product hits and 14/15 live expected statuses before the full-name form-word fix. The final measurements above rerun the same sample after that fix. The first unactivated release is preserved as historical build evidence. No historical v2 score or failed pilot was overwritten.
The initial app smoke had one incorrect expectation: it expected an answer about Ketocip Shampoo warnings despite that entry having only identity/introduction sections. Its appropriate insufficient-evidence response is retained in `api-smoke-initial.json`. The corrected smoke checks both its supported purpose and missing warnings; production behavior was not weakened to satisfy the test.

## Reproducibility and limits

- CSV SHA-256: `d2efadab6cfba2b5f713126c7b5dbccffd4698dee8fd2ffb795bbe7ba28c433e`.
- Combined corpus snapshot: `8350f0f3f001f6932da13bb51b7fbd69af1fc7be9667eeb275ccb288bcf0c3bd`.
- Semantic vector SHA-256: `d1f40d0d86e8bf1b5e4664b9d0abd019f687743fa19a3ad93ad2cb8b8cf8fd40`; 250 × 384 vectors.
- MiniLM revision: `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`.
- Local Qwen model: `qwen3-vl:2b-instruct`, digest `ea422f1e73652a95479954d8572d3c8c6022f628ce2d38a1a04aae1b7f2d5300`.

[Raw retrieval](artifacts/evaluation/netmeds-v2-final-retrieval/retrieval.json), [latest retrieval summary](artifacts/evaluation/netmeds-v2-final-retrieval/summary.json), [live responses](artifacts/evaluation/netmeds-v2-final/live-results.json), [summary](artifacts/evaluation/netmeds-v2-final/summary.json), [actual app smoke](artifacts/evaluation/netmeds-v2-final/api-smoke.json), [engineering checks](artifacts/evaluation/netmeds-v2-final/engineering-checks.json), [run manifest](artifacts/evaluation/netmeds-v2-final/run-manifest.json), [source-span verification](data/knowledge_v2/netmeds_import_verification.json).

Aster remains an educational/research assistant. Personal dosing, diagnosis and urgent-care gates are preserved. The dataset was not used to fine-tune Qwen or repair handwritten prescriptions. OCR and X-ray models/evaluation remain unchanged. See [the integration guide](NETMEDS_CLINICAL_LIBRARY.md) for exact names, provenance, exclusions and rollback to the original v2.
