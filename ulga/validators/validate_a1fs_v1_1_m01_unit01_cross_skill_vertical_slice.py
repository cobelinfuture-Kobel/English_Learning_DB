#!/usr/bin/env python3
"""Validate the A1FS V1.1 Unit 01 cross-skill vertical slice."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import (
    build_a1fs_v1_1_m01_unit01_cross_skill_vertical_slice as builder,
)

VALIDATOR_ID = "A1FS_V1_1_M01_UNIT01_CROSS_SKILL_VALIDATOR"
PASS_STATUS = "PASS"
EXPECTED_SENTENCE_COUNT = 6


class Unit01ValidationError(ValueError):
    """Fail-closed validation error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return policy_artifact.digest(value)


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise Unit01ValidationError(code)


def _receipt(payload: Mapping[str, Any]) -> dict[str, Any]:
    core = {
        "validator_id": VALIDATOR_ID,
        "status": PASS_STATUS,
        "validated_payload_sha256": digest(payload),
    }
    return {**core, "receipt_sha256": digest(core)}


def validate_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    _require(isinstance(payload, Mapping), "payload_object_required")
    _require(payload.get("unit_id") == builder.UNIT_ID, "unit_identity_invalid")
    _require(payload.get("level_scope") == ["A1"], "level_scope_invalid")
    situation = payload.get("shared_situation")
    _require(isinstance(situation, Mapping), "shared_situation_required")
    passage = str(situation.get("passage") or "")
    _require(passage == builder.PASSAGE, "approved_passage_identity_invalid")
    _require(
        int(situation.get("sentence_count") or 0) == EXPECTED_SENTENCE_COUNT,
        "passage_sentence_count_invalid",
    )
    _require(
        all(
            token in passage
            for token in (
                "a bag",
                "a book",
                "an apple",
                "A cat",
                "the book",
                "the apple",
            )
        ),
        "article_functions_not_contextualized",
    )
    _require(
        len(payload.get("reading", {}).get("specs", [])) == 4,
        "reading_spec_count_invalid",
    )
    _require(
        payload.get("reading", {}).get("real_passage_required") is True,
        "real_reading_not_required",
    )
    _require(
        len(payload.get("writing", {}).get("progression", [])) == 4,
        "writing_progression_invalid",
    )
    speaking = payload.get("speaking", {})
    _require(len(speaking.get("specs", [])) == 3, "speaking_spec_count_invalid")
    _require(speaking.get("practice_only") is True, "speaking_practice_boundary_invalid")
    _require(speaking.get("recording_enabled") is False, "speaking_recording_forbidden")
    reconcile = payload.get("cross_skill_reconciliation", {})
    for key in (
        "shared_grammar_target",
        "shared_vocabulary",
        "shared_situation",
        "reading_to_writing_transfer",
        "reading_to_speaking_transfer",
    ):
        _require(reconcile.get(key) is True, f"cross_skill_contract_missing:{key}")
    _require(
        reconcile.get("parallel_curriculum_created") is False,
        "parallel_curriculum_forbidden",
    )
    source_policy = payload.get("source_policy", {})
    _require(source_policy.get("content_origin") == "PROJECT_AUTHORED", "content_origin_invalid")
    _require(source_policy.get("raw_ket_text_copied") is False, "raw_ket_text_copy_forbidden")
    _require(source_policy.get("raw_raz_text_copied") is False, "raw_raz_text_copy_forbidden")
    boundaries = payload.get("boundaries", {})
    for key in (
        "unit02_or_later_modified",
        "lesson_identity_changed",
        "asset_identity_changed",
        "scoring_authority_changed",
        "learner_state_authority_changed",
        "listening_enabled",
        "speaking_capture_enabled",
        "a2_unlocked",
    ):
        _require(boundaries.get(key) is False, f"boundary_invalid:{key}")
    return _receipt(payload)


def validate_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    _require(
        candidate.get("artifact_role") == policy_artifact.CANDIDATE_ROLE,
        "candidate_role_invalid",
    )
    _require(candidate.get("learner_facing") is False, "candidate_learner_facing_forbidden")
    policy_artifact.verify_artifact_digest(candidate)
    payload = candidate.get("payload")
    _require(isinstance(payload, Mapping), "candidate_payload_missing")
    return validate_payload(payload)


def _asset_identity(bundle: Mapping[str, Any]) -> list[tuple[str, str]]:
    assets = bundle.get("assets")
    _require(isinstance(assets, list), "bundle_assets_invalid")
    return [
        (str(row.get("asset_key") or ""), str(row.get("role") or ""))
        for row in assets
        if isinstance(row, Mapping)
    ]


