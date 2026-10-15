"""Europe PMC discovery + open-access full text (JATS) with licence filtering.

Interfaces: REST search (https://www.ebi.ac.uk/europepmc/webservices/rest/search)
and fullTextXML for open-access articles. Only CC BY / CC BY-SA / CC0 articles are
acquired for the default edition; the licence is re-checked inside the XML.
Retractions are excluded; corrections/expressions of concern are flagged.
"""
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from aster_library.jats import parse_article
from aster_library.model import DEFAULT_EDITION_LICENSES, clean_text, normalize_license, today
from aster_library.net import FetchError

BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"
SKIP_SECTION = re.compile(
    r"^(?:references?|bibliography|acknowledg|funding|conflicts? of interest|competing interests?|"
    r"declaration|author(?:s'|s)? contributions?|data availability|availability of data|"
    r"abbreviations|ethics (?:approval|statement)|consent for publication|supplementary|"
    r"publisher'?s note|orcid|disclosure|financial support)", re.I)

QUOTA_FILTERS = {
    "cited_reviews": ('PUB_TYPE:"review"', None),
    "recent_reviews": ('PUB_TYPE:"review"', "recent"),
    "systematic": ('(PUB_TYPE:"systematic-review" OR PUB_TYPE:"meta-analysis" OR TITLE:"systematic review" OR TITLE:"meta-analysis")', None),
    "guidelines": ('(PUB_TYPE:"guideline" OR PUB_TYPE:"practice guideline" OR PUB_TYPE:"consensus development conference" '
                   'OR TITLE:"guideline" OR TITLE:"consensus" OR TITLE:"position paper" OR TITLE:"recommendations")', None),
    "case_reports": ('PUB_TYPE:"case-report"', None),
}
EVIDENCE_TYPES = [
    ("retracted", re.compile(r"retracted publication", re.I)),
    ("meta_analysis", re.compile(r"meta-analysis", re.I)),
    ("systematic_review", re.compile(r"systematic-review|systematic review", re.I)),
    ("guideline", re.compile(r"guideline|consensus", re.I)),
    ("rct", re.compile(r"randomized controlled trial", re.I)),
    ("case_report", re.compile(r"case-report|case reports?", re.I)),
    ("review", re.compile(r"review", re.I)),
    ("editorial", re.compile(r"editorial|comment|letter", re.I)),
]


def phrase_or(terms, field="TITLE_ABS"):
    quoted = []
    for term in terms:
        term = term.replace('"', "").strip()
        if term:
            quoted.append(f'{field}:"{term}"')
    return "(" + " OR ".join(quoted) + ")"


def context_clause(context):
    terms = [t.strip() for t in re.sub(r"[()]", "", context or "").split(" OR ") if t.strip()]
    return phrase_or(terms) if terms else ""


def license_filter(licenses):
    return "(" + " OR ".join(f'LICENSE:"{name}"' for name in licenses) + ")"


def topic_query(topic, domain, defaults):
    synonyms = topic[1:] or topic[:1]
    parts = [phrase_or(synonyms)]
    ctx = context_clause(domain.get("context"))
    if ctx:
        parts.append(ctx)
    return " AND ".join(parts)


def classify(result):
    types = " ".join(result.get("pubTypeList", {}).get("pubType", []))
    title = result.get("title", "")
    for label, pattern in EVIDENCE_TYPES:
        if pattern.search(types) or (label in {"systematic_review", "meta_analysis", "guideline"} and pattern.search(title)):
            return label
    return "original_research"


def corrections(result):
    items = result.get("commentCorrectionList", {}).get("commentCorrection", [])
    return [{"type": c.get("type"), "id": c.get("id"), "source": c.get("source")} for c in items]


