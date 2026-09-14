from __future__ import annotations

import importlib.util
import json
from pathlib import Path

TASK_ID = 'KET_Data_S2B_S1ItemSemanticProjection'
STATUS = 'PASS_KET_DATA_S2B_S1_ITEM_SEMANTIC_PROJECTION'

class S2BValidationError(ValueError):
    pass


def _root(root=None) -> Path:
    return Path(root or Path(__file__).resolve().parents[1])


def _load_builder(root: Path):
    path = root/'builders'/'build_ket_data_s2b_item_semantic_projection.py'
    spec = importlib.util.spec_from_file_location('ket_s2b_builder', path)
    if not spec or not spec.loader:
        raise S2BValidationError('BUILDER_IMPORT_FAILED')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def validate(root=None):
    root = _root(root)
    builder = _load_builder(root)
    payload = builder.materialize(root)
    summary = payload['summary']
    errors = []
    expected = {
        's1_confirmed_item_count':1452,
        'canonical_exam_projected_count':1360,
        'practice_deferred_count':92,
        'task_profile_count':14,
        'reading_projected_count':480,
        'writing_projected_count':32,
        'listening_projected_count':400,
        'speaking_projected_count':448,
        'missing_task_profile_count':0,
        'missing_semantic_dimension_count':0,
        'generic_mcq_label_count':0,
        'item_identity_mutation_count':0,
        'broken_source_lineage_count':0,
        'broken_media_lineage_count':0,
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            errors.append(f'{key}:{summary.get(key)}!={value}')
    projected = payload['projected_items']
    deferred = payload['deferred_practice_items']
    all_rows = projected + deferred
    ids = [x['item_id'] for x in all_rows]
    if len(ids) != len(set(ids)):
        errors.append('DUPLICATE_ITEM_ID')
    if len(ids) != 1452:
        errors.append(f'ITEM_TOTAL:{len(ids)}')
    for row in all_rows:
        if not row.get('source_id') or not row.get('drive_file_id') or not row.get('page_ids'):
            errors.append(f'BROKEN_SOURCE_LINEAGE:{row.get("item_id")}')
            break
        if row.get('image_ids') is None or row.get('media_bits') is None:
            errors.append(f'BROKEN_MEDIA_LINEAGE:{row.get("item_id")}')
            break
    if any(x['projection_status'] != 'PROJECTED_FROM_APPROVED_S2A_PROFILE' for x in projected):
        errors.append('PROJECTED_STATUS_DRIFT')
    if any(x['projection_status'] != 'DEFERRED_REQUIRES_MULTIMODAL_SEMANTIC_ADMISSION' for x in deferred):
        errors.append('DEFERRED_STATUS_DRIFT')
    if any(x.get('task_profile_id') for x in deferred):
        errors.append('PRACTICE_FALSE_PROFILE_BINDING')
    if payload.get('contract_source') != 'KET_S2.txt':
        errors.append('CONTRACT_SOURCE')
    if errors:
        raise S2BValidationError('\n'.join(errors[:50]))
    return {
        'task_id':TASK_ID,
        'status':STATUS,
        **summary,
        'canonical_exam_projection':'PASS',
        'practice_projection':'DEFERRED_REQUIRES_MULTIMODAL_SEMANTIC_ADMISSION',
        's1_identity_preserved':True,
        's2a_taxonomy_preserved':True,
        's3_started':False,
    }


if __name__ == '__main__':
    print(json.dumps(validate(), ensure_ascii=False, indent=2))
