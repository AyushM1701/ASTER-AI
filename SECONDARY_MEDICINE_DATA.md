# Aster secondary medicine references

The user authorized both Indian datasets as secondary AI data, with a subtle caution that it is unverified. The authorization is recorded without asserting a new licence, qualified review or clinical approval:

> use this as secondary data in the ai with a subtly caution of unverified data

Release: **aster-secondary-v1-r2-2026-10-07**. This is a separate, checksum-pinned secondary layer supplementing the existing 266,870-section library.

| Coverage | Count |
|---|---:|
| A-Z composition notes | 3,310 |
| HF composition, use and side-effect notes | 3,360 |
| Total secondary notes | 6,670 |
| A-Z source product names included | 3,310 |
| HF source product names included | 1,120 |
| Distinct linked Netmeds products | 3,408 |

Counts are products and source sections, not new medicines or clinical validation. The broader crosswalk includes many weaker candidates; this release admits only name-specific links with one target, no review flags or source composition conflicts, and agreeing reported composition fields. The builder rechecks those fields and exact raw rows against all three pinned snapshots. Duplicate HF names with differing uses or side-effect fields are excluded. Missing fields are not completed.

## Answer behavior

Primary/reference evidence is supplied first. For a question about composition, uses or side effects, Aster can append up to two relevant secondary sections. When the primary library lacks a requested section, a secondary section can supply it only after the same primary product, strength, form, variant, route and ambiguity gates resolve one Netmeds product. Questions involving several unresolved products, unsupported variants or mismatched strengths do not bypass those gates.

An exact name present only in the secondary table can follow its one checked crosswalk link for those eligibility gates. Additional strength/form/route words stay in the query. The link permits secondary notes only: it does not create a primary brand alias or borrow primary clinical sections. Existing manufacturer-label matches retain priority: a short Augmentin tablet question can resolve the Indian GSK label directly, without using secondary notes.

The secondary tables contain no warning, contraindication, dosing or interaction sections; they cannot fill those questions. A-Z contains only two short composition fields, so its record is described as reported fields rather than a guaranteed complete ingredient list. Purposes and side effects come from the HF table; they are reproduced with a dataset-reported prefix and retain source spelling/qualifications.

Every used secondary claim has a citation to its dataset and preserves source rows, raw snapshot hash, matched Netmeds anchor and `review_status: unverified`. The model receives this status alongside the evidence. Complete-source-text support is required whenever secondary material is supplied, even if the global strict-grounding setting is disabled. Unsupported generation uses an explicitly named secondary source-text fallback. The model cannot remove the server-added caution or promote a note to a verified product label.

The answer shows one small caption:

**Unverified secondary data · confirm with the product label.**

Secondary source cards also show **Unverified secondary data** in the existing caption style. The notice appears only when the answer actually cites secondary evidence. Qualified review and current product equivalence are not established by reported-field agreement or agreement across overlapping datasets.

The ambiguous Ascoril LS Syrup/Expectorant links remain excluded. This release does not make Syrup, Drops and Junior interchangeable. Prescription OCR confirmation and personal-dosing/urgent-care gates retain their existing behavior.

## Integrity and activation

The manifest, note file and individual canonical chunk IDs are validated before loading. The manifest hash is pinned in local configuration. A changed file, unsupported source URL, promoted review status, duplicate note or invalid anchor fails closed for the secondary layer. Its state appears separately under `secondary_references` in readiness.

```powershell
.\.venv\Scripts\python.exe scripts/activate_secondary_library.py --release data/references/secondary/aster-secondary-v1-r2-2026-10-07
# Restart Aster after activation or disabling.
.\.venv\Scripts\python.exe scripts/activate_secondary_library.py --disable
```

The pre-activation environment is backed up in ignored `.env.before-secondary`. A disabled secondary layer leaves the original primary release selected.

[Secondary manifest](data/references/secondary/aster-secondary-v1-r2-2026-10-07/manifest.json), [source notes](data/references/secondary/aster-secondary-v1-r2-2026-10-07/records.jsonl), [crosswalk](MEDICINE_DATASET_CROSSWALK.md), [HF acquisition audit](HF_INDIAN_MEDICINES_AUDIT.md), [builder](scripts/build_secondary_library.py), [runtime tests](tests/test_secondary_references.py).
