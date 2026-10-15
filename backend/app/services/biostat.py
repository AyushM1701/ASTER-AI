"""Deterministic, checked biostatistics calculations for study questions.

The model only maps a question to a calculation type and named inputs; every
input number must appear verbatim in the question (no invented values). The
arithmetic, formulas and stated assumptions come from this module.
"""
import math
import re
from statistics import NormalDist

from pydantic import BaseModel, Field

from backend.app.errors import SCOPE, envelope

CALC_WORDS = re.compile(r"\b(?:calculate|compute|find|work out|determine|what (?:is|are) the)\b", re.I)
NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


class CalculationRequest(BaseModel):
    calculation: str = Field(description="one of: diagnostic_2x2, odds_ratio_2x2, relative_risk_2x2, risk_difference_nnt, "
                                         "descriptive, kappa_2x2, chi_square_2x2, sample_size_two_proportions, "
                                         "sample_size_two_means, none")
    inputs: dict[str, float | list[float]] = Field(default_factory=dict)


SPEC = {
    "diagnostic_2x2": ("tp", "fn", "fp", "tn"),
    "odds_ratio_2x2": ("a", "b", "c", "d"),
    "relative_risk_2x2": ("a", "b", "c", "d"),
    "risk_difference_nnt": ("control_risk", "treatment_risk"),
    "descriptive": ("values",),
    "kappa_2x2": ("both_yes", "rater1_yes_rater2_no", "rater1_no_rater2_yes", "both_no"),
    "chi_square_2x2": ("a", "b", "c", "d"),
    "sample_size_two_proportions": ("p1", "p2", "alpha", "power"),
    "sample_size_two_means": ("difference", "sd", "alpha", "power"),
}
PROMPT = (
    "Map the statistics question to one calculation and its inputs. Use only numbers written in the question. "
    "Calculations and input names: diagnostic_2x2(tp, fn, fp, tn); odds_ratio_2x2(a=exposed cases, b=exposed non-cases or controls, "
    "c=unexposed cases, d=unexposed non-cases or controls); relative_risk_2x2(a=exposed events, b=exposed non-events, "
    "c=unexposed events, d=unexposed non-events); risk_difference_nnt(control_risk, treatment_risk as proportions or percentages); "
    "descriptive(values: list); kappa_2x2(both_yes, rater1_yes_rater2_no, rater1_no_rater2_yes, both_no); "
    "chi_square_2x2(a, b, c, d); sample_size_two_proportions(p1, p2, alpha, power); sample_size_two_means(difference, sd, alpha, power). "
    "If it is not one of these, calculation=none.")


def is_calculation(question):
    return bool(CALC_WORDS.search(question)) and len(NUMBER.findall(question)) >= 2


def _numbers_in(question):
    values = set()
    for token in NUMBER.findall(question):
        value = float(token)
        values.update({value, value / 100})
    return values


def validated(request, question):
    if request.calculation not in SPEC:
        return None
    allowed = _numbers_in(question)
    for name in SPEC[request.calculation]:
        if name not in request.inputs:
            if name in {"alpha", "power"}:
                continue
            return None
        values = request.inputs[name] if isinstance(request.inputs[name], list) else [request.inputs[name]]
        if not values or any(not any(math.isclose(v, a, rel_tol=1e-9, abs_tol=1e-9) for a in allowed) for v in values):
            return None
    return request


def _p(value):
    return value / 100 if value > 1 else value


