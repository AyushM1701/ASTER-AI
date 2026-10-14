"""Behavior checks for the staged collector; no active application imports."""
import hashlib
import importlib
import io
import json
import urllib.error
import urllib.parse

import pytest


def module():
    try:
        return importlib.import_module("scripts.mds_open_collect")
    except ModuleNotFoundError:
        pytest.fail("Bounded open collector is not implemented")


def xml(license_url="https://creativecommons.org/licenses/by/4.0/", extra="", body=None):
    return (f'<article xmlns:xlink="http://www.w3.org/1999/xlink"><front><article-meta>'
            f'<article-id pub-id-type="pmc">123</article-id><title-group><article-title>Dental evidence</article-title>'
            f'</title-group><permissions><license xlink:href="{license_url}"><license-p>Creative Commons</license-p>'
            f'</license></permissions>{extra}</article-meta></front><body>'
            f'{body or "<sec><title>Mechanisms</title><p>Exact clinical source text with sufficient content for extraction.</p></sec>"}'
            f'</body></article>').encode()


@pytest.mark.parametrize("url,track", [
    ("https://creativecommons.org/licenses/by/4.0/", "default"),
    ("http://creativecommons.org/licenses/by/3.0/", "default"),
    ("https://creativecommons.org/publicdomain/zero/1.0/", "default"),
    ("https://creativecommons.org/licenses/by-sa/4.0/", "conditional"),
    ("https://creativecommons.org/licenses/by-nc/4.0/", "excluded"),
    ("https://creativecommons.org/licenses/by-nd/4.0/", "excluded"),
    ("https://creativecommons.org.evil.test/licenses/by/4.0/", "excluded"),
    ("", "excluded"),
])
def test_reuse_license_url_allowlist(url, track):
    assert module().inspect_xml(xml(url), "PMC123")["track"] == track


def test_contradictory_metadata_quarantines_without_export():
    result = module().inspect_xml(xml(extra='<permissions><license href="https://creativecommons.org/licenses/by-nc/4.0/"/></permissions>'), "PMC123")
    assert result["track"] == "excluded"
    assert "conflict" in result["reason"]


def test_no_derivatives_notice_cannot_be_hidden_by_by_badge():
    assert module().inspect_xml(xml(extra='<permissions><copyright-statement>All rights reserved. No derivatives.</copyright-statement></permissions>'), "PMC123")["track"] == "excluded"


def test_identifier_mismatch_is_rejected():
    with pytest.raises(ValueError, match="identifier"):
        module().inspect_xml(xml(), "PMC999")


def test_unknown_figure_rights_withhold_original_and_omit_caption():
    result = module().inspect_xml(xml(body='<sec><title>Results</title><p>Exact eligible paragraph.</p><fig id="f1"><caption><p>Excluded photograph.</p></caption><graphic href="private.jpg"/></fig></sec>'), "PMC123")
    assert result["retain_original"] is False
    assert [s["text"] for s in result["sections"]] == ["Exact eligible paragraph."]
    assert b"private.jpg" not in result["sanitized_xml"]
    assert result["omitted_assets"] == ["fig:f1"]


def test_extraction_keeps_source_span_and_references_separate():
    result = module().inspect_xml(xml(body='<sec><title>Diagnosis</title><p>First source sentence.</p><p>Second source sentence.</p></sec><ref-list><ref>Reference noise.</ref></ref-list>'), "PMC123")
    assert result["sections"][1]["coordinate"] == "/article/body/sec[1]/p[2]"
    assert result["sections"][1]["heading"] == ["Diagnosis"]
    assert "Reference noise" not in " ".join(s["text"] for s in result["sections"])


@pytest.mark.parametrize("body", [b"<article>", b'<!DOCTYPE article [<!ENTITY secret SYSTEM "file:///etc/passwd">]><article>&secret;</article>'])
def test_malformed_or_entity_xml_never_exports(body):
    with pytest.raises(ValueError):
        module().inspect_xml(body, "PMC123")


def test_empty_article_is_extraction_failure():
    with pytest.raises(ValueError, match="body"):
        module().inspect_xml(xml(body="<sec><title>Empty</title></sec>"), "PMC123")


@pytest.mark.parametrize("url", ["http://127.0.0.1/a", "https://10.0.0.1/a", "https://[::1]/", "file:///a", "https://user:pass@www.ebi.ac.uk/a", "https://evil.test/a"])
def test_unsafe_urls_rejected_before_fetch(url):
    with pytest.raises(ValueError):
        module().validate_url(url)


