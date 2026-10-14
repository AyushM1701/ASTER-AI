"""Measure photographed-topic retrieval; candidate matches are not coverage proof."""

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.config import Settings  # noqa: E402
from backend.app.services.teaching import TeachingStore  # noqa: E402


def evaluate(release, syllabus, output, index=None, explanations=None):
    if index:
        import torch

        torch.set_num_threads(2)
    release, syllabus = Path(release), Path(syllabus)
    explanation_path = Path(explanations) if explanations else release / "explanations.json"
    profile = dict(enable_teaching=True, teaching_release_path=release,
                   teaching_backend="hybrid" if index else "lexical",
                   teaching_explanations_sha256="")
    if index:
        profile["teaching_index_path"] = Path(index)
    if explanation_path.exists():
        profile.update(teaching_explanations_path=explanation_path,
                       teaching_explanations_sha256=hashlib.sha256(explanation_path.read_bytes()).hexdigest())
    store = TeachingStore(Settings(_env_file=None, **profile))
    if store.error:
        raise ValueError(store.error)
    document = json.loads(syllabus.read_text(encoding="utf-8"))
    results = []
    for topic in document["topics"]:
        question = "Explain " + topic["title"]
        # The uncertain handwriting is tested under a clearly recorded assumption.
        if topic.get("transcription_uncertainty"):
            question = "Explain probability, normal distribution and inferential statistics"
        answer = store.answer(question)
        candidates = store.search(question)
        results.append({"id": topic["id"], "area": topic["area"], "title": topic["title"], "question": question,
                        "transcription_uncertainty": topic.get("transcription_uncertainty"),
                        "runtime_status": (answer or {}).get("status", "not_handled"),
                        "candidates": [{"chunk_id": row.chunk_id, "source_id": row.source_id,
                                        "section": row.section, "url": row.url, "excerpt": row.text,
                                        "material_type": store.metadata.get(row.chunk_id, {}).get("material_type", "foundation"),
                                        "declared_syllabus_ids": store.metadata.get(row.chunk_id, {}).get("syllabus_ids", [])}
                                       for row in candidates],
                        "answer": answer, "material_review": "candidate_only_pending_inspection",
                        "completeness": None, "clinical_correctness": None, "faculty_review": "pending"})
    report = {"schema_version": 1, "release": store.manifest(),
              "manifest_sha256": hashlib.sha256((release / "manifest.json").read_bytes()).hexdigest(),
              "syllabus_sha256": hashlib.sha256(syllabus.read_bytes()).hexdigest(),
              "topic_count": len(results), "runtime_statuses": dict(Counter(row["runtime_status"] for row in results)),
              "interpretation": "A response or lexical candidate is not verified syllabus coverage. Full-topic completeness and faculty correctness are unmeasured.",
              "topics": results}
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    store.close()
    return {key: value for key, value in report.items() if key != "topics"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--syllabus", type=Path, default=ROOT / "configs/mds_syllabus.json")
    parser.add_argument("--index", type=Path)
    parser.add_argument("--explanations", type=Path, help="Explicit baseline paired notes when they are stored outside the release")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(evaluate(args.release, args.syllabus, args.output, args.index, args.explanations), indent=2))
