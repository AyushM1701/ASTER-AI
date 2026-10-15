"""Run the frozen evaluation set against a running Aster API (source or packaged).

    python evaluation/run_eval.py --api http://127.0.0.1:8000 --split dev --out evaluation/runs/<name>

Each item gets a fresh session; multi-turn items reuse it across turns. Responses
are stored verbatim (no patient data is involved: all items are synthetic).
"""
import argparse
import hashlib
import json
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--split", choices=["dev", "holdout", "all"], default="dev")
    parser.add_argument("--out", required=True)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--category", default="")
    parser.add_argument("--header", action="append", default=[], help="extra header, e.g. X-Aster-Client:1")
    args = parser.parse_args()
    data = (ROOT / "eval_set_v1.jsonl").read_bytes()
    lock = json.loads((ROOT / "eval-set.lock.json").read_text(encoding="utf-8"))
    if hashlib.sha256(data).hexdigest() != lock["sha256"]:
        raise SystemExit("Evaluation set changed after freezing; refusing to run.")
    items = [json.loads(line) for line in data.decode("utf-8").splitlines() if line.strip()]
    items = [i for i in items if args.split == "all" or i["split"] == args.split]
    if args.category:
        items = [i for i in items if i["category"] in args.category.split(",")]
    if args.limit:
        items = items[:args.limit]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    done = set()
    results_path = out / "responses.jsonl"
    if results_path.exists():
        done = {json.loads(line)["id"] for line in results_path.read_text(encoding="utf-8").splitlines() if line.strip()}
    headers = dict(h.split(":", 1) for h in args.header)
    client = httpx.Client(base_url=args.api, timeout=httpx.Timeout(600, connect=10), headers=headers, trust_env=False)
    health = client.get("/health/ready").json()
    (out / "health.json").write_text(json.dumps(health, indent=2), encoding="utf-8")
    with results_path.open("a", encoding="utf-8") as handle:
        for n, item in enumerate(items, 1):
            if item["id"] in done:
                continue
            token = client.post("/v1/sessions").json()["token"]
            auth = {"Authorization": "Bearer " + token}
            turns = []
            for question in item["turns"]:
                started = time.monotonic()
                response = client.post("/v1/chat", json={"question": question, "audience": item["audience"],
                                                         "task_explicit": item["audience"] != "understand"}, headers=auth)
                elapsed = time.monotonic() - started
                try:
                    body = response.json()
                except ValueError:
                    body = {"status": "http_error", "text": response.text[:500]}
                turns.append({"question": question, "http_status": response.status_code, "seconds": round(elapsed, 2), "response": body})
            client.delete("/v1/sessions/current", headers=auth)
            record = {"id": item["id"], "item": item, "turns": turns}
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            handle.flush()
            last = turns[-1]
            print(f"[{n}/{len(items)}] {item['id']} {last['response'].get('status')} {last['seconds']}s", flush=True)
    (out / "run.json").write_text(json.dumps({"api": args.api, "split": args.split, "eval_sha256": lock["sha256"],
                                              "finished": time.strftime("%Y-%m-%dT%H:%M:%S"), "items": len(items)}, indent=2),
                                  encoding="utf-8")


if __name__ == "__main__":
    main()