def test_private_dns_and_redirect_targets_blocked(monkeypatch):
    m = module()
    monkeypatch.setattr(m.socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("192.168.1.7", 443))])
    with pytest.raises(ValueError, match="public"):
        m.validate_url("https://www.ebi.ac.uk/europepmc/webservices/rest/search")
    with pytest.raises(ValueError):
        m.SafeRedirect().redirect_request(None, None, 302, "Found", {}, "https://127.0.0.1/secret")


def test_safe_paths_reject_traversal_and_outside_workspace(tmp_path):
    m = module()
    with pytest.raises(ValueError):
        m.safe_path(tmp_path, "../outside")
    with pytest.raises(ValueError):
        m.safe_path(tmp_path, "C:/outside")


def test_immutable_atomic_cache_checksums_and_interrupted_write(tmp_path):
    m = module()
    dest = tmp_path / "snapshot.xml"
    m.atomic_bytes(dest, b"first", immutable=True)
    with pytest.raises(ValueError, match="immutable"):
        m.atomic_bytes(dest, b"different", immutable=True)
    assert dest.read_bytes() == b"first"
    assert not list(tmp_path.glob("*.part"))
    assert m.checked_bytes(dest, "0" * 64) is None
    assert m.checked_bytes(dest, hashlib.sha256(b"first").hexdigest()) == b"first"


def test_budget_never_overruns_request_or_bytes():
    m = module()
    b = m.Budget({"max_requests": 1, "max_bytes": 4, "max_seconds": 10, "max_file_bytes": 4, "per_host_requests": 1})
    b.request("www.ebi.ac.uk")
    with pytest.raises(m.BudgetStop):
        b.request("www.ebi.ac.uk")
    with pytest.raises(m.BudgetStop):
        b.add_bytes(5)
    assert b.bytes == 0


def test_retry_after_rate_limit_is_bounded_and_interruption_not_cached(monkeypatch, tmp_path):
    m = module()
    monkeypatch.setattr(m, "validate_url", lambda url: url)
    delays = []
    calls = []
    class Response(io.BytesIO):
        headers = {"Content-Type": "application/xml", "Content-Length": "5"}
        status = 200
    class Transport:
        def open(self, request, timeout):
            calls.append(request.full_url)
            if len(calls) == 1:
                raise urllib.error.HTTPError(request.full_url, 429, "rate limited", {"Retry-After": "2"}, None)
            return Response(b"12345")
    b = m.Budget({"max_requests": 5, "max_bytes": 50, "max_seconds": 100, "max_file_bytes": 10, "per_host_requests": 5})
    client = m.Client(b, {"retries": 2, "host_interval_seconds": 0, "timeout_seconds": 2, "max_retry_after_seconds": 5}, opener=Transport(), sleep=delays.append)
    assert client.fetch("https://www.ebi.ac.uk/a", "xml") == b"12345"
    assert delays == [2]
    assert b.requests == 2


def test_oversized_and_truncated_network_document_not_returned(monkeypatch):
    m = module()
    monkeypatch.setattr(m, "validate_url", lambda url: url)
    class Response(io.BytesIO):
        headers = {"Content-Type": "application/xml", "Content-Length": "30"}
        status = 200
    class Transport:
        def open(self, *a, **k):
            return Response(b"123")
    b = m.Budget({"max_requests": 3, "max_bytes": 50, "max_seconds": 100, "max_file_bytes": 10, "per_host_requests": 3})
    c = m.Client(b, {"retries": 0, "host_interval_seconds": 0, "timeout_seconds": 2}, opener=Transport())
    with pytest.raises(ValueError, match="size"):
        c.fetch("https://www.ebi.ac.uk/a", "xml")


def test_duplicate_versions_and_missing_doi_share_family_split():
    m = module()
    rows = [{"id": "a", "doi": None, "pmcid": "PMC123", "text_hash": "x"},
            {"id": "b", "doi": None, "pmcid": "PMC123", "text_hash": "y"},
            {"id": "c", "doi": "10.1/version", "pmcid": "PMC321", "text_hash": "x"}]
    result = m.deduplicate(rows)
    assert len({r["version_family_id"] for r in result}) == 1
    assert len({r["split"] for r in result}) == 1
    assert sum(r["duplicate_of"] is None for r in result) == 1


