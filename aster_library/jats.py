"""JATS/NLM XML -> document metadata + section-aware evidence units.

Tables are flattened row-wise and marked ``table_flattened`` (cell spans and
nested headers may be misaligned; numeric values must be checked against the
original). Reference lists are counted but not indexed as evidence.
"""
import re

from defusedxml import ElementTree as ET

from aster_library.model import chunk_paragraphs, clean_text, make_unit, normalize_license

XLINK = "{http://www.w3.org/1999/xlink}href"
SKIP_TAGS = {"xref-group", "ref-list", "fn-group", "ack", "glossary", "app-group", "supplementary-material"}
INLINE_DROP = {"xref", "inline-formula", "disp-formula", "fn", "table-wrap-foot"}


def _local(tag):
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def _text(node, drop=INLINE_DROP):
    """Collect text, dropping citation markers/formulas but keeping tails."""
    if node is None:
        return ""
    parts = [node.text or ""]
    for child in node:
        name = _local(child.tag)
        if name == "xref":
            pass  # drop citation marker text like "[12]"
        elif name in drop or name in {"table-wrap", "fig", "list"} and node.tag != child.tag:
            if name == "list":
                parts.append(" " + "; ".join(_text(item) for item in child if _local(item.tag) == "list-item") + " ")
        else:
            parts.append(_text(child, drop))
        parts.append(child.tail or "")
    text = "".join(parts)
    text = re.sub(r"\s*\[\s*[,–\-\s]*\]", "", text)  # empty brackets left by dropped xrefs
    text = re.sub(r"\(\s*[,;–\-\s]*\)", "", text)
    text = re.sub(r"\s+", " ", text)
    return re.sub(r"\s+([.,;:])", r"\1", text).strip()


def parse_xml(raw):
    raw = re.sub(rb"<!DOCTYPE[^>]*>", b"", raw, count=1)
    return ET.fromstring(raw)


def _find(node, path):
    for child in node.iter():
        if _local(child.tag) == path:
            return child
    return None


def metadata(root):
    meta = {}
    article_meta = _find(root, "article-meta")
    journal_meta = _find(root, "journal-meta")
    meta["article_type"] = root.get("article-type", "")
    if article_meta is not None:
        for aid in article_meta.findall("./{*}article-id") + article_meta.findall("./article-id"):
            kind = aid.get("pub-id-type")
            if kind in {"pmcid", "pmid", "doi"} and aid.text:
                meta.setdefault(kind, aid.text.strip())
        title = _find(article_meta, "article-title")
        meta["title"] = _text(title)
        subjects = [s.text.strip() for s in article_meta.iter() if _local(s.tag) == "subject" and s.text]
        meta["subjects"] = subjects
        dates = {}
        for pub in article_meta.iter():
            if _local(pub.tag) == "pub-date":
                year = next((c.text for c in pub if _local(c.tag) == "year"), None)
                month = next((c.text for c in pub if _local(c.tag) == "month"), "1")
                day = next((c.text for c in pub if _local(c.tag) == "day"), "1")
                if year and year.strip().isdigit():
                    try:
                        dates[pub.get("pub-type") or pub.get("date-type") or "pub"] = (
                            f"{int(year):04d}-{int(month):02d}-{int(day):02d}")
                    except ValueError:
                        dates[pub.get("pub-type") or "pub"] = f"{int(year):04d}-01-01"
        meta["published"] = dates.get("epub") or dates.get("pub") or dates.get("ppub") or next(iter(dates.values()), None)
        license_node = _find(article_meta, "license")
        license_url = None
        license_text = ""
        if license_node is not None:
            license_url = license_node.get(XLINK) or license_node.get("href")
            for child in license_node.iter():
                if _local(child.tag) == "license_ref" and child.text:
                    license_url = license_url or child.text.strip()
            license_text = _text(license_node)
        meta["license_url"] = license_url
        meta["license_statement"] = license_text[:600]
        meta["license"] = normalize_license(license_url) or normalize_license(license_text)
        if not meta["license"] and re.search(r"creative commons attribution (?:4\.0 )?(?:international )?licen[cs]e", license_text, re.I) \
                and not re.search(r"non-?commercial|noderiv|no derivatives|sharealike|share alike", license_text, re.I):
            meta["license"] = "CC-BY-4.0"
        authors = []
        for contrib in article_meta.iter():
            if _local(contrib.tag) == "contrib" and contrib.get("contrib-type") == "author":
                surname = next((c.text for c in contrib.iter() if _local(c.tag) == "surname"), None)
                given = next((c.text for c in contrib.iter() if _local(c.tag) == "given-names"), "")
                if surname:
                    authors.append(f"{surname} {given or ''}".strip())
        meta["authors"] = authors[:12]
        meta["author_count"] = len(authors)
        related = []
        for rel in article_meta.iter():
            if _local(rel.tag) == "related-article":
                related.append({"type": rel.get("related-article-type"), "href": rel.get(XLINK)})
        meta["related_articles"] = related
    if journal_meta is not None:
        meta["journal"] = _text(_find(journal_meta, "journal-title"))
        meta["publisher"] = _text(_find(journal_meta, "publisher-name"))
    return meta


