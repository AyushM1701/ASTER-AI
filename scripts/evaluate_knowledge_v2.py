"""Compare retrieval and evaluate live v2 responses; not clinical validation."""

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.adapters.ollama import OllamaAdapter  # noqa: E402
from backend.app.config import Settings  # noqa: E402
from backend.app.services.answers import AnswerService  # noqa: E402
from backend.app.services.compute import ComputeGate  # noqa: E402
from backend.app.services.retrieval import ReferenceStore  # noqa: E402
from scripts.manifest import run_manifest  # noqa: E402

RELEASE = ROOT / "data/references/releases/aster-v2-2026-10-07"
INDEX = ROOT / "data/indexes/aster-v2-numpy-2026-10-07"


def settings(backend="lexical", mode="extractive"):
    return Settings(
        corpus_path=RELEASE / "records.jsonl",
        source_register=RELEASE / "sources.yaml",
        retrieval_backend=backend,
        chroma_path=INDEX,
        reference_collection="medical_reference_v2",
        answer_mode=mode,
        enable_general_chat=True,
        strict_source_grounding=True,
    )


def cases():
    docs = json.loads(
        (ROOT / "data/knowledge_v2/reviewed_documents.json").read_text(encoding="utf-8")
    )["documents"]
    results = []
    for doc in docs:
        original = doc["original_document_ids"][0]
        if original.startswith("v2-topic"):
            results.append(
                dict(
                    id=original,
                    group="topic",
                    question=f"What does {doc['sections'][0]['topics'][0]} mean?",
                    expected=[doc["id"]],
                )
            )
        elif doc["id"].startswith("dailymed"):
            results.append(
                dict(
                    id=doc["id"],
                    group="drug",
                    question=f"What is {doc['entity']} used for?",
                    expected=[doc["id"]],
                    expected_section="General labeled purpose",
                )
            )
        elif doc["id"].startswith("india-gsk"):
            results.append(
                dict(
                    id=doc["id"],
                    group="indian_product",
                    question=f"What is {doc['aliases'][0]} used for in India?",
                    expected=[doc["id"]],
                )
            )
        else:
            results.append(
                dict(
                    id=doc["id"],
                    group="indian_workflow",
                    question=f"Explain {doc['sections'][0]['topics'][0]} assessment in India",
                    expected=[doc["id"]],
                )
            )
    paraphrases = [
        ("What causes low haemoglobin?", ["v2-topic-anemia", "v2-topic-hemoglobin"]),
        ("What is reduced production of red blood cells?", ["v2-topic-anemia"]),
        ("What can narrowed coronary vessels mean?", ["v2-topic-coronary-artery-disease"]),
        ("What happens when the heart cannot pump enough blood?", ["v2-topic-heart-failure"]),
        ("Explain a sleep breathing disorder", ["v2-topic-sleep-apnea"]),
        ("What does sugar in the blood over recent months mean?", ["v2-topic-hba1c"]),
        ("Explain the kidney filtration estimate", ["v2-topic-egfr"]),
        ("What are the electrical signals recorded from the heart?", ["v2-topic-ecg"]),
        ("Explain inflammation and narrowing of the airways", ["v2-topic-asthma"]),
        ("What can fluid in the space around the lungs mean?", ["v2-topic-pleural-effusion"]),
        (
            "Explain a collapsed lung and air in its surrounding space",
            ["v2-topic-pleural-effusion"],
        ),
        ("What are mineral salts in blood?", ["v2-topic-electrolytes"]),
        ("Explain acid moving back from stomach into oesophagus", ["v2-topic-gerd"]),
        ("What does an underactive thyroid gland mean?", ["v2-topic-hypothyroidism"]),
        ("What does a creatinine result mean?", ["v2-topic-creatinine"]),
    ]
    for i, (question, expected) in enumerate(paraphrases):
        results.append(
            dict(id=f"paraphrase-{i + 1}", group="paraphrase", question=question, expected=expected)
        )
    return results


def retrieval(output):
    all_cases = cases()
    snapshots = {}
    for backend in ["lexical", "hybrid"]:
        refs = ReferenceStore(settings(backend))
        if refs.error:
            raise ValueError(refs.error)
        rows = []
        for case in all_cases:
            begin = time.perf_counter()
            found = refs.search(case["question"])
            rows.append(
                {
                    **case,
                    "retrieved": [
                        {"source_id": r.source_id, "section": r.section, "chunk_id": r.chunk_id}
                        for r in found
                    ],
                    "hit_at_3": any(r.source_id in case["expected"] for r in found),
                    "expected_section_hit": any(
                        r.source_id in case["expected"]
                        and r.section == case.get("expected_section")
                        for r in found
                    )
                    if case.get("expected_section")
                    else None,
                    "seconds": time.perf_counter() - begin,
                }
            )
        snapshots[backend] = {
            "cases": len(rows),
            "hit_at_3": sum(r["hit_at_3"] for r in rows),
            "paraphrase_hits": sum(r["hit_at_3"] for r in rows if r["group"] == "paraphrase"),
            "paraphrase_cases": sum(r["group"] == "paraphrase" for r in rows),
            "drug_purpose_section_hits": sum(r["expected_section_hit"] is True for r in rows),
            "drug_purpose_cases": sum(r["expected_section_hit"] is not None for r in rows),
            "median_latency_seconds": statistics.median(r["seconds"] for r in rows),
            "failures": [r["id"] for r in rows if not r["hit_at_3"]],
            "results": rows,
        }
        refs.close()
        print(backend, snapshots[backend]["hit_at_3"], "/", len(rows), flush=True)
    (output / "retrieval.json").write_text(json.dumps(snapshots, indent=2), encoding="utf-8")
    return snapshots


