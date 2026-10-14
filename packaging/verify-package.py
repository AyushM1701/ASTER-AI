import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
import json
from pathlib import Path

from aster_release.release import verify_package

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--manifest-sha256")
    args = parser.parse_args()
    result = verify_package(args.root, args.manifest_sha256)
    print(json.dumps({k: v for k, v in result.items() if k != "manifest"}, indent=2))