def _sections(node, path, out):
    """Depth-first: yield (section_path, paragraphs, tables, captions)."""
    paragraphs, extras = [], []
    for child in node:
        name = _local(child.tag)
        if name in SKIP_TAGS:
            continue
        if name == "sec":
            title = _text(next((c for c in child if _local(c.tag) == "title"), None)) or "Section"
            _sections(child, path + [title[:120]], out)
        elif name == "p":
            text = _text(child)
            if len(text) > 40:
                paragraphs.append(text)
            for nested in child:
                if _local(nested.tag) in {"table-wrap", "fig"}:
                    extras.append(nested)
        elif name in {"table-wrap", "fig"}:
            extras.append(child)
        elif name == "list":
            items = [_text(item) for item in child if _local(item.tag) == "list-item"]
            if items:
                paragraphs.append("; ".join(i for i in items if i))
        elif name in {"boxed-text", "disp-quote"}:
            _sections(child, path + ["Box"], out)
    out.append((path, paragraphs, extras))


def _table_text(table_wrap):
    label = _text(next((c for c in table_wrap if _local(c.tag) == "label"), None))
    caption = _text(next((c for c in table_wrap if _local(c.tag) == "caption"), None))
    rows = []
    for row in table_wrap.iter():
        if _local(row.tag) == "tr":
            cells = [_text(cell) for cell in row if _local(cell.tag) in {"td", "th"}]
            if any(cells):
                rows.append(" | ".join(cells))
    return label, caption, rows


def parse_article(raw, doc):
    """Return (metadata, units, stats). ``doc`` supplies doc_id and title fallbacks."""
    root = parse_xml(raw)
    meta = metadata(root)
    doc = {**doc, "title": meta.get("title") or doc.get("title", "")}
    units, stats = [], {"paragraph_units": 0, "table_units": 0, "caption_units": 0, "references": 0}
    abstract = _find(root, "abstract")
    if abstract is not None:
        abstract_paras = [_text(p) for p in abstract.iter() if _local(p.tag) == "p"]
        for index, text in chunk_paragraphs(abstract_paras):
            units.append(make_unit(doc, section_path=["Abstract"], paragraph=index, text=text, kind="abstract"))
    body = _find(root, "body")
    sections = []
    if body is not None:
        _sections(body, [], sections)
    for path, paragraphs, extras in sections:
        for index, text in chunk_paragraphs(paragraphs):
            units.append(make_unit(doc, section_path=path or ["Body"], paragraph=index, text=text))
            stats["paragraph_units"] += 1
        for extra in extras:
            if _local(extra.tag) == "table-wrap":
                label, caption, rows = _table_text(extra)
                if rows:
                    body_text = (f"{label}. {caption}\n" if caption else f"{label}\n") + "\n".join(rows[:60])
                    units.append(make_unit(doc, section_path=(path or ["Body"]) + [label or "Table"], paragraph=0,
                                           text=body_text[:4000], kind="table", reliability="table_flattened"))
                    stats["table_units"] += 1
            else:
                label = _text(next((c for c in extra if _local(c.tag) == "label"), None))
                caption = _text(next((c for c in extra if _local(c.tag) == "caption"), None))
                if len(caption) > 60:
                    units.append(make_unit(doc, section_path=(path or ["Body"]) + [label or "Figure"], paragraph=0,
                                           text=f"{label}. {caption}" if label else caption, kind="figure_caption"))
                    stats["caption_units"] += 1
    stats["references"] = sum(1 for n in root.iter() if _local(n.tag) == "ref")
    stats["has_body"] = body is not None and stats["paragraph_units"] > 0
    for unit in units:
        unit["text"] = clean_text(unit["text"])
    return meta, units, stats
