import hashlib
import json

import pytest
import yaml

from backend.app.config import Settings
from backend.app.services.retrieval import permitted_source
from backend.app.services.teaching import TeachingStore, teaching_terms, validate_explanation_units
from tests.test_mbbs_teaching import teaching_release


def rewrite_manifest(root):
    manifest = json.loads((root / "manifest.json").read_text())
    manifest["files"] = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in manifest["files"]}
    (root / "manifest.json").write_text(json.dumps(manifest))


def research_release(tmp_path, complete=True):
    root, rows = teaching_release(tmp_path)
    row = rows[0]
    row.source_date = "2020-06-04"
    row.text = "Mixed preclinical research review; not a clinical trial. " + row.text
    row.permission_basis["material_type"] = "research"
    # Test fixtures preserve the source registry/checksum contract.
    row.chunk_id = row.stable_id()
    (root / "records.jsonl").write_text("\n".join(r.model_dump_json() for r in rows))
    register = yaml.safe_load((root / "sources.yaml").read_text())
    register["sources"][0].update(permission_basis=row.permission_basis, record_checksums=[row.content_hash()])
    (root / "sources.yaml").write_text(yaml.safe_dump(register))
    context = {r.chunk_id: {"subjects": ["Physiology"]} for r in rows}
    context[row.chunk_id].update(material_type="research", study_type="review",
                                 study_context="Mixed preclinical research review; not a clinical trial.",
                                 limitations=["Animal and laboratory evidence is not clinical effectiveness."])
    if not complete:
        context[row.chunk_id].pop("study_context")
    (root / "metadata.json").write_text(json.dumps(context))
    rewrite_manifest(root)
    return root


def test_research_context_survives_answer_and_citation(tmp_path):
    root = research_release(tmp_path)
    store = TeachingStore(Settings(_env_file=None, enable_teaching=True, teaching_backend="lexical", teaching_release_path=root))
    assert store.error is None
    answer = store.answer("Explain glomerular filtration")
    assert answer["citations"][0]["study_type"] == "review"
    assert "preclinical" in answer["claims"][0]["text"]
    assert any("Experimental findings" in text for text in answer["limitations"])


def test_research_without_study_context_fails_closed(tmp_path):
    root = research_release(tmp_path, complete=False)
    store = TeachingStore(Settings(_env_file=None, enable_teaching=True, teaching_backend="lexical", teaching_release_path=root))
    assert "Research reference lacks" in store.error
    assert store.answer("Explain glomerular filtration") is None


@pytest.mark.parametrize("host", ["openoregon.pressbooks.pub", "pmc.ncbi.nlm.nih.gov", "europepmc.org"])
def test_new_mds_hosts_are_not_blanket_reuse_approval(host):
    url = f"https://{host}/article/1"
    assert not permitted_source(url, {})
    basis = {"type": "open_license", "approved_host": host, "license": "CC-BY-4.0",
             "license_url": "https://creativecommons.org/licenses/by/4.0/", "snapshot_sha256": "a" * 64,
             "clinical_review": False}
    source = {"raw_sha256": "a" * 64, "permission_basis": basis}
    assert permitted_source(url, source)
    basis["license"] = "CC-BY-NC-ND-4.0"
    assert not permitted_source(url, source)


def test_composition_preserves_source_ids_notes_and_holds(tmp_path):
    from scripts.compose_mds_library import compose

    base_parent = tmp_path / "base"
    component_parent = tmp_path / "component"
    base_parent.mkdir()
    component_parent.mkdir()
    base, old_rows = teaching_release(base_parent)
    component, new_rows = teaching_release(component_parent)
    for row in new_rows:
        row.source_id += "-new"
        row.chunk_id = row.stable_id()
    (component / "records.jsonl").write_text("\n".join(row.model_dump_json() for row in new_rows))
    register = yaml.safe_load((component / "sources.yaml").read_text())
    for source, row in zip(register["sources"], new_rows):
        source.update(source_id=row.source_id, record_checksums=[row.content_hash()])
    (component / "sources.yaml").write_text(yaml.safe_dump(register))
    (component / "metadata.json").write_text(json.dumps({"chunks": {row.chunk_id: {"subjects": ["Dental"]} for row in new_rows}}))
    rewrite_manifest(component)
    old_row = old_rows[0]
    unit = {"id": "old-note", "text": "Large proteins normally remain in blood.", "topics": ["glomerular filtration"],
            "citation_ids": [old_row.chunk_id], "source_hashes": {old_row.chunk_id: old_row.content_hash()},
            "review_status": "developer_reviewed", "reviewer": "Developer", "clinical_review": False}
    flag = {"chunk_id": old_rows[1].chunk_id, "content_sha256": old_rows[1].content_hash(), "runtime_policy": "exclude",
            "reason": "Source concern under review", "clinical_review": False}
    notes = tmp_path / "notes.json"
    notes.write_text(json.dumps({"release_version": "test-teaching-v1", "units": [unit], "source_review_flags": [flag]}))
    syllabus = tmp_path / "syllabus.json"
    syllabus.write_text(json.dumps({"topic_count": 1, "topics": [{"id": "MDS-01"}]}))
    output = tmp_path / "combined"
    manifest = compose(base, [component], notes, syllabus, output)
    assert manifest["records"] == 6
    rows = [json.loads(line) for line in (output / "records.jsonl").read_text().splitlines()]
    assert rows[:3] == [row.model_dump() for row in old_rows]
    merged = json.loads((output / "explanations.json").read_text())
    assert merged["units"] == [unit]
    assert merged["source_review_flags"] == [flag]
    assert merged["release_version"] == "combined"
    with pytest.raises(ValueError, match="Release exists"):
        compose(base, [component], notes, syllabus, output)
    with pytest.raises(ValueError, match="Duplicate"):
        compose(base, [base], notes, syllabus, tmp_path / "invalid")


