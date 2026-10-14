"""Frozen retrieval-stage comparisons and an exact-extractive guarded B6 arm.

B2/B3/B5 are retrieval components, not complete generated-answer baselines.
Corpus permissions and holds are checked before any strategy sees candidates.
Unlabelled observations are never converted into relevance or medical truth.
"""

import hashlib
import json
import math
import platform
import re
import time
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

from pydantic import Field

from backend.app.schemas import StrictModel
from backend.app.services.evidence_plan import build_evidence_plan, source_reasons
from backend.app.services.policy import check_policy
from backend.app.services.question_plan import plan_question
from backend.app.services.teaching import (
    canonical_teaching_text,
    safe_teaching_text,
    teaching_terms,
)
from research.evaluate.metrics import retrieval_metrics

UNAVAILABLE = {
    "B1": "controlled_generator_no_rag_arm_not_implemented",
    "B4": "audited_fixed_cross_encoder_unavailable",
    "B7": "trained_group_calibrated_fgrc_unavailable",
    "B8": "licensed_trained_lora_and_validated_b7_unavailable",
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Snapshot:
    def __init__(self, paths):
        self.paths = {name: Path(path) for name, path in paths.items()}
        self.hashes = {name: digest(path) for name, path in self.paths.items()}

    def verify(self):
        if self.hashes != {name: digest(path) for name, path in self.paths.items()}:
            raise ValueError("Experiment input/code/source/model/index changed during capture")


def create_output(path):
    Path(path).mkdir(parents=True, exist_ok=False)


class EvaluationPipelineConfig(StrictModel):
    run_id: str = Field(min_length=1)
    candidate_budget: int = Field(10, ge=1, le=30)
    rrf_constant: int = Field(60, ge=1)
    strategies: list[str] = Field(default_factory=lambda: ["B0", "B2", "B3", "B5", "B6"])
    source_version: str
    input_hashes: dict[str, str]
    generator: str = "none; exact extraction only"
    prompt: str = "none; no generated synthesis"
    quantization: str = "not_applicable"
    seed: int = 0
    independent_unseen: bool = False
    output_usage: str = "local_development_only; no clinical deployment"


def reciprocal_rank_fusion(rankings, limit, constant=60):
    if limit < 1 or constant < 1:
        raise ValueError("positive budget and RRF constant required")
    scores = Counter()
    for ranking in rankings:
        for rank, identity in enumerate(dict.fromkeys(ranking), 1):
            scores[identity] += 1 / (constant + rank)
    return sorted(scores, key=lambda identity: (-scores[identity], identity))[:limit]


def round_robin(rankings, limit):
    result = []
    for rank in range(max((len(rows) for rows in rankings), default=0)):
        for rows in rankings:
            if rank < len(rows) and rows[rank] not in result:
                result.append(rows[rank])
                if len(result) == limit:
                    return result
    return result


class RetrievalExperiment:
    def __init__(self, teacher, candidate_budget=10, dense_rank=None, rrf_constant=60):
        if not 1 <= candidate_budget <= 30 or rrf_constant < 1:
            raise ValueError("bounded positive candidate budget and RRF constant required")
        self.teacher, self.budget, self.dense_rank, self.rrf = teacher, candidate_budget, dense_rank, rrf_constant
        self.all_records = {row.chunk_id: row for row in teacher.records}
        self.records = {
            row.chunk_id: row for row in teacher.records
            if not source_reasons(row, teacher.metadata.get(row.chunk_id, {}))
            and row.chunk_id not in teacher.review_flags and safe_teaching_text(row.text)
        }
        # Term-frequency counts must come from tokens, not the deduplicated
        # teaching_terms set; canonical words are retained as the vocabulary.
        self.words = {key: Counter(word for word in re.findall(r"[a-z0-9]+", canonical_teaching_text(row.section + " " + row.text).casefold())
                                   if word in teaching_terms(row.section + " " + row.text)) for key, row in self.records.items()}
        self.lengths = {key: sum(counts.values()) for key, counts in self.words.items()}
        self.average_length = sum(self.lengths.values()) / max(1, len(self.lengths))
        self.frequencies = Counter(word for counts in self.words.values() for word in counts)

    def lexical(self, question):
        scores = {}
        query = teaching_terms(question)
        n = len(self.records)
        for key, counts in self.words.items():
            score = 0
            for term in query:
                frequency = counts[term]
                if frequency:
                    idf = math.log(1 + (n - self.frequencies[term] + 0.5) / (self.frequencies[term] + 0.5))
                    denominator = frequency + 1.2 * (1 - 0.75 + 0.75 * self.lengths[key] / max(1, self.average_length))
                    score += idf * frequency * 2.2 / denominator
            if score:
                scores[key] = score
        return sorted(scores, key=lambda key: (-scores[key], key))[:self.budget]

    def dense(self, question):
        if self.dense_rank is None:
            raise ValueError("frozen_dense_index_unavailable")
        return [key for key in dict.fromkeys(self.dense_rank(question, list(self.records))) if key in self.records][:self.budget]

    def hybrid(self, question):
        return reciprocal_rank_fusion([self.lexical(question), self.dense(question)], self.budget, self.rrf)

    def retrieve(self, question, strategy, context_topic=None):
        if strategy == "B0":
            return self.lexical(question)
        if strategy == "B2":
            return self.dense(question)
        if strategy == "B3":
            return self.hybrid(question)
        if strategy in {"B5", "B6"}:
            plan = plan_question(question, "study", context_topic=context_topic)
            rank = self.hybrid if self.dense_rank else self.lexical
            return round_robin([rank(facet.query) for facet in plan.facets], self.budget)
        raise ValueError("unsupported experimental strategy")

    def checked_answer(self, question, candidates, context_topic=None):
        from backend.app.services.answer_composer import compose
        from backend.app.services.output_validation import finalize

        plan = plan_question(question, "study", context_topic=context_topic)
        records = {key: self.records[key] for key in candidates}
        metadata = {key: self.teacher.metadata.get(key, {}) for key in candidates}
        # Crucially, direct reviewed-binding lookup sees only this fixed budget.
        scoped = SimpleNamespace(records=list(records.values()), metadata=metadata, review_flags={},
                                 version=self.teacher.version, units=[], references=SimpleNamespace(id_records=records),
                                 search=lambda query, limit=8: list(records.values())[:limit])
        evidence, selected = build_evidence_plan(plan, scoped, None, candidate_limit=self.budget)
        answer = compose(plan, evidence, selected, source_metadata=metadata)
        return finalize(question, answer, [], plan, metadata, {}, records)

    def validate_labels(self, case):
        if case.get("gold") is None and case.get("facet_gold") is None:
            return
        if case.get("label_origin") not in {"independent_author", "synthetic_mechanics"}:
            raise ValueError("explicit label provenance required")
        gold = case.get("gold")
        if not isinstance(gold, dict) or any(not isinstance(grade, int) or not 0 <= grade <= 3 for grade in gold.values()):
            raise ValueError("explicit graded gold required")
        labelled_ids = set(gold) | {key for ids in case.get("facet_gold", {}).values() for key in ids}
        if not labelled_ids <= set(self.all_records):
            raise ValueError("gold identity must resolve within pinned corpus")
        hashes = case.get("passage_hashes", {})
        if any(hashes.get(key) != self.all_records[key].content_hash() for key in labelled_ids):
            raise ValueError("gold evidence hashes must resolve exactly")

    def run_case(self, case, strategy):
        self.validate_labels(case)
        base = {"case_id": case["case_id"], "strategy": strategy, "major": case.get("major", "unknown"),
                "question_sha256": hashlib.sha256(case["question"].encode()).hexdigest(),
                "clinical_accuracy": None, "qualified_review": "pending", "independent_unseen": False}
        if strategy in UNAVAILABLE:
            return {**base, "status": "not_run", "reason": UNAVAILABLE[strategy]}
        if strategy in {"B2", "B3"} and self.dense_rank is None:
            return {**base, "status": "not_run", "reason": "frozen_dense_index_unavailable"}
        if check_policy(case["question"]):
            return {**base, "status": "excluded_policy", "reason": "personal_or_unsafe_prompt_not_an_educational_comparison"}
        started = time.perf_counter()
        candidates = self.retrieve(case["question"], strategy, case.get("context_topic"))
        metrics_case = {"ranked": candidates}
        for name in ("gold", "facet_gold"):
            if name in case:
                metrics_case[name] = case[name]
        result = {**base, "status": "captured", "stage": "guarded_exact_extraction" if strategy == "B6" else "retrieval_only",
                  "candidate_ids": candidates, "candidate_count": len(candidates), "candidate_budget": self.budget,
                  "candidate_hashes": {key: self.records[key].content_hash() for key in candidates},
                  "metrics": retrieval_metrics([metrics_case], self.budget),
                  "label_origin": case.get("label_origin"), "facet_retrieval": "hybrid" if self.dense_rank else "bm25"}
        if strategy == "B6":
            result["answer"] = self.checked_answer(case["question"], candidates, case.get("context_topic"))
        result["latency_ms"] = 1000 * (time.perf_counter() - started)
        return result


def run(experiment, config, cases, snapshot, output):
    if len({case["case_id"] for case in cases}) != len(cases) or not cases:
        raise ValueError("nonempty uniquely identified cases required")
    if config.input_hashes != snapshot.hashes:
        raise ValueError("configuration must pin exact snapshot")
    if config.candidate_budget != experiment.budget or config.rrf_constant != experiment.rrf:
        raise ValueError("configuration and runner budgets differ")
    if config.source_version != experiment.teacher.version or config.independent_unseen:
        raise ValueError("development runner must pin corpus version and cannot claim unseen")
    if any(strategy not in {"B0", "B2", "B3", "B5", "B6", *UNAVAILABLE} for strategy in config.strategies):
        raise ValueError("unknown strategy")
    for case in cases:
        experiment.validate_labels(case)
    snapshot.verify()
    create_output(output)
    output = Path(output)
    manifest = {"config": config.model_dump(), "status": "running", "environment": {"python": platform.python_version(), "platform": platform.platform()},
                "cases": len(cases), "corpus_records": len(experiment.all_records), "eligible_records": len(experiment.records),
                "clinical_accuracy": None, "independent_unseen": False,
                "limitations": ["B2/B3/B5 capture retrieval components only, not generated-answer baselines.",
                                "No model call, calibration, independent annotation, qualified review or hardware peak profile.",
                                "B6 exact extraction excludes all prepared explanations for controlled corpus comparison."]}
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    rows = []
    try:
        with (output / "predictions.jsonl").open("w", encoding="utf-8") as handle:
            for case in cases:
                for strategy in config.strategies:
                    row = experiment.run_case(case, strategy)
                    rows.append(row)
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        snapshot.verify()
    except Exception as error:
        manifest.update(status="invalid", failure_type=type(error).__name__)
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        raise
    summary = []
    for strategy in config.strategies:
        selected = [row for row in rows if row["strategy"] == strategy]
        captured = [row for row in selected if row["status"] == "captured"]
        answer_rows = [row["answer"] for row in captured if "answer" in row]
        summary.append({"strategy": strategy, "cases": len(selected), "captured": len(captured),
                        "status_counts": dict(Counter(row["status"] for row in selected)),
                        "reasons": dict(Counter(row["reason"] for row in selected if "reason" in row)),
                        "substantive_answers": sum(bool(row.get("claims")) for row in answer_rows),
                        "substantive_complete": sum(bool(row.get("claims")) and row.get("coverage_status") == "complete" for row in answer_rows),
                        "labelled_cases": sum(row["metrics"]["labelled_cases"] for row in captured),
                        "clinical_accuracy": None})
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    manifest.update(status="stable_during_capture", predictions_sha256=digest(output / "predictions.jsonl"))
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return summary
