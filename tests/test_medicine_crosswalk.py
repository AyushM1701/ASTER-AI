"""Contracts for offline dataset links; no clinical aliases are promoted."""

import importlib.util
from pathlib import Path


def matcher():
    path = Path(__file__).resolve().parents[1] / "scripts/match_medicine_datasets.py"
    assert path.exists(), "Offline crosswalk matcher is not implemented"
    spec = importlib.util.spec_from_file_location("medicine_crosswalk", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pack_normalization_keeps_strength_and_release_variants():
    m = matcher()
    assert m.product_key("Augmentin 625 DUO Tablet 10'S") == m.product_key("Augmentin 625 Duo Tablet")
    assert m.product_key("Example 500mg Capsule 10's") == m.product_key("Example 500 mg Capsule")
    assert m.product_key("Example 500mg Tablet") != m.product_key("Example 50mg Tablet")
    assert m.product_key("Example Tablet SR") != m.product_key("Example Tablet")
    assert m.brand_key("Ascoril LS Junior Syrup") != m.brand_key("Ascoril LS Syrup")
    assert m.product_key("Example 1.2Gm Injection 1's").startswith("example 1.2 gm injection")


def test_brand_candidates_preserve_form_disagreement():
    m = matcher()
    assert m.product_key("Ascoril LS Syrup") != m.product_key("Ascoril LS Expectorant 100ml")
    assert m.brand_key("Ascoril LS Syrup") == m.brand_key("Ascoril LS Expectorant 100ml")
    assert m.forms("Ascoril LS Drops") != m.forms("Ascoril LS Syrup")


def test_composition_comparison_preserves_concentration_and_subset():
    m = matcher()
    assert m.compare_composition("A (500mg) + B (28.5mg)", "Generic Name B 28.50 mg+A 500 mg") == "reported_fields_agree"
    assert m.compare_composition("A (30mg/5ml)", "Generic Name A 30 mg") == "same_ingredients_amount_or_basis_differs"
    assert m.compare_composition("A (30mg/5ml)", "A (30mg/ml)") == "same_ingredients_amount_or_basis_differs"
    assert m.compare_composition("A (500mg)", "A 500 mg+B 20 mg") == "source_subset_only"
    assert m.compare_composition("A (NA)", "A 2 mg") == "unavailable_or_unparsed"
    assert m.compare_composition("Vitamin B12 (500mcg)", "Vitamin B12 500 mcg") == "reported_fields_agree"
    assert m.compare_composition("A (2% w/w)", "A 2 %") == "same_ingredients_amount_or_basis_differs"
    assert m.compare_composition("A (5mg)", "A 5 mcg") == "same_ingredients_amount_or_basis_differs"
    assert m.compare_composition("A (500mg)", "B 500 mg") == "ingredient_strings_differ"


def test_missing_amount_or_unknown_extra_component_is_not_dropped():
    m = matcher()
    assert m.compare_composition("A (5mg) + mystery", "A 5 mg") == "unavailable_or_unparsed"
    assert m.compare_composition("", "A 5 mg") == "unavailable_or_unparsed"
    assert m.compare_composition("A 5 mg+A 10 mg", "A 15 mg") == "same_ingredients_amount_or_basis_differs"


def test_matching_returns_ambiguity_without_choosing_first_product():
    m = matcher()
    products = [
        {"row": 1, "name": "Example 10mg Tablet 10's", "aliases": ["EXAMPLE TABLET"], "generic": "A 10 mg"},
        {"row": 2, "name": "Example 20mg Tablet 10's", "aliases": ["EXAMPLE TABLET"], "generic": "A 20 mg"},
    ]
    index = m.MatchIndex(products)
    kind, ids = index.match("Example Tablet")
    assert kind == "source_text_alias"
    assert ids == [1, 2]
    kind, ids = index.match("Example 10mg Tablet")
    assert kind == "pack_or_unit_normalized_name"
    assert ids == [1]
    assert index.match("Unrelated Tablet") == ("unmatched", [])


def test_name_indexes_do_not_fuzzily_swap_brands_or_modified_release():
    m = matcher()
    index = m.MatchIndex([
        {"row": 1, "name": "Allegra 120mg Tablet 10's", "aliases": [], "generic": "A 120 mg"},
        {"row": 2, "name": "Example 10mg Tablet SR 10's", "aliases": [], "generic": "B 10 mg"},
    ])
    assert index.match("Allegra-M 120mg Tablet") == ("unmatched", [])
    assert index.match("Example 10mg Tablet") == ("unmatched", [])


def test_source_conflicts_and_multiple_targets_are_explicit_flags():
    m = matcher()
    flags = m.review_flags("Ascoril LS Syrup", "Ascoril LS Expectorant 100ml", True, 2)
    assert "source_composition_conflict" in flags
    assert "multiple_netmeds_candidates" in flags
    assert "dosage_form_differs" in flags
