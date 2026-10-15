"""Keep source test passes separate from immutable packaged release acceptance."""
import argparse
from pathlib import Path

from aster_release.release import ReleaseError, read_json, sha256

REQUIRED = {
    "no_global_dependencies", "offline_after_install", "unicode_space_path", "hostile_environment",
    "model_digest_mismatch", "index_mismatch", "layout_mismatch", "slow_loading_status",
    "occupied_ports", "printed_ocr_revision_confirmation", "unsupported_medical_dosing",
    "crash_cleanup", "interrupted_download", "loopback_only", "owned_process_shutdown",
    "public_rights_scan", "cpu_only_windows10", "cpu_only_windows11", "non_admin",
    "missing_vc_runtime", "low_resources", "antivirus_smartscreen", "packaged_medical_regression",
}


def validate_acceptance(report, manifest_path):
    if (report.get("manifest_sha256") != sha256(manifest_path)
            or not report.get("reviewer") or not report.get("review_date")):
        raise ReleaseError("Acceptance evidence must identify this exact manifest and its reviewer")
    missing = [name for name in sorted(REQUIRED) if report.get("tests", {}).get(name, {}).get("passed") is not True
               or not report["tests"][name].get("evidence")]
    if missing:
        raise ReleaseError("Packaged release acceptance incomplete: " + ", ".join(missing))
    for name in ("first_ready_seconds", "peak_ram_bytes", "installed_bytes"):
        if type(report.get("measurements", {}).get(name)) not in {int, float} or report["measurements"][name] <= 0:
            raise ReleaseError("Actual clean-machine measurements are required")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    validate_acceptance(read_json(args.report), args.manifest)
    print("Packaged release acceptance verified")


if __name__ == "__main__":
    main()
