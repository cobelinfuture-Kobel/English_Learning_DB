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
    if full.get("status") == "SOURCE_PURPOSE_MAPPING_ONLY_NOT_ADMITTED":
        _require(full.get("canonical_role") ==
                 "UNIT06_WRITING360_SOURCE_PURPOSE_MAPPING_DRAFT_NO_LEARNER_TEXT",
                 "MAPPING_ROLE_DRIFT")
        _require(full.get("full360_materialization_allowed") is False,
                 "MAPPING_IMPROPERLY_UNLOCKED")
        _require(full.get("approved_pilot_count") == 15
                 and full.get("mapping_only_pending_authoring_count") == 345,
                 "MAPPING_DENOMINATOR_DRIFT")
        _require(full.get("pending345_authoring_model_required") == "GPT-5.6"
                 and full.get("pending345_semantic_and_pedagogical_qa_required") is True,
                 "MAPPING_MODEL_QA_POLICY_DRIFT")
        pilot_by_source = {x["source_episode_id"]: x for x in p["pilots"]}
        assigned = set()
        operation_counts = {}
        for i, row in enumerate(full["entries"], start=1):
            sid = f"U06-NEB-E{i:03d}"
            rid = f"U06-WRITE-E{i:03d}"
            _require(row.get("source_episode_id") == sid
                     and row.get("writing_entry_id") == rid
                     and sid not in assigned,
                     f"MAPPING_IDENTITY_DRIFT:{rid}")
            assigned.add(sid)
            src = episodes[sid]
            _require(row.get("source_episode_slot_id") == src["episode_slot_id"]
                     and [x.casefold() for x in row.get("target_chunk_surfaces", [])] ==
                     [x.casefold() for x in src["target_chunk_surfaces"]],
                     f"MAPPING_TARGET_DRIFT:{rid}")
            quotes = row.get("source_evidence", {})
            _require(all(quotes.get(k) and quotes[k] in src["paragraph"]
                         for k in ("scene_intro_exact", "detail_exact", "ability_exact")),
                     f"MAPPING_SOURCE_EVIDENCE_DRIFT:{rid}")
            _require(any(t.casefold() in quotes["ability_exact"].casefold()
                         for t in row["target_chunk_surfaces"]),
                     f"MAPPING_ABILITY_EVIDENCE_DRIFT:{rid}")
            operation = row.get("writing_operation")
            _require(operation in OP_COUNTS,
                     f"MAPPING_UNKNOWN_OPERATION:{rid}")
            operation_counts[operation] = operation_counts.get(operation, 0) + 1
            _require(row.get("writing_focus_zh") and
                     row.get("operation_selection_reason_zh") and
                     all(quotes[k] in row["operation_selection_reason_zh"]
                         for k in ("scene_intro_exact", "detail_exact", "ability_exact")),
                     f"MAPPING_SELECTION_REASON_MISSING:{rid}")
            _require(not any(k in row for k in (
                "learner_page", "teacher_only", "model_answer", "full_model_text")),
                     f"UNAPPROVED_LEARNER_TEXT_MATERIALIZED:{rid}")
            _require(row.get("writing_model_answer_materialized") is False
                     and row.get("gpt56_authoring_evidence") is None
                     and row.get("gpt56_semantic_qa_evidence") is None,
                     f"FALSE_GPT56_QA_CLAIM:{rid}")
            if sid in pilot_by_source:
                _require(row.get("pilot_id") == pilot_by_source[sid]["id"]
                         and operation == pilot_by_source[sid]["operation"]
                         and row.get("writing_content_status") ==
                         "PILOT_APPROVED_REFER_TO_CANONICAL_PILOT15",
                         f"PILOT_MUST_RETAIN_APPROVED_OPERATION:{rid}")
            else:
                _require(row.get("pilot_id") is None
                         and row.get("writing_content_status") ==
                         "MAPPING_ONLY_AWAIT_GPT56_PER_ENTRY_AUTHORING"
                         and row.get("operation_assignment_origin") ==
                         "GPT6_SOURCE_GROUNDED_MAPPING_PREFLIGHT_NOT_GPT56",
                         f"UNAPPROVED_WRITING_ADMITTED:{rid}")
        _require(assigned == set(episodes), "MAPPING_SOURCE_COVERAGE_DRIFT")
        _require(full.get("writing_operation_counts") == operation_counts,
                 "MAPPING_OPERATION_COUNT_DRIFT")
        return {
            "status": "PASS_WRITING360_SOURCE_PURPOSE_MAPPING_GATE",
            "approved": 15,
            "not_yet_admitted": 345,
            "full360_admitted": False,
            "mapped_source_count": 360,
            "operation_counts": operation_counts,
            "pilot_operation_counts": ops,
        }

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
