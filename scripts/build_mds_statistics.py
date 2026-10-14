"""Build immutable statistical foundations from the author's licensed HTML pages.

Whole paragraphs and mathematical notation are retained with source section URLs
and deterministic element/hash lineage. Figures, tables and executable code are
excluded. The matching author PDF is pinned as an additional provenance artifact.
"""

import argparse
import hashlib
import json
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

import yaml
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.services.retrieval import Reference  # noqa: E402
from scripts.build_mbbs_library import sha256, snapshot_path, split_context  # noqa: E402

HOST = 'learningstatisticswithr.com'
LICENSE = 'CC-BY-SA-4.0'
LICENSE_URL = 'https://creativecommons.org/licenses/by-sa/4.0/'
AI_RESTRICTION = re.compile(r'(?:may\s+not|must\s+not|shall\s+not|prohibit\w*|not\s+permitted|prior\s+written\s+permission)[^.\n]{0,350}(?:generative\s+AI|artificial\s+intelligence|large\s+language\s+model|machine\s+learning)|(?:generative\s+AI|artificial\s+intelligence|large\s+language\s+model)[^.\n]{0,200}(?:prohibit\w*|prior\s+written\s+permission)', re.I)
ALLOWED_PAGES = {'02-studydesign.html', '05-descriptives.html', '09-probability.html',
    '10-estimation.html', '11-hypothesistesting.html', '13-ttest.html', '14-anova.html', '15-regression.html'}
TOPIC_TITLES = {
    'MDS-44': 'Basic principles of biostatistics',
    'MDS-45': 'Collection and organization of data',
    'MDS-46': 'Measures of central tendency',
    'MDS-47': 'Measures of variability',
    'MDS-48': 'Sampling and planning of health survey',
    'MDS-49': 'Probability, normal distribution and inferential statistics',
    'MDS-50': 'Estimating population values',
    'MDS-51': 'Tests of significance (parametric/non-parametric)',
    'MDS-52': 'Analysis of variance',
    'MDS-53': 'Association, correlation and regression',
}


def topic_ids(title):
    labels = title.split(' / ')
    numbers = [re.match(r'^(\d+(?:\.\d+)*)\s', x) for x in labels]
    section = next((m.group(1) for m in reversed(numbers) if m), '')
    if section.startswith('2.'):
        return ['MDS-44', 'MDS-45'] if section.startswith(('2.1', '2.2', '2.3')) else ['MDS-44', 'MDS-48']
    if section.startswith('5.1'):
        return ['MDS-46']
    if section.startswith(('5.2', '5.3', '5.6')):
        return ['MDS-47']
    if section.startswith('5.7'):
        return ['MDS-53']
    if section.startswith('5.8'):
        return ['MDS-45']
    if section.startswith('9.'):
        return ['MDS-49']
    if section.startswith('10.1'):
        return ['MDS-48']
    if section.startswith(('10.2', '10.3')):
        return ['MDS-49', 'MDS-50']
    if section.startswith(('10.4', '10.5', '10.6')):
        return ['MDS-50']
    if section.startswith(('11.', '13.')):
        return ['MDS-51']
    if section.startswith('14.10'):
        return ['MDS-51', 'MDS-52']
    if section.startswith('14.'):
        return ['MDS-52']
    if section.startswith('15.'):
        return ['MDS-53']
    return []


def validate_document(doc, root=ROOT):
    parsed = urlsplit(doc['url'])
    if (parsed.scheme != 'https' or parsed.hostname != HOST or parsed.username or parsed.password
            or parsed.path.lstrip('/') not in ALLOWED_PAGES):
        raise ValueError('Unverified statistics publisher URL')
    if doc.get('license') != LICENSE or doc.get('license_url') != LICENSE_URL:
        raise ValueError('Unverified statistics license')
    if doc.get('approval') != 'developer_reviewed' or doc.get('clinical_review') is not False:
        raise ValueError('Developer source review required; clinical review cannot be claimed')
    if doc.get('ai_reuse_restriction') is not False:
        raise ValueError('AI reuse restriction unverified')
    evidence = {}
    for kind in ('raw', 'license', 'rights_review'):
        path = snapshot_path(doc[f'{kind}_snapshot_path'], root)
        key = 'raw_sha256' if kind == 'raw' else f'{kind}_snapshot_sha256'
        if sha256(path) != doc[key]:
            raise ValueError(f'{kind} snapshot hash mismatch')
        evidence[kind] = path.read_text(encoding='utf-8')
        if AI_RESTRICTION.search(BeautifulSoup(evidence[kind], 'html.parser').get_text(' ', strip=True)):
            raise ValueError('AI reuse restriction found in captured publisher evidence')
    rights = BeautifulSoup(evidence['license'], 'html.parser')
    if (not rights.find('a', href=LICENSE_URL) or 'Danielle Navarro' not in rights.get_text()
            or 'CC BY-SA 4.0' not in rights.get_text()):
        raise ValueError('Author-specific license evidence missing')
    if not all(doc.get(k) for k in ('edition', 'attribution', 'terms', 'subjects', 'level', 'include_sections')):
        raise ValueError('Missing provenance, rights or reviewed section scope')
    if doc.get('original_pdf_path'):
        if sha256(snapshot_path(doc['original_pdf_path'], root)) != doc.get('original_pdf_sha256'):
            raise ValueError('Original PDF snapshot hash mismatch')
    for item in doc.get('acquisition_evidence', []):
        if sha256(snapshot_path(item['path'], root)) != item['sha256']:
            raise ValueError('Acquisition evidence hash mismatch')


