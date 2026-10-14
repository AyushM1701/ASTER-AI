"""Developer reference-agreement benchmark; never clinical validation."""

import argparse
import hashlib
import json
import math
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def normalize(text):
    return re.sub(r'\s+', ' ', text).strip().casefold()


def as_dict(value):
    return value.model_dump() if hasattr(value, 'model_dump') else value


def validate_cases(cases):
    seen = set()
    for case in cases:
        if case['id'] in seen:
            raise ValueError('Duplicate benchmark case ID')
        seen.add(case['id'])
        if case['expected_status'] == 'ok':
            if not case.get('required_facts') or not case.get('expected_source_ids'):
                raise ValueError('Supported cases require reference facts and sources')
            for fact in case['required_facts']:
                if not fact.get('id') or not fact.get('any_of') or any(not normalize(x) for x in fact['any_of']):
                    raise ValueError('Empty required reference facts')


def score_case(case, retrieved, answer, records, validated_units=()):
    """Exact phrase facts measure bounded agreement, not semantic correctness.

    Units must come from TeachingStore.units after its hash/review validation.
    A source ID or keyword overlap alone cannot support an answer claim.
    """
    references = {key: as_dict(value) for key, value in records.items()}
    expected = set(case.get('expected_source_ids', []))
    retrieved_sources = {as_dict(row)['source_id'] for row in retrieved}
    claims = (answer or {}).get('claims', [])
    citations = (answer or {}).get('citations', [])
    citation_ids = [row.get('chunk_id') for row in citations]
    status = (answer or {}).get('status', 'not_handled')
    text = normalize(' '.join(claim.get('text', '') for claim in claims))
    facts = case.get('required_facts', [])
    matched = [fact['id'] for fact in facts if any(normalize(phrase) in text for phrase in fact['any_of'])]
    contradictions = [phrase for phrase in case.get('forbidden_contradictions', []) if normalize(phrase) in text]
    supports = []
    citation_checks = []
    for claim in claims:
        ids = claim.get('citation_ids', [])
        valid_ids = bool(ids) and all(key in references and key in citation_ids for key in ids)
        citation_checks.append(valid_ids)
        claim_text = normalize(claim.get('text', ''))
        source_support = bool(claim_text) and valid_ids and any(claim_text in normalize(references[key]['text']) for key in ids)
        unit_support = valid_ids and any(claim_text == normalize(unit['text']) and set(ids) == set(unit['citation_ids']) for unit in validated_units)
        supports.append({'citation_ids': ids, 'supported': source_support or unit_support,
                         'basis': 'exact_source_text' if source_support else 'validated_developer_unit' if unit_support else 'unsupported'})
    # Verify the citation excerpt where supplied, rather than trusting an ID.
    envelope_valid = bool(citations) and len(citation_ids) == len(set(citation_ids)) and all(
        row.get('chunk_id') in references and ('excerpt' not in row or normalize(row['excerpt']) == normalize(references[row['chunk_id']]['text']))
        for row in citations
    )
    claim_ids = {key for claim in claims for key in claim.get('citation_ids', [])}
    integrity = bool(claims) and envelope_valid and all(citation_checks) and claim_ids == set(citation_ids)
    completeness = len(matched) / len(facts) if facts else None
    support_rate = sum(row['supported'] for row in supports) / len(supports) if supports else None
    agreement = (bool(claims) and completeness == 1 and not contradictions and integrity and support_rate == 1
                 and status == case['expected_status']) if case['expected_status'] == 'ok' else None
    return {'id': case['id'], 'question': case['question'], 'subject': case.get('subject'),
            'question_type': case.get('question_type'), 'expected_status': case['expected_status'], 'actual_status': status,
            'status_pass': status == case['expected_status'],
            'retrieval_source_hit': bool(expected & retrieved_sources) if expected else None,
            'retrieval_expected_source_fraction': len(expected & retrieved_sources) / len(expected) if expected else None,
            'retrieved_source_ids': sorted(retrieved_sources), 'fact_completeness': completeness,
            'matched_fact_ids': matched, 'missing_fact_ids': [f['id'] for f in facts if f['id'] not in matched],
            'contradictions': contradictions, 'citation_integrity_pass': integrity,
            'claim_support_rate': support_rate, 'claim_support': supports,
            'reference_agreement_pass': agreement, 'clinical_correctness': None, 'faculty_review': 'pending'}


