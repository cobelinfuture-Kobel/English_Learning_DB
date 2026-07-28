#!/usr/bin/env python3
"""S05 public facade with deterministic role and rollback reconciliation.

The S03 approved candidate schema records pedagogical learning_role and
question_type rather than an M6 transport role. This facade derives PRD/CHK/XFR
without changing approved item identity, normalizes the approved response
contract to the complete M6 runtime shape, admits S05 RUNTIME_ACTIVE item
identities into the existing S04 evidence reader, and compares an isolated
failed update root with its own pre-update identity rather than production
metadata.
"""
from __future__ import annotations

import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import (
    _a1fs_online_v1_2_u01e_s05_release_migration_acceptance_core as _core,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Derives existing M6 PRD/CHK/XFR transport metadata, normalizes the approved "
    "response contract to required M6 transport fields without changing answers, "
    "maps installed RUNTIME_ACTIVE item identities into the existing S04 learner "
    "evidence reader, and reconciles isolated rollback identity against its own "
    "pre-update state. It creates no content, answer, scoring rule, learner state, "
    "mastery, audio, A2, external route, or parallel authority."
)


def runtime_role(item: Mapping[str, Any]) -> str:
    question_type = str(item.get("question_type") or "")
    learning_role = str(item.get("learning_role") or "")
    if question_type in {"checkpoint_choice", "checkpoint_write"}:
        return "CHK"
    if learning_role == "TRANSFER":
        return "XFR"
    return "PRD"


def runtime_asset(item: Mapping[str, Any], approved_sha: str) -> dict[str, Any]:
    key = str(item["candidate_item_id"])
    return {
        "asset_key": key,
        "asset_id": key,
        "lesson_id": _core.lesson_for_skill(str(item["skill"])),
        "skill": str(item["skill"]),
        "level": "A1",
        "role": runtime_role(item),
        "learner_payload": _core.learner_payload(item, approved_sha),
        "content_digest": _core.digest(
            {
                "candidate_item_id": key,
                "semantic_signature": item["semantic_signature"],
                "approved_sha": approved_sha,
            }
        ),
    }


def contract_record(
    item: Mapping[str, Any], asset: Mapping[str, Any]
) -> dict[str, Any]:
    contract = deepcopy(dict(item["response_contract"]))
    mode = str(contract.get("scoring_mode") or "NONE")
    capture = bool(
        contract.get("capture_enabled", str(item["skill"]) != "SPEAKING")
    )
    contract.update(
        {
            "asset_key": asset["asset_key"],
            "lesson_id": asset["lesson_id"],
            "skill": asset["skill"],
            "role": asset["role"],
            "capture_enabled": capture,
            "response_type": str(contract.get("response_type") or "string"),
            "accepted_texts": list(contract.get("accepted_texts") or []),
            "accepted_sequence": list(contract.get("accepted_sequence") or []),
            "case_insensitive": bool(contract.get("case_insensitive", True)),
            "punctuation_tolerance": bool(
                contract.get("punctuation_tolerance", True)
            ),
            "human_review_fallback": bool(
                contract.get("human_review_fallback", mode == "FEATURE_RUBRIC")
            ),
            "rubric": dict(contract.get("rubric") or {}),
            "m12_item_id": str(
                contract.get("m12_item_id")
                or f"A1FS_ASSET:{asset['asset_key']}"
            ),
            "m12_session_bank_sha256": contract.get(
                "m12_session_bank_sha256"
            ),
        }
    )
    return {
        "asset_key": asset["asset_key"],
        "lesson_id": asset["lesson_id"],
        "skill": asset["skill"],
        "role": asset["role"],
        "capture_enabled": int(capture),
        "contract": contract,
        "contract_digest": _core.digest(contract),
    }


_S04_LEARNER_EVIDENCE = _core.s04.learner_evidence


