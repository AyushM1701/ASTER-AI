"""Deterministic biostatistics: formulas, rounding and refusal of invented inputs."""
import math

import pytest

from backend.app.services.biostat import CalculationRequest, compute, is_calculation, validated


def run(kind, question, **inputs):
    request = validated(CalculationRequest(calculation=kind, inputs=inputs), question)
    assert request is not None
    return compute(request)[0]


def test_diagnostic_accuracy():
    q = "Calculate sensitivity and specificity: TP 90, FN 10, FP 20, TN 180."
    r = run("diagnostic_2x2", q, tp=90, fn=10, fp=20, tn=180)
    assert r["sensitivity"] == pytest.approx(0.9) and r["specificity"] == pytest.approx(0.9)
    assert r["positive_predictive_value"] == pytest.approx(90 / 110)


def test_odds_ratio_with_ci():
    q = "Calculate the odds ratio when exposed cases are 40, exposed controls 20, unexposed cases 60, unexposed controls 80."
    r = run("odds_ratio_2x2", q, a=40, b=20, c=60, d=80)
    assert r["odds_ratio"] == pytest.approx(2.6667, rel=1e-4)
    assert r["ci95_low"] < r["odds_ratio"] < r["ci95_high"]


def test_descriptive_sample_sd():
    q = "Compute the mean and standard deviation of these values: 4, 8, 6, 5, 3, 7."
    r = run("descriptive", q, values=[4, 8, 6, 5, 3, 7])
    assert r["mean"] == pytest.approx(5.5) and r["sample_sd"] == pytest.approx(1.8708, rel=1e-4) and r["median"] == 5.5


def test_nnt_from_percentages():
    q = "Event rate is 20% with control and 15% with treatment. What are the absolute risk reduction and NNT?"
    r = run("risk_difference_nnt", q, control_risk=20, treatment_risk=15)
    assert r["absolute_risk_reduction"] == pytest.approx(0.05) and r["number_needed_to_treat"] == pytest.approx(20)


def test_kappa_and_chi_square():
    r = run("kappa_2x2", "kappa for 20 5 10 15", both_yes=20, rater1_yes_rater2_no=5, rater1_no_rater2_yes=10, both_no=15)
    assert r["kappa"] == pytest.approx(0.4)
    chi = run("chi_square_2x2", "chi square 20 5 10 15", a=20, b=5, c=10, d=15)
    assert chi["chi_square"] == pytest.approx(8.3333, rel=1e-3) and 0 < chi["p_value"] < 0.01


def test_sample_size_two_proportions():
    q = "Calculate sample size to detect 0.3 vs 0.5 with alpha 0.05 and power 0.8"
    r = run("sample_size_two_proportions", q, p1=0.3, p2=0.5, alpha=0.05, power=0.8)
    assert r["n_per_group_rounded_up"] == 91


def test_invented_numbers_are_refused():
    request = CalculationRequest(calculation="diagnostic_2x2", inputs={"tp": 90, "fn": 10, "fp": 20, "tn": 999})
    assert validated(request, "TP 90, FN 10, FP 20, TN 180") is None
    assert validated(CalculationRequest(calculation="none"), "x 1 2") is None


def test_calculation_detection():
    assert is_calculation("Calculate the odds ratio for 40, 20, 60 and 80")
    assert not is_calculation("What is an odds ratio?")
    assert math.isfinite(1.0)


@pytest.mark.parametrize("question", [
    "Calculate sensitivity and specificity: true positives 90, false negatives 10, false positives 20, true negatives 180.",
    "Calculate sensitivity and specificity from TP 90, FN 10, FP 20, TN 180",
    "What are the sensitivity and specificity if TP = 90, FN = 10, FP = 20 and TN = 180?",
    "A test gave 90 true positives, 10 false negatives, 20 false positives and 180 true negatives. Calculate sensitivity.",
])
def test_labelled_diagnostic_cells_need_no_model(question):
    from backend.app.services.biostat import answer

    class NoModel:
        def complete(self, *args, **kwargs):
            raise AssertionError("labelled cells must not call the model")

    result = answer(question, NoModel(), None, None)
    assert result["answer_method"] == "deterministic_calculation"
    assert result["calculation"]["inputs"] == {"tp": 90, "fn": 10, "fp": 20, "tn": 180}
    assert result["calculation"]["results"]["sensitivity"] == 0.9


def test_ambiguous_labels_fall_back_to_model():
    from backend.app.services.biostat import labelled_diagnostic

    assert labelled_diagnostic("Calculate: TP 90 or TP 95, FN 10, FP 20, TN 180") is None
    assert labelled_diagnostic("Calculate the odds ratio: 20, 80, 10, 90") is None


@pytest.mark.parametrize("question", [
    "Compute the mean and standard deviation of these values: 4, 8, 6, 5, 3, 7.",
    "What is the median of 4, 8, 6, 5, 3 and 7?",
])
def test_listed_values_need_no_model(question):
    from backend.app.services.biostat import answer

    class NoModel:
        def complete(self, *args, **kwargs):
            raise AssertionError("an explicit value list must not call the model")

    result = answer(question, NoModel(), None, None)
    assert result["calculation"]["inputs"]["values"] == [4, 8, 6, 5, 3, 7]
    assert result["calculation"]["results"]["mean"] == 5.5 and result["calculation"]["results"]["median"] == 5.5


def test_two_value_lists_are_left_to_the_model():
    from backend.app.services.biostat import listed_values

    assert listed_values("Compare the mean of 1, 2, 3 with the mean of 4, 5, 6") is None
    assert listed_values("What is the standard deviation used for?") is None
