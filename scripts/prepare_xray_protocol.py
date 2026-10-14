"""Bind a research evaluation protocol to local dataset and model manifests.

An independent protocol is created as unresolved. Filling its review fields
requires actual training-overlap evidence; this command never certifies it.
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.config import Settings  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--integration-only", action="store_true")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Protocol exists; use a new version instead of overwriting a fixed protocol")
    settings = Settings()
    weights = json.loads(settings.xray_weights_manifest.read_text(encoding="utf-8"))
    protocol = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "model_id": weights["model_id"], "weight_sha256": weights["sha256"],
        "dataset_manifest_sha256": hashlib.sha256(args.dataset.read_bytes()).hexdigest(),
        "thresholds": {name: .5 for name in ("Cardiomegaly", "Effusion", "Lung Opacity")},
        "threshold_basis": "Upstream operating-point-normalized research score maps its operating point to 0.5. Fixed before this evaluation; not a clinically validated cutoff.",
        "threshold_source": "https://mlmed.org/torchxrayvision/models.html",
        "training_overlap": {
            "status": "integration_only" if args.integration_only else "unresolved",
            "reviewer": None,
            "rationale": "Demo assets cannot establish independent performance." if args.integration_only else "Complete checkpoint-specific patient and image overlap review required.",
            "evidence": [],
        },
        "probability_calibration": "not_fitted",
        "clinical_validation": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(protocol, indent=2) + "\n", encoding="utf-8")
    print("Bound protocol saved; overlap status:", protocol["training_overlap"]["status"])


if __name__ == "__main__":
    main()
