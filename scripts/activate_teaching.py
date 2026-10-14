"""Validate and activate a separate teaching profile with a local rollback."""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.config import Settings  # noqa: E402
from backend.app.services.teaching import TeachingStore  # noqa: E402

PROFILE = {
    "ENABLE_TEACHING": "true",
    "TEACHING_BACKEND": "hybrid",
    "TEACHING_RELEASE_PATH": "data/references/mbbs/releases/aster-mbbs-v1-r3-final-2026-10-08",
    "TEACHING_INDEX_PATH": "data/indexes/mbbs-v1-r3-final",
    "TEACHING_EXPLANATIONS_PATH": "data/references/mbbs/explanations/v1-r3-final.json",
    "TEACHING_EXPLANATIONS_SHA256": "1eceabe9f3dd7d03c9d14464f08762c9fa10042e26c04e6f160ad3955df495e8",
}


def activate(write=False, profile=None, ledger_directory=None):
    profile = PROFILE if profile is None else profile
    if set(profile) != set(PROFILE):
        raise ValueError("Teaching profile fields differ from the allowed configuration")
    for key in ("TEACHING_RELEASE_PATH", "TEACHING_INDEX_PATH", "TEACHING_EXPLANATIONS_PATH"):
        if not (ROOT / profile[key]).resolve().is_relative_to(ROOT.resolve()):
            raise ValueError("Teaching profile path outside workspace")
    values = {key.lower(): value for key, value in profile.items()}
    store = TeachingStore(Settings(_env_file=None, **values))
    if store.error or not store.records or not store.units:
        raise ValueError("Teaching profile failed validation: " + str(store.error))
    result = {"profile": profile, "teaching": store.manifest(), "activated": False}
    if write:
        env = ROOT / "configs/teaching.env"
        before = env.read_bytes() if env.exists() else None
        original_env_sha256 = hashlib.sha256((ROOT / ".env").read_bytes()).hexdigest()
        after = "# Validated local teaching profile; .env can override these fields.\n" + "\n".join(key + "=" + value for key, value in profile.items()) + "\n"
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup = None
        if before is not None:
            backup = ROOT / "data/private/config-backups" / ("before-teaching-profile-" + stamp + ".env")
            backup.parent.mkdir(parents=True, exist_ok=True)
            with backup.open("xb") as handle:
                handle.write(before)
        if (env.read_bytes() if env.exists() else None) != before:
            raise ValueError("Configuration changed while preparing activation")
        temporary = env.with_name("teaching-" + stamp + ".tmp")
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(after)
        os.replace(temporary, env)
        result.update(activated=True, configuration_path=str(env), rollback_path=str(backup) if backup else None,
                      rollback_action="restore_previous_profile" if backup else "remove_teaching_profile",
                      original_env_sha256=original_env_sha256, original_env_unchanged=hashlib.sha256((ROOT / ".env").read_bytes()).hexdigest() == original_env_sha256,
                      before_sha256=hashlib.sha256(before).hexdigest() if before else None,
                      active_profile_sha256=hashlib.sha256(env.read_bytes()).hexdigest())
        ledger = (Path(ledger_directory) if ledger_directory else ROOT / "artifacts/evaluation/mbbs-v1") / ("activation-" + stamp + ".json")
        ledger.parent.mkdir(parents=True, exist_ok=True)
        with ledger.open("x", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2)
            handle.write("\n")
    store.close()
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--activate", action="store_true", help="Write configs/teaching.env after validation; preserve the previous profile")
    parser.add_argument("--profile", type=Path, help="Validated JSON with exactly the six teaching fields")
    parser.add_argument("--ledger-directory", type=Path)
    args = parser.parse_args()
    print(json.dumps(activate(args.activate, json.loads(args.profile.read_text(encoding="utf-8")) if args.profile else None,
                              args.ledger_directory), indent=2))
