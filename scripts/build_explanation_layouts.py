"""Bind reviewed presentation boundaries to complete, existing teaching notes.

No facts are generated or removed. Sentence selections were reviewed against
the current notes; new/changed notes fall back until their layout is checked.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.config import Settings  # noqa: E402 -- standalone script path bootstrap

# Zero-based sentences for the initial explanation; qualifications stay visible.
INTRO = {
    'osmosis':[0,2], 'diffusion':[0], 'homeostasis':[0,1],
    'pharmacokinetics':[0,1], 'pharmacodynamics':[0], 'filtration':[0,1],
    'reabsorption':[0,1,2], 'innate-immunity':[0,1,2,3], 'adaptive-immunity':[0,1,3],
    'immunity-comparison':[0,1,3], 'muscle-contraction':[0,1], 'crossbridge':[0,1],
    'glycolysis':[0], 'competitive-inhibition':[0], 'fertilization':[0],
    'cardiac-output':[0,3], 'epidemiology':[0], 'incidence-proportion':[0,2],
    'incidence-rate':[0], 'prevalence':[0,1,2], 'depression':[0,1,4],
    'bipolar':[0], 'schizophrenia':[0,3], 'genetic-consent':[0,3],
    'mds-pulp':[0,2], 'mds-periodontal-ligament':[0], 'mds-cementum':[0],
    'mds-junctional-epithelium':[0], 'mds-salivary-glands':[0],
    'mds-amelogenesis':[0,1,3], 'mds-he':[0,3], 'mds-ihc':[0,2],
    'mds-fixation':[0,2], 'mds-processing':[0], 'mds-candidiasis':[0,2],
    'mds-normal-distribution':[0,3], 'mds-confidence-interval':[0,1],
    'mds-mean':[0], 'mds-anova':[0], 'audit-free-bound-drug':[0,1],
    'audit-metabolism-lifespan':[0,1,4], 'epithelium-overview':[0,1],
    'sulcular-epithelium-bounded':[0,1],
}


def build():
    settings = Settings()
    document = json.loads(settings.teaching_explanations_path.read_text(encoding='utf-8'))
    plans=[]
    for unit in document['units']:
        selected = INTRO[unit['id']]
        original = unit['text']
        match = re.match(r'^(\[Research context:.*?\])\s*', original, re.S)
        context = match.group(1) if match else ''
        body = original[match.end():] if match else original
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', body.strip())
        if not selected or len(set(selected)) != len(selected) or max(selected) >= len(sentences):
            raise ValueError((unit['id'],len(sentences),selected))
        simple = ' '.join(sentences[i] for i in selected)
        deeper = ' '.join(sentence for i,sentence in enumerate(sentences) if i not in selected)
        plans.append({'unit_id':unit['id'], 'text_sha256':hashlib.sha256(original.encode()).hexdigest(),
            'citation_ids':unit['citation_ids'], 'simple':simple,'deeper':deeper,'context':context,
            'original':original, 'simple_sentence_indices':selected,
            'review_status':'developer_reviewed_presentation', 'clinical_review':False})
    output = ROOT/'configs/explanation_layouts.json'
    output.write_text(json.dumps({'version':'simple-to-deep-v1','clinical_review':False,
        'source_release':document['release_version'],'plans':plans},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'{len(plans)} complete notes mapped to simple/deeper sections; no medical facts added.')


if __name__=='__main__':
    build()
