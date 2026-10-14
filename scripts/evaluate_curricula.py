"""Run every curriculum prompt; source bindings are not medical accuracy."""

import argparse
import hashlib
import json
import statistics
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.config import Settings  # noqa: E402
from backend.app.services.teaching import (  # noqa: E402
    TeachingStore,
    retrieval_queries,
    teaching_terms,
)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def normalize(text):
    return " ".join(text.casefold().split())


def validate_blueprint(cases):
    seen = set()
    for case in cases:
        if case["case_id"] in seen:
            raise ValueError("Duplicate curriculum case")
        seen.add(case["case_id"])
        if not case.get("question", "").strip():
            raise ValueError("Empty curriculum question")


def inspect_answer(case, answer, source_texts, units):
    claims = (answer or {}).get("claims", [])
    citations = (answer or {}).get("citations", [])
    cited = {row.get("chunk_id") for row in citations}
    checks = []
    for claim in claims:
        ids = claim.get("citation_ids", [])
        valid_ids = bool(ids) and all(key in cited and key in source_texts for key in ids)
        text = normalize(claim.get("text", ""))
        exact = valid_ids and bool(text) and any(text in normalize(source_texts[key]) for key in ids)
        bound_unit = valid_ids and any(text == normalize(unit["text"]) and set(ids) == set(unit["citation_ids"]) for unit in units)
        checks.append(bool(exact or bound_unit))
    citation_checks = bool(citations) and len(cited) == len(citations) and all(
        row.get("chunk_id") in source_texts and normalize(row.get("excerpt", "")) == normalize(source_texts[row["chunk_id"]])
        for row in citations
    )
    emitted_ids = {key for claim in claims for key in claim.get("citation_ids", [])}
    requested = teaching_terms(case["question"])
    emitted = teaching_terms(" ".join(claim.get("text", "") for claim in claims))
    return {
        "status": (answer or {}).get("status", "not_handled"),
        "handled": (answer or {}).get("status") == "ok" and bool(claims),
        "emitted_claims": len(claims), "bound_claims": sum(checks),
        "all_emitted_claims_bound": bool(claims) and all(checks) and citation_checks and emitted_ids == cited,
        "requested_term_presence": len(requested & emitted) / len(requested) if requested else None,
        "requested_terms_absent": sorted(requested - emitted),
        "term_presence_interpretation": "Lexical diagnostic only; not semantic question fit, completeness or correctness.",
        "clinical_accuracy": None, "curriculum_completeness": None,
        "practical_performance": None, "faculty_review": "pending",
    }


class PreparedDense:
    """Batch the same pinned embedding model; retain original rank mathematics."""

    def __init__(self, original, questions):
        import numpy as np

        if original.client is not None:
            raise ValueError("Prepared evaluation requires the pinned NumPy index")
        self.original = original
        unique = list(dict.fromkeys([*questions, *(part for question in questions for part in retrieval_queries(question))]))
        vectors = original.model.encode(unique, batch_size=64, normalize_embeddings=True, show_progress_bar=False)
        if vectors.shape != (len(unique), original.dimension) or not np.isfinite(vectors).all():
            raise ValueError("Invalid batched query embeddings")
        self.positions = {question: index for index, question in enumerate(unique)}
        self.vectors = vectors
        self.batch_validation = []
        for question in unique[:5]:
            single = original.model.encode([question], normalize_embeddings=True)[0]
            delta = float(np.max(np.abs(single - vectors[self.positions[question]])))
            self.batch_validation.append(delta)
        if max(self.batch_validation, default=0) > 1e-5:
            raise ValueError("Batched and single embeddings differ materially")

    def scores(self, question, allowed):
        if question not in self.positions:
            return self.original.scores(question, allowed)
        allowed = set(allowed)
        values = self.original.vectors @ self.vectors[self.positions[question]]
        return {key: float(value) for key, value in zip(self.original.ids, values, strict=True) if key in allowed}


