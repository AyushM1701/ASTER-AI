"""Build immutable dental foundation components from licensed publisher snapshots.

Acquisition uses pinned Exa markdown outputs because direct publisher HTTP returned
403. No network is required to rebuild. Figures, tables, quizzes and external media
are omitted; publisher paragraphs retain exact source spans and heading hierarchy.
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.services.retrieval import Reference  # noqa: E402
from scripts.build_mbbs_library import sha256, snapshot_path, split_context  # noqa: E402

BOOK_ROOT = 'https://openoregon.pressbooks.pub/histologyandembryology/'
LICENSE = 'CC-BY-NC-SA-4.0'
LICENSE_URL = 'https://creativecommons.org/licenses/by-nc-sa/4.0/'
LICENSE_LABEL = 'Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License'
AI_RESTRICTION = re.compile(r'(?:may\s+not|must\s+not|shall\s+not|prohibit\w*|not\s+permitted|prior\s+written\s+permission)[^.\n]{0,350}(?:generative\s+AI|artificial\s+intelligence|large\s+language\s+model|machine\s+learning)|(?:generative\s+AI|artificial\s+intelligence|large\s+language\s+model)[^.\n]{0,200}(?:prohibit\w*|prior\s+written\s+permission)', re.I)

# Associations identify relevant paragraphs, never certify completion of a topic.
# The first title is a chapter label; child headings are more specific and are
# used preferentially so a broad dentin/pulp chapter does not map every paragraph
# to both topics. Explicit prose terms add only directly named subject matter.
HEADING_MAP = {
    'MDS-01': r'cell membrane|organelle|cell biology|cytoplasm|mitochondri|ribosome|endoplasmic|golgi',
    'MDS-02': r'mitosis|meiosis|cell cycle|gametogenesis|fertilization',
    'MDS-03': r'nucleus|nuclei|chromatin',
    'MDS-04': r'blood vessel|capillar|angiogenesis',
    'MDS-05': r'epitheli|basement membrane|cell junction|desmosome',
    'MDS-06': r'connective tissue|collagen|ground substance|mesenchyme|extracellular matrix',
    'MDS-07': r'muscles of mastication|facial expression|masseter|temporalis|pterygoid',
    'MDS-08': r'cranial nerve|trigeminal|facial nerve|glossopharyngeal|hypoglossal',
    'MDS-09': r'lymph node',
    'MDS-10': r'macrophage|monocyte',
    'MDS-11': r'lymphatic|lymph drainage',
    'MDS-12': r'nervous tissue|muscle tissue|histology of nerves',
    'MDS-13': r'blood cell|erythrocyte|leukocyte|platelet',
    'MDS-15': r'nervous tissue|nervous system|somatosens|mechanoreceptor|nociceptor|receptor of',
    'MDS-16': r'\bpain\b|nociception|dentin hypersensitivity',
    'MDS-17': r'bone tissue|bone remodeling|bone homeostasis|bone formation',
    'MDS-18': r'calcium|phosphate|phosphorus',
    'MDS-19': r'mineralization|maturation|demineralization',
    'MDS-21': r'apoptosis',
    'MDS-22': r'inflammation|inflammatory',
    'MDS-25': r'wound|repair|regeneration|healing',
    'MDS-26': r'bone healing|dentin repair|reparative dentin|tertiary dentin|cementum repair',
    'MDS-30': r'neoplas|oral cancer|carcinoma|\btumou?r\b',
    'MDS-31': r'tooth formation|tooth development|odontogenesis|bud stage|cap stage|bell stage|crown stage|root development|dental lamina|tooth germ',
    'MDS-32': r'amelogenesis|ameloblast|enamel|tomes|retzius|perikymata',
    'MDS-33': r'dentin|odontoblast|dentinal',
    'MDS-34': r'\bpulp\b|pulpal',
    'MDS-35': r'cementum|cementogen|cementoblast|cementocyte',
    'MDS-36': r'periodontal ligament|\bPDL\b',
    'MDS-37': r'alveolar bone|alveolar ridge',
    'MDS-38': r'salivary gland|exocrine gland|parotid|submandibular|sublingual',
    'MDS-39': r'oral mucosa|oral cavity|lining mucosa|masticatory mucosa|specialized mucosa|gingiva|gingival|\btongue\b|\blips\b',
    'MDS-40': r'junctional epithelium|dento.?gingival|gingival sulcus|sulcular',
    'MDS-41': r'temporomandibular|\bTMJ\b',
    'MDS-42': r'maxillary sinus|para.nasal sinus',
    'MDS-43': r'tooth eruption|tooth exfoliation|shedding|primary root resorption',
    'MDS-54': r'aging|age.related|age changes|secondary dentin',
    'MDS-55': r'\bsaliva\b|salivary secretion|salivary gland',
    'MDS-56': r'mastication|speech|deglutition|swallowing',
    'MDS-57': r'taste bud|\btaste\b|gustation',
    'MDS-58': r'early development|gastrulation|neurulation|embryonic|germ layer|embryology|implantation|cleavage|blastocyst|morula|stem cell|differentiation|morphogen|homeobox|cell lineage',
    'MDS-59': r'formation of the face|development of the face|facial development|formation of the tongue|tongue development|development of the tongue|formation of the palate|palate development|pharyngeal arch|nasal process|frontonasal|inter.maxillary',
    'MDS-60': r'maxillary process|mandibular arch|mandible|meckel|growth of the maxilla',
    'MDS-61': r'ossification|bone formation|bone development',
    'MDS-62': r'epithelial.to.mesenchymal|reciprocal induction|induction of|neural crest|cell migration|planar cell polarity',
    'MDS-69': r'oral microflora|oral microbiome|dental plaque|biofilm',
    'MDS-70': r'antibod|antigen',
    'MDS-71': r'immun|lymphocyte|tonsillar|tonsils',
    'MDS-75': r'gene expression|transcription factor|genetics|mutation|epigenetic|methylation|homeobox',
    'MDS-76': r'protein synthesis|transcription|translation|\bDNA\b|\bRNA\b|ribosome',
    'MDS-80': r'light microscop|history of histology|histological stain|H.?&.?E',
    'MDS-81': r'H.?&.?E|hematoxylin|haematoxylin|eosin',
    'MDS-85': r'electron microscop',
}
PROSE_MAP = {
    'MDS-19': r'\b(?:mineralization|demineralization|remineralization)\b',
    'MDS-21': r'\bapoptosis\b',
    'MDS-40': r'\bjunctional epithelium\b',
    'MDS-41': r'\btemporomandibular joint\b',
    'MDS-43': r'\b(?:tooth eruption|tooth exfoliation|root resorption)\b',
    'MDS-57': r'\btaste buds?\b',
    'MDS-62': r'\b(?:epithelial.to.mesenchymal transition|reciprocal induction)\b',
    'MDS-69': r'\b(?:oral microbiome|dental plaque|oral microflora|oral biofilm)\b',
}


def syllabus_associations(title, text):
    headings = title.split(' / ')
    specific = ' / '.join(headings[1:]) if len(headings) > 1 else title
    ids = {key for key, pattern in HEADING_MAP.items() if re.search(pattern, specific, re.I)}
    ids.update(key for key, pattern in PROSE_MAP.items() if re.search(pattern, text, re.I))
    return sorted(ids)


def validate_document(doc, root=ROOT):
    parsed = urlsplit(doc['url'])
    if (parsed.scheme != 'https' or parsed.hostname != 'openoregon.pressbooks.pub'
            or parsed.username or parsed.password or not doc['url'].startswith(BOOK_ROOT + 'chapter/')):
        raise ValueError('Unverified dental publisher URL')
    if doc.get('license') != LICENSE or doc.get('license_url') != LICENSE_URL:
        raise ValueError('Unverified dental license')
    if doc.get('approval') != 'developer_reviewed' or doc.get('clinical_review') is not False:
        raise ValueError('Developer source review required; clinical review cannot be claimed')
    if doc.get('ai_reuse_restriction') is not False:
        raise ValueError('AI reuse restriction unverified')
    evidence = {}
    for kind in ('raw', 'license', 'terms'):
        path = snapshot_path(doc[f'{kind}_snapshot_path'], root)
        hash_key = 'raw_sha256' if kind == 'raw' else f'{kind}_snapshot_sha256'
        if sha256(path) != doc[hash_key]:
            raise ValueError(f'{kind} snapshot hash mismatch')
        evidence[kind] = path.read_text(encoding='utf-8')
        if AI_RESTRICTION.search(evidence[kind]):
            raise ValueError('AI reuse restriction found in publisher evidence')
    if LICENSE_LABEL not in evidence['raw'] or 'Laird C Sheldahl' not in evidence['raw']:
        raise ValueError('Chapter-specific license/author evidence missing')
    if (LICENSE_LABEL not in evidence['license'] or 'Laird C Sheldahl' not in evidence['license']
            or LICENSE_URL.rstrip('/') not in evidence['license']):
        raise ValueError('Publisher license evidence missing')
    if 'URL: https://pressbooks.com/' not in evidence['terms']:
        raise ValueError('Official platform terms evidence missing')
    if f'URL: {doc["url"]}' not in evidence['raw']:
        raise ValueError('Publisher chapter identity mismatch')
    if not all(doc.get(key) for key in ('edition', 'attribution', 'terms', 'subjects', 'level')):
        raise ValueError('Missing provenance, attribution or educational scope')
    for item in doc.get('acquisition_evidence', []):
        if sha256(snapshot_path(item['path'], root)) != item['sha256']:
            raise ValueError('Acquisition evidence hash mismatch')


def extract_sections(raw_text):
    if '\x00' in raw_text or raw_text.count('\ufffd') > max(3, len(raw_text) * 0.002):
        raise ValueError('Corrupt publisher extraction')
    sections, excluded, headings, paragraphs, spans = [], [], [], [], []
    skip = False

    def flush():
        if paragraphs and not skip:
            sections.append({'title': ' / '.join(label for _, label in headings) or 'Introduction',
                             'paragraphs': list(paragraphs), 'source_spans': list(spans)})
        paragraphs.clear()
        spans.clear()

    for match in re.finditer(r'\S[\s\S]*?(?=\n\s*\n|\Z)', raw_text):
        block = match.group().strip()
        start = match.start()
        end = start + len(block)
        heading = re.fullmatch(r'(#{1,6})\s+([^\n]+)(?:\nURL: https://[^\n]+)?', block)
        if heading:
            flush()
            depth, label = len(heading.group(1)), heading.group(2)
            headings = [(d, h) for d, h in headings if d < depth]
            headings.append((depth, label))
            skip = bool(re.search(r'chapter (?:outline|review)|references|resources|attributions|copyright|licen[cs]e|share this book|review questions', label, re.I))
            continue
        reason = None
        if skip:
            reason = 'non_content_section'
        elif re.match(r'^(?:URL:|Published:|navigation|Share this|Menu|Histology and Embryology for Dental Hygiene\s*$)', block, re.I) or re.fullmatch(r'[^\n]+[–-] Histology and Embryology for Dental Hygiene', block):
            reason = 'navigation_or_identity'
        elif re.match(r'^(?:Figure\s|Fig\.\s|Image:?\s|Image credit|!\[|<visual_element)', block, re.I):
            reason = 'figure_or_media'
        # Every pinned Sheldahl chapter starts with an unheaded outline; the
        # teaching prose begins at the first child heading. Outline labels are
        # sometimes bare text rather than list markup in the publisher extract.
        elif len(headings) == 1:
            reason = 'chapter_outline'
        elif block.startswith('|') or re.match(r'^Table\s', block, re.I):
            reason = 'table_requires_separate_review'
        elif re.fullmatch(r'[-*_\s]+', block) or len(block) < 10:
            reason = 'separator'
        elif re.search(r'One or more interactive elements has been excluded|iframe|<video|<audio', block, re.I):
            reason = 'figure_or_media'
        if reason:
            excluded.append({'start': start, 'end': end, 'reason': reason})
            continue
        paragraphs.append(block)
        spans.append({'start': start, 'end': end, 'text': block,
                      'sha256': hashlib.sha256(block.encode('utf-8')).hexdigest()})
    flush()
    return sections, excluded


def build_component(documents, output, root=ROOT):
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Component exists; choose a new version, never overwrite')
    if len({d['id'] for d in documents}) != len(documents):
        raise ValueError('Duplicate dental document ID')
    syllabus = json.loads((ROOT / 'configs/mds_syllabus.json').read_text(encoding='utf-8'))
    titles = {t['id']: t['title'] for t in syllabus['topics']}
    records, sources, chunks, source_meta, skipped, exclusions = [], [], {}, {}, [], []
    for doc in documents:
        validate_document(doc, root)
        raw = snapshot_path(doc['raw_snapshot_path'], root).read_text(encoding='utf-8')
        sections, omitted = extract_sections(raw)
        exclusions.extend({'source_id': doc['id'], **x} for x in omitted)
        basis = {'type': 'open_license', 'approved_host': 'openoregon.pressbooks.pub',
                 'license': LICENSE, 'license_url': LICENSE_URL,
                 'snapshot_sha256': doc['raw_sha256'], 'clinical_review': False}
        checksums = []
        for i, section in enumerate(sections):
            try:
                contexts = split_context(section['paragraphs'])
            except ValueError as exc:
                skipped.append({'source_id': doc['id'], 'section': section['title'], 'reason': str(exc),
                                'paragraphs': len(section['paragraphs'])})
                continue
            for j, context in enumerate(contexts):
                ids = syllabus_associations(section['title'], context['text'])
                topics = [titles[x] for x in ids] or [section['title'].split(' / ')[-1]]
                record = Reference(source_id=doc['id'], title=doc['title'], url=doc['url'],
                    publisher=doc['publisher'], jurisdiction=doc['jurisdiction'],
                    section=section['title'], source_date=doc['source_date'],
                    retrieved_date=doc['retrieved_date'], snapshot_id=output.name,
                    text=context['text'], topics=topics,
                    keywords=sorted(set(re.findall(r'[a-z][a-z-]{3,}', section['title'].lower()))) or doc['subjects'],
                    source_type='teaching', section_id=f'section-{i + 1}-context-{j + 1}',
                    text_revision=doc['edition'], permission_basis=basis, clinical_review=False)
                record.chunk_id = record.stable_id()
                if record.chunk_id in chunks:
                    raise ValueError('Duplicate dental chunk ID')
                records.append(record)
                checksums.append(record.content_hash())
                chunk_spans = section['source_spans'][context['paragraph_start']:context['paragraph_end']]
                chunks[record.chunk_id] = {'source_id': doc['id'], 'subjects': doc['subjects'],
                    'level': doc['level'], 'edition': doc['edition'], 'context': section['title'],
                    'section_id': record.section_id, 'material_type': 'foundation',
                    'syllabus_ids': ids, 'complete_paragraph': True,
                    'paragraph_start': context['paragraph_start'], 'paragraph_end': context['paragraph_end'],
                    'source_spans': [{k: span[k] for k in ('start', 'end', 'sha256')} for span in chunk_spans],
                    'context_overlap': 'one whole paragraph within same source section',
                    'license': LICENSE, 'clinical_review': False,
                    'review_status': 'developer_source_extraction_review',
                    'coverage_status': 'relevant_material_not_competency_mastery',
                    'limitations': doc.get('limitations', []) + ['Figures and tables excluded; text may refer to them.']}
        if not checksums:
            raise ValueError(f'{doc["id"]}: no usable source paragraphs')
        source = {k: doc.get(k) for k in ('title', 'url', 'publisher', 'jurisdiction', 'source_date',
            'retrieved_date', 'terms', 'attribution', 'raw_snapshot_path', 'raw_sha256',
            'license_snapshot_path', 'license_snapshot_sha256', 'terms_snapshot_path',
            'terms_snapshot_sha256', 'license', 'license_url', 'ai_reuse_restriction',
            'ai_reuse_review', 'acquisition_evidence')}
        source.update(source_id=doc['id'], version=doc['edition'], approval='developer_reviewed',
            reviewer='Codex publisher/source/rights and extraction review; no faculty review',
            clinical_review=False, permission_basis=basis, record_checksums=checksums,
            checksum_format='sha256-canonical-record-v2')
        sources.append(source)
        source_meta[doc['id']] = {**{key: doc.get(key) for key in ('subjects', 'level', 'edition',
            'attribution', 'acquisition_method', 'limitations')}, 'material_type': 'foundation',
            'syllabus_ids': sorted({x for c in chunks.values() if c['source_id'] == doc['id'] for x in c['syllabus_ids']})}
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='dental-staging-', dir=output.parent))
    (staging / 'records.jsonl').write_text('\n'.join(r.model_dump_json() for r in records) + '\n', encoding='utf-8')
    (staging / 'sources.yaml').write_text(yaml.safe_dump({'library_version': output.name, 'sources': sources}, sort_keys=False, allow_unicode=True), encoding='utf-8')
    metadata = {'schema_version': 1, 'chunks': chunks, 'sources': source_meta,
        'clinical_review': False, 'skipped_sections': skipped, 'excluded_blocks': exclusions,
        'faculty_review': 'pending', 'explanation_units': 'none; publisher original text only'}
    (staging / 'metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    report = ['# Dental foundation bibliography and licensing review', '',
        'Developer source/rights/extraction review only. Clinical correctness and faculty review remain pending.', '',
        'Local noncommercial educational retrieval. Retain attribution and CC BY-NC-SA 4.0; adaptations of this text retain the same license. No endorsement is implied.', '',
        'Extraction changes: chapter text segmented at headings; whole paragraphs overlap; tables, figures, image credits, media, quizzes and navigation removed. No third-party images were downloaded.', '',
        'Direct publisher HTTP returned 403; the pinned Exa publisher-page extraction is used. Extraction reaches the publisher License and Share This Book footer for every chapter. This is not a verified printed edition or a guarantee of all original HTML elements.', '',
        'AI reuse review: no explicit AI prohibition found in captured chapter copyright notices, publisher preface or official platform terms. This review concerns local licensed-text retrieval, and does not assert unrestricted commercial use or AI training rights.', '']
    for doc in documents:
        report.extend([f'## {doc["title"]}', '', doc['attribution'], '',
            f'Publisher: [{doc["publisher"]}]({doc["url"]}); source publication 2020; acquired {doc["retrieved_date"]}.', '',
            f'License: [{LICENSE}]({LICENSE_URL}); attribution, noncommercial use and ShareAlike required; third-party exceptions excluded.', '',
            f'Raw snapshot: `{doc["raw_snapshot_path"]}`, SHA-256 `{doc["raw_sha256"]}`.', '',
            f'License evidence: `{doc["license_snapshot_path"]}`, SHA-256 `{doc["license_snapshot_sha256"]}`.', '',
            f'Platform terms: `{doc["terms_snapshot_path"]}`, SHA-256 `{doc["terms_snapshot_sha256"]}`.', '',
            'Relevant syllabus associations: ' + ', '.join(source_meta[doc['id']]['syllabus_ids']) + '.', ''])
    mapped = sorted({x for c in chunks.values() for x in c['syllabus_ids']})
    absent = [t['id'] for t in syllabus['topics'] if t['id'] not in mapped]
    report.extend(['## Coverage limits', '',
        'The book targets dental hygiene students, with selected histology and development foundations. Association is not complete postgraduate coverage. Detailed oral pathology, oral microbiology, immunology, clinical salivary diagnostics, advanced laboratory protocols and statistics require additional sources.', '',
        f'{len(mapped)} of {len(titles)} photographed topics have at least one direct heading/prose association in this component.', '',
        'Unmapped topics in this component: ' + ', '.join(absent) + '.', '',
        f'Skipped oversized context sections: {len(skipped)}. Consult metadata.json for explicit exclusions.', ''])
    (staging / 'BIBLIOGRAPHY_LICENSE_REPORT.md').write_text('\n'.join(report), encoding='utf-8')
    manifest = {'version': output.name, 'library_version': output.name, 'schema_version': 1,
        'files': {name: sha256(staging / name) for name in ('records.jsonl', 'sources.yaml', 'metadata.json', 'BIBLIOGRAPHY_LICENSE_REPORT.md')},
        'records': len(records), 'sources': len(sources), 'clinical_review': False,
        'faculty_review': 'pending', 'material_type': 'foundation',
        'subjects': dict(Counter(s for r in records for s in r.topics)), 'licenses': [LICENSE],
        'syllabus_ids': mapped, 'unmapped_syllabus_ids': absent,
        'usage': 'Local noncommercial educational retrieval; source attribution, license and ShareAlike retained.',
        'coverage_claim': 'Partial dental hygiene foundations; no verified MDS competency mastery.',
        'skipped_sections': skipped}
    (staging / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    staging.rename(output)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT / 'configs/mds_dental_sources.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    docs = json.loads(args.config.read_text(encoding='utf-8'))['documents']
    manifest = build_component(docs, args.output)
    print(json.dumps({k: manifest[k] for k in ('version', 'records', 'sources', 'clinical_review', 'skipped_sections')}, indent=2))


if __name__ == '__main__':
    main()
