#!/usr/bin/env python3
"""Unit06 Reader360 P02A: representative Current360 pilot acceptance."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from product.a1fs_v1_2_1 import u06r360p01_natural360_source_projection as p01

TASK_ID="A1FS-V1-U06R360P02A_RepresentativeCurrent360PilotHumanReview"
STATUS="PASS_A1FS_V1_U06R360P02A_REPRESENTATIVE_CURRENT360_PILOT_MACHINE_ACCEPTANCE"
NEXT_SHORT_STEP="HUMAN_REVIEW_THEN_APPLY_APPROVED_NATURAL_STYLE_TO_FULL360_DRAFT"
REPO_ROOT=Path(__file__).resolve().parents[2]
DATA_PATH=REPO_ROOT/"product/a1fs_v1_2_1/data/u06r360p02a_current360_pilot12_gpt56.json"

FORBIDDEN_THERE_BE=re.compile(r"\bthere\s+(?:is|are)\b",re.I)
FORBIDDEN_PAST_BE=re.compile(r"\b(?:was|were)\b",re.I)
FORBIDDEN_CAN_NEGATIVE=re.compile(r"\b(?:cannot|can\s+not|can't)\b",re.I)
PRESENT_CONTINUOUS_SHAPE=re.compile(r"\b(?:am|is|are)\s+([A-Za-z]+ing)\b",re.I)

class PilotError(ValueError):
    pass

def _norm(text:str)->str:
    return re.sub(r"\s+"," ",text).strip().casefold()

def _sentence_count(text:str)->int:
    return len(re.findall(r"[^.!?]+[.!?]",text))

def _all_source_chunks()->set[str]:
    p=p01.build_unit06_natural360_source_projection()
    return {
        _norm(row["normalized_surface"])
        for cluster in p["source_clusters"]
        for row in cluster["functional_chunks"]
    }

def build_report()->dict[str,Any]:
    data=json.loads(DATA_PATH.read_text(encoding="utf-8"))
    if data.get("task_id")!=TASK_ID:
        raise PilotError("TASK_ID_DRIFT")
    if data.get("learner_facing_language_author")!="GPT-5.6 Sol":
        raise PilotError("AUTHOR_DRIFT")
    if data.get("python_may_generate_or_rewrite_learner_facing_english") is not False:
        raise PilotError("PYTHON_AUTHORING_NOT_DISABLED")
    contract=data["pilot_contract"]
    if contract.get("fixed_sentence_count") is not False:
        raise PilotError("FIXED_SENTENCE_COUNT_NOT_DISABLED")
    if contract.get("scene_first_support") is not True:
        raise PilotError("SCENE_FIRST_SUPPORT_NOT_LOCKED")
    if contract.get("chunk_stuffing_forbidden") is not True:
        raise PilotError("CHUNK_STUFFING_NOT_FORBIDDEN")
    if contract.get("support_sentence_requires_chunk_lineage") is not False:
        raise PilotError("SUPPORT_SENTENCE_CHUNK_LINEAGE_STILL_FORCED")
    if contract.get("full360_chunk_coverage_is_corpus_level") is not True:
        raise PilotError("CORPUS_LEVEL_CHUNK_COVERAGE_NOT_LOCKED")

    episodes=list(data["episodes"])
    if len(episodes)!=12:
        raise PilotError(f"PILOT_COUNT_DRIFT:{len(episodes)}")
    if len({x["pilot_id"] for x in episodes})!=12:
        raise PilotError("PILOT_ID_COLLISION")
    if len({x["scene_family"] for x in episodes})!=12:
        raise PilotError("SCENE_FAMILY_PILOT_COVERAGE_DRIFT")
    paragraphs=[_norm(x["paragraph"]) for x in episodes]
    if len(set(paragraphs))!=12:
        raise PilotError("PILOT_PARAGRAPH_DUPLICATE")

    source_chunks=_all_source_chunks()
    counts=[]
    target_counts=[]
    for row in episodes:
        if row.get("semantic_review")!="PASS":
            raise PilotError(f"SEMANTIC_REVIEW_NOT_PASS:{row['pilot_id']}")
        paragraph=str(row["paragraph"]).strip()
        count=_sentence_count(paragraph)
        counts.append(count)
        if not 4<=count<=8:
            raise PilotError(f"NATURAL_SENTENCE_RANGE_FAIL:{row['pilot_id']}:{count}")
        if "?" in paragraph:
            raise PilotError(f"INTERROGATIVE_LEAKAGE:{row['pilot_id']}")
        if FORBIDDEN_THERE_BE.search(paragraph):
            raise PilotError(f"THERE_BE_LEAKAGE:{row['pilot_id']}")
        if FORBIDDEN_PAST_BE.search(paragraph):
            raise PilotError(f"PAST_BE_LEAKAGE:{row['pilot_id']}")
        if FORBIDDEN_CAN_NEGATIVE.search(paragraph):
            raise PilotError(f"CAN_NEGATIVE_LEAKAGE:{row['pilot_id']}")
        continuous=[
            m.group(1).casefold()
            for m in PRESENT_CONTINUOUS_SHAPE.finditer(paragraph)
            if m.group(1).casefold()!="morning"
        ]
        if continuous:
            raise PilotError(f"PRESENT_CONTINUOUS_LEAKAGE:{row['pilot_id']}:{continuous}")
        targets=[_norm(x) for x in row.get("target_chunk_surfaces") or []]
        target_counts.append(len(targets))
        if not 1<=len(targets)<=2:
            raise PilotError(f"TARGET_CHUNK_COUNT_UNNATURAL:{row['pilot_id']}:{len(targets)}")
        for chunk in targets:
            if chunk not in source_chunks:
                raise PilotError(f"TARGET_CHUNK_NOT_AUTHORIZED:{row['pilot_id']}:{chunk}")
            if chunk not in _norm(paragraph):
                raise PilotError(f"TARGET_CHUNK_NOT_REALIZED:{row['pilot_id']}:{chunk}")

    if len(set(counts))<3:
        raise PilotError(f"SENTENCE_COUNT_VARIETY_INSUFFICIENT:{counts}")
    if all(count==5 for count in counts):
        raise PilotError("FIVE_SENTENCE_TEMPLATE_LOCK_DETECTED")

    return {
        "schema_version":"a1fs.v1.u06.r360.p02a.current360_pilot_acceptance.v1",
        "task_id":TASK_ID,
        "status":STATUS,
        "pilot_count":len(episodes),
        "scene_family_count":len({x["scene_family"] for x in episodes}),
        "sentence_count_distribution":{str(n):counts.count(n) for n in sorted(set(counts))},
        "sentence_count_min":min(counts),
        "sentence_count_max":max(counts),
        "target_chunk_count_min":min(target_counts),
        "target_chunk_count_max":max(target_counts),
        "unique_paragraph_count":len(set(paragraphs)),
        "fixed_sentence_count":False,
        "scene_first_support":True,
        "chunk_stuffing_forbidden":True,
        "support_sentence_requires_chunk_lineage":False,
        "full360_chunk_coverage_is_corpus_level":True,
        "human_review_status":data["human_review_status"],
        "episodes":episodes,
        "next_short_step":NEXT_SHORT_STEP,
    }

def main()->int:
    r=build_report()
    print(f"STATUS={r['status']}")
    print(f"PILOT={r['pilot_count']}")
    print(f"SCENE_FAMILIES={r['scene_family_count']}")
    print(f"SENTENCE_COUNTS={r['sentence_count_distribution']}")
    print(f"UNIQUE={r['unique_paragraph_count']}")
    print(f"HUMAN_REVIEW={r['human_review_status']}")
    print(f"NEXT_SHORT_STEP={r['next_short_step']}")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
