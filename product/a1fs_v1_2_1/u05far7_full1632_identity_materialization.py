from __future__ import annotations
import json
from collections import Counter
from pathlib import Path
from typing import Any

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "FAR7 identity validator only. Python validates slot identity, lineage, quota binding, "
    "pending-review state, and the three-file authority boundary; it does not author learner English."
)
TASK_ID = "A1FS-V1-U05FAR7_Full1632LearnerFacingPracticeMaterializationImplementation"
STATUS = "PASS_A1FS_V1_U05FAR7_IDENTITY_MATERIALIZATION"
NEXT_SHORT_STEP = "A1FS-V1-U05FAR7_Core480GPT56LearnerFacingMaterialization"

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "product/a1fs_v1_2_1/data"
FAR2 = DATA / "unit05_coverage_driven_practice_slots.json"
FAR3 = DATA / "unit05_learner_facing_practice_materialization_contract.json"
FAR4 = DATA / "unit05_gpt56_practice_materialization_preflight.json"
FAR6 = DATA / "unit05_full1632_materialization_preflight.json"
CORE = DATA / "unit05_core_practice_480.json"
KET = DATA / "unit05_ket_adapted_practice_672.json"
DICT = DATA / "unit05_dictation_practice_480.json"

class U05FAR7IdentityError(ValueError):
    pass

def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise U05FAR7IdentityError(f"MISSING:{path}")
    obj=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj,dict):
        raise U05FAR7IdentityError(f"NOT_OBJECT:{path}")
    return obj

def _req(ok: bool, code: str) -> None:
    if not ok:
        raise U05FAR7IdentityError(code)

def build_report() -> dict[str, Any]:
    far2,far3,far4,far6,core,ket,dct=map(_load,(FAR2,FAR3,FAR4,FAR6,CORE,KET,DICT))
    _req(far6["status"]=="PASS_A1FS_V1_U05FAR6_FULL1632_MATERIALIZATION_PREFLIGHT","FAR6_NOT_PASS")
    _req(far6["next_short_step"]==TASK_ID,"FAR6_NEXT_TASK_DRIFT")
    for obj,n in ((core,480),(ket,672),(dct,480)):
        _req(obj["task_id"]==TASK_ID,"TASK_ID_DRIFT")
        _req(obj["item_count"]==n and len(obj["items"])==n,"DENOMINATOR_DRIFT")
        _req(obj["authored_item_count"]==0,"PREMATURE_AUTHOR_COUNT")
        _req(obj["python_or_code_may_author_learner_facing_english"] is False,"CODE_AUTHORING_UNLOCKED")
        _req(obj["reader360_modified"] is False and obj["a2_grammar_unlocked"] is False and obj["pdf_materialized"] is False,"SCOPE_DRIFT")

    core_slots={x["slot_id"]:x for x in far2["core_grammar_slots"]}
    ket_slots={x["slot_id"]:x for x in far2["ket_adapted_slots"]}
    dict_slots={x["slot_id"]:x for x in far2["delayed_dictation_slots"]}
    _req({x["source_slot_id"] for x in core["items"]}==set(core_slots),"CORE_SLOT_SET_DRIFT")
    _req({x["source_slot_id"] for x in ket["items"]}==set(ket_slots),"KET_SLOT_SET_DRIFT")
    _req({x["source_slot_id"] for x in dct["items"]}==set(dict_slots),"DICT_SLOT_SET_DRIFT")
    all_items=core["items"]+ket["items"]+dct["items"]
    _req(len({x["practice_id"] for x in all_items})==1632,"PRACTICE_ID_COLLISION")
    _req(len({x["source_slot_id"] for x in all_items})==1632,"SOURCE_SLOT_COLLISION")

    for row in core["items"]:
        src=core_slots[row["source_slot_id"]]
        for k in ("practice_set_id","stage","episode_id","frame_id","subject_class","place_relation","polarity","complement_class"):
            _req(row[k]==src[k],f"CORE_LINEAGE_DRIFT:{row['practice_id']}:{k}")
        _req(row["reader_source_refs"]==[src["reader_ref"]],f"CORE_READER_DRIFT:{row['practice_id']}")
        _req(row["learner_facing_content"] is None and row["answer_binding_or_rubric"] is None,f"CORE_PREMATURE_CONTENT:{row['practice_id']}")
        _req(row["gpt56_semantic_review"]=="PENDING",f"CORE_REVIEW_DRIFT:{row['practice_id']}")

    quota=far4["full_production_core_archetype_quota_plan"]["quotas_by_frame"]
    actual={}
    for row in core["items"]:
        actual.setdefault(row["frame_id"],Counter())[row["target_archetype"]]+=1
    for frame,expected in quota.items():
        _req(dict(actual[frame])==expected,f"CORE_QUOTA_DRIFT:{frame}:{dict(actual[frame])}")

    contracts={x["task_family"]:x for x in far3["ket_adapted_materialization_contract"]["task_family_contracts"]}
    bundles=0
    for row in ket["items"]:
        src=ket_slots[row["source_slot_id"]]
        for k in ("practice_set_id","stage","episode_id","ket_profile_id","task_family","skill","response_mode","assessment_capability","output_level"):
            _req(row[k]==src[k],f"KET_LINEAGE_DRIFT:{row['practice_id']}:{k}")
        c=contracts[row["task_family"]]
        _req(row["answer_mode"]==c["answer_mode"],f"KET_ANSWER_MODE_DRIFT:{row['practice_id']}")
        _req(row["asset_preconditions"]==c["executable_preconditions"],f"KET_ASSET_GATE_DRIFT:{row['practice_id']}")
        _req(row["learner_facing_content"] is None,f"KET_PREMATURE_CONTENT:{row['practice_id']}")
        if row["source_bundle_review_required"]:
            bundles+=1
            _req(row["source_bundle_review"] is None,f"KET_PREMATURE_BUNDLE:{row['practice_id']}")
    _req(bundles==96,"MULTI_SOURCE_COUNT_DRIFT")

    for row in dct["items"]:
        src=dict_slots[row["source_slot_id"]]
        for k in ("practice_set_id","stage","episode_id","dictation_pass","spoken360_ref","audio_granularity","retention_source_slot_id","recommended_delay"):
            _req(row[k]==src[k],f"DICT_LINEAGE_DRIFT:{row['practice_id']}:{k}")
        _req(row["provenance_mode"]=="AUDIO_TRANSCRIPT_EXACT","DICT_PROVENANCE_DRIFT")
        _req(row["asset_preconditions"]==["AUDIO_ASSET_BOUND"],"DICT_ASSET_GATE_DRIFT")
        _req(row["learner_facing_content"] is None and row["gpt56_segment_selection_review"]=="PENDING",f"DICT_PREMATURE_CONTENT:{row['practice_id']}")

    return {
        "task_id":TASK_ID,"status":STATUS,
        "core_identity_count":480,"ket_identity_count":672,"dictation_identity_count":480,
        "total_identity_count":1632,"authored_item_count":0,
        "multi_source_bundle_review_pending_count":bundles,
        "next_short_step":NEXT_SHORT_STEP
    }

def main() -> int:
    print(json.dumps(build_report(),ensure_ascii=False,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