def run(blueprint, release, index, output, programme=None):
    import torch

    torch.set_num_threads(2)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    document = json.loads(Path(blueprint).read_text(encoding="utf-8"))
    cases = document["cases"]
    if programme:
        cases = [row for row in cases if row["programme"].casefold() == programme.casefold()]
    validate_blueprint(cases)
    runtime_paths = [ROOT / name for name in ("scripts/evaluate_curricula.py", "backend/app/services/teaching.py",
                                             "backend/app/services/policy.py", "backend/app/services/retrieval.py",
                                             "backend/app/adapters/embeddings.py", "backend/app/services/teaching_query.py")]
    hashes = {path.relative_to(ROOT).as_posix(): digest(path) for path in runtime_paths}
    inputs = {"blueprint_sha256": digest(blueprint), "release_manifest_sha256": digest(Path(release) / "manifest.json"),
              "index_manifest_sha256": digest(Path(index) / "manifest.json"), "runtime_hashes": hashes}
    store = TeachingStore(Settings(_env_file=None, enable_teaching=True, teaching_backend="hybrid",
                                   teaching_release_path=Path(release), teaching_index_path=Path(index), teaching_explanations_sha256=""))
    if store.error:
        raise ValueError(store.error)
    prepared = PreparedDense(store.dense, [row["question"] for row in cases])
    store.dense = prepared
    sources = {row.chunk_id: row.text for row in store.records}
    results, counters = [], defaultdict(Counter)
    started = time.perf_counter()
    try:
        with (output / "answers.jsonl").open("x", encoding="utf-8") as journal:
            for number, case in enumerate(cases, 1):
                began = time.perf_counter()
                answer = store.answer(case["question"])
                score = inspect_answer(case, answer, sources, store.units)
                row = dict(case, evaluation=score, answer=answer, seconds=round(time.perf_counter() - began, 6))
                results.append(row)
                journal.write(json.dumps(row, ensure_ascii=False) + "\n")
                for group in ("all", case["programme"], case["programme"] + ":" + case["subject"]):
                    counters[group]["cases"] += 1
                    counters[group][score["status"]] += 1
                    counters[group]["handled"] += score["handled"]
                    counters[group]["bound_answer"] += score["all_emitted_claims_bound"]
                if number % 100 == 0:
                    journal.flush()
                    print(json.dumps({"processed": number, "total": len(cases), "elapsed_seconds": round(time.perf_counter() - started),
                                      "handled": counters["all"]["handled"]}), flush=True)
        unchanged = all(digest(ROOT / name) == value for name, value in hashes.items()) and digest(blueprint) == inputs["blueprint_sha256"]
        summary = {"schema_version": 1, "created_utc": datetime.now(timezone.utc).isoformat(), "release": store.manifest(),
                   "cases": len(results), "groups": dict(counters), "inputs": inputs, "runtime_unchanged": unchanged,
                   "elapsed_seconds": round(time.perf_counter() - started, 3),
                   "median_case_seconds": statistics.median(row["seconds"] for row in results) if results else None,
                   "clinical_accuracy": None, "faculty_review": "not_performed", "complete_curriculum_coverage": None,
                   "batch_embedding_max_delta_first_five": max(prepared.batch_validation, default=0),
                   "limitations": ["Every inventory item is probed; this does not verify curriculum extraction completeness.",
                                   "Three prompt templates are correlated development probes, not independent examination items.",
                                   "A handled answer and source binding can coexist with factual errors or irrelevant content.",
                                   "Requested-term presence is only lexical triage for manual review, not a medical score.",
                                   "Text cannot demonstrate physical, clinical, communication or laboratory competence.",
                                   "No qualified human faculty has assessed clinical accuracy or completeness."]}
        for name, value in (("summary.json", summary), ("answers.json", {"schema_version": 1, "cases": results}),
                            ("gaps.json", {"clinical_accuracy": None, "cases": [row for row in results if not row["evaluation"]["handled"]]})):
            with (output / name).open("x", encoding="utf-8") as handle:
                json.dump(value, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
        if not unchanged:
            raise ValueError("Runtime or blueprint changed; evaluation is superseded")
        print(json.dumps({key: value for key, value in summary.items() if key != "inputs"}, ensure_ascii=False), flush=True)
        return summary
    finally:
        store.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blueprint", type=Path, required=True)
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--programme", choices=["MDS", "MBBS"])
    args = parser.parse_args()
    run(args.blueprint, args.release, args.index, args.output, args.programme)
