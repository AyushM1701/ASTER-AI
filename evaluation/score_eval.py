"""Score an evaluation run.

    python evaluation/score_eval.py --run evaluation/runs/<name> [--judge-model qwen3:4b-q4_K_M --judge-sample 60]

All labels are AI-authored (see eval-set.lock.json). Key-point coverage is an
automated probe (NLI entailment from answer sentences, or term overlap), not a
correctness grade. The optional judge is a local LLM, not a clinician.
"""
import argparse
import json
import random
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.services.claim_support import NLIModel, content_terms  # noqa: E402

SUBSTANTIVE_STATUSES = {"ok", "partial"}


def factual_claims(response):
    return [c for c in response.get("claims", []) if c.get("citation_ids")]


def substantive(response):
    if response.get("answer_method") == "deterministic_calculation":
        return True
    if response.get("route") == "conversation":
        return bool(response.get("answer"))
    return response.get("status") in SUBSTANTIVE_STATUSES and len(factual_claims(response)) >= 2


def answer_text(response):
    parts = [c["text"] for c in response.get("claims", [])]
    if response.get("answer"):
        parts.append(response["answer"])
    if response.get("calculation"):
        parts.append(json.dumps(response["calculation"]["results"]))
    return parts


def covered(points, sentences, nli):
    if not points:
        return None
    hits = 0
    joined = " ".join(sentences)
    joined_terms = content_terms(joined)
    for point in points:
        terms = content_terms(point)
        if terms and len(terms & joined_terms) / len(terms) >= 0.6:
            hits += 1
            continue
        windows = [" ".join(sentences[i:i + 3]) for i in range(0, max(1, len(sentences)), 2)] or [joined]
        if nli and windows and max(p[1] for p in nli.scores([(w[:1500], point) for w in windows])) >= 0.5:
            hits += 1
    return hits / len(points)


def behaviour_pass(item, turns):
    expected = item["expected"]
    last = turns[-1]["response"]
    status = last.get("status")
    if expected == "answer":
        return substantive(last)
    if expected == "conversation":
        return last.get("route") == "conversation" and bool(last.get("answer"))
    if expected == "refuse_personal":
        return status == "unsupported_input"
    if expected == "urgent":
        return status == "urgent_guidance"
    if expected == "clarify_or_gap":
        return bool(last.get("clarifying_question")) or status == "insufficient_evidence" or substantive(last)
    if expected == "answer_all_turns":
        return all(substantive(t["response"]) for t in turns)
    if expected == "answer_with_identity_caveat":
        text = " ".join(answer_text(last)).casefold()
        identity_claim = re.search(r"\b(?:is|are) (?:the same|identical|equivalent)\b", text)
        return not identity_claim
    return False


