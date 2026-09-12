from __future__ import annotations
import json, re
from collections import Counter, defaultdict
from pathlib import Path

TASK_ID="KET_Data_S0_SourceInventoryAndAuthorityClassification"
STATUS="PASS_KET_DATA_S0_SOURCE_INVENTORY_AND_AUTHORITY_CLASSIFICATION"
EXPECTED_COUNT=34
EXPECTED_AUTHORITY={
"PUBLISHER_COURSE_MATERIAL":8,
"REFERENCE_ANSWER_MATERIAL":2,
"THIRD_PARTY_PREP":10,
"UNVERIFIED_OFFICIAL_EXAM_CANDIDATE":4,
"UNVERIFIED_SCORING_REFERENCE_CANDIDATE":10,
}
EXPECTED_FAMILY={
"A2_COURSE_MATERIAL":8,
"A2_KEY_EXAM_REFERENCE":4,
"KET_PREP_PRACTICE":10,
"SPEAKING_REFERENCE_ANSWER":2,
"SPEAKING_SCORING_REFERENCE":10,
}
REQUIRED_BLOCKS={"CANONICAL_AUTHORITY_WRITE","CANONICAL_PROMOTION","PUBLIC_RAW_ASSET_REPUBLICATION"}
COLS=["source_id","drive_file_id","parent_ref","file_name","mime_type","size_bytes","year","variant","claimed_role","source_family","authority_class","duplicate_candidate_group"]

class KETDataS0ValidationError(ValueError): pass

def _path():
    return Path(__file__).resolve().parents[1]/"data"/"ket"/"ket_source_manifest.json"

def validate(path=None):
    with Path(path or _path()).open("r",encoding="utf-8") as f: p=json.load(f)
    e=[]
    if p.get("schema")!="ket.data.source_manifest.s0.v1":e.append("SCHEMA_DRIFT")
    if p.get("task_id")!=TASK_ID:e.append("TASK_ID_DRIFT")
    pol=p.get("classification_policy") or {}
    if pol.get("classification_level")!="FILE":e.append("CLASSIFICATION_NOT_FILE_LEVEL")
    for k in ("parent_folder_name_is_not_authority_evidence","official_filename_is_not_verification","canonical_authority_write_requires_verified_evidence"):
        if pol.get(k) is not True:e.append("POLICY_NOT_LOCKED:"+k)
    if pol.get("raw_asset_publication_allowed") is not False:e.append("RAW_PUBLICATION_POLICY_DRIFT")
    if pol.get("raw_asset_storage")!="GOOGLE_DRIVE_SOURCE":e.append("RAW_STORAGE_POLICY_DRIFT")
    if pol.get("duplicate_candidate_resolution")!="HASH_REQUIRED_BEFORE_MERGE":e.append("DUPLICATE_POLICY_DRIFT")

    scope=p.get("scope") or {}
    if scope.get("inventory_level")!="FILE_OBJECT":e.append("INVENTORY_LEVEL_DRIFT")
    if scope.get("source_object_count")!=EXPECTED_COUNT:e.append("SCOPE_COUNT_DRIFT")
    if scope.get("page_semantic_scan")!="NOT_STARTED":e.append("PAGE_SCAN_PREMATURE")
    if scope.get("image_extraction")!="NOT_STARTED":e.append("IMAGE_EXTRACTION_PREMATURE")
    if scope.get("unit04_modification") is not False:e.append("UNIT04_SCOPE_BREACH")

    ap=p.get("authority_policies") or {}
    if set(ap)!=set(EXPECTED_AUTHORITY):e.append("AUTHORITY_POLICY_SET_DRIFT")
    for c,v in ap.items():
        if v.get("verification_status")=="VERIFIED":e.append("PREMATURE_VERIFICATION:"+c)
        if not v.get("allowed_use"):e.append("ALLOWED_USE_EMPTY:"+c)
        miss=REQUIRED_BLOCKS-set(v.get("blocked_use") or [])
        if miss:e.append("BLOCK_MISSING:"+c+":"+",".join(sorted(miss)))
    rb=set((ap.get("REFERENCE_ANSWER_MATERIAL") or {}).get("blocked_use") or [])
    if not {"ANSWER_AUTHORITY","CANONICAL_WORDING_AUTHORITY"}<=rb:e.append("REFERENCE_ANSWER_BLOCK_DRIFT")

    if p.get("source_columns")!=COLS:e.append("COLUMN_CONTRACT_DRIFT")
    parents=p.get("parent_registry") or {}
    rows=p.get("sources") or []
    if len(rows)!=EXPECTED_COUNT:e.append("SOURCE_COUNT:"+str(len(rows)))
    ids=[]; drives=[]; ac=Counter(); fc=Counter(); dups=defaultdict(list)
    for i,row in enumerate(rows,1):
        if not isinstance(row,list) or len(row)!=len(COLS):
            e.append("ROW_SHAPE:"+str(i));continue
        r=dict(zip(COLS,row))
        sid=r["source_id"]; ids.append(sid); drives.append(r["drive_file_id"])
        if sid!=f"KET_SRC_{i:06d}" or not re.fullmatch(r"KET_SRC_\d{6}",sid):e.append("SOURCE_ID:"+str(i))
        if not r["drive_file_id"]:e.append("DRIVE_ID_EMPTY:"+sid)
        if r["parent_ref"] not in parents:e.append("UNKNOWN_PARENT:"+sid)
        if not r["file_name"]:e.append("FILENAME_EMPTY:"+sid)
        if not isinstance(r["size_bytes"],int) or r["size_bytes"]<=0:e.append("SIZE_INVALID:"+sid)
        if r["authority_class"] not in ap:e.append("UNKNOWN_AUTHORITY:"+sid)
        if r["authority_class"]=="VERIFIED_OFFICIAL_EXAM":e.append("PREMATURE_OFFICIAL:"+sid)
        ac[r["authority_class"]]+=1; fc[r["source_family"]]+=1
        if r["duplicate_candidate_group"]:dups[r["duplicate_candidate_group"]].append(r)
    if len(ids)!=len(set(ids)):e.append("SOURCE_ID_NOT_UNIQUE")
    if len(drives)!=len(set(drives)):e.append("DRIVE_ID_NOT_UNIQUE")
    if dict(sorted(ac.items()))!=EXPECTED_AUTHORITY:e.append("AUTHORITY_COUNTS_DRIFT")
    if dict(sorted(fc.items()))!=EXPECTED_FAMILY:e.append("FAMILY_COUNTS_DRIFT")
    if len(dups)!=5:e.append("DUP_GROUP_COUNT")
    if sum(map(len,dups.values()))!=10:e.append("DUP_OBJECT_COUNT")
    for g,x in dups.items():
        if len(x)!=2 or len({r["file_name"] for r in x})!=1 or len({r["size_bytes"] for r in x})!=1:e.append("DUP_METADATA:"+g)

    if e: raise KETDataS0ValidationError("\n".join(e))
    return {"task_id":TASK_ID,"status":STATUS,"source_object_count":34,
    "authority_class_counts":dict(sorted(ac.items())),"source_family_counts":dict(sorted(fc.items())),
    "duplicate_candidate_group_count":5,"duplicate_candidate_object_count":10,
    "verified_official_exam_count":0,"page_semantic_scan_started":False,
    "image_extraction_started":False,"unit04_modified":False,"raw_asset_publication_allowed":False}

if __name__=="__main__": print(json.dumps(validate(),ensure_ascii=False,indent=2))
