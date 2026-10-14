"""Secondary evidence remains visibly unverified and cannot bypass product gates."""

import hashlib
import importlib.util
import json
from pathlib import Path

from backend.app.config import Settings
from backend.app.errors import AppError
from backend.app.services.answers import AnswerService
from backend.app.services.retrieval import Reference


def secondary_module():
    path = Path(__file__).resolve().parents[1] / "backend/app/services/secondary_references.py"
    assert path.exists(), "Secondary reference service has not been implemented"
    spec = importlib.util.spec_from_file_location("secondary_references", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def note(section="Dataset-reported uses", text="Dataset-reported uses for Example 10mg Tablet: Example purpose."):
    record = Reference(
        source_id="secondary-example", title="Example 10mg Tablet — HF dataset",
        url="https://huggingface.co/datasets/dmedhi/indian-medicines",
        publisher="Hugging Face · dmedhi", jurisdiction="India", section=section,
        retrieved_date="2026-10-07", snapshot_id="test-secondary-v1", text=text,
        topics=["Example 10mg Tablet"], keywords=["example"],
        source_type="unverified_secondary", entity="Example 10mg Tablet", clinical_review=False,
        permission_basis={
            "type": "user_authorized_secondary", "dataset_ref": "dmedhi/indian-medicines",
            "snapshot_sha256": "a" * 64, "matched_netmeds_source_id": "netmeds-example",
            "matched_netmeds_product": "Example 10mg Tablet 10's",
            "review_status": "unverified", "source_rows": [1],
        },
    )
    record.chunk_id = record.stable_id()
    return record


def store(tmp_path, records=None):
    module = secondary_module()
    records = records or [note()]
    raw = "".join(r.model_dump_json() + "\n" for r in records).encode()
    (tmp_path / "records.jsonl").write_bytes(raw)
    manifest = {
        "library_version": "test-secondary-v1", "review_status": "unverified", "clinical_review": False,
        "authorization": {"type": "user_authorized_secondary", "user_statement": "use this as secondary data in the ai with a subtly caution of unverified data"},
        "records": len(records), "records_sha256": hashlib.sha256(raw).hexdigest(),
        "source_datasets": [{"dataset_ref": "dmedhi/indian-medicines", "snapshot_sha256": "a" * 64}],
    }
    encoded = json.dumps(manifest).encode()
    (tmp_path / "manifest.json").write_bytes(encoded)
    settings = Settings(enable_secondary_references=True, secondary_reference_path=tmp_path,
                        secondary_manifest_sha256=hashlib.sha256(encoded).hexdigest())
    return module.SecondaryReferenceStore(settings)


def anchor():
    record = note()
    record.source_id = "netmeds-example"
    record.source_type = "retailer_monograph"
    return record


def test_secondary_intent_uses_only_corresponding_source_fields(tmp_path):
    refs = store(tmp_path)
    assert refs.error is None
    found = refs.search("What is Example 10mg Tablet used for?", [anchor()])
    assert len(found) == 1 and found[0].source_type == "unverified_secondary"
    assert found[0].citation()["permission_basis"]["review_status"] == "unverified"
    assert refs.search("Example 10mg Tablet interactions", [anchor()]) == []
    assert refs.search("Example 10mg Tablet side effects", [anchor()]) == []
    assert refs.search("Example uses and warnings", [anchor()]) == []


def test_secondary_requires_one_validated_master_anchor(tmp_path):
    refs = store(tmp_path)
    assert refs.search("Example uses", []) == []
    other = anchor()
    other.source_id = "netmeds-other"
    assert refs.search("Example uses", [anchor(), other]) == []
    other.source_type = "drug_label"
    assert refs.search("Example uses", [other]) == []


def test_source_name_resolution_preserves_extra_strength_and_blocks_variant_aliases(tmp_path):
    refs = store(tmp_path)
    assert refs.resolve_question("What is Example 10mg Tablet used for?") == "What is Example 10mg Tablet 10's used for?"
    assert refs.resolve_question("Example 10mg Tablet 500mg uses") == "Example 10mg Tablet 10's 500mg uses"
    assert refs.resolve_question("Example 10mg Tablet Junior uses") is None
    assert refs.resolve_question("Exampl 10mg Tablet uses") is None
    second = note()
    second.permission_basis["matched_netmeds_source_id"] = "netmeds-second"
    second.chunk_id = second.stable_id()
    assert store(tmp_path, [note(), second]).resolve_question("Example 10mg Tablet uses") is None


def test_secondary_source_link_uses_real_primary_qualifier_gates(tmp_path):
    path = Path(__file__).resolve().parent / "test_retailer_retrieval.py"
    spec = importlib.util.spec_from_file_location("retailer_fixtures", path)
    fixtures = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixtures)
    primary_path, secondary_path = tmp_path / "primary", tmp_path / "secondary"
    primary_path.mkdir()
    secondary_path.mkdir()
    primary = fixtures.store_for(primary_path, [fixtures.retailer(
        name="Example 10mg Tablet 10's", strength="10mg", source_id="netmeds-example",
    )])
    refs = store(secondary_path)
    service = AnswerService(Settings(), primary, None, None, secondary=refs)
    result = service.answer("What is Example 10mg Tablet used for?")
    assert result["status"] == "ok"
    assert all(c["source_type"] == "unverified_secondary" for c in result["citations"])
    for question in ["Example 10mg Tablet 500mg uses", "Example 10mg Tablet Injection uses",
                     "Example 10mg Tablet IV uses", "Example 10mg Tablet Junior uses",
                     "Example 10mg Tablet SR uses", "Example 10mg Tablet interactions"]:
        assert service.answer(question)["status"] == "insufficient_evidence", question


