"""Snapshot public source documentation and audit CheXpert patient identifiers.

No accounts, agreements, images, model training or runtime corpus changes.
"""

import argparse
import hashlib
import io
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def audit(output):
    output.mkdir(parents=True, exist_ok=True)
    client = requests.Session()
    sources, repos = [], {}
    for repo, branch in [("mlmed/torchxrayvision", "main"), ("rajpurkarlab/cheXpert-test-set-labels", "main"), ("rajpurkarlab/cheXlocalize", "master")]:
        response = client.get(f"https://api.github.com/repos/{repo}/commits/{branch}", timeout=30)
        response.raise_for_status()
        repos[repo] = response.json()["sha"]
    content = {}
    for name, repo, path in [
        ("upstream-train.py.txt", "mlmed/torchxrayvision", "scripts/train_model.py"),
        ("chexpert-groundtruth.csv", "rajpurkarlab/cheXpert-test-set-labels", "groundtruth.csv"),
        ("chexpert-labels-README.md", "rajpurkarlab/cheXpert-test-set-labels", "README.md"),
        ("chexlocalize-README.md", "rajpurkarlab/cheXlocalize", "README.md"),
        ("chexlocalize-download-instructions.md", "rajpurkarlab/cheXlocalize", "download_instructions.md"),
    ]:
        url = f"https://raw.githubusercontent.com/{repo}/{repos[repo]}/{path}"
        response = client.get(url, timeout=30)
        response.raise_for_status()
        content[name] = response.content
        (output / name).write_bytes(response.content)
        sources.append({"url": url, "file": name, "sha256": digest(response.content), "revision": repos[repo]})
    client.close()
    train_path = ROOT / ".venv/Lib/site-packages/torchxrayvision/data/chexpert_train.csv.gz"
    train = pd.read_csv(train_path, usecols=["Path"])
    truth = pd.read_csv(io.BytesIO(content["chexpert-groundtruth.csv"]))
    def patient(value):
        match = re.search(r"(?:^|/)patient(\d+)(?:/|$)", value)
        if not match:
            raise ValueError("Source path has no CheXpert patient identifier")
        return match.group(1)
    train_groups = {patient(value) for value in train["Path"]}
    test_groups = {patient(value) for value in truth["Study"]}
    overlap = sorted(train_groups & test_groups)
    targets = {"Cardiomegaly": "Cardiomegaly", "Effusion": "Pleural Effusion", "Lung Opacity": "Lung Opacity"}
    weight = json.loads((ROOT / "configs/xray_weights.json").read_text(encoding="utf-8"))
    report = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "checkpoint": {key: weight[key] for key in ["model_id", "sha256", "source_revision", "source_url", "preprocessing_version"]},
        "filename_identified_source_families": ["NIH", "PadChest", "CheXpert", "MIMIC-CXR", "NIH-Google", "OpenI", "RSNA/Kaggle"],
        "published_checkpoint_specific_training_inventory": "Not established by the available model metadata; source script is corroborating evidence, not an exact run manifest.",
        "chexpert_metadata_comparison": {
            "training_csv_sha256": digest(train_path.read_bytes()), "training_rows": len(train),
            "training_patients": len(train_groups), "test_studies": len(truth), "test_patients": len(test_groups),
            "overlapping_patient_count": len(overlap), "overlapping_patient_ids": overlap,
            "label_counts": {label: {"source_column": source, "positive": int((truth[source] == 1).sum()),
                                      "negative": int((truth[source] == 0).sum()), "unknown": int((~truth[source].isin([0, 1])).sum())}
                             for label, source in targets.items()},
            "comparison_scope": "Same CheXpert identifier namespace only. Does not exclude all training sources or image duplicates.",
            "age_and_AP_PA_metadata_in_test_labels": False,
        },
        "candidate": {
            "name": "CheXlocalize / CheXpert expert test set", "status": "requires_provider_access_and_complete_review",
            "description_url": "https://aimi.stanford.edu/datasets/chexlocalize",
            "download_url": "https://stanford.redivis.com/datasets/efx9-5nspnbb4b",
            "label_mapping": targets, "required_before_evaluation": [
                "Provider-authorized image access and permitted research use",
                "Original adult age and AP/PA metadata plus supported-input/de-identification review",
                "Matching study-level labels to frontal images; lateral images excluded",
                "Documented checkpoint-specific patient/image training-overlap exclusion",
                "Patient-separated development/calibration and test cohorts",
                "Pinned image hashes and predeclared thresholds/protocol",
            ],
        },
        "sources": sources, "independent_accuracy": None, "calibration": None,
    }
    (output / "audit.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    inventory = {"sources_checked_utc": report["created_utc"], "runtime_ingestion": False, "resources": [
        {"name": "PCOM AI Datasets", "url": "https://libguides.pcom.edu/c.php?g=1386314&p=10554413", "role": "Discovery directory"},
        {"name": "CheXlocalize", "url": report["candidate"]["download_url"], "role": "Priority imaging evaluation candidate; provider access required"},
        {"name": "NIH expert labels", "url": "https://docs.cloud.google.com/healthcare-api/docs/resources/public-datasets/nih-chest", "role": "Research labels; NIH/Google training-source overlap unresolved"},
        {"name": "BRAX", "url": "https://physionet.org/content/brax/1.1.0/", "role": "External candidate; credentialed access; NLP-derived labels"},
        {"name": "WHO collections", "url": "https://www.who.int/data/collections", "role": "Future country/year-specific public-health knowledge; not medicine monographs"},
        {"name": "MIMIC", "url": "https://mimic.mit.edu/docs/gettingstarted/", "role": "Future clinical-text research; credentialing/training/DUA required; historical records are not guidelines"},
    ]}
    (output / "research-source-register.json").write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["chexpert_metadata_comparison"], indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/evaluation/pcom-xray/source-audit")
    args = parser.parse_args()
    audit(args.output)


if __name__ == "__main__":
    main()
