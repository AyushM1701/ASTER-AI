"""A parent tissue question must not silently become a subtype question."""
import pytest

from tests.test_teaching_precision import change, make_store


@pytest.mark.parametrize('question', ['What is epithelium?', 'Explain epithelium',
    'Define epithelial tissue', 'What are epithelia?', 'Please explain epithelium in simple terms for a patient.'])
def test_general_tissue_selects_general_heading(tmp_path, question):
    store = make_store(tmp_path)
    change(store, store.records[0], 'Epithelial Tissue',
           'Epithelial tissue covers surfaces and lines spaces.', ['histology'])
    change(store, store.records[1], 'Oral mucosa / Sulcular epithelium',
           'Sulcular epithelium lines the gingival sulcus.', ['epithelium'])
    result = store.answer(question)
    assert result is not None
    assert {r['section'] for r in result['citations']} == {'Epithelial Tissue'}


def test_specific_subtype_keeps_its_qualifier(tmp_path):
    store = make_store(tmp_path)
    change(store, store.records[0], 'Epithelial Tissue',
           'Epithelial tissue covers surfaces and lines spaces.', ['epithelium'])
    change(store, store.records[1], 'Oral mucosa / Sulcular epithelium',
           'Sulcular epithelium lines the gingival sulcus.', ['epithelium'])
    result = store.answer('What is sulcular epithelium?')
    assert result is not None
    assert {r['section'] for r in result['citations']} == {'Oral mucosa / Sulcular epithelium'}


def test_heading_match_preserves_context_and_separate_comparison_parts(tmp_path):
    store = make_store(tmp_path)
    change(store, store.records[0], 'Epithelium',
           'Epithelium covers surfaces and lines spaces.', ['epithelium'])
    change(store, store.records[1], 'Connective tissue',
           'Connective tissue supports other tissues.', ['connective tissue'])
    result = store.answer('Compare epithelium and connective tissue')
    assert {r['section'] for r in result['citations']} == {'Epithelium', 'Connective tissue'}
    assert store.answer('Explain epithelium in liver failure') is None


def test_general_heading_rule_applies_beyond_epithelium(tmp_path):
    store = make_store(tmp_path)
    change(store, store.records[0], 'Cartilage', 'Cartilage is described generally.', ['cartilage'])
    change(store, store.records[1], 'Elastic cartilage', 'Elastic cartilage is a specific tissue.', ['cartilage'])
    result = store.answer('What is cartilage?')
    assert {r['section'] for r in result['citations']} == {'Cartilage'}


def test_bounded_overview_cannot_replace_requested_example_subtype():
    from backend.app.services.teaching import TeachingStore
    unit = {'topics':['epithelium'], 'match_mode':'exact_topic',
            'text':'Epithelium includes stratified squamous epithelium and forms glands.'}
    assert TeachingStore._unit_matches(unit, 'epithelial tissue')
    assert not TeachingStore._unit_matches(unit, 'stratified squamous epithelium')
    assert not TeachingStore._unit_matches(unit, 'simple epithelium')
    assert not TeachingStore._unit_matches(unit, 'epithelium in cancer')


def test_simple_histology_qualifier_is_not_a_style_request():
    from backend.app.services.teaching import teaching_terms
    assert 'simple' in teaching_terms('simple cuboidal epithelium')
    assert 'simple' in teaching_terms('simple epithelial tissue')
    assert 'simple' not in teaching_terms('explain epithelium in simple terms')
