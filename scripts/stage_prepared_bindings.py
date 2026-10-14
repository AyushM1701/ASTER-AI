"""Stage inspected exact prepared-unit bindings without changing source text or holds."""

import argparse
import copy
import hashlib
import json
import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.config import Settings  # noqa: E402
from backend.app.services.prepared_evidence import prepared_support  # noqa: E402
from backend.app.services.question_plan import RequestedFacet  # noqa: E402
from backend.app.services.teaching import TeachingStore  # noqa: E402


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def stage(release, decisions, output):
    release, output = Path(release).resolve(), Path(output).resolve()
    if output.exists():
        raise FileExistsError(output)
    teacher = TeachingStore(Settings(_env_file=None, enable_teaching=True,
                                    teaching_backend="lexical", teaching_release_path=release))
    try:
        if teacher.error:
            raise ValueError(teacher.error)
        manifest_bytes = (release / "manifest.json").read_bytes()
        manifest = json.loads(manifest_bytes)
        explanations = json.loads((release / "explanations.json").read_bytes())
        units = {unit["id"]: unit for unit in explanations["units"]}
        seen = set()
        for decision in decisions:
            identity = decision.get("unit_id")
            if identity in seen or identity not in units:
                raise ValueError("unknown or repeated prepared unit")
            seen.add(identity)
            unit = units[identity]
            if (decision.get("clinical_review") is not False
                    or decision.get("review_origin") != "ai_source_inspection"
                    or decision.get("prepared_sha256") != sha(unit["text"].encode())
                    or decision.get("parent_hashes") != unit.get("source_hashes")
                    or not all(isinstance(decision.get(key), str) and decision[key].strip()
                               for key in ("support_rationale", "qualification_note"))):
                raise ValueError("inspection identity, hashes, origin and rationale required")
            if unit.get("facet_bindings"):
                raise ValueError("existing facet bindings must remain immutable")
            bindings = decision.get("bindings", [])
            if not isinstance(bindings, list):
                raise ValueError("binding list required")
            if not bindings:
                continue
            unit["prepared_text_sha256"] = decision["prepared_sha256"]
            unit["facet_bindings"] = copy.deepcopy(bindings)
            for binding in bindings:
                if set(binding) != {"topic_id", "facet", "scope"} or not all(isinstance(value, str) for value in binding.values()):
                    raise ValueError("exact topic, facet and scope required")
                facet = RequestedFacet(**binding, query="inspected exact prepared text")
                if not prepared_support(facet, unit, teacher.references.id_records,
                                        teacher.metadata, teacher.review_flags):
                    raise ValueError(f"prepared identity/rights/hold check failed: {identity}")
            unit["facet_review"] = {
                "reviewer": "Codex", "review_origin": decision["review_origin"],
                "reviewed_on": date.today().isoformat(), "clinical_review": False,
                "support_rationale": decision["support_rationale"],
                "qualification_note": decision["qualification_note"],
                "depth_limit": "bounded foundational explanation; not specialty completeness",
            }
        report = {
            "version": output.name, "decisions": len(decisions),
            "newly_bound_units": sum(bool(item.get("bindings")) for item in decisions),
            "activation": "none", "clinical_review": "pending_F03",
            "parent_manifest_sha256": sha(manifest_bytes),
            "inspection_sha256": sha(json.dumps(decisions, sort_keys=True).encode()),
            "rights": "Inherited per-source terms, holds and attribution unchanged; no new training or redistribution permission.",
        }
        explanations["release_version"] = output.name
        manifest.update(version=output.name, status="inactive_ai_inspected_development_candidate",
                        prepared_binding_audit=report)
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="prepared-binding-", dir=output.parent) as temporary:
            staging = Path(temporary) / "pack"
            staging.mkdir()
            for name in manifest["files"]:
                source = (release / name).resolve()
                if not source.is_relative_to(release):
                    raise ValueError("manifest path escapes release")
                target = staging / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
            (staging / "explanations.json").write_text(json.dumps(explanations, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            manifest["files"] = {name: sha((staging / name).read_bytes()) for name in manifest["files"]}
            (staging / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            probe = TeachingStore(Settings(_env_file=None, enable_teaching=True,
                                          teaching_backend="lexical", teaching_release_path=staging))
            try:
                if probe.error:
                    raise ValueError(probe.error)
            finally:
                probe.close()
            staging.rename(output)
        return report
    finally:
        teacher.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release", type=Path)
    parser.add_argument("decisions", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(stage(args.release, json.loads(args.decisions.read_text(encoding="utf-8")), args.output), indent=2))