def validate_overlay(
    *,
    source_bundles: Mapping[str, Mapping[str, Any]],
    overlaid_bundles: Mapping[str, Mapping[str, Any]],
    approved: Mapping[str, Any],
) -> dict[str, Any]:
    policy_artifact.verify_artifact_digest(approved)
    _require(
        approved.get("artifact_role") == policy_artifact.APPROVED_ROLE,
        "approved_role_invalid",
    )
    _require(set(source_bundles) == set(overlaid_bundles), "lesson_identity_set_changed")
    changed: list[str] = []
    for lesson_id in sorted(source_bundles):
        source = source_bundles[lesson_id]
        target = overlaid_bundles[lesson_id]
        _require(
            _asset_identity(source) == _asset_identity(target),
            f"asset_identity_changed:{lesson_id}",
        )
        if canonical(source) != canonical(target):
            changed.append(lesson_id)
    _require(set(changed) == set(builder.LESSON_IDS.values()), "non_unit01_bundle_changed")
    for skill, lesson_id in builder.LESSON_IDS.items():
        bundle = overlaid_bundles[lesson_id]
        assets = bundle.get("assets", [])
        _require(
            len(assets) == builder.EXPECTED_LANE_COUNTS[skill],
            f"{skill.lower()}_asset_count_invalid",
        )
        for asset in assets:
            learner = asset.get("learner_payload", {})
            _require(isinstance(learner, Mapping), f"learner_payload_missing:{lesson_id}")
            stimulus = learner.get("stimulus")
            _require(isinstance(stimulus, Mapping), f"stimulus_missing:{lesson_id}")
            _require(
                stimulus.get("body") == builder.PASSAGE,
                f"shared_passage_drift:{lesson_id}",
            )
            identity = learner.get("content_identity")
            _require(isinstance(identity, Mapping), f"content_identity_missing:{lesson_id}")
            _require(
                identity.get("approved_content_sha256") == approved["artifact_sha256"],
                f"approved_binding_invalid:{lesson_id}",
            )
    speaking_assets = overlaid_bundles[builder.LESSON_IDS["SPEAKING"]]["assets"]
    _require(
        all(
            asset["learner_payload"].get("response_capture_enabled") is False
            for asset in speaking_assets
        ),
        "speaking_capture_enabled",
    )
    return {
        "validation_status": builder.PASS_STATUS,
        "changed_lesson_ids": changed,
        "modified_lesson_count": len(changed),
        "other_lesson_count_preserved": len(source_bundles) - len(changed),
        "unit01_activity_count": sum(
            len(overlaid_bundles[lesson_id]["assets"])
            for lesson_id in builder.LESSON_IDS.values()
        ),
    }


def validate_outputs(
    *,
    receipt: Mapping[str, Any],
    safe_report: Mapping[str, Any],
    output_root: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        _require(receipt.get("task_id") == builder.TASK_ID, "receipt_task_id_invalid")
        _require(
            receipt.get("validation_status") == builder.PASS_STATUS,
            "receipt_status_invalid",
        )
        _require(
            receipt.get("product_version") == builder.PRODUCT_VERSION,
            "product_version_invalid",
        )
        core = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
        _require(receipt.get("artifact_sha256") == digest(core), "receipt_digest_invalid")
        _require(
            safe_report.get("validation_status") == builder.PASS_STATUS,
            "safe_status_invalid",
        )
        summary = receipt.get("milestone_summary", {})
        expected = {
            "modified_lesson_count": 3,
            "reading_activity_count": 4,
            "writing_activity_count": 4,
            "speaking_practice_count": 3,
            "real_reading_passage_present": True,
            "shared_cross_skill_context_present": True,
            "existing_asset_identities_preserved": True,
            "existing_scoring_contracts_preserved": True,
            "other_unit_bundles_preserved": True,
        }
        for key, value in expected.items():
            _require(summary.get(key) == value, f"summary_invalid:{key}")
        boundaries = receipt.get("boundaries", {})
        for key in (
            "parallel_curriculum_created",
            "learner_state_migrated",
            "learner_state_authority_changed",
            "scoring_authority_changed",
            "dashboard_authority_changed",
            "audio_enabled",
            "speaking_capture_enabled",
            "a2_unlocked",
        ):
            _require(boundaries.get(key) is False, f"output_boundary_invalid:{key}")
        outputs = receipt.get("runtime_outputs", {})
        root = Path(str(outputs.get("root") or "")).resolve()
        _require(
            root == (Path(output_root).resolve() / "unit01_cross_skill_vertical_slice"),
            "output_root_identity_invalid",
        )
        for key in (
            "bundles_path",
            "secure_static_root",
            "candidate_path",
            "approved_path",
            "projections_path",
        ):
            _require(Path(str(outputs.get(key) or "")).exists(), f"output_missing:{key}")
    except (Unit01ValidationError, KeyError, TypeError, ValueError, OSError) as exc:
        errors.append(str(exc))
    return {
        "task_id": builder.TASK_ID,
        "validation_status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
    }
