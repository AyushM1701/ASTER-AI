"""Controlled local source-to-answer comparison; never a clinical accuracy score.

Only supplied factual synopses are used. The deterministic rubric recognizes bounded
relations and explicit contradictions; it does not establish general truth or assess
unmapped prose semantically. Faculty review remains unavailable.
"""

import argparse
import hashlib
import json
import platform
import re
import statistics
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import psutil
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.config import Settings  # noqa: E402


def answer_schema():
    return {
        "type": "object", "additionalProperties": False,
        "required": ["plain_explanation", "mbbs_detail", "facts", "limitations", "mcq_choice", "evidence_available"],
        "properties": {
            "plain_explanation": {"type": "string"}, "mbbs_detail": {"type": "string"},
            "limitations": {"type": "string"}, "mcq_choice": {"type": ["string", "null"]},
            "evidence_available": {"type": "boolean"},
            "facts": {"type": "array", "items": {
                "type": "object", "additionalProperties": False,
                "required": ["claim", "source_id", "evidence_quote"],
                "properties": {key: {"type": "string"} for key in ("claim", "source_id", "evidence_quote")},
            }},
        },
    }


def decode_answer(content):
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate field: {key}")
            result[key] = value
        return result

    try:
        data = json.loads(content, object_pairs_hook=unique_object)
    except json.JSONDecodeError as exc:
        raise ValueError("Response is not one JSON object") from exc
    except TypeError as exc:
        raise ValueError("Response content is not JSON text") from exc
    expected = set(answer_schema()["required"])
    if not isinstance(data, dict) or set(data) != expected:
        raise ValueError("Answer fields do not match the fixed schema")
    for key in ("plain_explanation", "mbbs_detail", "limitations"):
        if not isinstance(data[key], str):
            raise ValueError(f"{key} must be a string")
    if type(data["evidence_available"]) is not bool:
        raise ValueError("evidence_available must be a boolean")
    if data["mcq_choice"] is not None and not isinstance(data["mcq_choice"], str):
        raise ValueError("mcq_choice must be a string or null")
    if not isinstance(data["facts"], list):
        raise ValueError("facts must be an array")
    for fact in data["facts"]:
        keys = {"claim", "source_id", "evidence_quote"}
        if not isinstance(fact, dict) or set(fact) != keys or any(not isinstance(fact[key], str) for key in keys):
            raise ValueError("Every fact needs claim, source_id and evidence_quote strings")
    return data


def normalize(text):
    return re.sub(r"\s+", " ", text.lower().replace("\u2019", "'")).strip()


def matches(patterns, text):
    return any(re.search(pattern, sentence, flags=re.I) for sentence in re.split(r"[.!?]", normalize(text)) for pattern in patterns)


def negates_relation(fact, text):
    if fact.get("allows_negation", False):
        return False
    for sentence in re.split(r"[.!?]", normalize(text)):
        for pattern in fact["patterns"]:
            for match in re.finditer(pattern, sentence, flags=re.I):
                scope = sentence[max(0, match.start() - 40):match.end()]
                scope = scope.replace("not enough insulin", "insufficient insulin")
                if re.search(r"\b(?:not|never|cannot|can't|don't|doesn't|false)\b", scope):
                    return True
    return False


