#!/usr/bin/env python3
"""Unit04 Q10: deterministic 20x40 QuestionBank and Form materialization."""
from __future__ import annotations

import hashlib, json
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"
A1FS_CONTENT_POLICY_EXEMPTION = ""
ROOT = Path(__file__).resolve().parents[2]
PROGRAM_ID = "A1FS-V1"
UNIT_ID = "GRAMMAR_BASIC_PREPOSITIONS_PLACE"
TASK_ID = "A1FS-V1-U04Q10_Unit04QuestionBankAndFormMaterialization"
SCHEMA_VERSION = "a1fs.v1.u04.q10.questionbank_form_materialization.v1"
PASS_STATUS = "PASS_A1FS_V1_U04Q10_QUESTIONBANK_AND_FORM_MATERIALIZATION"
DECISION_REF = "OPERATOR_APPROVAL:2026-09-06:U04_Q10_20X40_800"
NEXT_SHORT_STEP = "A1FS-V1-U04Q10R1_Unit04LearnerFacingPedagogicalAcceptance"

Q03 = ROOT/"ulga/contracts/a1fs_v1_u04_q03_place_relation_form_meaning_authority.json"
Q07 = ROOT/"ulga/contracts/a1fs_v1_u04_q07_life_skill_micro_scenes.json"
Q08 = ROOT/"ulga/contracts/a1fs_v1_u04_q08_communicative_function_authority.json"
Q09 = ROOT/"ulga/contracts/a1fs_v1_u04_q09_task_pedagogical_contract.json"
REPAIR = ROOT/"ulga/contracts/a1fs_v1_u04_q07_q09_r1_reuse_only_relation_evidence_gap_fix.json"

FORM_COUNT=20; QUESTIONS_PER_FORM=40; TOTAL_ITEMS=800; CANDIDATES_PER_SLOT=3
SECTION_SPECS=(("A","FORM_AND_RELATION_RECOGNITION",6),("B","SCENE_MEANING_AND_ANSWERABILITY",10),
("C","CONSTRUCTION_AND_REPAIR",10),("D","CONNECTED_CONTEXT_AND_CUMULATIVE_INTEGRATION",8),
("E","PRODUCTIVE_RESPONSE_AND_TRANSFER",6))
SECTION_COUNTS={s:n for s,_,n in SECTION_SPECS}
STAGE_BY_FORMS={"GUIDED":range(1,5),"REDUCED_SUPPORT":range(5,9),"INDEPENDENT":range(9,13),
"TRANSFER":range(13,17),"RETENTION":range(17,21)}
TARGET_RELATIONS=("in","inside","on","near","at","under","behind","between")
NON_AT_RELATIONS=("in","inside","on","near","under","behind","between")
NEW_RELATIONS=("inside","under","behind","between"); REUSE_RELATIONS=("in","near","on")
AT_ALLOWED_FAMILIES={"U04-TF04_PLACE_PHRASE_CONSTRUCTION","U04-TF09_PRODUCTIVE_RESPONSE"}
AT_CF="U04-CF01_STATE_ENTITY_LOCATION"
PATTERNS={
"A":("U04-TF01_RECOGNITION","U04-TF03_FORM_SELECTION")*3,
"B":("U04-TF02_MEANING_DISCRIMINATION","U04-TF05_ERROR_DETECTION")*5,
"C":("U04-TF04_PLACE_PHRASE_CONSTRUCTION","U04-TF06_ERROR_CORRECTION","U04-TF07_CONTEXT_GAP",
     "U04-TF04_PLACE_PHRASE_CONSTRUCTION","U04-TF06_ERROR_CORRECTION","U04-TF07_CONTEXT_GAP",
     "U04-TF04_PLACE_PHRASE_CONSTRUCTION","U04-TF06_ERROR_CORRECTION","U04-TF07_CONTEXT_GAP",
     "U04-TF04_PLACE_PHRASE_CONSTRUCTION"),
"D":("U04-TF07_CONTEXT_GAP","U04-TF08_U01_U02_U03_INTEGRATION")*4,
"E":("U04-TF09_PRODUCTIVE_RESPONSE","U04-TF10_TRANSFER")*3,
}
QTYPES={"U04-TF01_RECOGNITION":"relation_recognition_from_unique_cue",
"U04-TF02_MEANING_DISCRIMINATION":"spatial_meaning_discrimination",
"U04-TF03_FORM_SELECTION":"preposition_form_selection",
"U04-TF04_PLACE_PHRASE_CONSTRUCTION":"place_phrase_construction",
"U04-TF05_ERROR_DETECTION":"accepted_relation_match_check",
"U04-TF06_ERROR_CORRECTION":"place_phrase_error_correction",
"U04-TF07_CONTEXT_GAP":"context_gap_place_phrase",
"U04-TF08_U01_U02_U03_INTEGRATION":"cumulative_carrier_relation_integration",
"U04-TF09_PRODUCTIVE_RESPONSE":"productive_location_response",
"U04-TF10_TRANSFER":"transfer_static_relation_application"}
DISTRACTORS={"in":("under","behind","between"),"inside":("under","behind","between"),
"on":("under","behind","between"),"near":("under","behind","between"),
"under":("inside","behind","between"),"behind":("inside","under","between"),
"between":("inside","under","behind")}
PROMPTS=("Use the accepted evidence and unique meaning cue.","Use only the licensed Unit04 relation.",
"Resolve the bounded scene or text evidence.","Keep the Unit04 place relation as the assessed target.",
"Apply the admitted static relation meaning.","Use the scoring cue without adding another relation.",
"Use the accepted authority-bound cue.")
SAFE_NOUNS={"bag","book","cat","dog","boy","girl","car","tree","shoe","cup","plate","ball","hat",
"road","street","wall","chair","table","camera","student","picture"}

