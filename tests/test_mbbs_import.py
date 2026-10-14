import hashlib
import json

import pytest

from scripts.build_mbbs_library import (
    build_release,
    extract_markdown,
    split_context,
    validate_license,
)


def source(tmp_path):
    raw = tmp_path / 'chapter.md'
    raw.write_text('# Enzyme kinetics\n\nEnzymes speed reactions.\n\nThey do not change equilibrium.', encoding='utf-8')
    license_path = tmp_path / 'license.md'
    license_path.write_text('Licensed CC BY-NC-SA 4.0 https://creativecommons.org/licenses/by-nc-sa/4.0/', encoding='utf-8')
    return dict(id='test-chapter', title='Enzymes', url='https://pressbooks.lib.vt.edu/cellbio/chapter/test/', publisher='Virginia Tech', jurisdiction='US', source_date='2021-11-19', retrieved_date='2026-10-08', edition='2021 web edition', subjects=['biochemistry'], level='undergraduate_medical', license='CC-BY-NC-SA-4.0', license_url='https://creativecommons.org/licenses/by-nc-sa/4.0/', license_snapshot_path=str(license_path), license_snapshot_sha256=hashlib.sha256(license_path.read_bytes()).hexdigest(), raw_snapshot_path=str(raw), raw_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(), ai_reuse_restriction=False, approval='developer_reviewed', clinical_review=False, attribution='Renée LeClair, Virginia Tech, 2021', terms='Noncommercial; attribution; share alike; text extraction; figures omitted.')


def test_license_requires_exact_snapshot_and_no_ai_restriction(tmp_path):
    doc = source(tmp_path)
    validate_license(doc, root=tmp_path)
    doc['ai_reuse_restriction'] = True
    with pytest.raises(ValueError, match='AI'):
        validate_license(doc, root=tmp_path)


def test_license_unknown_or_changed_snapshot_fails(tmp_path):
    doc = source(tmp_path)
    doc['license'] = 'unknown'
    with pytest.raises(ValueError, match='license'):
        validate_license(doc, root=tmp_path)
    doc = source(tmp_path)
    doc['license_snapshot_sha256'] = '0' * 64
    with pytest.raises(ValueError, match='snapshot'):
        validate_license(doc, root=tmp_path)


def test_context_keeps_neighboring_negation_and_overlap():
    paragraphs = ['A' * 1800, 'This does not apply to all patients. ' + 'B' * 900, 'Except when contraindicated. ' + 'C' * 900, 'D' * 1000]
    chunks = split_context(paragraphs)
    assert all(len(c['text']) <= 4000 for c in chunks)
    assert any(paragraphs[1] in c['text'] and paragraphs[2] in c['text'] for c in chunks)
    for para in paragraphs:
        assert any(para in c['text'] for c in chunks)
    assert chunks[1]['paragraph_start'] < chunks[0]['paragraph_end']


def test_oversized_paragraph_is_rejected_not_truncated():
    with pytest.raises(ValueError, match='paragraph'):
        split_context(['A' * 4001])


def test_adjacent_context_that_cannot_fit_is_rejected():
    with pytest.raises(ValueError, match='Adjacent'):
        split_context(['A' * 2500, 'Except ' + 'B' * 2000])


def test_release_is_immutable_and_file_digests_match(tmp_path):
    output = tmp_path / 'releases' / 'test-v1'
    manifest = build_release([source(tmp_path)], output, root=tmp_path)
    for filename, digest in manifest['files'].items():
        assert hashlib.sha256((output / filename).read_bytes()).hexdigest() == digest
    row = json.loads((output / 'records.jsonl').read_text().splitlines()[0])
    assert row['source_type'] == 'teaching'
    assert 'do not change equilibrium' in row['text']
    assert not row['clinical_review']
    with pytest.raises(ValueError, match='exists'):
        build_release([source(tmp_path)], output, root=tmp_path)


def test_changed_raw_snapshot_rejected(tmp_path):
    doc = source(tmp_path)
    (tmp_path / 'chapter.md').write_text('changed', encoding='utf-8')
    with pytest.raises(ValueError, match='snapshot'):
        build_release([doc], tmp_path / 'release', root=tmp_path)


def test_corrupt_extractor_response_is_rejected(tmp_path):
    raw = tmp_path / 'corrupt.md'
    raw.write_text('# Publisher page\n\n' + '\ufffd' * 100, encoding='utf-8')
    with pytest.raises(ValueError, match='Corrupt'):
        extract_markdown(raw)


def test_parent_heading_context_and_exercise_exclusion(tmp_path):
    raw = tmp_path / 'cdc.md'
    raw.write_text('# Epidemiology\n\n## Distribution\n\nTextbox module not selected or not found.\n\nDisease frequency needs a denominator.\n\n### Exercise 1.1\n\nRecommend this antibiotic.\n\n## Determinants\n\nRisk factors do not establish causation.', encoding='utf-8')
    sections = extract_markdown(raw)
    assert sections[0]['title'] == 'Epidemiology / Distribution'
    assert sections[0]['paragraphs'] == ['Disease frequency needs a denominator.']
    assert all('antibiotic' not in ' '.join(s['paragraphs']) for s in sections)


def test_reviewed_pdf_units_are_bound_to_source_spans(tmp_path):
    doc = source(tmp_path)
    doc['reviewed_units'] = [{'title': 'Manual unit', 'start': 0, 'end': 15,
                             'sha256': '0' * 64, 'complete_paragraph': True,
                             'pdf_pages': [1]}]
    with pytest.raises(ValueError, match='Reviewed unit'):
        build_release([doc], tmp_path / 'release', root=tmp_path)
