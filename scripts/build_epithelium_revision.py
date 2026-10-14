"""Build a source-bound correction release; preserve originals and previous releases."""
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.config import Settings  # noqa: E402 -- standalone script path bootstrap
from backend.app.services.retrieval import Reference  # noqa: E402
from backend.app.services.teaching import validate_explanation_units  # noqa: E402

VERSION = 'aster-teaching-epithelium-v1-2026-10-09'


def build():
    settings = Settings()
    source = settings.teaching_release_path
    target = source.parent / VERSION
    if target.exists():
        raise FileExistsError(target)
    manifest = json.loads((source/'manifest.json').read_text(encoding='utf-8'))
    records = {r.chunk_id:r for r in (Reference.model_validate_json(line) for line in
               (source/'records.jsonl').read_text(encoding='utf-8').splitlines() if line)}
    notes = json.loads(settings.teaching_explanations_path.read_text(encoding='utf-8'))
    metadata = json.loads((source/'metadata.json').read_text(encoding='utf-8'))
    general = 'chunk_12cd61937831159f068be326'
    locations = 'chunk_7ee5aacab2d64854c44fc5db'
    glands = 'chunk_3fbce5758f2b9605b90ec58c'
    sulcular = 'chunk_445b03532f31ab4dbd17806e'
    junctional = 'chunk_90bcc3daa650e0adaa18d9ec'
    definitions = [
        ('epithelium-overview', ['epithelium', 'epithelial tissue', 'epithelia'],
         'Epithelium is a tissue made of closely packed cells that cover body surfaces, line internal spaces and form glands. Think of it as the body’s covering and lining.\n\n'
         'Its job depends on where it is found. It can protect underlying tissues, absorb substances such as nutrients, release substances such as mucus, and allow exchange by diffusion. Different types are adapted to different jobs.\n\n'
         'The tissue is supported by a basement membrane. Epithelia are classified by cell shape—squamous (flat), cuboidal (cube-shaped) or columnar (tall)—and by their arrangement. Simple epithelium has one cell layer; stratified epithelium has several.',
         [general, locations, glands], ['Different types']),
        ('sulcular-epithelium-bounded', ['sulcular epithelium', 'crevicular epithelium'],
         'Sulcular epithelium is the lining on the gum side of the gingival sulcus—the narrow space between the gum and the tooth. It lines that space; it does not create it.\n\n'
         'Sulcular epithelium is not attached to the tooth surface. The attachment to the tooth is made by junctional epithelium, a different epithelial region.',
         [sulcular, junctional], ['not attached']),
    ]
    for identifier, topics, text, ids, qualifications in definitions:
        notes['units'].append({
            'id':identifier, 'topics':topics, 'match_mode':'exact_topic', 'text':text,
            'qualifications':qualifications, 'citation_ids':ids,
            'source_hashes':{key:records[key].content_hash() for key in ids},
            'reviewer':'Developer source comparison; cross-check of epithelial terminology against OpenStax Anatomy and Physiology 2e section 4.2 and published oral histology references',
            'review_status':'developer_reviewed', 'clinical_review':False,
            'review_scope':'Bounded summary of supported portions only; no medical faculty approval. Source concerns remain visible and the original text is unchanged.',
            'attribution':[{'publisher':records[key].publisher,'title':records[key].title,'url':records[key].url,
                            'license':records[key].permission_basis.get('license'),
                            'license_url':records[key].permission_basis.get('license_url')} for key in ids],
        })
    issues = {
        general: ('explanation_only', 'The original conflates mucous membrane with epithelium alone and describes transitional layering imprecisely. Only bounded, source-compared explanations are served; faculty review pending.'),
        glands: ('explanation_only', 'The original overgeneralises surface-cell death from avascularity. Only the supported gland/epithelial overview is used; faculty review pending.'),
        sulcular: ('explanation_only', 'The source says this lining creates the sulcus and uses ambiguous keratinization wording. The bounded explanation covers lining and attachment only; keratinization/permeability details require reviewed evidence.'),
        'chunk_05e61b1642dcc05016d971b8': ('exclude', 'The source describes pseudostratified epithelium as more than one layer. This conflicts with its single-layer definition; exclude pending faculty review.'),
        'chunk_e881e58dc6f32f05894b728a': ('exclude', 'This is a book-coverage notice rather than an explanation of the named tissues.'),
    }
    for key, (policy, reason) in issues.items():
        if any(f['chunk_id']==key for f in notes['source_review_flags']):
            raise ValueError('Review flag already exists: '+key)
        notes['source_review_flags'].append({'chunk_id':key,'content_sha256':records[key].content_hash(),
            'runtime_policy':policy,'reason':reason,'clinical_review':False})
    notes['release_version'] = VERSION
    notes['epithelium_revision'] = {'clinical_review':False,'faculty_review':'pending',
        'cross_checks':['https://openstax.org/books/anatomy-and-physiology-2e/pages/4-2-epithelial-tissue',
                        'https://pmc.ncbi.nlm.nih.gov/articles/PMC11595533/',
                        'https://pubmed.ncbi.nlm.nih.gov/341307/',
                        'https://pubmed.ncbi.nlm.nih.gov/6167706/'],
        'scope':'General definition and bounded sulcular anatomy. No new raw source imports or claims of comprehensive histology review.'}
    validate_explanation_units(notes['units'], records, metadata.get('chunks',metadata))
    target.mkdir()
    for name, expected in manifest['files'].items():
        original = (source/name).resolve()
        if not original.is_relative_to(source.resolve()) or hashlib.sha256(original.read_bytes()).hexdigest()!=expected:
            raise ValueError('Source manifest mismatch')
        shutil.copy2(original, target/name)
    (target/'explanations.json').write_text(json.dumps(notes,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    manifest['lineage'].append({'path':str(source),'version':manifest['version'],
        'manifest_sha256':hashlib.sha256((source/'manifest.json').read_bytes()).hexdigest()})
    manifest['version']=VERSION
    manifest['files']={name:hashlib.sha256((target/name).read_bytes()).hexdigest() for name in manifest['files']}
    (target/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'release':str(target),'explanations_sha256':manifest['files']['explanations.json'],
                      'units':len(notes['units']),'holds':len(notes['source_review_flags'])}))
    return target


if __name__=='__main__':
    build()
