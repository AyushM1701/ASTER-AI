"""Bounded rights-gated acquisition of focused foundation source alternatives.

This separate inspection artifact does not alter the 120-document collection or
the active release. Reuses the tested collector transport and rights screen.
"""
import json
from pathlib import Path
from urllib.parse import urlencode

from scripts.mds_open_collect import (
    API,
    Budget,
    Client,
    atomic_bytes,
    inspect_xml,
    json_write,
    jsonl_write,
    now,
    sha,
)


def run():
    output = Path("artifacts/source-review/mds-foundations-v2/acquired")
    output.mkdir(parents=True, exist_ok=True)
    config = json.loads(Path("configs/mds_open_collection.json").read_text())
    config.update(max_requests=60, per_host_requests=60, max_seconds=600,
                  max_bytes=40 * 1024 * 1024, max_file_bytes=8 * 1024 * 1024,
                  retries=1, timeout_seconds=20)
    budget = Budget(config)
    client = Client(budget, config)
    # Explicit article identities are rights-inspected before discovered hits.
    # Absence of metadata permission is never treated as permission to retain.
    candidates = {pmcid: {"pmcid": pmcid} for pmcid in ("PMC8633170", "PMC9424112", "PMC6684678")}
    excluded, documents = [], []
    queries = [
        'OPEN_ACCESS:Y AND TITLE_ABS:"oral epithelium" AND TITLE_ABS:"layers"',
        'OPEN_ACCESS:Y AND TITLE_ABS:"oral mucosa" AND TITLE_ABS:"barrier"',
        'OPEN_ACCESS:Y AND TITLE:"odontogenic keratocyst" AND TITLE:"review"',
    ]
    for query in queries:
        url = API + "search?" + urlencode(dict(query=query, format="json", resultType="core", pageSize=12))
        result = json.loads(client.fetch(url, "json"))
        for item in result.get("resultList", {}).get("result", []):
            pmcid = item.get("pmcid")
            if pmcid and pmcid not in candidates:
                candidates[pmcid] = item
    for pmcid, item in candidates.items():
        if len(documents) >= 8:
            break
        metadata_license = str(item.get("license", "")).upper()
        if "NC" in metadata_license or "ND" in metadata_license or "RETRACT" in item.get("title", "").upper():
            excluded.append({"pmcid": pmcid, "reason": "restrictive_metadata_or_editorial_title", "license": metadata_license})
            continue
        if item.get("commentCorrectionList"):
            excluded.append({"pmcid": pmcid, "reason": "editorial_notice_requires_review"})
            continue
        try:
            raw = client.fetch(API + pmcid + "/fullTextXML", "xml")
            result = inspect_xml(raw, pmcid)
            if result["track"] != "default":
                excluded.append({"pmcid": pmcid, "reason": result["reason"], "license": result["license"], "source_sha256": sha(raw)})
                continue
            identity = pmcid.lower() + "-" + sha(raw)[:12]
            stored = raw if result["retain_original"] else result["sanitized_xml"]
            source_path = output / "sources" / (identity + ".xml")
            atomic_bytes(source_path, stored, immutable=True)
            rights = {key: result[key] for key in ("license", "license_url", "license_notices", "license_evidence_xml", "retain_original", "omitted_assets", "authors", "title")}
            rights.update(pmcid=pmcid, canonical_url="https://pmc.ncbi.nlm.nih.gov/articles/" + pmcid + "/", verified_at=now(), source_sha256=sha(raw), stored_sha256=sha(stored), source_path=str(source_path), publication_date=item.get("firstPublicationDate"), doi=item.get("doi"), status="STAGED", clinical_review="pending")
            json_write(output / "rights" / (identity + ".json"), rights)
            json_write(output / "prose" / (identity + ".json"), {"source": rights, "sections": result["sections"]})
            documents.append(rights)
            print(pmcid, result["license"], result["title"], flush=True)
        except (ValueError, OSError) as exc:
            excluded.append({"pmcid": pmcid, "reason": type(exc).__name__, "detail": str(exc)[:200]})
    jsonl_write(output / "catalogue.jsonl", documents)
    jsonl_write(output / "exclusions.jsonl", excluded)
    json_write(output / "checkpoint.json", {"usage": budget.usage(), "limits": config, "documents": len(documents), "metadata_candidates": len(candidates), "excluded": len(excluded), "status": "STAGED", "clinical_review": "pending"})


if __name__ == "__main__":
    run()
