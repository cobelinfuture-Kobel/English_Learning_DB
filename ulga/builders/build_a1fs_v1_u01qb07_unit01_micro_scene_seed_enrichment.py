#!/usr/bin/env python3
"""Build and admit policy-bound Unit01 life-scene enrichment from approved anchors."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as content_policy
from ulga.builders import build_a1fs_v1_u01qb06_unit01_micro_scene_pool_inventory as r1

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"
A1FS_CONTENT_POLICY_EXEMPTION = ""
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB07_Unit01MicroSceneSeedEnrichmentAndRotationCapacityExpansion"
PRODUCER_ID = "build_a1fs_v1_u01qb07_unit01_micro_scene_seed_enrichment"
VALIDATOR_ID = "validate_a1fs_v1_u01qb07_unit01_micro_scene_seed_enrichment"
SCHEMA_VERSION = "a1fs.v1.u01qb07.unit01_cumulative_scene_pool.v1"
SPEC_SCHEMA_VERSION = "a1fs.v1.u01qb07.unit01_model_authored_scene_supplement.v1"
PASS_STATUS = "PASS_A1FS_V1_U01QB07_UNIT01_MICRO_SCENE_SEED_ENRICHMENT_AND_ROTATION_CAPACITY_EXPANSION"
VALIDATION_PASS_STATUS = "PASS_A1FS_V1_U01QB07_UNIT01_MICRO_SCENE_SEED_ENRICHMENT_VALIDATION"
UNIT_ID = "GRAMMAR_ARTICLES_BASIC"
TARGET_MIN = 28
TARGET_MAX = 36
EXPECTED_SUPPLEMENT_COUNT = 27
DEFAULT_SPEC = Path("ulga/contracts/a1fs_v1_u01qb07_unit01_model_authored_scene_supplement.json")
DEFAULT_OUTPUT = Path("ulga/reports/a1fs_v1_u01qb07_unit01_cumulative_scene_pool.candidate.json")
NEXT_SHORT_STEP = "A1FS-V1-U01QB08_Unit01TwelveFormSceneRotationMaterialization"


class SceneEnrichmentError(ValueError):
    pass


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SceneEnrichmentError(f"UNREADABLE_JSON:{path}:{exc}") from exc


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def inventory_rows(inventory: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = inventory.get("scene_rows")
    if not isinstance(rows, list) or not all(isinstance(row, Mapping) for row in rows):
        raise SceneEnrichmentError("R1_SCENE_ROWS_REQUIRED")
    return [deepcopy(dict(row)) for row in rows]


def candidates(spec: Mapping[str, Any]) -> list[dict[str, Any]]:
    if (
        spec.get("schema_version") != SPEC_SCHEMA_VERSION
        or spec.get("task_id") != TASK_ID
        or spec.get("unit_id") != UNIT_ID
    ):
        raise SceneEnrichmentError("SUPPLEMENT_SPEC_IDENTITY_INVALID")
    rows = spec.get("candidates")
    if (
        not isinstance(rows, list)
        or len(rows) != EXPECTED_SUPPLEMENT_COUNT
        or not all(isinstance(row, Mapping) for row in rows)
    ):
        raise SceneEnrichmentError("SUPPLEMENT_27_CANDIDATES_REQUIRED")
    return [deepcopy(dict(row)) for row in rows]


def eligible_anchor_rows(rows: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [
        row
        for row in rows
        if row.get("scene_origin") == "CANONICAL_UNIT01_CONTEXT"
        or (
            row.get("scene_origin") == "REAL62_CONTENT_ASSET"
            and row.get("lineage_mode") != "PROJECT_AUTHORED_CONTRACT_COMPLETION"
        )
    ]


def resolve_anchor_refs(objects: set[str], anchors: Sequence[Mapping[str, Any]]) -> list[str]:
    remaining = set(objects)
    chosen: list[str] = []
    while remaining:
        ranked = sorted(
            (
                (
                    len(remaining & set(row.get("semantic_scene_core", {}).get("objects") or [])),
                    str(row.get("scene_ref_id") or ""),
                    row,
                )
                for row in anchors
            ),
            key=lambda item: (-item[0], item[1]),
        )
        if not ranked or ranked[0][0] == 0:
            raise SceneEnrichmentError("UNBACKED_MODEL_OBJECTS:" + ",".join(sorted(remaining)))
        _, ref, row = ranked[0]
        chosen.append(ref)
        remaining -= set(row.get("semantic_scene_core", {}).get("objects") or [])
    return chosen


def model_scene_row(candidate: Mapping[str, Any], anchors: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    required = {
        "candidate_id",
        "introduced_unit_id",
        "source_class",
        "large_situation_family",
        "medium_setting",
        "small_micro_scene_event",
        "participants",
        "objects",
        "actions",
        "relations",
        "information_structure",
        "communicative_function_ids",
        "communicative_goal",
        "source_claim",
    }
    if required - set(candidate):
        raise SceneEnrichmentError("CANDIDATE_FIELDS_MISSING:" + str(candidate.get("candidate_id")))
    if (
        candidate["source_class"] != "MODEL_AUTHORED_FROM_APPROVED_SEEDS"
        or candidate["source_claim"] != "SEED_ANCHORED_MODEL_AUTHORED_NOT_SOURCE_EQUIVALENT"
    ):
        raise SceneEnrichmentError("MODEL_PROVENANCE_INVALID:" + str(candidate["candidate_id"]))
    if candidate["introduced_unit_id"] != UNIT_ID:
        raise SceneEnrichmentError("INTRODUCED_UNIT_INVALID:" + str(candidate["candidate_id"]))

    core = r1.semantic_scene_core(
        setting=str(candidate["medium_setting"]),
        participants=candidate["participants"],
        objects=candidate["objects"],
        descriptors=candidate.get("descriptors") or [],
        actions=candidate["actions"],
        relations=candidate["relations"],
        information_structure=candidate["information_structure"],
        communicative_functions=candidate["communicative_function_ids"],
    )
    reasons = r1.genuine_scene_reason_codes(core)
    if reasons:
        raise SceneEnrichmentError(
            "MODEL_SCENE_GATE_FAIL:" + str(candidate["candidate_id"]) + ":" + ",".join(reasons)
        )
    taxonomy = r1.scene_taxonomy(core)
    if taxonomy["large_situation_family"] != candidate["large_situation_family"]:
        raise SceneEnrichmentError("MODEL_SCENE_FAMILY_MISMATCH:" + str(candidate["candidate_id"]))
    refs = resolve_anchor_refs(set(core["objects"]), anchors)
    return {
        "scene_origin": "MODEL_AUTHORED_SCENE_ENRICHMENT",
        "scene_ref_id": str(candidate["candidate_id"]),
        "introduced_unit_id": UNIT_ID,
        "semantic_scene_signature_v2": r1.digest(core),
        "semantic_scene_core": core,
        "scene_taxonomy": taxonomy,
        "situation_family": taxonomy["large_situation_family"],
        "small_micro_scene_event": str(candidate["small_micro_scene_event"]),
        "communicative_goal": str(candidate["communicative_goal"]),
        "lineage_mode": "MODEL_AUTHORED_FROM_APPROVED_SEEDS",
        "source_authority": "PROJECT_MODEL_AUTHORED_SCENE_ENRICHMENT",
        "provenance": {
            "resolved_seed_scene_ref_ids": refs,
            "source_claim": str(candidate["source_claim"]),
            "source_equivalence_claimed": False,
        },
        "rotation_class": "ROTATION_READY",
        "rotation_reason_codes": [],
        "counts_toward_scene_rotation": True,
    }


def unique_combined(
    existing: Sequence[Mapping[str, Any]],
    model: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    seen: dict[str, str] = {}
    output: list[dict[str, Any]] = []
    for row in list(existing) + list(model):
        signature = str(row["semantic_scene_signature_v2"])
        if signature in seen:
            raise SceneEnrichmentError(
                f"SEMANTIC_SCENE_DUPLICATE:{signature}:{seen[signature]}:{row.get('scene_ref_id')}"
            )
        seen[signature] = str(row.get("scene_ref_id"))
        output.append(
            {
                "semantic_scene_signature_v2": signature,
                "scene_ref_id": str(row.get("scene_ref_id")),
                "situation_family": str(row.get("situation_family")),
                "setting": str(row.get("semantic_scene_core", {}).get("setting")),
                "micro_scene_event_id": str(
                    (row.get("scene_taxonomy") or {}).get("small_micro_scene_event_id")
                ),
                "scene_origin": str(row.get("scene_origin")),
            }
        )
    return output


def build_pool_payload(r1_inventory: Mapping[str, Any], spec: Mapping[str, Any]) -> dict[str, Any]:
    rows = inventory_rows(r1_inventory)
    existing = [row for row in rows if row.get("counts_toward_scene_rotation") is True]
    anchors = eligible_anchor_rows(rows)
    supplement = candidates(spec)
    ids = [str(row["candidate_id"]) for row in supplement]
    if len(ids) != len(set(ids)):
        raise SceneEnrichmentError("DUPLICATE_CANDIDATE_ID")

    model = [model_scene_row(row, anchors) for row in supplement]
    combined = unique_combined(existing, model)
    families = Counter(row["situation_family"] for row in combined)
    total = len(combined)
    family_count = len([key for key, value in families.items() if value and key != "UNCLASSIFIED_OBJECT"])
    target = TARGET_MIN <= total <= TARGET_MAX
    rotation = total >= r1.HARD_MIN_DISTINCT_MICRO_SCENES and family_count >= r1.MIN_POOL_SITUATION_FAMILIES
    if not target:
        raise SceneEnrichmentError(f"TARGET_SCENE_RANGE_FAIL:{total}")

    payload = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "unit_id": UNIT_ID,
        "scope": {
            "unit01_only": True,
            "question_bank_modified": False,
            "parallel_question_bank_created": False,
            "scoring_modified": False,
            "learner_state_modified": False,
            "unit02_to_unit24_modified": False,
            "a2_unlocked": False,
        },
        "scene_growth_policy": deepcopy(r1.SCENE_GROWTH_POLICY),
        "source_counts": {
            "r1_scene_row_count": len(rows),
            "existing_rotation_ready_scene_count": len(existing),
            "eligible_anchor_row_count": len(anchors),
            "model_authored_supplement_count": len(model),
        },
        "model_authored_scenes": model,
        "cumulative_unique_scenes": combined,
        "situation_family_counts": dict(sorted(families.items())),
        "rotation_capacity": {
            "genuine_distinct_micro_scene_count": total,
            "target_range": [TARGET_MIN, TARGET_MAX],
            "target_range_pass": target,
            "hard_min_24_pass": total >= 24,
            "situation_family_count": family_count,
            "situation_family_min_5_pass": family_count >= 5,
            "maximum_scene_slots_at_two_uses_each": total * 2,
            "required_scene_slots": 48,
            "twelve_form_rotation_ready": rotation,
        },
        "boundaries": {
            "source_equivalence_claimed": False,
            "question_items_mutated": False,
            "scoring_mutated": False,
            "learner_state_mutated": False,
            "mastery_claimed": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    payload["pool_sha256"] = r1.digest(payload)
    return payload


def build_pool(r1_inventory: Mapping[str, Any], spec: Mapping[str, Any]) -> dict[str, Any]:
    payload = build_pool_payload(r1_inventory, spec)
    return content_policy.build_candidate(
        payload=payload,
        producer_id=PRODUCER_ID,
        level_scope=["A1", "A1+"],
        source_bindings={
            "unit_id": UNIT_ID,
            "r1_inventory_sha256": str(r1_inventory.get("inventory_sha256") or r1.digest(r1_inventory)),
            "supplement_spec_sha256": r1.digest(spec),
            "existing_rotation_ready_scene_count": payload["source_counts"]["existing_rotation_ready_scene_count"],
            "model_authored_supplement_count": payload["source_counts"]["model_authored_supplement_count"],
            "source_equivalence_claimed": False,
        },
    )


def admit_validated_candidate(
    candidate: Mapping[str, Any], validation_report: Mapping[str, Any]
) -> dict[str, Any]:
    if validation_report.get("status") != VALIDATION_PASS_STATUS:
        raise SceneEnrichmentError("VALIDATION_REPORT_NOT_PASS")
    if validation_report.get("candidate_artifact_sha256") != candidate.get("artifact_sha256"):
        raise SceneEnrichmentError("VALIDATION_REPORT_CANDIDATE_MISMATCH")
    report_sha256 = validation_report.get("report_sha256")
    unsigned_report = dict(validation_report)
    unsigned_report.pop("report_sha256", None)
    if (
        not isinstance(report_sha256, str)
        or len(report_sha256) != 64
        or report_sha256 != content_policy.digest(unsigned_report)
    ):
        raise SceneEnrichmentError("VALIDATION_REPORT_SHA256_INVALID")
    return content_policy.admit_candidate(
        candidate,
        validation_receipts=[
            {
                "validator_id": VALIDATOR_ID,
                "status": "PASS",
                "receipt_sha256": report_sha256,
            }
        ],
        decision_ref=f"{TASK_ID}:INDEPENDENT_VALIDATION_PASS",
        producer_id=PRODUCER_ID,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r1-inventory", type=Path, required=True)
    parser.add_argument("--supplement-spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--validation-report", type=Path)
    args = parser.parse_args(argv)
    try:
        candidate = build_pool(read_json(args.r1_inventory), read_json(args.supplement_spec))
        artifact = candidate
        if args.validation_report is not None:
            artifact = admit_validated_candidate(candidate, read_json(args.validation_report))
        write_json(args.output, artifact)
    except (SceneEnrichmentError, content_policy.ContentPolicyBuildError, KeyError, TypeError, ValueError, OSError) as exc:
        print("STATUS=FAIL_A1FS_V1_U01QB07_UNIT01_MICRO_SCENE_SEED_ENRICHMENT")
        print(f"ERROR={exc}")
        return 1
    capacity = artifact["payload"]["rotation_capacity"]
    print(f"STATUS={PASS_STATUS}")
    print(f"ARTIFACT_ROLE={artifact['artifact_role']}")
    print(f"EXISTING_SCENES={artifact['payload']['source_counts']['existing_rotation_ready_scene_count']}")
    print(f"MODEL_AUTHORED_SCENES={artifact['payload']['source_counts']['model_authored_supplement_count']}")
    print(f"CUMULATIVE_DISTINCT_SCENES={capacity['genuine_distinct_micro_scene_count']}")
    print(f"SITUATION_FAMILIES={capacity['situation_family_count']}")
    print(f"TWELVE_FORM_ROTATION_READY={capacity['twelve_form_rotation_ready']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