def test_secondary_tampering_and_promoted_status_fail_closed(tmp_path):
    refs = store(tmp_path)
    assert refs.error is None
    with (tmp_path / "records.jsonl").open("a") as handle:
        handle.write("{}\n")
    broken = secondary_module().SecondaryReferenceStore(refs.settings)
    assert broken.records == [] and broken.error
    unverified = note()
    unverified.clinical_review = True
    broken = store(tmp_path, [unverified])
    assert broken.records == [] and broken.error


def test_secondary_does_not_allow_arbitrary_urls(tmp_path):
    wrong = note()
    wrong.url = "https://untrusted.example/medicine"
    wrong.chunk_id = wrong.stable_id()
    refs = store(tmp_path, [wrong])
    assert refs.records == [] and refs.error


class Primary:
    error = None

    def __init__(self, initial=None, anchors=None):
        self.initial = initial or []
        self.anchors = anchors or []

    def search(self, question, **kwargs):
        return self.anchors if kwargs.get("require_requested_section") is False else self.initial

    def catalogue_match(self, question):
        return None

    def has_known_topic(self, question):
        return True


def test_answers_expose_subtle_notice_and_unverified_citations(tmp_path):
    refs = store(tmp_path)
    service = AnswerService(Settings(), Primary(anchors=[anchor()]), None, None, secondary=refs)
    result = service.answer("What is Example 10mg Tablet used for?")
    assert result["status"] == "ok"
    assert result["warnings"] == ["Unverified secondary data · confirm with the product label."]
    assert result["evidence_tier"] == "secondary_unverified"
    assert result["citations"][0]["source_type"] == "unverified_secondary"
    assert result["claims"][0]["text"] == note().text


def test_secondary_cannot_bypass_personal_dosing_or_product_mismatch(tmp_path):
    refs = store(tmp_path)
    service = AnswerService(Settings(), Primary(), None, None, secondary=refs)
    assert service.answer("How many mg of Example should I take?")["status"] == "unsupported_input"
    assert service.answer("Example 500mg Tablet uses")["status"] == "insufficient_evidence"


def test_primary_stays_first_and_notice_tracks_only_served_sources(tmp_path):
    refs = store(tmp_path)
    primary = anchor()
    service = AnswerService(Settings(), Primary(initial=[primary]), None, None, secondary=refs)
    result = service.answer("Example 10mg Tablet uses")
    assert result["citations"][0]["source_type"] == "retailer_monograph"
    assert result["citations"][-1]["source_type"] == "unverified_secondary"
    assert result["evidence_tier"] == "mixed_with_unverified_secondary"
    assert any("Unverified secondary data" in warning for warning in result["warnings"])
    result = service.answer("Example 10mg Tablet interactions")
    assert not any("Unverified secondary data" in warning for warning in result["warnings"])


def test_model_cannot_remove_unverified_notice_or_rephrase_secondary(tmp_path):
    class Model:
        def generate(self, question, evidence):
            raise AppError(502, "error", "Generated text was unsupported")

    from backend.app.services.compute import ComputeGate

    refs = store(tmp_path)
    settings = Settings(answer_mode="ollama", strict_source_grounding=False)
    result = AnswerService(settings, Primary(anchors=[anchor()]), Model(), ComputeGate(settings), secondary=refs).answer("Example uses")
    assert result["status"] == "ok"
    assert result["answer_method"] == "extractive_secondary_fallback"
    assert result["claims"][0]["text"] == note().text
    assert result["warnings"] == ["Unverified secondary data · confirm with the product label."]


def test_builder_rechecks_fields_and_does_not_admit_flagged_links():
    from copy import deepcopy

    from scripts.build_secondary_library import eligible

    record = {
        "name_match_method": "pack_or_unit_normalized_name", "source_name": "Example 10mg Tablet",
        "candidate_count": 1, "source_composition_conflict": False, "source_compositions": ["A (10mg)"],
        "candidates": [{"netmeds_name": "Example 10mg Tablet 10's", "netmeds_reported_generic": "Generic Name A 10 mg",
                        "review_flags": [], "composition_comparisons": [{"status": "reported_fields_agree"}]}],
    }
    assert eligible(record)
    for key, value in [("name_match_method", "brand_variant_candidate"), ("candidate_count", 2), ("source_composition_conflict", True)]:
        bad = deepcopy(record)
        bad[key] = value
        assert not eligible(bad)
    bad = deepcopy(record)
    bad["candidates"][0]["netmeds_reported_generic"] = "A 100 mg"
    assert not eligible(bad), "Reported-field agreement must be recalculated"
    bad = deepcopy(record)
    bad["candidates"][0]["netmeds_name"] = "Example 10mg Syrup 10ml"
    assert not eligible(bad), "A cleared review flag cannot hide a form difference"
