from __future__ import annotations
import json
from collections import Counter
from pathlib import Path
from typing import Any

A1FS_CONTENT_POLICY_MODE = "VALIDATOR_ONLY"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Validates GPT-5.6-authored Core480 materialization. Python does not author, rewrite, "
    "repair, select semantic answers, or create learner-facing English."
)
TASK_ID="A1FS-V1-U05FAR7_Core480GPT56LearnerFacingMaterialization"
STATUS="PASS_A1FS_V1_U05FAR7_CORE480_GPT56_MATERIALIZATION"
NEXT_SHORT_STEP="A1FS-V1-U05FAR7_KETText336GPT56LearnerFacingMaterialization"

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/"product/a1fs_v1_2_1/data"
CORE=DATA/"unit05_core_practice_480.json"
FAR2=DATA/"unit05_coverage_driven_practice_slots.json"
FAR3=DATA/"unit05_learner_facing_practice_materialization_contract.json"
FAR4=DATA/"unit05_gpt56_practice_materialization_preflight.json"
PATTERN=DATA/"unit05_pattern360_360.json"
Q05=ROOT/"ulga/contracts/a1fs_v1_u05_q05_core_sentence_frame_authority.json"

class U05FAR7CoreError(ValueError): pass
def _load(p:Path)->dict[str,Any]:
    x=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(x,dict): raise U05FAR7CoreError(f"NOT_OBJECT:{p}")
    return x
def _req(ok:bool,code:str)->None:
    if not ok: raise U05FAR7CoreError(code)

