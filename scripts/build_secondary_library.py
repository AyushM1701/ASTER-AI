"""Build an immutable, explicitly unverified secondary layer from eligible links."""

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.services.retrieval import Reference  # noqa: E402
from backend.app.services.secondary_references import (  # noqa: E402
    SOURCE_COLLECTIONS,
    USER_STATEMENT,
)
from scripts.match_medicine_datasets import (  # noqa: E402
    AZ,
    HF,
    NETMEDS,
    SOURCE_HASHES,
    compare_composition,
    literal_key,
    review_flags,
    sha256,
)

DATASETS = {"az_india": "shudhanshusingh/az-medicine-dataset-of-india", "hf_india": "dmedhi/indian-medicines"}


def eligible(record):
    if record["name_match_method"] in {"unmatched", "brand_variant_candidate"}:
        return False
    if record["candidate_count"] != 1 or record["source_composition_conflict"]:
        return False
    candidate = record["candidates"][0]
    if candidate["review_flags"] or not candidate["composition_comparisons"]:
        return False
    if any(item["status"] != "reported_fields_agree" for item in candidate["composition_comparisons"]):
        return False
    if review_flags(record["source_name"], candidate["netmeds_name"], False, 1):
        return False
    return all(compare_composition(value, candidate["netmeds_reported_generic"]) == "reported_fields_agree" for value in record["source_compositions"])


def build(crosswalk, output, authorization):
    if authorization != USER_STATEMENT:
        raise ValueError("Supply the explicit user authorization for unverified secondary use")
    if output.exists():
        raise ValueError("Secondary release already exists; choose a new version")
    for path, expected in SOURCE_HASHES.items():
        if sha256(path) != expected:
            raise ValueError(f"Raw source snapshot changed: {path.name}")
    csv.field_size_limit(10_000_000)
    with NETMEDS.open(encoding="utf-8-sig", newline="") as handle:
        master = {n: {key: row[key] for key in ["med_name", "med_url", "generic_name"]} for n, row in enumerate(csv.DictReader(handle), 1)}
    notes, counts, exclusions = [], Counter(), Counter()
    sources, crosswalk_hashes = [], {}
    for dataset, ref in DATASETS.items():
        path = crosswalk / f"{dataset}_crosswalk.jsonl"
        crosswalk_hashes[dataset] = sha256(path)
        links = []
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                if eligible(row):
                    links.append(row)
                else:
                    exclusions[dataset] += 1
        wanted = {number for link in links for number in link["source_rows"]}
        raw_rows = {}
        if dataset == "az_india":
            with AZ.open(encoding="utf-8-sig", newline="") as handle:
                for number, row in enumerate(csv.DictReader(handle), 1):
                    if number in wanted:
                        raw_rows[number] = row
        else:
            raw_rows = {number: row for number, row in enumerate(pq.read_table(HF).to_pylist(), 1) if number in wanted}
        for link in links:
            candidate = link["candidates"][0]
            target = master[candidate["netmeds_row"]]
            if (target["med_name"] != candidate["netmeds_name"] or target["generic_name"] != candidate["netmeds_reported_generic"]):
                raise ValueError("Crosswalk target changed")
            anchor_id = "netmeds-" + hashlib.sha256(target["med_url"].encode()).hexdigest()[:24]
            if anchor_id != candidate["netmeds_source_id"]:
                raise ValueError("Crosswalk master anchor identity changed")
            rows = [raw_rows[number] for number in link["source_rows"]]
            if any(row["name"] != link["source_name"] for row in rows):
                raise ValueError("Crosswalk source name/row changed")
            if dataset == "az_india":
                compositions = {"+".join(row[key].strip() for key in ["short_composition1", "short_composition2"] if row[key].strip()) for row in rows}
                fields = [("composition", sorted(compositions)[0])]
            else:
                compositions = {row["composition"] for row in rows}
                # A duplicate name with differing purposes/effects is not resolved by voting.
                if any(len({literal_key(row[field]) for row in rows}) > 1 for field in ["uses", "side_effects"]):
                    exclusions["hf_conflicting_clinical_fields"] += 1
                    continue
                fields = [("composition", rows[0]["composition"]), ("uses", rows[0]["uses"]), ("side effects", rows[0]["side_effects"])]
            if compositions != set(link["source_compositions"]):
                raise ValueError("Crosswalk composition fields differ from source snapshot")
            source_id = "secondary-" + hashlib.sha256((ref + "\n" + link["source_name"]).encode()).hexdigest()[:24]
            for field, value in fields:
                if not value.strip():
                    continue
                text = f"Dataset-reported {field} for {link['source_name']}: {value.strip()}"
                if len(text) > 1450:
                    exclusions["field_too_long"] += 1
                    continue
                record = Reference(
                    source_id=source_id, title=f"{link['source_name']} — {'HF Indian medicines' if dataset == 'hf_india' else 'A-Z India dataset'}",
                    url=SOURCE_COLLECTIONS[ref], publisher="Hugging Face · dmedhi" if dataset == "hf_india" else "Kaggle · Shudhanshu Singh",
                    jurisdiction="India", section="Dataset-reported " + field,
                    retrieved_date="2026-10-07", source_date=None, snapshot_id=output.name,
                    text=text, topics=[link["source_name"]], keywords=[field, link["source_name"]],
                    entity=link["source_name"], source_type="unverified_secondary", clinical_review=False,
                    permission_basis={
                        "type": "user_authorized_secondary", "review_status": "unverified",
                        "dataset_ref": ref, "snapshot_sha256": SOURCE_HASHES[HF if dataset == "hf_india" else AZ],
                        "source_rows": link["source_rows"], "source_ids": link["source_ids"],
                        "matched_netmeds_source_id": anchor_id, "matched_netmeds_product": target["med_name"],
                        "match_method": link["name_match_method"], "reported_fields_agree": True,
                        "clinical_equivalence_verified": False,
                    },
                )
                record.chunk_id = record.stable_id()
                notes.append(record)
                counts[dataset + "_notes"] += 1
            counts[dataset + "_products"] += 1
        sources.append({"dataset_ref": ref, "snapshot_sha256": SOURCE_HASHES[HF if dataset == "hf_india" else AZ],
                        "version": "a9f49cbc2f086110b455915ddacad136c7d4634e" if dataset == "hf_india" else "Kaggle version 1, November 2022"})
    output.mkdir(parents=True)
    raw = "".join(record.model_dump_json() + "\n" for record in notes).encode()
    (output / "records.jsonl").write_bytes(raw)
    manifest = {
        "library_version": output.name, "created_utc": datetime.now(timezone.utc).isoformat(),
        "review_status": "unverified", "clinical_review": False,
        "authorization": {"type": "user_authorized_secondary", "user_statement": USER_STATEMENT},
        "records": len(notes), "records_sha256": hashlib.sha256(raw).hexdigest(),
        "matched_products": len({r.permission_basis["matched_netmeds_source_id"] for r in notes}),
        "source_datasets": sources, "counts": dict(counts), "exclusions": dict(exclusions),
        "crosswalk_sha256": crosswalk_hashes, "builder_sha256": sha256(Path(__file__).resolve()),
        "scope": "Supplementary dataset-reported fields. Not clinical review, current product-label verification, or automatic medicine equivalence.",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--crosswalk", type=Path, default=ROOT / "artifacts/evaluation/medicine-crosswalk")
    parser.add_argument("--output", type=Path, default=ROOT / "data/references/secondary/aster-secondary-v1-2026-10-07")
    parser.add_argument("--user-authorization", required=True)
    args = parser.parse_args()
    manifest = build(args.crosswalk, args.output, args.user_authorization)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