def write_immutable(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write('\n')


def build_material_mapping(store, cases, competencies):
    """Queue lexical candidates and developer-inspected partial associations.

    Ranking only nominates material for review. Every competency, even those
    without candidates, stays in the explicit faculty review queue.
    """
    records = {as_dict(row)['chunk_id']: as_dict(row) for row in store.records}
    active = {row['code']: row for row in competencies if row.get('active', True)}
    # This independent sparse ranker nominates source paragraphs for faculty
    # inspection. It is deliberately separate from runtime answer performance.
    stop = set('describe discuss demonstrate enumerate explain identify define various common principles types features structure function functions based given and the of in to a an for with or on its their by'.split())
    def tokens(text):
        return set(re.findall(r'[a-z]{3,}', text.casefold())) - stop
    words = {key: tokens(row['text'] + ' ' + row.get('section', '')) for key, row in records.items()}
    inverted = defaultdict(set)
    for key, values in words.items():
        for word in values:
            inverted[word].add(key)
    manual = {}
    for case in cases:
        for association in case.get('manual_material_associations', []):
            code = association['competency_code']
            if code not in active or not association.get('contribution_scope') or not case.get('reference_evidence'):
                raise ValueError('Manual mapping requires active competency and inspected evidence')
            for evidence in case['reference_evidence']:
                record = records.get(evidence['chunk_id'])
                if not record or normalize(evidence['excerpt']) not in normalize(record['text']):
                    raise ValueError('Manual mapping source evidence changed')
                key = (code, evidence['chunk_id'])
                manual[key] = {'chunk_id': evidence['chunk_id'], 'source_id': record['source_id'],
                               'section': record.get('section'), 'url': record.get('url'),
                               'evidence_excerpt': evidence['excerpt'], 'contribution_scope': association['contribution_scope'],
                               'review_type': 'developer_material_mapping', 'clinical_correctness': None,
                               'faculty_verified': None, 'reviewer': 'developer_reference_paragraph_review'}
    queue = []
    for code, competency in active.items():
        query = tokens(competency['text'])
        hits = set().union(*(inverted[word] for word in query)) if query else set()
        ranked = []
        for key in hits:
            overlap = query & words[key]
            if len(overlap) < min(2, len(query)):
                continue
            score = sum(math.log(1 + len(records) / (1 + len(inverted[word]))) for word in overlap)
            score /= math.sqrt(max(len(words[key]), 1))
            ranked.append((score, key))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        candidates = []
        sources = set()
        for score, key in ranked:
            record = records[key]
            if record['source_id'] in sources:
                continue
            sources.add(record['source_id'])
            candidates.append({'rank': len(candidates) + 1, 'chunk_id': record['chunk_id'],
                               'source_id': record['source_id'], 'section': record.get('section'),
                               'nomination_score': round(score, 6),
                               'selection_basis': 'independent_sparse_lexical_nomination_only', 'faculty_verified': None})
            if len(candidates) == 3:
                break
        associations = [value for (key, _), value in manual.items() if key == code]
        queue.append({'code': code, 'subject': competency['subject'], 'competency_text': competency['text'],
                      'curriculum_page': competency['page'], 'candidate_records': candidates,
                      'manual_associations': associations,
                      'status': 'related_material_pending_review' if candidates or associations else 'material_gap_pending_review',
                      'clinical_correctness': None, 'faculty_review': {
                          'status': 'pending', 'reviewer_name': None, 'reviewer_qualification': None,
                          'review_date': None, 'decision': None, 'decision_reason': None,
                          'verified_competency_elements': None, 'missing_elements': None,
                          'currency_check': None, 'indian_context_check': None}})
    return {'schema_version': 1, 'release_version': store.version, 'mapping_scope': 'related_material_candidate_review_queue',
            'candidate_algorithm': 'IDF-weighted shared tokens normalized by square root of source token count; minimum two shared terms; top three distinct sources',
            'clinical_correctness': None, 'faculty_review': 'not_performed',
            'active_competencies': len(queue), 'manual_competencies': len({key[0] for key in manual}),
            'manual_associations': len(manual), 'candidate_competencies': sum(bool(row['candidate_records']) for row in queue),
            'verified_competencies': None,
            'limitations': ['Top source matches are retrieval nominations; they do not establish competency coverage.',
                            'Manual associations support only the stated contribution scope, not the complete competency.',
                            'No faculty review, skill demonstration or clinical examination has been performed.'],
            'competencies': queue}


def aggregate(results):
    metrics = ['status_pass', 'retrieval_source_hit', 'retrieval_expected_source_fraction', 'fact_completeness',
               'citation_integrity_pass', 'claim_support_rate', 'reference_agreement_pass']
    summary = {}
    for metric in metrics:
        eligible = [row[metric] for row in results if row[metric] is not None and
                    (metric != 'citation_integrity_pass' or row['expected_status'] == 'ok')]
        summary[metric] = {'mean': sum(eligible) / len(eligible) if eligible else None, 'denominator': len(eligible)}
    return summary


def evaluate(store, cases):
    validate_cases(cases)
    if store.error:
        raise ValueError('Teaching release failed validation: ' + store.error)
    records = {row.chunk_id: row for row in store.records}
    for case in cases:
        for evidence in case.get('reference_evidence', []):
            row = records.get(evidence['chunk_id'])
            if row is None or row.content_hash() != evidence['content_sha256'] or normalize(evidence['excerpt']) not in normalize(row.text):
                raise ValueError('Benchmark reference evidence changed: ' + case['id'])
    results = []
    for case in cases:
        started = time.perf_counter()
        retrieved = store.search(case['question'])
        answer = store.answer(case['question'])
        result = score_case(case, retrieved, answer, records, store.units)
        result['elapsed_seconds'] = round(time.perf_counter() - started, 6)
        result['answer'] = answer
        results.append(result)
    return {'schema_version': 1, 'benchmark_scope': 'developer_bounded_reference_agreement',
            'clinical_correctness': None, 'faculty_review': 'not_performed', 'teaching': store.manifest(),
            'cases': len(results), 'subjects': dict(Counter(c.get('subject', 'boundary') for c in cases)),
            'question_types': dict(Counter(c.get('question_type', 'unspecified') for c in cases)),
            'metrics': aggregate(results), 'by_question_type': {
                kind: aggregate([r for r in results if r['question_type'] == kind]) for kind in sorted({r['question_type'] for r in results})},
            'limitations': ['Exact reference phrases do not measure clinical correctness or educational mastery.',
                            'Developer-authored variants are not an independent medical faculty examination.',
                            'TeachingStore boundary non-handling is tested; complete application routing is outside this benchmark.',
                            'MCQ and fictional case tests assess supported facts, not a complete exam answer or diagnostic competence.'],
            'results': results}


def main():
    from backend.app.config import Settings
    from backend.app.services.teaching import TeachingStore

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release', type=Path, required=True)
    parser.add_argument('--index', type=Path, required=True)
    parser.add_argument('--backend', choices=['lexical', 'hybrid'], default='lexical')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--dataset', type=Path, default=ROOT / 'data/evaluation/mbbs_v1.jsonl')
    parser.add_argument('--explanations', type=Path)
    parser.add_argument('--explanations-sha256')
    parser.add_argument('--mapping-output', type=Path)
    parser.add_argument('--curriculum', type=Path, default=ROOT / 'data/references/mbbs/raw/curriculum-competencies.jsonl')
    args = parser.parse_args()
    if args.backend == 'hybrid':
        import torch

        torch.set_num_threads(2)
    if bool(args.explanations) != bool(args.explanations_sha256):
        raise ValueError('Explicit explanations require both a path and pinned SHA-256')
    if args.output.exists():
        raise FileExistsError('Benchmark output must be fresh: ' + str(args.output))
    if args.mapping_output and args.mapping_output.exists():
        raise FileExistsError('Mapping output must be fresh: ' + str(args.mapping_output))
    overrides = {}
    if args.explanations:
        if not args.explanations_sha256:
            raise ValueError('Explicit explanations require a pinned SHA-256')
        overrides = {'teaching_explanations_path': args.explanations, 'teaching_explanations_sha256': args.explanations_sha256}
    settings = Settings(enable_teaching=True, teaching_release_path=args.release, teaching_index_path=args.index,
                        teaching_backend=args.backend, **overrides)
    store = TeachingStore(settings)
    try:
        runtime_files = ['scripts/evaluate_mbbs.py', 'backend/app/services/teaching.py',
                         'backend/app/services/policy.py', 'backend/app/services/retrieval.py',
                         'backend/app/adapters/embeddings.py']
        runtime_start = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in runtime_files}
        cases = [json.loads(line) for line in args.dataset.read_text(encoding='utf-8').splitlines() if line.strip()]
        report = evaluate(store, cases)
        report['timestamp_utc'] = datetime.now(timezone.utc).isoformat()
        report['inputs'] = {'dataset': str(args.dataset.resolve()), 'dataset_sha256': hashlib.sha256(args.dataset.read_bytes()).hexdigest(),
                            'release': str(args.release.resolve()), 'manifest_sha256': hashlib.sha256((args.release / 'manifest.json').read_bytes()).hexdigest(),
                            'index': str(args.index.resolve()), 'backend': args.backend,
                            'explanations_path': str(settings.teaching_explanations_path.resolve()),
                            'explanations_sha256': settings.teaching_explanations_sha256,
                            'index_manifest_sha256': hashlib.sha256((args.index / 'manifest.json').read_bytes()).hexdigest() if args.backend == 'hybrid' else None,
                            'runtime_files_sha256': runtime_start,
                            'runtime_files_unchanged_during_evaluation': all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == value for name, value in runtime_start.items())}
        write_immutable(args.output, report)
        if args.mapping_output:
            competencies = [json.loads(line) for line in args.curriculum.read_text(encoding='utf-8').splitlines()]
            mapping = build_material_mapping(store, cases, competencies)
            mapping['input_hashes'] = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in
                                      [('curriculum', args.curriculum), ('dataset', args.dataset), ('release_manifest', args.release / 'manifest.json')]}
            write_immutable(args.mapping_output, mapping)
        print(json.dumps({'output': str(args.output), 'cases': report['cases'], 'metrics': report['metrics']}))
    finally:
        store.close()


if __name__ == '__main__':
    main()
