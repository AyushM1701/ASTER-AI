from backend.app.services.evidence_plan import build_evidence_plan
from backend.app.services.question_plan import QuestionPlan, RequestedFacet
from tests.mds_fixtures import make_teacher


def test_specific_facet_query_can_find_evidence_missed_by_entity_only_search(tmp_path):
    teacher, rows = make_teacher(tmp_path, [("apoptosis", "Apoptosis mechanism",
        "Apoptosis mechanism activates a synthetic pathway with source qualifications retained.")])
    calls = []
    def search(query, limit=8):
        calls.append(query)
        return rows if query == "apoptosis mechanism" else []
    teacher.search = search
    facet = RequestedFacet(topic_id="apoptosis", facet="mechanism", query="apoptosis mechanism")
    evidence, selected = build_evidence_plan(QuestionPlan(original_question="Explain apoptosis mechanism", topic="apoptosis", facets=[facet]), teacher, teacher.references)
    assert evidence.facets[0].state == "supported"
    assert list(selected) == [rows[0].chunk_id]
    assert "apoptosis mechanism" in calls


def test_facet_search_cannot_override_a_source_hold(tmp_path):
    teacher, rows = make_teacher(tmp_path, [("apoptosis", "Apoptosis mechanism",
        "Apoptosis mechanism activates a synthetic pathway with source qualifications retained.", {"runtime_policy": "exclude"})])
    teacher.search = lambda *args, **kwargs: rows
    facet = RequestedFacet(topic_id="apoptosis", facet="mechanism", query="apoptosis mechanism")
    evidence, selected = build_evidence_plan(QuestionPlan(original_question="Explain apoptosis mechanism", topic="apoptosis", facets=[facet]), teacher, teacher.references)
    assert evidence.facets[0].state == "missing" and not selected


def test_explicit_detail_accepts_source_hyphens_without_losing_topic():
    from backend.app.services.evidence_plan import supports_facet

    facet = RequestedFacet(topic_id="apoptosis", facet="cell_cycle_dysregulation", query="apoptosis cell cycle dysregulation")
    assert supports_facet(facet, "Apoptosis involves cell-cycle dysregulation in this synthetic mechanics fixture with limitations.")
    assert not supports_facet(facet, "Unrelated neuronal pathways involve cell-cycle dysregulation in this synthetic mechanics fixture.")
