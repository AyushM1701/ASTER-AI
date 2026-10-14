"""Offline metrics with explicit label denominators and undefined outcomes."""

import math
import random
from statistics import mean


def retrieval_metrics(cases, k=10):
    if k < 1:
        raise ValueError("positive retrieval budget required")
    rows = []
    for case in cases:
        if "gold" not in case or case["gold"] is None:
            continue
        ranked = list(dict.fromkeys(case.get("ranked", [])))[:k]
        gold = case["gold"]
        positives = {identity for identity, grade in gold.items() if grade > 0}
        hits = sum(identity in positives for identity in ranked)
        grades = [gold.get(identity, 0) for identity in ranked]
        dcg = sum((2**grade - 1) / math.log2(index + 2) for index, grade in enumerate(grades))
        ideal = sum((2**grade - 1) / math.log2(index + 2) for index, grade in enumerate(sorted(gold.values(), reverse=True)[:k]))
        facets = case.get("facet_gold")
        supported = [bool(set(ids) & set(ranked)) for ids in facets.values()] if facets else None
        rows.append({
            "precision_at_k": hits / k, "recall_at_k": hits / len(positives) if positives else None,
            "mrr": next((1 / (index + 1) for index, identity in enumerate(ranked) if identity in positives), 0),
            "ndcg_at_k": dcg / ideal if ideal else None,
            "facet_coverage": mean(supported) if supported else None,
            "all_essential_facets": float(all(supported)) if supported else None,
        })
    names = ["precision_at_k", "recall_at_k", "mrr", "ndcg_at_k", "facet_coverage", "all_essential_facets"]
    result = {name: mean(values) if (values := [row[name] for row in rows if row[name] is not None]) else None for name in names}
    result.update(cases=len(cases), labelled_cases=len(rows), k=k,
                  precision_denominator="fixed requested k per labelled case",
                  metric_denominators={name: sum(row[name] is not None for row in rows) for name in names})
    return result


def validate_probabilities(probabilities, labels):
    if len(probabilities) != len(labels) or not probabilities:
        raise ValueError("nonempty aligned probabilities and observed labels required")
    if any(not math.isfinite(p) or not 0 <= p <= 1 for p in probabilities) or any(label not in {0, 1} for label in labels):
        raise ValueError("finite probabilities and binary event labels required")


def calibration_metrics(probabilities, labels, *, event, bins=10):
    validate_probabilities(probabilities, labels)
    if not event.strip() or bins < 1:
        raise ValueError("defined event and positive bin count required")
    ece, diagram = 0, []
    for index in range(bins):
        members = [j for j, p in enumerate(probabilities) if min(bins - 1, int(p * bins)) == index]
        if not members:
            continue
        confidence = mean(probabilities[j] for j in members)
        outcome = mean(labels[j] for j in members)
        ece += len(members) / len(labels) * abs(confidence - outcome)
        diagram.append({"bin": index, "n": len(members), "confidence": confidence, "observed": outcome})
    return {"event": event, "n": len(labels), "prevalence": mean(labels), "bins": bins,
            "brier": mean((p - label) ** 2 for p, label in zip(probabilities, labels)),
            "ece": ece, "reliability_diagram": diagram, "clinical_review": "not_established_by_metric"}


def selective_metrics(probabilities, correct_labels, threshold):
    validate_probabilities(probabilities, correct_labels)
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be in [0, 1]")
    accepted = [correct for score, correct in zip(probabilities, correct_labels) if score >= threshold]
    return {"n": len(correct_labels), "accepted": len(accepted), "threshold": threshold,
            "coverage": len(accepted) / len(correct_labels),
            "selective_accuracy": mean(accepted) if accepted else None,
            "risk": 1 - mean(accepted) if accepted else None}


def grouped_bootstrap(groups, iterations=1000, seed=0):
    if not groups or iterations < 1 or any(not values for values in groups.values()):
        raise ValueError("nonempty labelled groups and positive iteration count required")
    rng = random.Random(seed)
    identities = sorted(groups)
    estimates = sorted(mean(value for identity in rng.choices(identities, k=len(identities)) for value in groups[identity]) for _ in range(iterations))
    return {"estimate": mean(value for values in groups.values() for value in values),
            "ci95": [estimates[int(0.025 * (iterations - 1))], estimates[int(0.975 * (iterations - 1))]],
            "groups": len(groups), "iterations": iterations, "seed": seed,
            "method": "whole-group percentile bootstrap; dependence retained within groups"}
