"""Acquire and build immutable article-licensed MDS research evidence.

Full JATS snapshots are retained for audit. Only complete article-body paragraphs
enter retrieval; figures, tables, quotations, supplements and references do not.
Unknown or NoDerivatives licenses are bibliography-only. Research context is
repeated in every chunk, not merely stored in a sidecar.
"""

import argparse
import hashlib
import json
import re
import sys
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.services.retrieval import Reference  # noqa: E402
from scripts.build_mbbs_library import sha256, snapshot_path, split_context  # noqa: E402

RESEARCH_HOSTS = {"pmc.ncbi.nlm.nih.gov"}
SKIP = {
    "fig",
    "table-wrap",
    "table",
    "ref-list",
    "disp-quote",
    "supplementary-material",
    "graphic",
    "media",
    "boxed-text",
}


def local_tag(element):
    return element.tag.rsplit("}", 1)[-1]


def plain(element):
    if element is None:
        return ""
    parts = [element.text or ""]
    for child in element:
        if local_tag(child) not in SKIP:
            parts.append(plain(child))
        parts.append(child.tail or "")
    return "".join(parts)


def normalized(element):
    return " ".join(plain(element).split())


def license_evidence(article):
    nodes = article.findall("./front/article-meta/permissions/license")
    if not nodes:
        raise ValueError("No article-level license evidence")
    evidence = "\n".join(ET.tostring(n, encoding="unicode") for n in nodes)
    if re.search(r'by[^"<>\s]*-nd/|No.?Deriv|no modifications|no derivatives', evidence, re.I):
        raise ValueError("No derivatives license: bibliography only")
    matches = set(
        re.findall(r"creativecommons.org/licenses/(by(?:-nc)?(?:-sa)?)/(\d\.\d)", evidence)
    )
    # Some JATS licenses spell out the full identifier and version without a link.
    for kind, slug in [
        ("Attribution-NonCommercial-ShareAlike", "by-nc-sa"),
        ("Attribution-NonCommercial", "by-nc"),
        ("Attribution-ShareAlike", "by-sa"),
        ("Attribution", "by"),
    ]:
        match = re.search(r"Creative Commons " + kind + r" (\d\.\d)", normalized(nodes[0]), re.I)
        if match:
            matches.add((slug, match.group(1)))
            break
    if len(matches) != 1:
        raise ValueError("Unverified or ambiguous article license/version")
    slug, version = next(iter(matches))
    if version not in {"2.0", "2.5", "3.0", "4.0"}:
        raise ValueError("Unsupported article license version")
    return {
        "license": "CC-" + slug.upper() + "-" + version,
        "license_url": f"https://creativecommons.org/licenses/{slug}/{version}/",
        "license_evidence": evidence,
    }


def extract_sections(article):
    sections = []

    def visit(node, headings):
        if local_tag(node) in SKIP:
            return
        if local_tag(node) == "sec":
            title = normalized(node.find("title")) or "Untitled section"
            headings = headings + [title]
        label = " / ".join(headings) or "Article body"
        if re.search(
            r"references|acknowledg|author contribution|conflict of interest|funding|supplement|data availability|copyright",
            label,
            re.I,
        ):
            return
        pending = []

        def flush():
            if pending:
                sections.append(
                    {"title": label, "paragraphs": pending.copy(), "section_id": node.get("id", "")}
                )
                pending.clear()

        for child in node:
            tag = local_tag(child)
            if tag == "p":
                # Exclude whole paragraphs containing third-party objects/quotes;
                # no clipped sentence masquerades as complete original prose.
                if any(local_tag(n) in SKIP for n in child.iter()):
                    continue
                text = normalized(child)
                if len(text) >= 10:
                    pending.append(text)
            elif tag == "sec":
                flush()
                visit(child, headings)
        flush()

    body = article.find("body")
    if body is None:
        raise ValueError("Missing article body")
    visit(body, [])
    return sections


def context_prefix(doc):
    return (
        f"[Research context: {doc['source_date']}; {doc['study_design']}; {doc['study_type']}. "
        f"{doc['study_context']} Limitations: {' '.join(doc['limitations'])} "
        "Educational research evidence; not a clinical recommendation. Faculty review pending.]\n\n"
    )


def validate_document(doc, root):
    location = urlsplit(doc["url"])
    if (
        location.scheme != "https"
        or location.hostname not in RESEARCH_HOSTS
        or location.username
        or location.password
    ):
        raise ValueError("Unverified article host")
    if not re.fullmatch(r"PMC\d+", doc["pmcid"]) or location.path != f"/articles/{doc['pmcid']}/":
        raise ValueError("Article identifier mismatch")
    path = snapshot_path(doc["raw_snapshot_path"], root)
    if sha256(path) != doc["raw_sha256"]:
        raise ValueError("Article snapshot hash mismatch")
    article = ET.parse(path).getroot()
    evidence = license_evidence(article)
    if doc.get("license_snapshot_path"):
        license_path = snapshot_path(doc["license_snapshot_path"], root)
        if sha256(license_path) != doc.get("license_snapshot_sha256"):
            raise ValueError("Article license snapshot hash mismatch")
        if license_path.read_text(encoding="utf-8") != evidence["license_evidence"]:
            raise ValueError("Article license snapshot differs from original JATS permissions")
    if any(doc[k] != evidence[k] for k in ("license", "license_url")):
        raise ValueError("Configured license differs from article evidence")
    if doc.get("approval") != "developer_reviewed" or doc.get("clinical_review") is not False:
        raise ValueError("Developer review required; no clinical review may be claimed")
    for key in (
        "source_date",
        "authors",
        "subjects",
        "syllabus_ids",
        "study_design",
        "study_context",
        "limitations",
    ):
        if not doc.get(key):
            raise ValueError(f"Missing research context: {key}")
    if doc["study_type"] not in {"human", "animal", "invitro", "mixed", "unknown"}:
        raise ValueError("Unknown study type")
    if len(context_prefix(doc)) > 1200:
        raise ValueError("Research context too long")
    return article, evidence


