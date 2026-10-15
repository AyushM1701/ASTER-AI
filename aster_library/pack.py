"""Assemble provider outputs into versioned, signed reference packs.

Two editions are produced from the same acquisition run:

* ``core``  — CC0/CC BY/CC BY-SA/public-domain material; default install.
* ``nc``    — CC BY-NC / CC BY-NC-SA material; a separate pack with its own
  licence notice. Setup lets users exclude it.

Every unit keeps publisher, URL, document identity, jurisdiction, version/date,
acquisition date, licence, checksum and evidence location. Deduplication is by
work identity (DOI/PMID/PMCID/title) and by exact unit text.
"""
import hashlib
import json
import re
import shutil
import time
from pathlib import Path

from aster_library import PIPELINE_VERSION
from aster_library.model import edition_for

PACK_SCHEMA = 2
FRESHNESS = {
    # days after acquisition: review = refresh recommended; warn = show outdated warning on answers
    "patient": {"review_after_days": 365, "warn_after_days": 730},
    "drug_label": {"review_after_days": 180, "warn_after_days": 365},
    "professional": {"review_after_days": 730, "warn_after_days": 1825},
    "research": {"review_after_days": 730, "warn_after_days": 1825},
}
CONTENT_FOR_TYPE = {
    "patient_summary": "patient", "patient_test_information": "patient", "drug_label": "drug_label",
    "textbook": "professional", "educational": "professional", "review": "professional",
    "systematic_review": "professional", "meta_analysis": "professional", "guideline": "professional",
    "rct": "research", "original_research": "research", "case_report": "research", "editorial": "research",
}
DOMAIN_FOR_BOOK = [
    (re.compile(r"anatomy", re.I), "basic_sciences"), (re.compile(r"microbio", re.I), "basic_sciences"),
    (re.compile(r"biology|chemistry|neuroscience", re.I), "basic_sciences"),
    (re.compile(r"pharmacolog", re.I), "pharmacology"), (re.compile(r"statistic", re.I), "research_methods"),
    (re.compile(r"nursing|population health|nutrition", re.I), "general_medicine"),
    (re.compile(r"psycholog|lifespan", re.I), "general_medicine"),
]


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def norm_title(title):
    return re.sub(r"[^a-z0-9]+", " ", (title or "").casefold()).strip()


def load_all(work):
    from aster_library.providers import legacy, medlineplus, openfda_labels, openstax

    items = []
    for name, loader in (("medlineplus", medlineplus.load), ("openfda", openfda_labels.load),
                         ("openstax", openstax.load), ("legacy", legacy.load)):
        loaded = loader(work)
        items.extend(loaded)
    links = {}
    link_path = Path(work) / "europepmc" / "topic_links.jsonl"
    if link_path.exists():
        for line in link_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                link = json.loads(line)
                links.setdefault(link["doc_id"], []).append({k: link[k] for k in ("domain", "topic", "quota")})
    for path in sorted((Path(work) / "europepmc" / "docs").glob("*.json")):
        item = json.loads(path.read_text(encoding="utf-8"))
        if item["doc"]["doc_id"] in links:
            item["doc"]["matched"] = item["doc"].get("matched", []) + links[item["doc"]["doc_id"]]
        items.append(item)
    return items


def domains_for(doc):
    if doc.get("matched"):
        return sorted({m["domain"] for m in doc["matched"]}), sorted({m["topic"] for m in doc["matched"]})
    if doc["provider"] == "openfda":
        return ["pharmacology"], [", ".join(doc.get("drug", {}).get("generic_name", []))]
    if doc["provider"] == "medlineplus":
        return ["patient_information"], doc.get("groups", [])
    if doc["provider"] == "openstax":
        book = doc.get("book", "")
        return [next((d for pattern, d in DOMAIN_FOR_BOOK if pattern.search(book)), "basic_sciences")], [book]
    subjects = doc.get("subjects") or []
    return (["legacy_" + s for s in subjects] or ["legacy"]), subjects


