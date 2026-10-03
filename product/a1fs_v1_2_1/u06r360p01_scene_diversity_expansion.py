#!/usr/bin/env python3
"""Unit06 Reader360 P01R1: GPT-5.6 scene-instance diversity expansion.

Creates structured Reader360-local scene semantics from approved Unit06 scene/chunk
authority. Python performs deterministic routing, counting and dedup only. No
learner-facing passage/dialogue/pattern English is authored here.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

from product.a1fs_v1_2_1 import u06r360p01_natural360_source_projection as p01
from ulga.builders import build_a1fs_v1_u05_q07_life_skill_micro_scenes as u05_q07
from ulga.builders import build_a1fs_v1_u06_q07_life_skill_micro_scenes as u06_q07
from ulga.builders import (
    build_a1fs_v1_u06_q07r1_functional_chunk_semantic_expansion as u06_q07r1,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Structured scene-semantics expansion only. GPT-5.6 authored the scene-setting, "
    "context-mode and verb-to-family mapping below. Python may materialize deterministic "
    "scene records, enforce semantic-key distinctness, compare predecessor/current counts, "
    "and route them to future Reader360 authoring. Python may not compose learner-facing "
    "sentences, passages, dialogues, questions, or unlock later grammar."
)

PROGRAM_ID="A1FS-V1"
UNIT_ID="GRAMMAR_CAN_STATEMENT"
TASK_ID="A1FS-V1-U06R360P01R1_SceneInstanceDiversityExpansionAndSuccessorRule"
STATUS="PASS_A1FS_V1_U06R360P01R1_SCENE_INSTANCE_DIVERSITY_EXPANSION"
SCENE_DIVERSITY_POLICY_ID="A1FS_SCENE_DIVERSITY_MONOTONIC_SUCCESSOR_V1"
DEFAULT_MINIMUM_INCREMENT=24
NEXT_SHORT_STEP="A1FS-V1-U06R360P02_Current360GPT56NaturalEpisodeMaterialization"

REPO_ROOT=Path(__file__).resolve().parents[2]
REUSABLE_CONTRACT=REPO_ROOT/"ulga/contracts/a1fs_v1_reusable_unit_production_contract.json"

# GPT-5.6-authored semantic setting palette. These are structured scene settings,
# not learner-visible English passages.
FAMILY_SETTINGS={
 "CLOTHING_PERSONAL_ITEMS":("bedroom clothes area","school coat area","home hallway before going out"),
 "COMMUNICATION_WRITING":("home writing desk","classroom message desk","library computer area"),
 "FAMILY_PEOPLE_SOCIAL":("family living room","family kitchen table","garden sitting area"),
 "HOME_BEDROOM_LIVING":("living room","bedroom","home hallway"),
 "KITCHEN_DINING":("home kitchen","school cooking area","dining table"),
 "MEDIA_ENTERTAINMENT_TECH":("computer room","living room screen area","classroom media corner"),
 "MUSIC_DANCE":("music room","dance room","home music corner"),
 "PARK_GARDEN_NATURE":("park path","garden","playground edge"),
 "SCHOOL_CLASSROOM_LEARNING":("classroom","school library","school hall"),
 "SPORTS_PLAY":("playground","sports centre","park field"),
 "TOWN_PUBLIC_PLACES":("town square","station entrance","library entrance"),
 "TRANSPORT_TRAVEL":("bus stop","station platform","school gate travel area"),
}

# GPT-5.6 semantic routing for controlled Q04R1 baseline chunks that did not
# already carry exact Q07 scene-family evidence.
VERB_FAMILY_HINTS={
 "add":"SCHOOL_CLASSROOM_LEARNING","answer":"SCHOOL_CLASSROOM_LEARNING",
 "ask":"SCHOOL_CLASSROOM_LEARNING","bring":"SCHOOL_CLASSROOM_LEARNING",
 "build":"SCHOOL_CLASSROOM_LEARNING","call":"COMMUNICATION_WRITING",
 "carry":"TRANSPORT_TRAVEL","catch":"SPORTS_PLAY","change":"MEDIA_ENTERTAINMENT_TECH",
 "clean":"HOME_BEDROOM_LIVING","climb":"PARK_GARDEN_NATURE","close":"HOME_BEDROOM_LIVING",
 "colour":"SCHOOL_CLASSROOM_LEARNING","complete":"SCHOOL_CLASSROOM_LEARNING",
 "cook":"KITCHEN_DINING","dance":"MUSIC_DANCE","do":"HOME_BEDROOM_LIVING",
 "draw":"SCHOOL_CLASSROOM_LEARNING","dress":"CLOTHING_PERSONAL_ITEMS","drink":"KITCHEN_DINING","dry":"KITCHEN_DINING",
 "eat":"KITCHEN_DINING","email":"COMMUNICATION_WRITING","find":"TOWN_PUBLIC_PLACES",
 "fly":"PARK_GARDEN_NATURE","get":"CLOTHING_PERSONAL_ITEMS","give":"FAMILY_PEOPLE_SOCIAL","go":"TRANSPORT_TRAVEL",
 "help":"FAMILY_PEOPLE_SOCIAL","hold":"HOME_BEDROOM_LIVING","jump":"SPORTS_PLAY",
 "kick":"SPORTS_PLAY","listen":"MUSIC_DANCE","make":"SCHOOL_CLASSROOM_LEARNING",
 "move":"HOME_BEDROOM_LIVING","open":"HOME_BEDROOM_LIVING","paint":"SCHOOL_CLASSROOM_LEARNING",
 "phone":"COMMUNICATION_WRITING","play":"SPORTS_PLAY","point":"TOWN_PUBLIC_PLACES",
 "read":"SCHOOL_CLASSROOM_LEARNING","ride":"TRANSPORT_TRAVEL","run":"SPORTS_PLAY",
 "say":"COMMUNICATION_WRITING","see":"TOWN_PUBLIC_PLACES","send":"COMMUNICATION_WRITING",
 "show":"FAMILY_PEOPLE_SOCIAL","sing":"MUSIC_DANCE","sit":"HOME_BEDROOM_LIVING",
 "spell":"SCHOOL_CLASSROOM_LEARNING","stand":"SCHOOL_CLASSROOM_LEARNING",
 "study":"SCHOOL_CLASSROOM_LEARNING","swim":"SPORTS_PLAY","take":"MEDIA_ENTERTAINMENT_TECH","talk":"FAMILY_PEOPLE_SOCIAL",
 "teach":"SCHOOL_CLASSROOM_LEARNING","tell":"COMMUNICATION_WRITING","text":"COMMUNICATION_WRITING",
 "throw":"SPORTS_PLAY","understand":"SCHOOL_CLASSROOM_LEARNING","wait":"TRANSPORT_TRAVEL",
 "walk":"PARK_GARDEN_NATURE","wash":"KITCHEN_DINING","work":"SCHOOL_CLASSROOM_LEARNING",
 "write":"COMMUNICATION_WRITING",
}

# Each approved chunk can support three semantically different scene purposes.
# The difference is not merely a name/pronoun substitution.
CONTEXT_MODES=(
 {
  "context_mode":"INDIVIDUAL_DEMONSTRATION",
  "participant_profile":"ONE_LEARNER_OR_ONE_REFERENT",
  "communicative_or_task_purpose":"show a clear ability during one familiar action",
  "truth_evidence_role":"DIRECT_ABILITY_DEMONSTRATION",
 },
 {
  "context_mode":"PAIR_SHARED_TASK",
  "participant_profile":"PAIR_OR_HELPER_AND_LEARNER",
  "communicative_or_task_purpose":"use the ability while completing or helping with a simple shared task",
  "truth_evidence_role":"ABILITY_USED_IN_SHARED_TASK",
 },
 {
  "context_mode":"SMALL_GROUP_TRANSFER",
  "participant_profile":"SMALL_GROUP_OR_NEARBY_TRANSFER",
  "communicative_or_task_purpose":"use the same ability in a nearby familiar setting with changed people, objects, or place cues",
  "truth_evidence_role":"ABILITY_TRANSFER_IN_FAMILIAR_CONTEXT",
 },
)

class U06SceneDiversityError(ValueError):
    pass

def _canon(value: Any)->str:
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"))

def _digest(value: Any)->str:
    return hashlib.sha256(_canon(value).encode("utf-8")).hexdigest()

def _load(path: Path)->dict[str,Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def _source_guard()->tuple[dict[str,Any],dict[str,Any],dict[str,Any],dict[str,Any]]:
    predecessor=u05_q07.build_report()
    q07=u06_q07.build_report()
    q07r1=u06_q07r1.build_report()
    p01_report=p01.build_unit06_natural360_source_projection()
    if predecessor.get("status")!="PASS_A1FS_V1_U05Q07_LIFE_SKILL_MICRO_SCENE_MATERIALIZATION_AND_SENTENCE_BINDING":
        raise U06SceneDiversityError("U05_Q07_NOT_PASS")
    if q07.get("status")!="PASS_A1FS_V1_U06Q07_LIFE_SKILL_MICRO_SCENE_MATERIALIZATION_AND_SENTENCE_BINDING":
        raise U06SceneDiversityError("U06_Q07_NOT_PASS")
    if q07r1.get("status")!="PASS_A1FS_V1_U06Q07R1_YLE_ABILITY_VERB_FUNCTIONAL_CHUNK_SEMANTIC_EXPANSION":
        raise U06SceneDiversityError("U06_Q07R1_NOT_PASS")
    if p01_report.get("status")!=p01.STATUS:
        raise U06SceneDiversityError("U06_R360_P01_NOT_PASS")
    reusable=_load(REUSABLE_CONTRACT)
    policy=reusable.get("common_contract",{}).get("scene_diversity",{})
    if policy.get("policy_id")!=SCENE_DIVERSITY_POLICY_ID:
        raise U06SceneDiversityError("REUSABLE_SCENE_DIVERSITY_POLICY_MISSING")
    if policy.get("default_minimum_increment")!=DEFAULT_MINIMUM_INCREMENT:
        raise U06SceneDiversityError("REUSABLE_SCENE_INCREMENT_DRIFT")
    return predecessor,q07,q07r1,p01_report

def _chunk_inventory(p01_report: Mapping[str,Any])->list[dict[str,Any]]:
    rows=[
      dict(chunk)
      for cluster in p01_report["source_clusters"]
      for chunk in cluster["functional_chunks"]
    ]
    if len(rows)!=182 or len({x["normalized_surface"] for x in rows})!=182:
        raise U06SceneDiversityError("P01_CHUNK_DENOMINATOR_DRIFT")
    return rows

def _family_for_chunk(row: Mapping[str,Any])->str:
    family=row.get("scene_family")
    if family:
        family=str(family)
    else:
        verb=str(row.get("base_verb") or "")
        family=VERB_FAMILY_HINTS.get(verb)
    if family not in FAMILY_SETTINGS:
        raise U06SceneDiversityError(
            f"SCENE_FAMILY_HINT_MISSING:{row.get('normalized_surface')}:{row.get('base_verb')}:{family}"
        )
    return family

def _semantic_key(row: Mapping[str,Any])->dict[str,str]:
    return {
      "scene_family":str(row["scene_family"]),
      "setting":str(row["setting"]),
      "functional_chunk_or_target_action":str(row["functional_chunk_surface"]),
      "context_mode":str(row["context_mode"]),
      "participant_profile":str(row["participant_profile"]),
      "communicative_or_task_purpose":str(row["communicative_or_task_purpose"]),
    }

def _candidate_scenes(p01_report: Mapping[str,Any])->list[dict[str,Any]]:
    chunks=_chunk_inventory(p01_report)
    by_pass:list[dict[str,Any]]=[]
    for mode_index,mode in enumerate(CONTEXT_MODES):
        for chunk in sorted(chunks,key=lambda x:(str(x.get("base_verb")),str(x["normalized_surface"]))):
            family=_family_for_chunk(chunk)
            settings=FAMILY_SETTINGS[family]
            setting=settings[mode_index]
            core={
              "scene_family":family,
              "setting":setting,
              "functional_chunk_surface":str(chunk["normalized_surface"]),
              "base_verb":str(chunk.get("base_verb") or ""),
              **mode,
            }
            semantic=_semantic_key(core)
            sid="U06-R360-SCENE-"+_digest(semantic)[:20].upper()
            by_pass.append({
              "scene_instance_id":sid,
              "scene_instance_scope":"READER360_LOCAL_SCENE_INSTANCE",
              "scene_diversity_policy_id":SCENE_DIVERSITY_POLICY_ID,
              "origin_unit":6,
              "authoring_model":"GPT-5.6 Sol",
              "authoring_mode":"GPT56_EXPLICIT_SEMANTIC_BLUEPRINT_PLUS_DETERMINISTIC_ROUTING",
              "scene_family":family,
              "setting":setting,
              "context_mode":mode["context_mode"],
              "participant_profile":mode["participant_profile"],
              "communicative_or_task_purpose":mode["communicative_or_task_purpose"],
              "truth_evidence_role":mode["truth_evidence_role"],
              "functional_chunk_surface":str(chunk["normalized_surface"]),
              "base_verb":str(chunk.get("base_verb") or ""),
              "chunk_source_kind":str(chunk.get("source_kind") or ""),
              "chunk_semantic_admission_class":str(chunk.get("semantic_admission_class") or ""),
              "candidate_source_scene_families":list(chunk.get("candidate_scene_families") or []),
              "scene_grounding":chunk.get("scene_grounding"),
              "semantic_scene_key":semantic,
              "semantic_scene_key_sha256":_digest(semantic),
              "creates_new_global_scene_family":False,
              "creates_new_canonical_q07_scene_identity":False,
              "creates_new_sentence_authority":False,
              "learner_facing_english_materialized":False,
              "can_interrogative_mastery_unlocked":False,
              "can_negative_mastery_unlocked":False,
              "permission_request_offer_possibility_can_unlocked":False,
              "a2_a2plus_unlocked":False,
            })
    if len(by_pass)!=546:
        raise U06SceneDiversityError(f"CANDIDATE_SCENE_COUNT_DRIFT:{len(by_pass)}")
    if len({x["scene_instance_id"] for x in by_pass})!=546:
        raise U06SceneDiversityError("SCENE_INSTANCE_ID_COLLISION")
    if len({x["semantic_scene_key_sha256"] for x in by_pass})!=546:
        raise U06SceneDiversityError("SEMANTIC_SCENE_KEY_COLLISION")
    return by_pass

def _slot_bindings(
    p01_report: Mapping[str,Any],
    scenes: list[dict[str,Any]],
)->list[dict[str,Any]]:
    slots=list(p01_report["episode_authoring_slots"])
    by_chunk:dict[str,list[str]]=defaultdict(list)
    for scene in scenes:
        by_chunk[str(scene["functional_chunk_surface"])].append(str(scene["scene_instance_id"]))
    bindings=[]
    scene_cursor=0
    for slot in slots:
        required=list(slot["required_functional_chunk_surfaces"])
        candidates=[]
        for surface in required:
            candidates.extend(by_chunk.get(str(surface),[]))
        if not candidates:
            candidates=[str(scenes[scene_cursor % len(scenes)]["scene_instance_id"])]
        primary=candidates[0]
        # A secondary semantic scene is available for transfer/variation without
        # forcing the Current360 author to merge two scenes.
        secondary=str(scenes[(scene_cursor+len(slots)) % len(scenes)]["scene_instance_id"])
        bindings.append({
          "episode_slot_id":str(slot["episode_slot_id"]),
          "target_current360_episode_id":str(slot["target_current360_episode_id"]),
          "primary_scene_instance_id":primary,
          "secondary_scene_option_id":secondary if secondary!=primary else None,
          "required_functional_chunk_surfaces":required,
          "primary_scene_required":True,
          "secondary_scene_optional":True,
          "learner_facing_episode_not_materialized":True,
        })
        scene_cursor+=1
    if len(bindings)!=360:
        raise U06SceneDiversityError("SLOT_BINDING_COUNT_DRIFT")
    return bindings

def build_unit06_scene_diversity_expansion()->dict[str,Any]:
    predecessor,q07,q07r1,p01_report=_source_guard()
    predecessor_count=len(predecessor["micro_scenes"])
    if not 0<predecessor_count<478:
        raise U06SceneDiversityError(f"U05_SCENE_COUNT_OUT_OF_EXPECTED_RANGE:{predecessor_count}")
    target=predecessor_count+DEFAULT_MINIMUM_INCREMENT
    candidates=_candidate_scenes(p01_report)
    if target>len(candidates):
        raise U06SceneDiversityError(
          f"SCENE_CANDIDATE_CAPACITY_INSUFFICIENT:{target}:{len(candidates)}"
        )
    selected=candidates[:target]
    if len(selected)<=predecessor_count:
        raise U06SceneDiversityError("MONOTONIC_SCENE_DIVERSITY_RULE_NOT_MET")
    if len({x["semantic_scene_key_sha256"] for x in selected})!=len(selected):
        raise U06SceneDiversityError("SELECTED_SCENE_SEMANTIC_DUPLICATION")

    chunks={x["functional_chunk_surface"] for x in selected}
    if len(chunks)!=182:
        raise U06SceneDiversityError(f"FUNCTIONAL_CHUNK_SCENE_COVERAGE_GAP:{len(chunks)}")
    q07r1_source_verbs={
        x["base_verb"] for x in selected if x["chunk_source_kind"]=="Q07R1_NEW"
    }
    if len(q07r1_source_verbs)!=62:
        raise U06SceneDiversityError(
            f"SOURCE_VERB_SCENE_COVERAGE_GAP:{len(q07r1_source_verbs)}"
        )
    families=Counter(x["scene_family"] for x in selected)
    if set(families)!=set(FAMILY_SETTINGS):
        raise U06SceneDiversityError(f"SCENE_FAMILY_COVERAGE_GAP:{sorted(families)}")

    modes=Counter(x["context_mode"] for x in selected)
    slot_bindings=_slot_bindings(p01_report,selected)
    successor_minimum=len(selected)+1
    report={
      "schema_version":"a1fs.v1.u06.r360.p01r1.scene_instance_diversity_expansion.v1",
      "program_id":PROGRAM_ID,
      "unit_id":UNIT_ID,
      "unit_number":6,
      "task_id":TASK_ID,
      "status":STATUS,
      "scene_diversity_policy_id":SCENE_DIVERSITY_POLICY_ID,
      "scene_diversity_authority_for_successor":True,
      "predecessor_unit":5,
      "predecessor_scene_count_source":"U05_Q07_CANONICAL_MICRO_SCENE_COUNT_BOOTSTRAP",
      "predecessor_distinct_scene_instance_count":predecessor_count,
      "default_minimum_increment":DEFAULT_MINIMUM_INCREMENT,
      "target_distinct_scene_instance_count":target,
      "current_distinct_scene_instance_count":len(selected),
      "successor_required_minimum_scene_instance_count":successor_minimum,
      "successor_default_target_scene_instance_count":len(selected)+DEFAULT_MINIMUM_INCREMENT,
      "authoring_contract":{
        "scene_semantics_author":"GPT-5.6 Sol",
        "python_may_route_count_and_deduplicate":True,
        "python_may_author_learner_facing_english":False,
        "reader360_episode_count_remains":360,
        "scene_reservoir_may_exceed_reader_episode_count":True,
        "semantic_scene_count_must_increase_over_predecessor":True,
        "superficial_name_or_pronoun_only_change_counts_as_new_scene":False,
      },
      "coverage":{
        "q07_canonical_scene_source_count":len(q07["micro_scenes"]),
        "q07r1_distinct_chunk_source_count":182,
        "q07r1_source_verb_count":62,
        "candidate_semantic_scene_count":len(candidates),
        "selected_semantic_scene_count":len(selected),
        "scene_growth_over_predecessor":len(selected)-predecessor_count,
        "functional_chunk_scene_coverage":"182/182",
        "source_verb_scene_coverage":"62/62",
        "scene_family_count":len(families),
        "scene_family_counts":dict(sorted(families.items())),
        "context_mode_counts":dict(sorted(modes.items())),
        "reader360_authoring_slot_scene_binding_count":len(slot_bindings),
      },
      "semantic_distinctness":{
        "dimensions":[
          "scene_family","setting","functional_chunk_or_target_action","context_mode",
          "participant_profile","communicative_or_task_purpose"
        ],
        "selected_semantic_key_distinct_count":len({x["semantic_scene_key_sha256"] for x in selected}),
        "person_name_only_variation_counted_as_distinct":False,
        "pronoun_only_variation_counted_as_distinct":False,
      },
      "reader360_local_scene_instances":selected,
      "reader360_authoring_slot_scene_bindings":slot_bindings,
      "integrity":{
        "semantic_scene_key_digest":_digest(sorted(x["semantic_scene_key_sha256"] for x in selected)),
        "scene_instance_digest":_digest(selected),
        "slot_scene_binding_digest":_digest(slot_bindings),
      },
      "scope_safety":{
        "u05_modified":False,
        "u06_q01_q10_modified":False,
        "u06_q07_canonical_scene_authority_modified":False,
        "u06_q07r1_chunk_semantics_modified":False,
        "new_global_scene_family_created":False,
        "new_q07_canonical_scene_identity_created":False,
        "new_sentence_authority_created":False,
        "learner_facing_english_materialized":False,
        "current360_materialized":False,
        "spoken360_materialized":False,
        "pattern360_materialized":False,
        "far_materialized":False,
        "pdf_materialized":False,
        "can_interrogative_mastery_unlocked":False,
        "can_negative_mastery_unlocked":False,
        "permission_request_offer_possibility_can_unlocked":False,
        "a2_a2plus_unlocked":False,
      },
      "next_short_step":NEXT_SHORT_STEP,
    }
    return report

def main()->int:
    r=build_unit06_scene_diversity_expansion()
    print(f"STATUS={r['status']}")
    print(f"PREDECESSOR_U05_SCENES={r['predecessor_distinct_scene_instance_count']}")
    print(f"CURRENT_U06_SCENES={r['current_distinct_scene_instance_count']}")
    print(f"GROWTH={r['coverage']['scene_growth_over_predecessor']}")
    print(f"CHUNKS={r['coverage']['functional_chunk_scene_coverage']}")
    print(f"VERBS={r['coverage']['source_verb_scene_coverage']}")
    print(f"SUCCESSOR_MINIMUM={r['successor_required_minimum_scene_instance_count']}")
    print(f"NEXT_SHORT_STEP={r['next_short_step']}")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
