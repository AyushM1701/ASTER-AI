"""General subject grammar required by the owner-adopted master plan."""

import pytest

from backend.app.services.question_plan import plan_question


@pytest.mark.parametrize("verb", ["Differentiate between", "Compare"])
@pytest.mark.parametrize("spelling", ["keratinized", "keratinised"])
def test_shared_epithelial_noun_and_examples_are_bound(verb, spelling):
    question = f"{verb} {spelling} and non-{spelling} oral epithelium with examples."
    plan = plan_question(question, "study")
    assert len(plan.canonical_topics) == 2
    assert all("epithelium" in topic for topic in plan.canonical_topics)
    assert not any(topic.endswith(":examples") for topic in plan.canonical_topics)
    assert "anatomical_examples" in plan.comparison_axes
    assert all(not facet.scope for facet in plan.facets)
    assert plan.original_question == question


@pytest.mark.parametrize("subject", ["oral submucous fibrosis", "chronic sialadenitis"])
def test_operation_list_before_of_keeps_subject_and_each_facet(subject):
    plan = plan_question(
        f"Explain the etiopathogenesis, histopathology, and clinical significance of {subject}.",
        "study",
    )
    assert plan.canonical_topics == ["local:" + subject.replace(" ", "_")]
    assert {facet.facet for facet in plan.facets} >= {
        "mechanism", "histopathology", "clinical_significance",
    }
    assert "clinical_features" not in {facet.facet for facet in plan.facets}


def test_fictional_case_binds_explicit_finding_without_inventing_disease():
    plan = plan_question(
        "A fictional 32-year-old patient reports lingering molar pain. "
        "Discuss differential diagnosis and relevant tests.", "study",
    )
    assert plan.is_fictional_case
    assert plan.canonical_topics == ["local:molar_pain"]
    assert not any("pulpitis" in topic for topic in plan.canonical_topics)
    assert {facet.facet for facet in plan.facets} >= {"differential_diagnosis", "clinical_tests"}


def test_unidentified_case_requests_clarification_without_case_as_topic():
    plan = plan_question("Discuss a fictional patient case and its differential diagnosis.", "study")
    assert not plan.canonical_topics
    assert plan.needs_clarification


def test_shared_noun_does_not_merge_different_full_entities():
    plan = plan_question("Compare oral lichen planus with oral lichenoid lesions with examples.", "study")
    assert plan.canonical_topics == ["local:oral_lichen_planus", "local:oral_lichenoid_lesions"]
    assert "anatomical_examples" in plan.comparison_axes
def test_facet_association_phrase_binds_to_the_named_subject():
    from backend.app.services.question_plan import plan_question

    for question, topic, facet in (
        ("Explain inflammation associated with apoptosis.", "apoptosis", "inflammation"),
        ("Describe membrane changes related to necrosis.", "necrosis", "membrane_changes"),
        ("Explain clinical significance associated with oral submucous fibrosis.", "local:oral_submucous_fibrosis", "clinical_significance"),
    ):
        plan = plan_question(question, "study")
        assert plan.canonical_topics == [topic]
        assert [(entry.topic_id, entry.facet) for entry in plan.facets] == [(topic, facet)]


def test_inflammatory_response_phrase_is_one_canonical_facet():
    from backend.app.services.question_plan import plan_question

    plan = plan_question("Compare apoptosis and necrosis, including their causes, cellular changes and inflammatory responses.", "study")
    assert plan.comparison_axes == ["cellular_features", "inflammation", "causes"]
    assert all(entry.facet != "inflammatory_responses" for entry in plan.facets)
    specific = plan_question("Compare apoptosis and necrosis, including inflammatory mediators.", "study")
    assert "inflammatory_mediators" in specific.comparison_axes


def test_coordinated_role_facet_does_not_become_part_of_subject():
    plan = plan_question("Explain the stages of tooth development and the role of epithelial–mesenchymal interactions.", "study")
    assert plan.canonical_topics == ["tooth_development"]
    assert {facet.facet for facet in plan.facets} >= {"stages", "epithelial_mesenchymal_interactions"}


def test_named_subject_resolves_pronoun_in_later_operation():
    plan = plan_question("Define the DMFT index and explain its components, applications, limitations and differences from indices used for primary dentition.", "study")
    assert plan.canonical_topics == ["local:dmft_index"]
    assert not plan.needs_clarification


def test_unresolved_first_operation_still_needs_clarification():
    plan = plan_question("Explain its structure and define apoptosis.", "study")
    assert plan.needs_clarification

