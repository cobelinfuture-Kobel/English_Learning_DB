#!/usr/bin/env python3
"""Validate the RAZQ01E existing-bank content runtime extension."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import (
    build_a1fs_v1_razq01d_unit01_micro_scene_passage_dialogue_admission_three_skill_projection_unit02_handoff
    as content_builder,
)
from ulga.builders import (
    build_a1fs_v1_u01qb01_unit01_pattern_family_approved_variant_pool as bank,
)
from ulga.builders import (
    build_a1fs_v1_u01qb02_unit01_approved_variant_session_runtime as qb02,
)
from ulga.builders import (
    build_a1fs_v1_razq01e_unit01_approved_content_existing_qb_learner_stimulus_runtime
    as builder,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
VALIDATOR_ID = "A1FS_V1_RAZQ01E_UNIT01_EXISTING_QB_CONTENT_RUNTIME_VALIDATOR"
EXPECTED_FAMILIES = {
    "READING": {"U01-PF04-FIRST-MENTION-CONTEXT"},
    "WRITING": {"U01-PF07-WORD-ORDER"},
    "SPEAKING": {
        "U01-PF10-SPEAK-NOUN",
        "U01-PF11-SPEAK-ADJ-NOUN",
        "U01-PF12-SPEAK-VERY-ADJ-NOUN",
    },
}
BLOCKED_LEARNER_KEYS = {
    "accepted_answers",
    "accepted_sequence",
    "accepted_texts",
    "answer_contract",
    "correct_answer",
    "private_item_json",
    "response_contract",
    "rubric",
}


class ContentRuntimeValidationError(ValueError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise ContentRuntimeValidationError(code)


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def _assert_safe(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            require(str(key) not in BLOCKED_LEARNER_KEYS, f"private_key_exposed:{key}")
            _assert_safe(child)
    elif isinstance(value, list):
        for child in value:
            _assert_safe(child)


def _source_ref(item: Mapping[str, Any]) -> dict[str, Any]:
    rows = [
        dict(row)
        for row in item.get("source_refs") or []
        if row.get("source_type") == "RAZQ01D_APPROVED_CONTENT_ASSET"
    ]
    require(len(rows) == 1, f"content_source_ref_invalid:{item.get('item_id')}")
    return rows[0]


def validate_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    require(payload.get("task_id") == builder.TASK_ID, "task_id_invalid")
    require(payload.get("status") == builder.PASS_STATUS, "status_invalid")
    scope = payload.get("scope") or {}
    require(scope.get("allowed_units") == [content_builder.UNIT_ID], "unit_scope_invalid")
    require(scope.get("existing_question_bank_id") == bank.BANK_ID, "bank_id_invalid")
    require(
        scope.get("existing_question_bank_version") == bank.BANK_VERSION,
        "bank_version_invalid",
    )
    require(
        scope.get("extension_mode")
        == "APPEND_VALIDATED_ITEMS_TO_EXISTING_BANK_RUNTIME",
        "extension_mode_invalid",
    )
    for key in (
        "second_question_bank_created",
        "parallel_planner_created",
        "parallel_learner_database_created",
        "parallel_response_capture_created",
        "parallel_scoring_created",
        "unit02_to_unit24_modified",
        "audio_enabled",
        "speaking_capture_enabled",
        "runtime_free_generation_allowed",
    ):
        require(scope.get(key) is False, f"scope_boundary_invalid:{key}")
    require(scope.get("a2_status") == "LOCKED", "a2_scope_invalid")

    bindings = payload.get("source_bindings") or {}
    require(
        bindings.get("approved_content_task_id") == content_builder.TASK_ID,
        "content_task_binding_invalid",
    )
    content_sha = bindings.get("approved_content_artifact_sha256")
    require(isinstance(content_sha, str) and len(content_sha) == 64, "content_sha_invalid")
    asset_count = bindings.get("approved_content_asset_count")
    require(isinstance(asset_count, int) and asset_count >= 2, "content_asset_count_invalid")
    require(bindings.get("base_question_bank_task_id") == bank.TASK_ID, "base_bank_task_invalid")
    require(bindings.get("base_question_bank_id") == bank.BANK_ID, "base_bank_id_invalid")
    require(
        bindings.get("base_question_bank_version") == bank.BANK_VERSION,
        "base_bank_version_invalid",
    )
    require(
        bindings.get("base_approved_item_count") == bank.EXPECTED_APPROVED_COUNT,
        "base_item_count_invalid",
    )
    require(bindings.get("runtime_task_id") == qb02.TASK_ID, "runtime_task_invalid")

    items = payload.get("extension_items")
    require(isinstance(items, list), "extension_items_list_required")
    require(
        len(items) == asset_count * len(content_builder.SKILLS),
        "extension_item_count_invalid",
    )
    item_ids = [item.get("item_id") for item in items]
    signatures = [item.get("semantic_signature") for item in items]
    require(
        None not in item_ids and len(item_ids) == len(set(item_ids)),
        "extension_item_identity_invalid",
    )
    require(
        None not in signatures and len(signatures) == len(set(signatures)),
        "extension_signature_invalid",
    )

    skill_counts = Counter()
    asset_skill_pairs: set[tuple[str, str]] = set()
    for item in items:
        item_id = str(item.get("item_id") or "")
        skill = str(item.get("skill") or "")
        family_id = str(item.get("pattern_family_id") or "")
        require(skill in content_builder.SKILLS, f"extension_skill_invalid:{item_id}")
        require(family_id in EXPECTED_FAMILIES[skill], f"extension_family_invalid:{item_id}")
        require(item.get("unit_id") == content_builder.UNIT_ID, f"extension_unit_invalid:{item_id}")
        require(item.get("learner_visible_capable") is True, f"extension_not_learner_visible:{item_id}")
        require(
            item.get("learner_delivery_status")
            == "READY_FOR_EXISTING_U01QB02_RUNTIME",
            f"extension_delivery_status_invalid:{item_id}",
        )
        require(item.get("runtime_generation_used") is False, f"runtime_generation_detected:{item_id}")
        require(
            item.get("content_extension_task_id") == builder.TASK_ID,
            f"extension_task_binding_invalid:{item_id}",
        )
        require(
            isinstance(item.get("content_asset_id"), str) and item["content_asset_id"],
            f"content_asset_id_invalid:{item_id}",
        )
        require(
            isinstance(item.get("content_sha256"), str)
            and len(item["content_sha256"]) == 64,
            f"content_digest_invalid:{item_id}",
        )
        require(
            isinstance(item.get("stimulus"), str) and item["stimulus"].strip(),
            f"extension_stimulus_missing:{item_id}",
        )
        require(
            isinstance(item.get("prompt"), str) and item["prompt"].strip(),
            f"extension_prompt_missing:{item_id}",
        )
        require(
            (item.get("admission_proposal") or {}).get("status") == "AUTO_APPROVED",
            f"extension_not_approved:{item_id}",
        )
        response = item.get("response_contract") or {}
        require(
            response.get("scoring_mode") == item.get("scoring_mode"),
            f"extension_scoring_mode_drift:{item_id}",
        )
        if skill == "SPEAKING":
            require(response.get("capture_enabled") is False, f"speaking_capture_enabled:{item_id}")
            require(item.get("assessment_eligible") is False, f"speaking_assessment_enabled:{item_id}")
        else:
            require(response.get("capture_enabled") is True, f"capture_disabled:{item_id}")
            require(item.get("assessment_eligible") is True, f"assessment_disabled:{item_id}")
        source_ref = _source_ref(item)
        require(source_ref.get("task_id") == content_builder.TASK_ID, f"content_source_task_invalid:{item_id}")
        require(
            source_ref.get("approved_content_artifact_sha256") == content_sha,
            f"content_source_sha_drift:{item_id}",
        )
        require(
            source_ref.get("content_asset_id") == item.get("content_asset_id"),
            f"content_source_asset_drift:{item_id}",
        )
        require(
            source_ref.get("content_sha256") == item.get("content_sha256"),
            f"content_source_digest_drift:{item_id}",
        )
        asset_skill_pairs.add((item["content_asset_id"], skill))
        skill_counts[skill] += 1

    require(len(asset_skill_pairs) == len(items), "content_asset_skill_pair_duplicate")
    expected_skills = {skill: asset_count for skill in content_builder.SKILLS}
    require(
        dict(sorted(skill_counts.items())) == expected_skills,
        "extension_skill_distribution_invalid",
    )

    readback = payload.get("materialization_readback") or {}
    require(readback.get("approved_content_asset_count") == asset_count, "readback_asset_count_invalid")
    require(readback.get("extension_item_count") == len(items), "readback_extension_count_invalid")
    require(
        readback.get("items_per_content_asset") == len(content_builder.SKILLS),
        "readback_items_per_asset_invalid",
    )
    require(readback.get("skill_distribution") == expected_skills, "readback_skill_distribution_invalid")
    require(
        readback.get("combined_runtime_item_count")
        == bank.EXPECTED_APPROVED_COUNT + len(items),
        "readback_combined_count_invalid",
    )
    require(
        readback.get("minimum_content_items_per_session")
        == builder.MIN_CONTENT_ITEMS_PER_SESSION,
        "readback_content_quota_invalid",
    )
    count_semantics = payload.get("count_semantics") or {}
    require(
        count_semantics.get("content_asset_count_is_not_task_count") is True,
        "count_semantics_asset_invalid",
    )
    require(
        count_semantics.get("extension_task_count_is_not_runtime_variant_count")
        is True,
        "count_semantics_task_invalid",
    )
    require(count_semantics.get("runtime_variant_count") == 0, "runtime_variant_count_invalid")
    return {
        "approved_content_asset_count": asset_count,
        "extension_item_count": len(items),
        "skill_distribution": expected_skills,
        "combined_runtime_item_count": bank.EXPECTED_APPROVED_COUNT + len(items),
    }


def validate_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    policy_artifact.verify_artifact_digest(candidate)
    require(candidate.get("artifact_role") == policy_artifact.CANDIDATE_ROLE, "candidate_role_invalid")
    require(candidate.get("producer_id") == builder.TASK_ID, "candidate_producer_invalid")
    require(candidate.get("level_scope") == ["A1"], "candidate_level_invalid")
    require(candidate.get("learner_facing") is False, "candidate_learner_facing_invalid")
    require(
        (candidate.get("admission") or {}).get("status") == "PENDING_VALIDATION",
        "candidate_admission_invalid",
    )
    summary = validate_payload(candidate.get("payload") or {})
    core = {
        "validator_id": VALIDATOR_ID,
        "status": policy_artifact.PASS_STATUS,
        "candidate_artifact_sha256": candidate["artifact_sha256"],
        "extension_item_count": summary["extension_item_count"],
    }
    return {
        "validator_id": VALIDATOR_ID,
        "status": policy_artifact.PASS_STATUS,
        "receipt_sha256": builder.digest(core),
    }


def validate_approved(approved: Mapping[str, Any]) -> dict[str, Any]:
    policy_artifact.verify_artifact_digest(approved)
    require(approved.get("artifact_role") == policy_artifact.APPROVED_ROLE, "approved_role_invalid")
    require(approved.get("producer_id") == builder.TASK_ID, "approved_producer_invalid")
    require(approved.get("level_scope") == ["A1"], "approved_level_invalid")
    require(approved.get("learner_facing") is False, "approved_learner_facing_invalid")
    require((approved.get("admission") or {}).get("status") == "APPROVED", "approved_admission_invalid")
    require(
        (approved.get("admission") or {}).get("decision_ref") == builder.DECISION_REF,
        "approved_decision_ref_invalid",
    )
    receipts = approved.get("validation_receipts") or []
    require(
        len(receipts) == 1 and receipts[0].get("validator_id") == VALIDATOR_ID,
        "approved_receipt_invalid",
    )
    return validate_payload(approved.get("payload") or {})


def table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return bool(
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
    )


def validate_runtime(database: Path, approved: Mapping[str, Any]) -> dict[str, Any]:
    summary = validate_approved(approved)
    errors: list[str] = []
    counts: dict[str, Any] = {}
    try:
        path = Path(database)
        require(path.is_file(), "runtime_database_missing")
        connection = sqlite3.connect(path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            for table in (
                "lesson_assets",
                "response_contracts",
                "u01qb02_metadata",
                "u01qb02_item_catalog",
                "u01qb02_session_plans",
                "u01qb02_session_items",
                "razq01e_metadata",
                "razq01e_extension_items",
            ):
                require(table_exists(connection, table), f"runtime_table_missing:{table}")
            metadata = dict(connection.execute("SELECT key,value FROM razq01e_metadata"))
            require(metadata.get("task_id") == builder.TASK_ID, "runtime_task_metadata_invalid")
            require(metadata.get("schema_version") == builder.SCHEMA_VERSION, "runtime_schema_metadata_invalid")
            require(metadata.get("validation_status") == builder.PASS_STATUS, "runtime_status_metadata_invalid")
            require(
                metadata.get("approved_extension_artifact_sha256")
                == approved["artifact_sha256"],
                "runtime_extension_sha_invalid",
            )
            require(
                metadata.get("extension_item_count")
                == str(summary["extension_item_count"]),
                "runtime_extension_count_metadata_invalid",
            )
            require(
                metadata.get("combined_runtime_item_count")
                == str(summary["combined_runtime_item_count"]),
                "runtime_combined_count_metadata_invalid",
            )
            require(metadata.get("existing_u01qb02_runtime_reused") == "true", "runtime_qb02_not_reused")
            require(metadata.get("existing_u01qb03_renderer_reused") == "true", "runtime_qb03_not_reused")
            require(metadata.get("parallel_question_bank_created") == "false", "parallel_question_bank_created")
            require(metadata.get("parallel_runtime_created") == "false", "parallel_runtime_created")
            require(metadata.get("a2_unlocked") == "false", "a2_unlocked")

            extension_rows = connection.execute(
                "SELECT * FROM razq01e_extension_items ORDER BY item_id"
            ).fetchall()
            require(
                len(extension_rows) == summary["extension_item_count"],
                "runtime_extension_row_count_invalid",
            )
            expected_items = {
                row["item_id"]: row
                for row in approved.get("payload", {}).get("extension_items") or []
            }
            for extension in extension_rows:
                item_id = extension["item_id"]
                require(item_id in expected_items, f"runtime_unexpected_extension_item:{item_id}")
                item = expected_items[item_id]
                require(extension["content_asset_id"] == item["content_asset_id"], f"runtime_content_asset_drift:{item_id}")
                require(extension["skill"] == item["skill"], f"runtime_skill_drift:{item_id}")
                require(extension["pattern_family_id"] == item["pattern_family_id"], f"runtime_family_drift:{item_id}")
                require(
                    extension["approved_extension_artifact_sha256"]
                    == approved["artifact_sha256"],
                    f"runtime_approved_sha_drift:{item_id}",
                )
                require(
                    extension["extension_item_sha256"] == qb02.digest(item),
                    f"runtime_item_sha_drift:{item_id}",
                )
                catalog = connection.execute(
                    "SELECT * FROM u01qb02_item_catalog WHERE item_id=?", (item_id,)
                ).fetchone()
                require(catalog is not None, f"runtime_catalog_item_missing:{item_id}")
                require(catalog["item_digest"] == qb02.digest(item), f"runtime_catalog_digest_drift:{item_id}")
                require(json.loads(catalog["private_item_json"]) == item, f"runtime_private_item_drift:{item_id}")
                lesson_asset = connection.execute(
                    "SELECT * FROM lesson_assets WHERE asset_key=?", (catalog["asset_key"],)
                ).fetchone()
                require(lesson_asset is not None, f"runtime_lesson_asset_missing:{item_id}")
                require(lesson_asset["asset_id"] == item_id, f"runtime_lesson_asset_id_drift:{item_id}")
                response = connection.execute(
                    "SELECT * FROM response_contracts WHERE asset_key=?", (catalog["asset_key"],)
                ).fetchone()
                require(response is not None, f"runtime_response_contract_missing:{item_id}")
                contract = json.loads(response["contract_json"])
                require(
                    qb02.m6.sha(contract) == response["contract_digest"],
                    f"runtime_response_digest_drift:{item_id}",
                )
                require(contract.get("m12_item_id") == item_id, f"runtime_response_item_drift:{item_id}")

            combined_count = connection.execute(
                "SELECT COUNT(*) FROM u01qb02_item_catalog"
            ).fetchone()[0]
            require(
                combined_count == summary["combined_runtime_item_count"],
                "runtime_combined_catalog_count_invalid",
            )
            combined_source_sha = dict(
                connection.execute("SELECT key,value FROM u01qb02_metadata")
            ).get("source_bank_artifact_sha256")
            require(
                isinstance(combined_source_sha, str) and len(combined_source_sha) == 64,
                "runtime_combined_source_sha_invalid",
            )
            for plan in connection.execute("SELECT * FROM u01qb02_session_plans"):
                if plan["source_bank_sha256"] != combined_source_sha:
                    continue
                extension_count = connection.execute(
                    """SELECT COUNT(*) FROM u01qb02_session_items s
                    JOIN razq01e_extension_items e USING(item_id)
                    WHERE s.session_id=?""",
                    (plan["session_id"],),
                ).fetchone()[0]
                require(
                    extension_count >= builder.MIN_CONTENT_ITEMS_PER_SESSION,
                    f"runtime_session_content_quota_invalid:{plan['session_id']}:{extension_count}",
                )
            counts = {
                "extension_item_count": len(extension_rows),
                "combined_runtime_item_count": combined_count,
                "combined_source_bank_sha256": combined_source_sha,
            }
        finally:
            connection.close()
    except (
        ContentRuntimeValidationError,
        sqlite3.Error,
        OSError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        errors.append(str(exc))
    return {
        "validator_id": VALIDATOR_ID,
        "validation_status": "PASS_A1FS_V1_RAZQ01E_RUNTIME_VALIDATION"
        if not errors
        else "FAIL_A1FS_V1_RAZQ01E_RUNTIME_VALIDATION",
        "error_count": len(errors),
        "errors": errors,
        **counts,
    }


def validate_workbench(
    output_root: Path, database: Path, approved: Mapping[str, Any]
) -> dict[str, Any]:
    summary = validate_approved(approved)
    root = Path(output_root)
    bundle = json.loads((root / "session.private.json").read_text(encoding="utf-8"))
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    _assert_safe(bundle)
    require(bundle.get("item_count") == qb02.SESSION_SIZE, "workbench_item_count_invalid")
    content_items = [
        row
        for row in bundle.get("items") or []
        if row.get("content_extension_task_id") == builder.TASK_ID
    ]
    require(
        len(content_items) >= builder.MIN_CONTENT_ITEMS_PER_SESSION,
        "workbench_content_quota_invalid",
    )
    expected_ids = {
        row["item_id"]
        for row in approved.get("payload", {}).get("extension_items") or []
    }
    require(
        all(row.get("item_id") in expected_ids for row in content_items),
        "workbench_unknown_extension_item",
    )
    require(
        manifest.get("content_extension_item_count") == len(content_items),
        "workbench_manifest_content_count_invalid",
    )
    require(
        manifest.get("existing_u01qb03_renderer_reused") is True,
        "workbench_renderer_authority_not_reused",
    )
    for name, metadata in manifest.get("files", {}).items():
        raw = (root / name).read_bytes()
        require(
            hashlib.sha256(raw).hexdigest() == metadata.get("sha256"),
            f"workbench_file_hash_invalid:{name}",
        )
        require(len(raw) == metadata.get("bytes"), f"workbench_file_size_invalid:{name}")
    runtime = validate_runtime(database, approved)
    require(runtime["error_count"] == 0, "workbench_runtime_validation_failed")
    return {
        "validation_status": "PASS_A1FS_V1_RAZQ01E_WORKBENCH_VALIDATION",
        "content_extension_item_count": len(content_items),
        "extension_item_count": summary["extension_item_count"],
        "combined_runtime_item_count": summary["combined_runtime_item_count"],
    }


def validate_package(
    approved: Mapping[str, Any], safe: Mapping[str, Any]
) -> dict[str, Any]:
    summary = validate_approved(approved)
    safe_core = {
        key: deepcopy(value)
        for key, value in safe.items()
        if key != "readback_sha256"
    }
    require(safe.get("readback_sha256") == builder.digest(safe_core), "safe_hash_invalid")
    require(
        safe.get("approved_extension_artifact_sha256")
        == approved.get("artifact_sha256"),
        "safe_approved_binding_invalid",
    )
    require(
        safe.get("content_governance") == approved.get("content_governance"),
        "safe_governance_binding_invalid",
    )
    hashes = safe.get("extension_item_hashes") or []
    require(
        len(hashes) == summary["extension_item_count"],
        "safe_item_hash_count_invalid",
    )
    expected = {
        row["item_id"]: builder.digest(row)
        for row in approved.get("payload", {}).get("extension_items") or []
    }
    require(
        {row.get("item_id"): row.get("item_sha256") for row in hashes}
        == expected,
        "safe_item_hash_binding_invalid",
    )
    return {
        "validation_status": "PASS_A1FS_V1_RAZQ01E_PACKAGE_VALIDATION",
        **summary,
        "approved_extension_artifact_sha256": approved["artifact_sha256"],
        "safe_readback_sha256": safe["readback_sha256"],
    }