def score_answer(case, data):
    # Claims, not cited source quotes, determine fact recall. This prevents copying
    # evidence into a wrong answer from manufacturing a correct score.
    claims = data["facts"]
    refs = {ref["id"]: ref for ref in case["references"]}
    prose = " ".join([data["plain_explanation"], data["mbbs_detail"], data["limitations"], *(claim["claim"] for claim in claims)])
    contradicted = [fact["id"] for fact in case["facts"] if matches(fact.get("contradictions", []), prose) or negates_relation(fact, prose)]
    covered, supported, unmapped = set(), 0, []
    for i, claim in enumerate(claims):
        mapped = [fact["id"] for fact in case["facts"] if matches(fact["patterns"], claim["claim"]) and fact["id"] not in contradicted]
        covered.update(mapped)
        ref = refs.get(claim["source_id"])
        quote = normalize(claim["evidence_quote"])
        # A real quote must itself support at least one matched relational fact.
        quote_mapped = [fact["id"] for fact in case["facts"] if matches(fact["patterns"], quote)]
        if ref and quote and quote in normalize(ref["passage"]) and set(mapped) & set(quote_mapped):
            supported += 1
        if not mapped:
            unmapped.append(i)
    missing = [fact["id"] for fact in case["facts"] if fact["id"] not in covered]
    recall = len(covered) / len(case["facts"]) if case["facts"] else None
    support = supported / len(claims) if claims else None
    mcq = data["mcq_choice"] == case["mcq_answer"] if case.get("mcq_answer") else None
    abstention = None
    if not case["supported"]:
        abstention = data["evidence_available"] is False and not claims and matches(
            [r"(?:insufficient|unavailable|unsupported|not (?:enough|support)|do(?:es)? not support|lack.{0,15}evidence|cannot.{0,40}(?:reference|evidence))"], prose
        ) and data["mcq_choice"] is None
    passed = abstention if abstention is not None else (
        data["evidence_available"] is True and not missing and not contradicted and not unmapped
        and bool(claims) and support == 1 and mcq is not False
    )
    return {
        "bounded_reference_pass": bool(passed), "required_fact_recall": recall,
        "citation_quote_support": support, "missing_facts": missing,
        "contradicted_facts": contradicted, "unmapped_claims": unmapped,
        "mcq_agreement": mcq, "unsupported_abstention": abstention,
        "clinical_correctness": None, "faculty_review": "not_performed",
        "metric_scope": "Developer-defined relational lexical reference agreement and exact quote support; not a semantic truth or clinical judgement.",
    }


def make_request(model, case, controls):
    sources = "\n".join(f"[{ref['id']}] {ref['passage']}" for ref in case["references"]) or "No relevant reference passage supplied."
    system = (
        "You teach an MBBS student from supplied references only. Explain plainly first, then give supported academic detail. "
        "Return the required JSON. Each fact must be a full relational claim with a source_id and a verbatim evidence_quote "
        "from the supplied passage that supports it. Include all facts needed to answer the question. Do not introduce "
        "outside facts or clinical prescriptions. All substantive explanatory claims must also appear in facts. "
        "If evidence is insufficient, set evidence_available false, facts empty, say the references do not support the answer, "
        "and do not guess. Set mcq_choice to the option letter for an MCQ, otherwise null. Educational fictional cases "
        "are for reasoning only; never prescribe a personal dose. /no_think"
    )
    return {
        "model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": f"References:\n{sources}\n\nQuestion: {case['question']}"}],
        "format": answer_schema(), "stream": False, "think": False,
        "options": controls, "keep_alive": "5m",
    }


def record_response(model, digest, case, raw, wall_seconds, resources, error=None):
    message = raw.get("message")
    content = message.get("content", "") if isinstance(message, dict) else ""
    data, score = None, {"bounded_reference_pass": False, "clinical_correctness": None, "faculty_review": "not_performed"}
    if error is None:
        try:
            data = decode_answer(content)
            score = score_answer(case, data)
        except ValueError as exc:
            error = {"type": "invalid_structured_output", "message": str(exc)}
        if raw.get("done") is not True or raw.get("done_reason") != "stop":
            error = {"type": "incomplete_generation", "message": f"done={raw.get('done')}, reason={raw.get('done_reason')}"}
            score["bounded_reference_pass"] = False
    eval_seconds = raw.get("eval_duration", 0) / 1e9
    return {
        "schema_version": 1, "case_id": case["id"], "subject": case["subject"], "question_type": case["question_type"],
        "model": model, "model_digest": digest, "raw_response": raw, "decoded_answer": data,
        "wall_seconds": wall_seconds, "load_seconds": raw.get("load_duration", 0) / 1e9,
        "prompt_eval_seconds": raw.get("prompt_eval_duration", 0) / 1e9,
        "output_tokens": raw.get("eval_count"), "output_tokens_per_second": raw.get("eval_count", 0) / eval_seconds if eval_seconds else None,
        "resources": resources, "score": score, "error": error,
    }


