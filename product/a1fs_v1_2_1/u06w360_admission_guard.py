"""Unit06 Writing360 admission guard.

Mechanical validation only. This code does not author learner-facing English.
The GPT-5.6 authoring and semantic/pedagogical reviews require separate evidence.
"""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/"product/a1fs_v1_2_1/data"
PILOT=DATA/"unit06_writing360_pilot15_approved.json"
CURRENT=DATA/"unit06_current360_360.json"
FULL=DATA/"unit06_writing360_360.json"
OP_COUNTS={"COPY_AND_CHANGE":4,"TABLE_TO_SENTENCES":4,
           "SENTENCE_PLAN":4,"GUIDED_MINI_TEXT":3}
PILOT_IDS={1,21,41,61,81,101,121,141,161,181,201,221,241,281,341}


class AdmissionError(ValueError):
    pass


def _load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def _require(pred,code):
    if not pred:
        raise AdmissionError(code)


def validate():
    p=_load(PILOT)
    source=_load(CURRENT)
    episodes={x["episode_id"]:x for x in source["episodes"]}
    _require(len(episodes)==360,"CURRENT360_SOURCE_INCOMPLETE")
    _require(len(p["pilots"])==15,"PILOT15_COUNT_DRIFT")
    _require(p.get("human_acceptance_status")=="PILOT15_APPROVED_BY_OPERATOR",
             "PILOT15_NOT_ACCEPTED")
    _require(p.get("full360_materialization_allowed") is False,
             "UNREVIEWED_FULL360_UNLOCK")
    _require(p.get("admission_rule",{}).get("programmatic_content_generation_permitted") is False,
             "PROGRAMMATIC_WRITING_AUTHORING_UNBLOCKED")
    _require(p.get("admission_rule",{}).get("model_author")=="GPT-5.6",
             "MODEL_AUTHORITY_DRIFT")
    ops={key:0 for key in OP_COUNTS}
    seen=set()
    for e in p["pilots"]:
        ident=e["source_episode_id"]
        number=int(ident.rsplit("E",1)[1])
        _require(number in PILOT_IDS,"UNAPPROVED_EPISODE")
        _require(number not in seen,"PILOT_DUPLICATE")
        seen.add(number)
        _require(e["writing_entry_id"]==f"U06-WRITE-PILOT-E{number:03d}",
                 f"WRITING_ID_DRIFT:{ident}")
        _require(e["human_review_status"]=="OPERATOR_APPROVED",
                 f"PILOT_ITEM_UNAPPROVED:{ident}")
        src=episodes[ident]
        _require(src["episode_slot_id"]==e["source_episode_slot_id"],
                 f"SLOT_ID_DRIFT:{ident}")
        _require([x.casefold() for x in src["target_chunk_surfaces"]]==
                 [x.casefold() for x in e["target_chunk_surfaces"]],
                 f"TARGET_LINEAGE_DRIFT:{ident}")
        answer=" ".join(e["model_answer"]).casefold()
        _require(all(t.casefold() in answer for t in e["target_chunk_surfaces"]),
                 f"TARGET_NOT_IN_ANSWER:{ident}")
        op=e["operation"]
        _require(op in ops,f"UNRECOGNISED_OPERATION:{ident}")
        ops[op]+=1
        _require(e["facts"] and e["word_bank"] and e["sentence_frames"],
                 f"SUPPORT_MISSING:{ident}")
        if op=="COPY_AND_CHANGE":
            _require(e.get("given_model") and e.get("change_cue"),
                     f"SUBSTITUTION_MISSING:{ident}")
        else:
            page=e.get("learner_page",{})
            teacher=e.get("teacher_only",{})
            _require(page.get("fact_card") and page.get("worked_example")
                     and page.get("write_sentence_steps")
                     and page.get("word_bank")
                     and page.get("full_version_task"),
                     f"LEARNER_PAGE_INCOMPLETE:{ident}")
            _require(teacher.get("model_answer")==e["model_answer"],
                     f"TEACHER_ANSWER_DRIFT:{ident}")
    _require(seen==PILOT_IDS,"PILOT_EPISODE_SET_DRIFT")
    _require(ops==OP_COUNTS,"PILOT_OPERATION_DISTRIBUTION_DRIFT")

    if not FULL.exists():
        return {
            "status":"PASS_WRITING360_PILOT15_ADMISSION_GUARD",
            "approved":15,"not_yet_admitted":345,
            "full360_admitted":False,"pilot_operation_counts":ops,
        }

    full=_load(FULL)
    _require(full.get("entry_count")==360
             and len(full.get("entries",[]))==360,
             "FULL360_COUNT_DRIFT")
    # Reusing Current360 sentences is NOT proof of per-entry model authoring.
    for e in full["entries"]:
        rid=e.get("writing_entry_id","UNKNOWN")
        evidence=e.get("authoring_evidence",{})
        qa=e.get("review_evidence",{})
        _require(evidence.get("model")=="GPT-5.6"
                 and evidence.get("source_ref")
                 and evidence.get("content_provenance_ref"),
                 f"MODEL_AUTHORING_EVIDENCE_MISSING:{rid}")
        _require(qa.get("model")=="GPT-5.6"
                 and qa.get("semantic")=="PASS"
                 and qa.get("pedagogical_answerability")=="PASS"
                 and qa.get("grammar_ceiling")=="PASS"
                 and qa.get("source_fact_grounding")=="PASS"
                 and qa.get("review_ref"),
                 f"MODEL_QA_EVIDENCE_MISSING:{rid}")
        _require(e.get("learner_page") and e.get("teacher_only"),
                 f"WRITING_ACTIVITY_MISSING:{rid}")
    return {"status":"PASS_WRITING360_FULL360_EVIDENCE_SCHEMA",
            "approved":360,"not_yet_admitted":0,
            "full360_admitted":True,"pilot_operation_counts":ops}


if __name__=="__main__":
    print(json.dumps(validate(),ensure_ascii=False,indent=2))