def build_release(documents, output, root=ROOT, bibliography=None, syllabus=None):
    output = Path(output).resolve()
    if output.exists():
        raise ValueError("Release exists; choose a new immutable version")
    records, sources, chunks, source_meta, exclusions, skipped = [], [], {}, {}, [], []
    seen = set()
    for doc in documents:
        if doc["id"] in seen:
            raise ValueError("Duplicate source ID")
        seen.add(doc["id"])
        article, evidence = validate_document(doc, root)
        prefix = context_prefix(doc)
        basis = {
            "type": "open_license",
            "approved_host": urlsplit(doc["url"]).hostname,
            "license": doc["license"],
            "license_url": doc["license_url"],
            "snapshot_sha256": doc["raw_sha256"],
            "clinical_review": False,
            "material_type": "research",
        }
        checksums = []
        for section_index, section in enumerate(extract_sections(article)):
            if doc.get("include_section_patterns") and not any(
                re.search(pattern, section["title"], re.I)
                for pattern in doc["include_section_patterns"]
            ):
                skipped.append(
                    {
                        "source_id": doc["id"],
                        "section": section["title"],
                        "reason": "Outside curated source section scope",
                    }
                )
                continue
            affected = [
                (p, flag)
                for p in section["paragraphs"]
                for flag in doc.get("excluded_paragraph_patterns", [])
                if re.search(flag["pattern"], p, re.I)
            ]
            if affected:
                # Hold the entire affected section, including its neighboring
                # qualifying paragraphs. Retain exact paragraph hashes in audit.
                for p, flag in affected:
                    exclusions.append(
                        {
                            "source_id": doc["id"],
                            "section": section["title"],
                            "paragraph_sha256": hashlib.sha256(p.encode()).hexdigest(),
                            "reason": flag["reason"],
                            "runtime_policy": "exclude",
                            "clinical_review": False,
                        }
                    )
                skipped.append(
                    {
                        "source_id": doc["id"],
                        "section": section["title"],
                        "reason": "Source discrepancy; entire section excluded",
                    }
                )
                continue
            try:
                contexts = split_context(section["paragraphs"], limit=4000 - len(prefix))
            except ValueError as exc:
                skipped.append(
                    {"source_id": doc["id"], "section": section["title"], "reason": str(exc)}
                )
                continue
            for context_index, context in enumerate(contexts):
                record = Reference(
                    source_id=doc["id"],
                    title=doc["title"],
                    url=doc["url"],
                    publisher=doc["publisher"],
                    jurisdiction="International research; study-specific populations",
                    source_date=doc["source_date"],
                    retrieved_date=doc["retrieved_date"],
                    snapshot_id=output.name,
                    section=section["title"],
                    text=prefix + context["text"],
                    topics=doc["subjects"],
                    keywords=sorted(set(re.findall(r"[a-z][a-z-]{3,}", section["title"].lower())))
                    or doc["subjects"],
                    source_type="teaching",
                    section_id=f"section-{section_index + 1}-context-{context_index + 1}",
                    text_revision=f"{doc['pmcid']}-{doc['raw_sha256'][:12]}",
                    permission_basis=basis,
                    clinical_review=False,
                )
                record.chunk_id = record.stable_id()
                records.append(record)
                checksums.append(record.content_hash())
                chunks[record.chunk_id] = {
                    "source_id": doc["id"],
                    "material_type": "research",
                    "subjects": doc["subjects"],
                    "syllabus_ids": doc["syllabus_ids"],
                    "study_type": doc["study_type"],
                    "study_design": doc["study_design"],
                    "study_context": doc["study_context"],
                    "source_date": doc["source_date"],
                    "limitations": doc["limitations"]
                    + [
                        "Figures, tables, quotations, and reference lists excluded; prose may refer to excluded elements."
                    ],
                    "level": "MDS supporting research",
                    "context": section["title"],
                    "section_id": record.section_id,
                    "complete_paragraph": True,
                    "paragraph_start": context["paragraph_start"],
                    "paragraph_end": context["paragraph_end"],
                    "context_overlap": "one whole paragraph",
                    "license": doc["license"],
                    "clinical_review": False,
                    "coverage_status": "relevant_material_not_competency_mastery",
                }
        if not checksums:
            raise ValueError(f"{doc['id']}: no usable complete paragraphs")
        attribution = f"{'; '.join(doc['authors'])}. {doc['title']}. {doc['source_date']}. DOI: {doc.get('doi') or 'not supplied'}. {doc['license']}."
        sources.append(
            {
                **{
                    k: doc.get(k)
                    for k in (
                        "title",
                        "url",
                        "publisher",
                        "source_date",
                        "retrieved_date",
                        "raw_snapshot_path",
                        "raw_sha256",
                        "license",
                        "license_url",
                        "license_snapshot_path",
                        "license_snapshot_sha256",
                    )
                },
                "source_id": doc["id"],
                "jurisdiction": "International research; study-specific populations",
                "version": record.text_revision,
                "approval": "developer_reviewed",
                "reviewer": "Codex source/license and extraction review; no faculty review",
                "clinical_review": False,
                "permission_basis": basis,
                "record_checksums": checksums,
                "checksum_format": "sha256-canonical-record-v2",
                "attribution": attribution,
                "terms": "Local noncommercial educational retrieval. Retain attribution and license. Share-alike sources retain identical terms. Prose extraction and repeated research-context annotation; figures excluded.",
                "license_evidence": evidence["license_evidence"],
            }
        )
        source_meta[doc["id"]] = {
            **{
                k: doc.get(k)
                for k in (
                    "pmcid",
                    "doi",
                    "authors",
                    "subjects",
                    "syllabus_ids",
                    "study_type",
                    "study_design",
                    "study_context",
                    "limitations",
                    "source_date",
                )
            },
            "material_type": "research",
            "attribution": attribution,
            "acquisition_method": "Europe PMC fullTextXML; original JATS snapshot",
            "clinical_review": False,
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="research-staging-", dir=output.parent))
    (staging / "records.jsonl").write_text(
        "\n".join(r.model_dump_json() for r in records) + "\n", encoding="utf-8"
    )
    (staging / "sources.yaml").write_text(
        yaml.safe_dump(
            {"library_version": output.name, "sources": sources},
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    metadata = {
        "schema_version": 1,
        "chunks": chunks,
        "sources": source_meta,
        "clinical_review": False,
        "faculty_review": "pending",
        "explanation_units": "none; original publisher paragraphs plus labelled research context",
        "extraction_exclusions": exclusions,
        "skipped_sections": skipped,
        "source_review_flags": [],
    }
    (staging / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (staging / "bibliography.json").write_text(
        json.dumps(bibliography or [], indent=2, ensure_ascii=False), encoding="utf-8"
    )
    covered = {t for doc in documents for t in doc["syllabus_ids"]}
    syllabus_path = Path(syllabus) if syllabus else Path(root) / "configs/mds_syllabus.json"
    topics = (
        json.loads(syllabus_path.read_text(encoding="utf-8"))["topics"]
        if syllabus_path.exists()
        else []
    )
    gaps = [
        {
            "syllabus_id": t["id"],
            "title": t["title"],
            "status": "research_supplement_only"
            if t["id"] in covered
            else "no_imported_research_source",
            "clinical_correctness": None,
        }
        for t in topics
    ]
    (staging / "coverage.json").write_text(
        json.dumps(
            {
                "claim": "Topic association only; not complete curriculum coverage or competency mastery.",
                "topics": gaps,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    names = ["records.jsonl", "sources.yaml", "metadata.json", "bibliography.json", "coverage.json"]
    manifest = {
        "version": output.name,
        "library_version": output.name,
        "schema_version": 1,
        "files": {n: sha256(staging / n) for n in names},
        "records": len(records),
        "sources": len(sources),
        "clinical_review": False,
        "faculty_review": "pending",
        "material_type": "research",
        "subjects": dict(Counter(s for r in records for s in r.topics)),
        "licenses": sorted({d["license"] for d in documents}),
        "source_dates": sorted({d["source_date"] for d in documents}),
        "bibliography_only": len(bibliography or []),
        "syllabus_topics_with_material": len(covered),
        "coverage_claim": "Partial supporting research; no verified MDS mastery or faculty correctness.",
        "usage": "Local noncommercial educational retrieval; attribution and share-alike obligations retained.",
    }
    (staging / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    staging.rename(output)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/mds_research_sources.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--syllabus", type=Path, help="Explicit topic map for this research pack")
    parser.add_argument(
        "--acquire",
        action="store_true",
        help="Download missing pinned XML snapshots before build; expected hashes still required",
    )
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if args.acquire:
        for doc in config["documents"]:
            path = snapshot_path(doc["raw_snapshot_path"], ROOT)
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                data = urllib.request.urlopen(
                    f"https://www.ebi.ac.uk/europepmc/webservices/rest/{doc['pmcid']}/fullTextXML",
                    timeout=60,
                ).read()
                if hashlib.sha256(data).hexdigest() != doc["raw_sha256"]:
                    raise ValueError(
                        "Remote article changed; source review and new version required"
                    )
                path.write_bytes(data)
    print(
        json.dumps(
            build_release(
                config["documents"], args.output, bibliography=config.get("bibliography"),
                syllabus=args.syllabus,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
