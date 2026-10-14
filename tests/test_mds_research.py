"""License and study-context invariants for the MDS research component."""

import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from scripts.build_mds_research import build_release, extract_sections, license_evidence


def article(license_xml, body):
    return ET.fromstring(
        f"<article><front><article-meta><permissions>{license_xml}</permissions></article-meta></front><body>{body}</body></article>"
    )


def test_article_license_is_not_inferred_from_pmc_membership():
    with pytest.raises(ValueError, match="license"):
        license_evidence(article("", "<p>Text</p>"))
    with pytest.raises(ValueError, match="derivative"):
        license_evidence(
            article(
                "<license><license-p>https://creativecommons.org/licenses/by-nc-nd/4.0/</license-p></license>",
                "",
            )
        )
    assert (
        license_evidence(
            article(
                "<license><license-p>https://creativecommons.org/licenses/by/4.0/</license-p></license>",
                "",
            )
        )["license"]
        == "CC-BY-4.0"
    )


def test_license_text_requires_explicit_version():
    with pytest.raises(ValueError, match="license"):
        license_evidence(
            article(
                "<license><license-p>Creative Commons Attribution License.</license-p></license>",
                "",
            )
        )
    assert (
        license_evidence(
            article(
                "<license><license-p>Creative Commons Attribution-NonCommercial-ShareAlike 4.0 License</license-p></license>",
                "",
            )
        )["license"]
        == "CC-BY-NC-SA-4.0"
    )


def test_extract_preserves_paragraphs_and_excludes_third_party_elements():
    e = article(
        "",
        '<sec id="s1"><title>Introduction</title><p>A complete paragraph about oral tissues and methods.</p><fig><caption><p>Third party caption must disappear.</p></caption></fig><table-wrap><p>Table prose must disappear.</p></table-wrap><disp-quote><p>Quoted third party text.</p></disp-quote><p>Another full paragraph retains the qualifying context.</p><sec><title>References</title><p>References excluded.</p></sec></sec>',
    )
    sections = extract_sections(e)
    assert sections[0]["paragraphs"] == [
        "A complete paragraph about oral tissues and methods.",
        "Another full paragraph retains the qualifying context.",
    ]
    assert "Third party" not in json.dumps(sections)
    assert "References excluded" not in json.dumps(sections)


def fixture_doc(tmp_path):
    raw = tmp_path / "article.xml"
    raw.write_text(
        "<article><front><article-meta><permissions><license><license-p>https://creativecommons.org/licenses/by/4.0/</license-p></license></permissions></article-meta></front><body><sec><title>Results</title><p>Animal experiments demonstrated a model-specific finding. Human translation was not studied.</p></sec></body></article>"
    )
    digest = hashlib.sha256(raw.read_bytes()).hexdigest()
    return {
        "id": "mds-pmc-test",
        "pmcid": "PMC123",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC123/",
        "title": "Example experiment",
        "publisher": "Example publisher",
        "authors": ["Example Author"],
        "doi": "10.example/test",
        "source_date": "2020-01-01",
        "retrieved_date": "2026-10-09",
        "raw_snapshot_path": "article.xml",
        "raw_sha256": digest,
        "license": "CC-BY-4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "subjects": ["oral_histology"],
        "syllabus_ids": ["MDS-31"],
        "study_type": "animal",
        "study_design": "experimental study",
        "study_context": "Mouse dental development model; no human outcomes.",
        "limitations": ["Animal results cannot establish human clinical effectiveness."],
        "approval": "developer_reviewed",
        "clinical_review": False,
        "excluded_paragraph_patterns": [],
    }


def test_each_chunk_carries_context_and_build_is_immutable(tmp_path):
    doc = fixture_doc(tmp_path)
    output = tmp_path / "v1"
    m = build_release([doc], output, root=tmp_path)
    assert m["records"] == 1
    r = json.loads((output / "records.jsonl").read_text().splitlines()[0])
    assert r["text"].startswith("[Research context: 2020-01-01; experimental study; animal.")
    assert "Mouse dental development model" in r["text"]
    assert "Animal results cannot establish" in r["text"]
    metadata = json.loads((output / "metadata.json").read_text())
    c = metadata["chunks"][r["chunk_id"]]
    assert c["study_type"] == "animal"
    assert c["material_type"] == "research"
    assert c["syllabus_ids"] == ["MDS-31"]
    with pytest.raises(ValueError, match="exists"):
        build_release([doc], output, root=tmp_path)


def test_research_coverage_uses_the_selected_specialty_topic_map(tmp_path):
    doc = fixture_doc(tmp_path)
    syllabus = tmp_path / "all-specialties.json"
    syllabus.write_text(json.dumps({"topics": [
        {"id": "MDS-31", "title": "Hard tissue healing"},
        {"id": "ALL-MDS-ORTHODONTICS-01", "title": "Craniofacial growth"}]}))
    output = tmp_path / "all-specialties"
    build_release([doc], output, root=tmp_path, syllabus=syllabus)
    coverage = json.loads((output / "coverage.json").read_text())
    assert [t["syllabus_id"] for t in coverage["topics"]] == ["MDS-31", "ALL-MDS-ORTHODONTICS-01"]
    assert coverage["topics"][0]["status"] == "research_supplement_only"
    assert coverage["topics"][1]["status"] == "no_imported_research_source"