def runtime_learner_evidence(
    database_path: Path,
    learner_id: str,
    registry: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    normalized_registry: list[dict[str, Any]] = []
    for row in registry:
        normalized = deepcopy(dict(row))
        if normalized.get("runtime_status") == "RUNTIME_ACTIVE":
            normalized["runtime_status"] = "RUNTIME_EXISTING"
        normalized_registry.append(normalized)
    return _S04_LEARNER_EVIDENCE(
        database_path=database_path,
        learner_id=learner_id,
        registry=normalized_registry,
    )


_core.runtime_asset = runtime_asset
_core.contract_record = contract_record
_core.s04.learner_evidence = runtime_learner_evidence
_core.MODULE = __name__

for _name, _value in vars(_core).items():
    if not _name.startswith("__") and _name not in globals():
        globals()[_name] = _value

MODULE = __name__


def materialize(
    *,
    product_root: Path,
    code_root: Path,
    output_path: Path,
    report_path: Path,
    acceptance_runner: Any | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    acceptance_runner = acceptance_runner or _core.run_acceptance
    product_root = Path(product_root).resolve()
    output_path = Path(output_path).resolve()
    report_path = Path(report_path).resolve()
    package_root = output_path.parent / "a1fs_v1_2_u01e_s05_release"
    if package_root.exists():
        shutil.rmtree(package_root)
    package_root.mkdir(parents=True)

    source = _core.source_product(product_root)
    production_before = {
        "current_version": _core.r01._current_version(product_root),
        "shared_identity": _core.m02_core.shared_identity(product_root),
        "legacy_rows": source["legacy_rows"],
    }
    overlay = _core.build_runtime_overlay(source)
    candidate, static_result = _core.build_candidate_release(
        source=source,
        overlay=overlay,
        package_root=package_root,
        code_root=code_root,
    )

    acceptance_root = _core.m02_core.build_acceptance_root(
        product_root=product_root,
        target_root=package_root / "acceptance_product_root",
    )
    install = _core.install_with_migration(
        product_root=acceptance_root,
        candidate=candidate,
        overlay=overlay,
    )
    acceptance = acceptance_runner(
        product_root=acceptance_root,
        source=source,
        overlay=overlay,
        static_result=static_result,
        screenshot_path=package_root / "visual/unit01_v1_2.png",
    )

    if _core.r01._current_version(product_root) != _core.SOURCE_VERSION:
        raise _core.S05ReleaseError("production_version_mutated")
    if _core.m02_core.shared_identity(product_root) != production_before["shared_identity"]:
        raise _core.S05ReleaseError("production_shared_state_mutated")
    if _core.source_product(product_root)["legacy_rows"] != production_before["legacy_rows"]:
        raise _core.S05ReleaseError("production_legacy_rows_mutated")

    failure_root = _core.m02_core.build_acceptance_root(
        product_root=product_root,
        target_root=package_root / "failed_update_product_root",
    )
    failure_before = _core.m02_core.shared_identity(failure_root)
    failed_rollback = False
    try:
        _core.install_with_migration(
            product_root=failure_root,
            candidate=candidate,
            overlay=overlay,
            inject_failure=True,
        )
    except _core.S05ReleaseError as exc:
        if "injected_migration_failure" not in str(exc):
            raise
        failed_rollback = (
            _core.r01._current_version(failure_root) == _core.SOURCE_VERSION
            and _core.m02_core.shared_identity(failure_root) == failure_before
        )
    if not failed_rollback:
        raise _core.S05ReleaseError("failed_update_rollback_acceptance_failed")

    installer = _core.write_installer(package_root, candidate)
    receipt_core = {
        "task_id": _core.TASK_ID,
        "program_id": _core.PROGRAM_ID,
        "schema_version": _core.SCHEMA_VERSION,
        "validation_status": _core.PASS_STATUS,
        "product_status": _core.PRODUCT_STATUS,
        "release_id": _core.RELEASE_ID,
        "source_product_version": _core.SOURCE_VERSION,
        "target_product_version": _core.TARGET_VERSION,
        "source_identity": {
            "source_release_sha256": _core.r01.directory_digest(source["release_root"]),
            "source_shared_identity": production_before["shared_identity"],
            "s03_approved_sha256": overlay["approved"]["artifact_sha256"],
            "s02_safe_pack_sha256": overlay["safe_pack"]["pack_sha256"],
        },
        "runtime_outputs": {
            "package_root": str(package_root),
            "candidate_root": str(candidate),
            "acceptance_product_root": str(acceptance_root),
            "installer_path": str(installer),
            "visual_screenshot_path": str(package_root / "visual/unit01_v1_2.png"),
        },
        "release_summary": {
            "unit_count": _core.EXPECTED_UNIT_COUNT,
            "lesson_count": _core.EXPECTED_LESSON_COUNT,
            "source_asset_count": _core.EXPECTED_SOURCE_ASSET_COUNT,
            "target_asset_count": _core.EXPECTED_TARGET_ASSET_COUNT,
            "new_asset_count": _core.s04.EXPECTED_NEW_COUNT,
            "unit01_activity_count": _core.s04.EXPECTED_TOTAL_COUNT,
            "unit01_counts": _core.EXPECTED_UNIT01_COUNTS,
            "context_count": 5,
            "question_type_count": _core.s04.EXPECTED_ASSESSMENT_PATTERN_COUNT,
            "changed_lesson_ids": overlay["changed_lesson_ids"],
            "preserved_lesson_count": 69,
        },
        "migration_summary": install["migration"],
        "acceptance_summary": acceptance,
        "recovery_summary": {
            "failed_update_automatic_rollback_pass": failed_rollback,
            "explicit_v1_1_rollback_pass": acceptance["rollback"]["v1_1_version_loaded"],
            "v1_1_post_migration_database_compatibility_pass": acceptance["rollback"][
                "post_migration_database_readable"
            ],
            "forward_switch_back_to_v1_2_pass": acceptance["rollback"][
                "forward_switch_back_to_v1_2_pass"
            ],
        },
        "production_safety": {
            "production_current_version_unchanged": True,
            "production_shared_state_unchanged": True,
            "production_legacy_rows_unchanged": True,
            "source_database_mutated": False,
            "existing_11_asset_identities_changed": False,
            "other_69_lessons_changed": False,
        },
        "boundaries": {
            "runtime_free_generation_allowed": False,
            "unit02_modified": False,
            "listening_enabled": False,
            "audio_enabled": False,
            "speaking_capture_enabled": False,
            "a2_unlocked": False,
            "external_binding_enabled": False,
            "mastery_inferred_from_single_attempt": False,
        },
        "stop_reason": "NONE",
        "next_short_step": _core.NEXT_SHORT_STEP,
    }
    receipt = {**receipt_core, "artifact_sha256": _core.digest(receipt_core)}
    safe_core = {
        "task_id": _core.TASK_ID,
        "program_id": _core.PROGRAM_ID,
        "schema_version": _core.SCHEMA_VERSION,
        "validation_status": _core.PASS_STATUS,
        "product_status": _core.PRODUCT_STATUS,
        "release_id": _core.RELEASE_ID,
        "source_product_version": _core.SOURCE_VERSION,
        "target_product_version": _core.TARGET_VERSION,
        "release_summary": receipt_core["release_summary"],
        "acceptance_summary": acceptance,
        "recovery_summary": receipt_core["recovery_summary"],
        "production_safety": receipt_core["production_safety"],
        "boundaries": receipt_core["boundaries"],
        "stop_reason": "NONE",
        "next_short_step": _core.NEXT_SHORT_STEP,
    }
    safe = {**safe_core, "report_sha256": _core.digest(safe_core)}
    _core.write_json(output_path, receipt, private=True)
    _core.write_json(report_path, safe)
    return receipt, safe


_core.materialize = materialize
