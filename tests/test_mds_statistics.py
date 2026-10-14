import hashlib
import importlib
import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def stats():
    return importlib.import_module('scripts.build_mds_statistics')


@pytest.fixture
def document(tmp_path):
    raw = tmp_path / '09-probability.html'
    raw.write_text('<main><header><h1>9 Introduction to probability</h1></header><section id="sec-normal" class="level2"><h2>9.5 The normal distribution</h2><p>The normal distribution is a symmetric bell shaped distribution.</p><p>Its parameters are the mean and standard deviation.</p></section></main>', encoding='utf-8')
    rights = tmp_path / 'index.html'
    rights.write_text('<main>Danielle Navarro: Learning Statistics with R, released under a permissive creative commons licence, <a href="https://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA 4.0</a>.</main>', encoding='utf-8')
    review = tmp_path / 'rights.html'
    review.write_text('<p>Source license permits adaptation with attribution and ShareAlike. No separate restrictive terms apply in this captured evidence.</p>', encoding='utf-8')
    def h(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()
    return {'id': 'mds-lsr-probability', 'title': 'Learning Statistics with R: Introduction to probability', 'url': 'https://learningstatisticswithr.com/09-probability.html', 'publisher': 'Danielle Navarro', 'jurisdiction': 'AU', 'source_date': '2026-10-07', 'retrieved_date': '2026-10-09', 'edition': '0.7.1', 'license': 'CC-BY-SA-4.0', 'license_url': 'https://creativecommons.org/licenses/by-sa/4.0/', 'approval': 'developer_reviewed', 'clinical_review': False, 'ai_reuse_restriction': False, 'terms': 'Attribution, same license for distributed adaptations, changes indicated; no endorsement.', 'attribution': 'Navarro, Danielle. Learning Statistics with R, version 0.7.1, 2026.', 'subjects': ['biostatistics'], 'level': 'Introductory university statistical foundations', 'raw_snapshot_path': raw.name, 'raw_sha256': h(raw), 'license_snapshot_path': rights.name, 'license_snapshot_sha256': h(rights), 'rights_review_snapshot_path': review.name, 'rights_review_snapshot_sha256': h(review), 'include_sections': ['9.5'], 'exclude_sections': [], 'limitations': []}


def test_html_retains_complete_prose_math_and_section_anchor_without_media(stats):
    html = '<main><header><h1>9 Probability</h1></header><section id="sec-normal"><h2>9.5 Normal distribution</h2><p>The distribution is symmetric around <span class="math inline">\\(\\mu\\)</span>.</p><p>Density depends on both parameters.</p><figure><img src="third-party.png"><figcaption>Figure caption.</figcaption></figure><pre>R output</pre><table><tr><td>Unlabeled table</td></tr></table><h3>9.5.1 Density</h3><p>Probability is the area under the curve.</p></section></main>'
    sections, excluded = stats.extract_html(html, ['9.5'], [])
    assert [(s['anchor'], s['paragraphs']) for s in sections] == [('sec-normal', ['The distribution is symmetric around \\(\\mu\\).', 'Density depends on both parameters.']), ('sec-normal', ['Probability is the area under the curve.'])]
    assert sections[0]['title'] == '9 Probability / 9.5 Normal distribution'
    assert any(x['reason'] == 'media_table_or_code' for x in excluded)


def test_selection_excludes_r_walkthrough_and_keeps_interpretation(stats):
    html = '<main><h1>10 Estimation</h1><section id="parent"><h2>10.5 Confidence intervals</h2><p>Initial informal example.</p><section id="interpreting"><h3>10.5.2 Interpreting confidence intervals</h3><p>The repeated procedure has coverage of 95 percent.</p></section><section id="code"><h3>10.5.3 Computing in R</h3><p>Call the function to get output.</p></section></section></main>'
    sections, _ = stats.extract_html(html, ['10.5.2'], [])
    assert len(sections) == 1
    assert sections[0]['anchor'] == 'interpreting'
    assert sections[0]['paragraphs'] == ['The repeated procedure has coverage of 95 percent.']


def test_footnote_qualification_is_retained_in_source_context(stats):
    html = '<main><h1>Probability</h1><section id="normal"><h2>9.5 Normal</h2><p>The approximation works<a role="doc-noteref"><sup>1</sup></a>.</p><div id="fn1"><p><sup>1</sup> Only under the specified assumptions.</p></div></section></main>'
    sections, _ = stats.extract_html(html, ['9.5'], [])
    assert sections[0]['paragraphs'] == ['The approximation works.', 'Footnote 1: Only under the specified assumptions.']


def test_statistics_mappings_do_not_confuse_clinical_normal_or_anova(stats):
    assert stats.topic_ids('9 Probability / 9.5 The normal distribution') == ['MDS-49']
    assert stats.topic_ids('5 Descriptive statistics / 5.1 Measures of central tendency') == ['MDS-46']
    assert stats.topic_ids('10 Estimation / 10.5.2 Interpreting a confidence interval') == ['MDS-50']
    assert stats.topic_ids('14 ANOVA / 14.10 Removing the normality assumption') == ['MDS-51', 'MDS-52']
    assert stats.topic_ids('15 Linear regression / 15.8 Assumptions of regression') == ['MDS-53']


def test_permissions_reject_ai_restriction_and_changed_evidence(document, tmp_path, stats):
    stats.validate_document(document, tmp_path)
    (tmp_path / 'rights.html').write_text('You may not use this content for generative AI or large language model training.', encoding='utf-8')
    with pytest.raises(ValueError, match='rights_review snapshot hash mismatch'):
        stats.validate_document(document, tmp_path)
    document['rights_review_snapshot_sha256'] = stats.sha256(tmp_path / 'rights.html')
    with pytest.raises(ValueError, match='AI reuse restriction'):
        stats.validate_document(document, tmp_path)


@pytest.mark.parametrize('key,value', [('url', 'https://www.openintro.org/book/os/'), ('license', 'CC-BY-SA-3.0'), ('clinical_review', True), ('ai_reuse_restriction', None), ('raw_snapshot_path', '../outside.html')])
def test_unverified_source_is_rejected(document, tmp_path, stats, key, value):
    document[key] = value
    with pytest.raises(ValueError):
        stats.validate_document(document, tmp_path)


def test_component_integrity_and_immutability(document, tmp_path, stats):
    target = tmp_path / 'stats-v1'
    manifest = stats.build_component([document], target, root=tmp_path)
    assert manifest['records'] == manifest['sources'] == 1
    rec = json.loads((target / 'records.jsonl').read_text(encoding='utf-8'))
    meta = json.loads((target / 'metadata.json').read_text(encoding='utf-8'))
    source = yaml.safe_load((target / 'sources.yaml').read_text(encoding='utf-8'))['sources'][0]
    assert rec['source_type'] == 'teaching'
    assert rec['topics'] == ['Probability, normal distribution and inferential statistics']
    assert rec['clinical_review'] is False
    chunk = meta['chunks'][rec['chunk_id']]
    assert chunk['syllabus_ids'] == ['MDS-49']
    assert chunk['material_type'] == 'foundation'
    assert chunk['page_url'] == 'https://learningstatisticswithr.com/09-probability.html#sec-normal'
    assert source['raw_sha256'] == rec['permission_basis']['snapshot_sha256']
    assert source['record_checksums']
    with pytest.raises(ValueError, match='exists'):
        stats.build_component([document], target, root=tmp_path)
