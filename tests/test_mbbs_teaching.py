"""Teaching answers must preserve evidence and product boundaries."""

import hashlib
import json

import pytest
import yaml

from backend.app.config import Settings
from backend.app.services.retrieval import Reference, permitted_source


def teaching_release(tmp_path):
    rows = []
    for i, (title, text, topic) in enumerate([
        ("Filtration", "The glomerulus filters fluid into Bowman's capsule. Large proteins normally remain in blood.", "glomerular filtration"),
        ("Reabsorption", "The tubules return useful water and solutes to blood. Filtration and reabsorption are different processes.", "tubular reabsorption"),
        ("Osmosis", "Osmosis is water movement across a selectively permeable membrane. Solute particles do not themselves cross by osmosis.", "osmosis"),
    ]):
        row = Reference(source_id=f"teaching-{i}", title=title, url=f"https://opentextbc.ca/example/chapter/{i}/",
                        publisher="Fixture publisher", jurisdiction="Canada", section=title, retrieved_date="2026-10-08",
                        snapshot_id="test-teaching-v1", text=text, topics=[topic], keywords=topic.split(), source_type="teaching",
                        permission_basis={"type": "open_license", "approved_host": "opentextbc.ca", "license": "CC BY 4.0",
                                          "license_url": "https://opentextbc.ca/example/", "snapshot_sha256": "a" * 64,
                                          "clinical_review": False})
        row.chunk_id = row.stable_id()
        rows.append(row)
    root = tmp_path / "release"
    root.mkdir()
    (root / "records.jsonl").write_text("\n".join(r.model_dump_json() for r in rows), encoding="utf-8")
    sources = [{"source_id": r.source_id, "url": r.url, "approval": "developer_reviewed", "terms": "CC BY 4.0",
                "record_checksums": [r.content_hash()], "permission_basis": r.permission_basis, "raw_sha256": "a" * 64}
               for r in rows]
    (root / "sources.yaml").write_text(yaml.safe_dump({"sources": sources}), encoding="utf-8")
    (root / "metadata.json").write_text(json.dumps({r.chunk_id: {"subjects": ["Physiology"]} for r in rows}), encoding="utf-8")
    manifest = {"version": "test-teaching-v1", "files": {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                for name in ("records.jsonl", "sources.yaml", "metadata.json")}}
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root, rows


def test_open_teaching_permission_requires_bound_reusable_license():
    source = {"raw_sha256": "a" * 64, "permission_basis": {"type": "open_license", "approved_host": "opentextbc.ca",
              "license": "CC BY 4.0", "license_url": "https://opentextbc.ca/example/", "snapshot_sha256": "a" * 64,
              "clinical_review": False}}
    assert permitted_source("https://opentextbc.ca/example/chapter/1/", source)
    source["permission_basis"]["license"] = "CC BY-NC-ND 4.0"
    assert not permitted_source("https://opentextbc.ca/example/chapter/1/", source)
    source["permission_basis"]["license"] = "CC BY 4.0"
    source["permission_basis"]["snapshot_sha256"] = "b" * 64
    assert not permitted_source("https://opentextbc.ca/example/chapter/1/", source)
    assert not permitted_source("https://openstax.org/books/microbiology/", source)


def test_canonical_cc_license_url_must_match_declared_license():
    basis = {"type": "open_license", "approved_host": "pressbooks.lib.vt.edu", "license": "CC-BY-NC-SA-4.0",
             "license_url": "https://creativecommons.org/licenses/by-nc-sa/4.0/", "snapshot_sha256": "a" * 64,
             "clinical_review": False}
    source = {"raw_sha256": "a" * 64, "permission_basis": basis}
    url = "https://pressbooks.lib.vt.edu/example/chapter/1/"
    assert permitted_source(url, source)
    basis["license_url"] = "https://creativecommons.org/licenses/by/4.0/"
    assert not permitted_source(url, source)


def make_teaching(tmp_path):
    from backend.app.services.teaching import TeachingStore

    root, rows = teaching_release(tmp_path)
    settings = Settings(enable_teaching=True, teaching_release_path=root, teaching_backend="lexical")
    return TeachingStore(settings), root, rows


def test_multi_concept_question_retrieves_both_processes(tmp_path):
    store, _, _ = make_teaching(tmp_path)
    results = store.search("Compare glomerular filtration and tubular reabsorption")
    assert {r.section for r in results} >= {"Filtration", "Reabsorption"}


def test_unknown_concept_does_not_return_generic_medical_notes(tmp_path):
    store, _, _ = make_teaching(tmp_path)
    assert store.search("Explain the Krebs cycle") == []


def test_teaching_rejects_changed_release_before_answering(tmp_path):
    from backend.app.services.teaching import TeachingStore

    store, root, _ = make_teaching(tmp_path)
    assert store.error is None
    path = root / "records.jsonl"
    path.write_text(path.read_text().replace("normally remain", "always disappear"), encoding="utf-8")
    changed = TeachingStore(store.settings)
    assert changed.error and changed.search("glomerular filtration") == []


def test_teaching_does_not_answer_product_or_patient_requests(tmp_path):
    store, _, _ = make_teaching(tmp_path)
    for question in ("glomerular filtration Dolo 650mg tablet", "What dose should I take for osmosis?",
                     "Diagnose me from glomerular filtration"):
        assert store.search(question) == []


def test_conversational_teaching_preserves_complete_qualifications(tmp_path):
    store, _, rows = make_teaching(tmp_path)
    result = store.answer("Explain glomerular filtration")
    assert result["status"] == "ok"
    assert "Let's" in result["message"]
    assert result["claims"][0]["text"] == rows[0].text
    assert result["citations"][0]["chunk_id"] == rows[0].chunk_id
    assert result["clinical_review"] is False


