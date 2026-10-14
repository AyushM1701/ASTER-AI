"""Offline extraction, review and immutable release tooling for Aster references.

Extracted documents are drafts. Extraction never supplies medical approval.
"""

import argparse
import hashlib
import json
import re
import sys
import tempfile
from pathlib import Path
from xml.etree import ElementTree

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.config import Settings  # noqa: E402
from backend.app.services.retrieval import Reference, ReferenceStore, permitted_source  # noqa: E402


def extract_sections(path):
    """Preserve heading/page boundaries; no automatic summarization or approval."""
    path = Path(path)
    suffix = path.suffix.lower()
    sections = []
    if suffix in {".html", ".htm"}:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(path.read_bytes(), "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        title, paragraphs = "Document", []
        for tag in soup.find_all(["h1", "h2", "h3", "p", "li"]):
            text = " ".join(tag.get_text(" ", strip=True).split())
            if tag.name.startswith("h"):
                if paragraphs:
                    sections.append({"title": title, "text": "\n".join(paragraphs)})
                title, paragraphs = text, []
            elif text:
                paragraphs.append(text)
        if paragraphs:
            sections.append({"title": title, "text": "\n".join(paragraphs)})
    elif suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(path)
        sections = [
            {"title": f"Page {i + 1}", "text": page.extract_text() or "", "page": i + 1}
            for i, page in enumerate(reader.pages)
        ]
    elif suffix == ".xml":
        # Reject entities/DTDs before stdlib XML parsing; imported text stays data.
        raw = path.read_bytes()
        if re.search(rb"<!\s*(?:DOCTYPE|ENTITY)", raw, re.I):
            raise ValueError("XML DTD/entities are unsupported")
        root = ElementTree.fromstring(raw)
        for node in root.iter():
            if node.tag.split("}")[-1] != "section":
                continue
            children = {child.tag.split("}")[-1]: child for child in node}
            if "text" in children:
                sections.append(
                    {
                        "title": " ".join(children["title"].itertext())
                        if "title" in children
                        else "SPL section",
                        "text": " ".join(children["text"].itertext()),
                    }
                )
    elif suffix in {".txt", ".md"}:
        sections = [
            {"title": f"Paragraph {i + 1}", "text": block.strip()}
            for i, block in enumerate(re.split(r"\n\s*\n", path.read_text(encoding="utf-8")))
        ]
    else:
        raise ValueError("Supported formats: HTML, PDF, SPL XML, text, Markdown")
    return [{**s, "id": f"section-{i + 1}"} for i, s in enumerate(sections) if s["text"].strip()]


def validate_documents(documents):
    seen_ids, seen_versions, seen_urls = set(), set(), set()
    for doc in documents:
        identity = (doc["url"], doc["version"])
        if doc["id"] in seen_ids or identity in seen_versions:
            raise ValueError(
                "Duplicate document ID or source URL/version; consolidate sections or resolve supersession"
            )
        if doc["url"] in seen_urls:
            raise ValueError(
                "Conflicting source versions; resolve supersession and release only one reviewed version"
            )
        seen_ids.add(doc["id"])
        seen_versions.add(identity)
        seen_urls.add(doc["url"])
        if not permitted_source(doc["url"], doc):
            raise ValueError("Source host has not been verified/approved")
        if doc.get("superseded_by"):
            raise ValueError("Superseded document cannot enter an active release")


def build_release(inputs, output, reviewer, reviewed=False, catalogue=None):
    if not reviewed or not reviewer.strip():
        raise ValueError(
            "Release requires --reviewed and named --reviewer after source/content review"
        )
    output = Path(output).resolve()
    if output.exists():
        raise ValueError("Release exists; create a new version, never overwrite")
    documents = []
    for path in inputs:
        documents.extend(json.loads(Path(path).read_text(encoding="utf-8"))["documents"])
    validate_documents(documents)
    records, sources, section_hashes = [], [], set()
    raw_hashes = {}
    for doc in documents:
        if not doc.get("terms") or doc.get("clinical_review"):
            raise ValueError(
                "Record source usage terms; clinician review cannot be claimed by this developer workflow"
            )
        raw_path = doc.get("raw_snapshot_path")
        if not raw_path or not doc.get("raw_sha256"):
            raise ValueError(f"{doc['id']}: missing source snapshot or hash")
        raw = (ROOT / raw_path).resolve()
        if not raw.is_relative_to(ROOT):
            raise ValueError("Source snapshot outside workspace")
        if raw not in raw_hashes:
            digest = hashlib.sha256()
            with raw.open("rb") as source:
                for block in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(block)
            raw_hashes[raw] = digest.hexdigest()
        if raw_hashes[raw] != doc["raw_sha256"]:
            raise ValueError("Source snapshot hash mismatch or outside workspace")
        checksums, section_ids = [], set()
        for section in doc["sections"]:
            if section["id"] in section_ids:
                raise ValueError("Duplicate section ID")
            section_ids.add(section["id"])
            text = section["text"].strip()
            text_hash = hashlib.sha256(text.encode()).hexdigest()
            section_identity = (doc["id"], text_hash)
            if section_identity in section_hashes:
                raise ValueError("Duplicate section text; resolve before release")
            section_hashes.add(section_identity)
            fields = {
                key: section.get(key, doc.get(key, default))
                for key, default in {
                    "source_type": "education",
                    "entity": None,
                    "formulations": [],
                    "strengths": [],
                    "routes": [],
                    "aliases": [],
                    "product_identity": None,
                    "products": [],
                    "label_strengths": [],
                    "permission_basis": {},
                }.items()
            }
            if "match_strengths" in doc:
                fields["label_strengths"] = fields["strengths"]
                fields["strengths"] = doc["match_strengths"]
            normalized_products = []
            for item in fields["products"]:
                product = dict(item)
                if "match_strengths" not in product:
                    product["match_strengths"] = []
                    ingredients = product.get("ingredients", [])
                    if len(ingredients) == 1:
                        match = re.fullmatch(
                            r"(\d+(?:\.\d+)?)\s*(mg|mcg|g) per (?:tablet|capsule)",
                            ingredients[0].get("strength", ""),
                            re.I,
                        )
                        if match:
                            canonical = (match[1] + match[2]).casefold()
                            if canonical in fields["strengths"]:
                                product["match_strengths"].append(canonical)
                product.setdefault(
                    "route", fields["routes"][0] if len(fields["routes"]) == 1 else ""
                )
                normalized_products.append(product)
            fields["products"] = normalized_products
            record = Reference(
                source_id=doc["id"],
                title=doc["title"],
                url=doc["url"],
                publisher=doc["publisher"],
                jurisdiction=doc["jurisdiction"],
                section=section["title"],
                source_date=doc.get("source_date"),
                retrieved_date=doc["retrieved_date"],
                snapshot_id=output.name,
                text=text,
                topics=section["topics"],
                keywords=section["keywords"],
                section_id=section["id"],
                text_revision=doc["version"],
                **fields,
            )
            record.chunk_id = record.stable_id()
            records.append(record)
            checksums.append(record.content_hash())
        if not checksums:
            raise ValueError("Document has no reviewed sections")
        sources.append(
            {
                "source_id": doc["id"],
                "title": doc["title"],
                "url": doc["url"],
                "publisher": doc["publisher"],
                "jurisdiction": doc["jurisdiction"],
                "source_date": doc.get("source_date"),
                "retrieved_date": doc["retrieved_date"],
                "version": doc["version"],
                "terms": doc["terms"],
                "approval": "user_attested"
                if doc.get("permission_basis")
                else "developer_reviewed",
                "reviewer": reviewer,
                "clinical_review": False,
                "permission_basis": doc.get("permission_basis", {}),
                "raw_snapshot_path": raw_path,
                "raw_sha256": doc["raw_sha256"],
                "record_checksums": checksums,
                "checksum_format": "sha256-canonical-record-v2",
                "original_document_ids": doc.get("original_document_ids", [doc["id"]]),
            }
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="library-staging-", dir=output.parent))
    (staging / "records.jsonl").write_text(
        "\n".join(r.model_dump_json() for r in records) + "\n", encoding="utf-8"
    )
    register = {"library_version": output.name, "sources": sources}
    if catalogue:
        raw = Path(catalogue).read_bytes()
        cat = json.loads(raw)
        source = cat["source"]
        validate_documents([{**source, "id": "india-nlem-2022"}])
        snapshot = (ROOT / source["raw_snapshot_path"]).resolve()
        if (
            not snapshot.is_relative_to(ROOT)
            or hashlib.sha256(snapshot.read_bytes()).hexdigest() != source["raw_sha256"]
        ):
            raise ValueError("Catalogue source snapshot mismatch")
        (staging / "india_catalog.json").write_bytes(raw)
        register["catalogue"] = {
            "path": "india_catalog.json",
            "approval": "developer_reviewed",
            "clinical_review": False,
            "reviewer": reviewer,
            "checksum": hashlib.sha256(raw).hexdigest(),
            **source,
        }
    (staging / "sources.yaml").write_text(
        yaml.dump(
            register,
            Dumper=getattr(yaml, "CSafeDumper", yaml.SafeDumper),
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    refs = ReferenceStore(
        Settings(
            corpus_path=staging / "records.jsonl",
            source_register=staging / "sources.yaml",
            retrieval_backend="lexical",
        )
    )
    if refs.error:
        raise ValueError(refs.error)
    manifest = {
        **refs.manifest(),
        "library_version": output.name,
        "reviewer": reviewer,
        "clinical_review": False,
        "previous_library": "data/references/normalized/seed.jsonl",
    }
    (staging / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    staging.rename(output)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    extract = sub.add_parser("extract")
    extract.add_argument("input", type=Path)
    extract.add_argument(
        "--metadata", type=Path, required=True, help="JSON document identity/provenance"
    )
    extract.add_argument("--output", type=Path, required=True)
    build = sub.add_parser("build")
    build.add_argument("inputs", nargs="+", type=Path)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--reviewer", required=True)
    build.add_argument("--reviewed", action="store_true")
    build.add_argument("--catalogue", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "extract":
            if args.output.exists():
                raise ValueError("Draft output exists")
            meta = json.loads(args.metadata.read_text(encoding="utf-8"))
            meta.update(
                approval="pending_review",
                clinical_review=False,
                raw_snapshot_path=str(args.input.resolve().relative_to(ROOT)),
                raw_sha256=hashlib.sha256(args.input.read_bytes()).hexdigest(),
                sections=extract_sections(args.input),
            )
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps({"documents": [meta]}, indent=2), encoding="utf-8")
            print(
                "Pending draft extracted. Check rights, source version, section qualifications and add topics/keywords before review."
            )
        else:
            result = build_release(
                args.inputs, args.output, args.reviewer, args.reviewed, args.catalogue
            )
            print(
                json.dumps(
                    {k: v for k, v in result.items() if k not in {"topics", "medicine_entities"}},
                    indent=2,
                )
            )
    except (ValueError, KeyError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
