"""Stage and audit a pinned Hugging Face medicine table without approving it.

Uses the already installed requests/PyArrow packages; never downloads images,
modifies the active corpus, or treats copied retailer text as verified labeling.
"""

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import pyarrow.parquet as pq
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/references/raw/v2/hf_dmedhi"
OUT = ROOT / "data/knowledge_v2"
DATASET = "dmedhi/indian-medicines"
REVISION = "a9f49cbc2f086110b455915ddacad136c7d4634e"
FILE = "train-00000-of-00001.parquet"
EXPECTED_SHA256 = "8d6d4f5e19ce637093183c246829247dcfa6a2373082f8a2b000e00b0146bee2"
COLUMNS = ["name", "composition", "uses", "side_effects", "image_url"]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized(value):
    # Comparison only: never infer ingredient, spelling, brand or form equivalence.
    return " ".join(value.split()).casefold()


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def acquire():
    RAW.mkdir(parents=True, exist_ok=True)
    base = f"https://huggingface.co/datasets/{DATASET}/resolve/{REVISION}/"
    urls = {
        FILE: base + "data/" + FILE,
        "README.md": base + "README.md",
        "dataset-metadata.json": f"https://huggingface.co/api/datasets/{DATASET}/revision/{REVISION}",
    }
    for name, url in urls.items():
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        content = response.content
        if name == FILE and hashlib.sha256(content).hexdigest() != EXPECTED_SHA256:
            raise ValueError("Pinned Parquet checksum mismatch")
        if name == "dataset-metadata.json" and response.json()["sha"] != REVISION:
            raise ValueError("Dataset metadata revision mismatch")
        path = RAW / name
        if not path.exists():
            path.write_bytes(content)
        elif name != "dataset-metadata.json" and path.read_bytes() != content:
            raise ValueError(f"Existing pinned snapshot differs: {name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true", help="Fetch missing pinned snapshot files")
    args = parser.parse_args()
    if args.download:
        acquire()
    source = RAW / FILE
    if sha256(source) != EXPECTED_SHA256:
        raise ValueError("Pinned Parquet checksum mismatch")
    metadata = json.loads((RAW / "dataset-metadata.json").read_text(encoding="utf-8"))
    if metadata["sha"] != REVISION:
        raise ValueError("Metadata belongs to a different revision")
    table = pq.read_table(source)
    if table.column_names != COLUMNS:
        raise ValueError("Unexpected column schema; refuse to reinterpret it")
    rows = table.to_pylist()
    if any(not isinstance(row[key], str) for row in rows for key in COLUMNS):
        raise ValueError("Non-string/null source fields; review schema before staging")
    names = Counter(row["name"] for row in rows)
    normalized_names = defaultdict(set)
    by_name = defaultdict(list)
    for number, row in enumerate(rows, 1):
        normalized_names[normalized(row["name"])].add(row["name"])
        by_name[row["name"]].append((number, row))
    conflicts = {}
    for name, items in by_name.items():
        compositions = {normalized(row["composition"]) for _, row in items}
        if len(compositions) > 1:
            conflicts[name] = [{"row": n, "composition": r["composition"]} for n, r in items]
    full_rows = {tuple(row[key] for key in COLUMNS) for row in rows}
    clinical_rows = {tuple(row[key] for key in COLUMNS[:-1]) for row in rows}
    varied_clinical_names = [
        name
        for name, items in by_name.items()
        if len({tuple(normalized(r[key]) for key in COLUMNS[1:4]) for _, r in items}) > 1
    ]
    csv.field_size_limit(10_000_000)
    with (ROOT / "data/references/raw/v2/kaggle_drowsyng/medicines.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        retailer_names = {row["med_name"] for row in csv.DictReader(handle)}
    earlier = json.loads((OUT / "kaggle_brand_candidates.json").read_text(encoding="utf-8"))
    prior_names = set(earlier["candidates"])
    overlap = {}
    for label, existing in [("active_netmeds_csv", retailer_names), ("earlier_az_catalogue", prior_names)]:
        previous_normalized = {normalized(name) for name in existing}
        overlap[label] = {
            "exact_name_overlap": len(set(names) & existing),
            "case_whitespace_name_overlap": len(set(normalized_names) & previous_normalized),
            "case_whitespace_names_not_in_source": len(set(normalized_names) - previous_normalized),
            "meaning": "String overlap only; neither matching nor nonmatching names establish equivalent/new medicines.",
        }
    entities_path = OUT / "hf_indian_medicine_candidates.json"
    OUT.mkdir(parents=True, exist_ok=True)
    candidates = {
        "dataset": DATASET,
        "revision": REVISION,
        "snapshot_sha256": EXPECTED_SHA256,
        "review_status": "unverified",
        "clinical_review": False,
        "runtime_enabled": False,
        "candidates": {
            name: {
                "source_rows": [n for n, _ in items],
                "reported_composition_strings": sorted({r["composition"] for _, r in items}),
                "composition_conflict": name in conflicts,
            }
            for name, items in sorted(by_name.items())
        },
    }
    save_json(entities_path, candidates)
    card = metadata.get("cardData") or {}
    profile = {
        "rows": len(rows),
        "columns": COLUMNS,
        "unique_exact_names": len(names),
        "unique_case_whitespace_names": len(normalized_names),
        "repeated_names": sum(count > 1 for count in names.values()),
        "extra_rows_with_repeated_names": len(rows) - len(names),
        "duplicate_entire_rows": len(rows) - len(full_rows),
        "duplicate_clinical_fields_ignoring_image_url": len(rows) - len(clinical_rows),
        "names_with_conflicting_normalized_composition_strings": len(conflicts),
        "names_with_different_normalized_clinical_fields": len(varied_clinical_names),
        "rows_with_explicit_unknown_composition_amount": sum(
            bool(re.search(r"\((?:NA|N/A|unknown|not specified)\)", row["composition"], re.I))
            for row in rows
        ),
        "blank_fields": {key: sum(not row[key].strip() for row in rows) for key in COLUMNS},
        "sentinel_fields": {
            key: sum(normalized(row[key]) in {"na", "n/a", "null", "none", "nan"} for row in rows)
            for key in COLUMNS
        },
        "image_url_hosts": dict(Counter(urlsplit(row["image_url"]).hostname for row in rows)),
        "image_downloads": 0,
    }
    assert profile["rows"] == 11825
    assert len(by_name) == sum(1 for _ in candidates["candidates"])
    audit = {
        "dataset": DATASET,
        "revision": REVISION,
        "audited_utc": datetime.now(timezone.utc).isoformat(),
        "snapshot_sha256": EXPECTED_SHA256,
        "repository_last_modified": metadata["lastModified"],
        "declared_license": card.get("license"),
        "license_files": [x["rfilename"] for x in metadata.get("siblings", []) if "license" in x["rfilename"].lower()],
        "upstream_origin": "Image URLs use onemg.gumlet.io; Tata 1mg origin is an inference, not documented provenance.",
        "profile": profile,
        "composition_conflicts": conflicts,
        "varied_clinical_names": varied_clinical_names,
        "overlap": overlap,
        "candidate_index": {"path": entities_path.relative_to(ROOT).as_posix(), "sha256": sha256(entities_path)},
        "decision": {
            "status": "staged_unverified_not_activated",
            "runtime_changed": False,
            "clinical_accuracy": None,
            "reasons": [
                "This repository declares neither a licence nor a documented source/review process.",
                "Three exact product names contain conflicting composition strings; no majority-choice repair is applied.",
                "Rows lack product-label links, manufacturers, per-product dates, warnings, contraindications and interaction sections.",
                "The earlier explicit verification/licensing attestation identifies the separate drowsyng dataset.",
            ],
        },
    }
    save_json(OUT / "hf_indian_medicines_audit.json", audit)
    write_report(audit)
    print(json.dumps({"profile": profile, "overlap": overlap, "conflict_names": sorted(conflicts), "status": audit["decision"]["status"]}, indent=2))


def write_report(audit):
    p = audit["profile"]
    page = f"https://huggingface.co/datasets/{DATASET}"
    card = f"{page}/blob/{REVISION}/README.md"
    lines = [
        "# Hugging Face Indian medicines — ingestion audit",
        "",
        f"Dataset [{DATASET}]({page}); pinned revision `{REVISION}`. Audited {audit['audited_utc']}.",
        "",
        "Downloaded, checksum-verified and staged locally. **Not activated in Aster's clinical retrieval.** "
        "The exact-name candidate index is unverified, not connected to runtime retrieval or OCR repair. "
        "These measurements describe data integrity and overlap, not clinical accuracy.",
        "",
        "| Check | Result |",
        "|---|---:|",
        f"| Rows | {p['rows']:,} |",
        f"| Unique exact product names | {p['unique_exact_names']:,} |",
        f"| Unique names after case/whitespace normalization | {p['unique_case_whitespace_names']:,} |",
        f"| Extra rows repeating a name | {p['extra_rows_with_repeated_names']:,} |",
        f"| Exact duplicate complete rows | {p['duplicate_entire_rows']:,} |",
        f"| Duplicate clinical fields ignoring image URL | {p['duplicate_clinical_fields_ignoring_image_url']:,} |",
        f"| Names with conflicting composition strings | {len(audit['composition_conflicts'])} |",
        f"| Names with different clinical field strings | {p['names_with_different_normalized_clinical_fields']} |",
        f"| Rows containing an explicit unknown composition amount | {p['rows_with_explicit_unknown_composition_amount']} |",
        "| Null / blank fields | 0 / 0 |",
        "| Parquet checksum and exact schema | Passed |",
        "| Images downloaded | 0 |",
        "| Qualified clinical accuracy | Not measured |",
        "",
        "The five columns are `name`, `composition`, `uses`, `side_effects`, `image_url`. "
        "Composition strings and short uses/side-effect fields could support product reference candidates after verification. "
        "They are incomplete medicine monographs: no contraindications, interactions, warnings, current product-label links, manufacturer identity or per-product review dates are supplied.",
        "",
        "## Licence and provenance",
        "",
        f"The [pinned dataset card]({card}) declares no licence and provides schema metadata without a source narrative. "
        "No licence file appears in the repository listing. This is missing evidence, not a conclusion that the dataset has no rights. "
        "Image links use `onemg.gumlet.io`; Tata 1mg origin is inferred from that host, not documented by the uploader. "
        "A similar mirror's licence cannot automatically be transferred to this repository. "
        "Hugging Face's verified commit marker concerns the commit, not medical review or content licensing. "
        "The upload was last modified 2024-12-24; that does not establish the clinical source date.",
        "",
        "The user's prior verification/licensing confirmation was recorded for `drowsyng/medicines-dataset`. "
        "It has not been silently reused as an attestation for a different uploader and inferred upstream source.",
        "",
        "## Exact-name conflicts",
        "",
        "The following names have more than one composition string after whitespace/case normalization. "
        "This flags data inconsistency; it does not establish which composition is medically correct. "
        "All rows remain in the raw snapshot and the candidate index marks these names as conflicted:",
        "",
    ]
    lines += [f"- {name}: source rows {', '.join(str(row['row']) for row in items)}." for name, items in audit["composition_conflicts"].items()]
    lines += [
        "",
        f"Different clinical strings occur for: {', '.join(audit['varied_clinical_names'])}. "
        "Differences may reflect units, incomplete amounts or wording; the audit does not treat them as proven clinical contradictions. "
        "Embedded `(NA)` amounts are retained as unknown, even though the composition field itself is nonblank.",
    ]
    lines += ["", "## Overlap with Aster's other tables", "", "| Source | Exact name overlap | Case/whitespace overlap | Names absent after normalization |", "|---|---:|---:|---:|"]
    lines += [f"| {label} | {o['exact_name_overlap']:,} | {o['case_whitespace_name_overlap']:,} | {o['case_whitespace_names_not_in_source']:,} |" for label, o in audit["overlap"].items()]
    lines += [
        "",
        "Overlap is based only on strings. Absence can reflect pack sizes, spellings and naming conventions; it is not a count of new medicines. "
        "No brand/ingredient/form equivalence or cross-source composition match was inferred.",
        "",
        "## Ascoril LS and next ingestion step",
        "",
        "This table contains separate exact names `Ascoril LS Syrup`, `Ascoril LS Junior Syrup` and `Ascoril LS Drops`. "
        "That may address the earlier Syrup-name gap after independent product verification. "
        "It does not establish equivalence to Netmeds' Expectorant entry; those names and concentrations must remain separate. "
        "Clinical promotion needs a recorded permission/source basis, conflict resolution against current product information, "
        "and a new versioned release with retrieval/abstention evaluation. All conflicting names should remain excluded from clinical evidence until resolved.",
        "",
        "## Reproduce",
        "",
        "The audit uses Aster's existing PyArrow and requests packages. No extra runtime dependency was installed:",
        "",
        "```powershell",
        ".\\.venv\\Scripts\\python.exe scripts/audit_hf_indian_medicines.py --download",
        "# Omit --download to audit the already downloaded snapshot offline.",
        "```",
        "",
        "The requested Hugging Face loader can load the same immutable version in an environment with `datasets` installed. "
        "This is loading reference data, not training Qwen. "
        "[Hugging Face documents the revision parameter](https://huggingface.co/docs/datasets/loading#hugging-face-hub):",
        "",
        "```python",
        "from datasets import load_dataset",
        "ds = load_dataset(",
        f'    "{DATASET}",',
        f'    revision="{REVISION}",',
        '    split="train",',
        ")",
        "```",
        "",
        f"Parquet SHA-256: `{EXPECTED_SHA256}`.",
        "",
        "[Machine-readable audit](data/knowledge_v2/hf_indian_medicines_audit.json), "
        "[unverified exact-name candidates](data/knowledge_v2/hf_indian_medicine_candidates.json), "
        "[audit script](scripts/audit_hf_indian_medicines.py).",
    ]
    (ROOT / "docs/reports/HF_INDIAN_MEDICINES_AUDIT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