class EuropePMC:
    def __init__(self, client, work_dir):
        self.client = client
        self.work = Path(work_dir)
        (self.work / "docs").mkdir(parents=True, exist_ok=True)

    def count(self, query):
        data = self.client.get_json(BASE + "/search", {"query": query, "format": "json", "pageSize": 1, "resultType": "idlist"})
        return int(data.get("hitCount", 0))

    def search(self, query, limit, sort="CITED desc"):
        params = {"query": query, "format": "json", "pageSize": min(max(limit * 3, 10), 100),
                  "resultType": "core", "sort": sort, "cursorMark": "*"}
        data = self.client.get_json(BASE + "/search", params)
        return int(data.get("hitCount", 0)), data.get("resultList", {}).get("result", [])

    def plan_searches(self, plan, refresh_from=None):
        """Run the specialty query plan. Returns (candidates by doc id, search log)."""
        defaults = plan["defaults"]
        candidates, log = {}, []
        lic = license_filter(defaults["licenses"])
        open_filter = f"OPEN_ACCESS:y AND HAS_FT:y AND IN_EPMC:y AND {lic} AND LANG:eng NOT SRC:PPR"
        date_from = refresh_from or f"{defaults['date_from']}-01-01"
        for domain in plan["domains"]:
            quotas = {**defaults["quotas"], **domain.get("quotas", {})}
            for topic in domain["topics"]:
                base = topic_query(topic, domain, defaults)
                entry = {"domain": domain["id"], "topic": topic[0], "query": base, "provider": "europepmc",
                         "date_from": date_from, "date_to": today(), "quotas": quotas, "searched_on": today()}
                try:
                    entry["discovered_any_access"] = self.count(f"({base}) AND FIRST_PDATE:[{date_from} TO 2026-12-31]")
                    entry["discovered_open_licensed"] = self.count(f"({base}) AND {open_filter} AND FIRST_PDATE:[{date_from} TO 2026-12-31]")
                    entry["selected"] = []
                    for quota, wanted in quotas.items():
                        if not wanted:
                            continue
                        type_filter, window = QUOTA_FILTERS[quota]
                        start = f"{defaults['recent_from']}-01-01" if window == "recent" else date_from
                        query = f"({base}) AND {type_filter} AND {open_filter} AND FIRST_PDATE:[{start} TO 2026-12-31]"
                        hits, results = self.search(query, wanted)
                        taken = 0
                        match = {"domain": domain["id"], "topic": topic[0], "quota": quota}
                        for result in results:
                            pmcid = result.get("pmcid")
                            if not pmcid or taken >= wanted:
                                continue
                            key = "epmc:" + pmcid
                            if key in candidates:
                                # Already selected elsewhere: record the extra topic
                                # association but keep looking for new documents.
                                candidates[key]["matched"].append(match)
                                entry.setdefault("also_matched", []).append(key)
                                continue
                            candidates[key] = {"result": result, "matched": [match]}
                            entry["selected"].append(key)
                            taken += 1
                        entry.setdefault("quota_hits", {})[quota] = hits
                except FetchError as exc:
                    entry["error"] = str(exc)
                log.append(entry)
        return candidates, log

    def gap_fill(self, plan, indexed_counts, existing, minimum=3, extra=5):
        """Second pass for topics with too few indexed documents.

        Uses word-level AND matching instead of exact phrases and any publication
        type (original research is labelled ``research`` downstream). Returns
        (new candidates, search log entries)."""
        defaults = plan["defaults"]
        lic = license_filter(defaults["licenses"])
        open_filter = f"OPEN_ACCESS:y AND HAS_FT:y AND IN_EPMC:y AND {lic} AND LANG:eng NOT SRC:PPR"
        candidates, log, links = {}, [], []
        for domain in plan["domains"]:
            ctx = context_clause(domain.get("context"))
            for topic in domain["topics"]:
                have = indexed_counts.get((domain["id"], topic[0]), 0)
                if have >= minimum:
                    continue
                synonyms = topic[1:] or topic[:1]
                clauses = []
                for synonym in synonyms:
                    words = [w for w in re.findall(r"[A-Za-z0-9\-]+", synonym) if len(w) > 2 and w.casefold() not in {"and", "the", "for", "with"}]
                    if words:
                        clauses.append("(" + " AND ".join(f'TITLE_ABS:"{w}"' for w in words) + ")")
                base = "(" + " OR ".join(clauses) + ")" + (f" AND {ctx}" if ctx else "")
                entry = {"domain": domain["id"], "topic": topic[0], "query": base, "provider": "europepmc", "pass": "gap_fill",
                         "date_from": f"{defaults['date_from']}-01-01", "date_to": today(), "had_indexed": have,
                         "searched_on": today(), "selected": []}
                try:
                    query = f"({base}) AND {open_filter} AND FIRST_PDATE:[{defaults['date_from']}-01-01 TO 2026-12-31]"
                    entry["discovered_open_licensed"], results = self.search(query, extra * 2)
                    entry["discovered_any_access"] = self.count(f"({base}) AND FIRST_PDATE:[{defaults['date_from']}-01-01 TO 2026-12-31]")
                    taken = 0
                    match = {"domain": domain["id"], "topic": topic[0], "quota": "gap_fill"}
                    for result in results:
                        pmcid = result.get("pmcid")
                        if not pmcid or taken >= extra:
                            continue
                        key = "epmc:" + pmcid
                        if key in existing or key in candidates:
                            entry.setdefault("also_matched", []).append(key)
                            if key in candidates:
                                candidates[key]["matched"].append(match)
                            else:
                                links.append({"doc_id": key, **match})
                            continue
                        candidates[key] = {"result": result, "matched": [match]}
                        entry["selected"].append(key)
                        taken += 1
                except FetchError as exc:
                    entry["error"] = str(exc)
                log.append(entry)
        return candidates, log, links

    def acquire(self, candidates, workers=4, progress=print):
        """Fetch and parse full text for each candidate; checkpoint per document."""
        outcomes = {}

        def one(item):
            key, candidate = item
            out_path = self.work / "docs" / (key.replace(":", "_") + ".json")
            if out_path.exists():
                return key, json.loads(out_path.read_text(encoding="utf-8"))["status"]
            status = self._acquire_one(key, candidate)
            out_path.write_text(json.dumps(status, ensure_ascii=False), encoding="utf-8")
            return key, status["status"]

        done = 0
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for key, status in pool.map(one, candidates.items()):
                outcomes[key] = status
                done += 1
                if done % 100 == 0:
                    progress(f"europepmc: {done}/{len(candidates)} documents processed")
        return outcomes

    def _acquire_one(self, key, candidate):
        result = candidate["result"]
        pmcid = result["pmcid"]
        evidence_type = classify(result)
        corr = corrections(result)
        doc = {
            "doc_id": key, "provider": "europepmc", "title": clean_text(result.get("title", "")),
            "identifiers": {"pmcid": pmcid, "pmid": result.get("pmid"), "doi": (result.get("doi") or "").lower() or None},
            "journal": (result.get("journalInfo") or {}).get("journal", {}).get("title"),
            "published": result.get("firstPublicationDate"),
            "evidence_type": evidence_type,
            "matched": candidate["matched"],
            "corrections": corr,
            "cited_by": int(result.get("citedByCount") or 0),
            "url": f"https://europepmc.org/article/PMC/{pmcid}",
            "pmc_url": f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/",
            "acquisition_endpoint": f"{BASE}/{pmcid}/fullTextXML",
            "acquired": today(),
            "search_license": normalize_license(result.get("license")),
        }
        if evidence_type == "retracted" or any((c["type"] or "").lower().startswith("retraction in") for c in corr):
            return {"status": "excluded", "reason": "retracted", "doc": doc}
        if any((c["type"] or "").lower().startswith("expression of concern") for c in corr):
            doc["publication_status"] = "expression_of_concern"
        elif any((c["type"] or "").lower().startswith(("erratum in", "correction in", "corrected and republished")) for c in corr):
            doc["publication_status"] = "published_with_correction"
        else:
            doc["publication_status"] = "published"
        try:
            raw, meta = self.client.get(doc["acquisition_endpoint"], max_bytes=25_000_000)
        except FetchError as exc:
            return {"status": "unavailable", "reason": f"full text unavailable: {exc}"[:300], "doc": doc}
        doc["raw_sha256"] = meta["sha256"]
        doc["raw_bytes"] = meta["bytes"]
        try:
            article, units, stats = parse_article(raw, doc)
        except Exception as exc:  # malformed XML is logged, never guessed
            return {"status": "parse_failed", "reason": f"{type(exc).__name__}: {exc}"[:300], "doc": doc}
        license_id = article.get("license") or doc["search_license"]
        doc.update({
            "title": article.get("title") or doc["title"],
            "publisher": article.get("publisher") or article.get("journal") or doc.get("journal"),
            "journal": article.get("journal") or doc.get("journal"),
            "authors": article.get("authors", []),
            "author_count": article.get("author_count", 0),
            "license": license_id,
            "license_url": article.get("license_url"),
            "license_statement": article.get("license_statement"),
            "article_type": article.get("article_type"),
            "published": article.get("published") or doc["published"],
            "parse_stats": stats,
        })
        if license_id not in DEFAULT_EDITION_LICENSES:
            return {"status": "excluded", "reason": f"licence in XML not default-edition compatible: {license_id}", "doc": doc}
        units = [u for u in units if not any(SKIP_SECTION.search(part) for part in u["location"]["section_path"])]
        if not stats.get("has_body"):
            doc["access"] = "abstract"
            units = [u for u in units if u["kind"] == "abstract"]
        else:
            doc["access"] = "full_text"
        if not units:
            return {"status": "excluded", "reason": "no extractable text", "doc": doc}
        return {"status": "acquired", "doc": doc, "units": units}
