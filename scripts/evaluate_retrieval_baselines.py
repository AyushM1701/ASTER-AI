"""Run local frozen retrieval components and guarded exact-extractive B6.

No public endpoints, downloads, model migration or deployment. Supply a new
output folder and optionally a compatible existing NumPy dense index.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.config import Settings  # noqa: E402
from backend.app.services.question_plan import plan_question  # noqa: E402
from backend.app.services.teaching import TeachingStore  # noqa: E402
from research.baselines.runner import (  # noqa: E402
    EvaluationPipelineConfig,
    RetrievalExperiment,
    Snapshot,
    run,
)
from scripts.evaluate_mds_supplied import cases_from_bank  # noqa: E402
from scripts.mds_supplied_contracts import DEFAULT_BANK  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--index", type=Path)
    parser.add_argument("--bank", type=Path, default=DEFAULT_BANK)
    parser.add_argument("--cases", type=Path, help="Explicit educational JSONL; optional exact gold hashes/provenance")
    parser.add_argument("--variations", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--candidate-budget", type=int, default=10)
    args = parser.parse_args()
    paths = {"source/" + path.name: path for path in args.release.iterdir() if path.is_file()}
    paths.update({str(path.relative_to(ROOT)).replace("\\", "/"): path
                  for directory in (ROOT / "backend/app", ROOT / "research") for path in directory.rglob("*.py")})
    paths["runner_script"] = Path(__file__)
    paths.update({"dependency/" + path.name: path for path in ROOT.glob("requirements*.txt")})
    paths["dependency/pyproject.toml"] = ROOT / "pyproject.toml"
    for name in ("configs/all_mds_topics.json", "configs/mds_full_curriculum.json"):
        paths[name] = ROOT / name
    for name in ("scripts/evaluate_mds_supplied.py", "scripts/mds_supplied_contracts.py"):
        paths[name] = ROOT / name
    if args.cases:
        paths["input/cases"] = args.cases
    else:
        paths.update({"bank/" + path.name: path for path in args.bank.iterdir() if path.is_file()})
    if args.index:
        paths.update({"index/" + path.name: path for path in args.index.iterdir() if path.is_file()})
    profile = Settings(enable_teaching=True, teaching_release_path=args.release.resolve(),
                       teaching_backend="hybrid" if args.index else "lexical",
                       teaching_index_path=args.index.resolve() if args.index else ROOT / "data/indexes/unused",
                       teaching_explanations_sha256="")
    if args.index:
        import torch

        torch.set_num_threads(2)
        paths.update({"embedder/" + str(path.relative_to(profile.embedding_path)).replace("\\", "/"): path
                      for path in profile.embedding_path.rglob("*") if path.is_file()})
    snapshot = Snapshot(paths)
    store = TeachingStore(profile)
    try:
        if store.error:
            raise ValueError(store.error)
        if args.cases:
            cases = [json.loads(line) for line in args.cases.read_text(encoding="utf-8").splitlines() if line.strip()]
        else:
            cases = []
            for item in cases_from_bank(args.bank, args.variations):
                context = None
                for index, turn in enumerate(item["turns"], 1):
                    cases.append({"case_id": f"{item['case_id']}:{index}", "question": turn["question"],
                                  "major": next(iter(item.get("specialties", [])), "unknown"), "context_topic": context})
                    # Derived only from the preceding original prompt, never a
                    # supplied expected-topic/rubric field.
                    context = plan_question(turn["question"], "study", context_topic=context).topic or context
        experiment = RetrievalExperiment(store, args.candidate_budget,
                                         dense_rank=store.dense.rank if store.dense else None)
        config = EvaluationPipelineConfig(run_id=args.output.name, candidate_budget=args.candidate_budget,
                                          source_version=store.version, input_hashes=snapshot.hashes,
                                          strategies=[f"B{n}" for n in range(9)])
        print(json.dumps(run(experiment, config, cases, snapshot, args.output), indent=2))
    finally:
        store.close()


if __name__ == "__main__":
    main()
