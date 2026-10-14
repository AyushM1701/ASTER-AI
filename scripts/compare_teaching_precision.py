"""Compare preserved and current teaching modules on identical frozen inputs."""

import argparse
import importlib.util
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.config import Settings  # noqa: E402
from backend.app.services.teaching import TeachingStore  # noqa: E402
from scripts.evaluate_curricula import PreparedDense, digest, inspect_answer  # noqa: E402


def run(blueprint, baseline, output):
    import torch

    torch.set_num_threads(2)
    document = json.loads(blueprint.read_text(encoding="utf-8"))
    cases = document["cases"]
    tracked = [ROOT / name for name in document["frozen_runtime_hashes"]]
    if any(digest(path) != document["frozen_runtime_hashes"][path.relative_to(ROOT).as_posix()] for path in tracked):
        raise ValueError("Runtime differs from the frozen sample")
    profile = json.loads((ROOT / "configs/comprehensive_teaching_profile.json").read_text())
    release, index = ROOT / profile["TEACHING_RELEASE_PATH"], ROOT / profile["TEACHING_INDEX_PATH"]
    settings = Settings(_env_file=None, enable_teaching=True, teaching_backend="hybrid",
                        teaching_release_path=release, teaching_index_path=index, teaching_explanations_sha256="")
    spec = importlib.util.spec_from_file_location("preserved_teaching_baseline", baseline)
    legacy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(legacy)
    old, new = legacy.TeachingStore(settings), TeachingStore(settings)
    try:
        if old.error or new.error:
            raise ValueError(old.error or new.error)
        if [r.chunk_id for r in old.records] != [r.chunk_id for r in new.records]:
            raise ValueError("Sources differ between comparison arms")
        prepared = PreparedDense(new.dense, [case["question"] for case in cases])
        old.dense = new.dense = prepared
        output.mkdir(parents=True, exist_ok=False)
        for label, store in (("before", old), ("after", new)):
            began = time.perf_counter()
            rows = []
            for case in cases:
                start = time.perf_counter()
                answer = store.answer(case["question"])
                score = inspect_answer(case, answer, {r.chunk_id: r.text for r in store.records}, store.units)
                rows.append(dict(case, answer=answer, evaluation=score, seconds=time.perf_counter() - start))
            summary = dict(cases=len(rows), handled=sum(r["evaluation"]["handled"] for r in rows),
                           bound_answers=sum(r["evaluation"]["all_emitted_claims_bound"] for r in rows),
                           clinical_accuracy=None, faculty_review="pending",
                           median_seconds=statistics.median(r["seconds"] for r in rows),
                           elapsed_seconds=time.perf_counter() - began, teaching=store.manifest(),
                           executing_teaching_sha256=digest(baseline if label == "before" else ROOT / "backend/app/services/teaching.py"),
                           blueprint_sha256=digest(blueprint), release_manifest_sha256=digest(release / "manifest.json"),
                           index_manifest_sha256=digest(index / "manifest.json"),
                           frozen_runtime_hashes=document["frozen_runtime_hashes"],
                           batch_embedding_delta=max(prepared.batch_validation),
                           interpretation="Paired module handling and exact source binding, not source relevance, clinical correctness or comprehensive curriculum coverage.")
            folder = output / label
            folder.mkdir()
            for name, value in (("summary.json", summary), ("answers.json", {"cases": rows})):
                (folder / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(json.dumps(dict(arm=label, cases=summary["cases"], handled=summary["handled"], bound=summary["bound_answers"])), flush=True)
        if any(digest(path) != document["frozen_runtime_hashes"][path.relative_to(ROOT).as_posix()] for path in tracked):
            raise ValueError("Runtime changed during comparison; discard this run")
    finally:
        old.close()
        new.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blueprint", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.blueprint, args.baseline, args.output)
