import pytest


def test_retrieval_scores_require_explicit_gold_and_keep_denominators():
    from research.evaluate.metrics import retrieval_metrics

    result = retrieval_metrics([{"ranked": ["wrong", "correct"], "gold": {"correct": 3},
                                 "facet_gold": {"definition": ["correct"], "mechanism": ["missing"]}}], k=2)
    assert result["precision_at_k"] == 0.5
    assert result["recall_at_k"] == 1
    assert result["mrr"] == 0.5
    assert result["facet_coverage"] == 0.5
    assert result["all_essential_facets"] == 0
    assert result["cases"] == 1


def test_no_labels_cannot_produce_attractive_retrieval_score():
    from research.evaluate.metrics import retrieval_metrics

    result = retrieval_metrics([{"ranked": ["anything"]}])
    assert result["recall_at_k"] is None
    assert result["labelled_cases"] == 0


def test_zero_accepted_selective_risk_is_undefined():
    from research.evaluate.metrics import selective_metrics

    result = selective_metrics([0.1, 0.2], [1, 0], threshold=0.9)
    assert result["coverage"] == 0
    assert result["risk"] is None


def test_calibration_is_for_defined_labelled_event():
    from research.evaluate.metrics import calibration_metrics

    result = calibration_metrics([0.8, 0.2], [1, 0], event="all essential facets supported")
    assert result["brier"] == pytest.approx(0.04)
    assert result["ece"] == pytest.approx(0.2)
    with pytest.raises(ValueError):
        calibration_metrics([0.8], [1], event="")


def test_grouped_bootstrap_is_reproducible():
    from research.evaluate.metrics import grouped_bootstrap

    groups = {"source-a": [0.1, 0.9], "source-b": [0.5]}
    assert grouped_bootstrap(groups, seed=7, iterations=100) == grouped_bootstrap(groups, seed=7, iterations=100)
