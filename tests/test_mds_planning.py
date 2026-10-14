"""Reconstructed regression tasks, not verbatim replays or medical answer keys."""

import pytest

from backend.app.services.question_plan import plan_question


def test_facets_inherit_oral_subject_instead_of_orphan_fragments():
    plan = plan_question("Define oral epithelium. Discuss its layers and functions.", "study")
    assert plan.primary_topic_id == "oral_epithelium"
    assert {(f.topic_id, f.facet) for f in plan.facets} == {
        ("oral_epithelium", "definition"),
        ("oral_epithelium", "layers"),
        ("oral_epithelium", "functions"),
    }
    assert all("oral epithelium" in f.query.casefold() for f in plan.facets)
    assert not any(p.casefold() in {"what is functions", "define functions"} for p in plan.subquestions)


def test_comparison_has_each_entity_by_each_requested_axis():
    plan = plan_question("Compare OKC versus dentigerous cyst: clinical, radiographic and histological features.", "study")
    assert plan.task == "compare"
    assert plan.canonical_topics == ["odontogenic_keratocyst", "dentigerous_cyst"]
    assert plan.comparison_axes == ["clinical_features", "radiographic_features", "histopathology"]
    assert len(plan.facets) == 6


def test_three_entity_comparison_and_shared_noun_resolution():
    plan = plan_question("Compare oral, sulcular and junctional epithelium: structure and functions", "study")
    assert plan.canonical_topics == ["oral_epithelium", "sulcular_epithelium", "junctional_epithelium"]
    assert len(plan.facets) == 6
    plan = plan_question("Keratinized vs non-keratinized epithelium with anatomical examples", "study")
    assert plan.task == "compare" and len(plan.canonical_topics) == 2
    assert "anatomical_examples" in plan.comparison_axes


@pytest.mark.parametrize("question,task,facets", [
    ("Describe apoptosis: intrinsic and extrinsic pathways, molecular and histological features", "mechanism", {"intrinsic_pathway", "extrinsic_pathway", "molecular_features", "histopathology"}),
    ("Explain tooth development stages and epithelial–mesenchymal interactions", "mechanism", {"stages", "epithelial_mesenchymal_interactions"}),
    ("Oral leukoplakia: definition, clinical presentation, histology and relationship to dysplasia", "essay", {"definition", "clinical_features", "histopathology", "relationship_to_dysplasia"}),
    ("Discuss OED architectural and cytological criteria and grading limitations", "histology", {"architectural_features", "cytological_features", "grading_limitations"}),
])
def test_reconstructed_tasks_have_explicit_facets(question, task, facets):
    plan = plan_question(question, "study")
    assert plan.task == task
    assert facets <= {f.facet for f in plan.facets}


def test_explicit_marks_only_and_personal_context_survives():
    assert plan_question("Write a 25-mark essay on apoptosis", "study").marks == 25
    assert plan_question("Write an essay on apoptosis", "study").marks is None
    plan = plan_question("Fictional case: I have a white patch on my tongue. Diagnose me", "study")
    assert not plan.is_fictional_case
    assert plan.individualized_advice_requested


def test_followup_uses_explicit_session_context_or_requests_clarification():
    unresolved = plan_question("What are its functions?", "study")
    assert unresolved.needs_clarification
    resolved = plan_question("What are its functions?", "study", context_topic="oral epithelium")
    assert resolved.original_question == "What are its functions?"
    assert resolved.primary_topic_id == "oral_epithelium"
    assert resolved.facets[0].facet == "functions"
def test_joined_definitions_keep_both_requested_entities():
    plan = plan_question("Define oral epithelium and apoptosis", "study")
    assert {f.topic_id for f in plan.facets} == {"oral_epithelium", "apoptosis"}


def test_independent_clauses_keep_facets_and_scope_with_their_entities():
    plan = plan_question("Define apoptosis; explain inflammation in necrosis.", "study")
    assert [(f.topic_id, f.facet, f.scope) for f in plan.facets] == [("apoptosis", "definition", ""), ("necrosis", "inflammation", "")]
    joined = plan_question("Define apoptosis and discuss oral epithelium layers", "study")
    assert [(f.topic_id, f.facet) for f in joined.facets] == [("apoptosis", "definition"), ("oral_epithelium", "layers")]

