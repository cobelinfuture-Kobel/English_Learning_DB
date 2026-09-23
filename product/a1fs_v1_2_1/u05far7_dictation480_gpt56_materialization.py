from __future__ import annotations
import json
from pathlib import Path
from typing import Any

A1FS_CONTENT_POLICY_MODE = "VALIDATOR_ONLY"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Validates GPT-5.6-reviewed Delayed Dictation 480 materialization. "
    "Python does not choose segments, author prompts, rewrite transcripts, or decide semantic answers."
)

TASK_ID="A1FS-V1-U05FAR7_DelayedDictation480GPT56LearnerFacingMaterialization"
STATUS="PASS_A1FS_V1_U05FAR7_DICTATION480_GPT56_MATERIALIZATION"
NEXT_SHORT_STEP="A1FS-V1-U05FAR7_Full1632AuthoringCloseoutReadback"

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/"product/a1fs_v1_2_1/data"
DICT=DATA/"unit05_dictation_practice_480.json"
SPOKEN=DATA/"unit05_spoken360_360.json"
FAR3=DATA/"unit05_learner_facing_practice_materialization_contract.json"

class U05FAR7DictationError(ValueError): pass
def _load(p:Path)->dict[str,Any]:
    x=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(x,dict): raise U05FAR7DictationError(f"NOT_OBJECT:{p}")
    return x
def _req(ok:bool,code:str)->None:
    if not ok: raise U05FAR7DictationError(code)

