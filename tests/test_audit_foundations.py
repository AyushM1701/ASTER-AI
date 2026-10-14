import hashlib
import json

import pytest

from scripts.build_audit_foundations import (
    build_release,
    build_reviews,
    extract_sections,
    validate_document,
)


def document(tmp_path):
    raw = tmp_path / 'chapter.md'
    raw.write_text('# Hemostasis\n\nPlatelets form a plug at the site of vessel injury.\n\n## Common Pathway\n\nThen thrombin converts the insoluble fibrinogen into soluble fibrin.\n\n## Fibrinolysis\n\nPlasmin breaks down fibrin in the clot during vessel healing.\n\n# Review Questions\n\nWhat causes bleeding?\n', encoding='utf-8')
    rights = tmp_path / 'rights.md'
    rights.write_text('Publisher license: licensed under a Creative Commons Attribution-ShareAlike 4.0 International License, except where otherwise noted.\nCanonical license URL: https://creativecommons.org/licenses/by-sa/4.0/', encoding='utf-8')
    return dict(id='audit-test', title='Hemostasis', url='https://open.oregonstate.education/anatomy2e/chapter/hemostasis/', publisher='Oregon State University', jurisdiction='US', source_date='2025-09-01', retrieved_date='2026-10-09', edition='2025 second edition', authors=['OpenStax'], subjects=['physiology'], level='undergraduate_medical_foundation', license='CC-BY-SA-4.0', license_url='https://creativecommons.org/licenses/by-sa/4.0/', license_snapshot_path=str(rights), license_snapshot_sha256=hashlib.sha256(rights.read_bytes()).hexdigest(), raw_snapshot_path=str(raw), raw_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(), ai_reuse_restriction=False, approval='developer_reviewed', clinical_review=False, attribution='OpenStax, 2025', terms='Attribution and share-alike', scope='foundation', limitations=['Text education; no clinical or practical skill validation.'])


def test_suspect_fibrin_paragraph_excluded_with_audit_reason(tmp_path):
    doc = document(tmp_path)
    sections, excluded = extract_sections(tmp_path / 'chapter.md', doc)
    text = ' '.join(p for s in sections for p in s['paragraphs'])
    assert 'Platelets form' in text and 'Plasmin breaks down' in text
    assert 'insoluble fibrinogen' not in text
    assert 'What causes' not in text
    assert any(e['reason'] == 'source reverses fibrinogen/fibrin solubility' for e in excluded)


def test_partial_license_name_is_not_rights_evidence(tmp_path):
    doc = document(tmp_path)
    rights = tmp_path / 'rights.md'
    rights.write_text('Canonical license URL: https://creativecommons.org/licenses/by-sa/4.0/', encoding='utf-8')
    doc['license_snapshot_sha256'] = hashlib.sha256(rights.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match='Publisher license'):
        validate_document(doc, tmp_path)


def test_missing_provenance_or_ai_terms_rejected(tmp_path):
    doc = document(tmp_path)
    doc['authors'] = []
    with pytest.raises(ValueError, match='authors'):
        validate_document(doc, tmp_path)
    doc = document(tmp_path)
    doc['ai_reuse_restriction'] = True
    with pytest.raises(ValueError, match='AI'):
        validate_document(doc, tmp_path)


def test_release_has_hashes_exclusions_and_pending_review(tmp_path):
    out = tmp_path / 'component'
    manifest = build_release([document(tmp_path)], out, tmp_path)
    assert manifest['records'] > 0 and manifest['faculty_review'] == 'pending'
    for name, digest in manifest['files'].items():
        assert hashlib.sha256((out / name).read_bytes()).hexdigest() == digest
    metadata = json.loads((out / 'metadata.json').read_text())
    assert metadata['exclusions']
    assert metadata['sources']['audit-test']['authors'] == ['OpenStax']
    with pytest.raises(ValueError, match='exists'):
        build_release([document(tmp_path)], out, tmp_path)


def test_tables_objectives_caption_and_nul_corruption_fail_closed(tmp_path):
    doc = document(tmp_path)
    raw = tmp_path / 'chapter.md'
    raw.write_text('# Chapter\n\nBy the end of this section, you will be able to:\n\n- Identify bacteria\n\nHealthy flora occupy adhesion sites and compete with pathogens.\n\nFigure 1 – A micrograph.\n\n| organism | disease |\n|---|---|\n| S | D |', encoding='utf-8')
    sections, exclusions = extract_sections(raw, doc)
    assert all('Identify bacteria' not in p and 'micrograph' not in p and '| S |' not in p for s in sections for p in s['paragraphs'])
    raw.write_text('Damaged\x00paragraph', encoding='utf-8')
    with pytest.raises(ValueError, match='Corrupt'):
        extract_sections(raw, doc)


def test_dopamine_channel_error_and_emergency_transfusion_are_excluded(tmp_path):
    doc = document(tmp_path)
    path = tmp_path/'chapter.md'
    path.write_text('# Membrane proteins\n\nMany integral proteins have transport or recognition functions.\n\nWhen a dopamine molecule binds to a dopamine receptor protein, a channel within the transmembrane protein opens.\n\n# ABO Transfusion Protocols\n\nA patient with type AB blood can receive any type of blood.\n', encoding='utf-8')
    sections, exclusions = extract_sections(path, doc)
    text = ' '.join(p for s in sections for p in s['paragraphs'])
    assert 'Many integral proteins' in text
    assert 'dopamine' not in text and 'any type of blood' not in text
    assert any('dopamine' in e['reason'] for e in exclusions)


def test_specialty_foundation_import_rejects_case_reports(tmp_path):
    raw = tmp_path/'case.xml'
    raw.write_text('<article article-type="case-report"><front/></article>')
    doc = {'id':'case','raw_snapshot_path':str(raw),'scope':'specialty_review'}
    with pytest.raises(ValueError, match='review article'):
        build_reviews([doc], tmp_path/'review-component', tmp_path)


def test_blood_group_source_errors_excluded_as_complete_paragraphs(tmp_path):
    doc = document(tmp_path)
    path = tmp_path/'chapter.md'
    path.write_text('# Rh Blood Groups\n\nOnly RhD is clinically important in the Rh blood group system.\n\nA donor is tested for Rh antibodies to determine the blood group.\n\nBoth ABO antigens are glycoproteins in the erythrocyte membrane.\n\nRed cells express different surface antigens according to blood group.\n', encoding='utf-8')
    sections, exclusions = extract_sections(path, doc)
    text = ' '.join(p for s in sections for p in s['paragraphs'])
    assert 'Red cells express' in text
    assert 'clinically important' not in text and 'tested for Rh antibodies' not in text and 'glycoproteins' not in text
    assert len(exclusions) == 3