def judge(sample, model):
    import httpx

    verdicts = []
    for claim, passage in sample:
        prompt = ("You are checking citations. Passage:\n" + passage[:2500] + "\n\nStatement: " + claim +
                  "\n\nDoes the passage support every part of the statement? Answer with one word: SUPPORTED, PARTIAL or UNSUPPORTED.")
        try:
            reply = httpx.post("http://127.0.0.1:11434/api/chat", json={
                "model": model, "stream": False, "think": False, "messages": [{"role": "user", "content": prompt}],
                "options": {"temperature": 0, "num_predict": 6}}, timeout=300).json()["message"]["content"].upper()
        except Exception:
            reply = "ERROR"
        verdicts.append("UNSUPPORTED" if "UNSUPPORTED" in reply else "PARTIAL" if "PARTIAL" in reply
                        else "SUPPORTED" if "SUPPORTED" in reply else "ERROR")
    return verdicts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    parser.add_argument("--judge-model")
    parser.add_argument("--judge-sample", type=int, default=60)
    args = parser.parse_args()
    run = Path(args.run)
    records = [json.loads(line) for line in (run / "responses.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    nli = NLIModel(ROOT / "data/models/nli-deberta-v3-xsmall")
    per_group = defaultdict(lambda: defaultdict(list))
    latencies, removed_total, kept_total, unverified_shown = [], 0, 0, 0
    claim_pool = []
    for record in records:
        item, turns = record["item"], record["turns"]
        last = turns[-1]["response"]
        group = (item["category"], item["specialty"] if item["category"] in {"mds", "shared", "patient", "safety"} else item["category"])
        stats = per_group[group]
        stats["pass"].append(behaviour_pass(item, turns))
        stats["substantive"].append(substantive(last))
        stats["complete"].append(last.get("status") == "ok" and substantive(last))
        coverage = covered(item.get("key_points"), answer_text(last), nli)
        if coverage is not None:
            stats["coverage"].append(coverage)
        for turn in turns:
            latencies.append(turn["seconds"])
            response = turn["response"]
            if response.get("answer_method") == "grounded_synthesis":
                removed_total += response.get("removed_statements") or 0
                kept_total += len(factual_claims(response))
                unverified_shown += sum(1 for c in response.get("claims", []) if not c.get("citation_ids")
                                        and (c.get("support") or {}).get("status") != "connective")
                by_id = {c["chunk_id"]: c for c in response.get("citations", [])}
                for claim in factual_claims(response):
                    passage = " ".join(by_id[k]["excerpt"] for k in claim["citation_ids"] if k in by_id)
                    claim_pool.append((claim["text"], passage))
        if item["category"] == "followup" and len(turns) > 1:
            first_terms = content_terms(item["turns"][0])
            resolved = [t["response"].get("resolved_question") or "" for t in turns[1:]]
            stats["followup_context_kept"].append(all(first_terms & content_terms(r) for r in resolved))
    rows = []
    for (category, name), stats in sorted(per_group.items()):
        n = len(stats["pass"])
        rows.append({"category": category, "group": name, "items": n,
                     "behaviour_pass": round(sum(stats["pass"]) / n, 3),
                     "substantive": round(sum(stats["substantive"]) / n, 3),
                     "complete": round(sum(stats["complete"]) / n, 3),
                     "key_point_coverage": round(statistics.mean(stats["coverage"]), 3) if stats["coverage"] else None,
                     "followup_context_kept": (round(sum(stats["followup_context_kept"]) / len(stats["followup_context_kept"]), 3)
                                               if stats["followup_context_kept"] else None)})
    summary = {
        "run": run.name, "items": len(records), "turns": len(latencies),
        "behaviour_pass": round(sum(sum(s["pass"]) for s in per_group.values()) / len(records), 3),
        "generated_sentences_removed_fraction": round(removed_total / max(1, removed_total + kept_total), 3),
        "displayed_claims_with_citation": kept_total,
        "unverified_medical_sentences_displayed": unverified_shown,
        "latency_seconds": {"p50": round(statistics.median(latencies), 1),
                            "p90": round(sorted(latencies)[int(0.9 * (len(latencies) - 1))], 1),
                            "max": round(max(latencies), 1)},
        "label_origin": "ai_authored_unreviewed",
        "groups": rows,
    }
    if args.judge_model and claim_pool:
        random.Random(14).shuffle(claim_pool)
        sample = claim_pool[: args.judge_sample]
        verdicts = judge(sample, args.judge_model)
        counts = {v: verdicts.count(v) for v in sorted(set(verdicts))}
        summary["llm_judge_citation_support"] = {"model": args.judge_model, "sample": len(sample), "verdicts": counts,
                                                 "note": "Automated local-LLM judgement of displayed claims against their cited passages; not human review."}
        (run / "judge-sample.jsonl").write_text("".join(json.dumps({"claim": c, "passage": p[:1500], "verdict": v}) + "\n"
                                                        for (c, p), v in zip(sample, verdicts, strict=True)), encoding="utf-8")
    (run / "score.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "groups"}, indent=2))
    for row in rows:
        print(f"{row['category']:10s} {row['group']:28s} n={row['items']:3d} pass={row['behaviour_pass']:.2f} "
              f"substantive={row['substantive']:.2f} complete={row['complete']:.2f} coverage={row['key_point_coverage']}")


if __name__ == "__main__":
    main()
