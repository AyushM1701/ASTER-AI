"""Acquisition must not turn a search hit into verified medical evidence."""

import xml.etree.ElementTree as ET
from http.client import IncompleteRead

import pytest

from scripts.acquire_all_mds import candidate_allowed, inspect_article


def test_candidates_require_identifiable_open_peer_reviewed_articles():
    good = {"pmcid": "PMC123", "isOpenAccess": "Y", "title": "Dental caries review",
            "pubTypeList": {"pubType": ["Review", "Journal Article"]}}
    assert candidate_allowed(good) is None
    assert candidate_allowed({**good, "isOpenAccess": "N"})
    assert candidate_allowed({**good, "pmcid": "../secret"})
    assert candidate_allowed({**good, "pubTypeList": {"pubType": ["Preprint"]}})
    assert candidate_allowed({**good, "commentCorrectionList": {"commentCorrection": [
        {"type": "Retraction in", "id": "123"}]}})
    assert candidate_allowed({**good, "title": "Corrigendum: Dental caries review"})


def xml(pmcid="123", license="by/4.0", notes=""):
    return ET.fromstring(f'''<article article-type="review-article"><front><article-meta>
    <article-id pub-id-type="pmc">{pmcid}</article-id><title-group><article-title>Dental caries review</article-title></title-group>
    <permissions><license><license-p>https://creativecommons.org/licenses/{license}/</license-p></license></permissions>
    {notes}</article-meta></front><body><sec><title>Introduction</title><p>Dental research has population-specific limitations.</p></sec></body></article>''')


def test_xml_identity_license_and_withdrawal_are_checked_before_ingestion():
    assert inspect_article(xml(), "PMC123")["license"] == "CC-BY-4.0"
    with pytest.raises(ValueError, match="identifier"):
        inspect_article(xml("456"), "PMC123")
    with pytest.raises(ValueError, match="derivative"):
        inspect_article(xml(license="by-nc-nd/4.0"), "PMC123")
    with pytest.raises(ValueError, match="restriction"):
        inspect_article(xml(notes="<custom-meta-group><custom-meta><meta-value>Use for AI training is prohibited.</meta-value></custom-meta></custom-meta-group>"), "PMC123")
    with pytest.raises(ValueError, match="retract"):
        inspect_article(xml(notes='<related-article related-article-type="retracted-article"/>'), "PMC123")
    with pytest.raises(ValueError, match="supported"):
        inspect_article(xml(license="by/2.0"), "PMC123")


def test_publisher_pmcid_identifier_variant_is_supported():
    article = xml()
    node = article.find('./front/article-meta/article-id')
    node.set('pub-id-type', 'pmcid')
    node.text = 'PMC123'
    assert inspect_article(article, "PMC123")["license"] == "CC-BY-4.0"


def test_interrupted_http_body_is_retried_without_returning_partial_bytes(monkeypatch):
    from scripts import acquire_all_mds

    attempts = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            attempts.append(1)
            if len(attempts) == 1:
                raise IncompleteRead(b"partial")
            return b"complete"

    monkeypatch.setattr(acquire_all_mds.urllib.request, "urlopen", lambda *a, **kw: Response())
    monkeypatch.setattr(acquire_all_mds.time, "sleep", lambda seconds: None)
    assert acquire_all_mds.fetch("https://www.ebi.ac.uk/example") == b"complete"
    assert len(attempts) == 2


def test_topic_selection_requires_a_specific_title_anchor():
    from scripts.acquire_all_mds import topic_title_match

    assert topic_title_match("The evolving microbiome of dental caries", "Dental caries")
    assert not topic_title_match("AI tools in medicine and healthcare", "Dental caries")
    assert topic_title_match("Regenerative endodontic procedures", "Regenerative endodontics")
    assert not topic_title_match("Global oral health report", "Public oral health India")
