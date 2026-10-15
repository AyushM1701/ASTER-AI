"""MedlinePlus public-domain patient information.

1. Health-topic summaries from NLM's published daily XML bulk file
   (https://medlineplus.gov/xml.html). Bulk files are offered by NLM for reuse;
   one file is fetched per build (not crawled).
2. Medical-test pages under /lab-tests/ (public domain per
   https://medlineplus.gov/about/using/usingcontent/), fetched at <= 1 request/s,
   honouring robots.txt (``/lab-tests/`` is not disallowed).

Excluded by terms: A.D.A.M. encyclopedia, ASHP drug monographs, licensed images.
"""
import html
import json
import re
import time
from pathlib import Path

from bs4 import BeautifulSoup
from defusedxml import ElementTree as ET

from aster_library.common import WORK, log, register
from aster_library.model import chunk_paragraphs, clean_text, make_unit, today
from aster_library.net import FetchError

TERMS_URL = "https://medlineplus.gov/about/using/usingcontent/"
LICENSE = "MedlinePlus-public-domain"
ATTRIBUTION = "Courtesy of MedlinePlus from the National Library of Medicine"


def html_paragraphs(fragment):
    soup = BeautifulSoup(fragment, "html.parser")
    paragraphs = []
    for node in soup.find_all(["p", "li", "h3", "h4"]):
        text = clean_text(node.get_text(" "))
        if node.name in {"h3", "h4"} and text:
            paragraphs.append(text + ":")
        elif text and not node.find_parent("li") or node.name == "li":
            if len(text) > 15:
                paragraphs.append(("• " if node.name == "li" else "") + text)
    if not paragraphs:
        text = clean_text(soup.get_text(" "))
        if text:
            paragraphs = [text]
    return paragraphs


def latest_topics_url(client):
    body, _ = client.get("https://medlineplus.gov/xml.html", cache=False)
    match = re.search(rb'href="(https://medlineplus\.gov/xml/mplus_topics_(\d{4}-\d{2}-\d{2})\.xml)"', body)
    if not match:
        raise FetchError("MedlinePlus XML listing changed; topics file not found")
    return match.group(1).decode(), match.group(2).decode()


def parse_topics(raw, file_date, source_url):
    root = ET.fromstring(raw)
    docs = []
    for topic in root.iter("health-topic"):
        if topic.get("language") != "English":
            continue
        summary = topic.findtext("full-summary") or ""
        paragraphs = html_paragraphs(html.unescape(summary) if "&lt;" in summary else summary)
        if not paragraphs:
            continue
        doc = {
            "doc_id": f"medlineplus:topic:{topic.get('id')}",
            "provider": "medlineplus",
            "title": clean_text(topic.get("title")),
            "url": topic.get("url"),
            "publisher": "U.S. National Library of Medicine (MedlinePlus)",
            "jurisdiction": "US",
            "content_class": "patient",
            "evidence_type": "patient_summary",
            "published": None,
            "version": f"date-created {topic.get('date-created')}; bulk file {file_date}",
            "acquired": today(),
            "license": LICENSE,
            "license_url": TERMS_URL,
            "attribution": ATTRIBUTION,
            "acquisition_endpoint": source_url,
            "also_called": [clean_text(a.text) for a in topic.findall("also-called") if a.text],
            "groups": [clean_text(g.text) for g in topic.findall("group") if g.text],
            "mesh": [clean_text(d.text) for m in topic.findall("mesh-heading") for d in m.findall("descriptor") if d.text],
            "access": "full_text",
            "publication_status": "published",
        }
        units = [make_unit(doc, section_path=["Summary"], paragraph=i, text=t)
                 for i, t in chunk_paragraphs(paragraphs, target=900)]
        docs.append({"status": "acquired", "doc": doc, "units": units})
    return docs


LAB_SKIP = re.compile(r"^(references|related health topics|related medical tests|learn more|images)", re.I)