def build_pack(work, out_root, version, *, log=print, signing_key=None):
    work, out_root = Path(work), Path(out_root)
    items = load_all(work)
    log(f"pack: {len(items)} provider items loaded")
    stats = {"items": len(items), "by_status": {}, "duplicates_work": 0, "duplicates_unit_text": 0,
             "excluded_license": 0, "by_edition": {}, "by_provider": {}}
    for item in items:
        stats["by_status"][item["status"]] = stats["by_status"].get(item["status"], 0) + 1
    acquired = [i for i in items if i["status"] == "acquired"]
    # Work-level deduplication. Priority: EPMC full text > legacy > others.
    priority = {"europepmc": 0, "legacy-candidate-v5": 1, "openstax": 2, "medlineplus": 3, "openfda": 4}
    acquired.sort(key=lambda i: (priority.get(i["doc"]["provider"], 9), -len(i.get("units", []))))
    seen_keys, kept, dedup_log = {}, [], []
    for item in acquired:
        doc = item["doc"]
        ids = doc.get("identifiers") or {}
        keys = [f"{kind}:{str(ids[kind]).strip().casefold()}" for kind in ("doi", "pmid", "pmcid") if ids.get(kind)]
        url = doc.get("url") or ""
        pmc_in_url = re.search(r"PMC\d+", url)
        if pmc_in_url:
            keys.append("pmcid:" + pmc_in_url.group(0).casefold())
        if doc["provider"] in {"europepmc", "legacy-candidate-v5"} and len(norm_title(doc.get("title"))) > 25:
            keys.append("title:" + norm_title(doc.get("title")))
        duplicate = next((seen_keys[k] for k in keys if k in seen_keys), None)
        if duplicate:
            stats["duplicates_work"] += 1
            dedup_log.append({"dropped": doc["doc_id"], "kept": duplicate, "keys": keys})
            continue
        for key in keys:
            seen_keys[key] = doc["doc_id"]
        kept.append(item)
    created = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    editions = {"core": {"docs": [], "units": []}, "nc": {"docs": [], "units": []}}
    seen_text = set()
    excluded_log = []
    for item in kept:
        doc = dict(item["doc"])
        edition = edition_for(doc.get("license"))
        if edition is None:
            stats["excluded_license"] += 1
            excluded_log.append({"doc_id": doc["doc_id"], "reason": f"licence {doc.get('license')} not redistributable"})
            continue
        target = editions["core" if edition == "default" else "nc"]
        doc["content_class"] = doc.get("content_class") if doc.get("content_class") in {"patient", "drug_label"} else \
            CONTENT_FOR_TYPE.get(doc.get("evidence_type"), "professional")
        doc["domains"], doc["topics"] = domains_for(doc)
        doc["edition"] = "core" if edition == "default" else "nc"
        unit_count = 0
        for unit in item.get("units", []):
            if unit["text_sha256"] in seen_text or len(unit["text"]) < 40:
                stats["duplicates_unit_text"] += unit["text_sha256"] in seen_text
                continue
            seen_text.add(unit["text_sha256"])
            unit = dict(unit)
            unit.update({"content_class": doc["content_class"], "evidence_type": doc.get("evidence_type"),
                         "license": doc.get("license"), "jurisdiction": doc.get("jurisdiction") or "International",
                         "domains": doc["domains"], "title": doc.get("title"), "publisher": doc.get("publisher"),
                         "url": doc.get("url"), "published": doc.get("published"), "acquired": doc.get("acquired"),
                         "access": doc.get("access", "full_text"),
                         "publication_status": doc.get("publication_status", "published")})
            target["units"].append(unit)
            unit_count += 1
        if unit_count:
            doc["unit_count"] = unit_count
            doc.pop("matched_raw", None)
            target["docs"].append(doc)
            stats["by_provider"][doc["provider"]] = stats["by_provider"].get(doc["provider"], 0) + 1
    outputs = []
    for edition, content in editions.items():
        pack_id = f"aster-library-{edition}-{version}"
        out = out_root / pack_id
        if out.exists():
            shutil.rmtree(out)
        (out / "licenses").mkdir(parents=True)
        with (out / "documents.jsonl").open("w", encoding="utf-8") as handle:
            for doc in content["docs"]:
                handle.write(json.dumps(doc, ensure_ascii=False, sort_keys=True) + "\n")
        with (out / "units.jsonl").open("w", encoding="utf-8") as handle:
            for unit in content["units"]:
                handle.write(json.dumps(unit, ensure_ascii=False, sort_keys=True) + "\n")
        for provider, snapshot in (("medlineplus", "terms-snapshot.html"), ("openfda", "terms-snapshot.html")):
            source = work / provider / snapshot
            if source.exists():
                shutil.copy2(source, out / "licenses" / f"{provider}-{snapshot}")
        licenses = {}
        for doc in content["docs"]:
            licenses[doc.get("license")] = licenses.get(doc.get("license"), 0) + 1
        (out / "NOTICE.md").write_text(notice_text(edition, content["docs"], licenses), encoding="utf-8")
        stats["by_edition"][edition] = {"documents": len(content["docs"]), "units": len(content["units"])}
        classes = {}
        for unit in content["units"]:
            classes[unit["content_class"]] = classes.get(unit["content_class"], 0) + 1
        manifest = {
            "schema_version": PACK_SCHEMA, "pack_id": pack_id, "version": version, "edition": edition,
            "created": created, "pipeline": PIPELINE_VERSION,
            "counts": {"documents": len(content["docs"]), "units": len(content["units"]), "by_content_class": classes},
            "licenses": licenses,
            "license_scope": ("Redistributable incl. commercial use, subject to attribution/share-alike terms per source"
                              if edition == "core" else "Noncommercial use only (CC BY-NC / CC BY-NC-SA); share-alike where stated"),
            "freshness": FRESHNESS,
            "quality_gate": {"automated_checks": ["licence allowlist", "work+text deduplication", "retraction exclusion",
                                                  "minimum unit length", "provenance fields present"],
                             "medical_review": "not performed; automated checks are not clinical review"},
            "files": {},
        }
        for name in ("documents.jsonl", "units.jsonl", "NOTICE.md"):
            manifest["files"][name] = {"sha256": sha256_file(out / name), "bytes": (out / name).stat().st_size}
        for path in sorted((out / "licenses").iterdir()):
            manifest["files"]["licenses/" + path.name] = {"sha256": sha256_file(path), "bytes": path.stat().st_size}
        (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        from aster_library.signing import sign_file

        sign_file(out / "manifest.json", signing_key)
        outputs.append(out)
        log(f"pack: {pack_id}: {len(content['docs'])} documents, {len(content['units'])} units")
    report_dir = out_root / f"build-{version}"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "pack-stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    with (report_dir / "dedup-log.jsonl").open("w", encoding="utf-8") as handle:
        for entry in dedup_log:
            handle.write(json.dumps(entry) + "\n")
    with (report_dir / "exclusions.jsonl").open("w", encoding="utf-8") as handle:
        for item in items:
            if item["status"] != "acquired":
                handle.write(json.dumps({"doc_id": item["doc"].get("doc_id"), "status": item["status"],
                                         "reason": item.get("reason")}) + "\n")
        for entry in excluded_log:
            handle.write(json.dumps({**entry, "status": "excluded"}) + "\n")
    return outputs


def notice_text(edition, docs, licenses):
    lines = [f"# Aster reference library — {edition} pack", "",
             "This pack contains third-party material redistributed under the licences listed per document in",
             "`documents.jsonl` (`license`, `license_url`, `attribution`, `url`). Aster's MIT licence does not",
             "apply to this material. No publisher endorsement is implied. Content was processed automatically",
             "(text extraction and segmentation); it has not been clinically reviewed.", "",
             "Licence counts: " + ", ".join(f"{k}: {v}" for k, v in sorted(licenses.items(), key=lambda kv: str(kv[0]))), ""]
    if edition == "nc":
        lines += ["**Noncommercial use only.** CC BY-NC / CC BY-NC-SA terms apply; adaptations must carry the same",
                  "licence where share-alike applies. Exclude this pack for any commercial use.", ""]
    lines += ["Publisher-specific notices:",
              "- MedlinePlus: Courtesy of MedlinePlus from the National Library of Medicine (public-domain health-topic",
              "  summaries and medical-test pages only; A.D.A.M. and ASHP content excluded).",
              "- openFDA drug labeling: CC0 1.0 (https://open.fda.gov/terms/). US labels for US products only.",
              "- OpenStax: Access for free at openstax.org (Rice University); licence per book.",
              "- Europe PMC/PMC open-access articles: licence per article as stated in the article XML.", ""]
    return "\n".join(lines)
