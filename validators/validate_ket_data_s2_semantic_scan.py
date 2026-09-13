from __future__ import annotations
import json
from collections import Counter
from pathlib import Path

TASK_ID='KET_Data_S2A_CanonicalKETTaskFamilySemanticAdmission'
STATUS='PASS_KET_DATA_S2A_CANONICAL_KET_TASK_FAMILY_SEMANTIC_ADMISSION'
RESPONSE_MODES=['SELECT','MATCH','TEXT_ENTRY','STRUCTURED_ENTRY','ORDER','SPEAK']
SEMANTIC_FIELDS=['paper','primary_skill','part','learner_visible_stimulus','learner_action','answer_shape','task_family','response_mode','stimulus_modality','response_format','assessment_capability']
EXPECTED_SKILLS=Counter({'READING':5,'WRITING':2,'LISTENING':5,'SPEAKING':2})
EXPECTED_PARTS={
 ('READING',1),('READING',2),('READING',3),('READING',4),('READING',5),
 ('WRITING',6),('WRITING',7),
 ('LISTENING',1),('LISTENING',2),('LISTENING',3),('LISTENING',4),('LISTENING',5),
 ('SPEAKING',1),('SPEAKING',2),
}
ALLOWED_MODALITIES={'TEXT','TEXT_INSTRUCTION','TEXT_FORM','IMAGE','IMAGE_SEQUENCE','AUDIO','SPOKEN_INTERLOCUTOR','TEXT_PROMPT_REFERENCE','PEER_SPEECH'}
S1_FILES=['data/ket/ket_page_media_segmentation.json.xz.b64.part0','data/ket/ket_page_media_segmentation.json.xz.b64.part1','tests/ci/test_ket_data_s1_page_media_segmentation.py']

class KETDataS2ValidationError(ValueError): pass

def _root(root=None): return Path(root or Path(__file__).resolve().parents[1])
def _artifact(root=None): return _root(root)/'data'/'ket'/'ket_s2_semantic_task_profiles.json'