def parse_lab_page(raw, url):
    soup = BeautifulSoup(raw, "html.parser")
    title = clean_text((soup.find("h1") or soup.title).get_text(" ")) if (soup.find("h1") or soup.title) else url
    article = soup.find("article") or soup.find(id="mplus-content") or soup.find("main") or soup
    sections, current, paragraphs = [], "Overview", []
    for node in article.find_all(["h2", "h3", "p", "li"]):
        if node.name in {"h2", "h3"}:
            if paragraphs:
                sections.append((current, paragraphs))
            current, paragraphs = clean_text(node.get_text(" ")), []
            continue
        if LAB_SKIP.match(current) or node.find_parent(["nav", "footer"]):
            continue
        text = clean_text(node.get_text(" "))
        if len(text) > 25 and "Courtesy of" not in text:
            paragraphs.append(("• " if node.name == "li" else "") + text)
    if paragraphs:
        sections.append((current, paragraphs))
    reviewed = re.search(r"Last updated ([A-Z][a-z]+ \d{1,2}, \d{4})", soup.get_text(" "))
    return title, sections, reviewed.group(1) if reviewed else None


@register("medlineplus")
def acquire(client, refresh=False):
    out_dir = WORK / "medlineplus"
    (out_dir / "docs").mkdir(parents=True, exist_ok=True)
    url, file_date = latest_topics_url(client)
    raw, meta = client.get(url, max_bytes=80_000_000)
    terms, terms_meta = client.get(TERMS_URL)
    (out_dir / "terms-snapshot.html").write_bytes(terms)
    docs = parse_topics(raw, file_date, url)
    for item in docs:
        item["doc"]["raw_sha256"] = meta["sha256"]
    log(f"medlineplus: {len(docs)} English health-topic summaries from {url}")
    # Medical tests (public domain).
    index, _ = client.get("https://medlineplus.gov/lab-tests/")
    links = sorted(set(re.findall(rb'href="(https://medlineplus\.gov/lab-tests/[a-z0-9-]+/)"', index)))
    log(f"medlineplus: {len(links)} medical-test pages")
    for link in links:
        link = link.decode()
        try:
            body, page_meta = client.get(link)
        except FetchError as exc:
            docs.append({"status": "unavailable", "reason": str(exc)[:200], "doc": {"doc_id": "medlineplus:labtest:" + link}})
            continue
        title, sections, reviewed = parse_lab_page(body, link)
        slug = link.rstrip("/").rsplit("/", 1)[-1]
        doc = {
            "doc_id": f"medlineplus:labtest:{slug}", "provider": "medlineplus", "title": title, "url": link,
            "publisher": "U.S. National Library of Medicine (MedlinePlus)", "jurisdiction": "US",
            "content_class": "patient", "evidence_type": "patient_test_information",
            "published": None, "version": f"page last updated {reviewed}" if reviewed else "undated page",
            "acquired": today(), "license": LICENSE, "license_url": TERMS_URL, "attribution": ATTRIBUTION,
            "acquisition_endpoint": link, "raw_sha256": page_meta["sha256"], "access": "full_text",
            "publication_status": "published",
        }
        units = []
        for heading, paragraphs in sections:
            for i, text in chunk_paragraphs(paragraphs, target=900):
                units.append(make_unit(doc, section_path=[heading], paragraph=i, text=text))
        docs.append({"status": "acquired" if units else "excluded", "reason": None if units else "no text", "doc": doc, "units": units})
        time.sleep(0.05)
    with (out_dir / "docs.jsonl").open("w", encoding="utf-8") as out:
        for item in docs:
            out.write(json.dumps(item, ensure_ascii=False) + "\n")
    (out_dir / "state.json").write_text(json.dumps({"last_run": today(), "topics_file": url,
                                                    "documents": len(docs)}, indent=2), encoding="utf-8")
    log(f"medlineplus: wrote {len(docs)} documents")


def load(work=WORK):
    path = Path(work) / "medlineplus" / "docs.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