def write_artifact(path, data):
    encoded = (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(encoded)
    return hashlib.sha256(encoded).hexdigest()


class ProcessSampler:
    """Sample only the identified local Ollama service and its descendants."""

    def __init__(self, pid):
        self.pid = pid
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._sample, daemon=True)
        self.peak = 0
        self.min_available = psutil.virtual_memory().available
        self.cpu_initial, self.cpu_last, self.observed = {}, {}, set()
        self.samples = 0

    def _sample(self):
        while not self.stop.is_set():
            total = 0
            try:
                parent = psutil.Process(self.pid)
                processes = [parent, *parent.children(recursive=True)]
            except psutil.Error:
                processes = []
            for process in processes:
                try:
                    total += process.memory_info().rss
                    times = process.cpu_times()
                    seconds = times.user + times.system
                    self.cpu_initial.setdefault(process.pid, seconds)
                    self.cpu_last[process.pid] = seconds
                    self.observed.add(process.pid)
                except psutil.Error:
                    continue
            self.peak = max(self.peak, total)
            self.min_available = min(self.min_available, psutil.virtual_memory().available)
            self.samples += 1
            self.stop.wait(0.25)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_args):
        self.stop.set()
        self.thread.join()

    def result(self):
        return {
            "peak_working_set_bytes": self.peak, "min_system_available_bytes": self.min_available,
            "cpu_seconds": sum(self.cpu_last[pid] - initial for pid, initial in self.cpu_initial.items()),
            "process_ids": sorted(self.observed), "sample_count": self.samples, "sample_interval_seconds": 0.25,
            "limitations": "Sum of sampled process working sets may double-count shared pages, misses subinterval peaks; GPU VRAM is separate. CPU deltas miss process start before first observation and short-lived processes.",
        }


def local_server_pid(base_url):
    from urllib.parse import urlsplit
    port = urlsplit(base_url).port or 80
    candidates = [conn.pid for conn in psutil.net_connections(kind="tcp") if conn.status == psutil.CONN_LISTEN and conn.laddr.port == port]
    if len(set(candidates)) != 1 or candidates[0] is None:
        raise RuntimeError("Cannot uniquely identify loopback Ollama server process")
    process = psutil.Process(candidates[0])
    if "ollama" not in process.name().lower():
        raise RuntimeError("Configured loopback listener is not identified as Ollama")
    return process.pid


def preflight_models(config, models):
    for model in config["models"]:
        if model not in models:
            raise RuntimeError(f"Required model is not installed: {model}")
        if not models[model]["digest"].startswith(config["expected_digest_prefixes"][model]):
            raise RuntimeError(f"Registry digest differs from pinned expected model: {model}")


