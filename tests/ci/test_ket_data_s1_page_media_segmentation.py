from __future__ import annotations
import base64
import hashlib
import json
import lzma
import math
import re
from pathlib import Path

TASK_ID = 'KET_Data_S1_ChunkCachedFull1398PageSegmentation_ExactKET_S1Acceptance'
STATUS = 'PASS_KET_DATA_S1_STRUCTURAL_SEGMENTATION_LEGACY_ITEM_IDENTITIES_FROZEN'
XZ_SHA = 'b557257b09693a65069e42885c4cbe76347a27e5f54c8090b9b94646252d6a04'
JSON_SHA = 'b915a0af67a57ae8b6b2b3ac7f16d8f2a6466b18bd6a3b41f50d6aa02a232480'
LEGACY_RT = ['TEXT','INSTRUCTION','QUESTION','ANSWER_OPTION','TABLE','IMAGE','DIAGRAM']
NORMALIZED_RT = ['TEXT','INSTRUCTION','QUESTION_CANDIDATE','ANSWER_OPTION','TABLE','IMAGE','DIAGRAM']
MT = ['IMAGE','AUDIO_REFERENCE','SPEAKING_CARD']
SC = ['source_id','drive_file_id','file_name','media_type_code','page_count','segmentation_status']
PC = ['page_id','source_index','page_number','width','height','text_mode_code','regions_by_rt','image_seq_start','item_seq_start','item_labels','media_bits']
EXPECTED_REGIONS = {'TEXT':1154,'INSTRUCTION':76,'QUESTION':629,'ANSWER_OPTION':181,'TABLE':67,'IMAGE':1572,'DIAGRAM':15}


class S1Error(ValueError):
    pass


def _root(root=None):
    return Path(root or Path(__file__).resolve().parents[2])


def _load(root=None):
    base = _root(root) / 'data' / 'ket'
    b64 = ''.join((base / f'ket_page_media_segmentation.json.xz.b64.part{i}').read_text('ascii').strip() for i in (0,1))
    xz = base64.b64decode(b64, validate=True)
    assert hashlib.sha256(xz).hexdigest() == XZ_SHA, 'XZ_SHA256_DRIFT'
    raw = lzma.decompress(xz, format=lzma.FORMAT_XZ)
    assert hashlib.sha256(raw).hexdigest() == JSON_SHA, 'JSON_SHA256_DRIFT'
    return json.loads(raw), xz, raw


def _load_identity_state(root=None):
    p = _root(root) / 'data' / 'ket' / 'ket_s1r2_item_identity_state.json'
    return json.loads(p.read_text(encoding='utf-8'))


def _load_m02(root=None):
    p = _root(root) / 'data' / 'ket' / 'ket_s1r2_canonical_exam_items.json.xz.b64'
    raw = lzma.decompress(base64.b64decode(p.read_text(encoding='ascii').strip()), format=lzma.FORMAT_XZ)
    return json.loads(raw)


def _bbox(b):
    return isinstance(b,list) and len(b)==4 and all(isinstance(x,(int,float)) and math.isfinite(x) and abs(x)<1_000_000 for x in b) and b[0]<=b[2] and b[1]<=b[3]


