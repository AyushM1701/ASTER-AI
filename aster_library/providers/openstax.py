"""OpenStax textbooks from the official CNXML source repositories on GitHub.

Only text (CNXML) is fetched; figures/media are excluded. The licence is read
per book from its collection metadata (CC BY 4.0 -> default edition,
CC BY-NC-SA 4.0 -> noncommercial pack). Attribution follows OpenStax's
required form: book title, authors (OpenStax), licence and openstax.org URL.
"""
import json
import re
from pathlib import Path

from defusedxml import ElementTree as ET

from aster_library.common import WORK, log, register
from aster_library.model import chunk_paragraphs, make_unit, normalize_license, today
from aster_library.net import FetchError

REPOS = [
    "osbooks-anatomy-physiology", "osbooks-microbiology", "osbooks-biology-bundle", "osbooks-chemistry-bundle",
    "osbooks-nursing-external-bundle", "osbooks-psychology", "osbooks-lifespan-development", "osbooks-neuroscience",
    "osbooks-introductory-statistics-bundle", "osbooks-statistics", "osbooks-organic-chemistry",
]
# Collections unrelated to health sciences inside multi-book bundles are skipped.
SKIP_COLLECTIONS = re.compile(r"business-statistics|chemistry-atoms-first|preparing-for-college|ap-", re.I)
CNX = "{http://cnx.rice.edu/cnxml}"
MD = "{http://cnx.rice.edu/mdml}"
COL = "{http://cnx.rice.edu/collxml}"


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.casefold()).strip("-")


def walk_collection(content, path, out):
    for child in content:
        if child.tag == COL + "module":
            out.append((list(path), child.get("document")))
        elif child.tag == COL + "subcollection":
            title = child.findtext(MD + "title") or ""
            inner = child.find(COL + "content")
            if inner is not None:
                walk_collection(inner, path + [title], out)


def node_text(node):
    parts = [node.text or ""]
    for child in node:
        tag = child.tag.replace(CNX, "")
        if tag in {"figure", "media", "image", "link"} and tag != "link":
            pass
        elif tag == "footnote":
            pass
        else:
            parts.append(node_text(child))
        parts.append(child.tail or "")
    return re.sub(r"\s+", " ", "".join(parts)).strip()


def module_sections(root):
    """Return (title, [(section_title, paragraphs)], glossary)."""
    title = root.findtext(f".//{MD}title") or root.findtext(f"{CNX}title") or ""
    content = root.find(CNX + "content")
    sections = []

    def visit(node, heading):
        paragraphs = []
        for child in node:
            tag = child.tag.replace(CNX, "")
            if tag == "section":
                visit(child, child.findtext(CNX + "title") or heading)
            elif tag == "para":
                text = node_text(child)
                if len(text) > 30:
                    paragraphs.append(text)
            elif tag == "list":
                items = [node_text(i) for i in child if i.tag == CNX + "item"]
                if items:
                    paragraphs.append("; ".join(i for i in items if i))
            elif tag == "note":
                inner = " ".join(node_text(p) for p in child.iter(CNX + "para"))
                if len(inner) > 40:
                    paragraphs.append(inner)
            elif tag == "table":
                rows = [" | ".join(node_text(e) for e in row.iter(CNX + "entry")) for row in child.iter(CNX + "row")]
                if rows:
                    paragraphs.append(("[table] " + (child.findtext(CNX + "title") or "")).strip() + "\n" + "\n".join(rows[:40]))
        if paragraphs:
            sections.append((heading, paragraphs))

    if content is not None:
        visit(content, title)
    glossary = []
    for definition in root.iter(CNX + "definition"):
        term = node_text(definition.find(CNX + "term")) if definition.find(CNX + "term") is not None else ""
        meaning = node_text(definition.find(CNX + "meaning")) if definition.find(CNX + "meaning") is not None else ""
        if term and meaning:
            glossary.append(f"{term}: {meaning}")
    return title, sections, glossary


