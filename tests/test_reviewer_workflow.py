import pytest


def setup_review(tmp_path):
    from research.data.review import ReviewStore

    store = ReviewStore(tmp_path / "review.sqlite3")
    rubric = {"version": "synthetic-mechanics", "dimensions": ["accuracy", "completeness"],
              "score_min": 0, "score_max": 4}
    cases = [{"case_id": "original-case", "question": "Synthetic question?", "answer": {"claims": []},
              "source_hashes": {}, "independent_reference_rubric": None}]
    batch = store.create_batch(cases, rubric, seed=42, source_version="synthetic", rights="local_review_authorized")
    for identity in ("one", "two", "three"):
        store.register_reviewer(identity, qualification="Synthetic fixture; not a dentist", specialty="test", independent=True)
    return store, batch


def submission(packet, score=2):
    return {"packet_sha256": packet["packet_sha256"], "rubric_sha256": packet["rubric_sha256"],
            "reviews": [{"blind_id": case["blind_id"], "case_sha256": case["case_sha256"],
                         "scores": {"accuracy": score, "completeness": None}, "critical_error": False,
                         "reason": "Synthetic mechanics assessment", "review_type": "synthetic_mechanics"}
                        for case in packet["cases"]]}


def test_blinded_packet_does_not_leak_system_or_private_reviewer_identity(tmp_path):
    store, batch = setup_review(tmp_path)
    assignment, token = store.assign(batch, "one")
    packet = store.packet(assignment, token)
    assert "original-case" not in str(packet)
    assert "one" not in packet
    assert "Synthetic fixture; not a dentist" not in str(packet)
    assert packet["independent_reference_state"] == "pending"
    assert packet["cases"][0]["independent_reference_rubric"] is None
    store.close()


def test_import_requires_assignment_token_and_exact_case_rubric_packet_hashes(tmp_path):
    store, batch = setup_review(tmp_path)
    assignment, token = store.assign(batch, "one")
    packet = store.packet(assignment, token)
    payload = submission(packet)
    with pytest.raises(ValueError, match="assignment authorization"):
        store.import_reviews(assignment, "wrong", payload)
    payload["reviews"][0]["case_sha256"] = "wrong"
    with pytest.raises(ValueError, match="case identity"):
        store.import_reviews(assignment, token, payload)
    assert store.report(batch)["submitted_reviews"] == 0
    store.close()


def test_missing_scores_stay_missing_and_one_rater_is_not_agreement(tmp_path):
    store, batch = setup_review(tmp_path)
    assignment, token = store.assign(batch, "one")
    packet = store.packet(assignment, token)
    store.import_reviews(assignment, token, submission(packet))
    report = store.report(batch)
    assert report["submitted_reviews"] == 1
    assert report["qualified_clinical_accuracy"] is None
    assert report["agreement"]["accuracy"]["cohen_kappa"] is None
    assert report["agreement"]["completeness"]["paired_cases"] == 0
    assert report["qualified_review"] == "external_credential_and_reference_verification_pending"
    with pytest.raises(ValueError, match="immutable"):
        store.import_reviews(assignment, token, submission(packet))
    store.close()


def test_two_rater_disagreement_requires_distinct_assigned_adjudicator(tmp_path):
    store, batch = setup_review(tmp_path)
    for identity, score in (("one", 1), ("two", 3)):
        assignment, token = store.assign(batch, identity)
        packet = store.packet(assignment, token)
        store.import_reviews(assignment, token, submission(packet, score))
    report = store.report(batch)
    assert report["disagreement_cases"] == 1
    assert report["adjudicated_cases"] == 0
    with pytest.raises(ValueError, match="independent third reviewer"):
        store.assign(batch, "one", role="adjudicator")
    assignment, token = store.assign(batch, "three", role="adjudicator")
    packet = store.packet(assignment, token)
    payload = submission(packet, 2)
    payload["reviews"][0]["adjudication_rationale"] = "Synthetic resolution of the differing scores."
    store.import_reviews(assignment, token, payload)
    assert store.report(batch)["adjudicated_cases"] == 1
    assert store.report(batch)["submitted_reviews"] == 2
    store.close()


def test_atomic_import_rejects_foreign_case_and_out_of_range_scores(tmp_path):
    store, batch = setup_review(tmp_path)
    assignment, token = store.assign(batch, "one")
    packet = store.packet(assignment, token)
    payload = submission(packet)
    payload["reviews"][0]["scores"]["accuracy"] = 9
    with pytest.raises(ValueError, match="score"):
        store.import_reviews(assignment, token, payload)
    payload = submission(packet)
    payload["reviews"].append({**payload["reviews"][0], "blind_id": "foreign"})
    with pytest.raises(ValueError, match="assigned cases"):
        store.import_reviews(assignment, token, payload)
    assert store.report(batch)["submitted_reviews"] == 0
    store.close()


