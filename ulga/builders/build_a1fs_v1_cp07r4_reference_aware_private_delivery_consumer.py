#!/usr/bin/env python3
"""Build a private R3F-aware four-skill delivery consumer.

The M4-selected KET Asset Body is always mounted from M2. Optional RAZ context
is projected through the existing policy-bound CP05 path only when R3F selected
exact context items. Missing KET99 references or contextual projections never
block the selected A1/A1+ KET lesson. The contract reports response and media
capability exactly; it does not fabricate scoring, audio, recording, mastery,
or learner-attempt evidence.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_cp05_private_candidate_materialization_and_admission as cp05  # noqa: E402
from ulga.builders import build_a1fs_v1_cp07r3f_reference_aware_optional_context_lesson_composition as r3f  # noqa: E402
from ulga.builders import build_a1fs_v1_m2_four_skill_asset_body_consumer as m2  # noqa: E402
from ulga.builders import build_a1fs_v1_policy_bound_content_artifact  # noqa: E402
from ulga.builders import cp07d_private_four_skill_delivery_consumer_impl as cp07d  # noqa: E402

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"

TASK_ID = "A1FS-V1-CP07F-R4_ReferenceAwarePrivateDeliveryConsumer"
SCHEMA_VERSION = "a1fs.v1.cp07f.r4.reference_aware_private_delivery_consumer.v1"
PASS_STATUS = "PASS_CP07F_R4_REFERENCE_AWARE_PRIVATE_DELIVERY_CONSUMER_READY"
NEXT_SHORT_STEP = "A1FS-V1-CP07F-R4A_KETAssetResponseAndMediaCapabilityAdmission"

DEFAULT_M2 = cp07d.DEFAULT_M2
DEFAULT_CP05_APPROVED = cp07d.DEFAULT_CP05_APPROVED
DEFAULT_R3F = r3f.DEFAULT_OUTPUT
DEFAULT_OUTPUT = REPO_ROOT / ".local/a1fs_v1/cp07r4/reference_aware_private_delivery_consumer.private.json"
DEFAULT_REPORT = REPO_ROOT / ".local/a1fs_v1/cp07r4/reference_aware_private_delivery_consumer.validation.json"

SKILLS = cp07d.SKILLS
CAPTURE_ROLES = cp07d.CAPTURE_ROLES
SPEAKING_RECORDING_ROLES = cp07d.SPEAKING_RECORDING_ROLES
ALLOWED_MODES = {
    "KET_ONLY_NO_EXACT_KET99_REFERENCE",
    "KET_WITH_KET99_REFERENCE_AND_OPTIONAL_CONTEXT",
    "KET_WITH_KET99_REFERENCE_CONTEXT_UNAVAILABLE",
    "KET_WITH_KET99_REFERENCE_NO_GRAMMAR_CONTEXT",
}


class R4BuildError(ValueError):
    """Fail-closed source, identity, projection, or delivery-contract error."""


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise R4BuildError(f"json_object_required:{path}")
    return value


def _verify_r3f(plan: Mapping[str, Any], consumer: Mapping[str, Any]) -> tuple[Mapping[str, Any], Mapping[str, Any], list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    if plan.get("cp07r3f_task_id") != r3f.TASK_ID or plan.get("cp07r3f_schema_version") != r3f.SCHEMA_VERSION:
        raise R4BuildError("r3f_contract_invalid")
    if plan.get("cp07r3f_validation_status") != r3f.PASS_STATUS or plan.get("stop_reason") != "NONE" or plan.get("errors") != []:
        raise R4BuildError("r3f_not_passed")
    if plan.get("a2_payload_included") is not False or plan.get("a2_session_started") is not False:
        raise R4BuildError("r3f_a2_boundary_invalid")
    if plan.get("source_identity", {}).get("m2_consumer_sha256") != cp07d._digest(consumer):
        raise R4BuildError("r3f_m2_binding_invalid")
    lesson = plan.get("selected_lesson")
    composition = plan.get("unified_lesson_composition")
    if not isinstance(lesson, Mapping) or not isinstance(composition, Mapping):
        raise R4BuildError("r3f_selected_lesson_or_composition_missing")
    if lesson.get("skill") not in SKILLS or lesson.get("level") not in {"A1", "A1+"}:
        raise R4BuildError("r3f_selected_lesson_scope_invalid")
    if composition.get("selected_lesson_id") != lesson.get("lesson_id") or composition.get("selected_skill") != lesson.get("skill"):
        raise R4BuildError("r3f_composition_selection_drift")
    if composition.get("composition_mode") not in ALLOWED_MODES:
        raise R4BuildError("r3f_composition_mode_invalid")
    gate = composition.get("consumer_gate")
    if not isinstance(gate, Mapping):
        raise R4BuildError("r3f_consumer_gate_missing")
    expected_gate = {
        "m4_selected_lesson_unchanged": True,
        "m1_hard_prerequisite_graph_unchanged": True,
        "ket_asset_body_required": True,
        "ket99_reference_optional": True,
        "raz_context_optional": True,
        "m11b_checkpoint_optional": True,
        "missing_reference_blocks_delivery": False,
        "a2_payload_included": False,
    }
    for key, expected in expected_gate.items():
        if gate.get(key) is not expected:
            raise R4BuildError(f"r3f_consumer_gate_invalid:{key}")
    items = composition.get("composition_items")
    if not isinstance(items, list):
        raise R4BuildError("r3f_composition_item_list_required")
    ket_items = [row for row in items if isinstance(row, Mapping) and row.get("source_kind") == "KET_ASSET_BODY"]
    raz_items = [row for row in items if isinstance(row, Mapping) and row.get("source_kind") == "RAZ_ACTIVITY_BINDING"]
    if not ket_items:
        raise R4BuildError("r3f_ket_asset_item_required")
    return lesson, composition, ket_items, raz_items


def _verify_ket_mount(
    *,
    lesson: Mapping[str, Any],
    ket_items: Sequence[Mapping[str, Any]],
    lesson_index: Mapping[str, Mapping[str, Any]],
    asset_index: Mapping[str, Mapping[str, Any]],
) -> tuple[Mapping[str, Any], list[str], list[Mapping[str, Any]]]:
    lesson_id = str(lesson.get("lesson_id") or "")
    catalog = lesson_index.get(lesson_id)
    if catalog is None:
        raise R4BuildError("selected_lesson_not_in_m2")
    for key in ("lesson_node_id", "skill", "level", "requirement_node_ids"):
        expected = list(lesson.get(key, [])) if key == "requirement_node_ids" else lesson.get(key)
        actual = list(catalog.get(key, [])) if key == "requirement_node_ids" else catalog.get(key)
        if actual != expected:
            raise R4BuildError(f"m2_r3f_selected_lesson_drift:{key}")
    mounted_keys = sorted(str(value) for value in catalog.get("asset_keys", []))
    item_keys = sorted(str(row.get("source_lineage", {}).get("m2_asset_key") or "") for row in ket_items)
    if not mounted_keys or mounted_keys != item_keys or len(mounted_keys) != len(set(mounted_keys)):
        raise R4BuildError("r3f_m2_ket_asset_bundle_not_reconciled")
    assets: list[Mapping[str, Any]] = []
    for asset_key in mounted_keys:
        asset = asset_index.get(asset_key)
        if asset is None:
            raise R4BuildError(f"m2_ket_asset_missing:{asset_key}")
        if asset.get("lesson_id") != lesson_id or asset.get("skill") != lesson.get("skill") or asset.get("level") != lesson.get("level"):
            raise R4BuildError(f"m2_ket_asset_partition_drift:{asset_key}")
        assets.append(asset)
    return catalog, mounted_keys, assets


def _project_optional_context(
    *,
    cp05_approved: Mapping[str, Any],
    raz_items: Sequence[Mapping[str, Any]],
    lesson_id: str,
    skill: str,
    selected_level: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not raz_items:
        return [], []
    cp05_payload = cp07d._verify_cp05(cp05_approved)
    materials, bindings = cp07d._source_indexes(cp05_payload)
    projections: list[dict[str, Any]] = []
    assets: list[dict[str, Any]] = []
    for item in raz_items:
        if item.get("skill") != skill:
            raise R4BuildError("r3f_context_skill_drift")
        lineage = item.get("source_lineage")
        if not isinstance(lineage, Mapping):
            raise R4BuildError("r3f_context_source_lineage_missing")
        material_id = str(lineage.get("cp05_material_id") or "")
        binding_id = str(lineage.get("cp05_activity_binding_id") or "")
        material = materials.get(material_id)
        binding = bindings.get(binding_id)
        if material is None or binding is None:
            raise R4BuildError("r3f_cp05_source_identity_unresolved")
        if binding.get("material_id") != material_id or binding.get("grammar_unit_id") != item.get("grammar_unit_id"):
            raise R4BuildError("r3f_cp05_binding_drift")
        contract = cp07d._skill_contract(material, skill)
        payload = cp07d._projection_payload(item=item, material=material, binding=binding, contract=contract)
        projection = build_a1fs_v1_policy_bound_content_artifact.build_four_skill_projection(
            cp05_approved,
            skill=skill,
            projection_payload=payload,
            producer_id="A1FS_V1_CP07R4_REFERENCE_AWARE_PRIVATE_DELIVERY_CONSUMER",
        )
        projections.append(projection)
        projected = cp07d._assets_for_projection(projection, lesson_id)
        for asset in projected:
            asset["level"] = selected_level
        assets.extend(projected)
    if len({row["asset_key"] for row in assets}) != len(assets):
        raise R4BuildError("projected_asset_key_collision")
    return projections, assets


def build_private_delivery_consumer(
    m2_consumer: Mapping[str, Any],
    cp05_approved: Mapping[str, Any],
    r3f_plan: Mapping[str, Any],
) -> dict[str, Any]:
    lesson_index, asset_index = cp07d._verify_m2(m2_consumer)
    lesson, composition, ket_items, raz_items = _verify_r3f(r3f_plan, m2_consumer)
    _, mounted_ket_keys, mounted_ket_assets = _verify_ket_mount(
        lesson=lesson,
        ket_items=ket_items,
        lesson_index=lesson_index,
        asset_index=asset_index,
    )
    lesson_id = str(lesson["lesson_id"])
    skill = str(lesson["skill"])
    selected_level = str(lesson["level"])
    projections, projected_assets = _project_optional_context(
        cp05_approved=cp05_approved,
        raz_items=raz_items,
        lesson_id=lesson_id,
        skill=skill,
        selected_level=selected_level,
    )

    result = copy.deepcopy(dict(m2_consumer))
    if projected_assets:
        result["asset_records"].extend(projected_assets)
        selected_catalog = next(row for row in result["lesson_catalog"] if row["lesson_id"] == lesson_id)
        selected_catalog["asset_keys"] = list(selected_catalog["asset_keys"]) + [row["asset_key"] for row in projected_assets]
        selected_catalog["roles"] = list(dict.fromkeys(list(selected_catalog["roles"]) + [row["role"] for row in projected_assets]))

    all_selected_assets = list(mounted_ket_assets) + projected_assets
    response_capture_keys = sorted(
        str(row["asset_key"])
        for row in all_selected_assets
        if row.get("role") in CAPTURE_ROLES and row.get("payload", {}).get("response_capture_enabled") is True
    )
    listening_audio_keys = sorted(
        str(row["asset_key"])
        for row in all_selected_assets
        if skill == "LISTENING" and row.get("role") == "AUD" and row.get("payload", {}).get("media_registration_required") is True
    )
    speaking_recording_keys = sorted(
        str(row["asset_key"])
        for row in all_selected_assets
        if skill == "SPEAKING"
        and row.get("role") in SPEAKING_RECORDING_ROLES
        and row.get("payload", {}).get("recording_capture_required") is True
    )
    projected_keys = [str(row["asset_key"]) for row in projected_assets]
    role_counts = Counter(str(row.get("role") or "") for row in all_selected_assets)
    delivery_mode = "KET_ASSET_BODY_WITH_OPTIONAL_CONTEXT_PROJECTIONS" if projected_assets else "KET_ASSET_BODY_ONLY"

    result["cp07r4_task_id"] = TASK_ID
    result["cp07r4_schema_version"] = SCHEMA_VERSION
    result["cp07r4_validation_status"] = PASS_STATUS
    result["cp07d_task_id"] = cp07d.TASK_ID
    result["cp07d_schema_version"] = cp07d.SCHEMA_VERSION
    result["cp07d_validation_status"] = cp07d.PASS_STATUS
    result["cp07r4_source_identity"] = {
        "m2_consumer_sha256": cp07d._digest(m2_consumer),
        "r3f_plan_sha256": cp07d._digest(r3f_plan),
        "cp05_approved_artifact_sha256": str(cp05_approved.get("artifact_sha256") or "") if projected_assets else None,
    }
    result["counts"]["asset_record_count"] = len(result["asset_records"])
    result["counts"]["cp07r4_mounted_ket_asset_count"] = len(mounted_ket_keys)
    result["counts"]["cp07d_projected_asset_count"] = len(projected_assets)
    result["counts"]["cp07d_projection_artifact_count"] = len(projections)
    result["cp07d_projection_artifacts"] = projections
    result["cp07d_delivery_contract"] = {
        "selected_lesson_id": lesson_id,
        "selected_skill": skill,
        "selected_level": selected_level,
        "delivery_mode": delivery_mode,
        "composition_mode": str(composition["composition_mode"]),
        "mounted_ket_asset_keys": mounted_ket_keys,
        "projected_context_asset_keys": projected_keys,
        "projected_asset_keys": projected_keys,
        "mounted_role_counts": dict(sorted(role_counts.items())),
        "response_capture_asset_keys": response_capture_keys,
        "listening_audio_asset_keys": listening_audio_keys,
        "speaking_recording_asset_keys": speaking_recording_keys,
        "ket99_instructional_reference_count": len(composition.get("instructional_references", [])),
        "m3_session_compatible": True,
        "m5_private_renderer_compatible": True,
        "m6_feature_rubric_compatible": bool(response_capture_keys),
        "m10_private_media_registration_compatible": bool(listening_audio_keys or speaking_recording_keys),
        "missing_reference_blocks_delivery": False,
        "optional_context_projection_required": False,
        "real_attempt_completed": False,
        "real_media_registered": False,
        "a2_payload_included": False,
    }
    result["cp07r4_capability_gaps"] = {
        "response_capture_contract_missing": not bool(response_capture_keys),
        "listening_audio_registration_contract_missing": skill == "LISTENING" and not bool(listening_audio_keys),
        "speaking_recording_contract_missing": skill == "SPEAKING" and not bool(speaking_recording_keys),
        "optional_context_not_projected": not bool(projected_assets),
    }
    result["cp07d_claim_boundaries"] = {
        "real_learner_attempt_claimed": False,
        "real_listening_audio_claimed": False,
        "real_speaking_recording_claimed": False,
        "automatic_speaking_score_claimed": False,
        "mastery_or_retention_claimed": False,
        "public_delivery_claimed": False,
        "a2_a2plus_in_scope": False,
    }
    result["cp07d_errors"] = []
    result["cp07d_stop_reason"] = "NONE"
    result["cp07d_next_short_step"] = NEXT_SHORT_STEP
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--m2-consumer", type=Path, default=DEFAULT_M2)
    parser.add_argument("--cp05-approved", type=Path, default=DEFAULT_CP05_APPROVED)
    parser.add_argument("--r3f-plan", type=Path, default=DEFAULT_R3F)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    try:
        inputs = (_read(args.m2_consumer), _read(args.cp05_approved), _read(args.r3f_plan))
        artifact = build_private_delivery_consumer(*inputs)
        from ulga.validators import validate_a1fs_v1_cp07r4_reference_aware_private_delivery_consumer as validator
        report = validator.validate_artifact(
            artifact,
            m2_consumer=inputs[0],
            cp05_approved=inputs[1],
            r3f_plan=inputs[2],
        )
        cp07d._write_atomic(args.output, artifact, private=True)
        cp07d._write_atomic(args.report, report)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0 if report["validation_status"] == PASS_STATUS else 1
    except (
        R4BuildError,
        cp07d.CP07DBuildError,
        build_a1fs_v1_policy_bound_content_artifact.ContentPolicyBuildError,
        OSError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
