from pathlib import Path

import pytest


def test_inventory_preserves_every_table_entry_and_specialty():
    from research.data.source_inventory import build_inventory

    raw = Path("docs/implementation/inputs/ASTER_Complete_Medical_Dental_Source_Inventory_2026.md").read_text(encoding="utf-8")
    registry = build_inventory(raw)
    assert len(registry["specialties"]) == 9
    assert len(registry["entries"]) > 100
    assert any("DENTEX" in e["name"] and e["source_class"] == "imaging_dataset" for e in registry["entries"])
    assert any("DailyMed" in e["name"] and e["source_class"] == "drug_label_service" for e in registry["entries"])
    assert any("MeSH" in e["name"] and e["source_class"] == "terminology" for e in registry["entries"])
    assert any("glossary" in e["name"] and e["source_class"] == "terminology" for e in registry["entries"])
    assert any(e["source_class"] == "licensed_textbook" for e in registry["entries"])
    assert all(e["acquisition_state"] == "discovered" for e in registry["entries"])
    assert all(e["rights"]["rights_state"] == "unknown" for e in registry["entries"])


def test_read_or_api_rights_cannot_authorize_training_or_weights():
    from research.data.source_inventory import SourceItem

    item = SourceItem(source_id="test", source_class="patient_education", name="Test", source_url="https://example.com",
                      rights_state="verified", license_evidence_sha256="a" * 64,
                      allowed_actions=["read", "api_extract", "private_retrieval"])
    item.require_action("private_retrieval")
    for action in ("train", "redistribute_raw", "redistribute_weights", "commercial"):
        with pytest.raises(ValueError):
            item.require_action(action)


def test_imaging_and_benchmark_data_cannot_enter_educational_retrieval():
    from research.data.source_inventory import SourceItem

    for kind in ("imaging_dataset", "evaluation_dataset", "terminology", "curriculum"):
        item = SourceItem(source_id="test", source_class=kind, name="Test", source_url="https://example.com",
                          rights_state="verified", license_evidence_sha256="a" * 64,
                          allowed_actions=["private_retrieval"])
        with pytest.raises(ValueError):
            item.require_route("medical_explanation", "private_retrieval")
