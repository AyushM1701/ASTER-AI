# Aster medicine dataset crosswalk

Subsequent update: selected links with one target and agreeing reported fields are included in the user-authorized [unverified secondary layer](SECONDARY_MEDICINE_DATA.md). The broader crosswalk remains candidate evidence, with no automatic alias promotion.

Matched both Indian datasets to the **23,939-product Netmeds snapshot**. Run: 2026-10-07T14:05:01.489173+00:00.

**These are offline candidate links, not verified clinical equivalences or new runtime aliases.** The raw datasets and Aster's active clinical library are preserved. Names, source rows/IDs, compositions, candidate products and review flags remain traceable.

| Measure — unique exact source names | A-Z India | Hugging Face India |
|---|---:|---:|
| Input rows | 253,973 | 11,825 |
| Unique exact source names | 249,398 | 11,498 |
| exact name | 10 | 6 |
| case whitespace name | 3 | 1 |
| source text alias | 4,662 | 1,687 |
| pack or unit normalized name | 1,384 | 590 |
| brand variant candidate | 11,074 | 3,333 |
| unmatched | 232,265 | 5,881 |
| Any name or brand candidate | 17,133 | 5,617 |
| Name-specific candidate (excludes brand-only) | 6,059 | 2,284 |
| Exactly one candidate | 11,182 | 3,369 |
| Multiple candidates | 5,951 | 2,248 |
| Source names with composition-string conflicts | 461 | 3 |
| Unique candidate with reported field agreement and no flags | 3,310 | 1,120 |

Methods are mutually exclusive per source name, tried in table order. Counts use distinct exact source names, not source rows or new medicines. Names with one candidate still require evidence review. The final row measures syntactic field agreement only; it is not a clinical accuracy score.

## How the comparison works

1. Compare exact names, then case/whitespace names, then aliases already extracted from Netmeds source text.
2. Compare candidate keys after trailing-pack removal and unit-space/plural-form normalization. Strength numbers and release/variant qualifiers remain.
3. Generate review candidates with exact brand/qualifier keys while ignoring numbers and form words. Junior, SR/CR/SF, route and flavour tokens remain. No fuzzy spelling search is used.
4. Preserve every candidate; flag ambiguous targets, differing forms/numbers, incomplete compositions and source conflicts. No first-candidate selection occurs.
5. Compare reported ingredient/amount strings with concentrations intact. No synonym, concentration, unit conversion or missing-ingredient repair is applied.

The conservative matcher can miss equivalent products with different spellings, qualifiers or units. A detected difference is a source-string difference, not proof that an ingredient or label is medically wrong. A-Z's two composition fields can be incomplete, so matching a subset never establishes the complete ingredient list.

## Netmeds master coverage

| Unique Netmeds rows reached | A-Z India | Hugging Face India |
|---|---:|---:|
| any | 14,858 | 6,638 |
| name specific | 6,251 | 2,416 |
| unflagged field agreement | 3,309 | 1,120 |

Both Indian datasets have name-specific candidates for **2,375** master products; at least one does for **6,292**. Candidate coverage is not independently verified coverage.

## Reported composition comparisons

Counts below are per candidate product and distinct source composition string; several comparisons can come from one source name.

| Outcome | A-Z India | Hugging Face India |
|---|---:|---:|
| ingredient strings differ | 4,635 | 1,370 |
| reported fields agree | 9,461 | 3,701 |
| same ingredients amount or basis differs | 12,916 | 4,887 |
| source subset only | 565 | 18 |
| unavailable or unparsed | 542 | 143 |

## Ascoril LS example

- `Ascoril LS Syrup` → `Ascoril LS Drops 15ml`: multiple_netmeds_candidates, dosage_form_differs, brand_only_review_candidate, composition_requires_review; composition outcomes unavailable_or_unparsed.
- `Ascoril LS Syrup` → `Ascoril LS Expectorant 100ml`: multiple_netmeds_candidates, dosage_form_differs, brand_only_review_candidate, composition_requires_review; composition outcomes ingredient_strings_differ.

The Syrup/Expectorant naming gap can be linked for review. It is not resolved as a runtime alias. The A-Z record omits the third ingredient supplied by the HF and Netmeds rows; HF reports `/5ml` while the Netmeds generic field omits that denominator. Those differences must be checked against current product information before any formulation equivalence is asserted.

## Files and reproducibility

- [Summary](../../artifacts/evaluation/medicine-crosswalk/summary.json).
- [A-Z full crosswalk](../../artifacts/evaluation/medicine-crosswalk/az_india_crosswalk.jsonl) and [name summary CSV](../../artifacts/evaluation/medicine-crosswalk/az_india_name_summary.csv).
- [HF full crosswalk](../../artifacts/evaluation/medicine-crosswalk/hf_india_crosswalk.jsonl) and [name summary CSV](../../artifacts/evaluation/medicine-crosswalk/hf_india_name_summary.csv).
- [Netmeds reverse coverage CSV](../../artifacts/evaluation/medicine-crosswalk/netmeds_reverse_coverage.csv).
- [Selected A-Z examples](../../artifacts/evaluation/medicine-crosswalk/az_india_examples.json), [HF examples](../../artifacts/evaluation/medicine-crosswalk/hf_india_examples.json).

```powershell
.\.venv\Scripts\python.exe scripts/match_medicine_datasets.py --output artifacts/evaluation/NEW_CROSSWALK_RUN
.\.venv\Scripts\python.exe -m pytest -q tests/test_medicine_crosswalk.py
```

Run took 14.26 seconds. Raw snapshot, alias corpus and matcher hashes are recorded in the summary. No medical factual accuracy or clinical equivalence metric is claimed. Source licensing/review metadata stays separate: matching another table does not transfer its permission basis or approval status.

## Validation

All 253,973 A-Z rows and 11,825 HF rows are accounted for exactly once. Candidate totals, ambiguity/conflict flags and the 23,939-row reverse CSV agree with the saved summary. Real-source checks passed for Augmentin's reported fields, Ascoril Syrup ambiguity, Junior isolation and the Drops name link. The full automated suite passed **149 tests** in 26.99 seconds with one existing Starlette/httpx deprecation warning; Ruff passed. See [integrity and engineering checks](../../artifacts/evaluation/medicine-crosswalk/integrity-checks.json).