def build_report()->dict[str,Any]:
    dct,spoken,far3=map(_load,(DICT,SPOKEN,FAR3))
    c=far3["delayed_dictation_materialization_contract"]
    _req(dct["item_count"]==480 and len(dct["items"])==480,"DICT_DENOMINATOR_DRIFT")
    _req(dct["authored_item_count"]==480,"DICT_AUTHOR_COUNT_DRIFT")
    _req(dct["asset_pending_count"]==480 and dct["executable_count"]==0,"DICT_EXECUTION_BOUNDARY_DRIFT")
    _req(dct["d1_authored_count"]==360 and dct["d2_authored_count"]==120,"DICT_PASS_COUNT_DRIFT")
    _req(dct["status"]=="PASS_DICTATION480_GPT56_AUTHORED_AUDIO_ASSET_PENDING","DICT_STATUS_DRIFT")
    _req(dct["audio_asset_generated"] is False,"AUDIO_GENERATION_SCOPE_VIOLATION")
    _req(c["audio_generation_or_recording_is_separate_scope"] is True,"FAR3_AUDIO_SCOPE_DRIFT")
    _req(c["transcript_source_must_be_exact_spoken360_segment"] is True,"FAR3_TRANSCRIPT_AUTHORITY_DRIFT")
    _req(c["segment_selection_requires_gpt56_review"] is True,"FAR3_SEGMENT_REVIEW_DRIFT")

    spoken_by={x["reader_entry_id"]:x for x in spoken["entries"]}
    d1_by_episode={}
    d1_practice_by_slot={}
    reviews=(
        "gpt56_segment_selection_review",
        "gpt56_semantic_review",
        "gpt56_pedagogical_review",
        "gpt56_source_grounding_review",
        "gpt56_unit05_scope_review",
        "gpt56_answerability_review",
    )
    d1=d2=0
    for row in dct["items"]:
        _req(row["spoken360_ref"] in spoken_by,f"SPOKEN_REF_MISSING:{row['practice_id']}")
        entry=spoken_by[row["spoken360_ref"]]
        _req(row["materialization_status"]=="MATERIALIZED_GPT56_SEGMENT_REVIEW_PASS",f"MATERIALIZATION_STATUS_DRIFT:{row['practice_id']}")
        _req(all(row[k]=="PASS" for k in reviews),f"GPT56_REVIEW_NOT_PASS:{row['practice_id']}")
        _req(row["execution_status"]=="NOT_EXECUTABLE_ASSET_PENDING",f"EXECUTION_STATUS_DRIFT:{row['practice_id']}")
        _req(row["asset_preconditions"]==["AUDIO_ASSET_BOUND"],f"ASSET_GATE_DRIFT:{row['practice_id']}")
        content=row["learner_facing_content"]
        response=row["response_contract"]
        answer=row["answer_binding_or_rubric"]
        seg=row["selected_segment"]
        _req(content["stimulus"]["type"]=="AUDIO_ASSET_PENDING",f"STIMULUS_TYPE_DRIFT:{row['practice_id']}")
        _req(content["stimulus"]["learner_visible_transcript"] is False,f"TRANSCRIPT_VISIBILITY_VIOLATION:{row['practice_id']}")
        _req(content["stimulus"]["spoken360_ref"]==row["spoken360_ref"],f"STIMULUS_SOURCE_DRIFT:{row['practice_id']}")
        _req(response["type"]=="DICTATION" and response["pass"]==row["dictation_pass"],f"RESPONSE_PASS_DRIFT:{row['practice_id']}")
        _req(response["learner_flow"]==["LISTEN_WITHOUT_TRANSCRIPT","WRITE","CHECK_AFTER_ATTEMPT","LISTEN_AGAIN","SAY_ALOUD"],f"LEARNER_FLOW_DRIFT:{row['practice_id']}")
        _req(response["retention_schedule"]==row["recommended_delay"],f"RETENTION_SCHEDULE_DRIFT:{row['practice_id']}")
        indexes=seg["source_turn_indexes"]
        _req(all(isinstance(i,int) and 0<=i<len(entry["dialogue_turns"]) for i in indexes),f"TURN_INDEX_INVALID:{row['practice_id']}")
        exact_turns=[entry["dialogue_turns"][i] for i in indexes]
        _req(answer["source_turns"]==exact_turns,f"SOURCE_TURN_EXACTNESS_DRIFT:{row['practice_id']}")
        _req(answer["target_transcript"]==" ".join(t["text"] for t in exact_turns),f"TARGET_TRANSCRIPT_DRIFT:{row['practice_id']}")
        _req(answer["normalization"]==["CASE","TERMINAL_PUNCTUATION","NON_SEMANTIC_EXTRA_SPACES"],f"NORMALIZATION_DRIFT:{row['practice_id']}")
        _req(answer["normalization_may_not_ignore"]==["MISSING_WORDS","WRONG_BE_FORM","NEGATION_ERROR","WORD_ORDER_ERROR","CONTENT_WORD_SUBSTITUTION"],f"STRICT_NORMALIZATION_DRIFT:{row['practice_id']}")
        _req(seg["core_d1_turn_index"] in indexes,f"CORE_D1_NOT_IN_SEGMENT:{row['practice_id']}")
        _req(entry["dialogue_turns"][seg["core_d1_turn_index"]]["text"]==seg["core_d1_target_text"],f"CORE_D1_TEXT_DRIFT:{row['practice_id']}")

        if row["dictation_pass"]=="D1":
            d1+=1
            _req(len(indexes)==1,f"D1_NOT_SINGLE_TURN:{row['practice_id']}")
            _req(seg["selected_audio_granularity"]=="TURN",f"D1_GRANULARITY_DRIFT:{row['practice_id']}")
            _req(response["selected_audio_granularity"]=="TURN",f"D1_RESPONSE_GRANULARITY_DRIFT:{row['practice_id']}")
            _req(response["retention_source_practice_id"] is None,f"D1_RETENTION_LINK_FORBIDDEN:{row['practice_id']}")
            d1_by_episode[row["episode_id"]]=row
            d1_practice_by_slot[row["source_slot_id"]]=row["practice_id"]
        elif row["dictation_pass"]=="D2":
            d2+=1
            _req(len(indexes)==2 and indexes[1]==indexes[0]+1,f"D2_NOT_ADJACENT_MICROCLIP:{row['practice_id']}")
            _req(seg["selected_audio_granularity"]=="MULTI_TURN_MICROCLIP",f"D2_GRANULARITY_DRIFT:{row['practice_id']}")
            _req(response["selected_audio_granularity"]=="MULTI_TURN_MICROCLIP",f"D2_RESPONSE_GRANULARITY_DRIFT:{row['practice_id']}")
        else:
            raise U05FAR7DictationError(f"UNKNOWN_PASS:{row['practice_id']}")

    _req(d1==360 and d2==120,"D1_D2_COUNT_DRIFT")

    for row in dct["items"]:
        if row["dictation_pass"]!="D2": continue
        _req(row["episode_id"] in d1_by_episode,f"D2_D1_EPISODE_MISSING:{row['practice_id']}")
        d1row=d1_by_episode[row["episode_id"]]
        _req(row["retention_source_slot_id"]==d1row["source_slot_id"],f"D2_RETENTION_SLOT_DRIFT:{row['practice_id']}")
        _req(row["response_contract"]["retention_source_practice_id"]==d1row["practice_id"],f"D2_RETENTION_PRACTICE_DRIFT:{row['practice_id']}")
        _req(row["selected_segment"]["core_d1_target_text"]==d1row["selected_segment"]["core_d1_target_text"],f"D2_CORE_TARGET_NOT_REUSED:{row['practice_id']}")
        _req(row["selected_segment"]["core_d1_turn_index"]==d1row["selected_segment"]["core_d1_turn_index"],f"D2_CORE_TURN_NOT_REUSED:{row['practice_id']}")
        _req(d1row["answer_binding_or_rubric"]["target_transcript"] in row["answer_binding_or_rubric"]["target_transcript"],f"D2_DOES_NOT_CONTAIN_D1_TRANSCRIPT:{row['practice_id']}")

    return {
        "task_id":TASK_ID,
        "status":STATUS,
        "dictation_authored_count":480,
        "d1_count":d1,
        "d2_count":d2,
        "asset_pending_count":480,
        "executable_count":0,
        "all_gpt56_reviews_pass":True,
        "all_transcripts_exact_spoken360":True,
        "all_d2_reuse_d1_core_target":True,
        "next_short_step":NEXT_SHORT_STEP,
    }

def main()->int:
    print(json.dumps(build_report(),ensure_ascii=False,indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