def extract_html(raw_html, include_sections, exclude_sections):
    soup = BeautifulSoup(raw_html, 'html.parser')
    main = soup.find('main')
    if main is None:
        raise ValueError('Publisher main teaching content missing')
    sections, excluded, headings, paragraphs, elements = [], [], [], [], []
    selected, anchor = False, ''

    def flush():
        if paragraphs:
            sections.append({'title': ' / '.join(h for _, h in headings), 'anchor': anchor,
                             'paragraphs': list(paragraphs), 'source_elements': list(elements)})
        paragraphs.clear()
        elements.clear()

    candidates = main.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'ul', 'ol', 'figure', 'pre', 'table'])
    for index, node in enumerate(candidates):
        if node.name.startswith('h') and len(node.name) == 2 and node.name[1].isdigit():
            flush()
            depth = int(node.name[1])
            label = re.sub(r'\s+', ' ', node.get_text('', strip=False)).strip()
            headings = [(d, h) for d, h in headings if d < depth] + [(depth, label)]
            section = node.find_parent('section')
            anchor = section.get('id', '') if section else node.get('id', '')
            if not anchor and node.find(id=True):
                anchor = node.find(id=True)['id']
            number = re.match(r'^(\d+(?:\.\d+)*)\s', label)
            code = number.group(1) if number else ''
            def matches(prefix):
                return code == prefix or code.startswith(prefix + '.')
            selected = any(matches(x) for x in include_sections) and not any(matches(x) for x in exclude_sections)
            continue
        if node.name in ('figure', 'pre', 'table'):
            excluded.append({'html_element_index': index, 'reason': 'media_table_or_code'})
            continue
        if node.find_parent(['figure', 'pre', 'table', 'nav', 'ul', 'ol']):
            continue
        if not selected:
            excluded.append({'html_element_index': index, 'reason': 'outside_reviewed_section_scope'})
            continue
        clone = BeautifulSoup(str(node), 'html.parser')
        for unwanted in clone.select('a[role="doc-noteref"], a.anchorjs-link, script, style, img, button'):
            unwanted.decompose()
        footnote = node.find_parent(id=re.compile(r'^fn\d+$'))
        if footnote:
            for sup in clone.select('sup'):
                sup.decompose()
        if node.name in ('ul', 'ol'):
            text = '\n'.join('- ' + re.sub(r'\s+', ' ', li.get_text('', strip=False)).strip() for li in clone.find_all('li', recursive=True))
        else:
            text = re.sub(r'\s+', ' ', clone.get_text('', strip=False)).strip()
        if footnote:
            text = 'Footnote ' + footnote['id'].removeprefix('fn') + ': ' + text
        if len(text) < 10:
            continue
        if '\ufffd' in text or '\x00' in text:
            raise ValueError('Corrupt statistics paragraph extraction')
        paragraphs.append(text)
        elements.append({'html_element_index': index, 'element_type': node.name,
                         'sha256': hashlib.sha256(text.encode('utf-8')).hexdigest()})
    flush()
    return sections, excluded