def validate(root=None):
    p, xz, raw = _load(root)
    state = _load_identity_state(root)
    m02 = _load_m02(root)
    e = []

    if p.get('s') != 'ket.data.page_media_segmentation.s1.v1': e.append('SCHEMA')
    if p.get('e') != 'compact_arrays_v4': e.append('ENCODING')
    if p.get('t') != TASK_ID or p.get('c') != 'KET_S1.txt': e.append('LEGACY_AUTHORITY')
    if p.get('rt') != LEGACY_RT or p.get('mt') != MT: e.append('LEGACY_REGION_MEDIA_CONTRACT')
    if p.get('sc') != SC or p.get('pc') != PC: e.append('COLUMN_CONTRACT')

    region_repair = state.get('region_contract_repair') or {}
    if region_repair.get('legacy_region_name') != 'QUESTION': e.append('REGION_REPAIR_LEGACY_NAME')
    if region_repair.get('normalized_region_name') != 'QUESTION_CANDIDATE': e.append('REGION_REPAIR_NORMALIZED_NAME')
    if region_repair.get('legacy_question_region_implies_canonical_item') is not False: e.append('QUESTION_REGION_CANONICAL_LEAK')
    if region_repair.get('canonical_item_requires_admission') is not True: e.append('CANONICAL_ADMISSION_GATE')

    ic = p.get('ic') or {}
    if ic.get('page_id') != '{source_id}_P{page_number:03d}': e.append('PAGE_ID_CONTRACT')
    if ic.get('image_id') != 'KET_IMG_{global_image_seq:06d}': e.append('IMAGE_ID_CONTRACT')
    if ic.get('item_id') != 'KET_ITEM_{global_item_seq:06d}': e.append('LEGACY_ITEM_ID_CONTRACT')
    if ic.get('item_image_binding') != 'PAGE_IMAGES': e.append('ITEM_IMAGE_BINDING')

    ss = p.get('ss') or []
    ps = p.get('ps') or []
    if len(ss) != 34: e.append(f'SOURCES:{len(ss)}')
    src = {}
    for i, row in enumerate(ss, 1):
        if not isinstance(row,list) or len(row) != len(SC):
            e.append(f'SOURCE_SHAPE:{i}')
            continue
        sid, drive, name, mcode, n, status = row
        if sid != f'KET_SRC_{i:06d}' or not drive or not name: e.append(f'SOURCE_ID_LINEAGE:{i}')
        if sid in src: e.append(f'SOURCE_DUP:{sid}')
        src[sid] = row
        if i <= 33 and (mcode != 0 or not isinstance(n,int) or n < 1): e.append(f'PDF_SOURCE:{sid}')
        if i == 34 and (mcode != 1 or n is not None or status != 'NOT_APPLICABLE_PDF_PAGE_SEGMENTATION'): e.append('DOCX_SOURCE')

    if len(ps) != 1398: e.append(f'PAGES:{len(ps)}')
    bysrc = {i:[] for i in range(34)}
    seen = set()
    img_next = item_next = 1
    pdf_text = ocr = audio = speaking = 0
    rc = {k:0 for k in LEGACY_RT}
    reverse_img = reverse_legacy_item = 0
    for j, row in enumerate(ps, 1):
        if not isinstance(row,list) or len(row) != len(PC):
            e.append(f'PAGE_SHAPE:{j}')
            continue
        pid, si, pn, w, h, tm, regs, istart, qstart, labels, bits = row
        if not isinstance(si,int) or not 0 <= si < 33:
            e.append(f'SOURCE_INDEX:{j}')
            continue
        sid = ss[si][0]
        expected = f'{sid}_P{pn:03d}' if isinstance(pn,int) else ''
        if pid != expected or not re.fullmatch(r'KET_SRC_\d{6}_P\d{3}', pid or ''): e.append(f'PAGE_ID:{j}')
        if pid in seen: e.append(f'PAGE_DUP:{pid}')
        seen.add(pid)
        bysrc[si].append(pn)
        if not (isinstance(w,int) and isinstance(h,int) and w>0 and h>0): e.append(f'PAGE_SIZE:{pid}')
        if tm == 0: pdf_text += 1
        elif tm == 1: ocr += 1
        else: e.append(f'TEXT_MODE:{pid}')
        if not isinstance(regs,list) or len(regs) != len(LEGACY_RT):
            e.append(f'REGIONS:{pid}')
            continue
        for k, boxes in enumerate(regs):
            if not isinstance(boxes,list):
                e.append(f'REGION_SHAPE:{pid}:{LEGACY_RT[k]}')
                continue
            rc[LEGACY_RT[k]] += len(boxes)
            if any(not _bbox(b) for b in boxes): e.append(f'BBOX:{pid}:{LEGACY_RT[k]}')
        images = len(regs[5])
        legacy_questions = len(regs[2])
        if images:
            if istart != img_next: e.append(f'IMAGE_SEQ:{pid}')
            reverse_img += images
            img_next += images
        elif istart is not None: e.append(f'IMAGE_ZERO_START:{pid}')
        if not isinstance(labels,list) or len(labels) != legacy_questions or any(not isinstance(x,int) for x in labels): e.append(f'LEGACY_ITEM_LABELS:{pid}')
        if legacy_questions:
            if qstart != item_next: e.append(f'LEGACY_ITEM_SEQ:{pid}')
            reverse_legacy_item += legacy_questions
            item_next += legacy_questions
        elif qstart is not None: e.append(f'LEGACY_ITEM_ZERO_START:{pid}')
        if not isinstance(bits,int) or bits < 0 or bits > 3: e.append(f'MEDIA_BITS:{pid}')
        else:
            audio += bool(bits & 1)
            speaking += bool(bits & 2)

    for i in range(33):
        n = ss[i][4]
        if bysrc[i] != list(range(1,n+1)): e.append(f'PAGE_SEQUENCE:{ss[i][0]}')

    actual = {
        'source_count':34,
        'pdf_source_count':33,
        'non_pdf_source_count':1,
        'page_count':len(ps),
        'image_count':img_next-1,
        'item_count':item_next-1,
        'pdf_text_pages':pdf_text,
        'ocr_pages':ocr,
        'audio_reference_pages':audio,
        'speaking_card_pages':speaking,
        'region_counts':rc,
    }
    if p.get('sum') != actual: e.append('SUMMARY')
    if rc != EXPECTED_REGIONS: e.append('REGION_TOTALS')
    if img_next-1 != 1572 or item_next-1 != 629 or reverse_img != 1572 or reverse_legacy_item != 629: e.append('LEGACY_IDENTITY_TOTALS')
    if pdf_text != 131 or ocr != 1267: e.append('TEXT_MODE_TOTALS')
    if p.get('cb') != {'raw_page_text_in_github':False,'raw_ocr_text_in_github':False,'raw_images_in_github':False,'source_assets_remain_external':True}: e.append('COPYRIGHT_BOUNDARY')

    audit = state.get('legacy_identity_audit') or {}
    counts = audit.get('status_counts') or {}
    if counts != {'CONFIRMED_CANONICAL_ITEM':0,'DEPRECATED_NON_ITEM':0,'UNRESOLVED':629}: e.append('M01_STATUS_COUNTS')
    m02_items = m02.get('items') or []
    if len(m02_items) != 85: e.append('M02_CANONICAL_ITEM_COUNT')
    if any(x.get('identity_status') != 'CONFIRMED_CANONICAL_ITEM' for x in m02_items): e.append('M02_CANONICAL_ITEM_STATUS')
    m02_ids = [x.get('item_id') for x in m02_items]
    if m02_ids != [f'KET_ITEM_{i:06d}' for i in range(630,715)]: e.append('M02_ITEM_SEQUENCE')
    m02_gates = m02.get('gates') or {}
    if m02_gates.get('canonical_exam_item_identity_complete') is not True: e.append('M02_CANONICAL_EXAM_COMPLETENESS')
    if m02_gates.get('full_corpus_item_completeness') != 'NOT_EVALUATED_M02': e.append('M02_FULL_CORPUS_SCOPE')
    if m02_gates.get('global_s2_item_projection_readiness') is not False: e.append('M02_S2_READINESS')

    if e:
        raise S1Error('\n'.join(e[:100]))

    normalized_counts = dict(rc)
    normalized_counts['QUESTION_CANDIDATE'] = normalized_counts.pop('QUESTION')
    return {
        'task_id': TASK_ID,
        'status': STATUS,
        'legacy_contract_source': 'KET_S1.txt',
        'repair_contract_source': state['contract_source'],
        'source_count': 34,
        'pdf_source_count': 33,
        'page_count': 1398,
        'image_count': 1572,
        'legacy_question_candidate_count': 629,
        'legacy_item_id_count': 629,
        'confirmed_canonical_item_count': 85,
        'deprecated_non_item_count': 0,
        'unresolved_legacy_item_count': 629,
        'next_available_new_item_id': 'KET_ITEM_000715',
        'normalized_region_types': NORMALIZED_RT,
        'normalized_region_counts': normalized_counts,
        'canonical_exam_item_completeness': 'PASS_PRIMARY_CANONICAL_EXAM_TEST1',
        'full_corpus_item_completeness': 'NOT_PROVEN_M02',
        's2_item_projection_readiness': False,
        'xz_sha256': hashlib.sha256(xz).hexdigest(),
        'json_sha256': hashlib.sha256(raw).hexdigest(),
        'copyright_boundary': 'PASS',
    }


def test_ket_data_s1_structural_contract_with_s1r2_m01_identity_freeze():
    r = validate()
    assert r['status'] == STATUS
    assert (r['page_count'], r['image_count'], r['legacy_item_id_count']) == (1398, 1572, 629)
    assert r['normalized_region_types'][2] == 'QUESTION_CANDIDATE'
    assert r['confirmed_canonical_item_count'] == 85
    assert r['unresolved_legacy_item_count'] == 629
    assert r['next_available_new_item_id'] == 'KET_ITEM_000715'
    assert r['canonical_exam_item_completeness'] == 'PASS_PRIMARY_CANONICAL_EXAM_TEST1'
    assert r['full_corpus_item_completeness'] == 'NOT_PROVEN_M02'
    assert r['s2_item_projection_readiness'] is False
    assert r['copyright_boundary'] == 'PASS'


if __name__ == '__main__':
    print(json.dumps(validate(), ensure_ascii=False, indent=2))