def validate(root=None, artifact_path=None):
    r=_root(root)
    p=json.loads(Path(artifact_path or _artifact(r)).read_text(encoding='utf-8'))
    e=[]
    if p.get('schema')!='ket.data.semantic_scan.s2.v1': e.append('SCHEMA_DRIFT')
    if p.get('task_id')!=TASK_ID: e.append('TASK_ID_DRIFT')
    if p.get('contract_source')!='KET_S2.txt': e.append('CONTRACT_SOURCE_DRIFT')
    if p.get('model_contract')!='GPT-5.6_MULTIMODAL_SEMANTIC_SCAN': e.append('MODEL_CONTRACT_DRIFT')
    if p.get('response_mode_contract')!=RESPONSE_MODES: e.append('RESPONSE_MODE_CONTRACT_DRIFT')
    scope=p.get('scope') or {}
    if scope.get('exam_family')!='A2_KEY' or scope.get('scan_level')!='CANONICAL_PART_TASK_PROFILE': e.append('SCOPE_DRIFT')
    if scope.get('primary_source_id')!='KET_SRC_000004' or scope.get('cross_variant_source_id')!='KET_SRC_000011': e.append('SOURCE_SCOPE_DRIFT')
    if scope.get('s1_predecessor_required') is not True: e.append('S1_PREDECESSOR_NOT_REQUIRED')
    if scope.get('authority_promotion') is not False: e.append('UNAPPROVED_AUTHORITY_PROMOTION')
    for f in S1_FILES:
        if not (r/f).is_file(): e.append('S1_PREDECESSOR_FILE_MISSING:'+f)

    ic=p.get('input_contract') or {}
    dims=ic.get('semantic_dimensions') or []
    if dims!=SEMANTIC_FIELDS: e.append('SEMANTIC_DIMENSION_CONTRACT_DRIFT')
    req=ic.get('required_modalities_or_evidence') or []
    for x in ['PAGE_IMAGE','LAYOUT','INSTRUCTIONS','ANSWER_KEY_OR_SCORING_EVIDENCE']:
        if x not in req: e.append('REQUIRED_MULTIMODAL_EVIDENCE_MISSING:'+x)
    if 'IF_ABSENT_DO_NOT_INVENT' not in str(ic.get('pdf_text_layer_policy')): e.append('PDF_TEXT_LAYER_FAIL_CLOSED_POLICY_MISSING')

    rows=p.get('task_profiles') or []
    if len(rows)!=14: e.append(f'TASK_PROFILE_COUNT:{len(rows)}')
    ids=[]; skills=Counter(); parts=set(); families=[]
    for i,row in enumerate(rows,1):
        rid=row.get('id'); ids.append(rid)
        if rid!=f'KET_S2_TASK_{i:03d}': e.append(f'ID_SEQUENCE:{i}')
        for field in SEMANTIC_FIELDS:
            if field not in row or row[field] in (None,'',[]): e.append(f'SEMANTIC_FIELD_MISSING:{rid}:{field}')
        skill=row.get('primary_skill'); part=row.get('part'); skills[skill]+=1; parts.add((skill,part))
        if row.get('response_mode') not in RESPONSE_MODES: e.append(f'RESPONSE_MODE_INVALID:{rid}')
        mods=row.get('stimulus_modality') or []
        if not isinstance(mods,list) or any(x not in ALLOWED_MODALITIES for x in mods): e.append(f'STIMULUS_MODALITY_INVALID:{rid}')
        family=row.get('task_family'); families.append(family)
        if not isinstance(family,str) or 'MCQ' in family: e.append(f'GENERIC_MCQ_NOT_ALLOWED:{rid}')
        for field in ['learner_visible_stimulus','learner_action','answer_shape','assessment_capability','response_format']:
            if not isinstance(row.get(field),str) or len(row[field])<8: e.append(f'SEMANTIC_VALUE_TOO_SHALLOW:{rid}:{field}')
        ev=row.get('standard_evidence') or {}
        if ev.get('source_id')!='KET_SRC_000004' or not ev.get('task_pages'): e.append(f'PRIMARY_EVIDENCE_MISSING:{rid}')
        if not set(['PAGE_IMAGE','LAYOUT','INSTRUCTIONS']).issubset(set(ev.get('evidence_inputs') or [])): e.append(f'MULTIMODAL_EVIDENCE_INCOMPLETE:{rid}')
        if skill=='SPEAKING':
            if not ev.get('scoring_reference_pages'): e.append(f'SPEAKING_SCORING_EVIDENCE_MISSING:{rid}')
        else:
            if not ev.get('answer_key_pages'): e.append(f'ANSWER_KEY_EVIDENCE_MISSING:{rid}')
        cor=row.get('schools_corroboration') or {}
        if cor.get('source_id')!='KET_SRC_000011': e.append(f'CROSS_VARIANT_SOURCE_MISSING:{rid}')
        if row.get('semantic_confidence')!='HIGH': e.append(f'CONFIDENCE_NOT_HIGH:{rid}')
    if len(ids)!=len(set(ids)): e.append('TASK_PROFILE_ID_NOT_UNIQUE')
    if len(families)!=len(set(families)): e.append('TASK_FAMILY_NOT_UNIQUE')
    if skills!=EXPECTED_SKILLS: e.append('SKILL_COUNTS_DRIFT')
    if parts!=EXPECTED_PARTS: e.append('PART_COVERAGE_DRIFT')

    r1=rows[0] if rows else {}
    expected_r1={'task_family':'SHORT_MESSAGE_MEANING','response_mode':'SELECT','stimulus_modality':['TEXT'],'response_format':'SINGLE_CHOICE','assessment_capability':'COMMUNICATIVE_MEANING_EXTRACTION'}
    for k,v in expected_r1.items():
        if r1.get(k)!=v: e.append('S2_EXAMPLE_CONTRACT_DRIFT:'+k)

    byid={x.get('id'):x for x in rows}
    if 'IMAGE_SEQUENCE' not in (byid.get('KET_S2_TASK_007',{}).get('stimulus_modality') or []): e.append('PICTURE_STORY_VISUAL_MODALITY_MISSING')
    if byid.get('KET_S2_TASK_009',{}).get('response_mode')!='STRUCTURED_ENTRY': e.append('LISTENING_NOTE_COMPLETION_RESPONSE_MODE_DRIFT')
    if byid.get('KET_S2_TASK_012',{}).get('response_mode')!='MATCH': e.append('LISTENING_MATCH_RESPONSE_MODE_DRIFT')
    if byid.get('KET_S2_TASK_014',{}).get('response_mode')!='SPEAK' or 'IMAGE' not in (byid.get('KET_S2_TASK_014',{}).get('stimulus_modality') or []): e.append('SPEAKING_VISUAL_DISCUSSION_DRIFT')

    sm=p.get('scan_summary') or {}
    if sm.get('canonical_task_profile_count')!=14 or sm.get('reading_profiles')!=5 or sm.get('writing_profiles')!=2 or sm.get('listening_profiles')!=5 or sm.get('speaking_profiles')!=2: e.append('SCAN_SUMMARY_DRIFT')
    if sm.get('cross_variant_semantic_corroboration') is not True: e.append('CROSS_VARIANT_CORROBORATION_MISSING')

    if e: raise KETDataS2ValidationError('\n'.join(e[:100]))
    return {'task_id':TASK_ID,'status':STATUS,'contract_source':'KET_S2.txt','task_profile_count':14,'skill_counts':dict(skills),'response_modes_used':sorted(set(x['response_mode'] for x in rows)),'task_families':families,'primary_source_id':'KET_SRC_000004','cross_variant_source_id':'KET_SRC_000011','s1_predecessor':'PASS','generic_mcq_labels':0,'semantic_dimensions_complete':True}

if __name__=='__main__': print(json.dumps(validate(),ensure_ascii=False,indent=2))