def compute(request):
    x = request.inputs
    kind = request.calculation
    steps, assumptions = [], []
    if kind == "diagnostic_2x2":
        tp, fn, fp, tn = (float(x[k]) for k in SPEC[kind])
        sens, spec = tp / (tp + fn), tn / (tn + fp)
        ppv, npv = tp / (tp + fp), tn / (tn + fn)
        results = {"sensitivity": sens, "specificity": spec, "positive_predictive_value": ppv, "negative_predictive_value": npv,
                   "accuracy": (tp + tn) / (tp + fn + fp + tn)}
        steps = [f"Sensitivity = TP/(TP+FN) = {tp:g}/({tp:g}+{fn:g}) = {sens:.4f}",
                 f"Specificity = TN/(TN+FP) = {tn:g}/({tn:g}+{fp:g}) = {spec:.4f}",
                 f"PPV = TP/(TP+FP) = {ppv:.4f}; NPV = TN/(TN+FN) = {npv:.4f}"]
        assumptions = ["Predictive values depend on the prevalence in this sample and do not transfer to populations with different prevalence."]
    elif kind in {"odds_ratio_2x2", "relative_risk_2x2", "chi_square_2x2"}:
        a, b, c, d = (float(x[k]) for k in SPEC[kind])
        if kind == "odds_ratio_2x2":
            value = (a * d) / (b * c)
            se = math.sqrt(1 / a + 1 / b + 1 / c + 1 / d)
            low, high = math.exp(math.log(value) - 1.96 * se), math.exp(math.log(value) + 1.96 * se)
            results = {"odds_ratio": value, "ci95_low": low, "ci95_high": high}
            steps = [f"OR = (a×d)/(b×c) = ({a:g}×{d:g})/({b:g}×{c:g}) = {value:.4f}",
                     f"SE(ln OR) = √(1/a+1/b+1/c+1/d) = {se:.4f}; 95% CI = {low:.3f} to {high:.3f} (Woolf)"]
            assumptions = ["Woolf (log) confidence interval; requires no zero cells."]
        elif kind == "relative_risk_2x2":
            r1, r0 = a / (a + b), c / (c + d)
            value = r1 / r0
            se = math.sqrt(b / (a * (a + b)) + d / (c * (c + d)))
            low, high = math.exp(math.log(value) - 1.96 * se), math.exp(math.log(value) + 1.96 * se)
            results = {"risk_exposed": r1, "risk_unexposed": r0, "relative_risk": value, "ci95_low": low, "ci95_high": high}
            steps = [f"Risk exposed = a/(a+b) = {r1:.4f}; risk unexposed = c/(c+d) = {r0:.4f}", f"RR = {r1:.4f}/{r0:.4f} = {value:.4f}",
                     f"95% CI = {low:.3f} to {high:.3f} (log method)"]
            assumptions = ["Valid for cohort or trial designs where risks can be estimated directly."]
        else:
            n = a + b + c + d
            expected = [(a + b) * (a + c) / n, (a + b) * (b + d) / n, (c + d) * (a + c) / n, (c + d) * (b + d) / n]
            chi = sum((o - e) ** 2 / e for o, e in zip((a, b, c, d), expected, strict=True))
            p_value = math.erfc(math.sqrt(chi / 2))
            results = {"chi_square": chi, "df": 1, "p_value": p_value, "min_expected_count": min(expected)}
            steps = [f"Expected counts = {', '.join(f'{e:.2f}' for e in expected)}", f"χ² = Σ(O−E)²/E = {chi:.4f}, df = 1, p = {p_value:.4g}"]
            assumptions = ["Pearson chi-square without continuity correction.",
                           "Use Fisher's exact test if any expected count is below 5."]
    elif kind == "risk_difference_nnt":
        control, treated = _p(float(x["control_risk"])), _p(float(x["treatment_risk"]))
        arr = control - treated
        results = {"absolute_risk_reduction": arr, "relative_risk_reduction": arr / control if control else float("nan"),
                   "number_needed_to_treat": (1 / arr) if arr else float("inf")}
        steps = [f"ARR = control risk − treatment risk = {control:.4f} − {treated:.4f} = {arr:.4f}",
                 f"NNT = 1/ARR = {results['number_needed_to_treat']:.2f} (round up to {math.ceil(results['number_needed_to_treat']) if arr > 0 else '—'})"]
        assumptions = ["Risks are for the same outcome over the same follow-up period."]
    elif kind == "descriptive":
        values = [float(v) for v in x["values"]]
        n = len(values)
        mean = sum(values) / n
        sd = math.sqrt(sum((v - mean) ** 2 for v in values) / (n - 1)) if n > 1 else 0.0
        ordered = sorted(values)
        median = (ordered[(n - 1) // 2] + ordered[n // 2]) / 2
        results = {"n": n, "mean": mean, "sample_sd": sd, "median": median, "min": ordered[0], "max": ordered[-1]}
        steps = [f"Mean = Σx/n = {sum(values):g}/{n} = {mean:.4f}", f"Sample SD = √(Σ(x−mean)²/(n−1)) = {sd:.4f}", f"Median = {median:g}"]
        assumptions = ["Standard deviation uses the sample (n−1) denominator."]
    elif kind == "kappa_2x2":
        a, b, c, d = (float(x[k]) for k in SPEC[kind])
        n = a + b + c + d
        po = (a + d) / n
        pe = ((a + b) * (a + c) + (c + d) * (b + d)) / n ** 2
        kappa = (po - pe) / (1 - pe)
        results = {"observed_agreement": po, "expected_agreement": pe, "kappa": kappa}
        steps = [f"Po = (a+d)/n = {po:.4f}", f"Pe = [(a+b)(a+c)+(c+d)(b+d)]/n² = {pe:.4f}", f"κ = (Po−Pe)/(1−Pe) = {kappa:.4f}"]
        assumptions = ["Cohen's kappa for two raters and two categories; depends on prevalence."]
    elif kind in {"sample_size_two_proportions", "sample_size_two_means"}:
        alpha = _p(float(x.get("alpha", 0.05)))
        power = _p(float(x.get("power", 0.8)))
        za, zb = NormalDist().inv_cdf(1 - alpha / 2), NormalDist().inv_cdf(power)
        if kind == "sample_size_two_proportions":
            p1, p2 = _p(float(x["p1"])), _p(float(x["p2"]))
            n = (za + zb) ** 2 * (p1 * (1 - p1) + p2 * (1 - p2)) / (p1 - p2) ** 2
            steps = [f"n per group = (Zα/2+Zβ)²[p1(1−p1)+p2(1−p2)]/(p1−p2)² = ({za:.3f}+{zb:.3f})²×{p1 * (1 - p1) + p2 * (1 - p2):.4f}/{(p1 - p2) ** 2:.4f}"]
        else:
            diff, sd = float(x["difference"]), float(x["sd"])
            n = 2 * (za + zb) ** 2 * sd ** 2 / diff ** 2
            steps = [f"n per group = 2(Zα/2+Zβ)²σ²/Δ² = 2×({za:.3f}+{zb:.3f})²×{sd:g}²/{diff:g}²"]
        results = {"n_per_group": n, "n_per_group_rounded_up": math.ceil(n), "alpha_two_sided": alpha, "power": power}
        assumptions = ["Two-sided test, equal group sizes, normal approximation; no allowance for dropout."]
        if "alpha" not in x or "power" not in x:
            assumptions.append("Alpha 0.05 and power 0.80 were assumed because the question did not state them.")
    else:
        return None
    return results, steps, assumptions


DIAGNOSTIC_LABELS = {
    "tp": r"true[\s-]*positives?|TP", "fn": r"false[\s-]*negatives?|FN",
    "fp": r"false[\s-]*positives?|FP", "tn": r"true[\s-]*negatives?|TN",
}


def labelled_diagnostic(question):
    """Read explicitly labelled TP/FN/FP/TN cells ("TP 90", "true positives = 90", "90 true positives")."""
    inputs = {}
    for key, label in DIAGNOSTIC_LABELS.items():
        found = {float(m.group(1) or m.group(2)) for m in re.finditer(
            rf"(?:\b(?:{label})\b\s*(?:[:=]|\bof\b|\bwere\b|\bwas\b|\bare\b|\bis\b)?\s*(\d+(?:\.\d+)?))|"
            rf"(?:\b(\d+(?:\.\d+)?)\s+(?:{label})\b)", question, re.I)}
        if len(found) != 1:
            return None
        inputs[key] = found.pop()
    return CalculationRequest(calculation="diagnostic_2x2", inputs=inputs)


DESCRIPTIVE_WORDS = re.compile(r"\b(?:mean|average|median|standard deviation|sd|variance)\b", re.I)
VALUE_LIST = re.compile(r"(-?\d+(?:\.\d+)?(?:\s*(?:,|;|\band\b)\s*-?\d+(?:\.\d+)?){2,})")


def listed_values(question):
    """A single explicit list of three or more values ("4, 8, 6, 5, 3 and 7") with mean/median/SD wording."""
    if not DESCRIPTIVE_WORDS.search(question):
        return None
    lists = VALUE_LIST.findall(question)
    if len(lists) != 1:
        return None
    values = [float(v) for v in NUMBER.findall(lists[0])]
    return CalculationRequest(calculation="descriptive", inputs={"values": values})


def answer(question, ollama, settings, compute_gate):
    from backend.app.errors import AppError

    # Unambiguous inputs (labelled cells, one explicit value list) need no model;
    # otherwise the model maps names to numbers and every number is checked against the question.
    request = labelled_diagnostic(question) or listed_values(question)
    if request is None:
        try:
            with compute_gate.enter():
                request = ollama.complete(settings.text_model, [
                    {"role": "system", "content": PROMPT}, {"role": "user", "content": question[:1500]}], CalculationRequest, tokens=200)
        except AppError:
            return None
    request = validated(request, question)
    if request is None:
        return None
    computed = compute(request)
    if computed is None:
        return None
    results, steps, assumptions = computed
    shown = {k: (round(v, 4) if isinstance(v, float) and math.isfinite(v) else v) for k, v in results.items()}
    return envelope(
        "ok", "medical_education", "Calculation", answer_method="deterministic_calculation",
        calculation={"type": request.calculation, "inputs": request.inputs, "results": shown, "steps": steps,
                     "assumptions": assumptions},
        answer="\n".join(steps), limitations=[SCOPE, "Inputs were read from your question; check that each number was assigned "
                                                      "to the right cell or group before using the result."],
        warnings=["Calculated by Aster's checked formulas, not by the language model."],
    )