@register("openstax")
def acquire(client, refresh=False):
    out_dir = WORK / "openstax"
    out_dir.mkdir(parents=True, exist_ok=True)
    docs = []
    for repo in REPOS:
        try:
            tree = client.get_json(f"https://api.github.com/repos/openstax/{repo}/git/trees/main", {"recursive": "1"})
        except FetchError as exc:
            log(f"openstax: {repo} tree unavailable: {exc}")
            continue
        commit = tree.get("sha")
        paths = {item["path"] for item in tree.get("tree", [])}
        raw_base = f"https://raw.githubusercontent.com/openstax/{repo}/{commit}/"
        for collection_path in sorted(p for p in paths if p.startswith("collections/") and p.endswith(".collection.xml")):
            if SKIP_COLLECTIONS.search(collection_path):
                continue
            raw, _ = client.get(raw_base + collection_path)
            collection = ET.fromstring(raw)
            meta = collection.find(COL + "metadata")
            book = meta.findtext(MD + "title")
            slug = meta.findtext(MD + "slug") or slugify(book)
            license_node = meta.find(MD + "license")
            license_id = normalize_license(license_node.get("url") if license_node is not None else "")
            modules = []
            walk_collection(collection.find(COL + "content"), [], modules)
            log(f"openstax: {book} ({license_id}) — {len(modules)} modules")
            for chapter_path, module_id in modules:
                module_path = f"modules/{module_id}/index.cnxml"
                if module_path not in paths:
                    continue
                try:
                    body, meta_http = client.get(raw_base + module_path)
                    root = ET.fromstring(body)
                except (FetchError, ET.ParseError) as exc:
                    docs.append({"status": "parse_failed", "reason": str(exc)[:200], "doc": {"doc_id": f"openstax:{slug}:{module_id}"}})
                    continue
                title, sections, glossary = module_sections(root)
                doc = {
                    "doc_id": f"openstax:{slug}:{module_id}", "provider": "openstax",
                    "title": f"{book} — {title}", "book": book, "chapter_path": chapter_path,
                    "url": f"https://openstax.org/books/{slug}/pages/{slugify(title)}",
                    "source_url": f"https://github.com/openstax/{repo}/blob/{commit}/{module_path}",
                    "publisher": "OpenStax, Rice University", "jurisdiction": "International",
                    "content_class": "professional", "evidence_type": "textbook",
                    "published": None, "version": f"git {commit[:12]}", "acquired": today(),
                    "license": license_id, "license_url": license_node.get("url") if license_node is not None else None,
                    "attribution": f"Access for free at openstax.org. {book}, OpenStax, Rice University; {license_id}.",
                    "acquisition_endpoint": raw_base + module_path, "raw_sha256": meta_http["sha256"],
                    "access": "full_text", "publication_status": "published",
                }
                units = []
                for heading, paragraphs in sections:
                    for i, text in chunk_paragraphs(paragraphs, target=1000):
                        units.append(make_unit(doc, section_path=chapter_path + [heading], paragraph=i, text=text))
                for i, text in chunk_paragraphs(glossary, target=900):
                    units.append(make_unit(doc, section_path=chapter_path + [title, "Glossary"], paragraph=i, text=text, kind="glossary"))
                docs.append({"status": "acquired" if units else "excluded", "reason": None if units else "no text",
                             "doc": doc, "units": units})
    with (out_dir / "docs.jsonl").open("w", encoding="utf-8") as out:
        for item in docs:
            out.write(json.dumps(item, ensure_ascii=False) + "\n")
    (out_dir / "state.json").write_text(json.dumps({"last_run": today(), "documents": len(docs)}, indent=2), encoding="utf-8")
    log(f"openstax: wrote {len(docs)} module documents")


def load(work=WORK):
    path = Path(work) / "openstax" / "docs.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.exists() else []
