#!/usr/bin/env python3
"""Validate the RAZQ01D Unit01 reusable content handoff."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import (
    build_a1fs_v1_razq01d_unit01_micro_scene_passage_dialogue_admission_three_skill_projection_handoff as builder,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Validates the RAZQ01D policy-bound content handoff; it creates no learner-facing content."
)
PROGRAM_ID = builder.PROGRAM_ID
TASK_ID = builder.TASK_ID
PASS_STATUS = builder.PASS_STATUS
SCHEMA_VERSION = builder.SCHEMA_VERSION
BLOCKED_RAW_KEYS = {
    "text_excerpt",
    "original_excerpt",
    "raw_text",
    "source_text",
    "raw_raz_text",
}


class ContentHandoffValidationError(ValueError):
    """Fail-closed Unit01 content handoff validation error."""


def _walk_no_raw_source(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key) in BLOCKED_RAW_KEYS:
                raise ContentHandoffValidationError(
                    f"RAW_SOURCE_KEY_FORBIDDEN:{path}.{key}"
                )
            _walk_no_raw_source(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk_no_raw_source(child, f"{path}[{index}]")


def _error(condition: bool, code: str, errors: list[str]) -> None:
    if condition:
        errors.append(code)


def validate(report: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    _error(report.get("schema_version") != SCHEMA_VERSION, "schema_version_invalid", errors)
    _error(report.get("program_id") != PROGRAM_ID, "program_id_invalid", errors)
    _error(report.get("task_id") != TASK_ID, "task_id_invalid", errors)
    _error(report.get("status") != PASS_STATUS, "status_invalid", errors)
    scope = report.get("scope") or {}
    _error(scope.get("allowed_units") != [builder.UNIT_ID], "unit01_scope_invalid", errors)
    _error(
        scope.get("unit02_to_unit24_modified") is not False,
        "later_unit_modified",
        errors,
    )
    _error(
        scope.get("raw_raz_text_published") is not False,
        "raw_raz_publication_invalid",
        errors,
    )
    _error(
        scope.get("second_question_bank_created") is not False,
        "second_bank_created",
        errors,
    )
    _error(scope.get("a2_status") != "LOCKED", "a2_not_locked", errors)

    try:
        _walk_no_raw_source(report)
    except ContentHandoffValidationError as exc:
        errors.append(str(exc))

    assets = report.get("content_assets")
    if not isinstance(assets, list) or not assets:
        errors.append("content_assets_required")
        assets = []
    asset_ids: list[str] = []
    source_ids: list[str] = []
    scene_signatures: list[str] = []
    for asset in assets:
        if not isinstance(asset, Mapping):
            errors.append("content_asset_object_required")
            continue
        asset_id = str(asset.get("content_asset_id") or "")
        asset_ids.append(asset_id)
        _error(
            not asset_id.startswith("U01-"),
            f"unit01_asset_id_invalid:{asset_id}",
            errors,
        )
        _error(
            asset.get("content_kind") not in builder.CONTENT_KINDS,
            f"content_kind_invalid:{asset_id}",
            errors,
        )
        _error(
            asset.get("unit_id") != builder.UNIT_ID,
            f"unit_id_invalid:{asset_id}",
            errors,
        )
        lineage = asset.get("source_lineage") or {}
        source_id = str(lineage.get("source_record_id") or "")
        source_ids.append(source_id)
        _error(
            len(str(lineage.get("original_excerpt_sha256") or "")) != 64,
            f"source_hash_invalid:{asset_id}",
            errors,
        )
        _error(
            lineage.get("original_excerpt_private") is not True,
            f"source_private_flag_invalid:{asset_id}",
            errors,
        )
        _error(
            lineage.get("original_excerpt_published") is not False,
            f"source_publication_flag_invalid:{asset_id}",
            errors,
        )
        admission = asset.get("admission") or {}
        _error(
            admission.get("review_status") != "APPROVED",
            f"review_not_approved:{asset_id}",
            errors,
        )
        _error(
            admission.get("canonical_admission") is not True,
            f"canonical_admission_missing:{asset_id}",
            errors,
        )
        scene = asset.get("scene_profile") or {}
        signature = str(scene.get("distinct_scene_signature") or "")
        scene_signatures.append(signature)
        _error(
            len(signature) != 64,
            f"scene_signature_invalid:{asset_id}",
            errors,
        )
        _error(
            scene.get("template_only") is not False,
            f"template_only_asset:{asset_id}",
            errors,
        )

        dialogue = asset.get("dialogue_profile") or {}
        content = asset.get("content") or {}
        if asset.get("content_kind") == "SHORT_DIALOGUE":
            turns = content.get("turns") or []
            speakers = {
                str(row.get("speaker_id") or "")
                for row in turns
                if isinstance(row, Mapping)
            }
            _error(
                dialogue.get("is_real_dialogue") is not True,
                f"dialogue_flag_invalid:{asset_id}",
                errors,
            )
            _error(
                len(turns) < 2,
                f"dialogue_turn_count_invalid:{asset_id}",
                errors,
            )
            _error(
                len(speakers) < 2,
                f"dialogue_speaker_count_invalid:{asset_id}",
                errors,
            )
            _error(
                dialogue.get("role_play_supported") is not True,
                f"dialogue_role_play_missing:{asset_id}",
                errors,
            )
        else:
            _error(
                dialogue.get("is_real_dialogue") is not False,
                f"narrative_mislabeled_dialogue:{asset_id}",
                errors,
            )

        projections = asset.get("skill_projections") or {}
        for skill in builder.SKILLS:
            rows = projections.get(skill.lower())
            _error(
                not isinstance(rows, list) or not rows,
                f"{skill.lower()}_projection_missing:{asset_id}",
                errors,
            )
            for row in rows or []:
                _error(
                    row.get("content_asset_id") != asset_id,
                    f"projection_asset_identity_drift:{asset_id}:{skill}",
                    errors,
                )
                _error(
                    row.get("target_bank_id") != builder.TARGET_BANK_ID,
                    f"target_bank_drift:{asset_id}:{skill}",
                    errors,
                )
                _error(
                    row.get("projection_mode")
                    != "REFERENCE_EXISTING_FAMILIES_NO_SECOND_BANK",
                    f"projection_mode_invalid:{asset_id}:{skill}",
                    errors,
                )
        _error(
            projections.get("listening") != [],
            f"listening_projection_not_deferred:{asset_id}",
            errors,
        )
        _error(
            projections.get("three_skill_projection_complete") is not True,
            f"three_skill_incomplete:{asset_id}",
            errors,
        )
        reuse = asset.get("later_unit_reuse") or {}
        _error(
            reuse.get("copy_on_reuse") is not False,
            f"reuse_copy_forbidden:{asset_id}",
            errors,
        )
        _error(
            reuse.get("reuse_identity_mode")
            != "REFERENCE_STABLE_CONTENT_ASSET_ID",
            f"reuse_identity_invalid:{asset_id}",
            errors,
        )

        expected_sha = builder.digest(
            {key: value for key, value in asset.items() if key != "content_asset_sha256"}
        )
        _error(
            asset.get("content_asset_sha256") != expected_sha,
            f"content_asset_sha_invalid:{asset_id}",
            errors,
        )

    _error(len(asset_ids) != len(set(asset_ids)), "duplicate_content_asset_id", errors)
    _error(
        len(source_ids) != len(set(source_ids)),
        "duplicate_source_record_admission",
        errors,
    )
    _error("" in asset_ids, "empty_content_asset_id", errors)
    _error("" in source_ids, "empty_source_record_id", errors)
    _error("" in scene_signatures, "empty_scene_signature", errors)

    integration = report.get("question_bank_integration") or {}
    _error(
        integration.get("target_bank_id") != builder.TARGET_BANK_ID,
        "question_bank_target_invalid",
        errors,
    )
    _error(
        integration.get("second_bank_created") is not False,
        "parallel_question_bank_detected",
        errors,
    )
    _error(
        integration.get("content_asset_ids") != sorted(asset_ids),
        "question_bank_asset_index_mismatch",
        errors,
    )

    handoff = report.get("unit02_reusable_handoff") or {}
    _error(
        handoff.get("handoff_mode") != "REFERENCE_ONLY_NO_CONTENT_COPY",
        "unit02_handoff_mode_invalid",
        errors,
    )
    _error(
        handoff.get("stable_content_asset_ids") != sorted(asset_ids),
        "unit02_handoff_asset_index_mismatch",
        errors,
    )
    _error(
        handoff.get("unit02_content_modified") is not False,
        "unit02_content_modified",
        errors,
    )

    coverage = report.get("coverage_readback") or {}
    _error(
        coverage.get("admitted_content_asset_count") != len(assets),
        "coverage_asset_count_mismatch",
        errors,
    )
    _error(
        coverage.get("three_skill_shared_content_count") != len(assets),
        "coverage_three_skill_count_mismatch",
        errors,
    )
    _error(
        coverage.get("unit02_reusable_asset_count") != len(assets),
        "coverage_reuse_count_mismatch",
        errors,
    )
    _error(
        coverage.get("template_only_task_count") != 0,
        "template_only_count_nonzero",
        errors,
    )

    expected_artifact_sha = builder.digest(
        {key: value for key, value in report.items() if key != "artifact_sha256"}
    )
    _error(
        report.get("artifact_sha256") != expected_artifact_sha,
        "artifact_sha_invalid",
        errors,
    )

    if errors:
        raise ContentHandoffValidationError(";".join(errors))
    return {
        "status": PASS_STATUS,
        "error_count": 0,
        "content_asset_count": len(assets),
        "distinct_scene_count": len(set(scene_signatures)),
        "three_skill_shared_content_count": len(assets),
        "unit02_reusable_asset_count": len(assets),
        "claim_boundaries": {
            "raw_raz_text_published": False,
            "second_question_bank_created": False,
            "unit02_to_unit24_modified": False,
            "listening_claimed_complete": False,
            "a2_unlocked": False,
        },
    }


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ContentHandoffValidationError("OBJECT_REQUIRED")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = validate(load_json(args.report.resolve()))
    except (ContentHandoffValidationError, OSError, json.JSONDecodeError) as exc:
        print("STATUS=FAIL_A1FS_V1_RAZQ01D_UNIT01_CONTENT_HANDOFF_VALIDATION")
        print(f"ERROR={exc}")
        return 1
    print(f"STATUS={result['status']}")
    print(f"CONTENT_ASSETS={result['content_asset_count']}")
    print(f"THREE_SKILL_SHARED={result['three_skill_shared_content_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
