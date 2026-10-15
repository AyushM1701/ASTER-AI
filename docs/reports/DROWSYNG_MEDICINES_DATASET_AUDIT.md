# Medicines Dataset (drowsyng): acquisition and suitability audit

**Subsequent user authorization:** The user explicitly confirmed verification/licensing and instructed import into Aster's clinical library. The dataset was then integrated in a separate release under that recorded user attestation. See [the integration guide](NETMEDS_CLINICAL_LIBRARY.md). The suitability decision below preserves the initial assessment before that authorization; it is not the current integration status.

Audit date: **2026-10-07**. Downloaded Kaggle version **1**, `medicines.csv`. Raw snapshots are ignored local audit material, not active clinical evidence.

## Measured profile

| Measure | Value |
|---|---:|
| rows | 23,939 |
| unique exact names | 23,939 |
| unique exact product urls | 23,939 |
| malformed csv rows | 0 |
| duplicate entire rows | 0 |
| missing names | 0 |
| names with multiple rows | 0 |
| duplicate name extra rows | 0 |
| names with conflicting raw generic strings | 0 |
| product urls with conflicting raw generic strings | 0 |
| product urls with differing content | 0 |
| product urls in multiple disease categories | 0 |
| rows with nonblank drug content | 23,756 |
| previous catalogue exact name overlap | 10 |
| names absent from previous exact name catalogue | 23,929 |

The exact-name comparison does not measure new drugs: package-size, case and spelling differences count separately. Conflicts refer to differing raw strings, which can include formatting differences; they were not clinically reconciled. `disease_name` is a retailer browsing category, not a validated indication. No repeated product URLs were observed in this file. No clinical claims are inferred from these counts.

Columns: `disease_name`, `disease_url`, `med_name`, `med_url`, `final_price`, `price`, `prescription_required`, `drug_varient`, `drug_manufacturer`, `drug_manufacturer_origin`, `drug_content`, `generic_name`, `img_urls`. The actual CSV spells the package column **`drug_varient`**, while the description says `drug_variant`.

Missing fields: **370 generic names**, **183 descriptions**, 2,830 prescription-requirement strings and 8,740 package-variant strings. Missing prescription-requirement text must not be interpreted as over-the-counter status. There are 6,378 distinct raw generic strings including the blank string; strengths and combinations are retained, so this is not a count of distinct ingredients.

## Suitability decision

**Not added to Aster's clinical library or runtime catalogue.**

The [Kaggle description](https://www.kaggle.com/datasets/drowsyng/medicines-dataset) identifies Netmeds as the scraped source. Its metadata declares Apache 2.0 and was last updated March 17, 2025; the description says collection was in February 2025. Those dates do not establish current labels, availability or price accuracy. [Netmeds terms](https://www.netmeds.com/terms-and-conditions), sections 8.3 and 9.2, restrict content reuse/extraction without permission. No upstream permission is evidenced. The uploader's licence declaration does not establish clearance for the source text.

This dataset offers richer fields than the earlier two-composition-column catalogue, but retailer prose is not a substitute for exact manufacturer prescribing information or qualified review. It contains no demonstrated handwritten-prescription training labels. It is excluded from medical RAG, training, OCR correction, dosing, substitution and current price/availability answers. The existing v2 release, approved source count and baseline scores are unchanged.

If rights are established, a future separate release can review product identities and descriptions against authoritative labels, preserve conflicting records and evaluate retrieval/grounding. Another route is independently collecting permitted manufacturer/CDSCO source documents. No medicine aliases or ingredients have been promoted based on this file.

## Correct file selection

Kaggle's [current documentation](https://github.com/Kaggle/kagglehub/blob/main/README.md#kaggledatasetadapterpandas) uses `dataset_load` and a real filename:

```python
import kagglehub
from kagglehub import KaggleDatasetAdapter

df = kagglehub.dataset_load(
    KaggleDatasetAdapter.PANDAS,
    "drowsyng/medicines-dataset/versions/1",
    "medicines.csv",
)
print(df.head())
```

The audit used the public Kaggle API and Python's CSV reader; no dependency installation or app runtime change was needed. Loading a dataframe is not training or approving a model. Avoid silently replacing a reviewed version with a future latest version.

[Machine-readable audit](../../data/knowledge_v2/drowsyng_catalogue_audit.json). Reproduce the offline profile with `.venv/Scripts/python.exe scripts/audit_drowsyng_medicines.py` after obtaining the recorded snapshots. SHA-256 values for metadata, ZIP and CSV are in that audit. Full scraped medicine descriptions are not reproduced in this report.
