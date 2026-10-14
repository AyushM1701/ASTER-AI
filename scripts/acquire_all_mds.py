"""Reproducible, bounded nine-specialty Europe PMC research acquisition."""

import argparse
import hashlib
import http.client
import json
import re
import threading
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

from backend.app.services.teaching import teaching_terms
from scripts.build_mds_research import extract_sections, license_evidence, normalized

ROOT = Path(__file__).resolve().parents[1]
API = "https://www.ebi.ac.uk/europepmc/webservices/rest/"
SUPPORTED = {"CC-BY-4.0", "CC-BY-NC-4.0", "CC-BY-SA-4.0", "CC-BY-NC-SA-4.0"}


def topic_title_match(title, topic):
    """A discovery gate, not an assessment of clinical relevance or truth."""
    generic = teaching_terms("oral dental public health dentistry tooth teeth child children")
    focus = teaching_terms(topic) - generic
    present = teaching_terms(title)
    if "india" in focus and "india" not in present:
        return False
    return bool(focus) and len(focus & present) >= max(1, (len(focus) + 1) // 2)


def candidate_allowed(row):
    if not re.fullmatch(r"PMC\d+", row.get("pmcid", "")):
        return "No valid full-text identifier"
    if row.get("isOpenAccess") != "Y":
        return "Not in open-access subset"
    types = " ".join(row.get("pubTypeList", {}).get("pubType", [])).casefold()
    if "preprint" in types or not any(t in types for t in ("review", "journal article")):
        return "Not a journal review/article"
    if row.get("commentCorrectionList") or re.search(
        r"\b(retract\w*|withdraw\w*|corrigendum|erratum|expression of concern)\b",
        row.get("title", ""), re.I,
    ):
        return "Correction/retraction/withdrawal requires human assessment"
    return None


def inspect_article(article, pmcid):
    ids = {normalized(n).removeprefix("PMC") for n in
           article.findall('./front/article-meta/article-id')
           if n.get("pub-id-type") in {"pmc", "pmcid"}}
    if pmcid.removeprefix("PMC") not in ids:
        raise ValueError("Article identifier does not match the requested snapshot")
    if any(re.search(r"retract|withdraw|correct|concern", n.get("related-article-type", ""), re.I)
           for n in article.findall(".//related-article")):
        raise ValueError("Related correction/retraction requires human assessment")
    rights = " ".join(normalized(n) for path in (".//permissions", ".//custom-meta-group")
                     for n in article.findall(path))
    if re.search(r"(?:AI|artificial intelligence|machine learning).{0,100}(?:prohibit|not permitted|not allowed)|"
                 r"(?:prohibit|not permitted|not allowed).{0,100}(?:AI training|artificial intelligence|machine learning)",
                 rights, re.I):
        raise ValueError("Additional AI reuse restriction requires assessment")
    evidence = license_evidence(article)
    if evidence["license"] not in SUPPORTED:
        raise ValueError("Licence version not supported by Aster's current source validator")
    if not extract_sections(article):
        raise ValueError("No complete article-body paragraphs")
    return evidence


def fetch(url):
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Aster-Educational-Source-Acquisition/1.0"})
            with urllib.request.urlopen(request, timeout=35) as response:
                return response.read()
        except (OSError, TimeoutError, http.client.HTTPException):
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))


