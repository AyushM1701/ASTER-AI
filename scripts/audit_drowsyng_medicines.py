"""Profile a downloaded Netmeds-derived Kaggle CSV without approving its content.

Offline audit only: never creates clinical records, runtime catalogue aliases,
medicine recommendations, OCR corrections or clinical source citations.
"""

import collections
import csv
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/references/raw/v2/kaggle_drowsyng"
OUT = ROOT / "data/knowledge_v2"


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def artifact(path):
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": digest(path),
    }


def main():
    metadata_path = RAW / "dataset-view-response.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    csv_path = RAW / "medicines.csv"
    csv.field_size_limit(10_000_000)
    names = collections.Counter()
    urls = collections.Counter()
    blanks = collections.Counter()
    sentinels = collections.Counter()
    generic_by_name = collections.defaultdict(set)
    generic_by_url = collections.defaultdict(set)
    content_by_url = collections.defaultdict(set)
    categories_by_url = collections.defaultdict(set)
    generic_strings = set()
    category_strings = set()
    origins = collections.Counter()
    url_hosts = collections.Counter()
    row_hashes = set()
    rows = malformed = duplicate_rows = missing_names = content_present = 0
    examples = []
    with csv_path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        columns = reader.fieldnames
        required = {"med_name", "med_url", "generic_name", "drug_content", "disease_name"}
        if not columns or not required.issubset(columns):
            raise ValueError("Unexpected schema; refuse to interpret changed columns")
        for row in reader:
            rows += 1
            if None in row or any(row.get(key) is None for key in columns):
                malformed += 1
                continue
            row_hash = hashlib.sha256(
                json.dumps([row[key] for key in columns], ensure_ascii=False).encode()
            ).digest()
            duplicate_rows += row_hash in row_hashes
            row_hashes.add(row_hash)
            for key in columns:
                blanks[key] += not row[key].strip()
                sentinels[key] += row[key].strip().casefold() in {
                    "na", "n/a", "null", "none", "nan"
                }
            name, url, generic = row["med_name"], row["med_url"], row["generic_name"]
            missing_names += not name.strip()
            if name.strip():
                names[name] += 1
                generic_by_name[name].add(generic)
            if url.strip():
                urls[url] += 1
                url_hosts[urlsplit(url).hostname or "invalid"] += 1
                generic_by_url[url].add(generic)
                content_by_url[url].add(hashlib.sha256(row["drug_content"].encode()).hexdigest())
                categories_by_url[url].add(row["disease_name"])
            generic_strings.add(generic)
            category_strings.add(row["disease_name"])
            origins[row["drug_manufacturer_origin"]] += 1
            content_present += bool(row["drug_content"].strip())
            if len(examples) < 5:
                # Identity fields only; do not reproduce scraped medical prose.
                examples.append({key: row[key] for key in ("med_name", "generic_name", "disease_name", "med_url")})
    old = json.loads((OUT / "kaggle_brand_candidates.json").read_text(encoding="utf-8"))
    previous_names = set(old["candidates"])
    del old
    exact_overlap = len(set(names) & previous_names)
    profile = {
        "rows": rows,
        "columns": columns,
        "malformed_csv_rows": malformed,
        "duplicate_entire_rows": duplicate_rows,
        "missing_names": missing_names,
        "unique_exact_names": len(names),
        "unique_exact_product_urls": len(urls),
        "names_with_multiple_rows": sum(n > 1 for n in names.values()),
        "duplicate_name_extra_rows": sum(n - 1 for n in names.values()),
        "names_with_conflicting_raw_generic_strings": sum(len(v) > 1 for v in generic_by_name.values()),
        "product_urls_with_conflicting_raw_generic_strings": sum(len(v) > 1 for v in generic_by_url.values()),
        "product_urls_with_differing_content": sum(len(v) > 1 for v in content_by_url.values()),
        "product_urls_in_multiple_disease_categories": sum(len(v) > 1 for v in categories_by_url.values()),
        "unique_raw_generic_strings_including_blank": len(generic_strings),
        "unique_raw_disease_categories_including_blank": len(category_strings),
        "rows_with_nonblank_drug_content": content_present,
        "blank_or_whitespace_counts": dict(blanks),
        "literal_null_like_string_counts": dict(sentinels),
        "manufacturer_origin_raw_counts": dict(origins),
        "product_url_hosts": dict(url_hosts),
        "previous_catalogue_exact_name_overlap": exact_overlap,
        "names_absent_from_previous_exact_name_catalogue": len(names) - exact_overlap,
        "comparison_limitation": "Exact strings only. Pack-size/case/spacing variants can inflate apparent novelty; no new drug-entity count or equivalence is inferred.",
    }
    payload = {
        "dataset": {
            "ref": "drowsyng/medicines-dataset",
            "url": "https://www.kaggle.com/datasets/drowsyng/medicines-dataset",
            "title": metadata["title"],
            "creator": metadata["creatorName"],
            "version": 1,
            "metadata_current_version": metadata["currentVersionNumber"],
            "metadata_last_updated": metadata["lastUpdated"],
            "description_collection_date": "February 2025 (uploader statement, not independently verified)",
            "retrieved_date": "2026-10-07",
            "uploader_declared_license": metadata["licenseName"],
            "declared_upstream": "Netmeds; programmatically scraped, per uploader description",
        },
        "artifacts": [artifact(metadata_path), artifact(RAW / "medicines-dataset-version-1.zip"), artifact(csv_path)],
        "profile": profile,
        "first_five_identity_rows": examples,
        "decision": {
            "status": "excluded_pending_rights_and_clinical_source_review",
            "clinical_review": False,
            "active_records_added": 0,
            "runtime_catalogue_added": False,
            "rights": "Kaggle uploader declares Apache 2.0, but no upstream permission is evidenced. Netmeds terms sections 8.3 and 9.2 restrict content copying/extraction/database reuse without permission. The uploader label alone does not establish rights to this scraped content.",
            "rights_source": "https://www.netmeds.com/terms-and-conditions",
            "medical": "Retailer descriptions and disease browsing categories are not manufacturer-approved Indian prescribing information. No independent accuracy/completeness validation or formulation equivalence is established.",
            "excluded_uses": ["clinical RAG", "model training", "OCR name corrections", "substitution", "dosing", "current prices/availability", "automatic medicine-disease indications"],
            "future_work": "Establish upstream permission or independently source permitted authoritative manufacturer/CDSCO material; preserve product identity and version, review sections, release separately and evaluate before activation.",
        },
    }
    audit_path = OUT / "drowsyng_catalogue_audit.json"
    audit_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report = [
        "# Medicines Dataset (drowsyng): acquisition and suitability audit",
        "",
        "Audit date: **2026-10-07**. Downloaded Kaggle version **1**, `medicines.csv`. Raw snapshots are ignored local audit material, not active clinical evidence.",
        "",
        "## Measured profile",
        "",
        "| Measure | Value |",
        "|---|---:|",
    ]
    for key in (
        "rows", "unique_exact_names", "unique_exact_product_urls", "malformed_csv_rows", "duplicate_entire_rows", "missing_names",
        "names_with_multiple_rows", "duplicate_name_extra_rows", "names_with_conflicting_raw_generic_strings",
        "product_urls_with_conflicting_raw_generic_strings", "product_urls_with_differing_content", "product_urls_in_multiple_disease_categories",
        "rows_with_nonblank_drug_content", "previous_catalogue_exact_name_overlap", "names_absent_from_previous_exact_name_catalogue",
    ):
        report.append(f"| {key.replace('_', ' ')} | {profile[key]:,} |")
    report += [
        "",
        "The exact-name comparison does not measure new drugs: package-size, case and spelling differences count separately. "
        "Conflicts refer to differing raw strings, which can include formatting differences; they were not clinically reconciled. "
        "`disease_name` is a retailer browsing category, not a validated indication. No repeated product URLs were observed in this file. "
        "No clinical claims are inferred from these counts.",
        "",
        "Columns: `" + "`, `".join(columns) + "`. The actual CSV spells the package column **`drug_varient`**, while the description says `drug_variant`.",
        "",
        f"Missing fields: **{blanks['generic_name']} generic names**, **{blanks['drug_content']} descriptions**, "
        f"{blanks['prescription_required']:,} prescription-requirement strings and {blanks['drug_varient']:,} package-variant strings. "
        "Missing prescription-requirement text must not be interpreted as over-the-counter status. "
        "There are 6,378 distinct raw generic strings including the blank string; strengths and combinations are retained, so this is not a count of distinct ingredients.",
        "",
        "## Suitability decision",
        "",
        "**Not added to Aster's clinical library or runtime catalogue.**",
        "",
        "The [Kaggle description](https://www.kaggle.com/datasets/drowsyng/medicines-dataset) identifies Netmeds as the scraped source. "
        "Its metadata declares Apache 2.0 and was last updated March 17, 2025; the description says collection was in February 2025. "
        "Those dates do not establish current labels, availability or price accuracy. "
        "[Netmeds terms](https://www.netmeds.com/terms-and-conditions), sections 8.3 and 9.2, restrict content reuse/extraction without permission. "
        "No upstream permission is evidenced. The uploader's licence declaration does not establish clearance for the source text.",
        "",
        "This dataset offers richer fields than the earlier two-composition-column catalogue, but retailer prose is not a substitute for exact "
        "manufacturer prescribing information or qualified review. It contains no demonstrated handwritten-prescription training labels. "
        "It is excluded from medical RAG, training, OCR correction, dosing, substitution and current price/availability answers. "
        "The existing v2 release, approved source count and baseline scores are unchanged.",
        "",
        "If rights are established, a future separate release can review product identities and descriptions against authoritative labels, "
        "preserve conflicting records and evaluate retrieval/grounding. Another route is independently collecting permitted manufacturer/CDSCO source documents. "
        "No medicine aliases or ingredients have been promoted based on this file.",
        "",
        "## Correct file selection",
        "",
        "Kaggle's [current documentation](https://github.com/Kaggle/kagglehub/blob/main/README.md#kaggledatasetadapterpandas) uses `dataset_load` and a real filename:",
        "",
        "```python",
        "import kagglehub",
        "from kagglehub import KaggleDatasetAdapter",
        "",
        "df = kagglehub.dataset_load(",
        "    KaggleDatasetAdapter.PANDAS,",
        '    "drowsyng/medicines-dataset/versions/1",',
        '    "medicines.csv",',
        ")",
        "print(df.head())",
        "```",
        "",
        "The audit used the public Kaggle API and Python's CSV reader; no dependency installation or app runtime change was needed. "
        "Loading a dataframe is not training or approving a model. Avoid silently replacing a reviewed version with a future latest version.",
        "",
        "[Machine-readable audit](data/knowledge_v2/drowsyng_catalogue_audit.json). Reproduce the offline profile with "
        "`.venv/Scripts/python.exe scripts/audit_drowsyng_medicines.py` after obtaining the recorded snapshots. "
        "SHA-256 values for metadata, ZIP and CSV are in that audit. Full scraped medicine descriptions are not reproduced in this report.",
    ]
    (ROOT / "docs/reports/DROWSYNG_MEDICINES_DATASET_AUDIT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps({"audit": str(audit_path), "profile": profile, "decision": payload["decision"]["status"]}, indent=2))


if __name__ == "__main__":
    main()
