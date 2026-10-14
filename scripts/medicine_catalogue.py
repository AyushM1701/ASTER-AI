"""Exact-name lookup in the quarantined Indian Kaggle catalogue."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.services.brand_catalogue import lookup  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", help="Exact full CSV name, including formulation/strength")
    print(json.dumps(lookup(parser.parse_args().name), indent=2))
