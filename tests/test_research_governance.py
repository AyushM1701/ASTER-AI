import pytest


def test_unknown_counts_and_rights_cannot_become_training_permission():
    from research.data.governance import DatasetManifest

    manifest = DatasetManifest(name="proposed dental evidence", source_url="https://example.org")
    assert manifest.observed_count is None
    assert manifest.human_review_count is None
    with pytest.raises(ValueError, match="rights"):
        manifest.require_action("train")


def test_declared_counts_do_not_fill_observed_counts():
    from research.data.governance import DatasetManifest

    manifest = DatasetManifest(name="MedMCQA", source_url="https://example.org",
                               declared_counts={"train": 182822})
    assert manifest.observed_count is None
    assert manifest.observed_splits == {}


def test_shared_article_and_augmentation_parent_prevent_hidden_split_claim():
    from research.data.leakage import audit_splits

    rows = [
        {"id": "a", "split": "train", "article_ids": ["doi:10.1/example"], "text": "An original question", "family": "f1"},
        {"id": "b", "split": "test_hidden", "article_ids": ["https://doi.org/10.1/example"], "text": "A different wording", "family": "f2", "augmentation_parent_id": "a"},
    ]
    report = audit_splits(rows)
    assert not report["split_integrity_passed"]
    assert {finding["kind"] for finding in report["findings"]} >= {"article_overlap", "augmentation_parent_crossing"}
    assert report["public_pretraining_contamination"] == "unknown"


def test_opened_holdout_cannot_remain_unseen():
    from research.data.governance import HoldoutManifest

    manifest = HoldoutManifest(dataset_sha256="a" * 64, group_sha256="b" * 64)
    assert manifest.unseen
    manifest.record_exposure("development repair", "2026-10-13T00:00:00Z")
    assert not manifest.unseen
    assert manifest.status == "development_exposed"


def test_retrieval_document_availability_is_not_label_split_leakage():
    from research.data.leakage import audit_splits

    report = audit_splits([
        {"id": "a", "split": "train", "article_ids": ["PMC1"], "retrieval_article_ids": ["PMC2"], "text": "Distinct training question", "family": "f1"},
        {"id": "b", "split": "test_hidden", "article_ids": ["PMC2"], "text": "Independent testing item", "family": "f2"},
    ])
    assert report["split_integrity_passed"]


def test_article_whitespace_does_not_hide_source_overlap():
    from research.data.leakage import audit_splits

    report = audit_splits([
        {"id": "a", "split": "train", "article_ids": ["doi:10.1/example"], "text": "One original case"},
        {"id": "b", "split": "test_hidden", "article_ids": [" doi:10.1/example"], "text": "Another wording"},
    ])
    assert not report["split_integrity_passed"]
    assert report["findings"][0]["kind"] == "article_overlap"
