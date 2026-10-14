"""Stage complete public topic summaries. No patient queries or live chat hook."""

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

from research.data.medlineplus import ENDPOINT, POLICY, PUBLIC_TOPICS, parse_topics


def fetch(client, url, params=None):
    with client.stream("GET", url, params=params) as response:
        response.raise_for_status()
        chunks, size = [], 0
        for chunk in response.iter_bytes():
            size += len(chunk)
            if size > 2_000_000:
                raise ValueError("Service response exceeded acquisition bound")
            chunks.append(chunk)
        return b"".join(chunks)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic", choices=PUBLIC_TOPICS, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    items, captures = {}, []
    with httpx.Client(timeout=30, follow_redirects=False, trust_env=False) as client:
        policy = fetch(client, POLICY)
        (args.output / "service-policy.html").write_bytes(policy)
        for index, topic in enumerate(dict.fromkeys(args.topic)):
            if index:
                time.sleep(1)  # <=60/min for this sequential acquisition process.
            raw = fetch(client, ENDPOINT, {"db": "healthTopics", "term": topic,
                                           "retmax": 3, "rettype": "brief", "tool": "aster_acquisition"})
            filename = f"query-{index + 1}.xml"
            (args.output / filename).write_bytes(raw)
            rows = parse_topics(raw)
            for row in rows:
                row["acquisition_queries"] = sorted(set(items.get(row["source_id"], {}).get("acquisition_queries", []) + [topic]))
                items[row["source_id"]] = row
            captures.append({"public_topic": topic, "file": filename,
                             "sha256": hashlib.sha256(raw).hexdigest(), "returned_full_summaries": len(rows)})
    (args.output / "items.json").write_text(json.dumps(list(items.values()), indent=2, ensure_ascii=False), encoding="utf-8")
    manifest = {"state": "staged_for_source_review", "acquired_at": datetime.now(timezone.utc).isoformat(),
                "service": ENDPOINT, "policy_url": POLICY, "policy_sha256": hashlib.sha256(policy).hexdigest(),
                "captures": captures, "items": len(items), "runtime_admitted": 0, "activated": False,
                "scope": "Public-topic service summaries only. External links, drug pages and third-party content not acquired.",
                "training": "not_approved", "redistribution": "not_approved", "commercial": "not_approved",
                "clinical_review": "pending", "source_facet_review": "pending"}
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"items": len(items), "state": manifest["state"], "activated": False}))


if __name__ == "__main__":
    main()
