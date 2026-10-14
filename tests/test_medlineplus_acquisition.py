import pytest

from research.data.medlineplus import parse_topics


def test_full_summary_is_preserved_not_snippet_or_external_content():
    raw = b'''<nlmSearchResult><list><document url="https://medlineplus.gov/asthma.html"><content name="title">Asthma</content><content name="FullSummary">&lt;p&gt;Complete first paragraph.&lt;/p&gt;&lt;p&gt;Qualifications remain here.&lt;/p&gt;</content><content name="snippet">Partial snippet</content></document></list></nlmSearchResult>'''
    item = parse_topics(raw)[0]
    assert item["text"] == "Complete first paragraph.\n\nQualifications remain here."
    assert "snippet" not in item["text"]
    assert item["clinical_review_status"] == "pending"
    assert item["runtime_admitted"] is False
    assert item["training_approved"] is False


@pytest.mark.parametrize("raw", [
    b'<!DOCTYPE x [<!ENTITY leak "secret">]><nlmSearchResult>&leak;</nlmSearchResult>',
    b'<nlmSearchResult><list><document url="https://evil.test/a"><content name="title">Asthma</content><content name="FullSummary">Foreign</content></document></list></nlmSearchResult>',
    b'<wrong/>',
])
def test_invalid_xml_or_non_medline_topics_rejected(raw):
    with pytest.raises(ValueError):
        parse_topics(raw)
