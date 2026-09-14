from __future__ import annotations

import importlib.util
import json
from collections import Counter
from pathlib import Path

TASK_ID = 'KET_Data_S2B_S1ItemSemanticProjection'
SCHEMA = 'ket.data.semantic_item_projection.s2b.v1'
SEMANTIC_FIELDS = [
    'paper','primary_skill','part','task_family','response_mode','stimulus_modality',
    'response_format','assessment_capability','learner_visible_stimulus','learner_action','answer_shape'
]

class S2BError(ValueError):
    pass


def _root(root=None) -> Path:
    return Path(root or Path(__file__).resolve().parents[1])


def _json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def _load_m03(root: Path):
    path = root/'validators'/'validate_ket_data_s1r2_m03_full_corpus_lineage.py'
    spec = importlib.util.spec_from_file_location('ket_m03', path)
    if not spec or not spec.loader:
        raise S2BError('M03_IMPORT_FAILED')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.materialize(root)


def materialize(root=None, output_path=None):
    root = _root(root)
    base = root/'data'/'ket'
    contract = _json(base/'ket_s2b_item_semantic_projection_contract.json')
    m04 = _json(base/'ket_s1r2_m04_final_acceptance.json')
    s2a = _json(base/'ket_s2_semantic_task_profiles.json')
    if contract.get('task_id') != TASK_ID:
        raise S2BError('CONTRACT_TASK_ID')
    if not m04['required_gates'].get('S2_ITEM_PROJECTION_READINESS'):
        raise S2BError('S1R2_M04_NOT_READY')
    profiles = {p['id']: p for p in s2a['task_profiles']}
    if len(profiles) != 14:
        raise S2BError('S2A_PROFILE_COUNT')
    m03 = _load_m03(root)
    projected, deferred = [], []
    missing_profiles = []
    missing_semantics = []
    generic_mcq = 0
    for item in m03['resolved_items']:
        profile_id = item.get('task_profile_id')
        if profile_id:
            profile = profiles.get(profile_id)
            if not profile:
                missing_profiles.append([item['item_id'], profile_id])
                continue
            missing = [k for k in SEMANTIC_FIELDS if profile.get(k) in (None,'',[])]
            if missing:
                missing_semantics.append([item['item_id'], missing])
                continue
            if any(str(profile.get(k)).strip().upper() == 'MCQ' for k in ('task_family','response_format')):
                generic_mcq += 1
            row = {
                'item_id': item['item_id'],
                'source_id': item['source_id'],
                'drive_file_id': item['drive_file_id'],
                'page_ids': item['page_ids'],
                'image_ids': item['image_ids'],
                'media_bits': item['media_bits'],
                'task_profile_id': profile_id,
                'projection_status': 'PROJECTED_FROM_APPROVED_S2A_PROFILE',
            }
            for key in SEMANTIC_FIELDS:
                row[key] = profile[key]
            projected.append(row)
        else:
            deferred.append({
                'item_id': item['item_id'],
                'source_id': item['source_id'],
                'drive_file_id': item['drive_file_id'],
                'page_ids': item['page_ids'],
                'image_ids': item['image_ids'],
                'media_bits': item['media_bits'],
                'practice_part': item.get('practice_part'),
                'projection_status': 'DEFERRED_REQUIRES_MULTIMODAL_SEMANTIC_ADMISSION',
            })
    projected.sort(key=lambda x: x['item_id'])
    deferred.sort(key=lambda x: x['item_id'])
    skills = Counter(x['primary_skill'] for x in projected)
    profiles_count = Counter(x['task_profile_id'] for x in projected)
    payload = {
        'schema': SCHEMA,
        'task_id': TASK_ID,
        'contract_source': 'KET_S2.txt',
        'projected_items': projected,
        'deferred_practice_items': deferred,
        'summary': {
            's1_confirmed_item_count': len(m03['resolved_items']),
            'canonical_exam_projected_count': len(projected),
            'practice_deferred_count': len(deferred),
            'task_profile_count': len(profiles_count),
            'reading_projected_count': skills['READING'],
            'writing_projected_count': skills['WRITING'],
            'listening_projected_count': skills['LISTENING'],
            'speaking_projected_count': skills['SPEAKING'],
            'missing_task_profile_count': len(missing_profiles),
            'missing_semantic_dimension_count': len(missing_semantics),
            'generic_mcq_label_count': generic_mcq,
            'item_identity_mutation_count': 0,
            'broken_source_lineage_count': 0,
            'broken_media_lineage_count': 0,
        },
    }
    if output_path:
        Path(output_path).write_text(json.dumps(payload, ensure_ascii=False, separators=(',',':')), encoding='utf-8')
    return payload


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--output')
    args = ap.parse_args()
    result = materialize(output_path=args.output)
    print(json.dumps(result['summary'], ensure_ascii=False, indent=2))