def test_project_taxonomy_maps_all_nine_specialties_and_foundations():
    rows = module().topics({"taxonomy": "configs/all_mds_topics.json"})
    assert {r["specialty_id"] for r in rows} == {"oral_pathology", "oral_medicine", "oral_surgery", "endodontics", "prosthodontics", "periodontology", "orthodontics", "pediatric_dentistry", "public_health", "foundations"}


def test_search_endpoint_uses_default_relevance_without_unsupported_sort():
    params = urllib.parse.parse_qs(urllib.parse.urlsplit(module().search_url({"id": "x", "query": "dental", "specialty_id": "oral_pathology"}, {"page_size": 15})).query)
    assert "sort" not in params
    assert params["cursorMark"] == ["*"]
    assert params["pageSize"] == ["15"]


def test_snapshot_checksum_failure_withholds_derived_export(tmp_path):
    m = module()
    p = tmp_path / "raw" / "item.xml"
    m.atomic_bytes(p, b"tampered")
    d = {"stored_document_path": "raw/item.xml", "stored_sha256": hashlib.sha256(b"original").hexdigest(), "extracted_path": "extracted/item.json"}
    assert m.snapshot_valid(d, tmp_path) is False


def test_article_retraction_type_is_excluded():
    raw = xml().replace(b"<article xmlns", b'<article article-type="retraction" xmlns')
    assert module().inspect_xml(raw, "PMC123")["track"] == "excluded"


def test_authoritative_rights_notice_plain_url_is_accepted():
    raw = xml().replace(b' xlink:href="https://creativecommons.org/licenses/by/4.0/"', b'').replace(b'Creative Commons</license-p>', b'Creative Commons Attribution https://creativecommons.org/licenses/by/4.0/</license-p>')
    assert module().inspect_xml(raw, "PMC123")["license"] == "CC-BY-4.0"


def test_topic_anchor_alone_does_not_admit_nondental_specialty_review():
    topic = {"title": "Dental epidemiology", "specialty_id": "public_health"}
    assert module().relevance("Hantavirus disease: epidemiology and treatment", topic) is False
    assert module().relevance("Dental caries epidemiology in childhood", topic) is True


def test_metadata_discovery_can_resume_into_rights_gated_acquisition(monkeypatch, tmp_path):
    m = module()
    monkeypatch.setattr(m, "ROOT", tmp_path)
    topic = {"id": "test-topic", "title": "Dental mechanisms", "query": "dental", "specialty_id": "endodontics", "scope_status": "provisional"}
    monkeypatch.setattr(m, "topics", lambda c: [topic])
    payload = {"hitCount": 1, "resultList": {"result": [{"pmcid": "PMC123", "isOpenAccess": "Y", "title": "Dental mechanisms", "pubTypeList": {"pubType": ["review"]}}]}}
    monkeypatch.setattr(m.Client, "fetch", lambda self, url, expected: json.dumps(payload).encode() if expected == "json" else xml())
    config = {"output": "corpus", "max_documents": 1, "max_bytes": 50000, "max_seconds": 10, "max_requests": 10, "per_host_requests": 10, "max_file_bytes": 10000, "page_size": 1, "candidates_per_topic": 1, "documents_per_topic": 1, "minimum_prose_characters": 1, "version": "test", "assets": "strict"}
    assert m.collect(config, stage="discover")["counts"]["rights_verified_default"] == 0
    assert m.collect(config)["counts"]["rights_verified_default"] == 1


def test_eligible_table_preserves_headers_cells_and_coordinates():
    body = '<sec><title>Results</title><p>Eligible source explanation.</p><table-wrap id="t1"><permissions><license href="https://creativecommons.org/licenses/by/4.0/"/></permissions><table><thead><tr><th>Group</th><th>Concentration (mg/L)</th></tr></thead><tbody><tr><td>A</td><td>2.5</td></tr></tbody></table></table-wrap></sec>'
    result = module().inspect_xml(xml(body=body), "PMC123")
    tables = [s for s in result["sections"] if s.get("kind") == "table"]
    assert result["retain_original"] is True
    assert tables[0]["table"]["headers"] == [["Group", "Concentration (mg/L)"]]
    assert tables[0]["table"]["rows"] == [["A", "2.5"]]
    assert tables[0]["coordinate"] == "/article/body/sec[1]/table-wrap[1]/table[1]"