def test_skin_eruption_does_not_use_dental_eruption_or_graft_text(tmp_path):
    root, _ = teaching_release(tmp_path)
    store = TeachingStore(Settings(_env_file=None, enable_teaching=True, teaching_backend="lexical", teaching_release_path=root))
    row = store.records[0]
    row.section = "Tooth eruption / Gingival grafts"
    row.topics = ["eruption"]
    row.text = "Skin can be used in grafts for gum tissue. Tooth eruption is part of dental development."
    store.words[row.chunk_id] = teaching_terms(row.text + " " + row.section)
    assert store.answer("Explain skin eruption") is None
    row.section = "Cutaneous eruptions / Rash"
    row.text = "Skin eruptions are rashes that can arise in inflammatory disorders."
    store.words[row.chunk_id] = teaching_terms(row.text + " " + row.section)
    assert store.answer("Explain skin eruption")["claims"][0]["text"] == row.text


def test_mds_instruction_does_not_prevent_a_bound_plain_explanation():
    assert teaching_terms("Explain MDS dental pulp in detail") == {"dental", "pulp"}


def test_general_concept_prefers_explanation_over_a_study_protocol(tmp_path):
    root, _ = teaching_release(tmp_path)
    store = TeachingStore(Settings(_env_file=None, enable_teaching=True, teaching_backend="lexical", teaching_release_path=root))
    protocol, definition = store.records[:2]
    protocol.section = "Immunohistochemistry / Methods"
    protocol.text = "Immunohistochemistry methods in this study used fixed tissue and a specific antibody procedure."
    definition.section = "Introduction"
    definition.text = "Immunohistochemical stains use antibodies to detect tissue antigens."
    for row in (protocol, definition):
        row.topics = ["immunohistochemistry"]
        store.words[row.chunk_id] = teaching_terms(row.text + " " + row.section)
        store.metadata[row.chunk_id] = {"material_type": "research"}
    assert store.search("Explain immunohistochemistry")[0] is definition
    assert store.search("Explain immunohistochemistry methods")[0] is protocol


def test_normal_distribution_does_not_mean_normal_pulmonary_distribution(tmp_path):
    root, _ = teaching_release(tmp_path)
    store = TeachingStore(Settings(_env_file=None, enable_teaching=True, teaching_backend="lexical", teaching_release_path=root))
    row = store.records[0]
    row.section = "Distribution of ventilation and perfusion"
    row.text = "In a normal lung, the distribution of blood and oxygen depends on ventilation and perfusion."
    row.topics = ["distribution"]
    store.words[row.chunk_id] = teaching_terms(row.text + " " + row.section)
    assert store.answer("Explain normal distribution") is None


def test_plain_research_note_cannot_drop_study_context(tmp_path):
    root = research_release(tmp_path)
    store = TeachingStore(Settings(_env_file=None, enable_teaching=True, teaching_backend="lexical", teaching_release_path=root))
    row = store.records[0]
    unit = {"id": "research-note", "text": "Large proteins normally remain in blood.",
            "citation_ids": [row.chunk_id], "source_hashes": {row.chunk_id: row.content_hash()},
            "reviewer": "Developer", "review_status": "developer_reviewed", "clinical_review": False}
    with pytest.raises(ValueError, match="study context"):
        validate_explanation_units([unit], store.references.id_records, store.metadata)
    unit["text"] = store.metadata[row.chunk_id]["study_context"] + " " + unit["text"]
    validate_explanation_units([unit], store.references.id_records, store.metadata)


def test_unknown_named_syndrome_does_not_answer_another_syndrome(tmp_path):
    root, _ = teaching_release(tmp_path)
    store = TeachingStore(Settings(_env_file=None, enable_teaching=True, teaching_backend="lexical", teaching_release_path=root))
    row = store.records[0]
    row.section = "Apert syndrome"
    row.text = "Apert syndrome is a congenital syndrome discussed in craniofacial development."
    row.topics = ["Apert syndrome"]
    store.words[row.chunk_id] = teaching_terms(row.text + " " + row.section)
    assert store.answer("Explain Zorbexium congenital syndrome") is None
    assert store.answer("Explain Apert syndrome")["claims"][0]["text"] == row.text


def test_personal_reassurance_cannot_retrieve_statistics(tmp_path):
    from backend.app.services.policy import check_policy

    question = "My X-ray looks normal. Confirm that I do not have pneumonia."
    assert check_policy(question)["status"] == "unsupported_input"
    root, _ = teaching_release(tmp_path)
    store = TeachingStore(Settings(_env_file=None, enable_teaching=True, teaching_backend="lexical", teaching_release_path=root))
    assert store.answer(question) is None
    assert check_policy("Explain how imaging helps rule out pneumonia in general") is None


def test_free_drug_distribution_requires_pharmacokinetic_context(tmp_path):
    root, _ = teaching_release(tmp_path)
    store = TeachingStore(Settings(_env_file=None, enable_teaching=True, teaching_backend="lexical", teaching_release_path=root))
    row = store.records[0]
    row.section = "Antimicrobial resistance"
    row.text = "Bacterial cell walls prevent free drug molecules from penetrating."
    row.topics = ["free drug"]
    store.words[row.chunk_id] = teaching_terms(row.text + " " + row.section)
    assert store.answer("Explain free drug") is None
    row.section = "Drug distribution"
    row.text = "Free drug can distribute while protein-bound drug forms a reservoir in blood."
    store.words[row.chunk_id] = teaching_terms(row.text + " " + row.section)
    assert store.answer("Explain free drug")["claims"][0]["text"] == row.text
