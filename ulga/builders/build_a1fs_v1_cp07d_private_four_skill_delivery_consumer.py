#!/usr/bin/env python3
"""Project CP05-approved RAZ content into a private M2-compatible runtime consumer.

The output preserves the selected KET lesson and all original KET assets.  It
adds only policy-bound four-skill projections selected by CP07C.  Existing
M3/M5/M6/M10 components remain the runtime authority for session state,
learner delivery, response/scoring, and private media registration.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_cp05_private_candidate_materialization_and_admission as cp05  # noqa: E402
from ulga.builders import build_a1fs_v1_cp07c_unified_m4_lesson_composition as cp07c  # noqa: E402
from ulga.builders import build_a1fs_v1_m2_four_skill_asset_body_consumer as m2  # noqa: E402
from ulga.builders import build_a1fs_v1_m4_lesson_planner_selection_a2_lock as m4  # noqa: E402
from ulga.builders import build_a1fs_v1_policy_bound_content_artifact  # noqa: E402

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"

TASK_ID = "A1FS-V1-CP07D_FourSkillDeliveryResponseAndMediaCanaryIntegration"
PROGRAM_ID = cp07c.PROGRAM_ID
PRODUCER_ID = "A1FS_V1_CP07D_PRIVATE_FOUR_SKILL_DELIVERY_CONSUMER"
SCHEMA_VERSION = "a1fs.v1.cp07d.private_four_skill_delivery_consumer.v1"
PASS_STATUS = "PASS_CP07D_PRIVATE_FOUR_SKILL_DELIVERY_CONSUMER_READY"
NEXT_SHORT_STEP = "A1FS-V1-CP07E_DiagnosisRemediationReassessmentAndRetentionClosure"

DEFAULT_M2 = REPO_ROOT / ".local/a1fs_v1/m2/four_skill_asset_body_consumer.private.json"
DEFAULT_CP05_APPROVED = cp05.DEFAULT_APPROVED_OUTPUT
DEFAULT_CP07C = cp07c.DEFAULT_OUTPUT
DEFAULT_OUTPUT = REPO_ROOT / ".local/a1fs_v1/cp07d/private_four_skill_delivery_consumer.private.json"
DEFAULT_REPORT = REPO_ROOT / ".local/a1fs_v1/cp07d/private_four_skill_delivery_consumer.validation.json"

SKILLS = ("LISTENING", "SPEAKING", "READING", "WRITING")
CAPTURE_ROLES = {"CHK", "PRD", "XFR", "EVD"}
SPEAKING_RECORDING_ROLES = {"PRD", "XFR", "EVD"}
CONTEXT_ROLE_TO_ASSET_ROLE = {
    "READING": {"FOCUS": "PRD", "CONTRAST": "CHK", "RECYCLE": "PRD", "TRANSFER": "XFR"},
    "WRITING": {"FOCUS": "PRD", "CONTRAST": "CHK", "RECYCLE": "PRD", "TRANSFER": "EVD"},
    "SPEAKING": {"FOCUS": "PRD", "CONTRAST": "PRD", "RECYCLE": "PRD", "TRANSFER": "EVD"},
}


class CP07DBuildError(ValueError):
    """Fail-closed projection or runtime-consumer error."""


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CP07DBuildError(f"json_object_required:{path}")
    return value


def _write_atomic(path: Path, value: Mapping[str, Any], *, private: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
        if private:
            os.chmod(path, 0o600)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def _stable_asset_key(runtime_activity_id: str, suffix: str) -> str:
    token = hashlib.sha256(f"{runtime_activity_id}\0{suffix}".encode("utf-8")).hexdigest()[:24]
    return f"CP07D:{token}:{suffix}"


def _verify_m2(consumer: Mapping[str, Any]) -> tuple[dict[str, Mapping[str, Any]], dict[str, Mapping[str, Any]]]:
    if consumer.get("task_id") != m2.TASK_ID or consumer.get("schema_version") != m2.SCHEMA_VERSION:
        raise CP07DBuildError("m2_contract_invalid")
    if consumer.get("validation_status") != m2.STATUS or consumer.get("errors") != []:
        raise CP07DBuildError("m2_not_passed")
    if consumer.get("access_contract", {}).get("a2_payload_query_allowed") is not False:
        raise CP07DBuildError("m2_a2_lock_invalid")
    lessons = consumer.get("lesson_catalog")
    assets = consumer.get("asset_records")
    if not isinstance(lessons, list) or not isinstance(assets, list):
        raise CP07DBuildError("m2_catalog_invalid")
    lesson_index = {str(row.get("lesson_id") or ""): row for row in lessons if isinstance(row, Mapping)}
    asset_index = {str(row.get("asset_key") or ""): row for row in assets if isinstance(row, Mapping)}
    if len(lesson_index) != len(lessons) or len(asset_index) != len(assets):
        raise CP07DBuildError("m2_identity_missing_or_duplicate")
    return lesson_index, asset_index


def _verify_cp05(approved: Mapping[str, Any]) -> Mapping[str, Any]:
    try:
        build_a1fs_v1_policy_bound_content_artifact.verify_artifact_digest(approved)
    except build_a1fs_v1_policy_bound_content_artifact.ContentPolicyBuildError as exc:
        raise CP07DBuildError(f"cp05_digest_invalid:{exc}") from exc
    if approved.get("artifact_role") != build_a1fs_v1_policy_bound_content_artifact.APPROVED_ROLE:
        raise CP07DBuildError("cp05_artifact_role_invalid")
    if approved.get("admission", {}).get("status") != "APPROVED" or approved.get("learner_facing") is not False:
        raise CP07DBuildError("cp05_admission_invalid")
    payload = approved.get("payload")
    if not isinstance(payload, Mapping) or payload.get("task_id") != cp05.TASK_ID:
        raise CP07DBuildError("cp05_payload_invalid")
    if payload.get("scope") != "A1_A1_PLUS_ONLY" or payload.get("stop_reason") != "NONE":
        raise CP07DBuildError("cp05_scope_or_status_invalid")
    return payload


def _verify_cp07c(plan: Mapping[str, Any], consumer: Mapping[str, Any]) -> tuple[Mapping[str, Any], list[Mapping[str, Any]]]:
    if plan.get("task_id") != m4.TASK_ID or plan.get("validation_status") != m4.STATUS:
        raise CP07DBuildError("cp07c_m4_compatibility_invalid")
    if plan.get("cp07c_task_id") != cp07c.TASK_ID or plan.get("cp07c_validation_status") != cp07c.PASS_STATUS:
        raise CP07DBuildError("cp07c_contract_invalid")
    if plan.get("a2_payload_included") is not False or plan.get("a2_session_started") is not False:
        raise CP07DBuildError("cp07c_a2_boundary_invalid")
    if plan.get("source_identity", {}).get("m2_consumer_sha256") != _digest(consumer):
        raise CP07DBuildError("cp07c_m2_binding_invalid")
    lesson = plan.get("selected_lesson")
    composition = plan.get("unified_lesson_composition")
    if not isinstance(lesson, Mapping) or not isinstance(composition, Mapping):
        raise CP07DBuildError("cp07c_selected_lesson_or_composition_missing")
    if lesson.get("level") not in {"A1", "A1+"} or lesson.get("skill") not in SKILLS:
        raise CP07DBuildError("cp07c_selected_lesson_scope_invalid")
    if composition.get("selected_lesson_id") != lesson.get("lesson_id") or composition.get("selected_skill") != lesson.get("skill"):
        raise CP07DBuildError("cp07c_composition_selection_drift")
    items = composition.get("composition_items")
    if not isinstance(items, list):
        raise CP07DBuildError("cp07c_composition_item_list_required")
    raz_items = [row for row in items if isinstance(row, Mapping) and row.get("source_kind") == "RAZ_ACTIVITY_BINDING"]
    if not raz_items:
        raise CP07DBuildError("cp07c_raz_projection_required")
    return lesson, raz_items


def _source_indexes(payload: Mapping[str, Any]) -> tuple[dict[str, Mapping[str, Any]], dict[str, Mapping[str, Any]]]:
    materials: dict[str, Mapping[str, Any]] = {}
    for row in payload.get("materialized_raz_sources", []):
        if not isinstance(row, Mapping):
            raise CP07DBuildError("cp05_material_row_invalid")
        material_id = str(row.get("material_id") or "")
        if not material_id or material_id in materials:
            raise CP07DBuildError("cp05_material_identity_invalid")
        if row.get("materialization_status") != "MATERIALIZED_PRIVATE_SOURCE_BOUND":
            raise CP07DBuildError(f"cp05_material_not_materialized:{material_id}")
        source_content = row.get("source_content")
        if not isinstance(source_content, Mapping) or not isinstance(source_content.get("text"), str) or not source_content["text"].strip():
            raise CP07DBuildError(f"cp05_material_source_text_missing:{material_id}")
        materials[material_id] = row
    bindings: dict[str, Mapping[str, Any]] = {}
    for row in payload.get("raz_unit_activity_bindings", []):
        if not isinstance(row, Mapping):
            raise CP07DBuildError("cp05_binding_row_invalid")
        binding_id = str(row.get("activity_binding_id") or "")
        if not binding_id or binding_id in bindings:
            raise CP07DBuildError("cp05_binding_identity_invalid")
        bindings[binding_id] = row
    return materials, bindings


def _skill_contract(material: Mapping[str, Any], skill: str) -> Mapping[str, Any]:
    rows = material.get("skill_contracts")
    if not isinstance(rows, list):
        raise CP07DBuildError("cp05_skill_contract_list_required")
    matches = [row for row in rows if isinstance(row, Mapping) and row.get("skill") == skill]
    if len(matches) != 1:
        raise CP07DBuildError(f"cp05_exact_skill_contract_required:{material.get('material_id')}:{skill}")
    contract = matches[0]
    if not isinstance(contract.get("prompt"), str) or not isinstance(contract.get("scoring_contract"), Mapping):
        raise CP07DBuildError("cp05_skill_contract_incomplete")
    return contract


def _projection_payload(
    *, item: Mapping[str, Any], material: Mapping[str, Any], binding: Mapping[str, Any], contract: Mapping[str, Any]
) -> dict[str, Any]:
    skill = str(item["skill"])
    return {
        "skill": skill,
        "prompt": str(contract["prompt"]),
        "response_mode": str(contract["response_mode"]),
        "support_level": str(contract["support_level"]),
        "initiative_level": str(contract["initiative_level"]),
        "scoring_contract": copy.deepcopy(dict(contract["scoring_contract"])),
        "evidence_level": str(contract["evidence_level"]),
        "source_bindings": {
            "cp07c_composition_item_id": str(item["composition_item_id"]),
            "cp05_activity_binding_id": str(binding["activity_binding_id"]),
            "cp05_material_id": str(material["material_id"]),
            "cp05_source_unit_ref": str(material["source_unit_ref"]),
            "cp05_source_content_sha256": str(material["source_content_sha256"]),
            "learning_unit_id": str(binding["learning_unit_id"]),
            "grammar_unit_id": str(binding["grammar_unit_id"]),
        },
        "content_identity": {
            "material_id": str(material["material_id"]),
            "activity_binding_id": str(binding["activity_binding_id"]),
            "runtime_activity_id": str(item["composition_item_id"]),
            "instructional_role": str(item["instructional_role"]),
        },
        "source_text": str(material["source_content"]["text"]),
        "activity_kind": str(contract["activity_kind"]),
        "runtime_dependency_status": str(contract["runtime_dependency_status"]),
        "instructional_role": str(item["instructional_role"]),
        "learning_unit_id": str(binding["learning_unit_id"]),
        "grammar_unit_id": str(binding["grammar_unit_id"]),
    }


def _rubric(contract: Mapping[str, Any]) -> dict[str, Any]:
    criteria = contract.get("scoring_contract", {}).get("criteria", [])
    if not isinstance(criteria, list) or not criteria:
        raise CP07DBuildError("projection_rubric_criteria_required")
    return {str(value): {"required": True} for value in criteria}


def _base_asset(
    *, projection: Mapping[str, Any], lesson_id: str, skill: str, role: str, suffix: str, capture: bool
) -> dict[str, Any]:
    payload = projection["payload"]
    asset_key = _stable_asset_key(str(payload["content_identity"]["runtime_activity_id"]), suffix)
    learner_payload = {
        "source_text": str(payload["source_text"]),
        "prompt": str(payload["prompt"]),
        "activity_kind": str(payload["activity_kind"]),
        "instructional_role": str(payload["instructional_role"]),
        "learning_unit_id": str(payload["learning_unit_id"]),
        "grammar_unit_id": str(payload["grammar_unit_id"]),
        "runtime_dependency_status": str(payload["runtime_dependency_status"]),
        "response_capture_enabled": capture,
        "private_scoring_contract": {
            "scoring_mode": "FEATURE_RUBRIC",
            "rubric": _rubric(payload),
        },
        "content_governance_ref": {
            "projection_artifact_sha256": str(projection["artifact_sha256"]),
            "approved_canonical_artifact_sha256": str(projection["source_bindings"]["approved_canonical_artifact_sha256"]),
        },
    }
    return {
        "asset_id": asset_key,
        "asset_key": asset_key,
        "lesson_id": lesson_id,
        "skill": skill,
        "level": projection["level_scope"][0] if len(projection["level_scope"]) == 1 else "A1+",
        "role": role,
        "payload": learner_payload,
        "content_digest": str(projection["artifact_sha256"]),
        "release_scope": "PRIVATE_INTERNAL_CP07D_CANARY",
    }


def _assets_for_projection(projection: Mapping[str, Any], lesson_id: str) -> list[dict[str, Any]]:
    payload = projection["payload"]
    skill = str(payload["skill"])
    role = str(payload["instructional_role"])
    if skill == "LISTENING":
        audio = _base_asset(projection=projection, lesson_id=lesson_id, skill=skill, role="AUD", suffix="AUD", capture=False)
        audio["payload"]["learner_instruction"] = "Play the registered private audio before answering the evidence prompt."
        audio["payload"]["media_registration_required"] = True
        evidence = _base_asset(projection=projection, lesson_id=lesson_id, skill=skill, role="EVD", suffix="EVD", capture=True)
        evidence["payload"].pop("source_text", None)
        return [audio, evidence]
    if skill == "SPEAKING":
        asset_role = CONTEXT_ROLE_TO_ASSET_ROLE[skill][role]
        asset = _base_asset(projection=projection, lesson_id=lesson_id, skill=skill, role=asset_role, suffix=asset_role, capture=True)
        asset["payload"]["recording_capture_required"] = True
        asset["payload"]["recording_consent_required"] = True
        return [asset]
    asset_role = CONTEXT_ROLE_TO_ASSET_ROLE[skill][role]
    return [_base_asset(projection=projection, lesson_id=lesson_id, skill=skill, role=asset_role, suffix=asset_role, capture=True)]


def build_private_delivery_consumer(
    m2_consumer: Mapping[str, Any],
    cp05_approved: Mapping[str, Any],
    cp07c_plan: Mapping[str, Any],
) -> dict[str, Any]:
    lesson_index, _ = _verify_m2(m2_consumer)
    cp05_payload = _verify_cp05(cp05_approved)
    lesson, selected_items = _verify_cp07c(cp07c_plan, m2_consumer)
    lesson_id = str(lesson["lesson_id"])
    skill = str(lesson["skill"])
    if lesson_id not in lesson_index:
        raise CP07DBuildError("selected_lesson_not_in_m2")
    materials, bindings = _source_indexes(cp05_payload)

    projection_artifacts: list[dict[str, Any]] = []
    projected_assets: list[dict[str, Any]] = []
    for item in selected_items:
        if item.get("skill") != skill:
            raise CP07DBuildError("cp07c_composition_skill_drift")
        lineage = item.get("source_lineage")
        if not isinstance(lineage, Mapping):
            raise CP07DBuildError("cp07c_source_lineage_missing")
        material_id = str(lineage.get("cp05_material_id") or "")
        binding_id = str(lineage.get("cp05_activity_binding_id") or "")
        material = materials.get(material_id)
        binding = bindings.get(binding_id)
        if material is None or binding is None:
            raise CP07DBuildError("cp07c_cp05_source_identity_unresolved")
        if binding.get("material_id") != material_id or binding.get("grammar_unit_id") != item.get("grammar_unit_id"):
            raise CP07DBuildError("cp07c_cp05_binding_drift")
        contract = _skill_contract(material, skill)
        payload = _projection_payload(item=item, material=material, binding=binding, contract=contract)
        projection = build_a1fs_v1_policy_bound_content_artifact.build_four_skill_projection(
            cp05_approved,
            skill=skill,
            projection_payload=payload,
            producer_id=PRODUCER_ID,
        )
        projection_artifacts.append(projection)
        projected_assets.extend(_assets_for_projection(projection, lesson_id))

    if not projected_assets:
        raise CP07DBuildError("projected_asset_required")
    if len({row["asset_key"] for row in projected_assets}) != len(projected_assets):
        raise CP07DBuildError("projected_asset_key_collision")

    result = copy.deepcopy(dict(m2_consumer))
    result["cp07d_task_id"] = TASK_ID
    result["cp07d_schema_version"] = SCHEMA_VERSION
    result["cp07d_validation_status"] = PASS_STATUS
    result["cp07d_source_identity"] = {
        "m2_consumer_sha256": _digest(m2_consumer),
        "cp05_approved_artifact_sha256": str(cp05_approved["artifact_sha256"]),
        "cp07c_plan_sha256": _digest(cp07c_plan),
    }
    result["asset_records"].extend(projected_assets)
    catalog = next(row for row in result["lesson_catalog"] if row["lesson_id"] == lesson_id)
    catalog["asset_keys"] = list(catalog["asset_keys"]) + [row["asset_key"] for row in projected_assets]
    catalog["roles"] = list(dict.fromkeys(list(catalog["roles"]) + [row["role"] for row in projected_assets]))
    result["counts"]["asset_record_count"] = len(result["asset_records"])
    result["counts"]["cp07d_projected_asset_count"] = len(projected_assets)
    result["counts"]["cp07d_projection_artifact_count"] = len(projection_artifacts)
    result["cp07d_projection_artifacts"] = projection_artifacts
    role_counts = Counter(row["role"] for row in projected_assets)
    result["cp07d_delivery_contract"] = {
        "selected_lesson_id": lesson_id,
        "selected_skill": skill,
        "selected_level": str(lesson["level"]),
        "projected_asset_keys": [row["asset_key"] for row in projected_assets],
        "projected_role_counts": dict(sorted(role_counts.items())),
        "response_capture_asset_keys": [row["asset_key"] for row in projected_assets if row["role"] in CAPTURE_ROLES],
        "listening_audio_asset_keys": [row["asset_key"] for row in projected_assets if row["role"] == "AUD"],
        "speaking_recording_asset_keys": [row["asset_key"] for row in projected_assets if skill == "SPEAKING" and row["role"] in SPEAKING_RECORDING_ROLES],
        "m3_session_compatible": True,
        "m5_private_renderer_compatible": True,
        "m6_feature_rubric_compatible": True,
        "m10_private_media_registration_compatible": skill in {"LISTENING", "SPEAKING"},
        "real_attempt_completed": False,
        "real_media_registered": False,
        "a2_payload_included": False,
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
    parser.add_argument("--cp07c-plan", type=Path, default=DEFAULT_CP07C)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    try:
        inputs = (_read(args.m2_consumer), _read(args.cp05_approved), _read(args.cp07c_plan))
        consumer = build_private_delivery_consumer(*inputs)
        from ulga.validators import validate_a1fs_v1_cp07d_private_four_skill_delivery_consumer as validator
        report = validator.validate_artifact(
            consumer,
            m2_consumer=inputs[0], cp05_approved=inputs[1], cp07c_plan=inputs[2],
        )
        _write_atomic(args.output, consumer, private=True)
        _write_atomic(args.report, report)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0 if report["validation_status"] == PASS_STATUS else 1
    except (
        CP07DBuildError,
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
