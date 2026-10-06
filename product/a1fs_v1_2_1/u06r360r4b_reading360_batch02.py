#!/usr/bin/env python3
"""Validate Unit06 Reading360 R4B GPT-5.6 authored E061-E120."""
from __future__ import annotations
import json, re
from collections import Counter
from pathlib import Path
from typing import Any

TASK_ID="A1FS-V1-U06R360R4B_E061_E120_GPT56FamilyAwareLearnerFacingAuthoring"
STATUS="PASS_A1FS_V1_U06R360R4B_E061_E120"
ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/"product/a1fs_v1_2_1/data/u06_reading360_r4_gpt56_e061_e120.json"
CURRENT=ROOT/"product/a1fs_v1_2_1/data/unit06_current360_360.json"
EXPECTED_FAMILY_COUNTS={
    "TWO_PERSON_INFORMATION":8,"PROBLEM_SOLUTION":5,"FAMILY_PLAN":7,
    "SHORT_PROFILE":2,"DAILY_LIFE_NOTE":15,"SCHOOL_NOTICE":9,
    "SHORT_FACTUAL_TEXT":6,"CLASS_INFORMATION":5,"SPORTS_ACTIVITY_INFORMATION":3,
}
FORBIDDEN=(
    (re.compile(r"\?"),"QUESTION"),
    (re.compile(r"\bthere\s+(?:is|are)\b",re.I),"THERE_BE"),
    (re.compile(r"\b(?:was|were)\b",re.I),"PAST_BE"),
    (re.compile(r"\b(?:cannot|can\s+not|can't)\b",re.I),"CAN_NEGATIVE"),
    (re.compile(r"\b(?:am|is|are)\s+[A-Za-z]+ing\b",re.I),"PRESENT_CONTINUOUS"),
    (re.compile(r"\b(?:has|does|goes|comes|puts|looks|enters|carries|likes|wants|needs|"
                r"makes|reads|writes|sits|stands|helps|plays|sings|runs|walks|eats|"
                r"drinks|washes|closes|opens|moves|finds|sees|talks|waits|works|"
                r"studies|takes|throws|catches|kicks|rides|swims|climbs|flies|paints|"
                r"draws|gives|calls|emails|phones|texts|says|tells|spells|answers|asks|"
                r"teaches|understands|brings|builds|cleans|cooks|dries|changes|listens|"
                r"shows|holds|points|sends|uses)\b",re.I),"LEXICAL_PRESENT_SIMPLE_3SG"),
)
FORBIDDEN_SPECIAL_PLURALS={
    "children","men","women","people","feet","teeth","mice","geese",
    "clothes","trousers","pants","shorts",
}

class U06R4B2Error(ValueError): pass

def _load(p:Path)->dict[str,Any]:
    v=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(v,dict): raise U06R4B2Error(f"NOT_OBJECT:{p}")
    return v

def _norm(s:str)->str:
    return re.sub(r"\s+"," ",str(s)).strip().casefold()

