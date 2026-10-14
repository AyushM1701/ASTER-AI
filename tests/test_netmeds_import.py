"""Source-boundary, identity and exclusion contracts for the retail CSV importer."""

import csv
import importlib.util
import json
from pathlib import Path


def load_importer():
    path = Path(__file__).resolve().parents[1] / "scripts/import_netmeds_medicines.py"
    assert path.exists(), "The Netmeds source-preserving importer has not been implemented"
    spec = importlib.util.spec_from_file_location("netmeds_importer", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def row(name="Example 25mg Tablet 10'S", content="", generic="Generic Name  Exampleine 25 mg"):
    return {
        "med_name": name,
        "med_url": "https://www.netmeds.com/prescriptions/example-25mg-tablet-10-s",
        "drug_content": content,
        "generic_name": generic,
        "drug_manufacturer": "Example Ltd",
        "prescription_required": "Prescription required",
        "disease_name": "Example category",
    }


def test_source_sections_keep_negations_but_exclude_directions_and_faqs():
    importer = load_importer()
    content = (
        "INTRODUCTION ABOUT EXAMPLE 25MG TABLETEXAMPLE 25MG TABLET is not recommended "
        "during pregnancy unless clearly necessary. "
        "USES OF EXAMPLE 25MG TABLET Used for an example condition. "
        "DIRECTIONS FOR USETake two tablets daily. "
        "WARNING & PRECAUTIONSPREGNANCYDo not take this medicine unless your doctor advises it. "
        "BREASTFEEDINGThis medicine is not recommended while breastfeeding. "
        "FAQs ABOUT EXAMPLE 25MG TABLETHow much should I take? Take two tablets. "
        "AUTHOR DETAILS Reviewed By Dr. Example Last updated on 20 Dec 2022 | 05:49 PM(IST)"
    )
    documents, audit = importer.import_rows([row(content=content)], "abc123", "I authorize it")
    doc = documents[0]
    texts = " ".join(s["text"] for s in doc["sections"])
    assert "is not recommended during pregnancy unless clearly necessary." in texts
    assert "Do not take this medicine unless your doctor advises it." in texts
    assert "Take two tablets" not in texts
    assert "Reviewed By Dr." not in texts
    assert doc["source_date"] == "2022-12-20"
    assert doc["clinical_review"] is False
    assert doc["permission_basis"]["user_statement"] == "I authorize it"
    assert doc["permission_basis"]["snapshot_sha256"] == "abc123"
    assert {x["reason"] for x in audit["excluded_sections"]} >= {
        "direct_directions_or_self_treatment", "author_metadata_not_clinical_approval"
    }


def test_alias_is_heading_verified_and_route_is_not_guessed_from_tablet():
    importer = load_importer()
    documents, _ = importer.import_rows(
        [row(content="INTRODUCTION ABOUT EXAMPLE 25MG TABLETEXAMPLE 25MG TABLET contains exampleine.")],
        "hash", "permission",
    )
    doc = documents[0]
    assert doc["entity"] == "Example 25mg Tablet 10'S"
    assert doc["aliases"] == ["EXAMPLE 25MG TABLET", "EXAMPLE 25MG"]
    assert "exampleine" not in doc["aliases"]
    assert doc["formulations"] == ["tablet"]
    assert doc["strengths"] == ["25mg"]
    assert doc["routes"] == []
    assert doc["products"][0]["route"] == ""


def test_missing_description_and_generic_still_have_identity_without_inference():
    importer = load_importer()
    documents, audit = importer.import_rows([row(content="", generic="")], "hash", "permission")
    doc = documents[0]
    assert len(doc["sections"]) == 1
    assert doc["aliases"] == []
    assert "Generic name: not provided in the CSV" in doc["sections"][0]["text"]
    assert "Description: not provided in the CSV" in doc["sections"][0]["text"]
    assert audit["counts"]["missing_description"] == 1
    assert audit["counts"]["missing_generic"] == 1


def test_product_pack_quantity_is_not_a_strength_and_explicit_eye_route_is_preserved():
    importer = load_importer()
    documents, _ = importer.import_rows(
        [row(name="Example Eye Drops 5ml", content="")], "hash", "permission"
    )
    doc = documents[0]
    assert doc["strengths"] == []
    assert doc["formulations"] == ["drops"]
    assert doc["routes"] == ["ophthalmic"]
    assert doc["aliases"] == []


def test_long_warning_chunks_preserve_complete_sentences_with_context_and_source_spans():
    importer = load_importer()
    sentences = [f"Do not take this medicine during condition {i} unless your doctor advises it." for i in range(30)]
    content = "WARNING & PRECAUTIONSPREGNANCY" + " ".join(sentences)
    documents, audit = importer.import_rows([row(content=content)], "hash", "permission", max_chars=500)
    sections = [s for s in documents[0]["sections"] if s["title"].startswith("WARNING")]
    assert len(sections) > 1
    normalized = importer.normalize_source(content)
    for sentence in sentences:
        assert any(sentence in s["text"] for s in sections)
    for section in sections:
        assert 10 <= len(section["text"]) <= 500
        assert "PREGNANCY" in section["text"]
        assert "Do not" in section["text"]
        assert section["text"] == " ".join(normalized[a:b] for a, b in section["source_spans"])
    assert not audit["excluded_sections"]


def test_unsplittable_sentence_is_audited_in_full_instead_of_truncated():
    importer = load_importer()
    sentence = "Do not take " + "examplecondition " * 110 + "unless the doctor says so."
    documents, audit = importer.import_rows(
        [row(content="WARNING & PRECAUTIONSPREGNANCY" + sentence)], "hash", "permission", max_chars=500
    )
    assert len(documents[0]["sections"]) == 1
    assert audit["excluded_sections"][0]["reason"] == "unsplittable_qualified_unit_over_limit"
    assert audit["excluded_sections"][0]["end"] == len(importer.normalize_source("WARNING & PRECAUTIONSPREGNANCY" + sentence))


def test_nonstandard_prose_is_not_guessed_and_legacy_intro_is_preserved():
    importer = load_importer()
    examples = [row(content="PRODUCT DETAILS Ingredient exampleine Directions to use Take two."),
                row(name="Legacy Tablet 10'S", content="INTRODUCTIONLEGACY contains exampleine. USES OF LEGACY Used for a condition.")]
    examples[1]["med_url"] = "https://www.netmeds.com/prescriptions/legacy"
    documents, audit = importer.import_rows(examples, "hash", "permission")
    assert len(documents) == 2
    assert len(documents[0]["sections"]) == 1
    assert any("LEGACY contains exampleine." in s["text"] for s in documents[1]["sections"])
    assert documents[1]["aliases"] == []  # legacy prose has no independent product headline
    assert audit["excluded_sections"][0]["reason"] == "unrecognized_source_layout"


def test_rejects_duplicate_products_untrusted_urls_and_ambiguous_dates():
    importer = load_importer()
    valid = row(content="AUTHOR DETAILS Last updated on 01/02/2025")
    bad = row(name="Bad Tablet", content="")
    bad["med_url"] = "https://www.netmeds.com.evil.example/product"
    documents, audit = importer.import_rows([valid, valid, bad], "hash", "permission")
    assert len(documents) == 1
    assert documents[0]["source_date"] is None
    assert len(audit["rejected_rows"]) == 2
    assert {r["reason"] for r in audit["rejected_rows"]} == {"duplicate_product_identity", "unapproved_product_url"}
    assert any(w["code"] == "unparsed_source_date" for w in audit["warnings"])


def test_cli_writes_documents_and_independently_checkable_hash_audit(tmp_path):
    importer = load_importer()
    import hashlib
    source = tmp_path / "source.csv"
    fixture = row(content="INTRODUCTION ABOUT EXAMPLE 25MG TABLETEXAMPLE 25MG TABLET contains exampleine.")
    with source.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fixture))
        writer.writeheader()
        writer.writerow(fixture)
    output, audit_path = tmp_path / "documents.json", tmp_path / "audit.json"
    importer.main(["--csv", str(source), "--output", str(output), "--audit", str(audit_path),
                   "--user-statement", "I authorize it"])
    payload = json.loads(output.read_text(encoding="utf-8"))
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    assert len(payload["documents"]) == 1
    assert audit["snapshot_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert audit["documents_sha256"] == hashlib.sha256(output.read_bytes()).hexdigest()
    assert source.exists()


def test_all_excluded_long_warning_audits_its_header_as_well_as_body():
    importer = load_importer()
    text = "WARNING & PRECAUTIONSPREGNANCYDo not use " + "condition " * 100 + "unless prescribed."
    _, audit = importer.import_rows([row(content=text)], "hash", "permission", max_chars=500)
    exclusions = sorted((x["start"], x["end"]) for x in audit["excluded_sections"])
    assert exclusions[0][0] == 0
    assert max(end for _, end in exclusions) == len(text)


def test_duplicate_chunk_consolidation_preserves_all_equivalent_source_locations():
    importer = load_importer()
    sentence = "Do not take this medicine while pregnant unless a doctor advises it."
    text = "WARNING & PRECAUTIONSPREGNANCY" + " ".join([sentence] * 30)
    documents, _ = importer.import_rows([row(content=text)], "hash", "permission", max_chars=500)
    served = documents[0]["sections"][1:]
    assert any(s.get("equivalent_source_spans") for s in served)


def test_warning_subheading_does_not_split_a_verified_product_name():
    importer = load_importer()
    text = (
        "INTRODUCTION ABOUT EXAMPLE ALCOHOL FREE SOLUTIONEXAMPLE ALCOHOL FREE SOLUTION contains exampleine. "
        "WARNING & PRECAUTIONSPREGNANCYDo not take EXAMPLE ALCOHOL FREE SOLUTION unless your doctor advises it. "
        + " ".join(f"Use is not recommended in condition {i}." for i in range(35))
    )
    documents, _ = importer.import_rows([row(name="Example Alcohol Free Solution 60ml", content=text)],
                                         "hash", "permission", max_chars=500)
    warnings = [s for s in documents[0]["sections"] if s["title"].startswith("WARNING")]
    assert warnings
    assert all("PREGNANCY" in s["text"] for s in warnings)
    assert all("Do not take EXAMPLE ALCOHOL FREE SOLUTION unless your doctor advises it." in s["text"] for s in warnings)


def test_mixed_case_source_heading_and_verified_pack_free_prefix_support_dolo_without_guessing():
    importer = load_importer()
    content = "INTRODUCTION ABOUT DOLO 650MG TABLETDolo 650 Tablet is a fever and pain reducing medicine."
    documents, _ = importer.import_rows([row(name="Dolo 650 Tablet 15's", content=content)], "hash", "permission")
    doc = documents[0]
    assert {"DOLO 650MG TABLET", "Dolo 650 Tablet", "Dolo 650"} <= set(doc["aliases"])
    assert doc["strengths"] == ["650mg"]
    assert doc["routes"] == []
    assert doc["strength_evidence"] == "INTRODUCTION headline: DOLO 650MG TABLET"
    assert "Dolo 650 Tablet is a fever" in doc["sections"][1]["text"]


def test_verified_brand_alias_preserves_junior_suffix_and_does_not_relabel_expectorant_as_syrup():
    importer = load_importer()
    content = "INTRODUCTION ABOUT ASCORIL LS JUNIOR EXPECTORANTASCORIL LS JUNIOR EXPECTORANT is used in children."
    documents, _ = importer.import_rows([row(name="ASCORIL LS JUNIOR Expectorant 60ml", content=content)], "hash", "permission")
    doc = documents[0]
    assert "ASCORIL LS JUNIOR" in doc["aliases"]
    assert "ASCORIL LS" not in doc["aliases"]
    assert "Ascoril LS Syrup" not in doc["aliases"]
    assert doc["formulations"] == ["expectorant"]


def test_pack_removal_does_not_create_alias_when_source_only_describes_unrelated_brand():
    importer = load_importer()
    documents, _ = importer.import_rows([row(name="Dolo 650 Tablet 15's", content="PRODUCT DETAILS Generic paracetamol 650mg")], "hash", "permission")
    assert documents[0]["aliases"] == []
    assert documents[0]["strengths"] == []
