"""Bounded public-topic acquisition, isolated from patient/session requests."""

import hashlib
from urllib.parse import urlsplit
from xml.etree import ElementTree

from bs4 import BeautifulSoup

ENDPOINT = "https://wsearch.nlm.nih.gov/ws/query"
POLICY = "https://medlineplus.gov/about/developers/webservices/"
PUBLIC_TOPICS = ("asthma", "diabetes", "anemia", "tooth disorders", "gum disease", "oral cancer",
                 "high blood pressure", "heart diseases", "kidney diseases", "skin conditions")


def parse_topics(raw):
    if len(raw) > 2_000_000 or b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise ValueError("Unsupported or oversized service XML")
    root = ElementTree.fromstring(raw)
    if root.tag != "nlmSearchResult":
        raise ValueError("Unexpected MedlinePlus service document")
    items = []
    for document in root.findall("./list/document"):
        url = document.get("url", "")
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname != "medlineplus.gov" or parsed.username or parsed.password or parsed.port:
            raise ValueError("External content is not a MedlinePlus topic summary")
        fields = {node.get("name", "").casefold(): "".join(node.itertext()) for node in document.findall("content")}
        summary = fields.get("fullsummary", "")
        if not summary:
            continue
        soup = BeautifulSoup(summary, "html.parser")
        if soup.find(["script", "style", "iframe", "object"]):
            raise ValueError("Unexpected active summary markup")
        for node in soup.find_all(["p", "li", "h2", "h3"]):
            node.insert_after("\n\n")
        text = "\n\n".join(" ".join(part.split()) for part in soup.get_text().split("\n\n") if part.strip())
        title = BeautifulSoup(fields.get("title", ""), "html.parser").get_text(" ", strip=True)
        if not title or not text:
            raise ValueError("Incomplete topic summary")
        items.append({"source_id": "medlineplus_" + hashlib.sha256(url.encode()).hexdigest()[:16],
                      "title": title, "url": url, "text": text,
                      "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                      "source_class": "patient_education", "jurisdiction": "US",
                      "attribution": "Information from MedlinePlus.gov. MedlinePlus does not endorse Aster.",
                      "clinical_review_status": "pending", "runtime_admitted": False,
                      "training_approved": False, "rights_evidence_url": POLICY,
                      "external_links_followed": False})
    return items
