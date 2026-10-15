import copy
import hashlib
import importlib
import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def dental():
    return importlib.import_module('scripts.build_mds_dental')


@pytest.fixture
def document(tmp_path, dental):
    raw = tmp_path / 'chapter.md'
    raw.write_text('# Enamel development\nURL: https://openoregon.pressbooks.pub/histologyandembryology/chapter/chapter-9-enamel-development/\n\n## Amelogenesis\n\nAmelogenesis forms enamel from ameloblasts during tooth development.\n\n## License\n\nHistology and Embryology for Dental Hygiene Copyright © 2020 by Laird C Sheldahl is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License, except where otherwise noted.\n\n## Share This Book\n', encoding='utf-8')
    rights = tmp_path / 'rights.md'
    rights.write_text('URL: https://openoregon.pressbooks.pub/histologyandembryology/front-matter/chapter-0-preface/\nHistology and Embryology for Dental Hygiene Copyright © 2020 by Laird C Sheldahl is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License.\nNoncommercial. Share Alike.\nhttps://creativecommons.org/licenses/by-nc-sa/4.0/', encoding='utf-8')
    terms = tmp_path / 'terms.md'
    terms.write_text('URL: https://pressbooks.com/app/uploads/TOS/20250123-02-PressbooksPlatformIndividualUserTermsofUse.html\nEbooks remain owned by their authors, use is in accordance with any license imposed on ebooks.', encoding='utf-8')
    return {'id': 'dental-test-9', 'title': 'Enamel development', 'url': 'https://openoregon.pressbooks.pub/histologyandembryology/chapter/chapter-9-enamel-development/', 'publisher': 'Open Oregon Educational Resources / Laird C Sheldahl', 'jurisdiction': 'US', 'source_date': '2020', 'retrieved_date': '2026-10-09', 'edition': '2020; publisher extraction 2026-10-09', 'license': 'CC-BY-NC-SA-4.0', 'license_url': 'https://creativecommons.org/licenses/by-nc-sa/4.0/', 'approval': 'developer_reviewed', 'clinical_review': False, 'ai_reuse_restriction': False, 'terms': 'Noncommercial educational retrieval; attribution and ShareAlike required.', 'attribution': 'Sheldahl, Laird C. Histology and Embryology for Dental Hygiene. 2020.', 'subjects': ['dental_histology'], 'level': 'dental hygiene foundations; partial MDS support', 'raw_snapshot_path': raw.name, 'raw_sha256': dental.sha256(raw), 'license_snapshot_path': rights.name, 'license_snapshot_sha256': dental.sha256(rights), 'terms_snapshot_path': terms.name, 'terms_snapshot_sha256': dental.sha256(terms), 'acquisition_method': 'publisher markdown extraction', 'limitations': ['No faculty review']}


def test_extraction_preserves_section_hierarchy_whole_paragraphs_and_excludes_figures(dental):
    text = '# Tooth tissues\nURL: https://openoregon.pressbooks.pub/histologyandembryology/chapter/example/\n\n## Dentin\n\nDentin is avascular, but it is not acellular.\n\nFigure 4.1: Image credit third-party copyright.\n\n### Pulp interface\n\nOdontoblast cell bodies border the pulp. Processes extend into dentinal tubules.\n\n![third party](https://example.com/a.png)\n\n## Chapter review questions\n\nIdentify the image.\n\n## License\n\nCopyright text.\n'
    sections, excluded = dental.extract_sections(text)
    assert [(s['title'], s['paragraphs']) for s in sections] == [('Tooth tissues / Dentin', ['Dentin is avascular, but it is not acellular.']), ('Tooth tissues / Dentin / Pulp interface', ['Odontoblast cell bodies border the pulp. Processes extend into dentinal tubules.'])]
    assert all(text[p['start']:p['end']] == p['text'] for s in sections for p in s['source_spans'])
    assert any(x['reason'] == 'figure_or_media' for x in excluded)


def test_dental_license_checks_all_snapshot_hashes_and_ai_terms(document, tmp_path, dental):
    dental.validate_document(document, tmp_path)
    (tmp_path / document['terms_snapshot_path']).write_text('The content may not be used for generative AI or large language model training.', encoding='utf-8')
    with pytest.raises(ValueError, match='terms snapshot hash mismatch'):
        dental.validate_document(document, tmp_path)
    document['terms_snapshot_sha256'] = dental.sha256(tmp_path / document['terms_snapshot_path'])
    with pytest.raises(ValueError, match='AI reuse restriction'):
        dental.validate_document(document, tmp_path)


@pytest.mark.parametrize('field,value', [('url', 'https://untrusted.example/book'), ('license', 'CC-BY-4.0'), ('clinical_review', True), ('ai_reuse_restriction', None), ('raw_snapshot_path', '../outside.md')])
def test_rejects_unverified_rights_hosts_review_and_paths(document, tmp_path, dental, field, value):
    document[field] = value
    with pytest.raises(ValueError):
        dental.validate_document(document, tmp_path)


