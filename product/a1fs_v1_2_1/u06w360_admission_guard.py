"""Gate for Unit06 Writing360 pilot + GPT-6 authored batches.

Checks provenance and structure, NOT independent model review.
No learner-facing sentence generation is performed here.
"""
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/"product/a1fs_v1_2_1/data"
PILOT=DATA/"unit06_writing360_pilot15_approved.json"
SOURCE=DATA/"unit06_current360_360.json"
MAPPING=DATA/"unit06_writing360_360.json"
BATCH01=DATA/"unit06_writing360_gpt6_batch01_e002_e016.json"
OPS={"COPY_AND_CHANGE","TABLE_TO_SENTENCES","SENTENCE_PLAN","GUIDED_MINI_TEXT"}
FORBIDDEN=re.compile(r"\b(children|clothes|feet|women|men|people|mice|geese|teeth|was|were|cannot|can't)\b",re.I)

def require(ok,code):
    if not ok:
        raise ValueError(code)

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def validate():
    p=load(PILOT); s=load(SOURCE); m=load(MAPPING); b=load(BATCH01)
    sources={e["episode_id"]:e for e in s["episodes"]}
    pilot={e["source_episode_id"]:e for e in p["pilots"]}
    rows=m["entries"]; authored=b["entries"]
    require(len(sources)==len(rows)==360,"SOURCE_360_COUNT")
    require(len(pilot)==15 and p["human_acceptance_status"]=="PILOT15_APPROVED_BY_OPERATOR","PILOT15_STATUS")
    require(p["admission_rule"]["model_author"]=="GPT-6"
            and p["admission_rule"]["programmatic_content_generation_permitted"] is False,
            "MODEL_AUTHORITY_POLICY")
    require(m["status"]=="SOURCE_PURPOSE_MAPPING_WITH_GPT6_AUTHORING_BATCH01_PARTIAL"
            and m["full360_materialization_allowed"] is False,
            "PARTIAL_STATUS")
    require(m["mapping_only_pending_authoring_count"]==330
            and m["gpt6_authored_self_reviewed_count"]==15
            and m["approved_pilot_count"]==15,
            "PROGRESS_COUNT")
    require(len(authored)==b["entry_count"]==15
            and b["authoring_model"]==b["review_model"]=="GPT-6"
            and b["review_mode"]=="SAME_MODEL_EDITORIAL_SELF_REVIEW_NOT_INDEPENDENT"
            and b["programmatic_english_generation"] is False,
            "BATCH01_PROVENANCE")
    counts={o:0 for o in OPS}
    for i,row in enumerate(rows,1):
        sid=f"U06-NEB-E{i:03d}"; rid=f"U06-WRITE-E{i:03d}"
        src=sources[sid]
        require(row["source_episode_id"]==sid and row["writing_entry_id"]==rid,
                f"ROW_ID:{rid}")
        require(row["source_episode_slot_id"]==src["episode_slot_id"]
                and [x.casefold() for x in row["target_chunk_surfaces"]]
                    ==[x.casefold() for x in src["target_chunk_surfaces"]],
                f"ROW_LINEAGE:{rid}")
        evidence=row["source_evidence"]
        require(all(evidence[key] in src["paragraph"] for key in
                    ("scene_intro_exact","detail_exact","ability_exact")),
                f"SOURCE_QUOTE:{rid}")
        op=row["writing_operation"]
        require(op in OPS,f"OPERATION:{rid}")
        counts[op]+=1
        require(row["writing_focus_zh"] and row["operation_selection_reason_zh"],
                f"WRITING_PURPOSE:{rid}")
        require(not any(field in row for field in ("model_answer","learner_page","teacher_only")),
                f"MAPPING_TEXT_LEAK:{rid}")
        if sid in pilot:
            require(row["writing_content_status"]=="PILOT_APPROVED_REFER_TO_CANONICAL_PILOT15"
                    and row["pilot_id"]==pilot[sid]["id"]
                    and op==pilot[sid]["operation"],
                    f"PILOT_MAPPING_DRIFT:{rid}")
        elif 2<=i<=16:
            require(row["writing_content_status"]=="GPT6_BATCH01_AUTHORED_SELF_REVIEW_PASS"
                    and row["gpt6_authored_self_reviewed"] is True
                    and row["authoring_content_ref"]==
                    f"{BATCH01.relative_to(ROOT)}#{rid}",
                    f"BATCH01_MAPPING_DRIFT:{rid}")
        else:
            require(row["writing_content_status"]=="MAPPING_ONLY_AWAIT_GPT6_PER_ENTRY_AUTHORING"
                    and row["pilot_id"] is None,
                    f"FALSE_AUTHORSHIP:{rid}")
    require(counts==m["writing_operation_counts"],"OPERATION_COUNT")
    for j,e in enumerate(authored,2):
        sid=f"U06-NEB-E{j:03d}"; rid=f"U06-WRITE-E{j:03d}"
        src=sources[sid]; row=rows[j-1]
        require(e["writing_entry_id"]==rid and e["source_episode_id"]==sid
                and e["source_episode_slot_id"]==src["episode_slot_id"]
                and e["operation"]==row["writing_operation"]
                and e["target_chunk_surfaces"]==src["target_chunk_surfaces"],
                f"AUTHORED_ID:{rid}")
        answer=e["model_answer"]
        pg=e["learner_page"]; teacher=e["teacher_only"]
        require(len(answer) in (2,3,4) and all(x.endswith(".") for x in answer)
                and e["full_model_text"]==" ".join(answer)
                and all(t.casefold() in e["full_model_text"].casefold()
                        for t in src["target_chunk_surfaces"]),
                f"MODEL_ANSWER:{rid}")
        require(pg["worked_example"]["complete_sentence"]==answer[0]
                and len(pg["write_sentence_steps"])==len(answer)
                and pg["word_bank"] and pg["fact_card"]
                and len(pg["sentence_plan"])==len(answer)
                and pg["blank_full_version_line_count"]==len(answer)
                and pg["full_version_task"],
                f"LEARNER_SUPPORT:{rid}")
        require(teacher["model_answer"]==answer
                and teacher["show_after_submission"] is True,
                f"ANSWER_DRIFT:{rid}")
        auth=e["authoring_evidence"]; qa=e["review_evidence"]
        require(auth["model"]=="GPT-6"
                and auth["source_episode_id"]==sid
                and auth["source_ref"] and auth["content_provenance_ref"],
                f"AUTHORING_EVIDENCE:{rid}")
        require(qa["model"]=="GPT-6"
                and qa["review_mode"]=="SAME_MODEL_EDITORIAL_SELF_REVIEW_NOT_INDEPENDENT"
                and qa["review_note"] and qa["review_ref"]
                and all(qa[k]=="PASS" for k in
                    ("semantic","pedagogical_answerability","grammar_ceiling",
                     "source_fact_grounding","writing_operation_fit")),
                f"REVIEW_EVIDENCE:{rid}")
        check=" ".join(answer+[x["sentence_frame"] for x in pg["write_sentence_steps"]])
        require(FORBIDDEN.search(check) is None,f"WORD_FORM_BOUNDARY:{rid}")
        require(re.search(r"\bcan\s+(not|to)\b",check,re.I) is None,
                f"CAN_BOUNDARY:{rid}")
        modes=[x["response_mode"] for x in pg["write_sentence_steps"][1:]]
        if e["operation"]=="TABLE_TO_SENTENCES":
            require(len(answer)==3 and teacher["frame_blank_answers"]
                    and len(teacher["frame_blank_answers"])==2
                    and modes==["FILL_ONE_WORD","FILL_ONE_WORD"],
                    f"TABLE_CLOZE:{rid}")
        if e["operation"]=="SENTENCE_PLAN":
            require(len(answer)==3 and modes==["WRITE_FULL_SENTENCE_FROM_CUES"]*2,
                    f"SENTENCE_PLAN_OUTPUT:{rid}")
        if e["operation"]=="GUIDED_MINI_TEXT":
            require(len(answer)==4 and modes==["WRITE_FULL_SENTENCE_FROM_CUES"]*3,
                    f"MINITEXT_OUTPUT:{rid}")
        if e["operation"]=="COPY_AND_CHANGE":
            require(pg["original_model_sentence"] and pg["change_cue"]
                    and modes==["SUBSTITUTE_SUBJECT_AND_WRITE_FULL_SENTENCE"],
                    f"SUBSTITUTION_OUTPUT:{rid}")
    return {
        "status":"PASS_WRITING360_GPT6_BATCH01_PARTIAL_ADMISSION_GATE",
        "source_mapped":360,"operator_approved_pilot":15,
        "gpt6_authored_self_reviewed":15,"pending_authoring":330,
        "full360_admitted":False,"operation_distribution":counts
    }

if __name__=="__main__":
    print(json.dumps(validate(),ensure_ascii=False,indent=2))
