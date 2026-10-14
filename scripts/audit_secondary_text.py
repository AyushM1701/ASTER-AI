"""Compare every admitted secondary note with its original source fields."""

import csv
import json
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]


def main():
    release = ROOT / "data/references/secondary/aster-secondary-v1-r2-2026-10-07"
    with (ROOT / "data/references/raw/v2/kaggle/A_Z_medicines_dataset_of_India.csv").open(encoding="utf-8-sig", newline="") as handle:
        az = {number: row for number, row in enumerate(csv.DictReader(handle), 1)}
    hf = {number: row for number, row in enumerate(pq.read_table(ROOT / "data/references/raw/v2/hf_dmedhi/train-00000-of-00001.parquet").to_pylist(), 1)}
    failures, checked = [], 0
    for line in (release / "records.jsonl").read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        basis = record["permission_basis"]
        field = record["section"].removeprefix("Dataset-reported ")
        is_hf = basis["dataset_ref"] == "dmedhi/indian-medicines"
        for number in basis["source_rows"]:
            row = (hf if is_hf else az)[number]
            value = row[field.replace(" ", "_")] if is_hf else "+".join(row[key].strip() for key in ("short_composition1", "short_composition2") if row[key].strip())
            expected = f"Dataset-reported {field} for {row['name']}: {value.strip()}"
            if record["text"] != expected:
                failures.append({"chunk_id": record["chunk_id"], "source_row": number})
        checked += 1
    result = {"notes_checked": checked, "full_source_text_matches": checked if not failures else None, "failures": failures, "clinical_accuracy": None}
    output = ROOT / "artifacts/evaluation/secondary-v1/source-text-audit.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    assert not failures


if __name__ == "__main__":
    main()