def test_modified_snapshot_fails_closed(tmp_path):
    doc = fixture_doc(tmp_path)
    (tmp_path / "article.xml").write_text("<article/>")
    with pytest.raises(ValueError, match="hash"):
        build_release([doc], tmp_path / "v1", root=tmp_path)


def test_modified_license_snapshot_fails_closed(tmp_path):
    doc = fixture_doc(tmp_path)
    evidence = tmp_path / "license.xml"
    evidence.write_text("unrelated license text")
    doc["license_snapshot_path"] = "license.xml"
    doc["license_snapshot_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="license snapshot hash"):
        build_release([doc], tmp_path / "v1", root=tmp_path)


def test_curated_section_scope_rejects_irrelevant_body_sections(tmp_path):
    doc = fixture_doc(tmp_path)
    doc["include_section_patterns"] = ["^Laboratory methods$"]
    with pytest.raises(ValueError, match="no usable"):
        build_release([doc], tmp_path / "v1", root=tmp_path)


def test_excluded_paragraph_retains_audit_hash_without_importing_claim(tmp_path):
    doc = fixture_doc(tmp_path)
    doc["excluded_paragraph_patterns"] = [
        {
            "pattern": "Animal experiments",
            "reason": "Known source discrepancy; excluded without correcting publisher text.",
        }
    ]
    with pytest.raises(ValueError, match="no usable"):
        build_release([doc], tmp_path / "v1", root=tmp_path)


@pytest.mark.parametrize("version,record_count,source_count", [("v1", 427, 25), ("v2", 447, 27)])
def test_saved_component_is_verified_and_every_research_chunk_keeps_context(
    version, record_count, source_count
):
    import yaml

    from backend.app.services.retrieval import Reference

    root = Path(__file__).resolve().parents[1]
    release = root / f"data/references/mds/components/research/mds-research-2026-10-09-{version}"
    config = json.loads((root / "configs/mds_research_sources.json").read_text(encoding="utf-8"))
    manifest = json.loads((release / "manifest.json").read_text(encoding="utf-8"))
    for name, digest in manifest["files"].items():
        assert hashlib.sha256((release / name).read_bytes()).hexdigest() == digest
    sources = yaml.safe_load((release / "sources.yaml").read_text(encoding="utf-8"))["sources"]
    source_map = {s["source_id"]: s for s in sources}
    metadata = json.loads((release / "metadata.json").read_text(encoding="utf-8"))
    records = [
        Reference.model_validate_json(line)
        for line in (release / "records.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(records) == manifest["records"] == record_count
    assert len(sources) == manifest["sources"] == source_count
    for doc in config["documents"]:
        raw = root / doc["raw_snapshot_path"]
        assert hashlib.sha256(raw.read_bytes()).hexdigest() == doc["raw_sha256"]
        evidence = root / doc["license_snapshot_path"]
        assert hashlib.sha256(evidence.read_bytes()).hexdigest() == doc["license_snapshot_sha256"]
        assert license_evidence(ET.parse(raw).getroot())["license"] == doc["license"]
    bibliography_ids = {b["id"] for b in config["bibliography"]}
    for record in records:
        assert record.chunk_id == record.stable_id()
        assert record.source_id not in bibliography_ids
        assert record.content_hash() in source_map[record.source_id]["record_checksums"]
        meta = metadata["chunks"][record.chunk_id]
        assert meta["material_type"] == "research"
        assert meta["study_context"] in record.text
        assert meta["source_date"] in record.text
        assert meta["study_type"] in record.text
        assert meta["limitations"][0] in record.text
        assert "not a clinical recommendation" in record.text
        assert not record.clinical_review
        assert len(record.text) <= 4000
        assert "epithelium is derived from the embryonic endoderm" not in record.text
        assert "population assumptions are unnecessary" not in record.text
        assert "Central limit theorem states that when sample size has 100" not in record.text
    assert len(metadata["extraction_exclusions"]) == 4
    assert all(x["runtime_policy"] == "exclude" for x in metadata["extraction_exclusions"])
    if version == "v2":
        text = "\n".join(r.text for r in records if r.source_id == "mds-pmc-13170827")
        assert "blue-purple" in text and "cytoplasm and extracellular matrix proteins pink" in text
        assert "typically cut at a thickness of 2–5 microns" in text
        ground = "\n".join(r.text for r in records if r.source_id == "mds-pmc-10150715")
        assert "Undemineralized human premolars" in ground
        assert "diamond knife" in ground and "15–25 µm" in ground
