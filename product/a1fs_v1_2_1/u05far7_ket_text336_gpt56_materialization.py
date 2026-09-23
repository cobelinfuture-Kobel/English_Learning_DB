from __future__ import annotations
import json
from collections import Counter
from pathlib import Path
from typing import Any

A1FS_CONTENT_POLICY_MODE = "VALIDATOR_ONLY"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Validates GPT-5.6-authored KET text-first 336 materialization. "
    "Python does not author, rewrite, gap, select distractors, or decide semantic answers."
)

TASK_ID="A1FS-V1-U05FAR7_KETText336GPT56LearnerFacingMaterialization"
STATUS="PASS_A1FS_V1_U05FAR7_KET_TEXT336_GPT56_MATERIALIZATION"
NEXT_SHORT_STEP="A1FS-V1-U05FAR7_KETAssetDependent336GPT56LearnerFacingMaterialization"

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/"product/a1fs_v1_2_1/data"
KET=DATA/"unit05_ket_adapted_practice_672.json"
CURRENT=DATA/"unit05_current360_360.json"
PATTERN=DATA/"unit05_pattern360_360.json"
SPOKEN=DATA/"unit05_spoken360_360.json"
FAR3=DATA/"unit05_learner_facing_practice_materialization_contract.json"

TEXT_FAMILIES={
    "SHORT_MESSAGE_MEANING",
    "PERSON_TEXT_DETAIL_MATCHING",
    "LONG_TEXT_DETAIL_INFERENCE",
    "LEXICAL_CLOZE",
    "OPEN_CLOZE",
    "SHORT_COMMUNICATIVE_EMAIL",
    "PERSONAL_INTERVIEW",
}
MEDIA_FAMILIES={
    "PICTURE_SEQUENCE_STORY",
    "AUDIO_PICTURE_DETAIL_SELECTION",
    "AUDIO_NOTE_COMPLETION",
    "AUDIO_CONVERSATION_DETAIL",
    "SHORT_AUDIO_GIST_INTENT_DETAIL",
    "AUDIO_LIST_MATCHING",
    "COLLABORATIVE_VISUAL_DISCUSSION",
}

class U05FAR7KETTextError(ValueError): pass
def _load(p:Path)->dict[str,Any]:
    x=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(x,dict): raise U05FAR7KETTextError(f"NOT_OBJECT:{p}")
    return x
def _req(ok:bool,code:str)->None:
    if not ok: raise U05FAR7KETTextError(code)

