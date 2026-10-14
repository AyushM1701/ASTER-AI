from scripts.evaluate_curricula import inspect_answer, validate_blueprint


def test_answer_handling_does_not_become_clinical_or_curriculum_accuracy():
    row = {"case_id": "one", "question": "Explain dental pulp", "text_assessable": True}
    answer = {"status": "ok", "claims": [{"text": "Pulp is connective tissue.", "citation_ids": ["c"]}],
              "citations": [{"chunk_id": "c", "excerpt": "Pulp is connective tissue."}]}
    report = inspect_answer(row, answer, {"c": "Pulp is connective tissue."}, [])
    assert report["handled"] is True
    assert report["all_emitted_claims_bound"] is True
    assert report["clinical_accuracy"] is None
    assert report["curriculum_completeness"] is None
    assert report["practical_performance"] is None


def test_changed_or_uncited_claim_fails_binding_even_if_status_ok():
    answer = {"status": "ok", "claims": [{"text": "Pulp is bone.", "citation_ids": ["c"]}],
              "citations": [{"chunk_id": "c", "excerpt": "Pulp is connective tissue."}]}
    report = inspect_answer({"question": "Explain pulp"}, answer, {"c": "Pulp is connective tissue."}, [])
    assert report["all_emitted_claims_bound"] is False
    assert report["clinical_accuracy"] is None


def test_duplicate_or_empty_curriculum_prompt_is_rejected():
    import pytest

    with pytest.raises(ValueError, match="Duplicate"):
        validate_blueprint([{"case_id": "same", "question": "Explain pulp"}] * 2)
    with pytest.raises(ValueError, match="question"):
        validate_blueprint([{"case_id": "one", "question": ""}])


def test_batched_evaluation_encodes_the_same_focused_queries_used_by_retrieval():
    import numpy as np

    from scripts.evaluate_curricula import PreparedDense

    class Model:
        def encode(self, texts, **kwargs):
            return np.tile(np.array([1.0, 0.0]), (len(texts), 1))

    class Original:
        client = None
        model = Model()
        dimension = 2
        vectors = np.array([[1.0, 0.0]])
        ids = ["source"]

        def scores(self, question, allowed):
            raise AssertionError("Focused query was not included in the batch")

    prepared = PreparedDense(Original(), ["Please explain osmosis in simple terms for a patient."])
    assert prepared.scores("osmosis", ["source"]) == {"source": 1.0}
