"""Deterministic label-split checks; retrieval exposure is recorded separately."""

import hashlib
import re
from itertools import combinations


def normalize_article(identity):
    return re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:)", "", identity.strip().casefold()).strip()


def normalized_text(value):
    return " ".join(re.findall(r"\w+", value.casefold()))


def ngrams(text):
    words = normalized_text(text).split()
    return {tuple(words[index:index + 3]) for index in range(max(0, len(words) - 2))}


def audit_splits(rows, near_duplicate_threshold=0.85):
    if not 0 < near_duplicate_threshold <= 1:
        raise ValueError("similarity threshold must be in (0, 1]")
    ids = [row["id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate case identities")
    findings = []
    for left, right in combinations(rows, 2):
        if left["split"] == right["split"]:
            continue
        kinds = []
        articles_left = {normalize_article(value) for value in left.get("article_ids", [])}
        articles_right = {normalize_article(value) for value in right.get("article_ids", [])}
        if articles_left & articles_right:
            kinds.append("article_overlap")
        for field in ("family", "source_family", "rubric_hash", "passage_hash", "similarity_cluster"):
            if left.get(field) and left[field] == right.get(field):
                kinds.append(field + "_overlap")
        if left.get("augmentation_parent_id") == right["id"] or right.get("augmentation_parent_id") == left["id"] or (
            left.get("augmentation_parent_id") and left.get("augmentation_parent_id") == right.get("augmentation_parent_id")
        ):
            kinds.append("augmentation_parent_crossing")
        a, b = normalized_text(left.get("text", "")), normalized_text(right.get("text", ""))
        if a and a == b:
            kinds.append("exact_text_duplicate")
        else:
            grams_left, grams_right = ngrams(a), ngrams(b)
            union = grams_left | grams_right
            if union and len(grams_left & grams_right) / len(union) >= near_duplicate_threshold:
                kinds.append("near_text_duplicate")
        findings.extend({"left_id": left["id"], "right_id": right["id"], "kind": kind} for kind in kinds)
    return {
        "rows": len(rows), "findings": findings, "split_integrity_passed": not findings,
        "row_hashes": {row["id"]: hashlib.sha256(normalized_text(row.get("text", "")).encode()).hexdigest() for row in rows},
        "near_duplicate_method": "word-trigram Jaccard; embeddings/MinHash not run",
        "public_pretraining_contamination": "unknown",
        "retrieval_exposure_is_separate": True,
    }
