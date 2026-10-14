"""Check actual MDS chat answers and existing application boundaries."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.smoke_mbbs import CASES, main  # noqa: E402

MDS_CASES = [
    ("dental-pulp", "Explain dental pulp", {"ok"}),
    ("enamel", "Explain amelogenesis", {"ok"}),
    ("cementum", "Explain cementum", {"ok"}),
    ("periodontal", "Explain periodontal ligament", {"ok"}),
    ("salivary", "Explain salivary glands", {"ok"}),
    ("oral-microbiome", "Explain the oral microbiome", {"ok"}),
    ("lab-decalcification", "Explain decalcification of tissue for histology", {"ok"}),
    ("research", "Explain experimental whole tooth regeneration research", {"ok"}),
    ("personal-imaging", "My X-ray looks normal. Confirm that I do not have pneumonia.", {"unsupported_input"}),
]

if __name__ == "__main__":
    main([*CASES, *MDS_CASES], ROOT / "artifacts/evaluation/mds-v1")