def test_reviewed_plain_explanation_is_source_bound(tmp_path):
    from backend.app.services.teaching import validate_explanation_units

    _, _, rows = make_teaching(tmp_path)
    unit = {"id": "filter-plain", "text": "Think of the glomerulus as a filter: it passes fluid, while large proteins normally stay in the blood.",
            "citation_ids": [rows[0].chunk_id], "source_hashes": {rows[0].chunk_id: rows[0].content_hash()},
            "reviewer": "Developer", "review_status": "developer_reviewed", "clinical_review": False,
            "qualifications": ["normally"]}
    validate_explanation_units([unit], {r.chunk_id: r for r in rows})
    unit["text"] = "All proteins stay in blood."
    with pytest.raises(ValueError, match="qualification"):
        validate_explanation_units([unit], {r.chunk_id: r for r in rows})
    unit["text"] = "Proteins normally stay in blood."
    unit["source_hashes"][rows[0].chunk_id] = "b" * 64
    with pytest.raises(ValueError, match="hash"):
        validate_explanation_units([unit], {r.chunk_id: r for r in rows})


def test_answer_service_uses_teaching_for_concepts_but_preserves_named_products(tmp_path):
    from backend.app.services.answers import AnswerService
    from tests.test_knowledge_v2 import make_store, note

    teaching, _, _ = make_teaching(tmp_path)
    primary_root = tmp_path / "primary"
    primary_root.mkdir()
    records = [note(source_type="drug_label", entity="example brand", topics=["example brand"],
                    text="This medicine label describes a specific product; it is not a physiology teaching reference.")]
    primary = make_store(primary_root, records)
    service = AnswerService(Settings(), primary, None, None, teaching=teaching)
    assert service.answer("Explain glomerular filtration")["answer_method"] == "source_backed_teaching"
    response = service.answer("What is example brand used for? Explain glomerular filtration")
    assert "teaching_version" not in response


def test_explicit_fictional_case_is_educational_but_real_symptoms_still_escalate():
    from backend.app.services.policy import check_policy

    assert check_policy("In a fictional case, he has severe chest pain. Explain the physiology for an MBBS viva.") is None
    assert check_policy("In a fictional case discussion, I have severe chest pain now.")["status"] == "urgent_guidance"
    assert check_policy("For an MBBS case, should I double my medicine?")["status"] == "unsupported_input"


@pytest.mark.parametrize("question", [
    "In a fictional clinical case, he has asthma. But this is actually happening: he cannot breathe now.",
    "In a fictional clinical case, explain glomerular filtration. Separately, a real patient is unconscious and not breathing now.",
])
def test_fictional_prefix_does_not_suppress_later_real_emergency(question):
    from backend.app.services.policy import check_policy

    assert check_policy(question)["status"] == "urgent_guidance"


def test_plain_explanation_requires_the_requested_meaning(tmp_path):
    store, _, rows = make_teaching(tmp_path)
    store.units = [{"id": "diffusion", "topics": ["diffusion"], "text": "Diffusion moves material down a concentration gradient.",
                    "citation_ids": [rows[2].chunk_id]}]
    assert store.answer("What is diffusion tensor imaging?") is None


def test_generic_connective_words_do_not_match_an_unrelated_depression_meaning(tmp_path):
    from backend.app.services.teaching import teaching_terms

    store, _, _ = make_teaching(tmp_path)
    row = store.records[0]
    row.section = "Psychiatric depression"
    row.topics = ["depression"]
    row.text = "Depression can be caused by many risk factors in pregnancy."
    store.words[row.chunk_id] = teaching_terms(row.text + " " + row.section)
    assert store.answer("Explain respiratory depression caused by opioids") is None


def test_teaching_source_cannot_turn_general_question_into_personal_treatment(tmp_path):
    store, _, _ = make_teaching(tmp_path)
    store.records[0].text = "For glomerular filtration, you should take 5 mg of a medicine daily."
    assert store.answer("Explain glomerular filtration") is None


def test_publisher_page_headers_are_not_teaching_answers():
    from backend.app.services.teaching import safe_teaching_text

    assert not safe_teaching_text("# Glycolysis textbook\nURL: https://example.org/book\nThis is publisher navigation.")


def test_comparison_parts_share_the_final_concept_word():
    from backend.app.services.teaching import comparison_queries

    assert comparison_queries("Compare innate and adaptive immunity") == ["innate immunity", "adaptive immunity"]
    assert comparison_queries("Difference between filtration and tubular reabsorption") == ["filtration", "tubular reabsorption"]
    assert comparison_queries("Explain osmosis") == []


def test_primary_definition_beats_related_chapter_mentions(tmp_path):
    store, _, _ = make_teaching(tmp_path)
    row = store.records[0]
    row.section = "Regulation of osmosis in disease / Treatment overview"
    row.text = "Osmosis is mentioned in a wider discussion of disease and its management."
    store.words[row.chunk_id] = {"osmosis", "disease", "regulation"}
    assert store.search("Explain osmosis")[0].section == "Osmosis"


def test_review_flag_cannot_expose_held_source_text_in_detailed_answer(tmp_path):
    store, _, rows = make_teaching(tmp_path)
    store.review_flags = {rows[0].chunk_id: {"runtime_policy": "explanation_only"}}
    assert store.answer("Explain glomerular filtration in detail") is None
    store.units = [{"id": "filter", "topics": ["glomerular filtration"], "text": "The glomerulus filters fluid.",
                    "citation_ids": [rows[0].chunk_id]}]
    result = store.answer("Explain glomerular filtration in detail")
    assert [c['text'] for c in result['claims']] == ["The glomerulus filters fluid."]
