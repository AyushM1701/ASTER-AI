import pytest

from scripts.evaluate_mbbs import (
    build_material_mapping,
    score_case,
    validate_cases,
    write_immutable,
)


def case():
    return {'id': 'renal', 'question': 'Explain filtration', 'expected_status': 'ok',
            'expected_source_ids': ['renal-book'], 'required_facts': [{'id': 'filter', 'any_of': ['filters fluid']}],
            'forbidden_contradictions': ['proteins always cross']}


def response(text='The glomerulus filters fluid. Large proteins remain in blood.', ids=None):
    ids = ['r1'] if ids is None else ids
    return {'status': 'ok', 'claims': [{'text': text, 'citation_ids': ids}],
            'citations': [{'chunk_id': key, 'source_id': 'renal-book'} for key in ids]}


RECORDS = {'r1': {'chunk_id': 'r1', 'source_id': 'renal-book',
                  'text': 'The glomerulus filters fluid. Large proteins remain in blood.'}}


def test_missing_facts_and_contradictions_fail_independently():
    result = score_case(case(), [], response('Proteins always cross.'), RECORDS)
    assert result['fact_completeness'] == 0
    assert result['missing_fact_ids'] == ['filter']
    assert result['contradictions'] == ['proteins always cross']
    assert result['reference_agreement_pass'] is False
    assert result['retrieval_source_hit'] is False


def test_empty_claims_and_citations_cannot_pass_supported_case():
    result = score_case(case(), [], {'status': 'ok', 'claims': [], 'citations': []}, RECORDS)
    assert result['claim_support_rate'] is None
    assert result['citation_integrity_pass'] is False
    assert result['reference_agreement_pass'] is False


def test_citation_id_alone_does_not_support_invented_claim():
    result = score_case(case(), [], response('The glomerulus filters fluid and cures cancer.'), RECORDS)
    assert result['fact_completeness'] == 1
    assert result['claim_support_rate'] == 0
    assert result['reference_agreement_pass'] is False


def test_validated_reviewed_unit_requires_exact_text_and_bound_citations():
    unit = {'text': 'Think of the glomerulus as a filter: it filters fluid.', 'citation_ids': ['r1']}
    result = score_case(case(), [{'source_id': 'renal-book'}], response(unit['text']), RECORDS, [unit])
    assert result['claim_support_rate'] == 1
    assert result['reference_agreement_pass'] is True
    assert score_case(case(), [], response(unit['text'] + ' It diagnoses you.'), RECORDS, [unit])['claim_support_rate'] == 0


def test_unknown_citations_and_absent_envelope_citations_fail():
    assert score_case(case(), [], response(ids=['unknown']), RECORDS)['citation_integrity_pass'] is False
    value = response()
    value['citations'] = []
    assert score_case(case(), [], value, RECORDS)['citation_integrity_pass'] is False


def test_unsupported_case_reports_nonapplicable_facts_without_vacuous_agreement():
    unsupported = dict(case(), expected_status='not_handled', expected_source_ids=[], required_facts=[])
    result = score_case(unsupported, [], None, RECORDS)
    assert result['status_pass'] is True
    assert result['fact_completeness'] is None
    assert result['reference_agreement_pass'] is None


def test_supported_dataset_requires_facts_and_unique_ids():
    with pytest.raises(ValueError, match='facts'):
        validate_cases([dict(case(), required_facts=[])])
    with pytest.raises(ValueError, match='Duplicate'):
        validate_cases([case(), case()])


def test_output_is_immutable(tmp_path):
    path = tmp_path / 'report.json'
    write_immutable(path, {'first': True})
    with pytest.raises(FileExistsError):
        write_immutable(path, {'first': False})


def test_material_mapping_keeps_manual_evidence_and_pending_review():
    class Store:
        version = 'fixture'
        records = list(RECORDS.values())

        def search(self, text, limit=5):
            return self.records

    value = dict(case(), reference_evidence=[{'chunk_id': 'r1', 'excerpt': RECORDS['r1']['text']}],
                 manual_material_associations=[{'competency_code': 'PY7.3', 'contribution_scope': 'Filtration only'}])
    competency = {'code': 'PY7.3', 'text': 'Describe filtration and reabsorption', 'subject': 'Physiology', 'page': 140, 'active': True}
    result = build_material_mapping(Store(), [value], [competency])
    association = result['competencies'][0]
    assert association['status'] == 'related_material_pending_review'
    assert association['manual_associations'][0]['review_type'] == 'developer_material_mapping'
    assert association['manual_associations'][0]['evidence_excerpt'] == RECORDS['r1']['text']
    assert association['faculty_review']['decision'] is None
    assert result['clinical_correctness'] is None


def test_manual_mapping_rejects_unread_or_changed_evidence():
    class Store:
        version = 'fixture'
        records = list(RECORDS.values())

        def search(self, text, limit=5):
            return self.records

    value = dict(case(), reference_evidence=[{'chunk_id': 'r1', 'excerpt': 'Invented material'}],
                 manual_material_associations=[{'competency_code': 'PY7.3', 'contribution_scope': 'Filtration only'}])
    with pytest.raises(ValueError, match='evidence'):
        build_material_mapping(Store(), [value], [{'code': 'PY7.3', 'text': 'Filtration', 'subject': 'Physiology', 'page': 140, 'active': True}])
