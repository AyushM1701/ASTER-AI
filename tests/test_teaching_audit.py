import hashlib
import json

import pytest

from backend.app.config import Settings
from backend.app.services.teaching import TeachingStore, teaching_terms
from tests.test_mbbs_teaching import teaching_release


def store_for(root):
    return TeachingStore(Settings(_env_file=None, enable_teaching=True, teaching_backend="lexical", teaching_release_path=root, teaching_explanations_sha256=""))


def test_release_bound_holds_cannot_be_disabled_by_omitting_profile_checksum(tmp_path):
    root, rows = teaching_release(tmp_path)
    notes = {"release_version": "test-teaching-v1", "units": [], "source_review_flags": [
        {"chunk_id": rows[0].chunk_id, "content_sha256": rows[0].content_hash(),
         "runtime_policy": "exclude", "reason": "Incorrect reference under review", "clinical_review": False}]}
    (root / "explanations.json").write_text(json.dumps(notes))
    manifest = json.loads((root / "manifest.json").read_text())
    manifest["files"]["explanations.json"] = hashlib.sha256((root / "explanations.json").read_bytes()).hexdigest()
    (root / "manifest.json").write_text(json.dumps(manifest))
    store = store_for(root)
    assert store.error is None
    assert rows[0].chunk_id in store.review_flags
    assert store.answer("Explain glomerular filtration") is None


def test_generic_concept_does_not_answer_with_research_methods(tmp_path):
    root, _ = teaching_release(tmp_path)
    store = store_for(root)
    row = store.records[0]
    row.section = "Materials and Methods / Literature search"
    row.topics = ["neoplasia"]
    row.text = "Neoplasia articles were found using a database search protocol."
    store.words[row.chunk_id] = teaching_terms(row.text + " " + row.section)
    store.metadata[row.chunk_id] = {"material_type": "research", "study_design": "narrative review"}
    assert store.answer("Explain neoplasia") is None
    assert store.answer("Explain neoplasia research methods") is not None


def test_spelling_aliases_and_negative_scope_do_not_erase_concepts():
    assert teaching_terms("Explain haemostasis") == teaching_terms("Explain hemostasis")
    assert teaching_terms("Compare hepatic metabolism without dosing") == teaching_terms("Compare liver metabolism")
    assert teaching_terms("Explain medicine dosing") != teaching_terms("Explain medicine")


def test_compare_with_recognizes_both_requested_concepts():
    from backend.app.services.teaching import comparison_queries

    assert comparison_queries("Compare hepatic metabolism with renal excretion.") == ["hepatic metabolism", "renal excretion"]


def test_anchor_matching_recognizes_general_topic_defined_in_body(tmp_path):
    from collections import Counter

    root, _ = teaching_release(tmp_path)
    store = store_for(root)
    row = store.records[0]
    row.section = "Blood flow"
    row.topics = ["pharmacology"]
    row.text = "Free drug is dissolved in plasma water. Protein-bound drug is a reservoir during drug distribution."
    store.words[row.chunk_id] = teaching_terms(row.text + " " + row.section)
    store.df = Counter(word for record in store.records for word in teaching_terms(record.text + " " + record.section))
    answer = store.answer("For a viva describe free drug and protein binding in drug distribution")
    assert answer is not None
    assert answer["claims"][0]["text"] == row.text


def test_reviewed_explanation_is_not_padded_with_raw_text_for_a_viva(tmp_path):
    root, rows = teaching_release(tmp_path)
    store = store_for(root)
    store.units = [{"id": "filter", "topics": ["glomerular filtration"],
                    "text": "The glomerulus filters fluid.", "citation_ids": [rows[0].chunk_id]}]
    answer = store.answer("Explain glomerular filtration for a viva")
    assert [claim["text"] for claim in answer["claims"]] == ["The glomerulus filters fluid."]


def test_bibliography_body_cannot_answer_a_concept_question(tmp_path):
    root, rows = teaching_release(tmp_path)
    store = store_for(root)
    row = store.records[0]
    row.section = "Tumor immunology"
    row.topics = ["tumor immunology"]
    row.text = "Text References\n1. A paper on tumor immunology."
    store.words[row.chunk_id] = teaching_terms(row.text + " " + row.section)
    assert store.answer("Explain tumor immunology") is None


def test_comparison_cannot_drop_the_parent_drug_metabolism_scope(tmp_path):
    root, _ = teaching_release(tmp_path)
    store = store_for(root)
    row = store.records[0]
    row.section = "Liver metabolism"
    row.topics = ["liver metabolism"]
    row.text = "Liver metabolism uses glucose and fatty acids in fed and fasted states."
    store.words[row.chunk_id] = teaching_terms(row.text + " " + row.section)
    assert store.answer("Compare liver metabolism with drug metabolism") is None


def test_blood_vessel_anatomy_is_not_a_transfusion_mention(tmp_path):
    root, _ = teaching_release(tmp_path)
    store = store_for(root)
    row = store.records[0]
    row.section = "ABO incompatibility"
    row.topics = ["blood"]
    row.text = "Blood vessels can be mentioned during a blood transfusion reaction."
    store.words[row.chunk_id] = teaching_terms(row.text + " " + row.section)
    assert store.answer("Explain blood vessels") is None


def test_cached_scope_checks_do_not_reuse_a_previous_safe_source_value(tmp_path):
    root, _ = teaching_release(tmp_path)
    store = store_for(root)
    assert store.answer("Explain glomerular filtration") is not None
    row = store.records[0]
    row.text = "For glomerular filtration, you should take 5 mg every day."
    store.words[row.chunk_id] = teaching_terms(row.text + " " + row.section)
    assert store.answer("Explain glomerular filtration") is None


@pytest.mark.parametrize("question", [
    "My child is choking now.",
    "My father has suddenly become weak on one side and cannot speak.",
    "I swallowed poison and vomited blood.",
])
def test_new_current_emergency_variants_escalate(question):
    from backend.app.services.policy import check_policy

    assert check_policy(question)["status"] == "urgent_guidance"


@pytest.mark.parametrize("question", [
    "Which antibiotic is best for my tooth swelling?",
    "My child has amoxicillin 250mg tablets. How many each day?",
    "Is this swelling an abscess?",
])
def test_personal_treatment_and_diagnosis_variants_need_review(question):
    from backend.app.services.policy import check_policy

    assert check_policy(question)["status"] == "unsupported_input"


@pytest.mark.parametrize("question", [
    "Explain choking first aid in general.",
    "What is poisoning?",
    "In a fictional clinical case, a person swallowed poison. Explain toxicology concepts.",
    "I was choking last year but I am fine now.",
    "What is an abscess?",
    "Explain antibiotic mechanisms in general.",
])
def test_general_or_historical_variants_are_not_personal_policy_requests(question):
    from backend.app.services.policy import check_policy

    assert check_policy(question) is None
