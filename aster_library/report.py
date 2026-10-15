"""Collection and coverage report per domain/topic for a built pack pair."""
import json
from collections import Counter, defaultdict
from pathlib import Path


def _jsonl(path):
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_report(pack_dir, work, *, log=print):
    pack_dir, work = Path(pack_dir), Path(work)
    packs_root = pack_dir.parent
    version = json.loads((pack_dir / "manifest.json").read_text(encoding="utf-8"))["version"]
    packs = [p for p in packs_root.glob(f"aster-library-*-{version}") if (p / "manifest.json").exists()]
    docs = [d for p in packs for d in _jsonl(p / "documents.jsonl")]
    plan = json.loads((Path(__file__).resolve().parents[1] / "configs/library/query_plan.json").read_text(encoding="utf-8"))
    search_log = _jsonl(work / "europepmc" / "search_log.jsonl")
    gap_log = {(e["domain"], e["topic"]): e for e in _jsonl(work / "europepmc" / "search_log_gapfill.jsonl")}
    statuses = {}
    for path in (work / "europepmc" / "docs").glob("*.json"):
        item = json.loads(path.read_text(encoding="utf-8"))
        statuses[item["doc"]["doc_id"]] = item
    indexed_by_topic = defaultdict(set)
    units_by_doc = {d["doc_id"]: d.get("unit_count", 0) for d in docs}
    for doc in docs:
        for match in doc.get("matched", []) or []:
            indexed_by_topic[(match["domain"], match["topic"])].add(doc["doc_id"])
    build_dir = packs_root / f"build-{version}"
    dedup = _jsonl(build_dir / "dedup-log.jsonl")
    exclusions = _jsonl(build_dir / "exclusions.jsonl")
    rows, domain_rows = [], []
    for domain in plan["domains"]:
        domain_totals = Counter()
        for entry in [e for e in search_log if e["domain"] == domain["id"]]:
            gap_entry = gap_log.get((entry["domain"], entry["topic"]), {})
            selected = entry.get("selected", []) + gap_entry.get("selected", [])
            outcome = Counter(statuses[k]["status"] if k in statuses else "not_attempted" for k in selected)
            reasons = Counter((statuses[k].get("reason") or "")[:60] for k in selected if k in statuses and statuses[k]["status"] != "acquired")
            indexed = indexed_by_topic.get((domain["id"], entry["topic"]), set())
            full_text = sum(1 for k in indexed if statuses.get(k, {}).get("doc", {}).get("access") == "full_text")
            types = Counter(statuses[k]["doc"].get("evidence_type") for k in indexed if k in statuses)
            row = {
                "domain": domain["id"], "topic": entry["topic"], "provider": "Europe PMC (PMC OA full text)",
                "date_range": f"{entry['date_from']} to {entry['date_to']}",
                "discovered_any_access": entry.get("discovered_any_access"),
                "discovered_open_licensed": entry.get("discovered_open_licensed"),
                "selected": len(selected), "acquired": outcome.get("acquired", 0),
                "unavailable_full_text": outcome.get("unavailable", 0), "parse_failed": outcome.get("parse_failed", 0),
                "excluded": outcome.get("excluded", 0), "exclusion_reasons": dict(reasons),
                "indexed_documents": len(indexed), "indexed_full_text": full_text,
                "indexed_units": sum(units_by_doc.get(k, 0) for k in indexed),
                "evidence_types": dict(types), "search_error": entry.get("error") or gap_entry.get("error"),
                "gap_fill_pass": bool(gap_entry), "gap_fill_query": gap_entry.get("query"),
                "gap": len(indexed) < 2,
            }
            rows.append(row)
            for key in ("selected", "acquired", "unavailable_full_text", "parse_failed", "excluded", "indexed_documents", "indexed_units"):
                domain_totals[key] += row[key]
            domain_totals["topics"] += 1
            domain_totals["gap_topics"] += row["gap"]
        domain_rows.append({"domain": domain["id"], "title": domain["title"], "mds_specialty": domain.get("mds_specialty", False),
                            **domain_totals})
    other = Counter(d["provider"] for d in docs)
    licenses = Counter(d.get("license") for d in docs)
    report = {
        "version": version, "packs": [p.name for p in packs], "documents": len(docs),
        "units": sum(units_by_doc.values()), "by_provider": dict(other), "licenses": dict(licenses),
        "deduplicated_works": len(dedup), "exclusions": Counter(e.get("status") for e in exclusions),
        "exclusion_reasons": Counter((e.get("reason") or "")[:70] for e in exclusions).most_common(15),
        "domains": domain_rows, "topics": rows,
        "latest_update": max((d.get("acquired") or "" for d in docs), default=None),
    }
    out = build_dir / "coverage-report.json"
    out.write_text(json.dumps(report, indent=2, default=dict), encoding="utf-8")
    (build_dir / "COVERAGE_REPORT.md").write_text(markdown(report), encoding="utf-8")
    log(f"report: {out}")
    return report


def markdown(report):
    lines = [f"# Library collection and coverage report — {report['version']}", "",
             f"Packs: {', '.join(report['packs'])}. Documents: {report['documents']}; evidence units: {report['units']}.",
             f"Latest acquisition date: {report['latest_update']}. Work-level duplicates removed: {report['deduplicated_works']}.", "",
             "Counts describe what was searched and collected. They are not a claim of exhaustive coverage, and inclusion",
             "does not mean clinician or faculty review.", "", "## By provider", ""]
    lines += [f"- {k}: {v} documents" for k, v in sorted(report["by_provider"].items())]
    lines += ["", "## Rights decisions (documents by licence)", ""]
    lines += [f"- {k}: {v}" for k, v in sorted(report["licenses"].items(), key=lambda kv: str(kv[0]))]
    lines += ["", "## Exclusions", ""]
    lines += [f"- {reason or '(no reason recorded)'}: {count}" for reason, count in report["exclusion_reasons"]]
    lines += ["", "## Europe PMC literature by domain", "",
              "| Domain | Topics | Selected | Acquired | Full text unavailable | Parse failed | Excluded | Indexed docs | Indexed units | Topics with <2 docs |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for d in report["domains"]:
        lines.append(f"| {d['title']} | {d.get('topics', 0)} | {d.get('selected', 0)} | {d.get('acquired', 0)} | "
                     f"{d.get('unavailable_full_text', 0)} | {d.get('parse_failed', 0)} | {d.get('excluded', 0)} | "
                     f"{d.get('indexed_documents', 0)} | {d.get('indexed_units', 0)} | {d.get('gap_topics', 0)} |")
    lines += ["", "## Topic detail", "",
              "| Domain | Topic | Date range | Discovered (any access) | Discovered (open licence) | Selected | Indexed docs | Full text | Evidence types | Gap |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for r in report["topics"]:
        types = ", ".join(f"{k}:{v}" for k, v in sorted(r["evidence_types"].items(), key=lambda kv: str(kv[0])))
        lines.append(f"| {r['domain']} | {r['topic']} | {r['date_range']} | {r['discovered_any_access']} | {r['discovered_open_licensed']} | "
                     f"{r['selected']} | {r['indexed_documents']} | {r['indexed_full_text']} | {types} | {'yes' if r['gap'] else ''} |")
    return "\n".join(lines) + "\n"
