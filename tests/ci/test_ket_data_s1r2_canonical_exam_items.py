from __future__ import annotations
import base64
import json
import lzma
import re
from collections import Counter, defaultdict
from pathlib import Path

ITEM_RE = re.compile(r'^KET_ITEM_(\d{6})$')
REGION_RE = re.compile(r'^KET_CANDREG_(\d{6})$')
EXPECTED_PROFILE_COUNTS = {
    'KET_S2_TASK_001': 6,
    'KET_S2_TASK_002': 7,
    'KET_S2_TASK_003': 5,
    'KET_S2_TASK_004': 6,
    'KET_S2_TASK_005': 6,
    'KET_S2_TASK_006': 1,
    'KET_S2_TASK_007': 1,
    'KET_S2_TASK_008': 5,
    'KET_S2_TASK_009': 5,
    'KET_S2_TASK_010': 5,
    'KET_S2_TASK_011': 5,
    'KET_S2_TASK_012': 5,
    'KET_S2_TASK_013': 16,
    'KET_S2_TASK_014': 12,
}


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load(path: str):
    p = _root() / path
    if path.endswith('.xz.b64'):
        raw = lzma.decompress(base64.b64decode(p.read_text(encoding='ascii').strip()), format=lzma.FORMAT_XZ)
        return json.loads(raw)
    return json.loads(p.read_text(encoding='utf-8'))


def _idnum(s: str, rx: re.Pattern[str]) -> int:
    m = rx.fullmatch(s)
    assert m, s
    return int(m.group(1))


def test_s1r2_m02_canonical_exam_item_admission_and_completeness():
    state = _load('data/ket/ket_s1r2_item_identity_state.json')
    m02 = _load('data/ket/ket_s1r2_canonical_exam_items.json.xz.b64')
    s2 = _load('data/ket/ket_s2_semantic_task_profiles.json')

    assert m02['schema'] == 'ket.data.s1r2.canonical_exam_items.m02.v1'
    assert m02['task_id'] == 'KET_Data_S1R2_M02_CanonicalExamItemAdmissionAndCompleteness'
    assert m02['contract_source'] == 'KET_S1_revised.txt'
    assert m02['contract_sha256'] == state['contract_sha256']
    assert m02['predecessor_identity_state'] == 'data/ket/ket_s1r2_item_identity_state.json'
    assert m02['scope']['canonical_exam_source_id'] == 'KET_SRC_000004'
    assert m02['scope']['canonical_exam_instance'] == 'TEST_1'
    assert m02['scope']['full_corpus_completeness_evaluated'] is False
    assert m02['scope']['s2_semantic_projection_materialized'] is False
    assert m02['scope']['s3_started'] is False

    legacy = m02['legacy_identity_policy']
    assert legacy['existing_range'] == ['KET_ITEM_000001', 'KET_ITEM_000629']
    assert legacy['renumbered'] is False
    assert legacy['rebound'] is False
    assert legacy['reused'] is False

    items = m02['items']
    assert len(items) == 85
    ids = [_idnum(x['item_id'], ITEM_RE) for x in items]
    assert ids == list(range(630, 715))
    assert len(set(ids)) == 85
    assert min(ids) > 629
    region_ids = [_idnum(x['question_candidate_region_id'], REGION_RE) for x in items]
    assert region_ids == list(range(1, 86))

    assert all(x['identity_status'] == 'CONFIRMED_CANONICAL_ITEM' for x in items)
    assert all(x['source_id'] == 'KET_SRC_000004' for x in items)
    assert all(x['geometry_status'] == 'BOUNDARY_IDENTITY_ADMITTED_BBOX_DEFERRED_TO_M03' for x in items)
    assert all(x['image_link_status'] == 'DEFERRED_TO_M03' for x in items)
    assert all(x['media_link_status'] == 'DEFERRED_TO_M03' for x in items)

    profile_counts = Counter(x['task_profile_id'] for x in items)
    assert dict(profile_counts) == EXPECTED_PROFILE_COUNTS
    s2_profiles = {x['id']: x for x in s2['task_profiles']}
    assert set(profile_counts) == set(s2_profiles)

    by_paper = Counter(x['paper'] for x in items)
    assert by_paper == Counter({'READING_AND_WRITING': 32, 'LISTENING': 25, 'SPEAKING': 28})

    rw = [x for x in items if x['paper'] == 'READING_AND_WRITING']
    assert [int(x['source_local_item_label']) for x in rw] == list(range(1, 33))
    listening = [x for x in items if x['paper'] == 'LISTENING']
    assert [int(x['source_local_item_label']) for x in listening] == list(range(1, 26))
    speaking = [x for x in items if x['paper'] == 'SPEAKING']
    assert len({x['source_local_item_label'] for x in speaking}) == 28

    item_pages_by_profile = defaultdict(set)
    for x in items:
        item_pages_by_profile[x['task_profile_id']].update(x['page_ids'])
    for pid, profile in s2_profiles.items():
        evidence = profile['standard_evidence']
        expected_pages = {f"KET_SRC_000004_P{p:03d}" for p in evidence['task_pages']}
        if 'visual_material_pages' in evidence:
            expected_pages |= {f"KET_SRC_000004_P{p:03d}" for p in evidence['visual_material_pages']}
        assert expected_pages <= item_pages_by_profile[pid], (pid, expected_pages, item_pages_by_profile[pid])

    gates = m02['gates']
    assert gates['canonical_exam_item_identity_complete'] is True
    assert gates['canonical_exam_missing_item_count'] == 0
    assert gates['canonical_exam_unresolved_item_count'] == 0
    assert gates['canonical_exam_duplicate_item_id_count'] == 0
    assert gates['legacy_id_reuse_count'] == 0
    assert gates['answer_key_reconciliation'] == 'PASS_FOR_NUMBERED_READING_WRITING_AND_LISTENING'
    assert gates['speaking_prompt_completeness'] == 'PASS_FOR_TEST1_SOURCE_PROMPTS'
    assert gates['geometry_lineage_status'] == 'DEFERRED_TO_M03'
    assert gates['full_corpus_item_completeness'] == 'NOT_EVALUATED_M02'
    assert gates['global_s2_item_projection_readiness'] is False

    nr = m02['new_identity_range']
    assert nr == {
        'first': 'KET_ITEM_000630',
        'last': 'KET_ITEM_000714',
        'count': 85,
        'next_available_new_item_id': 'KET_ITEM_000715',
    }
    assert m02['next_milestone'] == 'KET_Data_S1R2_M03_FullItemBearingSourceCompletenessAndLineageRepair'