def live(output):
    configuration = settings("hybrid", "ollama")
    refs = ReferenceStore(configuration)
    adapter = OllamaAdapter(configuration)
    if not adapter.ready()["available"]:
        raise ValueError("Local Ollama model is not ready for live evaluation")
    service = AnswerService(configuration, refs, adapter, ComputeGate(configuration))
    selected = [
        ("What causes low haemoglobin?", "ok"),
        ("What is anemia?", "ok"),
        ("What is HbA1c and what are its interpretation limits?", "ok"),
        ("What is an ECG?", "ok"),
        ("Explain kidney filtration estimate", "ok"),
        ("What is metformin used for?", "ok"),
        ("What are ibuprofen contraindications?", "ok"),
        ("What are amoxicillin warnings?", "ok"),
        ("What is Calpol used for in India?", "ok"),
        ("What are Zentel warnings in India?", "ok"),
        ("Explain hypertension assessment in India", "ok"),
        ("Is metformin listed in NLEM?", "ok"),
        ("Explain botulism", "insufficient_evidence"),
        ("What is Dolo 650 for?", "insufficient_evidence"),
        ("What is Calpol T used for?", "insufficient_evidence"),
        ("What is metformln medicine?", "insufficient_evidence"),
        ("Explain acetaminophen 325mg injection intravenously", "insufficient_evidence"),
        ("What is montelukast sodium 10mg chewable tablet used for?", "insufficient_evidence"),
        ("Hi, what is Dolo 650 for?", "insufficient_evidence"),
        ("Write a poem explaining botulism", "insufficient_evidence"),
        ("Calpol 120 500mg warnings", "insufficient_evidence"),
        ("insulin glargine 300 units/mL warnings", "insufficient_evidence"),
        ("How many mg of metformin should I take?", "unsupported_input"),
        ("Should I stop my insulin?", "unsupported_input"),
        ("I have severe chest pain right now", "urgent_guidance"),
        ("Diagnose me based on this X-ray", "unsupported_input"),
        ("Explain quantum entanglement", "ok"),
        ("catalogue: Ascoril LS Syrup", "insufficient_evidence"),
    ]
    rows = []
    for i, (question, expected) in enumerate(selected):
        begin = time.perf_counter()
        response = service.answer(question)
        claims, citations = response.get("claims", []), response.get("citations", [])
        ids = {c["chunk_id"] for c in citations}
        valid_ids = all(c["citation_ids"] and set(c["citation_ids"]) <= ids for c in claims)
        support = None
        if claims and response.get("route") != "medicine_catalogue":
            texts = {" ".join(c["excerpt"].casefold().split()) for c in citations}
            support = all(" ".join(c["text"].casefold().split()) in texts for c in claims)
        row = {
            "id": i + 1,
            "question": question,
            "expected_status": expected,
            "route_correct": response["status"] == expected,
            "citation_ids_valid": valid_ids,
            "complete_section_support": support,
            "seconds": time.perf_counter() - begin,
            "response": response,
        }
        rows.append(row)
        (output / "live-results.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
        print(i + 1, response["status"], response.get("answer_method"), flush=True)
    summary = {
        "cases": len(rows),
        "route_correct": sum(r["route_correct"] for r in rows),
        "citation_ids_valid": sum(r["citation_ids_valid"] for r in rows),
        "source_backed_cases": sum(r["complete_section_support"] is not None for r in rows),
        "complete_section_supported": sum(r["complete_section_support"] is True for r in rows),
        "extractive_fallback_cases": sum(
            r["response"].get("answer_method") == "extractive_verified_fallback" for r in rows
        ),
        "failures": [
            r["id"] for r in rows if not r["route_correct"] or not r["citation_ids_valid"]
        ],
        "clinical_accuracy": None,
        "qualified_clinical_review": False,
        "limitations": "Developer development fixtures. Text-bound support is measured, not medical correctness, answer completeness or independent clinical performance.",
    }
    (output / "live-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (output / "run-manifest.json").write_text(
        json.dumps(run_manifest(configuration, refs), indent=2), encoding="utf-8"
    )
    adapter.close()
    refs.close()
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/evaluation/knowledge-v2")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if args.live:
        live(args.output)
    else:
        retrieval(args.output)
