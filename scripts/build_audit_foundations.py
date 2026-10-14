"""Build immutable foundation teaching components from reviewed publisher snapshots.

Exact publisher prose only. Tables, media, exercises and suspect paragraphs are
excluded with recorded reasons. Educational coverage never means faculty approval.
"""

import argparse
import hashlib
import json
import re
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.services.retrieval import Reference  # noqa: E402
from scripts.build_mbbs_library import (  # noqa: E402
    sha256,
    snapshot_path,
    split_context,
    validate_license,
)

LICENSE_NAMES = {
    'CC-BY-SA-4.0': 'Creative Commons Attribution-ShareAlike 4.0 International License',
    'CC-BY-NC-SA-4.0': 'Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License',
    'CC-BY-NC-4.0': 'Creative Commons Attribution-NonCommercial 4.0 International License',
    'CC-BY-4.0': 'Creative Commons Attribution 4.0 International License',
}
SKIP_HEADING = re.compile(r'review questions|critical thinking|check your understanding|learning objectives|chapter review|glossary|references|resources?|clinical focus|eye on ethics|micro connections|case in point|ABO Transfusion Protocols|license|copyright|summary|multiple choice|fill.in.the.blank|key concepts|footnotes', re.I)


def validate_document(doc, root=ROOT):
    validate_license(doc, root)
    for key in ('authors', 'scope', 'limitations', 'source_date'):
        if not doc.get(key):
            raise ValueError(f'Missing foundation provenance: {key}')
    evidence = snapshot_path(doc['license_snapshot_path'], root).read_text(encoding='utf-8')
    if LICENSE_NAMES.get(doc['license'], 'INVALID LICENSE') not in evidence:
        raise ValueError('Publisher license statement absent from rights snapshot')
    if doc.get('scope') not in {'foundation', 'specialty_review'}:
        raise ValueError('Unsupported educational scope')


def extract_sections(path, doc):
    raw = Path(path).read_text(encoding='utf-8')
    if '\x00' in raw or raw.count('\ufffd') > max(3, len(raw) * .002):
        raise ValueError('Corrupt publisher extraction')
    sections, excluded, paragraphs, headings = [], [], [], []
    title, skip = doc['title'], False

    def flush():
        if paragraphs:
            sections.append({'title': title, 'paragraphs': paragraphs.copy()})
            paragraphs.clear()

    for block in re.split(r'\n\s*\n', raw):
        block = block.strip()
        if not block:
            continue
        heading = re.match(r'^(#{1,6})\s+(.+)$', block)
        if heading:
            flush()
            depth, label = len(heading[1]), heading[2]
            headings = [(d, h) for d, h in headings if d < depth] + [(depth, label)]
            title = ' / '.join(h for _, h in headings)
            skip = bool(SKIP_HEADING.search(title))
            continue
        reason = None
        if skip:
            reason = ('oversimplified whole-blood/universal-recipient guidance; transfusion protocol excluded' if 'ABO Transfusion Protocols' in title
                      else 'assessment, glossary, historical case, media or nonteaching section')
        elif block.startswith(('URL:', 'Published:', 'By the end', '- ', '* ', 'Figure ', 'Table ', '![', 'Reveal ', 'Share This Book', 'Textbox module', 'Chapter Review', 'Glossary')):
            reason = 'navigation, objective, list, caption or table heading'
        elif '|' in block or re.search(r'^[-:]{3,}', block, re.M):
            reason = 'table or unsupported extracted object'
        elif 'insoluble fibrinogen' in block.lower() or 'soluble fibrin protein' in block.lower():
            reason = 'source reverses fibrinogen/fibrin solubility'
        elif 'dopamine molecule binds' in block.lower() and 'channel' in block.lower():
            reason = 'source incorrectly presents dopamine receptor as a directly gated ion channel'
        elif 'clinically important' in block.lower() and re.search(r'only (?:one|rhd)', block, re.I):
            reason = 'source incorrectly limits clinically important Rh antigens to D'
        elif 'tested for rh antibodies' in block.lower():
            reason = 'source confuses Rh antigen typing with antibody screening'
        elif 'both are glycoproteins' in block.lower() or 'both abo antigens are glycoproteins' in block.lower():
            reason = 'source misidentifies ABO glycan epitopes as exclusively glycoproteins'
        elif 'galea = “apple”' in block or 'corrugator supercilli' in block:
            reason = 'suspect etymology or oversimplified brow action; specialist verification pending'
        elif 'Streptococcus enters the bloodstream' in block and 'atherosclerosis' in block:
            reason = 'source asserts atherosclerosis causation beyond established association'
        elif len(block) < 50 or not re.search(r'[.!?][”\"\u2019\u201d)]?\s*$', block):
            reason = 'fragment, duplicate title, formula or extraction artifact'
        if reason:
            excluded.append({'source_id': doc['id'], 'section': title, 'reason': reason,
                             'paragraph_sha256': hashlib.sha256(block.encode()).hexdigest(), 'preview': block[:160]})
        else:
            paragraphs.append(block)
    flush()
    return sections, excluded


