"""Build immutable, licensed educational references from pinned publisher snapshots.

No generated paraphrases or clinical approval. Markdown snapshots may be obtained
through the Exa publisher-page extractor when the publisher blocks direct HTTP.
Whole paragraph blocks and adjacent paragraph context are retained. Figures and
reference lists are excluded; exceptionally large paragraphs fail closed.
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

LICENSES = {
    'CC-BY-4.0': 'https://creativecommons.org/licenses/by/4.0/',
    'CC-BY-SA-4.0': 'https://creativecommons.org/licenses/by-sa/4.0/',
    'CC-BY-NC-4.0': 'https://creativecommons.org/licenses/by-nc/4.0/',
    'CC-BY-NC-SA-4.0': 'https://creativecommons.org/licenses/by-nc-sa/4.0/',
    'NIDDK-copyright-free': 'https://www.niddk.nih.gov/copyright',
    'CDC-public-domain': 'https://stacks.cdc.gov/view/cdc/13178',
    'NIMH-public-domain': 'https://www.nimh.nih.gov/site-info/policies',
    'MedlinePlus-genetics-public-domain': 'https://medlineplus.gov/about/using/usingcontent/',
    'CC-BY-NC-SA-3.0-IGO': 'https://creativecommons.org/licenses/by-nc-sa/3.0/igo/',
}
PUBLISHER_HOSTS = {
    'pressbooks.lib.vt.edu', 'opentextbc.ca',
    'humanbiology.pressbooks.tru.ca', 'open.oregonstate.education',
    'open.lib.umn.edu', 'www.niddk.nih.gov',
    'archive.cdc.gov', 'stacks.cdc.gov',
    'www.nimh.nih.gov', 'medlineplus.gov', 'hlh.who.int',
}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def snapshot_path(value, root):
    path = (Path(root) / value).resolve()
    if not path.is_relative_to(Path(root).resolve()):
        raise ValueError('Source snapshot outside workspace')
    return path


def validate_license(doc, root=ROOT):
    parsed = urlsplit(doc['url'])
    if parsed.scheme != 'https' or parsed.hostname not in PUBLISHER_HOSTS:
        raise ValueError('Unverified publisher host')
    if doc.get('ai_reuse_restriction') is not False:
        raise ValueError('AI reuse restriction unverified or disallows this use')
    if doc.get('license') not in LICENSES:
        raise ValueError('Unverified license')
    if doc.get('license_url', '').rstrip('/') != LICENSES[doc['license']].rstrip('/'):
        raise ValueError('Mismatched license URL')
    if doc.get('approval') != 'developer_reviewed' or doc.get('clinical_review') is not False:
        raise ValueError('Developer source review required; clinical review cannot be claimed')
    for kind in ('raw', 'license'):
        path = snapshot_path(doc[f'{kind}_snapshot_path'], root)
        if sha256(path) != doc[f'{kind}_sha256' if kind == 'raw' else 'license_snapshot_sha256']:
            raise ValueError(f'{kind} snapshot hash mismatch')
    if doc.get('original_pdf_path'):
        if sha256(snapshot_path(doc['original_pdf_path'], root)) != doc.get('original_pdf_sha256'):
            raise ValueError('Original PDF snapshot hash mismatch')
    evidence = snapshot_path(doc['license_snapshot_path'], root).read_text(encoding='utf-8')
    if doc['license_url'].rstrip('/') not in evidence:
        raise ValueError('License snapshot does not contain the claimed license link')
    if re.search(r'may not.*(?:large language model|generative AI)|prior written permission', evidence, re.I):
        raise ValueError('AI reuse restriction found in publisher evidence')
    if not all(doc.get(k) for k in ('edition', 'attribution', 'terms', 'subjects', 'level')):
        raise ValueError('Missing edition, attribution, terms or educational scope')


def split_context(paragraphs, limit=4000):
    """Overlap a whole paragraph so adjacent qualifications share a chunk.

    Reject paragraphs/pairs that cannot fit: never truncate a sentence or qualify
    a medical assertion by dropping its neighboring exception paragraph.
    """
    paragraphs = [p.strip() for p in paragraphs if p.strip()]
    if any(len(p) > limit for p in paragraphs):
        raise ValueError('Oversized paragraph requires manual coherent source selection')
    if any(len(a) + len(b) + 2 > limit for a, b in zip(paragraphs, paragraphs[1:])):
        raise ValueError('Adjacent paragraph context exceeds limit; manual review required')
    result, start = [], 0
    while start < len(paragraphs):
        end = start + 1
        while end < len(paragraphs) and len('\n\n'.join(paragraphs[start:end + 1])) <= limit:
            end += 1
        result.append({'text': '\n\n'.join(paragraphs[start:end]),
                       'paragraph_start': start, 'paragraph_end': end})
        if end == len(paragraphs):
            break
        start = end - 1
    return result


def extract_markdown(path):
    raw_text = Path(path).read_text(encoding='utf-8').strip()
    if raw_text.count('\ufffd') > max(3, len(raw_text) * 0.002) or '\x00' in raw_text:
        raise ValueError('Corrupt publisher extraction; acquire another exact snapshot')
    blocks = re.split(r'\n\s*\n', raw_text)
    title, paragraphs, sections, skip = 'Introduction', [], [], False
    headings = []
    for block in blocks:
        block = block.strip()
        heading = re.match(r'^(#{1,6})\s+(.+)$', block)
        if heading:
            if paragraphs and not skip:
                sections.append({'title': title, 'paragraphs': paragraphs})
            depth, label = len(heading.group(1)), heading.group(2)
            headings = [(d, h) for d, h in headings if d < depth]
            headings.append((depth, label))
            title, paragraphs = ' / '.join(h for _, h in headings), []
            skip = bool(re.search(r'references|resources|attributions|review questions|exercise|answers|licen[cs]e|footnotes|copyright|reprints|contact us|for more information|clinical trials|topics in the|multiple choice|fill.in.the.blank|critical thinking', title, re.I))
            continue
        if skip or block.startswith(('URL:', 'Published:', 'Figure ', 'Table ', '![', '>')):
            continue
        if block.startswith(('Textbox module not selected', 'Last Reviewed:')):
            continue
        if block == 'Menu' or block.startswith(('Share this page', 'Share this Page')):
            continue
        # Tables can lose header associations in extracted markdown; exclude them
        # from answer evidence until the whole table has a separately reviewed unit.
        if ' | ' in block or '\n---' in block:
            continue
        if re.match(r'^\[?(?:Previous|Next|Share This Book|Creative Commons)', block):
            continue
        if len(block) >= 10:
            paragraphs.append(block)
    if paragraphs and not skip:
        sections.append({'title': title, 'paragraphs': paragraphs})
    return sections


def build_release(documents, output, root=ROOT):
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Release exists; create a new version, never overwrite')
    records, sources, chunks, source_metadata = [], [], {}, {}
    identifiers, skipped = set(), []
    for doc in documents:
        validate_license(doc, root)
        if doc['id'] in identifiers:
            raise ValueError('Duplicate document ID')
        identifiers.add(doc['id'])
        basis = {'type': 'open_license' if doc['license'].startswith('CC-') else 'publisher_reuse', 'approved_host': urlsplit(doc['url']).hostname,
                 'license': doc['license'], 'license_url': doc['license_url'],
                 'snapshot_sha256': doc['raw_sha256'], 'clinical_review': False}
        checksums = []
        raw_path = snapshot_path(doc['raw_snapshot_path'], root)
        if doc.get('reviewed_units'):
            raw = raw_path.read_text(encoding='utf-8')
            sections = []
            for unit in doc['reviewed_units']:
                text = raw[unit['start']:unit['end']]
                if hashlib.sha256(text.encode('utf-8')).hexdigest() != unit['sha256']:
                    raise ValueError('Reviewed unit source-span hash mismatch')
                if unit.get('complete_paragraph') is not True or not unit.get('pdf_pages'):
                    raise ValueError('Reviewed unit needs confirmed coherent prose and PDF page context')
                sections.append({'title': unit['title'], 'paragraphs': [text.strip()],
                                 'reviewed_unit': unit})
        else:
            sections = extract_markdown(raw_path)
        for i, section in enumerate(sections):
            try:
                contexts = split_context(section['paragraphs'])
            except ValueError as exc:
                skipped.append({'source_id': doc['id'], 'section': section['title'], 'reason': str(exc)})
                continue
            for j, context in enumerate(contexts):
                record = Reference(source_id=doc['id'], title=doc['title'], url=doc['url'],
                    publisher=doc['publisher'], jurisdiction=doc['jurisdiction'],
                    source_date=doc.get('source_date'), retrieved_date=doc['retrieved_date'],
                    snapshot_id=output.name, section=section['title'], text=context['text'],
                    topics=doc['subjects'], keywords=sorted(set(re.findall(r'[a-z][a-z-]{3,}', section['title'].lower()))) or doc['subjects'],
                    source_type='teaching', section_id=f'section-{i + 1}-context-{j + 1}',
                    text_revision=doc['edition'], permission_basis=basis, clinical_review=False)
                record.chunk_id = record.stable_id()
                records.append(record)
                checksums.append(record.content_hash())
                chunks[record.chunk_id] = {'source_id': doc['id'], 'subjects': doc['subjects'],
                    'level': doc['level'], 'edition': doc['edition'], 'context': section['title'],
                    'section_id': record.section_id, 'complete_paragraph': True,
                    'paragraph_start': context['paragraph_start'], 'paragraph_end': context['paragraph_end'],
                    'context_overlap': 'one whole paragraph', 'license': doc['license'],
                    'clinical_review': False, 'coverage_status': 'relevant_material_not_competency_mastery',
                    'limitations': doc.get('limitations', []) + ['Figures and tables excluded; text may refer to them.']}
                if section.get('reviewed_unit'):
                    chunks[record.chunk_id]['reviewed_unit'] = section['reviewed_unit']
        if not checksums:
            raise ValueError(f"{doc['id']}: no usable source paragraphs")
        sources.append({**{k: doc.get(k) for k in ('title', 'url', 'publisher', 'jurisdiction', 'source_date', 'retrieved_date', 'terms', 'attribution', 'raw_snapshot_path', 'raw_sha256', 'license_snapshot_path', 'license_snapshot_sha256', 'license', 'license_url')},
            'source_id': doc['id'], 'version': doc['edition'], 'approval': 'developer_reviewed',
            'reviewer': 'Codex source/license and extraction review; no faculty review',
            'clinical_review': False, 'permission_basis': basis,
            'record_checksums': checksums, 'checksum_format': 'sha256-canonical-record-v2'})
        source_metadata[doc['id']] = {k: doc.get(k) for k in ('subjects', 'level', 'edition', 'attribution', 'acquisition_method', 'limitations', 'original_pdf_path', 'original_pdf_sha256')}
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='mbbs-staging-', dir=output.parent))
    (staging / 'records.jsonl').write_text('\n'.join(r.model_dump_json() for r in records) + '\n', encoding='utf-8')
    (staging / 'sources.yaml').write_text(yaml.safe_dump({'library_version': output.name, 'sources': sources}, sort_keys=False, allow_unicode=True), encoding='utf-8')
    metadata = {'schema_version': 1, 'chunks': chunks, 'sources': source_metadata,
                'clinical_review': False, 'skipped_sections': skipped,
                'faculty_review': 'pending', 'explanation_units': 'none; publisher original text only'}
    (staging / 'metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    manifest = {'version': output.name, 'library_version': output.name, 'schema_version': 1,
                'files': {name: sha256(staging / name) for name in ('records.jsonl', 'sources.yaml', 'metadata.json')},
                'records': len(records), 'sources': len(sources), 'clinical_review': False,
                'faculty_review': 'pending', 'subjects': dict(Counter(s for r in records for s in r.topics)),
                'licenses': sorted({doc['license'] for doc in documents}),
                'usage': 'Local noncommercial educational retrieval; retain source attribution, licenses and share-alike terms.',
                'coverage_claim': 'Partial source material. No verified NMC competency mastery or complete MBBS coverage.',
                'skipped_sections': skipped}
    (staging / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    staging.rename(output)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT / 'configs/mbbs_sources.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    manifest = build_release(json.loads(args.config.read_text(encoding='utf-8'))['documents'], args.output)
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
