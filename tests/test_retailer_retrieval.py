import json

import yaml

from backend.app.config import Settings
from backend.app.services.retrieval import Reference, ReferenceStore

ATTESTATION = {
    "type": "user_attested",
    "user_statement": "it is verified and has the license, use it for aster's clinical library",
    "dataset_ref": "drowsyng/medicines-dataset",
    "snapshot_sha256": "a" * 64,
    "approved_host": "www.netmeds.com",
    "asserted_verification": True,
    "asserted_license": True,
    "clinical_review": False,
}


def retailer(name="Sample 20mg Tablet", strength="20mg", **overrides):
    return Reference(
        **{
            "source_id": name.replace(" ", "-"),
            "title": name,
            "publisher": "Netmeds via Kaggle (secondary retailer monograph)",
            "url": "https://www.netmeds.com/prescriptions/" + name.replace(" ", "-"),
            "jurisdiction": "India",
            "section": "Uses",
            "retrieved_date": "2026-10-07",
            "snapshot_id": "retailer-test",
            "text": "The retailer describes the named medicine's general educational purpose.",
            "topics": [name],
            "keywords": ["uses", "purpose"],
            "source_type": "retailer_monograph",
            "entity": name,
            "aliases": [name],
            "formulations": ["tablet"],
            "strengths": [strength],
            "routes": ["oral"],
            "products": [
                {
                    "brand": name,
                    "formulation": "tablet",
                    "match_strengths": [strength],
                    "route": "oral",
                }
            ],
            "permission_basis": ATTESTATION,
            **overrides,
        }
    )


def store_for(tmp_path, records, attestation=ATTESTATION):
    path = tmp_path / "records.jsonl"
    path.write_text("\n".join(record.model_dump_json() for record in records), encoding="utf-8")
    sources = {}
    for record in records:
        sources.setdefault(
            record.source_id,
            {
                "source_id": record.source_id,
                "url": record.url,
                "approval": "user_attested",
                "terms": "User attests verification and permission; secondary retailer material.",
                "permission_basis": attestation,
                "raw_sha256": "a" * 64,
                "record_checksums": [],
            },
        )["record_checksums"].append(record.content_hash())
    register = tmp_path / "sources.yaml"
    register.write_text(yaml.safe_dump({"sources": list(sources.values())}), encoding="utf-8")
    return ReferenceStore(Settings(corpus_path=path, source_register=register))


def test_user_attested_source_is_explicitly_admitted_and_citation_is_labelled(tmp_path):
    store = store_for(tmp_path, [retailer()])
    assert store.error is None
    found = store.search("What is Sample 20mg Tablet used for?")
    assert found and found[0].source_type == "retailer_monograph"
    assert found[0].citation()["permission_basis"]["type"] == "user_attested"
    assert found[0].citation()["clinical_review"] is False


def test_attestation_cannot_approve_a_different_host_or_snapshot(tmp_path):
    bad = dict(ATTESTATION, approved_host="evil.example")
    assert store_for(tmp_path, [retailer()], bad).error
    bad = dict(ATTESTATION, snapshot_sha256="b" * 64)
    assert store_for(tmp_path, [retailer()], bad).error


def test_retailer_strength_route_and_variant_mismatches_abstain(tmp_path):
    store = store_for(tmp_path, [retailer()])
    assert store.error is None
    for question in (
        "Sample 20mg Tablet 40mg warnings",
        "Sample 20mg Tablet injection intravenously",
        "Sample 20mg Tablet 20mg/ml warnings",
        "Sample 20mg Tablet Plus warnings",
    ):
        assert store.search(question) == []


def test_identity_index_does_not_scan_every_retailer_record_on_each_query(tmp_path, monkeypatch):
    records = [retailer(f"Brand{i} 20mg Tablet") for i in range(200)]
    store = store_for(tmp_path, records)
    assert store.error is None
    import backend.app.services.retrieval as retrieval

    actual = retrieval.phrase_match
    calls = []

    def counted(phrase, text):
        calls.append(phrase)
        return actual(phrase, text)

    monkeypatch.setattr(retrieval, "phrase_match", counted)
    assert store.search("Brand199 20mg Tablet uses")
    assert len(calls) < 100, "Per-query medicine matching must use candidate identities"


