from __future__ import annotations
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

A1FS_CONTENT_POLICY_MODE = "VALIDATOR_ONLY"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Validates the GPT-5.6 Reader360-backed Core480 R2 materialization. "
    "Python validates lineage, answerability, uniqueness, source binding and learner-facing quality; "
    "it does not author or rewrite learner-facing English."
)
TASK_ID="A1FS-V1-U05FAR7_Core480GPT56LearnerFacingMaterialization"
STATUS="PASS_A1FS_V1_U05FAR7_CORE480_GPT56_READER360_BACKED_R2"
NEXT_SHORT_STEP="A1FS-V1-U05FAR7_KETText336GPT56LearnerFacingMaterialization"

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/"product/a1fs_v1_2_1/data"
CORE=DATA/"unit05_core_practice_480.json"
FAR2=DATA/"unit05_coverage_driven_practice_slots.json"
FAR3=DATA/"unit05_learner_facing_practice_materialization_contract.json"
FAR4=DATA/"unit05_gpt56_practice_materialization_preflight.json"
PATTERN=DATA/"unit05_pattern360_360.json"
CURRENT=DATA/"unit05_current360_360.json"
SPOKEN=DATA/"unit05_spoken360_360.json"
Q05=ROOT/"ulga/contracts/a1fs_v1_u05_q05_core_sentence_frame_authority.json"

BANNED=("children","people","feet","men","women")
REVIEWS=("gpt56_semantic_review","gpt56_pedagogical_review","gpt56_source_grounding_review","gpt56_unit05_scope_review","gpt56_answerability_review")
GAP_ARCHETYPES={"BE_FORM_SELECTION","ONE_WORD_BE_COMPLETION","SUBJECT_BE_AGREEMENT"}

class U05FAR7CoreError(ValueError): pass
def _load(p:Path)->dict[str,Any]:
    x=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(x,dict): raise U05FAR7CoreError(f"NOT_OBJECT:{p}")
    return x
def _req(ok:bool,code:str)->None:
    if not ok: raise U05FAR7CoreError(code)
def _be(text:str)->str:
    m=re.search(r"\b(am|is|are)\b",text,re.I)
    return m.group(1).lower() if m else ""
def _pattern_texts(entry:dict[str,Any])->set[str]:
    return {
        ex["text"]
        for fam in entry.get("families",{}).values()
        for ex in fam.get("examples",[])
        if isinstance(ex,dict) and isinstance(ex.get("text"),str)
    }
def _signature(row:dict[str,Any])->str:
    c=row["learner_facing_content"]; r=row["response_contract"]
    return json.dumps([c.get("prompt"),r.get("options"),(c.get("stimulus") or {}).get("text"),c.get("model_sentence")],ensure_ascii=False,sort_keys=True)