def build_release(documents, output, root=ROOT):
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Component exists; choose a new immutable version')
    records, sources, metadata_sources, chunks, exclusions, ids = [], [], {}, {}, [], set()
    for doc in documents:
        validate_document(doc, root)
        if doc['id'] in ids:
            raise ValueError('Duplicate foundation source ID')
        ids.add(doc['id'])
        sections, excluded = extract_sections(snapshot_path(doc['raw_snapshot_path'], root), doc)
        exclusions.extend(excluded)
        basis = {'type': 'open_license', 'approved_host': urlsplit(doc['url']).hostname,
                 'license': doc['license'], 'license_url': doc['license_url'],
                 'snapshot_sha256': doc['raw_sha256'], 'clinical_review': False}
        checksums = []
        for i, section in enumerate(sections):
            try:
                contexts = split_context(section['paragraphs'])
            except ValueError as exc:
                exclusions.append({'source_id': doc['id'], 'section': section['title'], 'reason': str(exc)})
                continue
            for j, context in enumerate(contexts):
                record = Reference(source_id=doc['id'], title=doc['title'], url=doc['url'], publisher=doc['publisher'],
                    jurisdiction=doc['jurisdiction'], source_date=doc['source_date'], retrieved_date=doc['retrieved_date'],
                    snapshot_id=output.name, section=section['title'], text=context['text'], topics=doc['subjects'],
                    keywords=sorted(set(re.findall(r'[a-z][a-z-]{3,}', section['title'].lower()))) or doc['subjects'],
                    source_type='teaching', section_id=f'section-{i+1}-context-{j+1}', text_revision=doc['edition'],
                    permission_basis=basis, clinical_review=False)
                record.chunk_id = record.stable_id()
                records.append(record)
                checksums.append(record.content_hash())
                chunks[record.chunk_id] = {'source_id': doc['id'], 'subjects': doc['subjects'], 'level': doc['level'],
                    'scope': doc['scope'], 'edition': doc['edition'], 'context': section['title'], 'section_id': record.section_id,
                    'complete_paragraph': True, 'paragraph_start': context['paragraph_start'], 'paragraph_end': context['paragraph_end'],
                    'context_overlap': 'one whole paragraph', 'license': doc['license'], 'clinical_review': False,
                    'coverage_status': 'relevant_material_not_competency_mastery', 'limitations': doc['limitations']}
        if not checksums:
            raise ValueError(f"{doc['id']}: no coherent foundation paragraphs")
        sources.append({**{k: doc[k] for k in ('title', 'url', 'publisher', 'jurisdiction', 'source_date', 'retrieved_date', 'terms', 'attribution', 'raw_snapshot_path', 'raw_sha256', 'license_snapshot_path', 'license_snapshot_sha256', 'license', 'license_url')},
            'source_id': doc['id'], 'version': doc['edition'], 'approval': 'developer_reviewed', 'reviewer': 'Codex rights/extraction review; faculty review pending',
            'clinical_review': False, 'permission_basis': basis, 'record_checksums': checksums, 'checksum_format': 'sha256-canonical-record-v2'})
        metadata_sources[doc['id']] = {k: doc[k] for k in ('authors', 'subjects', 'level', 'scope', 'edition', 'attribution', 'limitations')}
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='audit-foundation-staging-', dir=output.parent))
    (staging/'records.jsonl').write_text('\n'.join(r.model_dump_json() for r in records)+'\n', encoding='utf-8')
    (staging/'sources.yaml').write_text(yaml.safe_dump({'library_version': output.name, 'sources': sources}, sort_keys=False, allow_unicode=True), encoding='utf-8')
    (staging/'metadata.json').write_text(json.dumps({'schema_version': 1, 'sources': metadata_sources, 'chunks': chunks, 'exclusions': exclusions,
        'clinical_review': False, 'faculty_review': 'pending', 'explanation_units': 'publisher original prose only'}, ensure_ascii=False, indent=2), encoding='utf-8')
    manifest = {'version': output.name, 'library_version': output.name, 'schema_version': 1,
        'files': {n: sha256(staging/n) for n in ('records.jsonl', 'sources.yaml', 'metadata.json')}, 'records': len(records), 'sources': len(sources),
        'clinical_review': False, 'faculty_review': 'pending', 'subjects': dict(Counter(s for r in records for s in r.topics)),
        'licenses': sorted({d['license'] for d in documents}), 'usage': 'Local noncommercial educational retrieval; attribution and share-alike terms retained.',
        'coverage_claim': 'Partial foundation material; no verified curriculum mastery, practical competence or complete MBBS/MDS coverage.',
        'excluded_paragraphs_or_sections': len(exclusions)}
    (staging/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    staging.rename(output)
    return manifest


def build_reviews(documents, output, root=ROOT):
    """Narrative reviews remain labelled research; case reports cannot be foundations."""
    from scripts.build_mds_research import build_release as research_release
    for doc in documents:
        article = ET.parse(snapshot_path(doc['raw_snapshot_path'], root)).getroot()
        if article.get('article-type') != 'review-article' or doc.get('scope') != 'specialty_review':
            raise ValueError('Specialty foundation source must be a verified review article')
    return research_release(documents, output, root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT/'configs/audit_foundation_sources.json')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--kind', choices=['foundation', 'reviews'], default='foundation')
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding='utf-8'))
    builder = build_release if args.kind == 'foundation' else build_reviews
    print(json.dumps(builder(config['documents' if args.kind == 'foundation' else 'reviews'], args.output), indent=2))


if __name__ == '__main__':
    main()