def test_dense_subset_manifest_rejects_missing_required_vectors():
    from backend.app.adapters.embeddings import dense_records

    base = retailer(source_type="drug_label")
    secondary = retailer("Secondary 20mg Tablet")
    eligible = dense_records(
        [base, secondary], {"dense_excluded_source_types": ["retailer_monograph"]}
    )
    assert eligible == [base]
    import pytest

    with pytest.raises(ValueError):
        dense_records([base, secondary], {"dense_excluded_source_types": ["drug_label"]})


def test_attestation_does_not_change_legacy_reference_hash_payload():
    from tests.test_knowledge_v2 import note

    record = note()
    payload = json.loads(record.model_dump_json(exclude={"chunk_id"}))
    assert not payload.get("permission_basis")
    assert record.content_hash() == note().content_hash()


def test_shared_brand_alias_requires_a_compatible_product_variant(tmp_path):
    records = [
        retailer("Sample 20mg Tablet", aliases=["Sample"]),
        retailer("Sample 40mg Tablet", strength="40mg", aliases=["Sample"]),
    ]
    store = store_for(tmp_path, records)
    assert store.search("What is Sample used for?") == []
    found = store.search("Sample 20mg tablet uses")
    assert found and all(r.strengths == ["20mg"] for r in found)


def test_purpose_questions_retrieve_the_product_uses_section_first(tmp_path):
    identity = retailer(
        section="Product identity (CSV fields)",
        text="Sample 20mg Tablet is the exact product name. Its generic name is reported separately. It is used for education.",
    )
    uses = retailer(
        section="USES OF SAMPLE 20MG TABLET",
        text="The medicine's retailer page lists its purpose for a specific educational context.",
        keywords=["uses", "purpose"],
    )
    store = store_for(tmp_path, [identity, uses])
    assert store.search("What is Sample 20mg Tablet used for?")[0].section.startswith("USES OF")


def test_exact_pack_volume_is_identity_but_added_strength_is_checked(tmp_path):
    liquid = retailer(
        "Sample Shampoo 100ml",
        strength="",
        formulations=["shampoo"],
        strengths=[],
        routes=[],
        products=[
            {
                "brand": "Sample Shampoo",
                "formulation": "shampoo",
                "match_strengths": [],
                "route": "",
            }
        ],
        aliases=["Sample Shampoo", "Sample"],
    )
    store = store_for(tmp_path, [liquid])
    assert store.search("What is Sample Shampoo 100ml used for?")
    assert store.search("Sample Shampoo 100ml 20mg/ml warnings") == []
    assert store.search("Sample Shampoo 100ml as a soap") == []
    assert store.search("Sample Shampoo by the otic route") == []


def test_numeric_unit_words_are_checked_instead_of_ignored(tmp_path):
    store = store_for(tmp_path, [retailer(aliases=["Sample"])])
    for qualifier in ("40 milligrams", "5 micrograms", "5 ug", "5 gm"):
        assert store.search("Sample " + qualifier + " warnings") == []


def test_full_identity_form_words_are_not_reinterpreted_as_extra_requirements(tmp_path):
    product = retailer(
        "Sample ICE CREAM Flavour Nasal Spray Drops 10ml",
        formulations=["cream", "spray", "drops"],
        strengths=[],
        routes=["nasal"],
        products=[{"formulation": "", "route": "nasal", "match_strengths": []}],
    )
    store = store_for(tmp_path, [product])
    assert store.search("What is Sample ICE CREAM Flavour Nasal Spray Drops 10ml used for?")
    assert store.search("Sample ICE CREAM Flavour Nasal Spray Drops 10ml as a tablet") == []


def test_missing_product_interaction_section_does_not_return_purpose_notes(tmp_path):
    store = store_for(tmp_path, [retailer(section="USES OF SAMPLE", aliases=["Sample"])])
    assert store.search("What are Sample interactions?") == []
