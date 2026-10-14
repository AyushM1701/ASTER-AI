"""Isolated abstract benchmark. Never installs answer keys into retrieval."""
import argparse
import hashlib
import json
import random
import time
from pathlib import Path

import httpx

from backend.app.config import Settings
from backend.app.services.medical_evaluation import (
    benchmark_prompt,
    extract_prediction,
    score_pubmedqa,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20261010)
    args = parser.parse_args()
    if not 1 <= args.count <= 1000:
        parser.error("count must be between 1 and 1000")
    args.output.mkdir(parents=True, exist_ok=False)
    settings = Settings()
    with httpx.Client(timeout=300, trust_env=False, follow_redirects=False) as client:
        response = client.get("https://api.github.com/repos/pubmedqa/pubmedqa/commits/master")
        response.raise_for_status()
        revision = response.json()["sha"]
        origin = f"https://raw.githubusercontent.com/pubmedqa/pubmedqa/{revision}/"
        dataset = client.get(origin + "data/ori_pqal.json")
        dataset.raise_for_status()
        license_response = client.get(origin + "LICENSE")
        license_response.raise_for_status()
        args.output.joinpath("LICENSE").write_bytes(license_response.content)
        rows = dataset.json()
        ids = random.Random(args.seed).sample(sorted(rows), args.count)
        selected = {key: rows[key] for key in ids}
        args.output.joinpath("benchmark.json").write_text(json.dumps(selected), encoding="utf-8")
        metadata = {"publisher": "PubMedQA authors", "repository": "https://github.com/pubmedqa/pubmedqa", "revision": revision,
                    "sha256": hashlib.sha256(dataset.content).hexdigest(), "repository_license": "MIT",
                    "dataset": "PQA-L expert-labelled", "count": args.count, "seed": args.seed,
                    "ids": ids, "model": settings.text_model, "clinical_review": "pending",
                    "purpose": "development benchmark pilot, not a final holdout", "model_training_contamination": "unknown"}
        args.output.joinpath("provenance.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        tags = client.get(settings.ollama_base_url + "/api/tags")
        tags.raise_for_status()
        args.output.joinpath("model-snapshot.json").write_text(json.dumps(tags.json(), indent=2), encoding="utf-8")
        predictions, results = {}, []
        for key, row in selected.items():
            started = time.monotonic()
            try:
                response = client.post(settings.ollama_base_url + "/api/chat", json={"model": settings.text_model,
                    "messages": [{"role": "user", "content": benchmark_prompt(row)}], "stream": False,
                    "options": {"temperature": 0, "num_predict": 8, "num_ctx": 8192}})
                response.raise_for_status()
                raw = response.json()["message"]["content"]
                prediction = extract_prediction(raw)
                predictions[key] = prediction
                results.append({"id": key, "prediction": prediction, "raw": raw, "seconds": time.monotonic() - started})
            except (httpx.HTTPError, KeyError, ValueError) as exc:
                results.append({"id": key, "error_category": type(exc).__name__})
            args.output.joinpath("responses.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
            print(f"Completed {len(results)}/{args.count}", flush=True)
        args.output.joinpath("scores.json").write_text(json.dumps(score_pubmedqa(selected, predictions), indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