def build_component(documents, output, root=ROOT):
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Component exists; choose a new version, never overwrite')
    if len({d['id'] for d in documents}) != len(documents):
        raise ValueError('Duplicate statistics document ID')
    records, sources, chunks, source_meta, skipped = [], [], {}, {}, []
    for doc in documents:
        validate_document(doc, root)
        raw = snapshot_path(doc['raw_snapshot_path'], root).read_text(encoding='utf-8')
        sections, exclusions = extract_html(raw, doc['include_sections'], doc.get('exclude_sections', []))
        basis = {'type': 'open_license', 'approved_host': HOST, 'license': LICENSE,
                 'license_url': LICENSE_URL, 'snapshot_sha256': doc['raw_sha256'], 'clinical_review': False}
        checksums = []
        for i, section in enumerate(sections):
            try:
                contexts = split_context(section['paragraphs'])
            except ValueError as exc:
                skipped.append({'source_id': doc['id'], 'section': section['title'], 'reason': str(exc), 'paragraphs': len(section['paragraphs'])})
                continue
            for j, context in enumerate(contexts):
                ids = topic_ids(section['title'])
                if not ids:
                    raise ValueError('Selected section has no verified statistics syllabus mapping')
                page_url = doc['url'] + ('#' + section['anchor'] if section['anchor'] else '')
                record = Reference(source_id=doc['id'], title=doc['title'], url=doc['url'],
                    publisher=doc['publisher'], jurisdiction=doc['jurisdiction'], source_date=doc['source_date'],
                    retrieved_date=doc['retrieved_date'], snapshot_id=output.name, section=section['title'],
                    text=context['text'], topics=[TOPIC_TITLES[x] for x in ids],
                    keywords=sorted(set(re.findall(r'[a-z][a-z-]{3,}', section['title'].lower()))) or ['statistics'],
                    source_type='teaching', section_id=f'section-{i + 1}-context-{j + 1}',
                    text_revision=doc['edition'], permission_basis=basis, clinical_review=False)
                record.chunk_id = record.stable_id()
                if record.chunk_id in chunks:
                    raise ValueError('Duplicate statistics chunk ID')
                records.append(record)
                checksums.append(record.content_hash())
                elements = section['source_elements'][context['paragraph_start']:context['paragraph_end']]
                chunks[record.chunk_id] = {'source_id': doc['id'], 'subjects': doc['subjects'],
                    'level': doc['level'], 'edition': doc['edition'], 'context': section['title'],
                    'section_id': record.section_id, 'page_url': page_url, 'source_anchor': section['anchor'],
                    'source_elements': elements, 'paragraph_start': context['paragraph_start'],
                    'paragraph_end': context['paragraph_end'], 'complete_paragraph': True,
                    'context_overlap': 'one whole paragraph within source section',
                    'material_type': 'foundation', 'syllabus_ids': ids, 'license': LICENSE,
                    'clinical_review': False, 'review_status': 'developer_source_extraction_review',
                    'coverage_status': 'relevant_material_not_competency_mastery',
                    'original_pdf_path': doc.get('original_pdf_path'),
                    'pdf_pages': doc.get('section_pdf_pages', {}).get(section['anchor'], []),
                    'limitations': doc.get('limitations', []) + ['Tables, figures and executable code omitted; prose can refer to them.']}
        if not checksums:
            raise ValueError(f'{doc["id"]}: no usable paragraphs')
        source = {k: doc.get(k) for k in ('title', 'url', 'publisher', 'jurisdiction', 'source_date',
            'retrieved_date', 'terms', 'attribution', 'raw_snapshot_path', 'raw_sha256',
            'license_snapshot_path', 'license_snapshot_sha256', 'rights_review_snapshot_path',
            'rights_review_snapshot_sha256', 'license', 'license_url', 'ai_reuse_restriction',
            'ai_reuse_review', 'original_pdf_path', 'original_pdf_sha256', 'acquisition_evidence')}
        source.update(source_id=doc['id'], version=doc['edition'], approval='developer_reviewed',
            reviewer='Codex publisher/source/rights and extraction review; no faculty review',
            clinical_review=False, permission_basis=basis, record_checksums=checksums,
            checksum_format='sha256-canonical-record-v2')
        sources.append(source)
        source_meta[doc['id']] = {**{k: doc.get(k) for k in ('subjects', 'level', 'edition', 'attribution',
            'acquisition_method', 'limitations', 'original_pdf_path', 'original_pdf_sha256', 'include_sections', 'exclude_sections')},
            'material_type': 'foundation', 'excluded_blocks': exclusions,
            'syllabus_ids': sorted({x for c in chunks.values() if c['source_id'] == doc['id'] for x in c['syllabus_ids']})}
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='statistics-staging-', dir=output.parent))
    (staging / 'records.jsonl').write_text('\n'.join(r.model_dump_json() for r in records) + '\n', encoding='utf-8')
    (staging / 'sources.yaml').write_text(yaml.safe_dump({'library_version': output.name, 'sources': sources}, sort_keys=False, allow_unicode=True), encoding='utf-8')
    metadata = {'schema_version': 1, 'chunks': chunks, 'sources': source_meta,
        'clinical_review': False, 'faculty_review': 'pending', 'skipped_sections': skipped,
        'explanation_units': 'none; publisher original text with whitespace normalization only',
        'pdf_page_numbering': 'One-based physical PDF pages; HTML pages/anchors remain the canonical evidence locator.'}
    (staging / 'metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    report = ['# Statistical foundations: bibliography and licensing review', '',
        '[Learning Statistics with R](https://learningstatisticswithr.com/), Danielle Navarro, version 0.7.1 (2026-10-07), author-published.', '',
        '[Author license](https://learningstatisticswithr.com/): CC BY-SA 4.0; [canonical license](https://creativecommons.org/licenses/by-sa/4.0/). Attribution, license link, indicated changes and ShareAlike for adaptations are retained. No endorsement implied.', '',
        'No explicit AI reuse restriction found in captured author license/preface, changelog, selected source pages or CC legalcode. No separate site-specific terms page was linked in the captured author pages. This evidence is reviewed for local educational retrieval; no publisher agreement, account or payment was used.', '',
        'OpenIntro Statistics was considered but retained link-only: its [current official terms](https://www.openintro.org/terms/) include an automated AI/ML-training scraping agreement effective January 2025. No OpenIntro textbook prose was imported. UniSQ was considered but not imported because reviewed normality explanations conflate univariate and multivariate assumptions.', '',
        'Extraction changes: whitespace normalized in rendered HTML paragraphs and LaTeX notation; whole-paragraph overlap; section selections exclude detailed R walkthroughs, graphics, tables and code. Footnote qualifications retained when present in the source section. The complete author PDF and raw HTML are pinned. Physical PDF page locators are secondary to the exact HTML page/anchor and element/hash lineage.', '',
        'Statistical examples are instructional, often simulated or psychological examples, and are not clinical evidence. Faculty correctness review is pending. Sampling and research-design foundations do not establish complete health-survey planning or MDS competency coverage.', '']
    for doc in documents:
        report.extend([f'## {doc["title"]}', '', doc['attribution'], '',
            f'Publisher page: [{doc["url"]}]({doc["url"]}).', '',
            f'Raw SHA-256 `{doc["raw_sha256"]}`; author rights SHA-256 `{doc["license_snapshot_sha256"]}`.', '',
            'Reviewed section prefixes: ' + ', '.join(doc['include_sections']) + '.', '',
            'Syllabus associations: ' + ', '.join(source_meta[doc['id']]['syllabus_ids']) + '.', ''])
    report.extend(['## Coverage and review limits', '', f'{len(records)} contexts from {len(sources)} chapter sources. Skipped oversized sections: {len(skipped)}; see metadata.json for explicit source scope and omissions.', ''])
    (staging / 'BIBLIOGRAPHY_LICENSE_REPORT.md').write_text('\n'.join(report), encoding='utf-8')
    manifest = {'version': output.name, 'library_version': output.name, 'schema_version': 1,
        'files': {name: sha256(staging / name) for name in ('records.jsonl', 'sources.yaml', 'metadata.json', 'BIBLIOGRAPHY_LICENSE_REPORT.md')},
        'records': len(records), 'sources': len(sources), 'clinical_review': False, 'faculty_review': 'pending',
        'material_type': 'foundation', 'licenses': [LICENSE],
        'subjects': dict(Counter(s for r in records for s in r.topics)),
        'syllabus_ids': sorted({x for c in chunks.values() for x in c['syllabus_ids']}),
        'skipped_sections': skipped, 'usage': 'Educational retrieval; attribution and distributed-adaptation ShareAlike retained.',
        'coverage_claim': 'Partial statistical foundations; no verified MDS competency mastery.'}
    (staging / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    staging.rename(output)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT / 'configs/mds_statistics_sources.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    manifest = build_component(json.loads(args.config.read_text(encoding='utf-8'))['documents'], args.output)
    print(json.dumps({k: manifest[k] for k in ('version', 'sources', 'records', 'syllabus_ids', 'skipped_sections')}, indent=2))


if __name__ == '__main__':
    main()