def test_truncated_response_has_no_partial_usable_result(monkeypatch):
    m = module()
    monkeypatch.setattr(m, "validate_url", lambda url: url)
    class Response(io.BytesIO):
        headers = {"Content-Type": "application/xml", "Content-Length": "5"}
        status = 200
    class Transport:
        def open(self, *args, **kwargs):
            return Response(b"abc")
    b = m.Budget({"max_requests": 3, "max_bytes": 50, "max_seconds": 100, "max_file_bytes": 10, "per_host_requests": 3})
    with pytest.raises(ValueError, match="Interrupted"):
        m.Client(b, {"retries": 0, "host_interval_seconds": 0}, opener=Transport()).fetch("https://www.ebi.ac.uk/a", "xml")


def test_heldout_sources_never_export_to_training_or_rag(tmp_path):
    m = module()
    config = {"minimum_prose_characters": 1, "version": "test", "assets": "strict"}
    topic = {"id": "topic", "title": "Dental mechanisms", "query": "dental", "specialty_id": "endodontics", "scope_status": "provisional"}
    docs = {}
    for number in range(123, 143):
        raw = xml(body=f'<sec><title>Methods</title><p>Unique eligible source paragraph for sample {number}.</p></sec>').replace(b">123</article-id>", f">{number}</article-id>".encode())
        inspected = m.inspect_xml(raw, f"PMC{number}")
        doc = m.make_document({"pmcid": f"PMC{number}"}, topic, inspected, raw, tmp_path, config)
        docs[doc["id"]] = doc
    state = {"documents": docs, "searches": [], "decisions": [], "failures": []}
    m.export_report(state, config, tmp_path, [topic])
    def records(name):
        return [json.loads(line) for line in (tmp_path / name).read_text(encoding="utf8").splitlines()]
    held = {r["document_id"] for r in records("evaluation_holdout/source_chunks.jsonl")}
    rag = {r["document_id"] for r in records("rag_chunks/staged_rag.jsonl")}
    training = {r["document_id"] for r in records("training_candidates/rights_screened_candidates.jsonl")}
    assert held
    assert held.isdisjoint(rag | training)
    assert rag == training


def test_gap_query_constrains_title_without_recent_cutoff():
    result = module().query_for({"query": "oral AND histology", "title": "Oral histology", "specialty_id": "foundations", "require_title_anchors": True})
    assert "TITLE:histology" in result
    assert "FIRST_PDATE" not in result


@pytest.mark.parametrize("title,want", [("Dental expert consensus statement", "consensus_statement_title_indicated"), ("A systematic review and meta-analysis", "systematic_review_title_indicated"), ("An umbrella review of oral disease", "umbrella_review_title_indicated"), ("A dental narrative review", "narrative_review_title_indicated"), ("Study of oral disease", "journal_review_design_unresolved"), ("A propensity score-matched cohort study", "primary_study_title_indicated")])
def test_resource_type_is_title_indicated_without_quality_grade(title, want):
    assert module().resource_type(title) == want


def test_omitted_credited_paragraph_does_not_shift_source_coordinates():
    raw = xml(body='<sec><title>Methods</title><p>Reprinted from third party with permission.</p><p>Exact eligible source text.</p></sec>')
    result = module().inspect_xml(raw, "PMC123")
    assert result["sections"][0]["coordinate"] == "/article/body/sec[1]/p[2]"
    assert result["sections"][0]["text"] == "Exact eligible source text."


def test_near_duplicate_prose_with_changed_identifier_has_one_split():
    text = " ".join(f"Unique dental mechanism phrase {n}." for n in range(200))
    rows = [{"id": "published", "pmcid": "PMC1", "normalized_text": text}, {"id": "accepted", "pmcid": "PMC2", "normalized_text": text.replace("phrase 199", "phrase 200")}]
    result = module().deduplicate(rows)
    assert len({r["version_family_id"] for r in result}) == 1
    assert len({r["split"] for r in result}) == 1


def test_author_names_keep_given_and_family_names_separate():
    raw = xml(extra='<contrib-group><contrib contrib-type="author"><name><surname>Smith</surname><given-names>Jane</given-names></name></contrib></contrib-group>')
    assert module().inspect_xml(raw, "PMC123")["authors"] == ["Jane Smith"]


def test_extreme_xml_nesting_is_rejected_before_recursive_extraction():
    raw = xml(body="<sec>" * 100 + "<p>Extreme nesting source.</p>" + "</sec>" * 100)
    with pytest.raises(ValueError, match="depth"):
        module().inspect_xml(raw, "PMC123")