def build_report()->dict[str,Any]:
    core,far2,far3,far4,pattern,q05=map(_load,(CORE,FAR2,FAR3,FAR4,PATTERN,Q05))
    _req(core["item_count"]==480 and len(core["items"])==480,"CORE_COUNT_DRIFT")
    _req(core["authored_item_count"]==480,"AUTHOR_COUNT_DRIFT")
    _req(core["status"]=="PASS_CORE480_GPT56_LEARNER_FACING_MATERIALIZED","STATUS_DRIFT")
    _req(core["python_or_code_may_author_learner_facing_english"] is False,"CODE_AUTHORING_UNLOCKED")
    bank=core["static_template_bank"]
    _req(bank["author_model"]=="GPT-5.6 Sol" and bank["review_status"]=="PASS","STATIC_BANK_REVIEW_DRIFT")
    _req(len(bank["instructions"])==6,"INSTRUCTION_BANK_DRIFT")
    _req(bank["q05_authority_ref"]=="ulga/contracts/a1fs_v1_u05_q05_core_sentence_frame_authority.json","Q05_BINDING_DRIFT")

    source_by_ref={x["reader_entry_id"]:x for x in pattern["entries"]}
    q05_be={x["subject_class"]:x["be_surface"] for x in q05["subject_be_resolution"]["affirmative_full"]}
    allowed=set(far3["core_grammar_materialization_contract"]["allowed_practice_archetypes"])
    slots={x["slot_id"]:x for x in far2["core_grammar_slots"]}
    quota=far4["full_production_core_archetype_quota_plan"]["quotas_by_frame"]
    actual={}
    reviews=("gpt56_semantic_review","gpt56_pedagogical_review","gpt56_source_grounding_review","gpt56_unit05_scope_review","gpt56_answerability_review")
    correction=productive=deterministic=0
    source_visible=Counter()
    for row in core["items"]:
        src=slots[row["source_slot_id"]]
        _req(row["target_archetype"] in allowed,f"ARCHETYPE_INVALID:{row['practice_id']}")
        _req(row["materialization_status"]=="MATERIALIZED_GPT56_STATIC_BANK_REVIEW_PASS",f"MATERIALIZATION_STATUS_DRIFT:{row['practice_id']}")
        _req(row["execution_status"]=="EXECUTABLE_TEXT_ONLY",f"EXECUTION_STATUS_DRIFT:{row['practice_id']}")
        _req(all(row[k]=="PASS" for k in reviews),f"GPT56_REVIEW_NOT_PASS:{row['practice_id']}")
        _req(isinstance(row["learner_facing_content"],dict),f"CONTENT_MISSING:{row['practice_id']}")
        _req(isinstance(row["response_contract"],dict),f"RESPONSE_MISSING:{row['practice_id']}")
        _req(isinstance(row["answer_binding_or_rubric"],dict),f"ANSWER_MISSING:{row['practice_id']}")
        _req(row["reader_source_refs"]==[src["reader_ref"]],f"READER_REF_DRIFT:{row['practice_id']}")
        _req(row["reader_source_refs"][0] in source_by_ref,f"PATTERN_REF_MISSING:{row['practice_id']}")
        _req(row["learner_facing_content"]["source_example"] is not None,f"SOURCE_EXAMPLE_MISSING:{row['practice_id']}")
        _req(row["learner_facing_content"]["frame_formula"] is not None,f"FRAME_FORMULA_MISSING:{row['practice_id']}")
        expected_be=q05_be[row["subject_class"]]
        if row["target_archetype"] in {"BE_FORM_SELECTION","SUBJECT_BE_AGREEMENT"}:
            _req(row["answer_binding_or_rubric"]["correct_option"]==expected_be,f"BE_ANSWER_DRIFT:{row['practice_id']}")
            deterministic+=1
        elif row["target_archetype"]=="ONE_WORD_BE_COMPLETION":
            _req(row["answer_binding_or_rubric"]["accepted_answers"]==[expected_be],f"ONE_WORD_ANSWER_DRIFT:{row['practice_id']}")
            deterministic+=1
        elif row["target_archetype"]=="AFFIRMATIVE_NEGATIVE_CONTRAST":
            expected="B" if row["polarity"]=="NEGATIVE" else "A"
            _req(row["answer_binding_or_rubric"]["correct_option_id"]==expected,f"POLARITY_ANSWER_DRIFT:{row['practice_id']}")
            deterministic+=1
        elif row["target_archetype"]=="SENTENCE_CORRECTION":
            vals=row["answer_binding_or_rubric"].get("accepted_full_answers")
            _req(isinstance(vals,list) and len(vals)==1 and vals[0].endswith("."),f"CORRECTION_FULL_SENTENCE_REQUIRED:{row['practice_id']}")
            correction+=1; deterministic+=1
        else:
            _req(row["response_contract"]["type"]=="FREE_TEXT",f"PRODUCTIVE_RESPONSE_DRIFT:{row['practice_id']}")
            rub=row["answer_binding_or_rubric"]
            _req("rubric_dimensions" in rub and "model_response_example" in rub,f"PRODUCTIVE_RUBRIC_MISSING:{row['practice_id']}")
            _req("correct_option" not in rub and "accepted_answers" not in rub and "accepted_full_answers" not in rub,f"PRODUCTIVE_SINGLE_ANSWER_FORBIDDEN:{row['practice_id']}")
            productive+=1
        actual.setdefault(row["frame_id"],Counter())[row["target_archetype"]]+=1
        source_visible[(row["stage"],bool(row["learner_facing_content"]["source_example_visible_during_attempt"]))]+=1

    for frame,expected in quota.items():
        _req(dict(actual[frame])==expected,f"QUOTA_DRIFT:{frame}:{dict(actual[frame])}")
    _req(Counter(x["target_archetype"] for x in core["items"])=={a:80 for a in allowed},"ARCHETYPE_GLOBAL_BALANCE_DRIFT")
    _req(correction==80 and productive==80 and deterministic==400,"ANSWER_MODE_COUNT_DRIFT")
    return {
        "task_id":TASK_ID,"status":STATUS,"core_authored_count":480,
        "deterministic_count":deterministic,"productive_count":productive,
        "sentence_correction_count":correction,"archetype_count":len(allowed),
        "all_gpt56_reviews_pass":True,"next_short_step":NEXT_SHORT_STEP
    }

def main()->int:
    print(json.dumps(build_report(),ensure_ascii=False,indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
