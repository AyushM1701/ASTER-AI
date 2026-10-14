"""Task grammar regressions; no benchmark imports or medical answer keys."""
import pytest

from backend.app.services.question_plan import plan_question


@pytest.mark.parametrize("question,identity", [
    ("Explain the mechanism of cherubism as an ordered account. State evidence limitations.", "local:cherubism"),
    ("Write a 20-mark educational essay on chronic sialadenitis: definition, mechanism and histopathology.", "local:chronic_sialadenitis"),
    ("Critically appraise direct immunofluorescence: definition, investigations and diagnostic limitations.", "local:direct_immunofluorescence"),
    ("Define inflammation in an MDS oral pathology teaching context.", "local:inflammation"),
    ("Define oral exfoliative cytology in a postgraduate teaching context.", "local:oral_exfoliative_cytology"),
    ("Define amelogenesis imperfecta.", "local:amelogenesis_imperfecta"),
    ("Define amelogenesis.", "amelogenesis"),
])
def test_explicit_subject_preserved_across_generic_task_grammar(question, identity):
    plan = plan_question(question, "research" if question.startswith("Critically") else "study")
    assert plan.canonical_topics == [identity]
    assert all(f.topic_id == identity for f in plan.facets)


def test_entity_facet_words_do_not_create_unrequested_operations():
    for question in ("Define inflammation.", "Define oral exfoliative cytology."):
        assert [f.facet for f in plan_question(question, "study").facets] == ["definition"]


def test_explicit_histopathology_retained_with_architecture_and_cytology():
    plan = plan_question("Discuss histopathological features of ameloblastoma. Separate architecture from cytology where applicable.", "study")
    assert {f.facet for f in plan.facets} == {"histopathology", "architectural_features", "cytological_features"}
    assert plan.task == "histology"
    assert {f.facet for f in plan_question("Describe oral epithelium architecture.", "study").facets} == {"structure"}


def test_comparison_entity_stops_before_axes_and_cell_instruction_is_not_scope():
    plan = plan_question("Compare amelogenesis imperfecta with dentinogenesis imperfecta along definition and histopathology. Identify any evidence gap in each cell.", "study")
    assert plan.canonical_topics == ["local:amelogenesis_imperfecta", "local:dentinogenesis_imperfecta"]
    assert plan.comparison_axes == ["definition", "histopathology"]
    assert all(not f.scope for f in plan.facets)
    assert len(plan.facets) == 4


def test_clinical_scope_retained_but_educational_context_is_not_source_scope():
    clinical = plan_question("Compare cherubism with fibrous dysplasia: histopathology in children.", "study")
    assert clinical.canonical_topics == ["local:cherubism", "fibrous_dysplasia"]
    assert all(f.scope == "in children" for f in clinical.facets)
    pedagogic = plan_question("Define cherubism in a postgraduate teaching context.", "study")
    assert pedagogic.canonical_topics == ["local:cherubism"]
    assert all(not f.scope for f in pedagogic.facets)


def test_research_target_is_planned_without_assuming_source_readiness():
    plan = plan_question("Critically appraise oral brush cytology: definition and investigations. Distinguish a written account from observed laboratory competence.", "research")
    assert plan.canonical_topics == ["local:oral_brush_cytology"]
    assert {f.facet for f in plan.facets} == {"definition", "investigations"}
    assert plan.medical_audience == "research"


def test_multiple_independent_clauses_do_not_collapse_to_first_subject():
    plan = plan_question("Define oral epithelium; explain apoptosis intrinsic pathway.", "study")
    assert plan.canonical_topics == ["oral_epithelium", "apoptosis"]
    assert {(f.topic_id, f.facet) for f in plan.facets} == {("oral_epithelium", "definition"), ("apoptosis", "intrinsic_pathway")}


def test_entity_word_can_still_be_an_explicit_comparison_axis():
    plan = plan_question("Compare inflammation with necrosis along definition and inflammation.", "study")
    assert plan.canonical_topics == ["local:inflammation", "necrosis"]
    assert plan.comparison_axes == ["definition", "inflammation"]


def test_mixed_known_and_provisional_clauses_remain_separate():
    plan = plan_question("Define oral epithelium and explain the mechanism of oral lichen planus", "study")
    assert {(f.topic_id, f.facet) for f in plan.facets} == {("oral_epithelium", "definition"), ("local:oral_lichen_planus", "mechanism")}
    plan = plan_question("Discuss histopathological features of dentigerous cyst and oral lichen planus", "study")
    assert plan.canonical_topics == ["dentigerous_cyst", "local:oral_lichen_planus"]


def test_facet_language_cannot_remove_explicit_clinical_scope():
    plan = plan_question("Compare apoptosis and necrosis in diabetic adults with histological features", "study")
    assert all("diabetic adults" in f.scope for f in plan.facets)


def test_plain_language_is_presentation_not_clinical_population():
    plan = plan_question("Explain the molecular mechanism of apoptosis in simple language", "study")
    assert all(f.scope == "" for f in plan.facets)


def test_apoptotic_pathway_followup_has_the_same_explicit_process():
    plan = plan_question("Now explain the intrinsic and extrinsic apoptotic pathways in postgraduate detail without repeating your earlier explanation.", "study", "apoptosis")
    assert plan.canonical_topics == ["apoptosis"]
    assert {f.facet for f in plan.facets} >= {"intrinsic_pathway", "extrinsic_pathway"}