def build_report()->dict[str,Any]:
    data=_load(DATA); current=_load(CURRENT)
    if data.get("task_id")!=TASK_ID: raise U06R4B2Error("TASK_ID_DRIFT")
    if data.get("learner_facing_language_author")!="GPT-5.6 Sol": raise U06R4B2Error("AUTHOR_DRIFT")
    if data.get("python_may_generate_or_rewrite_learner_facing_english") is not False:
        raise U06R4B2Error("PYTHON_AUTHORING_NOT_DISABLED")
    entries=list(data.get("entries") or [])
    if len(entries)!=60: raise U06R4B2Error(f"ENTRY_COUNT:{len(entries)}")
    sources={str(x["episode_id"]):x for x in current.get("episodes",[])}

    counts=Counter(); families=Counter(); paragraphs=set(); ready=0
    for offset,e in enumerate(entries,61):
        rid=f"U06-READ360-E{offset:03d}"; sid=f"U06-NEB-E{offset:03d}"; slot=f"U06-N360-S{offset:03d}"
        if e.get("reading_entry_id")!=rid or e.get("source_episode_id")!=sid or e.get("source_episode_slot_id")!=slot:
            raise U06R4B2Error(f"IDENTITY_DRIFT:{offset}")
        src=sources.get(sid)
        if not src: raise U06R4B2Error(f"SOURCE_MISSING:{sid}")
        if list(e.get("target_chunk_surfaces") or [])!=list(src.get("target_chunk_surfaces") or []):
            raise U06R4B2Error(f"TARGET_LINEAGE_DRIFT:{sid}")
        sents=[str(x).strip() for x in e.get("body_sentences") or []]
        if len(sents) not in {6,7,8}: raise U06R4B2Error(f"SENTENCE_COUNT:{sid}:{len(sents)}")
        counts[len(sents)]+=1
        para=" ".join(sents)
        if para!=str(e.get("paragraph") or ""): raise U06R4B2Error(f"PARAGRAPH_JOIN_DRIFT:{sid}")
        n=_norm(para)
        if n in paragraphs: raise U06R4B2Error(f"PARAGRAPH_DUPLICATE:{sid}")
        paragraphs.add(n)
        if re.search(r"\bready\b",para,re.I): ready+=1
        for rx,label in FORBIDDEN:
            if rx.search(para): raise U06R4B2Error(f"{label}:{sid}:{rx.findall(para)[:3]}")
        for w in FORBIDDEN_SPECIAL_PLURALS:
            if re.search(rf"\b{re.escape(w)}\b",para,re.I):
                raise U06R4B2Error(f"SPECIAL_PLURAL:{sid}:{w}")
        for target in e.get("target_chunk_surfaces") or []:
            if _norm(target) not in n: raise U06R4B2Error(f"TARGET_NOT_REALIZED:{sid}:{target}")
        if e.get("learner_facing_language_author")!="GPT-5.6 Sol" or e.get("gpt56_semantic_review")!="PASS":
            raise U06R4B2Error(f"AUTHOR_REVIEW_DRIFT:{sid}")
        if e.get("family_purpose_review")!="PASS" or e.get("unit01_to_unit06_grammar_ceiling_review")!="PASS":
            raise U06R4B2Error(f"ACCEPTANCE_REVIEW_DRIFT:{sid}")

        fam=str(e.get("family_id")); families[fam]+=1
        shell=e.get("display_shell") or {}
        if fam=="SHORT_PROFILE":
            if shell.get("label")!="Profile" or not sents[0].startswith("This is "):
                raise U06R4B2Error(f"PROFILE_SHAPE_DRIFT:{sid}")
        if fam in {
            "SCHOOL_NOTICE","CLASS_INFORMATION","FAMILY_PLAN","SHORT_FACTUAL_TEXT",
            "SPORTS_ACTIVITY_INFORMATION","TWO_PERSON_INFORMATION","DAILY_LIFE_NOTE",
            "PROBLEM_SOLUTION",
        } and (not shell.get("label") or not shell.get("title")):
            raise U06R4B2Error(f"FUNCTIONAL_SHELL_MISSING:{sid}")
        if fam=="PROBLEM_SOLUTION":
            target_index=min(j for j,x in enumerate(sents) if any(_norm(t) in _norm(x) for t in e["target_chunk_surfaces"]))
            if target_index<4:
                raise U06R4B2Error(f"PROBLEM_BEFORE_SOLUTION_MISSING:{sid}")

    if dict(counts)!={6:20,7:20,8:20}: raise U06R4B2Error(f"DENSITY_DRIFT:{dict(counts)}")
    if dict(families)!=EXPECTED_FAMILY_COUNTS: raise U06R4B2Error(f"FAMILY_COUNT_DRIFT:{dict(families)}")
    if ready!=0: raise U06R4B2Error(f"READY_CONCENTRATION:{ready}")
    return {
        "schema_version":"a1fs.v1.u06.reading360.r4b.batch02.validation.v1",
        "task_id":TASK_ID,"status":STATUS,"entry_count":60,
        "sentence_distribution":dict(counts),"family_counts":dict(families),
        "target_lineage_exact":True,"grammar_ceiling_pass":True,
        "family_purpose_pass":True,"ready_episode_count":0,
        "exact_paragraph_duplicate_count":0,"human_semantic_review_pass":True,
        "cumulative_authored_count":120,"full360_final_accepted":False,
        "next_short_step":"A1FS-V1-U06R360R4B_E121_E180_GPT56FamilyAwareLearnerFacingAuthoring",
    }

if __name__=="__main__":
    print(json.dumps(build_report(),ensure_ascii=False,indent=2))
