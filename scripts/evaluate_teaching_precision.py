"""Measure developer source fit and explicit uncertainty, never medical accuracy."""

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.config import Settings  # noqa: E402
from backend.app.services.policy import check_policy  # noqa: E402
from backend.app.services.teaching import TeachingStore  # noqa: E402
from scripts.evaluate_curricula import inspect_answer  # noqa: E402


def inspect_fit(case, response):
    status = (response or {}).get("status", "not_handled")
    citations = (response or {}).get("citations", [])
    patterns = case.get("required_patterns", [case["source_pattern"]] if case.get("source_pattern") else [])
    contexts = [" ".join(str(row.get(key, "")) for key in ("title", "section", "excerpt")) for row in citations]
    forbidden = case.get("forbidden_pattern")
    relevant = [any(re.search(pattern, text, re.I) for pattern in patterns)
                and not (forbidden and re.search(forbidden, text, re.I)) for text in contexts]
    all_topics = all(any(re.search(pattern, text, re.I) for text in contexts) for pattern in patterns)
    status_ok = status == ("ok" if case["status"] == "partial" else case["status"])
    missing = case.get("missing")
    explicit_missing = not missing or any(missing.casefold() in part.casefold()
                                         for part in (response or {}).get("unsupported_topics", []))
    return {"pass": bool(status_ok and all_topics and all(relevant) and explicit_missing),
            "status": status, "relevant_citations": sum(relevant), "emitted_citations": len(citations),
            "all_requested_topics_found": all_topics, "missing_topic_explicit": bool(explicit_missing),
            "clinical_accuracy": None}


def cases_from(document):
    cases = []
    for number, topic in enumerate(document["topics"]):
        for variant, wording in enumerate(document["wordings"]):
            cases.append(dict(topic, id=f"topic-{number}-{variant}", status="ok",
                              question=wording.format(topic=topic["topic"])))
    return [*cases, *document["cases"]]


def run(output, backend):
    import torch

    torch.set_num_threads(2)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    path = ROOT / "data/evaluation/teaching_precision_v1.json"
    profile = json.loads((ROOT / "configs/comprehensive_teaching_profile.json").read_text())
    store = TeachingStore(Settings(_env_file=None, enable_teaching=True, teaching_backend=backend,
                                   teaching_release_path=ROOT / profile["TEACHING_RELEASE_PATH"],
                                   teaching_index_path=ROOT / profile["TEACHING_INDEX_PATH"],
                                   teaching_explanations_sha256=""))
    if store.error:
        raise ValueError(store.error)
    paths = [ROOT / name for name in ("backend/app/services/teaching.py", "backend/app/services/policy.py",
                                     "scripts/evaluate_teaching_precision.py")]
    query_module = ROOT / "backend/app/services/teaching_query.py"
    if query_module.exists():
        paths.append(query_module)
    hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    rows = []
    sources = {row.chunk_id: row.text for row in store.records}
    try:
        for case in cases_from(json.loads(path.read_text(encoding="utf-8"))):
            began = time.perf_counter()
            response = check_policy(case["question"]) or store.answer(case["question"])
            fit = inspect_fit(case, response)
            binding = inspect_answer(case, response, sources, store.units)
            rows.append(dict(case, response=response, fit=fit, binding=binding,
                             seconds=round(time.perf_counter() - began, 6)))
        emitted = sum(row["fit"]["emitted_citations"] for row in rows)
        relevant = sum(row["fit"]["relevant_citations"] for row in rows)
        summary = {"cases": len(rows), "passed": sum(row["fit"]["pass"] for row in rows),
                   "emitted_citations": emitted, "relevant_citations": relevant,
                   "source_fit_precision": relevant / emitted if emitted else None,
                   "source_binding_failures": sum(row["binding"]["handled"] and not row["binding"]["all_emitted_claims_bound"] for row in rows),
                   "backend": backend, "release": store.manifest(), "runtime_hashes": hashes,
                   "challenge_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                   "clinical_accuracy": None, "faculty_review": "pending",
                   "interpretation": "Developer-selected source-context/uncertainty checks. Pattern fit is not factual or semantic medical correctness."}
        if any(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != value for name, value in hashes.items()):
            raise ValueError("Runtime changed during evaluation")
        for name, data in (("summary.json", summary), ("answers.json", {"cases": rows})):
            with (output / name).open("x", encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
        print(json.dumps(summary, ensure_ascii=True))
    finally:
        store.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--backend", choices=("lexical", "hybrid"), default="hybrid")
    args = parser.parse_args()
    run(args.output, args.backend)