def run(config_path, output_root):
    config = json.loads(config_path.read_text(encoding="utf-8"))
    settings = Settings()
    base = settings.ollama_base_url
    session = requests.Session()
    session.trust_env = False
    version = session.get(base + "/api/version", timeout=10).json()
    tags_response = session.get(base + "/api/tags", timeout=10)
    tags_response.raise_for_status()
    models = {tag["name"]: tag for tag in tags_response.json()["models"]}
    preflight_models(config, models)
    pid = local_server_pid(base)
    # Exclusive timestamped directory; earlier evidence is never overwritten.
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out = output_root / stamp
    out.mkdir(parents=True, exist_ok=False)
    metadata = {
        "schema_version": 1, "started_utc": stamp, "ollama_url": base, "ollama_version": version,
        "server_pid": pid, "platform": platform.platform(), "logical_cpu_count": psutil.cpu_count(),
        "ram_total_bytes": psutil.virtual_memory().total, "ram_available_start_bytes": psutil.virtual_memory().available,
        "disk_free_bytes": psutil.disk_usage(str(ROOT)).free,
        "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        "controls": config["controls"], "model_selection": config["model_selection"],
        "faculty_review": "not_performed", "clinical_correctness": None,
        "limitations": config["limitations"], "model_metadata": {},
    }
    hashes = {"config.snapshot.json": write_artifact(out / "config.snapshot.json", config)}
    rows = []
    for model in config["models"]:
        show = session.post(base + "/api/show", json={"model": model}, timeout=30)
        show.raise_for_status()
        info = show.json()
        metadata["model_metadata"][model] = {"tag": models[model], "details": info.get("details"), "capabilities": info.get("capabilities"), "license": info.get("license"), "model_info": info.get("model_info")}
        for index, case in enumerate(config["cases"]):
            request = make_request(model, case, config["controls"])
            raw, error = {}, None
            start = time.perf_counter()
            with ProcessSampler(pid) as sampler:
                try:
                    response = session.post(base + "/api/chat", json=request, timeout=(10, config["timeout_seconds"]))
                    response.raise_for_status()
                    raw = response.json()
                    if raw.get("error"):
                        error = {"type": "ollama_error", "message": str(raw["error"])}
                except (requests.RequestException, ValueError) as exc:
                    error = {"type": type(exc).__name__, "message": str(exc)}
                wall = time.perf_counter() - start
            resources = sampler.result()
            try:
                resources["loaded_model_state"] = session.get(base + "/api/ps", timeout=10).json()
            except requests.RequestException:
                resources["loaded_model_state"] = None
            row = record_response(model, models[model]["digest"], case, raw, wall, resources, error)
            row["request"] = request
            row["cold_or_warm"] = "first_prompt_model_load" if index == 0 else "subsequent_prompt"
            name = f"{model.replace(':', '_')}-{index + 1:02d}-{case['id']}.json"
            hashes[name] = write_artifact(out / name, row)
            rows.append(row)
            print(json.dumps({"model": model, "case": case["id"], "seconds": round(wall, 2), "pass": row["score"]["bounded_reference_pass"], "error": error}), flush=True)
        # Release only the benchmarked model's cache before the next comparison.
        unload = session.post(base + "/api/generate", json={"model": model, "keep_alive": 0}, timeout=30)
        unload.raise_for_status()
    summary = {"models": {}, "clinical_correctness": None, "faculty_review": "not_performed", "limitations": config["limitations"]}
    for model in config["models"]:
        selected = [row for row in rows if row["model"] == model]
        rates = [row["output_tokens_per_second"] for row in selected if row["output_tokens_per_second"] is not None]
        summary["models"][model] = {
            "cases": len(selected), "bounded_reference_passes": sum(row["score"]["bounded_reference_pass"] for row in selected),
            "errors": sum(row["error"] is not None for row in selected),
            "median_wall_seconds": statistics.median(row["wall_seconds"] for row in selected),
            "median_warm_wall_seconds": statistics.median(row["wall_seconds"] for row in selected[1:]),
            "first_load_seconds": selected[0]["load_seconds"],
            "median_output_tokens_per_second": statistics.median(rates) if rates else None,
            "peak_process_working_set_bytes": max(row["resources"]["peak_working_set_bytes"] for row in selected),
            "min_system_available_bytes": min(row["resources"]["min_system_available_bytes"] for row in selected),
            "runtime_gpu_offload_bytes": max((model_state.get("size_vram", 0) for row in selected for model_state in (row["resources"].get("loaded_model_state") or {}).get("models", [])), default=0),
        }
    hashes["metadata.json"] = write_artifact(out / "metadata.json", metadata)
    hashes["summary.json"] = write_artifact(out / "summary.json", summary)
    write_artifact(out / "manifest.json", {"sha256": hashes, "finished_utc": datetime.now(timezone.utc).isoformat()})
    print(json.dumps({"artifact_directory": str(out), "summary": summary}, indent=2), flush=True)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/mbbs_model_benchmark.json")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/evaluation/mbbs-v1/model-benchmark")
    args = parser.parse_args()
    run(args.config, args.output)


if __name__ == "__main__":
    main()
