"""Library build orchestrator.

    python -m aster_library.build acquire --provider europepmc|medlineplus|dailymed|openstax|legacy|all
    python -m aster_library.build pack --version <v>
    python -m aster_library.build index --pack <dir>

Work state lives under ``data/library-work`` (HTTP cache, per-document
checkpoints, search logs). Re-running resumes from checkpoints; ``--refresh``
re-queries providers for new material since the last run.
"""
import argparse
import json
import sys
import time
from pathlib import Path

from aster_library.common import PROVIDERS, ROOT, WORK, log, register
from aster_library.net import PoliteClient


@register("europepmc")
def acquire_europepmc(client, refresh=False):
    from aster_library.providers.europepmc import EuropePMC

    plan = json.loads((ROOT / "configs/library/query_plan.json").read_text(encoding="utf-8"))
    provider = EuropePMC(client, WORK / "europepmc")
    state_path = WORK / "europepmc" / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    refresh_from = state.get("last_search_date") if refresh else None
    if refresh:
        client.offline = False
    log("europepmc: running specialty query plan")
    candidates, search_log = provider.plan_searches(plan, refresh_from=refresh_from)
    (WORK / "europepmc").mkdir(parents=True, exist_ok=True)
    with (WORK / "europepmc" / ("search_log_refresh.jsonl" if refresh else "search_log.jsonl")).open("w", encoding="utf-8") as out:
        for entry in search_log:
            out.write(json.dumps(entry, ensure_ascii=False) + "\n")
    log(f"europepmc: {len(candidates)} unique candidate documents; acquiring full text")
    outcomes = provider.acquire(candidates, progress=log)
    counts = {}
    for status in outcomes.values():
        counts[status] = counts.get(status, 0) + 1
    state.update({"last_search_date": time.strftime("%Y-%m-%d"), "plan_id": plan["plan_id"], "outcomes": counts,
                  "candidates": len(candidates)})
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    log(f"europepmc: outcomes {counts}")


@register("europepmc-gapfill")
def acquire_europepmc_gaps(client, refresh=False):
    from aster_library.providers.europepmc import EuropePMC

    plan = json.loads((ROOT / "configs/library/query_plan.json").read_text(encoding="utf-8"))
    provider = EuropePMC(client, WORK / "europepmc")
    counts, existing = {}, set()
    for path in (WORK / "europepmc" / "docs").glob("*.json"):
        item = json.loads(path.read_text(encoding="utf-8"))
        existing.add(item["doc"]["doc_id"])
        if item["status"] == "acquired":
            for match in item["doc"].get("matched", []):
                counts[(match["domain"], match["topic"])] = counts.get((match["domain"], match["topic"]), 0) + 1
    for link in load_links():
        if link["doc_id"] in existing:
            counts[(link["domain"], link["topic"])] = counts.get((link["domain"], link["topic"]), 0) + 1
    log("europepmc-gapfill: searching topics with fewer than 3 indexed documents")
    candidates, search_log, links = provider.gap_fill(plan, counts, existing)
    with (WORK / "europepmc" / "search_log_gapfill.jsonl").open("w", encoding="utf-8") as out:
        for entry in search_log:
            out.write(json.dumps(entry, ensure_ascii=False) + "\n")
    with (WORK / "europepmc" / "topic_links.jsonl").open("w", encoding="utf-8") as out:
        for link in links:
            out.write(json.dumps(link) + "\n")
    log(f"europepmc-gapfill: {len(search_log)} gap topics, {len(candidates)} new candidates, {len(links)} links to existing documents")
    outcomes = provider.acquire(candidates, progress=log)
    counts = {}
    for status in outcomes.values():
        counts[status] = counts.get(status, 0) + 1
    log(f"europepmc-gapfill: outcomes {counts}")


def load_links():
    path = WORK / "europepmc" / "topic_links.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.exists() else []


def main(argv=None):
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    acq = sub.add_parser("acquire")
    acq.add_argument("--provider", default="all")
    acq.add_argument("--refresh", action="store_true")
    acq.add_argument("--offline", action="store_true", help="replay from cache only")
    pack = sub.add_parser("pack")
    pack.add_argument("--version", required=True)
    pack.add_argument("--out", default=str(ROOT / "data" / "library" / "packs"))
    idx = sub.add_parser("index")
    idx.add_argument("--pack", required=True)
    rep = sub.add_parser("report")
    rep.add_argument("--pack", required=True)
    args = parser.parse_args(argv)

    # Optional providers register themselves on import.
    import aster_library.providers.registry  # noqa: F401

    if args.command == "acquire":
        client = PoliteClient(WORK / "http-cache", offline=args.offline)
        try:
            names = list(PROVIDERS) if args.provider == "all" else args.provider.split(",")
            for name in names:
                PROVIDERS[name](client, refresh=args.refresh)
        finally:
            log(f"http stats {client.stats}")
            client.close()
    elif args.command == "pack":
        from aster_library.pack import build_pack

        build_pack(WORK, Path(args.out), args.version, log=log)
    elif args.command == "index":
        from aster_library.index import build_index

        build_index(Path(args.pack), log=log)
    elif args.command == "report":
        from aster_library.report import write_report

        write_report(Path(args.pack), WORK, log=log)
    return 0


if __name__ == "__main__":
    sys.exit(main())
