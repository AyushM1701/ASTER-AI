"""Audit a public Kaggle catalogue and emit quarantined exact-name candidates.

No Kaggle client installation is needed. This script never creates authoritative
drug notes, inferred aliases, clinical indications, or prescribing guidance.
Use --offline to profile already downloaded metadata/ZIP/CSV snapshots.
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import zipfile
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/references/raw/v2/kaggle"
OUT = ROOT / "data/knowledge_v2"
DATASET = "shudhanshusingh/az-medicine-dataset-of-india"
PAGE = f"https://www.kaggle.com/datasets/{DATASET}"
METADATA_URL = f"https://www.kaggle.com/api/v1/datasets/view/{DATASET}"
VERSION = 1
DOWNLOAD_URL = (
    f"https://www.kaggle.com/api/v1/datasets/download/{DATASET}?datasetVersionNumber={VERSION}"
)
RETRIEVED = "2026-10-07"
ZIP_PATH = RAW / "az-medicine-dataset-of-india-version-1.zip"
METADATA_PATH = RAW / "dataset-view-response.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def artifact(path: Path) -> dict:
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def acquire() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    metadata = requests.get(METADATA_URL, timeout=60)
    metadata.raise_for_status()
    metadata.json()  # Reject non-JSON access-block responses.
    METADATA_PATH.write_bytes(metadata.content)
    response = requests.get(DOWNLOAD_URL, timeout=180)
    response.raise_for_status()
    ZIP_PATH.write_bytes(response.content)
    if not zipfile.is_zipfile(ZIP_PATH):
        raise ValueError("Public download did not return a ZIP archive")
    with zipfile.ZipFile(ZIP_PATH) as archive:
        for member in archive.infolist():
            target = (RAW / member.filename).resolve()
            if not target.is_relative_to(RAW.resolve()):
                raise ValueError(f"Unsafe archive member: {member.filename}")
            archive.extract(member, RAW)


def profile() -> None:
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    with zipfile.ZipFile(ZIP_PATH) as archive:
        members = [
            {
                "filename": m.filename,
                "uncompressed_bytes": m.file_size,
                "compressed_bytes": m.compress_size,
            }
            for m in archive.infolist()
        ]
    csv_paths = sorted(RAW.rglob("*.csv"))
    if len(csv_paths) != 1:
        raise ValueError(f"Expected one CSV; found {len(csv_paths)}")
    csv_path = csv_paths[0]
    candidates: dict[str, list[list[str]]] = {}
    blanks = collections.Counter()
    sentinels = collections.Counter()
    names = collections.Counter()
    ids = collections.Counter()
    type_counts = collections.Counter()
    discontinued = collections.Counter()
    ingredient_pairs: dict[str, set[tuple[str, str]]] = collections.defaultdict(set)
    manufacturers_by_name: dict[str, set[str]] = collections.defaultdict(set)
    full_rows = set()
    non_id_rows = set()
    full_duplicates = non_id_duplicates = rows = both_missing = first_missing = malformed_rows = (
        missing_names
    ) = 0
    provenance_examples = []
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames
        if not columns or not {"id", "name", "short_composition1", "short_composition2"}.issubset(
            columns
        ):
            raise ValueError("Required exact-name/composition columns are absent")
        for row in reader:
            rows += 1
            if None in row or any(row.get(c) is None for c in columns):
                malformed_rows += 1
                continue
            values = tuple(row[c] for c in columns)
            no_id = tuple(row[c] for c in columns if c != "id")
            full_duplicates += values in full_rows
            non_id_duplicates += no_id in non_id_rows
            full_rows.add(values)
            non_id_rows.add(no_id)
            for col in columns:
                value = row[col]
                blanks[col] += not value.strip()
                sentinels[col] += value.strip().lower() in {"na", "n/a", "null", "none", "nan"}
            name, first, second = row["name"], row["short_composition1"], row["short_composition2"]
            names[name] += 1
            ids[row["id"]] += 1
            type_counts[row["type"]] += 1
            discontinued[row["Is_discontinued"]] += 1
            first_missing += not first.strip()
            both_missing += not first.strip() and not second.strip()
            if not name.strip():
                missing_names += 1
                continue
            # Exact spelling, case, whitespace and composition strings are preserved.
            # Duplicate-name records remain separate; nothing is merged by similarity.
            candidates.setdefault(name, []).append([row["id"], first, second])
            ingredient_pairs[name].add((first, second))
            manufacturers_by_name[name].add(row["manufacturer_name"])
            if len(provenance_examples) < 5:
                provenance_examples.append(
                    {
                        "source_id": row["id"],
                        "name": name,
                        "short_composition1": first,
                        "short_composition2": second,
                    }
                )

    duplicate_names = {name: count for name, count in names.items() if count > 1}
    composition_conflicts = [name for name, claims in ingredient_pairs.items() if len(claims) > 1]
    manufacturer_conflicts = [
        name for name, makers in manufacturers_by_name.items() if len(makers) > 1
    ]
    provenance = {
        "dataset_ref": DATASET,
        "title": metadata.get("title"),
        "url": PAGE,
        "publisher": "Kaggle; uploaded by " + str(metadata.get("ownerName", "unknown")),
        "creator": metadata.get("creatorName"),
        "owner_ref": metadata.get("ownerRef"),
        "dataset_id": metadata.get("id"),
        "downloaded_version": VERSION,
        "metadata_current_version": metadata.get("currentVersionNumber"),
        "last_updated": metadata.get("lastUpdated"),
        "retrieved_date": RETRIEVED,
        "licence": {
            "uploader_declared_name": metadata.get("licenseName"),
            "url": "https://creativecommons.org/licenses/by-sa/4.0/",
            "verified_basis": "Kaggle public dataset metadata declares this licence; ZIP has no separate licence file; upstream rights clearance is not verified.",
        },
        "review_status": "unverified",
        "clinical_review": False,
        "upstream_source": "Not identified in the downloaded Kaggle metadata or CSV. The uploader describes research but supplies no named original clinical source, manufacturer-label provenance, or validation method.",
        "source_snapshot": artifact(csv_path),
    }
    audit = {
        "dataset": provenance,
        "access": {
            "status": "public_download_succeeded",
            "authentication_required": False,
            "acquisition": "requests to public Kaggle API; no kagglehub installation",
            "metadata_url": METADATA_URL,
            "download_url": DOWNLOAD_URL,
        },
        "metadata_version_history": metadata.get("versions", []),
        "raw_artifacts": [artifact(METADATA_PATH), artifact(ZIP_PATH), artifact(csv_path)],
        "archive_members": members,
        "profile": {
            "rows": rows,
            "columns": columns,
            "blank_or_whitespace_counts": {col: blanks[col] for col in columns},
            "literal_null_like_string_counts": {col: sentinels[col] for col in columns},
            "malformed_csv_rows": malformed_rows,
            "unique_exact_names_including_blank": len(names),
            "candidate_exact_names": len(candidates),
            "candidate_records": sum(len(v) for v in candidates.values()),
            "missing_names": missing_names,
            "unique_source_ids": len(ids),
            "duplicate_source_id_occurrences": sum(n - 1 for n in ids.values()),
            "duplicate_entire_row_occurrences": full_duplicates,
            "duplicate_row_occurrences_excluding_id": non_id_duplicates,
            "exact_names_with_multiple_rows": len(duplicate_names),
            "duplicate_name_extra_rows": sum(n - 1 for n in duplicate_names.values()),
            "exact_names_with_conflicting_composition_strings": len(composition_conflicts),
            "exact_names_with_multiple_manufacturer_strings": len(manufacturer_conflicts),
            "rows_missing_first_composition": first_missing,
            "rows_missing_both_composition_fields": both_missing,
            "type_counts": dict(type_counts),
            "is_discontinued_raw_value_counts": dict(discontinued),
            "duplicate_name_examples": list(duplicate_names.items())[:10],
            "conflicting_composition_examples": composition_conflicts[:10],
        },
        "usage_boundary": {
            "allowed_candidate_use": "Exact catalogue-name lookup for human review, displaying only unverified raw composition claims with provenance.",
            "excluded_use": "No authoritative ingredient confirmation, fuzzy aliases, generic-equivalence mapping, current market-availability claim, therapeutic guidance, warnings, substitution, dosing or personal treatment advice.",
            "staleness": "Uploader metadata says prices and discontinued status describe November 2022. Downloaded version 1 is dated 2022-11-17; current availability is unverified.",
            "composition_limit": "Only two short composition columns exist. Blank second fields may represent single ingredients or incomplete data. Completeness of multi-ingredient products is not established.",
            "licensing": "Uploader-declared CC BY-SA 4.0 and attribution metadata are preserved. This audit does not establish the uploader's rights in upstream material.",
        },
        "raw_examples": provenance_examples,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    audit_path = OUT / "kaggle_catalogue_audit.json"
    index_path = OUT / "kaggle_brand_candidates.json"
    index = {
        "dataset": provenance,
        "review_status": "unverified",
        "clinical_review": False,
        "match_policy": "exact original name equality only; case and whitespace preserved; no inferred aliases or fuzzy matching",
        "entry_fields": ["source_id", "short_composition1", "short_composition2"],
        "composition_status": "unverified raw uploader strings; may be incomplete",
        "candidates": candidates,
    }
    index_path.write_text(
        json.dumps(index, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8"
    )
    audit["candidate_index"] = {
        **artifact(index_path),
        "format": "candidates maps exact original name to a list of compact records in entry_fields order",
    }
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit["profile"], ensure_ascii=False, indent=2))
    print("candidate index:", index_path.stat().st_size, "bytes; sha256:", sha256(index_path))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    if not args.offline:
        acquire()
    profile()


if __name__ == "__main__":
    main()
