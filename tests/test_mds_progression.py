from backend.app.services.progression import asks_for_depth, remove_previous_claims


def test_progression_keeps_new_whole_qualified_unit_and_rebinds_sections():
    result = {"claims": [{"text": "Old definition", "citation_ids": ["a"]}, {"text": "New mechanism. However, evidence is limited.", "citation_ids": ["b"]}],
        "citations": [{"chunk_id": "a"}, {"chunk_id": "b"}],
        "claim_evidence": [{"claim_index": 0}, {"claim_index": 1}],
        "structured_answer": {"sections": [{"claim_indices": [0, 1], "state": "supported"}]}}
    checked = remove_previous_claims(result, [{"response": {"claims": [{"text": "Old definition"}]}}])
    assert checked["claims"] == [{"text": "New mechanism. However, evidence is limited.", "citation_ids": ["b"]}]
    assert checked["claim_evidence"] == [{"claim_index": 0}]
    assert checked["structured_answer"]["sections"][0]["claim_indices"] == [0]
    assert checked["citations"] == [{"chunk_id": "b"}]


def test_depth_requests_do_not_include_new_symptom_questions():
    assert asks_for_depth("Go deeper into the cellular mechanisms without repeating the previous explanation.")
    assert asks_for_depth("Now explain the intrinsic pathway in postgraduate detail without repeating.")
    assert not asks_for_depth("My tooth hurts. What should I do?")