def build_report()->dict[str,Any]:
    core,far2,far3,far4,pattern,current,spoken,q05=map(_load,(CORE,FAR2,FAR3,FAR4,PATTERN,CURRENT,SPOKEN,Q05))
    _req(core["schema_version"]=="a1fs.v1.u05.far7.core480.reader360.r2","SCHEMA_DRIFT")
    _req(core["item_count"]==480 and len(core["items"])==480,"CORE_COUNT_DRIFT")
    _req(core["authored_item_count"]==480,"AUTHOR_COUNT_DRIFT")
    _req(core["status"]=="PASS_CORE480_GPT56_READER360_BACKED_R2","STATUS_DRIFT")
    _req(core["python_or_code_may_author_learner_facing_english"] is False,"CODE_AUTHORING_UNLOCKED")
    _req("static_template_bank" not in core,"LEGACY_STATIC_TEMPLATE_BANK_STILL_AUTHORITY")

    meta=core["reader360_backed_materialization"]
    _req(meta["learner_target_sentence_unique_count"]==480,"TARGET_UNIQUENESS_META_DRIFT")
    _req(meta["activity_signature_unique_count"]==480,"ACTIVITY_UNIQUENESS_META_DRIFT")
    _req(meta["pattern360_target_count"]+meta["gpt56_controlled_transfer_target_count"]==480,"TARGET_SOURCE_DENOMINATOR_DRIFT")
    _req(meta["old_static_template_bank_retired"] is True,"STATIC_BANK_NOT_RETIRED")

    pattern_by_ref={x["reader_entry_id"]:x for x in pattern["entries"]}
    current_ids={x["episode_id"] for x in current["episodes"]}
    spoken_by_ref={x["reader_entry_id"]:x for x in spoken["entries"]}
    q05_be={x["subject_class"]:x["be_surface"] for x in q05["subject_be_resolution"]["affirmative_full"]}
    allowed=set(far3["core_grammar_materialization_contract"]["allowed_practice_archetypes"])
    slots={x["slot_id"]:x for x in far2["core_grammar_slots"]}
    quota=far4["full_production_core_archetype_quota_plan"]["quotas_by_frame"]

    actual:dict[str,Counter[str]]= {}
    target_sentences:list[str]=[]
    signatures:list[str]=[]
    source_counts=Counter()
    context_counts=Counter()
    correction=productive=deterministic=0

    for row in core["items"]:
        pid=row["practice_id"]; src=slots[row["source_slot_id"]]
        for key in ("practice_set_id","stage","episode_id","frame_id","subject_class","place_relation","polarity","complement_class"):
            _req(row[key]==src[key],f"LINEAGE_DRIFT:{pid}:{key}")
        _req(row["reader_source_refs"]==[src["reader_ref"]],f"SLOT_READER_LINEAGE_DRIFT:{pid}")
        _req(row["target_archetype"] in allowed,f"ARCHETYPE_INVALID:{pid}")
        _req(row["materialization_status"]=="MATERIALIZED_READER360_BACKED_GPT56_REVIEW_PASS",f"MATERIALIZATION_STATUS_DRIFT:{pid}")
        _req(row["execution_status"]=="EXECUTABLE_TEXT_ONLY",f"EXECUTION_STATUS_DRIFT:{pid}")
        _req(all(row[k]=="PASS" for k in REVIEWS),f"GPT56_REVIEW_NOT_PASS:{pid}")

        c=row["learner_facing_content"]; a=row["answer_binding_or_rubric"]; r=row["response_contract"]
        _req(isinstance(c,dict) and isinstance(a,dict) and isinstance(r,dict),f"LEARNER_PAYLOAD_MISSING:{pid}")
        _req(c.get("source_example") is None and c.get("source_example_visible_during_attempt") is False,f"LEGACY_EXAMPLE_CARD_ACTIVE:{pid}")
        target=c["learner_target_sentence"]
        _req(isinstance(target,str) and target.endswith("."),f"TARGET_SENTENCE_INVALID:{pid}")
        _req(not any(re.search(rf"\b{re.escape(token)}\b",json.dumps(c,ensure_ascii=False),re.I) for token in BANNED),f"BANNED_IRREGULAR_PLURAL:{pid}")
        _req(not re.search(r"\bthe students\s+___\s+(?:not\s+)?students\b",c["prompt"],re.I),f"TAUTOLOGY_REINTRODUCED:{pid}")
        sig=c["target_signature"]
        _req(sig["subject_class"]==row["subject_class"] and sig["complement_class"]==row["complement_class"] and sig["polarity"]==row["polarity"],f"TARGET_SIGNATURE_DRIFT:{pid}")
        expected_be=q05_be[row["subject_class"]]
        _req(sig["be_form"]==expected_be and _be(target)==expected_be,f"TARGET_BE_DRIFT:{pid}")
        _req(c["subject_cue"] and target.startswith(c["subject_cue"]+" "),f"SUBJECT_CUE_TARGET_DRIFT:{pid}")

        source=c["learner_target_source"]; mode=source["source_mode"]; source_counts[mode]+=1
        if mode=="PATTERN360":
            ref=source["reader_entry_id"]; _req(ref in pattern_by_ref,f"TARGET_PATTERN_REF_MISSING:{pid}")
            pe=pattern_by_ref[ref]
            _req(source["episode_id"]==pe["source_episode_id"],f"TARGET_PATTERN_EPISODE_DRIFT:{pid}")
            _req(target in _pattern_texts(pe),f"TARGET_NOT_EXACT_PATTERN360:{pid}")
        else:
            _req(mode=="GPT56_CONTROLLED",f"TARGET_SOURCE_MODE_INVALID:{pid}:{mode}")
            _req(source["reader_entry_id"] is None and source["evidence_mode"]=="CONTROLLED_TRANSFER_NOT_SOURCE_FACT",f"CONTROLLED_SOURCE_CONTRACT_DRIFT:{pid}")

        stimulus=c.get("stimulus")
        if row["stage"]=="GUIDED":
            _req(isinstance(stimulus,dict),f"GUIDED_CONTEXT_MISSING:{pid}")
            _req(stimulus["source_mode"] in {"CURRENT360","GPT56_CONTROLLED_CONTEXT"},f"GUIDED_CONTEXT_MODE:{pid}")
        elif row["stage"]=="REDUCED_SUPPORT":
            _req(isinstance(stimulus,dict),f"REDUCED_CONTEXT_MISSING:{pid}")
            _req(stimulus["source_mode"] in {"SPOKEN360","GPT56_CONTROLLED_CONTEXT"},f"REDUCED_CONTEXT_MODE:{pid}")
        else:
            _req(stimulus is None,f"LATE_STAGE_CONTEXT_SHOULD_BE_HIDDEN:{pid}")
        if stimulus:
            context_counts[stimulus["source_mode"]]+=1
            _req(isinstance(stimulus.get("text"),str) and stimulus["text"].strip(),f"EMPTY_CONTEXT:{pid}")
            if stimulus["source_mode"]=="CURRENT360":
                _req(stimulus["source_ref"] in current_ids,f"CURRENT_CONTEXT_REF_MISSING:{pid}")
                if mode=="PATTERN360": _req(stimulus["episode_id"]==source["episode_id"],f"CURRENT_CONTEXT_EPISODE_DRIFT:{pid}")
            elif stimulus["source_mode"]=="SPOKEN360":
                _req(stimulus["source_ref"] in spoken_by_ref,f"SPOKEN_CONTEXT_REF_MISSING:{pid}")
                if mode=="PATTERN360": _req(stimulus["episode_id"]==source["episode_id"],f"SPOKEN_CONTEXT_EPISODE_DRIFT:{pid}")
            else:
                _req(stimulus["source_mode"]=="GPT56_CONTROLLED_CONTEXT",f"CONTEXT_MODE_INVALID:{pid}")

        if row["target_archetype"] in GAP_ARCHETYPES:
            _req("___" in c["prompt"] and c["subject_cue"] in c["prompt"],f"GAP_SUBJECT_NOT_VISIBLE:{pid}")
        if row["target_archetype"] in {"BE_FORM_SELECTION","SUBJECT_BE_AGREEMENT"}:
            _req(a["correct_option"]==expected_be and r["options"]==["am","is","are"],f"SELECT_ANSWER_DRIFT:{pid}"); deterministic+=1
        elif row["target_archetype"]=="ONE_WORD_BE_COMPLETION":
            _req(a["accepted_answers"]==[expected_be],f"ONE_WORD_ANSWER_DRIFT:{pid}"); deterministic+=1
        elif row["target_archetype"]=="AFFIRMATIVE_NEGATIVE_CONTRAST":
            _req(a["correct_option_id"]==("B" if row["polarity"]=="NEGATIVE" else "A"),f"POLARITY_ANSWER_DRIFT:{pid}")
            _req(len(r.get("options") or [])==2,f"POLARITY_OPTIONS_DRIFT:{pid}"); deterministic+=1
        elif row["target_archetype"]=="SENTENCE_CORRECTION":
            _req(a["accepted_full_answers"]==[target],f"CORRECTION_TARGET_DRIFT:{pid}")
            _req(c["prompt"]!=target,f"CORRECTION_NOT_ACTUALLY_WRONG:{pid}"); correction+=1; deterministic+=1
        else:
            _req(r["type"]=="FREE_TEXT",f"PRODUCTIVE_RESPONSE_DRIFT:{pid}")
            _req(a.get("model_response_example")==target,f"PRODUCTIVE_MODEL_DRIFT:{pid}")
            _req("correct_option" not in a and "accepted_answers" not in a and "accepted_full_answers" not in a,f"PRODUCTIVE_SINGLE_ANSWER_FORBIDDEN:{pid}")
            productive+=1

        target_sentences.append(target); signatures.append(_signature(row))
        actual.setdefault(row["frame_id"],Counter())[row["target_archetype"]]+=1

    for frame,expected in quota.items():
        _req(dict(actual[frame])==expected,f"QUOTA_DRIFT:{frame}:{dict(actual[frame])}")
    _req(Counter(x["target_archetype"] for x in core["items"])=={a:80 for a in allowed},"ARCHETYPE_GLOBAL_BALANCE_DRIFT")
    _req(len(set(target_sentences))==480,"TARGET_SENTENCE_DUPLICATION")
    _req(len(set(signatures))==480,"ACTIVITY_SIGNATURE_DUPLICATION")
    _req(correction==80 and productive==80 and deterministic==400,"ANSWER_MODE_COUNT_DRIFT")
    _req(source_counts==Counter({"PATTERN360":372,"GPT56_CONTROLLED":108}),f"TARGET_SOURCE_COUNT_DRIFT:{dict(source_counts)}")
    _req(sum(context_counts.values())==240,f"VISIBLE_CONTEXT_COUNT_DRIFT:{dict(context_counts)}")

    return {
        "task_id":TASK_ID,"status":STATUS,"core_authored_count":480,
        "deterministic_count":deterministic,"productive_count":productive,
        "sentence_correction_count":correction,"archetype_count":len(allowed),
        "unique_target_sentence_count":len(set(target_sentences)),
        "unique_activity_signature_count":len(set(signatures)),
        "pattern360_target_count":source_counts["PATTERN360"],
        "controlled_transfer_target_count":source_counts["GPT56_CONTROLLED"],
        "visible_context_count":sum(context_counts.values()),
        "context_mode_counts":dict(context_counts),
        "legacy_static_template_bank_retired":True,
        "all_gpt56_reviews_pass":True,"next_short_step":NEXT_SHORT_STEP
    }

def main()->int:
    print(json.dumps(build_report(),ensure_ascii=False,indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
