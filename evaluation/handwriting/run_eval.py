"""Score prescription transcription on the synthetic handwritten-style set.

    python evaluation/handwriting/run_eval.py --api http://127.0.0.1:8100 --set D:/aster-eval/handwriting/set --out evaluation/runs/handwriting-<name>
    # re-run selected images into an existing run (summary is recomputed from all records):
    python evaluation/handwriting/run_eval.py ... --files synthetic-hw-026.png synthetic-hw-046.png

Per critical field: correct, wrong (a value that differs from the truth — the
dangerous outcome) or abstained (left unreadable for the user to fill in).
Lines naming the same medicine are paired in reading order (first truth line with
the first read group of that name, and so on).
"""
import argparse
import json
import re
import time
from collections import Counter, defaultdict
from pathlib import Path

import httpx

CRITICAL = ["medicine_name", "strength", "frequency", "duration"]
LABEL_ORIGIN = "synthetic_generated (rendered handwriting fonts, not real handwriting)"


def norm(value):
    return re.sub(r"[\s.]+", "", (value or "").casefold()).replace("for", "x")


def groups_from(fields):
    groups = defaultdict(dict)
    for field in fields:
        prefix = "_".join(field["field_id"].split("_")[:2])
        groups[prefix][field["kind"]] = field.get("candidate_value")
    return list(groups.values())


def score(truth_lines, groups):
    """Pair each truth line with an unused read group of the same medicine, in reading order."""
    used, pairs = set(), {}
    for t, truth in enumerate(truth_lines):
        index = next((i for i, g in enumerate(groups)
                      if i not in used and norm(g.get("medicine_name")) == norm(truth["medicine_name"])), None)
        if index is not None:
            used.add(index)
            pairs[t] = index
    # A misread name ("Letirizine" for Cetirizine) is a wrong value shown to the user, not an abstention:
    # pair leftover truth lines with leftover named groups in reading order and score them too.
    leftover = [i for i, g in enumerate(groups) if i not in used and g.get("medicine_name")]
    for t in range(len(truth_lines)):
        if t not in pairs and leftover:
            pairs[t] = leftover.pop(0)
            used.add(pairs[t])
    outcome = []
    for t, truth in enumerate(truth_lines):
        match = groups[pairs[t]] if t in pairs else {}
        for field in CRITICAL:
            expected, got = truth.get(field), match.get(field)
            if not got:
                verdict = "abstained"
            elif norm(got) == norm(expected) or norm(expected) in norm(got):
                verdict = "correct"
            else:
                verdict = "wrong"
            outcome.append({"field": field, "expected": expected, "got": got, "verdict": verdict})
    # Extra medicine groups that match no true line are invented medicines.
    invented = [g.get("medicine_name") for g in groups if g.get("medicine_name") and
                not any(norm(g.get("medicine_name")) == norm(t["medicine_name"]) for t in truth_lines)]
    return outcome, invented


def summarise(records):
    counts = {field: Counter() for field in CRITICAL}
    by_difficulty = defaultdict(Counter)
    for record in records:
        for o in record["outcome"]:
            counts[o["field"]][o["verdict"]] += 1
            by_difficulty[record["difficulty"]][o["verdict"]] += 1
    latencies = sorted(r["seconds"] for r in records)
    return {
        "images": len(records), "classified_as": dict(Counter(r["kind"] for r in records)),
        "fields": {f: dict(c) for f, c in counts.items()},
        "wrong_rate": {f: round(c["wrong"] / max(1, sum(c.values())), 3) for f, c in counts.items()},
        "correct_rate": {f: round(c["correct"] / max(1, sum(c.values())), 3) for f, c in counts.items()},
        "by_difficulty": {str(k): dict(v) for k, v in sorted(by_difficulty.items())},
        "unmatched_medicine_names_total": sum(len(r["unmatched_medicine_names"]) for r in records),
        "latency_seconds_median": latencies[len(latencies) // 2] if latencies else None,
        "label_origin": LABEL_ORIGIN,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://127.0.0.1:8100")
    parser.add_argument("--set", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--files", nargs="*", help="re-run only these images, keeping the other records")
    args = parser.parse_args()
    root, out = Path(args.set), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    existing = {}
    if args.files and (out / "records.json").exists():
        existing = {r["file"]: r for r in json.loads((out / "records.json").read_text(encoding="utf-8"))}
    selected = [item for item in manifest if not args.files or item["file"] in args.files]
    client = httpx.Client(base_url=args.api, timeout=600, trust_env=False)
    for item in selected:
        token = client.post("/v1/sessions").json()["token"]
        headers = {"Authorization": "Bearer " + token}
        started = time.monotonic()
        result = client.post("/v1/attachments", headers=headers,
                             files={"file": (item["file"], (root / item["file"]).read_bytes(), "image/png")}).json()
        seconds = round(time.monotonic() - started, 1)
        client.delete("/v1/sessions/current", headers=headers)
        groups = groups_from(result.get("fields", []))
        outcome, invented = score(item["truth"], groups)
        existing[item["file"]] = {"file": item["file"], "difficulty": item["difficulty"],
                                  "kind": (result.get("classification") or {}).get("kind"), "engine": result.get("ocr_engine"),
                                  "outcome": outcome, "read_groups": groups, "unmatched_medicine_names": invented,
                                  "seconds": seconds}
        print(item["file"], existing[item["file"]]["kind"], Counter(o["verdict"] for o in outcome), flush=True)
    records = [existing[item["file"]] for item in manifest if item["file"] in existing]
    summary = summarise(records)
    (out / "records.json").write_text(json.dumps(records, indent=1), encoding="utf-8")
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
