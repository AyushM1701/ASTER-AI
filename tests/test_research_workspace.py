import httpx
import pytest

from backend.app.services.research_workspace import (
    LiteratureSearch,
    ResearchRequest,
    export_markdown,
)


def record(**kw):
    return dict(
        id="123",
        source="MED",
        title="Oral leukoplakia study",
        authorString="A Author",
        pubYear="2024",
        doi="10.1000/example",
        abstractText="Background: Oral leukoplakia is studied. Methods: Adults were observed. Results: Findings remain uncertain. Conclusions: Further studies are needed.",
        **kw,
    )


def provider(rows, xml=None):
    def handle(request):
        if request.url.path.endswith("fullTextXML"):
            return httpx.Response(200, text=xml or "", headers={"content-type": "application/xml"})
        return httpx.Response(200, json={"hitCount": len(rows), "resultList": {"result": rows}})

    return httpx.Client(transport=httpx.MockTransport(handle), trust_env=False)


def request(**kw):
    return ResearchRequest(
        question="Malignant transformation of oral leukoplakia",
        population="Adults",
        article_type="narrative review",
        query="oral leukoplakia",
        public_query_confirmed=True,
        **kw,
    )


def test_search_log_dedup_and_access_honesty():
    result = LiteratureSearch(provider([record(), record()])).search(request())
    assert result["search"]["scope"] == "limited_single_provider"
    assert result["search"]["received"] == 2
    assert len(result["papers"]) == 1
    assert result["search"]["duplicates_removed"] == 1
    paper = result["papers"][0]
    assert paper["access"] == "abstract_only"
    assert paper["publication_status"] == "notices_not_reported_by_provider"
    assert sum(len(q["text"].split()) for q in paper["passages"]) <= 25
    draft = export_markdown(result)
    assert "limited" in draft.lower() and "not independently" in draft.lower()
    assert "10.1000/example" in draft
    assert paper["passages"][0]["text"] in draft


def test_retracted_papers_are_not_draft_evidence():
    result = LiteratureSearch(
        provider([record(pubTypeList={"pubType": ["Retracted Publication"]})])
    ).search(request())
    assert result["papers"][0]["publication_status"] == "retracted"
    assert result["evidence_table"] == []
    assert result["task_completion"] is False


def test_full_text_requires_machine_readable_permission():
    xml = '<article><front><article-meta><article-id pub-id-type="pmc">123</article-id><article-id pub-id-type="doi">10.1000/example</article-id><permissions><license><license-p>Copyright publisher</license-p></license></permissions></article-meta></front><body><sec><title>Results</title><p>Some result</p></sec></body></article>'
    result = LiteratureSearch(provider([record(pmcid="PMC123", isOpenAccess="Y")], xml)).search(
        request(inspect_full_text=True)
    )
    assert result["papers"][0]["access"] == "abstract_only"
    assert "full_text_permission_not_supported" in result["papers"][0]["warnings"]


def test_permitted_full_text_with_identifiers_is_bound_to_passages():
    xml = '<article xmlns:xlink="http://www.w3.org/1999/xlink"><front><article-meta><article-id pub-id-type="pmc">123</article-id><article-id pub-id-type="doi">10.1000/example</article-id><permissions><license xlink:href="https://creativecommons.org/licenses/by/4.0/"/></permissions></article-meta></front><body><sec><title>Methods</title><p>Adults with leukoplakia were followed in an observational cohort.</p></sec><sec><title>Results</title><p>These findings apply to this cohort only.</p></sec></body></article>'
    result = LiteratureSearch(provider([record(pmcid="PMC123", isOpenAccess="Y")], xml)).search(
        request(inspect_full_text=True)
    )
    assert result["papers"][0]["access"] == "permitted_full_text_inspected"
    row = result["evidence_table"][0]
    assert row["methods"]["passage_id"]
    assert row["findings"]["text"] == "These findings apply to this cohort only."
    assert row["limitations"]["text"] == "Not extracted; assess in the original paper."


def test_full_text_identity_mismatch_and_dtd_rejected():
    for xml in (
        '<!DOCTYPE article [<!ENTITY bad "bad">]><article/>',
        '<article><front><article-meta><article-id pub-id-type="doi">10.1000/other</article-id></article-meta></front></article>',
    ):
        result = LiteratureSearch(provider([record(pmcid="PMC123", isOpenAccess="Y")], xml)).search(
            request(inspect_full_text=True)
        )
        assert result["papers"][0]["access"] == "abstract_only"


def test_real_jats_external_doctype_is_safe_without_loading_dtd():
    xml = '<!DOCTYPE article PUBLIC "JATS" "https://invalid.example/external.dtd"><article xmlns:xlink="http://www.w3.org/1999/xlink"><front><article-meta><article-id pub-id-type="pmcid">PMC123</article-id><article-id pub-id-type="doi">10.1000/example</article-id><permissions><license xlink:href="http://creativecommons.org/licenses/by/4.0/"/></permissions></article-meta></front><body><sec><title>Results</title><p>Only this study result.</p></sec></body></article>'
    result = LiteratureSearch(provider([record(pmcid="PMC123", isOpenAccess="Y")], xml)).search(
        request(inspect_full_text=True)
    )
    assert result["papers"][0]["access"] == "permitted_full_text_inspected"


def test_license_href_inside_license_paragraph_is_recognized():
    xml = '<article xmlns:xlink="http://www.w3.org/1999/xlink"><front><article-meta><article-id pub-id-type="pmcid">PMC123</article-id><article-id pub-id-type="doi">10.1000/example</article-id><permissions><license><license-p>Licensed under <ext-link xlink:href="https://creativecommons.org/licenses/by/4.0/">CC BY</ext-link></license-p></license></permissions></article-meta></front><body><sec><title>Results</title><p>Only this study result.</p></sec></body></article>'
    result = LiteratureSearch(provider([record(pmcid="PMC123", isOpenAccess="Y")], xml)).search(
        request(inspect_full_text=True)
    )
    assert result["papers"][0]["access"] == "permitted_full_text_inspected"


def test_provider_failure_is_explicit():
    client = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(503)))
    with pytest.raises(httpx.HTTPError):
        LiteratureSearch(client).search(request())


def test_do_not_silently_merge_conflicting_doi_metadata():
    second = record()
    second["title"] = "A different article"
    result = LiteratureSearch(provider([record(), second])).search(request())
    assert result["search"]["identity_conflicts"] == 1
    assert result["evidence_table"] == []


def test_public_query_confirmation_and_limits():
    with pytest.raises(ValueError):
        ResearchRequest(
            question="q",
            population="p",
            query="q",
            article_type="review",
            public_query_confirmed=False,
        )
    with pytest.raises(ValueError):
        request(limit=1000)


def test_bibliography_preserves_structured_authors():
    from backend.app.services.research_workspace import export_bibtex

    r = record(authorList={"author": [{"fullName": "Smith J"}, {"fullName": "Jones A"}]})
    result = LiteratureSearch(provider([r])).search(request())
    assert "Smith J and Jones A" in export_bibtex(result)


def test_duplicate_notices_cannot_downgrade_retraction():
    a = record(pubTypeList={"pubType": ["Retracted Publication"]})
    b = record(commentCorrectionList={"commentCorrection": [{"type": "ErratumIn"}]})
    result = LiteratureSearch(provider([a, b])).search(request())
    assert result["papers"][0]["publication_status"] == "retracted"