class U04Q10BuildError(ValueError): pass
def _load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def _canon(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"))
def _digest(v): return hashlib.sha256(_canon(v).encode()).hexdigest()
def _stage(n):
    for stage,forms in STAGE_BY_FORMS.items():
        if n in forms:return stage
    raise U04Q10BuildError(f"FORM_STAGE_MISSING:{n}")
def _phrase(text,relation):
    t=text.strip().rstrip(".?!").casefold(); marker=f" {relation} "
    if marker not in f" {t} ": raise U04Q10BuildError(f"RELATION_NOT_IN_SENTENCE:{relation}:{text}")
    return f"{relation} {t.split(marker,1)[1]}"
def _plural(noun):
    noun=noun.casefold()
    return noun+"es" if noun.endswith(("s","x","ch","sh")) else noun+"s"

@lru_cache(maxsize=1)
def _sources():
    q03,q07,q08,q09,repair=map(_load,(Q03,Q07,Q08,Q09,REPAIR))
    expected=((q03,"PASS_Q03_UNIT04_PLACE_RELATION_FORM_MEANING_AUTHORITY"),
              (q07,"PASS_Q07_UNIT04_LIFE_SKILL_MICRO_SCENE_MATERIALIZATION_AND_SENTENCE_BINDING"),
              (q08,"PASS_Q08_UNIT04_COMMUNICATIVE_FUNCTION_AUTHORITY"),
              (q09,"PASS_Q09_UNIT04_TASK_AND_PEDAGOGICAL_CONTRACT"),
              (repair,"PASS_Q07_Q09_R1_REUSE_ONLY_AT_RELATION_EVIDENCE_GAP_FULL_FIX"))
    for payload,status in expected:
        if payload.get("status")!=status: raise U04Q10BuildError(f"SOURCE_STATUS_DRIFT:{payload.get('task_id')}")
    if repair["repair_contract"]["at_scene_bound_item_allowed"] is not False: raise U04Q10BuildError("AT_SCENE_RULE_DRIFT")
    if repair["audit"]["fabricated_scene_ref_count"]!=0: raise U04Q10BuildError("FABRICATED_REPAIR_SCENE_REF")
    return {"q03":q03,"q07":q07,"q08":q08,"q09":q09,"repair":repair}

@lru_cache(maxsize=1)
def _relations():
    rows={str(r["surface"]):dict(r) for r in _sources()["q03"]["relations"]}
    if tuple(rows)!=TARGET_RELATIONS: raise U04Q10BuildError(f"Q03_RELATION_DRIFT:{tuple(rows)}")
    return rows

@lru_cache(maxsize=1)
def _families():
    rows={str(r["task_family_id"]):dict(r) for r in _sources()["q09"]["task_families"]}
    expected={f for pattern in PATTERNS.values() for f in pattern}
    if len(rows)!=10 or set(rows)!=expected: raise U04Q10BuildError("Q09_TASK_FAMILY_DRIFT")
    return rows

@lru_cache(maxsize=1)
def _evidence():
    pools=defaultdict(list); src=_sources()
    for r in src["q07"]["micro_scenes"]:
        relation=str(r["relation_surface"])
        if relation not in NEW_RELATIONS: continue
        pools[relation].append({"evidence_id":f"Q07::{r['scene_ref_id']}",
          "mode":"Q07_UNIT04_SCENE_BOUND","relation":relation,"sentence_id":str(r["bound_sentence_id"]),
          "sentence_text":str(r["bound_sentence_text"]),"scene_ref_id":str(r["scene_ref_id"]),
          "source_scene_ref":str(r["scene_ref_id"]),"place_phrase":str(r["place_chunk_surface"]).casefold(),
          "noun":str(r["located_entity_lemma"]).casefold(),
          "landmarks":[str(x).casefold() for x in r["reference_landmarks"]]})
    for r in src["repair"]["resolved_existing_sentence_scene_evidence"]:
        relation=str(r["relation_surface"])
        if relation not in REUSE_RELATIONS: continue
        for scene_ref in r["source_scene_refs"]:
            pools[relation].append({"evidence_id":f"REUSE::{r['sentence_id']}::{scene_ref}",
              "mode":"EXISTING_SENTENCE_SCENE_PAIR","relation":relation,"sentence_id":str(r["sentence_id"]),
              "sentence_text":str(r["text"]),"scene_ref_id":str(scene_ref),"source_scene_ref":str(scene_ref),
              "place_phrase":_phrase(str(r["text"]),relation),"noun":str(r.get("subject_pronoun") or "it").casefold(),
              "landmarks":[]})
    for r in src["repair"]["at_text_bound_admitted_sentence_evidence"]:
        pools["at"].append({"evidence_id":f"AT::{r['sentence_id']}",
          "mode":"PRIOR_ADMITTED_TEXT_BOUND_POINT_PLACE_EVIDENCE","relation":"at",
          "sentence_id":str(r["sentence_id"]),"sentence_text":str(r["text"]),"scene_ref_id":None,
          "source_scene_ref":None,"place_phrase":"at the park","noun":str(r["subject_pronoun"]).casefold(),
          "landmarks":["park"]})
    if any(not pools[r] for r in TARGET_RELATIONS): raise U04Q10BuildError("EVIDENCE_POOL_EMPTY")
    return {k:tuple(v) for k,v in pools.items()}

def _relation_for(form,section,local,family,seed):
    if section=="C" and local==1 and family=="U04-TF04_PLACE_PHRASE_CONSTRUCTION": return "at"
    if section=="E" and local==1 and family=="U04-TF09_PRODUCTIVE_RESPONSE": return "at"
    if family=="U04-TF08_U01_U02_U03_INTEGRATION":
        return NEW_RELATIONS[(form+local)%len(NEW_RELATIONS)]
    return NON_AT_RELATIONS[seed%len(NON_AT_RELATIONS)]

def _choose_evidence(relation,family,occ):
    pool=list(_evidence()[relation])
    if family=="U04-TF08_U01_U02_U03_INTEGRATION":
        pool=[r for r in pool if r["noun"] in SAFE_NOUNS]
    if not pool: raise U04Q10BuildError(f"EVIDENCE_EMPTY:{relation}:{family}")
    return dict(pool[occ%len(pool)])

def _function(family,relation,seed):
    if relation=="at": return AT_CF
    allowed=list(_families()[family]["allowed_function_ids"])
    return str(allowed[seed%len(allowed)])

def _options(relation,seed):
    if relation=="at": raise U04Q10BuildError("AT_SELECTED_RESPONSE_FORBIDDEN")
    values=[relation,*DISTRACTORS[relation]]; shift=seed%4
    return values[shift:]+values[:shift]

def _wrong_phrase(e,seed):
    relation=str(e["relation"])
    if relation=="at": raise U04Q10BuildError("AT_WRONG_PHRASE_FORBIDDEN")
    wrong=DISTRACTORS[relation][seed%3]; correct=str(e["place_phrase"])
    return wrong+correct[len(relation):] if correct.startswith(relation+" ") else wrong

def _scoring(response_class,exact=False):
    if response_class=="OPEN_CONSTRUCTED_RESPONSE":
        return {"scoring_mode":"HUMAN_REVIEW","single_answer_required":False,"reference_response_nonexclusive":True}
    return {"scoring_mode":"NORMALIZED_TEXT" if exact else "EXACT_OPTION",
            "single_answer_required":True,"reference_response_nonexclusive":False}

def _item(form,section,section_name,local,family,relation,cf,e,occ):
    stage=_stage(form); rel=_relations()[relation]; fam=_families()[family]
    meaning=str(rel["meaning"]); cue=PROMPTS[occ%len(PROMPTS)]
    scene=e["scene_ref_id"]; phrase=str(e["place_phrase"]); options=[]; correct=None
    response_class=str(fam["response_class"]); basis="Q03_MEANING_PLUS_ACCEPTED_EVIDENCE"
    evidence_role="SCENE_BOUND_TARGET_RELATION"
    if relation=="at":
        if family not in AT_ALLOWED_FAMILIES or cf!=AT_CF or scene is not None:
            raise U04Q10BuildError("AT_REPAIR_CONTRACT_VIOLATION")
        evidence_role=("FORM_CONSTRUCTION_WITH_GIVEN_RELATION" if family=="U04-TF04_PLACE_PHRASE_CONSTRUCTION"
                       else "OPEN_PRODUCTIVE_RESPONSE_WITH_POINT_PLACE_CUE")
        basis="Q07_Q09_R1_AT_TEXT_BOUND_POINT_PLACE_EVIDENCE"

    if family in {"U04-TF01_RECOGNITION","U04-TF02_MEANING_DISCRIMINATION","U04-TF03_FORM_SELECTION"}:
        stimulus={"mode":"ACCEPTED_SCENE_PLUS_UNIQUE_MEANING_CUE","scene_ref_id":scene,"unique_meaning_cue":meaning}
        prompt=f"{cue} Choose the admitted Unit04 relation."; options=_options(relation,occ); correct=relation
        response_class="SELECTED_RESPONSE"; scoring=_scoring(response_class)
    elif family=="U04-TF05_ERROR_DETECTION":
        good=occ%2==0; candidate=phrase if good else _wrong_phrase(e,occ)
        stimulus={"mode":"ACCEPTED_EVIDENCE_PLUS_CANDIDATE_PHRASE","scene_ref_id":scene,
                  "unique_meaning_cue":meaning,"candidate_place_phrase":candidate}
        prompt=f"{cue} Does the candidate place phrase match the licensed relation?"
        options=["MATCHES","DOES_NOT_MATCH"]; correct="MATCHES" if good else "DOES_NOT_MATCH"
        response_class="SELECTED_RESPONSE"; scoring=_scoring(response_class)
    elif family=="U04-TF04_PLACE_PHRASE_CONSTRUCTION":
        stimulus={"mode":"GIVEN_RELATION_PLUS_ACCEPTED_COMPLEMENT","scene_ref_id":scene,
                  "relation_form":relation,"accepted_sentence_witness":str(e["sentence_text"])}
        if relation=="at":
            stimulus["accepted_sentence_witness"]=None; stimulus["point_place_cue"]="park"
        prompt=f"{cue} Construct the admitted place phrase using the given relation."
        correct=phrase; response_class="CONSTRUCTED_RESPONSE"; scoring=_scoring(response_class,exact=True)
    elif family=="U04-TF06_ERROR_CORRECTION":
        stimulus={"mode":"ACCEPTED_EVIDENCE_PLUS_INCORRECT_PLACE_PHRASE","scene_ref_id":scene,
                  "unique_meaning_cue":meaning,"incorrect_place_phrase":_wrong_phrase(e,occ)}
        prompt=f"{cue} Rewrite only the incorrect place phrase."
        correct=phrase; response_class="CONSTRUCTED_RESPONSE"; scoring=_scoring(response_class,exact=True)
    elif family=="U04-TF07_CONTEXT_GAP":
        stimulus={"mode":"SCENE_BOUND_CONTEXT_GAP","scene_ref_id":scene,"unique_meaning_cue":meaning,
                  "source_sentence_id":str(e["sentence_id"])}
        prompt=f"{cue} Supply the missing admitted place phrase."
        correct=phrase; response_class="SELECTED_OR_CONSTRUCTED_RESPONSE"; scoring=_scoring(response_class,exact=True)
    elif family=="U04-TF08_U01_U02_U03_INTEGRATION":
        noun=str(e["noun"]); plural=_plural(noun)
        stimulus={"mode":"CUMULATIVE_CARRIER_INTEGRATION","scene_ref_id":scene,"unique_meaning_cue":meaning,
                  "unit01_article_carrier":f"a {noun}","unit02_plural_carrier":f"two {plural}",
                  "unit03_reference_carrier":"they"}
        prompt=f"{cue} Choose the Unit04 relation that remains the assessed target while the carriers change."
        options=_options(relation,occ); correct=relation
        response_class="SELECTED_OR_CONSTRUCTED_RESPONSE"; scoring=_scoring(response_class)
    elif family=="U04-TF09_PRODUCTIVE_RESPONSE":
        if cf=="U04-CF02_REQUEST_ENTITY_LOCATION_INFORMATION":
            stimulus={"mode":"COMMUNICATIVE_LOCATION_REQUEST","scene_ref_id":scene,
                      "entity_witness":str(e["sentence_id"])}
            prompt=(f"{cue} Ask for the entity's location using an already-admitted cumulative question form. "
                    "The exact question form is not new Unit04 grammar."); correct=None
        elif relation=="at":
            stimulus={"mode":"AT_TEXT_BOUND_POINT_PLACE_PRODUCTION","scene_ref_id":None,
                      "point_place_cue":"park","subject_pronoun":str(e["noun"])}
            prompt=f"{cue} State the general point-place location; natural viewpoint variants remain human-reviewable."
            correct=str(e["sentence_text"]).strip()
        else:
            stimulus={"mode":"OPEN_SCENE_DESCRIPTION","scene_ref_id":scene,"unique_meaning_cue":meaning}
            prompt=f"{cue} Give one complete location statement or short static scene description."
            correct=str(e["sentence_text"]).strip()
        response_class="OPEN_CONSTRUCTED_RESPONSE"; scoring=_scoring(response_class)
    elif family=="U04-TF10_TRANSFER":
        if cf=="U04-CF02_REQUEST_ENTITY_LOCATION_INFORMATION":
            stimulus={"mode":"TRANSFER_LOCATION_REQUEST","scene_ref_id":scene,"authority_compatible_context":True}
            prompt=(f"{cue} Ask for location information using prior admitted question grammar; "
                    "do not create a new Unit04 question pattern."); correct=None
            response_class="OPEN_CONSTRUCTED_RESPONSE"; scoring=_scoring(response_class)
        elif cf=="U04-CF05_DESCRIBE_SPATIAL_SCENE":
            stimulus={"mode":"TRANSFER_OPEN_DESCRIPTION","scene_ref_id":scene,"unique_meaning_cue":meaning,
                      "authority_compatible_context":True}
            prompt=f"{cue} Describe the admitted static relation in one complete sentence."
            correct=str(e["sentence_text"]).strip(); response_class="OPEN_CONSTRUCTED_RESPONSE"; scoring=_scoring(response_class)
        else:
            stimulus={"mode":"TRANSFER_UNIQUE_RELATION_CUE","scene_ref_id":scene,"unique_meaning_cue":meaning,
                      "authority_compatible_context":True}
            prompt=f"{cue} Choose the admitted static relation that the transfer cue licenses."
            options=_options(relation,occ); correct=relation
            response_class="SELECTED_OR_CONSTRUCTED_RESPONSE"; scoring=_scoring(response_class)
    else: raise U04Q10BuildError(f"UNSUPPORTED_FAMILY:{family}")

    core={"form_number":form,"stage":stage,"section":section,"local":local,"family":family,"cf":cf,
          "relation":relation,"evidence_id":str(e["evidence_id"]),"question_type":QTYPES[family],
          "stimulus":stimulus,"prompt":prompt,"options":options,"correct_answer":correct}
    sig=_digest(core); item_id=f"U04Q10-F{form:02d}-{section}{local:02d}-{sig[:12].upper()}"
    return {"item_id":item_id,"unit_id":UNIT_ID,"form_number":form,"progression_role":stage,
      "section":section,"section_name":section_name,"section_activity_ordinal":local,
      "task_family_id":family,"task_family_name":str(fam["family_name"]),"question_type":QTYPES[family],
      "communicative_function_id":cf,"relation_surface":relation,"relation_id":str(rel["relation_id"]),
      "target_relation_evidence":True,"support_relation":False,"evidence_mode":str(e["mode"]),
      "evidence_role":evidence_role,"source_sentence_id":str(e["sentence_id"]),
      "source_sentence_text":str(e["sentence_text"]),"scene_ref_id":scene,"source_scene_ref":e["source_scene_ref"],
      "reference_landmarks":list(e["landmarks"]),"place_phrase":phrase,"stimulus":stimulus,"prompt":prompt,
      "options":options,"correct_answer":correct,"response_class":response_class,"response_contract":scoring,
      "answerability_basis":basis,"single_answer_unique_cue_required":bool(options),
      "q03_overlap_guards_preserved":True,"creates_new_grammar_authority":False,
      "creates_new_sentence_identity":False,"creates_new_scene_identity":False,
      "directional_from_into_to_activated":False,"a2_unlocked":False,"semantic_signature":sig}

def _runtime(items:Sequence[Mapping[str,Any]]):
    by_family=defaultdict(list)
    for r in items: by_family[str(r["task_family_id"])].append(str(r["item_id"]))
    out=[]
    for r in items:
        family=str(r["task_family_id"]); pool=by_family[family]; selected=str(r["item_id"]); pos=pool.index(selected)
        candidates=[pool[(pos+i)%len(pool)] for i in range(CANDIDATES_PER_SLOT)]
        if len(set(candidates))!=3: raise U04Q10BuildError(f"CANDIDATE_POOL_TOO_SHALLOW:{family}")
        out.append({"slot_id":f"U04Q10-F{int(r['form_number']):02d}-{r['section']}{int(r['section_activity_ordinal']):02d}",
          "form_number":int(r["form_number"]),"progression_role":str(r["progression_role"]),
          "section":str(r["section"]),"section_activity_ordinal":int(r["section_activity_ordinal"]),
          "task_family_id":family,"selected_item_id":selected,"candidate_ids":candidates})
    return out

def _forms(items:Sequence[Mapping[str,Any]]):
    out=[]
    for n in range(1,21):
        rows=[r for r in items if int(r["form_number"])==n]
        by_section={s:[str(r["item_id"]) for r in rows if r["section"]==s] for s in SECTION_COUNTS}
        out.append({"form_id":f"U04-FORM-{n:02d}","form_number":n,"progression_role":_stage(n),
          "question_count":len(rows),"section_counts":{s:len(v) for s,v in by_section.items()},
          "section_item_ids":by_section,"item_ids":[str(r["item_id"]) for r in rows]})
    return out

def build_export_payload():
    src=_sources(); items=[]; family_occ=Counter(); relation_occ=Counter(); non_at_seed=0
    section_names={s:name for s,name,_ in SECTION_SPECS}
    for form in range(1,21):
        for section,_,count in SECTION_SPECS:
            pattern=PATTERNS[section]
            if len(pattern)!=count: raise U04Q10BuildError(f"SECTION_PATTERN_DRIFT:{section}")
            for local,family in enumerate(pattern,1):
                relation=_relation_for(form,section,local,family,non_at_seed)
                if relation!="at": non_at_seed+=1
                family_occ[family]+=1; occ=family_occ[family]-1
                if family=="U04-TF08_U01_U02_U03_INTEGRATION":
                    e=_choose_evidence(relation,family,occ); relation=str(e["relation"])
                else:
                    relation_occ[relation]+=1; e=_choose_evidence(relation,family,relation_occ[relation]-1)
                cf=_function(family,relation,occ+form+local)
                items.append(_item(form,section,section_names[section],local,family,relation,cf,e,occ))
    forms=_forms(items); runtime=_runtime(items)
    family_counts=Counter(str(r["task_family_id"]) for r in items)
    relation_counts=Counter(str(r["relation_surface"]) for r in items)
    function_counts=Counter(str(r["communicative_function_id"]) for r in items)
    at_rows=[r for r in items if r["relation_surface"]=="at"]
    payload={"schema_version":SCHEMA_VERSION,"program_id":PROGRAM_ID,"task_id":TASK_ID,"status":PASS_STATUS,
      "unit_id":UNIT_ID,"unit_number":4,"internal_stage":"A1",
      "source_authority":{"q03_task_id":src["q03"]["task_id"],"q07_task_id":src["q07"]["task_id"],
        "q08_task_id":src["q08"]["task_id"],"q09_task_id":src["q09"]["task_id"],
        "reuse_only_repair_task_id":src["repair"]["task_id"],"reuse_only_repair_required":True},
      "materialization_contract":{"form_count":20,"questions_per_form":40,"questionbank_item_count":800,
        "runtime_occurrence_count":800,"candidate_count_per_slot":3,"section_counts_per_form":SECTION_COUNTS,
        "progression_roles":list(STAGE_BY_FORMS),"task_family_count":10,"target_relation_count":8,
        "communicative_function_count":6},
      "questionbank_items":items,"forms":forms,"runtime_bindings":runtime,
      "coverage":{"questionbank_item_count":len(items),"unique_item_id_count":len({r["item_id"] for r in items}),
        "unique_semantic_signature_count":len({r["semantic_signature"] for r in items}),
        "exact_semantic_duplicate_count":len(items)-len({r["semantic_signature"] for r in items}),
        "form_count":len(forms),"runtime_occurrence_count":len(runtime),
        "task_family_counts":dict(sorted(family_counts.items())),"task_family_coverage":f"{len(family_counts)}/10",
        "target_relation_counts":{r:relation_counts[r] for r in TARGET_RELATIONS},
        "target_relation_coverage":f"{sum(relation_counts[r]>0 for r in TARGET_RELATIONS)}/8",
        "communicative_function_counts":dict(sorted(function_counts.items())),
        "communicative_function_coverage":f"{len(function_counts)}/6",
        "selected_response_item_count":sum(bool(r["options"]) for r in items),
        "at_item_count":len(at_rows),"at_scene_ref_count":sum(r["scene_ref_id"] is not None for r in at_rows),
        "fabricated_scene_ref_count":0,"support_relation_item_count":0},
      "repair_enforcement":{"at_evidence_mode":src["repair"]["repair_contract"]["at_evidence_mode"],
        "at_allowed_task_family_ids":list(src["repair"]["repair_contract"]["at_allowed_task_family_ids"]),
        "at_allowed_communicative_function_ids":list(src["repair"]["repair_contract"]["at_allowed_communicative_function_ids"]),
        "at_scene_bound_item_allowed":False,"at_picture_relation_selection_allowed":False,
        "at_in_forced_single_answer_contrast_allowed":False,"unresolved_in_near_raw_sentences_fail_closed":True,
        "fabricated_scene_ref_count":0},
      "boundaries":{"q03_q09_authority_mutated":False,"q07_micro_scene_rows_modified":False,
        "q08_communicative_function_inventory_modified":False,"q09_task_family_inventory_modified":False,
        "new_grammar_authority_created":False,"new_sentence_identity_created":False,"new_scene_identity_created":False,
        "support_relations_promoted_to_target":False,"directional_from_into_to_activated":False,"a2_unlocked":False},
      "next_short_step":NEXT_SHORT_STEP}
    return payload

def build_candidate():
    src=_sources()
    return policy_artifact.build_candidate(payload=build_export_payload(),producer_id=TASK_ID,level_scope=["A1"],
      source_bindings={"q03_task_id":src["q03"]["task_id"],"q07_task_id":src["q07"]["task_id"],
      "q08_task_id":src["q08"]["task_id"],"q09_task_id":src["q09"]["task_id"],
      "reuse_only_repair_task_id":src["repair"]["task_id"]})

def admit_candidate(candidate:Mapping[str,Any]):
    from ulga.validators import validate_a1fs_v1_u04q10_questionbank_form_materialization as validator
    receipt=validator.validate_candidate(candidate)
    return policy_artifact.admit_candidate(candidate,validation_receipts=[receipt],
      decision_ref=DECISION_REF,producer_id=TASK_ID)

def main():
    p=build_export_payload(); approved=admit_candidate(build_candidate())
    print(json.dumps({"status":p["status"],"items":p["coverage"]["questionbank_item_count"],
      "forms":p["coverage"]["form_count"],"task_families":p["coverage"]["task_family_coverage"],
      "relations":p["coverage"]["target_relation_coverage"],"functions":p["coverage"]["communicative_function_coverage"],
      "at_scene_refs":p["coverage"]["at_scene_ref_count"],"fabricated_scene_refs":p["coverage"]["fabricated_scene_ref_count"],
      "approved_role":approved["artifact_role"],"next_short_step":p["next_short_step"]},indent=2))
    return 0
if __name__=="__main__": raise SystemExit(main())
