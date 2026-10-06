#!/usr/bin/env python3
"""Validate Unit06 Reading360 R5 full 360 canonical authority."""
from __future__ import annotations
import json,re
from collections import Counter
from pathlib import Path
from typing import Any

TASK_ID="A1FS-V1-U06R360R5_Full360CanonicalAuthority"
STATUS="PASS_A1FS_V1_U06R360R5_FULL360"
ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/"product/a1fs_v1_2_1/data/unit06_reading360_360.json"
CURRENT=ROOT/"product/a1fs_v1_2_1/data/unit06_current360_360.json"
EXPECTED_QUOTAS={
"PERSONAL_MESSAGE":28,"MINI_EMAIL":28,"SCHOOL_NOTICE":24,"EVENT_INFORMATION":24,
"SHORT_PROFILE":24,"PICTURE_LINKED_DESCRIPTION":24,"MAP_ROUTE_INFORMATION":24,
"DAILY_LIFE_NOTE":28,"CLASS_INFORMATION":24,"SHORT_FACTUAL_TEXT":20,
"TWO_PERSON_INFORMATION":20,"FAMILY_PLAN":20,"SPORTS_ACTIVITY_INFORMATION":24,
"SIMPLE_CONNECTED_STORY":24,"PROBLEM_SOLUTION":24,
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
FORBIDDEN_SPECIAL_PLURALS={"children","men","women","people","feet","teeth","mice","geese","clothes","trousers","pants","shorts"}

class U06R5Error(ValueError): pass

def _load(p:Path)->dict[str,Any]:
    v=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(v,dict): raise U06R5Error(f"NOT_OBJECT:{p}")
    return v

def _norm(s:str)->str:
    return re.sub(r"\s+"," ",str(s)).strip().casefold()

def build_report()->dict[str,Any]:
    data=_load(DATA); current=_load(CURRENT)
    if data.get("task_id")!=TASK_ID: raise U06R5Error("TASK_ID_DRIFT")
    if data.get("canonical_role")!="UNIT06_READING360_LEARNER_FACING_AUTHORITY":
        raise U06R5Error("CANONICAL_ROLE_DRIFT")
    if data.get("human_pilot_status")!="APPROVED_BY_OPERATOR":
        raise U06R5Error("HUMAN_PILOT_NOT_APPROVED")
    if data.get("learner_facing_language_author")!="GPT-5.6 Sol":
        raise U06R5Error("AUTHOR_DRIFT")
    if data.get("python_may_generate_or_rewrite_learner_facing_english") is not False:
        raise U06R5Error("PYTHON_AUTHORING_NOT_DISABLED")
    entries=list(data.get("entries") or [])
    if len(entries)!=360: raise U06R5Error(f"ENTRY_COUNT:{len(entries)}")
    sources={str(x["episode_id"]):x for x in current.get("episodes",[])}
    if len(sources)!=360: raise U06R5Error(f"SOURCE_COUNT:{len(sources)}")

    families=Counter(); density=Counter(); seen=set(); ready=0
    for idx,e in enumerate(entries,1):
        rid=f"U06-READ360-E{idx:03d}"; sid=f"U06-NEB-E{idx:03d}"; slot=f"U06-N360-S{idx:03d}"
        if e.get("reading_entry_id")!=rid or e.get("source_episode_id")!=sid or e.get("source_episode_slot_id")!=slot:
            raise U06R5Error(f"IDENTITY_DRIFT:{idx}")
        src=sources.get(sid)
        if not src: raise U06R5Error(f"SOURCE_MISSING:{sid}")
        if list(e.get("target_chunk_surfaces") or [])!=list(src.get("target_chunk_surfaces") or []):
            raise U06R5Error(f"TARGET_LINEAGE_DRIFT:{sid}")
        sents=[str(x).strip() for x in e.get("body_sentences") or []]
        if len(sents) not in {6,7,8}: raise U06R5Error(f"SENTENCE_COUNT:{sid}:{len(sents)}")
        density[len(sents)]+=1
        para=" ".join(sents)
        if para!=str(e.get("paragraph") or ""): raise U06R5Error(f"PARAGRAPH_JOIN_DRIFT:{sid}")
        n=_norm(para)
        if n in seen: raise U06R5Error(f"PARAGRAPH_DUPLICATE:{sid}")
        seen.add(n)
        if re.search(r"\bready\b",para,re.I): ready+=1
        for rx,label in FORBIDDEN:
            if rx.search(para): raise U06R5Error(f"{label}:{sid}:{rx.findall(para)[:3]}")
        for w in FORBIDDEN_SPECIAL_PLURALS:
            if re.search(rf"\b{re.escape(w)}\b",para,re.I):
                raise U06R5Error(f"SPECIAL_PLURAL:{sid}:{w}")
        for target in e.get("target_chunk_surfaces") or []:
            if _norm(target) not in n: raise U06R5Error(f"TARGET_NOT_REALIZED:{sid}:{target}")

        fam=str(e.get("family_id")); families[fam]+=1
        sh=e.get("display_shell") or {}
        if fam=="PERSONAL_MESSAGE":
            if not sh.get("greeting") or not sh.get("signoff") or not re.search(r"\b(?:I|my)\b",para,re.I):
                raise U06R5Error(f"PERSONAL_MESSAGE_SHAPE:{sid}")
        elif fam=="MINI_EMAIL":
            if any(not sh.get(k) for k in ("greeting","signoff","to","from","subject")) or not re.search(r"\b(?:I|my)\b",para,re.I):
                raise U06R5Error(f"MINI_EMAIL_SHAPE:{sid}")
        elif fam=="SHORT_PROFILE":
            if not sents[0].startswith("This is "): raise U06R5Error(f"PROFILE_SHAPE:{sid}")
        elif fam=="PICTURE_LINKED_DESCRIPTION":
            if sh.get("label")!="Look at the picture": raise U06R5Error(f"PICTURE_SHAPE:{sid}")
        elif fam=="MAP_ROUTE_INFORMATION":
            if not sh.get("start") or not sh.get("destination"): raise U06R5Error(f"MAP_ROUTE_SHAPE:{sid}")
        elif fam=="SIMPLE_CONNECTED_STORY":
            if not sents[0].startswith("First,"): raise U06R5Error(f"CONNECTED_STORY_SHAPE:{sid}")
        elif fam=="PROBLEM_SOLUTION":
            ti=min(i for i,x in enumerate(sents) if any(_norm(t) in _norm(x) for t in e["target_chunk_surfaces"]))
            if ti<4: raise U06R5Error(f"PROBLEM_BEFORE_SOLUTION:{sid}")
        else:
            if not sh.get("label") or not sh.get("title"): raise U06R5Error(f"FUNCTIONAL_SHELL_MISSING:{sid}")

    if dict(families)!=EXPECTED_QUOTAS: raise U06R5Error(f"FAMILY_QUOTA_DRIFT:{dict(families)}")
    if dict(density)!={6:120,7:120,8:120}: raise U06R5Error(f"DENSITY_DRIFT:{dict(density)}")
    if ready!=0: raise U06R5Error(f"READY_CONCENTRATION:{ready}")

    return {
      "schema_version":"a1fs.v1.u06.reading360.r5.full360.validation.v1",
      "task_id":TASK_ID,"status":STATUS,"entry_count":360,
      "exact_family_quota":dict(families),"sentence_distribution":dict(density),
      "target_lineage_exact":True,"grammar_ceiling_pass":True,
      "family_purpose_structure_pass":True,"ready_episode_count":0,
      "exact_paragraph_duplicate_count":0,"human_pilot_approved":True,
      "full360_final_accepted":True,
      "next_short_step":"A1FS-V1-U06R360R5_PostMergeCanonicalReadbackAndDownstreamConsumerPreflight",
    }

if __name__=="__main__":
    print(json.dumps(build_report(),ensure_ascii=False,indent=2))