def test_blinding_omits_pipeline_metadata_and_critical_error_disagreements_count(tmp_path):
    from research.data.review import ReviewStore

    store = ReviewStore(tmp_path / "review.sqlite3")
    batch = store.create_batch(
        [{"case_id": "B7:model-name", "question": "Synthetic?", "source_hashes": {},
          "answer": {"claims": [], "answer_method": "B7", "model": "model-name", "clinical_score": 0.9}}],
        {"version": "fixture", "dimensions": ["accuracy"], "score_min": 0, "score_max": 4},
        seed=1, source_version="synthetic", rights="local_review_authorized")
    for index, identity in enumerate(("one", "two")):
        store.register_reviewer(identity, qualification="Synthetic fixture", specialty="test", independent=True)
        assignment, token = store.assign(batch, identity)
        packet = store.packet(assignment, token)
        assert "model-name" not in str(packet) and "clinical_score" not in str(packet)
        payload = {"packet_sha256": packet["packet_sha256"], "rubric_sha256": packet["rubric_sha256"],
                   "reviews": [{"blind_id": case["blind_id"], "case_sha256": case["case_sha256"],
                                "scores": {"accuracy": 2}, "critical_error": bool(index),
                                "reason": "Synthetic mechanics", "review_type": "synthetic_mechanics"} for case in packet["cases"]]}
        store.import_reviews(assignment, token, payload)
    assert store.report(batch)["disagreement_cases"] == 1
    store.close()


def test_blinded_answer_keeps_display_layout_and_spans_without_nested_model_metadata(tmp_path):
    from research.data.review import ReviewStore

    store = ReviewStore(tmp_path / "review.sqlite3")
    answer = {"claims": [{"text": "Synthetic statement.", "citation_ids": [], "model": "B7-private-model"}],
              "structured_answer": {"task": "compare", "sections": [{"heading": "First", "claim_indices": [0], "state": "supported"}]},
              "comparison": {"entities": ["First", "Second"], "axes": []},
              "claim_evidence": [{"claim_index": 0, "span": {"start": 0, "end": 20, "text_sha256": "a" * 64}}]}
    batch = store.create_batch([{"case_id": "original", "question": "Compare synthetic subjects.", "answer": answer, "source_hashes": {}}],
                              {"version": "fixture", "dimensions": ["accuracy"], "score_min": 0, "score_max": 4},
                              seed=1, source_version="synthetic", rights="local_review_authorized")
    store.register_reviewer("one", qualification="Synthetic", specialty="test", independent=True)
    assignment, token = store.assign(batch, "one")
    blinded = store.packet(assignment, token)["cases"][0]["answer"]
    assert "B7-private-model" not in str(blinded)
    assert blinded["structured_answer"] == answer["structured_answer"]
    assert blinded["comparison"] == answer["comparison"]
    assert blinded["claim_evidence"] == answer["claim_evidence"]
    store.close()


def test_failed_token_delivery_rolls_back_assignment_and_adjudication_retains_reasons(tmp_path):
    store, batch = setup_review(tmp_path)
    with pytest.raises(OSError):
        store.assign(batch, "one", deliver=lambda assignment, token: (_ for _ in ()).throw(OSError("synthetic delivery failure")))
    for identity, score in (("one", 1), ("two", 3)):
        assignment, token = store.assign(batch, identity)
        packet = store.packet(assignment, token)
        store.import_reviews(assignment, token, submission(packet, score))
    assignment, token = store.assign(batch, "three", role="adjudicator")
    packet = store.packet(assignment, token)
    assert len(packet["prior_assessments"][packet["cases"][0]["blind_id"]]) == 2
    assert all("reason" in row and "reviewer_id" not in row for values in packet["prior_assessments"].values() for row in values)
    payload = submission(packet)
    with pytest.raises(ValueError, match="adjudication rationale"):
        store.import_reviews(assignment, token, payload)
    payload["reviews"][0]["adjudication_rationale"] = "Synthetic resolution addresses the two different ratings."
    store.import_reviews(assignment, token, payload)
    assert store.report(batch)["adjudicated_cases"] == 1
    store.close()


def test_source_hashes_cannot_hide_pipeline_metadata(tmp_path):
    from research.data.review import ReviewStore

    store = ReviewStore(tmp_path / "review.sqlite3")
    with pytest.raises(ValueError, match="source identities"):
        store.create_batch([{"case_id": "fixture", "question": "Synthetic?", "answer": {"claims": []},
                             "source_hashes": {"model_B7_private": "a" * 64}}],
                           {"version": "fixture", "dimensions": ["accuracy"], "score_min": 0, "score_max": 4},
                           seed=1, source_version="synthetic", rights="local_review_authorized")
    store.close()


def test_adjudication_freezes_original_review_membership_and_submissions(tmp_path):
    store, batch = setup_review(tmp_path)
    for identity in ("one", "two"):
        assignment, token = store.assign(batch, identity)
        packet = store.packet(assignment, token)
        store.import_reviews(assignment, token, submission(packet))
    store.register_reviewer("late", qualification="Synthetic", specialty="test", independent=True)
    late_assignment, late_token = store.assign(batch, "late")
    late_packet = store.packet(late_assignment, late_token)
    adjudication, adjudication_token = store.assign(batch, "three", role="adjudicator")
    original_packet_hash = store.packet(adjudication, adjudication_token)["packet_sha256"]
    with pytest.raises(ValueError, match="frozen"):
        store.import_reviews(late_assignment, late_token, submission(late_packet, 0))
    store.register_reviewer("fourth", qualification="Synthetic", specialty="test", independent=True)
    with pytest.raises(ValueError, match="frozen"):
        store.assign(batch, "fourth")
    assert store.packet(adjudication, adjudication_token)["packet_sha256"] == original_packet_hash
    store.close()
