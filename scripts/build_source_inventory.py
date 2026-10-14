"""Preserve a supplied inventory as a reproducible typed discovery catalog."""

import argparse
import json
from pathlib import Path

from research.data.source_inventory import build_inventory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    registry = build_inventory(args.input.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(registry, handle, indent=2, ensure_ascii=False)
    print(json.dumps({"entries": len(registry["entries"]), "specialties": len(registry["specialties"]),
                      "acquired": 0, "output": str(args.output)}))


if __name__ == "__main__":
    main()