def acquire(config, output, per_topic=2, page_size=30):
    """Resume cached snapshots, keep search provenance, and cap original full texts."""
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT):
        raise ValueError("Acquisition output must stay in the project")
    output.mkdir(parents=True, exist_ok=True)
    cache = output / "raw"
    cache.mkdir(exist_ok=True)
    specs = json.loads(Path(config).read_text(encoding="utf-8"))
    docs, searches, outcomes = {}, [], []
    lock = threading.Lock()
    today = date.today().isoformat()

    def task(specialty, topic):
        query = (f'({topic["query"]}) AND OPEN_ACCESS:Y AND PUB_TYPE:review '
                 f'AND FIRST_PDATE:[2000-01-01 TO {today}]')
        params = urllib.parse.urlencode({"query": query, "format": "json", "pageSize": page_size,
                                       "resultType": "core"})
        search_path = cache / (topic["id"] + "-" + hashlib.sha256(params.encode()).hexdigest()[:10] + ".search.json")
        try:
            if not search_path.exists():
                search_path.write_bytes(fetch(API + "search?" + params))
            result = json.loads(search_path.read_bytes())
        except (OSError, ValueError, http.client.HTTPException) as exc:
            return {"topic_id": topic["id"], "error": str(exc), "query": query}, [], []
        found, decisions = [], []
        for row in result.get("resultList", {}).get("result", []):
            if len(found) >= per_topic:
                break
            pmcid = row.get("pmcid", "")
            decision = {"topic_id": topic["id"], "pmcid": pmcid, "title": row.get("title"),
                        "url": f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/" if pmcid else None}
            reason = candidate_allowed(row)
            if not reason and not topic_title_match(row.get("title", ""), topic["title"]):
                reason = "No specific topic anchor in article title; search hit alone is insufficient"
            if reason:
                decisions.append({**decision, "status": "excluded", "reason": reason})
                continue
            try:
                xml_path = cache / (pmcid + ".xml")
                if not xml_path.exists():
                    xml_path.write_bytes(fetch(API + pmcid + "/fullTextXML"))
                raw = xml_path.read_bytes()
                article = ET.fromstring(raw)
                evidence = inspect_article(article, pmcid)
                title = normalized(article.find("./front/article-meta/title-group/article-title"))
                if not title or not row.get("firstPublicationDate"):
                    raise ValueError("Missing title or publication date")
                # Keep the complete structured abstract separately for study appraisal;
                # never label automatically inferred patient/model details as reviewed.
                abstract = normalized(article.find("./front/article-meta/abstract"))
                licence_path = cache / (pmcid + ".license.xml")
                licence_path.write_text(evidence["license_evidence"], encoding="utf-8")
                author_names = [normalized(n.find("name")) for n in
                                article.findall("./front/article-meta/contrib-group/contrib")
                                if n.get("contrib-type") == "author"]
                author_names = [n for n in author_names if n] or [row.get("authorString", "Authors in original article")]
                doc = {
                    "id": "mds-all-" + pmcid.lower(), "pmcid": pmcid, "title": title,
                    "url": f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/",
                    "publisher": normalized(article.find("./front/journal-meta/publisher/publisher-name"))
                        or row.get("journalInfo", {}).get("journal", {}).get("title", "Publisher in original JATS"),
                    "authors": author_names, "doi": row.get("doi"),
                    "source_date": row["firstPublicationDate"], "retrieved_date": today,
                    "raw_snapshot_path": xml_path.relative_to(ROOT).as_posix(),
                    "raw_sha256": hashlib.sha256(raw).hexdigest(),
                    **{k: evidence[k] for k in ("license", "license_url")},
                    "license_snapshot_path": licence_path.relative_to(ROOT).as_posix(),
                    "license_snapshot_sha256": hashlib.sha256(licence_path.read_bytes()).hexdigest(),
                    "subjects": [specialty["id"], topic["title"]], "syllabus_ids": [topic["id"]],
                    "study_type": "unknown", "study_design": "Journal review; synthesis design not independently appraised",
                    "study_context": f'Review scope: {title}. Population and experimental models require checking in the original article.',
                    "limitations": ["Review findings depend on the included studies; quality, recency and applicability have not been independently graded.",
                                    "Research supplement, not a complete textbook, current guideline or patient-specific treatment advice."],
                    "approval": "developer_reviewed", "clinical_review": False,
                    "source_review_method": "Automated identifier, rights, withdrawal and complete-paragraph checks; no medical appraisal",
                    "publication_types": row.get("pubTypeList", {}).get("pubType", []),
                    "abstract_for_appraisal": abstract,
                }
                # An unusually long title could make the required context unchunkable.
                from scripts.build_mds_research import context_prefix
                if len(context_prefix(doc)) > 1200:
                    raise ValueError("Study context exceeds the chunk budget")
                found.append(doc)
                decisions.append({**decision, "status": "selected", "license": doc["license"]})
            except (OSError, ValueError, ET.ParseError, http.client.HTTPException) as exc:
                decisions.append({**decision, "status": "excluded", "reason": str(exc)})
        search = {"topic_id": topic["id"], "specialty_id": specialty["id"], "query": query,
                  "api_url": API + "search?" + params, "retrieved_date": today,
                  "hit_count": result.get("hitCount"), "candidate_limit": page_size,
                  "candidates_examined": len(decisions), "selected": len(found),
                  "snapshot_path": search_path.relative_to(ROOT).as_posix(),
                  "snapshot_sha256": hashlib.sha256(search_path.read_bytes()).hexdigest()}
        return search, found, decisions

    jobs = [(s, t) for s in specs["specialties"] for t in s["topics"]]
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(task, s, t) for s, t in jobs]
        for future in as_completed(futures):
            search, found, decisions = future.result()
            with lock:
                searches.append(search)
                outcomes.extend(decisions)
                for doc in found:
                    if doc["id"] in docs:
                        old = docs[doc["id"]]
                        if old["raw_sha256"] != doc["raw_sha256"]:
                            raise ValueError("Article snapshot changed during acquisition")
                        for key in ("subjects", "syllabus_ids"):
                            old[key] = sorted(set(old[key]) | set(doc[key]))
                    else:
                        docs[doc["id"]] = doc
                progress = {"version": specs["version"], "documents": sorted(docs.values(), key=lambda d: d["id"]),
                            "searches": sorted(searches, key=lambda s: s["topic_id"]), "decisions": outcomes,
                            "limits": {"per_topic": per_topic, "search_page_size": page_size,
                                       "exhaustive": False, "clinical_review": False}}
                (output / "acquisition.json").write_text(json.dumps(progress, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f'{len(searches)}/{len(jobs)} topics; {len(docs)} unique selected articles', flush=True)
    return progress


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/all_mds_topics.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--per-topic", type=int, default=2)
    parser.add_argument("--page-size", type=int, default=30)
    args = parser.parse_args()
    if not 1 <= args.per_topic <= 10 or not 1 <= args.page_size <= 100:
        parser.error("Use a bounded acquisition: 1–10 articles per topic, 1–100 candidates")
    acquire(args.config, args.output, args.per_topic, args.page_size)
