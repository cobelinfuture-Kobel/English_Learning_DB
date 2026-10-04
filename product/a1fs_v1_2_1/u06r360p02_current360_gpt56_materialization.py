#!/usr/bin/env python3
"""Unit06 Reader360 P02: GPT-5.6 Current360 natural episode materialization.

Static learner-facing English is authored and semantically reviewed by GPT-5.6 Sol.
Python only loads, joins, counts, validates and reports the corpus.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from product.a1fs_v1_2_1 import u06r360p01_natural360_source_projection as p01
from product.a1fs_v1_2_1 import u06r360p01_scene_diversity_expansion as p01r1

A1FS_CONTENT_POLICY_MODE="NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION=(
    "Validation-only loader for static GPT-5.6-authored Current360 JSON shards. "
    "Python may count, bind, deduplicate and validate but may not generate, rewrite, "
    "paraphrase or repair learner-facing English."
)
TASK_ID="A1FS-V1-U06R360P02_Current360GPT56NaturalEpisodeMaterialization"
STATUS="PASS_A1FS_V1_U06R360P02_CURRENT360_GPT56_NATURAL_EPISODE_MATERIALIZATION"
NEXT_SHORT_STEP="A1FS-V1-U06R360P03_Spoken360GPT56DialogueMaterialization"
REPO_ROOT=Path(__file__).resolve().parents[2]
DATA_PATHS=tuple(
    REPO_ROOT/f"product/a1fs_v1_2_1/data/u06r360p02_current360_gpt56_e{start:03d}_e{start+59:03d}.json"
    for start in (1,61,121,181,241,301)
)
FORBIDDEN_THERE_BE=re.compile(r"\bthere\s+(?:is|are)\b",re.I)
FORBIDDEN_PAST_BE=re.compile(r"\b(?:was|were)\b",re.I)
FORBIDDEN_CAN_NEGATIVE=re.compile(r"\b(?:cannot|can\s+not|can't)\b",re.I)
PRESENT_CONTINUOUS=re.compile(r"\b(?:am|is|are)\s+([A-Za-z]+ing)\b",re.I)
FORBIDDEN_SIMPLE_3SG=re.compile(
    r"\b(?:has|does|goes|comes|knows|opens|finishes|starts|checks|throws|waits|"
    r"understands|writes|reads|plays|runs|walks|helps|sings|sits|stands|works|"
    r"lives|likes|wants|needs)\b",re.I
)
FORBIDDEN_SIMPLE_PLURAL=re.compile(
    r"\b(?:i|you|we|they)\s+(?:know|finish|start|check|open|come|understand|"
    r"write|read|play|run|walk|help|sing|sit|stand|work|live|like|want|need)\b",re.I
)

class U06Current360Error(ValueError):
    pass

def _norm(value:str)->str:
    return re.sub(r"\s+"," ",str(value)).strip().casefold()

def _sentence_count(value:str)->int:
    return len(re.findall(r"[^.!?]+[.!?]",str(value)))

def _load(path:Path)->dict[str,Any]:
    value=json.loads(path.read_text(encoding="utf-8"))
    if value.get("task_id")!=TASK_ID:
        raise U06Current360Error(f"TASK_ID_DRIFT:{path.name}")
    if value.get("learner_facing_language_author")!="GPT-5.6 Sol":
        raise U06Current360Error(f"AUTHOR_DRIFT:{path.name}")
    if value.get("python_may_generate_or_rewrite_learner_facing_english") is not False:
        raise U06Current360Error(f"PYTHON_AUTHORING_NOT_DISABLED:{path.name}")
    if value.get("pilot_human_review_status")!="APPROVED_BY_OPERATOR":
        raise U06Current360Error(f"PILOT_NOT_APPROVED:{path.name}")
    return value

def _validate_language(row:dict[str,Any])->int:
    eid=str(row["episode_id"])
    paragraph=str(row["paragraph"]).strip()
    count=_sentence_count(paragraph)
    if not 4<=count<=8:
        raise U06Current360Error(f"NATURAL_SENTENCE_RANGE_FAIL:{eid}:{count}")
    if "?" in paragraph:
        raise U06Current360Error(f"INTERROGATIVE_LEAKAGE:{eid}")
    if FORBIDDEN_THERE_BE.search(paragraph):
        raise U06Current360Error(f"THERE_BE_LEAKAGE:{eid}")
    if FORBIDDEN_PAST_BE.search(paragraph):
        raise U06Current360Error(f"PAST_BE_LEAKAGE:{eid}")
    if FORBIDDEN_CAN_NEGATIVE.search(paragraph):
        raise U06Current360Error(f"CAN_NEGATIVE_LEAKAGE:{eid}")
    continuous=[
        match.group(1).casefold()
        for match in PRESENT_CONTINUOUS.finditer(paragraph)
        if match.group(1).casefold()!="morning"
    ]
    if continuous:
        raise U06Current360Error(f"PRESENT_CONTINUOUS_LEAKAGE:{eid}:{continuous}")
    if FORBIDDEN_SIMPLE_3SG.search(paragraph):
        raise U06Current360Error(
            f"NONCAN_SUPPORT_PRESENT_SIMPLE_3SG_LEAKAGE:{eid}:"
            f"{FORBIDDEN_SIMPLE_3SG.findall(paragraph)}"
        )
    if FORBIDDEN_SIMPLE_PLURAL.search(paragraph):
        raise U06Current360Error(
            f"NONCAN_SUPPORT_PRESENT_SIMPLE_PLURAL_LEAKAGE:{eid}:"
            f"{FORBIDDEN_SIMPLE_PLURAL.findall(paragraph)}"
        )
    targets=[_norm(x) for x in row.get("target_chunk_surfaces") or []]
    if not 1<=len(targets)<=2:
        raise U06Current360Error(f"TARGET_CHUNK_COUNT_INVALID:{eid}:{len(targets)}")
    norm=_norm(paragraph)
    for target in targets:
        if target not in norm:
            raise U06Current360Error(f"TARGET_CHUNK_NOT_REALIZED:{eid}:{target}")
    if row.get("author_model")!="GPT-5.6 Sol":
        raise U06Current360Error(f"EPISODE_AUTHOR_DRIFT:{eid}")
    if row.get("gpt56_semantic_review")!="PASS":
        raise U06Current360Error(f"SEMANTIC_REVIEW_NOT_PASS:{eid}")
    if row.get("natural_style_review")!="PASS":
        raise U06Current360Error(f"NATURAL_STYLE_REVIEW_NOT_PASS:{eid}")
    return count

def build_report()->dict[str,Any]:
    projection=p01.build_unit06_natural360_source_projection()
    diversity=p01r1.build_unit06_scene_diversity_expansion()
    if projection.get("status")!=p01.STATUS:
        raise U06Current360Error("P01_NOT_PASS")
    if diversity.get("status")!=p01r1.STATUS:
        raise U06Current360Error("P01R1_NOT_PASS")
    shards=[_load(path) for path in DATA_PATHS]
    episodes=[row for shard in shards for row in shard["episodes"]]
    if len(episodes)!=360:
        raise U06Current360Error(f"EPISODE_COUNT_DRIFT:{len(episodes)}")
    if len({x["episode_id"] for x in episodes})!=360:
        raise U06Current360Error("EPISODE_ID_COLLISION")
    if len({x["episode_slot_id"] for x in episodes})!=360:
        raise U06Current360Error("EPISODE_SLOT_COLLISION")
    if len({_norm(x["paragraph"]) for x in episodes})!=360:
        raise U06Current360Error("EXACT_PARAGRAPH_DUPLICATE")

    slots=list(projection["episode_authoring_slots"])
    if len(slots)!=360:
        raise U06Current360Error("P01_SLOT_DENOMINATOR_DRIFT")
    authorized={
        _norm(chunk["normalized_surface"])
        for cluster in projection["source_clusters"]
        for chunk in cluster["functional_chunks"]
    }
    if len(authorized)!=182:
        raise U06Current360Error(f"AUTHORIZED_CHUNK_DENOMINATOR_DRIFT:{len(authorized)}")

    sentence_counts=[]
    cluster_sentence_counts:dict[str,set[int]]={}
    corpus_targets:set[str]=set()
    scene_family_counts=Counter()
    output=[]
    controlled_chunk_family={}
    for scene in diversity["reader360_local_scene_instances"]:
        controlled_chunk_family.setdefault(_norm(scene["functional_chunk_surface"]),str(scene["scene_family"]))

    for index,(row,slot) in enumerate(zip(episodes,slots),start=1):
        eid=f"U06-NEB-E{index:03d}"
        sid=f"U06-N360-S{index:03d}"
        if row["episode_id"]!=eid or row["episode_slot_id"]!=sid:
            raise U06Current360Error(f"IDENTITY_ORDER_DRIFT:{eid}:{row['episode_id']}:{row['episode_slot_id']}")
        count=_validate_language(row)
        sentence_counts.append(count)
        cluster=str(slot["cluster_id"])
        cluster_sentence_counts.setdefault(cluster,set()).add(count)
        targets={_norm(x) for x in row["target_chunk_surfaces"]}
        if not targets<=authorized:
            raise U06Current360Error(f"UNAUTHORIZED_TARGET_CHUNK:{eid}:{sorted(targets-authorized)}")
        corpus_targets.update(targets)
        family=slot.get("scene_family")
        if family is None:
            family=controlled_chunk_family.get(sorted(targets)[0])
        if not family:
            raise U06Current360Error(f"SCENE_FAMILY_LINEAGE_MISSING:{eid}")
        scene_family_counts[str(family)]+=1
        output.append({
            **row,
            "cluster_id":cluster,
            "scene_family":str(family),
            "scene_lineage_mode":"P01R1_SCENE_FAMILY_PLUS_TARGET_CHUNK_SEMANTIC_LINEAGE",
        })

    if corpus_targets!=authorized:
        raise U06Current360Error(
            f"CORPUS_CHUNK_COVERAGE_GAP:{len(corpus_targets)}/182:"
            f"{sorted(authorized-corpus_targets)[:20]}"
        )
    if len(scene_family_counts)!=12:
        raise U06Current360Error(f"SCENE_FAMILY_COVERAGE_DRIFT:{len(scene_family_counts)}")
    if len(cluster_sentence_counts)!=13:
        raise U06Current360Error(f"CLUSTER_COUNT_DRIFT:{len(cluster_sentence_counts)}")
    for cluster,counts in cluster_sentence_counts.items():
        if not {4,5,6}<=counts:
            raise U06Current360Error(f"FIXED_LENGTH_RISK:{cluster}:{sorted(counts)}")

    predecessor=int(diversity["predecessor_distinct_scene_instance_count"])
    reservoir=int(diversity["current_distinct_scene_instance_count"])
    if reservoir<=predecessor:
        raise U06Current360Error("SCENE_DIVERSITY_MONOTONIC_RULE_BROKEN")

    distribution=dict(sorted(Counter(sentence_counts).items()))
    return {
        "schema_version":"a1fs.v1.u06.r360.current360_gpt56_materialization.v2",
        "task_id":TASK_ID,
        "status":STATUS,
        "episode_count":360,
        "unique_paragraph_count":360,
        "learner_facing_language_author":"GPT-5.6 Sol",
        "python_may_generate_or_rewrite_learner_facing_english":False,
        "pilot_human_review_status":"APPROVED_BY_OPERATOR",
        "sentence_count_policy":"NATURAL_VARIABLE_4_TO_8_NOT_FIXED",
        "sentence_count_distribution":distribution,
        "sentence_count_min":min(sentence_counts),
        "sentence_count_max":max(sentence_counts),
        "clusters_with_4_5_6_sentence_variety":sum({4,5,6}<=v for v in cluster_sentence_counts.values()),
        "source_cluster_count":len(cluster_sentence_counts),
        "scene_family_count":len(scene_family_counts),
        "scene_family_episode_counts":dict(sorted(scene_family_counts.items())),
        "functional_chunk_realization_coverage":"182/182",
        "scene_first_support":True,
        "chunk_stuffing_forbidden":True,
        "per_episode_preassigned_chunk_surface_realization_required":False,
        "scene_diversity_policy_id":diversity["scene_diversity_policy_id"],
        "scene_diversity_reservoir_count":reservoir,
        "predecessor_scene_diversity_count":predecessor,
        "scene_diversity_growth_over_predecessor":reservoir-predecessor,
        "scope_safety":{
            "q01_q10_modified":False,
            "q07_canonical_scene_authority_modified":False,
            "q07r1_chunk_semantics_modified":False,
            "new_global_scene_family_created":False,
            "spoken360_materialized":False,
            "pattern360_materialized":False,
            "far_materialized":False,
            "pdf_materialized":False,
            "can_interrogative_mastery_unlocked":False,
            "can_negative_mastery_unlocked":False,
            "permission_request_offer_possibility_can_unlocked":False,
            "a2_a2plus_unlocked":False,
        },
        "episodes":output,
        "next_short_step":NEXT_SHORT_STEP,
    }

def main()->int:
    r=build_report()
    print(f"STATUS={r['status']}")
    print(f"EPISODES={r['episode_count']}")
    print(f"UNIQUE={r['unique_paragraph_count']}")
    print(f"SENTENCE_COUNTS={r['sentence_count_distribution']}")
    print(f"CLUSTERS_WITH_4_5_6={r['clusters_with_4_5_6_sentence_variety']}/{r['source_cluster_count']}")
    print(f"CHUNKS={r['functional_chunk_realization_coverage']}")
    print(f"SCENE_FAMILIES={r['scene_family_count']}")
    print(f"SCENE_RESERVOIR={r['scene_diversity_reservoir_count']}")
    print(f"SCENE_GROWTH={r['scene_diversity_growth_over_predecessor']}")
    print(f"NEXT_SHORT_STEP={r['next_short_step']}")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