def build_report()->dict[str,Any]:
    ket,current,pattern,spoken,far3=map(_load,(KET,CURRENT,PATTERN,SPOKEN,FAR3))
    _req(ket["item_count"]==672 and len(ket["items"])==672,"KET_DENOMINATOR_DRIFT")
    _req(ket["authored_item_count"]==336,"KET_AUTHORED_COUNT_DRIFT")
    _req(ket["executable_text_only_count"]==336,"KET_TEXT_EXECUTABLE_COUNT_DRIFT")
    _req(ket["asset_pending_count"]==336,"KET_ASSET_PENDING_COUNT_DRIFT")
    _req(ket["status"]=="IN_PROGRESS_KET_TEXT336_GPT56_MATERIALIZED_MEDIA336_PENDING","KET_STATUS_DRIFT")
    _req(ket["text_first_static_contract"]["author_model"]=="GPT-5.6 Sol","AUTHOR_MODEL_DRIFT")
    _req(ket["text_first_static_contract"]["review_status"]=="PASS","STATIC_CONTRACT_REVIEW_DRIFT")
    _req(ket["text_first_static_contract"]["code_may_compose_new_learner_english"] is False,"CODE_AUTHORING_UNLOCKED")

    current_by={x["episode_id"]:x for x in current["episodes"]}
    pattern_by={x["reader_entry_id"]:x for x in pattern["entries"]}
    spoken_by={x["reader_entry_id"]:x for x in spoken["entries"]}
    contracts={x["task_family"]:x for x in far3["ket_adapted_materialization_contract"]["task_family_contracts"]}

    counts=Counter()
    bundles=0
    productive=0
    oral=0
    deterministic=0
    reviews=("gpt56_semantic_review","gpt56_pedagogical_review","gpt56_source_grounding_review","gpt56_unit05_scope_review","gpt56_answerability_review")

    for row in ket["items"]:
        fam=row["task_family"]
        if fam in MEDIA_FAMILIES:
            _req(row["learner_facing_content"] is None,f"MEDIA_FAMILY_PREMATURE_CONTENT:{row['practice_id']}")
            _req(row["execution_status"]=="NOT_EXECUTABLE_AUTHORING_PENDING",f"MEDIA_FAMILY_EXECUTION_DRIFT:{row['practice_id']}")
            continue

        _req(fam in TEXT_FAMILIES,f"UNKNOWN_TEXT_FAMILY:{fam}")
        counts[fam]+=1
        _req(row["materialization_status"]=="MATERIALIZED_GPT56_TEXT_FIRST_REVIEW_PASS",f"MATERIALIZATION_STATUS_DRIFT:{row['practice_id']}")
        _req(row["execution_status"]=="EXECUTABLE_TEXT_ONLY",f"TEXT_EXECUTION_STATUS_DRIFT:{row['practice_id']}")
        _req(all(row[k]=="PASS" for k in reviews),f"GPT56_REVIEW_NOT_PASS:{row['practice_id']}")
        _req(isinstance(row["learner_facing_content"],dict),f"CONTENT_MISSING:{row['practice_id']}")
        _req(isinstance(row["response_contract"],dict),f"RESPONSE_MISSING:{row['practice_id']}")
        _req(isinstance(row["answer_binding_or_rubric"],dict),f"ANSWER_MISSING:{row['practice_id']}")
        _req(row["asset_preconditions"]==[],f"TEXT_FAMILY_ASSET_GATE_DRIFT:{row['practice_id']}")
        _req(contracts[fam]["executable_preconditions"]==[],f"FAR3_TEXT_FAMILY_ASSET_GATE_DRIFT:{fam}")

        content=row["learner_facing_content"]
        answer=row["answer_binding_or_rubric"]
        response=row["response_contract"]

        if fam=="SHORT_MESSAGE_MEANING":
            stim=content["stimulus"]
            _req(stim["source_ref"] in current_by,f"MESSAGE_SOURCE_MISSING:{row['practice_id']}")
            _req(stim["text"]==current_by[stim["source_ref"]]["paragraph"],f"MESSAGE_SOURCE_TEXT_DRIFT:{row['practice_id']}")
            opts=response["options"]
            _req(len(opts)==3 and answer["correct_option_id"]=="A",f"MESSAGE_OPTION_SHAPE_DRIFT:{row['practice_id']}")
            _req(answer["evidence_text"] in stim["text"],f"MESSAGE_EVIDENCE_NOT_IN_SOURCE:{row['practice_id']}")
            _req(opts[0]["text"]==answer["evidence_text"],f"MESSAGE_CORRECT_OPTION_EVIDENCE_DRIFT:{row['practice_id']}")
            _req(all(o["text"] not in stim["text"] for o in opts[1:]),f"MESSAGE_DISTRACTOR_EXACTLY_IN_SOURCE:{row['practice_id']}")
            deterministic+=1

        elif fam=="PERSON_TEXT_DETAIL_MATCHING":
            bundle=row["source_bundle_review"]
            _req(bundle and bundle["status"]=="PASS_GPT56_SOURCE_BUNDLE_REVIEW",f"MATCH_BUNDLE_REVIEW_MISSING:{row['practice_id']}")
            refs=bundle["source_refs"]
            _req(len(refs)==3 and len(set(refs))==3,f"MATCH_BUNDLE_DISTINCT_SOURCE_DRIFT:{row['practice_id']}")
            _req(row["reader_source_refs"]==refs,f"MATCH_READER_REF_BUNDLE_DRIFT:{row['practice_id']}")
            texts=response["texts"]; statements=response["statements"]
            _req(len(texts)==3 and len(statements)==3,f"MATCH_SHAPE_DRIFT:{row['practice_id']}")
            by_label={x["label"]:x for x in texts}
            for idx,label in enumerate(("A","B","C"),start=1):
                ref=by_label[label]["source_ref"]
                _req(ref in current_by,f"MATCH_SOURCE_MISSING:{row['practice_id']}:{ref}")
                _req(by_label[label]["text"]==current_by[ref]["paragraph"],f"MATCH_SOURCE_TEXT_DRIFT:{row['practice_id']}:{label}")
                statement=next(x["text"] for x in statements if x["id"]==str(idx))
                _req(statement in by_label[label]["text"],f"MATCH_STATEMENT_NOT_IN_ANSWER_SOURCE:{row['practice_id']}:{idx}")
                _req(answer["matches"][str(idx)]==label,f"MATCH_KEY_DRIFT:{row['practice_id']}:{idx}")
            bundles+=1; deterministic+=1

        elif fam=="LONG_TEXT_DETAIL_INFERENCE":
            stim=content["stimulus"]
            _req(stim["source_ref"] in current_by and stim["text"]==current_by[stim["source_ref"]]["paragraph"],f"LONG_SOURCE_DRIFT:{row['practice_id']}")
            opts=response["options"]
            _req(len(opts)==3 and answer["correct_option_id"]=="A",f"LONG_OPTION_SHAPE_DRIFT:{row['practice_id']}")
            _req(answer["evidence_text"] in stim["text"],f"LONG_EVIDENCE_NOT_IN_SOURCE:{row['practice_id']}")
            _req(opts[0]["text"]==answer["evidence_text"],f"LONG_CORRECT_OPTION_DRIFT:{row['practice_id']}")
            _req(all(o["text"] not in stim["text"] for o in opts[1:]),f"LONG_DISTRACTOR_EXACTLY_IN_SOURCE:{row['practice_id']}")
            deterministic+=1

        elif fam=="LEXICAL_CLOZE":
            stim=content["stimulus"]
            _req(stim["source_ref"] in current_by and stim["text"]==current_by[stim["source_ref"]]["paragraph"],f"LEXICAL_CONTEXT_DRIFT:{row['practice_id']}")
            _req(content["source_sentence_ref"] in pattern_by,f"LEXICAL_PATTERN_REF_MISSING:{row['practice_id']}")
            word=answer["accepted_word"]
            source_sentence=answer["source_sentence"]
            _req(word.lower() in source_sentence.lower(),f"LEXICAL_ANSWER_NOT_IN_SOURCE_SENTENCE:{row['practice_id']}")
            _req("___" in content["prompt"],f"LEXICAL_GAP_MISSING:{row['practice_id']}")
            _req(any(o["text"]==word for o in response["options"]),f"LEXICAL_CORRECT_OPTION_MISSING:{row['practice_id']}")
            deterministic+=1

        elif fam=="OPEN_CLOZE":
            stim=content["stimulus"]
            _req(stim["source_ref"] in current_by and stim["text"]==current_by[stim["source_ref"]]["paragraph"],f"OPEN_CONTEXT_DRIFT:{row['practice_id']}")
            _req(content["source_sentence_ref"] in pattern_by,f"OPEN_PATTERN_REF_MISSING:{row['practice_id']}")
            accepted=answer["accepted_answers"]
            _req(len(accepted)==1 and accepted[0] in {"am","is","are"},f"OPEN_BE_ANSWER_DRIFT:{row['practice_id']}")
            _req("___" in content["prompt"],f"OPEN_GAP_MISSING:{row['practice_id']}")
            _req(response["type"]=="ONE_WORD_ENTRY" and response["word_limit"]==1,f"OPEN_RESPONSE_DRIFT:{row['practice_id']}")
            deterministic+=1

        elif fam=="SHORT_COMMUNICATIVE_EMAIL":
            stim=content["stimulus"]
            _req(stim["source_ref"] in current_by and stim["source_context"]==current_by[stim["source_ref"]]["paragraph"],f"EMAIL_SOURCE_DRIFT:{row['practice_id']}")
            points=[x["source_fact"] for x in stim["content_point_plan"]]
            _req(points==answer["content_points"],f"EMAIL_CONTENT_POINT_DRIFT:{row['practice_id']}")
            _req(all(p in stim["source_context"] for p in points),f"EMAIL_CONTENT_POINT_NOT_SOURCE_GROUNDED:{row['practice_id']}")
            _req(response["type"]=="FREE_TEXT" and response["final_integration_required"] is True,f"EMAIL_FINAL_INTEGRATION_MISSING:{row['practice_id']}")
            _req("correct_option_id" not in answer and "accepted_answers" not in answer,f"EMAIL_SINGLE_ANSWER_FORBIDDEN:{row['practice_id']}")
            productive+=1

        elif fam=="PERSONAL_INTERVIEW":
            pref=content["source_pattern_ref"]
            _req(pref in pattern_by,f"PERSONAL_PATTERN_REF_MISSING:{row['practice_id']}")
            _req(content["source_pattern_role"]=="LANGUAGE_PATTERN_GROUNDING_NOT_PERSONAL_FACT",f"PERSONAL_SOURCE_ROLE_DRIFT:{row['practice_id']}")
            _req(response["type"]=="SPEAK",f"PERSONAL_RESPONSE_MODE_DRIFT:{row['practice_id']}")
            _req("rubric_dimensions" in answer and answer["model_response_role"]=="EXAMPLE_NOT_SINGLE_ANSWER",f"PERSONAL_RUBRIC_DRIFT:{row['practice_id']}")
            _req("correct_option_id" not in answer and "accepted_answers" not in answer,f"PERSONAL_SINGLE_ANSWER_FORBIDDEN:{row['practice_id']}")
            oral+=1

    _req(counts==Counter({f:48 for f in TEXT_FAMILIES}),f"TEXT_FAMILY_COUNTS_DRIFT:{dict(counts)}")
    _req(bundles==48,"MATCH_BUNDLE_COUNT_DRIFT")
    _req(productive==48 and oral==48 and deterministic==240,"ANSWER_MODE_TOTAL_DRIFT")
    return {
        "task_id":TASK_ID,"status":STATUS,
        "ket_text_authored_count":336,
        "ket_media_pending_count":336,
        "text_family_counts":dict(counts),
        "matching_bundle_review_pass_count":bundles,
        "deterministic_count":deterministic,
        "productive_count":productive,
        "oral_count":oral,
        "all_gpt56_reviews_pass":True,
        "next_short_step":NEXT_SHORT_STEP,
    }

def main()->int:
    print(json.dumps(build_report(),ensure_ascii=False,indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
