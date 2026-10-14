import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
from pathlib import Path

from aster_release.release import generate_manifest, read_json, verify_package

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--profile", type=Path, required=True)
    args = parser.parse_args()
    generate_manifest(args.root, read_json(args.profile))
    verify_package(args.root)