def test_chunk_mappings_are_specific_not_blanket(dental):
    assert dental.syllabus_associations('Enamel development / Amelogenesis', 'Ameloblasts secrete enamel matrix.') == ['MDS-32']
    assert dental.syllabus_associations('Histology / Nervous tissue', 'Axons conduct impulses.') == ['MDS-12', 'MDS-15']
    assert dental.syllabus_associations('Dentin-pulp complex development / Dentinogenesis', 'Mineralization of dentin.') == ['MDS-19', 'MDS-33']


def test_internal_structure_does_not_match_nucleic_acid_substrings(dental):
    assert dental.syllabus_associations('Pharyngeal arches / Development of internal structures', 'The mouth and palate develop.') == []


def test_chapter_titles_and_outline_are_not_answer_evidence(dental):
    text = '# Enamel development – Histology and Embryology for Dental Hygiene\nURL: https://openoregon.pressbooks.pub/histologyandembryology/chapter/example/\n\nEnamel development – Histology and Embryology for Dental Hygiene\n\nAmelogenesis\n\n- Initiation\n- Apposition\n- Maturation\n\n## Amelogenesis\n\nAmeloblasts secrete enamel matrix.\n'
    sections, exclusions = dental.extract_sections(text)
    assert len(sections) == 1
    assert sections[0]['paragraphs'] == ['Ameloblasts secrete enamel matrix.']
    assert any(e['reason'] == 'chapter_outline' for e in exclusions)


def test_component_records_and_permission_metadata_are_immutable(document, tmp_path, dental):
    out = tmp_path / 'component-v1'
    manifest = dental.build_component([document], out, root=tmp_path)
    assert manifest['records'] == manifest['sources'] == 1
    record = json.loads((out / 'records.jsonl').read_text(encoding='utf-8').strip())
    meta = json.loads((out / 'metadata.json').read_text(encoding='utf-8'))
    source = yaml.safe_load((out / 'sources.yaml').read_text(encoding='utf-8'))['sources'][0]
    assert record['source_type'] == 'teaching'
    assert record['clinical_review'] is False
    assert record['topics'] == ['Enamel and amelogenesis']
    assert meta['chunks'][record['chunk_id']]['syllabus_ids'] == ['MDS-32']
    assert meta['chunks'][record['chunk_id']]['material_type'] == 'foundation'
    assert source['record_checksums']
    assert source['raw_sha256'] == record['permission_basis']['snapshot_sha256']
    before = (out / 'records.jsonl').read_bytes()
    with pytest.raises(ValueError, match='exists'):
        dental.build_component([document], out, root=tmp_path)
    assert (out / 'records.jsonl').read_bytes() == before


def test_component_refuses_duplicate_ids_and_no_text(document, tmp_path, dental):
    with pytest.raises(ValueError, match='Duplicate'):
        dental.build_component([document, copy.deepcopy(document)], tmp_path / 'duplicate', root=tmp_path)
    (tmp_path / document['raw_snapshot_path']).write_text('# Empty\nURL: ' + document['url'] + '\n\n## License\n\nHistology and Embryology for Dental Hygiene Copyright © 2020 by Laird C Sheldahl is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License.\n', encoding='utf-8')
    document['raw_sha256'] = dental.sha256(tmp_path / document['raw_snapshot_path'])
    with pytest.raises(ValueError, match='no usable'):
        dental.build_component([document], tmp_path / 'empty', root=tmp_path)


@pytest.mark.local  # needs licensed source packs that are not committed
def test_acquired_component_proves_license_checksums_and_exact_source_spans(dental):
    from backend.app.services.retrieval import Reference

    component = ROOT / 'data/references/mds/components/dental/mds-dental-v3-2026-10-09'
    config = json.loads((ROOT / 'configs/mds_dental_sources.json').read_text(encoding='utf-8'))
    docs = {d['id']: d for d in config['documents']}
    assert len(docs) == 11
    for d in docs.values():
        dental.validate_document(d)
    manifest = json.loads((component / 'manifest.json').read_text(encoding='utf-8'))
    for name, expected in manifest['files'].items():
        assert hashlib.sha256((component / name).read_bytes()).hexdigest() == expected
    meta = json.loads((component / 'metadata.json').read_text(encoding='utf-8'))
    sources = yaml.safe_load((component / 'sources.yaml').read_text(encoding='utf-8'))['sources']
    records = [Reference.model_validate_json(line) for line in (component / 'records.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(records) == manifest['records']
    assert not manifest['skipped_sections']
    source_checksums = {s['source_id']: set(s['record_checksums']) for s in sources}
    raw_texts = {sid: (ROOT / d['raw_snapshot_path']).read_text(encoding='utf-8') for sid, d in docs.items()}
    for record in records:
        assert record.chunk_id == record.stable_id()
        assert record.content_hash() in source_checksums[record.source_id]
        info = meta['chunks'][record.chunk_id]
        spans = [raw_texts[record.source_id][span['start']:span['end']] for span in info['source_spans']]
        assert '\n\n'.join(spans) == record.text
        for span, text in zip(info['source_spans'], spans):
            assert hashlib.sha256(text.encode('utf-8')).hexdigest() == span['sha256']
        assert ' / ' in record.section
        assert record.clinical_review is False
        assert record.permission_basis['license'] == 'CC-BY-NC-SA-4.0'
