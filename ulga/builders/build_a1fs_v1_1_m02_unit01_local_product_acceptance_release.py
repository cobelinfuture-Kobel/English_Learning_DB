#!/usr/bin/env python3
"""Materialize, accept, and package the A1FS V1.1 Unit 01 localhost release."""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from ulga.builders import _a1fs_v1_1_m02_acceptance as acceptance
from ulga.builders import _a1fs_v1_1_m02_release_core as core
from ulga.builders import build_a1fs_online_v1_r01_self_contained_product_root_update_channel as r01
from ulga.builders import build_a1fs_v1_1_m01_unit01_cross_skill_vertical_slice as m01

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Orchestrates M01 approved-content materialization, R01-compatible release packaging, and isolated localhost acceptance; it creates no learner content, answer, scoring, mastery, dashboard, state, audio, A2, external route, or parallel authority."

PROGRAM_ID = "A1FS-ONLINE-V1.1"
TASK_ID = "A1FS-ONLINE-V1.1-M02_Unit01LocalProductAcceptanceAndV1_1ReleasePackaging"
SCHEMA_VERSION = "a1fs.online.v1_1.m02.unit01_local_product_acceptance_release.v1"
PASS_STATUS = "PASS_A1FS_ONLINE_V1_1_M02_UNIT01_LOCAL_PRODUCT_ACCEPTED_AND_RELEASE_PACKAGED"
PRODUCT_STATUS = "A1FS_V1_1_UNIT01_LOCALHOST_RELEASE_PACKAGE_READY"
RELEASE_ID = core.RELEASE_ID
SOURCE_PRODUCT_VERSION = core.SOURCE_VERSION
TARGET_PRODUCT_VERSION = core.TARGET_VERSION
NEXT_SHORT_STEP = "A1FS-ONLINE-V1.1-M03_Unit02CrossSkillLearnerContentVerticalSlice"


class M02ReleaseError(ValueError):
    """Fail-closed M02 orchestration error."""


def digest(value: Any) -> str:
    return core.digest(value)


def write_json(path: Path, value: Mapping[str, Any], *, private: bool = False) -> None:
    core.write_json(path, value, private=private)


def _package_manifest(*, package_root: Path, candidate_root: Path, installer: Path) -> dict[str, Any]:
    return {
        "schema_version": "a1fs.online.v1_1.m02.update_package.v1",
        "release_id": RELEASE_ID,
        "source_version": SOURCE_PRODUCT_VERSION,
        "target_version": TARGET_PRODUCT_VERSION,
        "candidate_root": str(candidate_root),
        "installer_path": str(installer),
        "install_contract": "STOP_PRODUCT_THEN_R01_STAGE_VALIDATE_BACKUP_ATOMIC_SWITCH",
        "rollback_contract": "R01_PREVIOUS_VERSION_POINTER_AND_SHARED_STATE_PRESERVATION",
        "package_root": str(package_root),
        "production_state_packaged": False,
        "production_state_mutated": False,
        "external_network_binding_allowed": False,
        "audio_enabled": False,
        "a2_unlocked": False,
    }


def materialize(
    *, product_root: Path, code_root: Path, output_path: Path, report_path: Path,
    acceptance_runner: Callable[..., dict[str, Any]] = acceptance.run,
) -> tuple[dict[str, Any], dict[str, Any]]:
    product_root = Path(product_root).resolve()
    code_root = Path(code_root).resolve()
    output_path = Path(output_path).resolve()
    report_path = Path(report_path).resolve()
    if not (code_root / "ulga").is_dir():
        raise M02ReleaseError("code_root_ulga_missing")
    source = core.source_product(product_root)
    production_before = dict(source["shared_identity"])
    package_root = output_path.parent / "a1fs_v1_1_unit01_release_package"
    if package_root.exists():
        shutil.rmtree(package_root)
    package_root.mkdir(parents=True)
    overlay = core.build_m01_overlay(source, package_root)
    candidate_root = core.build_candidate_release(
        package_root=package_root,
        code_root=code_root,
        source=source,
        overlay=overlay,
    )
    acceptance_root = core.build_acceptance_root(
        product_root=product_root,
        target_root=package_root / "acceptance" / "A1FS_V1_ACCEPTANCE_CLONE",
    )
    acceptance_before = core.shared_identity(acceptance_root)
    acceptance_contract_before = core.response_contract_identity(
        acceptance_root / "shared/database/learner_runtime.sqlite3",
        list(m01.LESSON_IDS.values()),
    )
    update_result = r01.install_candidate(
        product_root=acceptance_root,
        candidate=candidate_root,
        version=TARGET_PRODUCT_VERSION,
    )
    acceptance_after_update = core.shared_identity(acceptance_root)
    acceptance_contract_after = core.response_contract_identity(
        acceptance_root / "shared/database/learner_runtime.sqlite3",
        list(m01.LESSON_IDS.values()),
    )
    if acceptance_after_update != acceptance_before:
        raise M02ReleaseError("acceptance_shared_state_changed_during_update")
    if acceptance_contract_after != acceptance_contract_before:
        raise M02ReleaseError("acceptance_response_contract_changed_during_update")
    local_acceptance = acceptance_runner(product_root=acceptance_root)
    production_after = core.shared_identity(product_root)
    production_contract_after = core.response_contract_identity(
        product_root / "shared/database/learner_runtime.sqlite3",
        list(m01.LESSON_IDS.values()),
    )
    if production_after != production_before:
        raise M02ReleaseError("production_shared_state_mutated")
    if production_contract_after != source["unit01_contract_sha256"]:
        raise M02ReleaseError("production_response_contract_mutated")
    installer = core.write_installer(package_root=package_root, candidate_root=candidate_root)
    package_manifest = _package_manifest(
        package_root=package_root,
        candidate_root=candidate_root,
        installer=installer,
    )
    package_manifest_path = package_root / "update_package.json"
    write_json(package_manifest_path, package_manifest)
    release_summary = {
        "source_product_version": SOURCE_PRODUCT_VERSION,
        "target_product_version": TARGET_PRODUCT_VERSION,
        "release_id": RELEASE_ID,
        "unit_count": 24,
        "lesson_count": 72,
        "asset_count": 264,
        "modified_unit_count": 1,
        "modified_lesson_count": overlay["overlay"]["modified_lesson_count"],
        "preserved_lesson_count": overlay["overlay"]["preserved_lesson_count"],
        "reading_activity_count": overlay["overlay"]["reading_activity_count"],
        "writing_activity_count": overlay["overlay"]["writing_activity_count"],
        "speaking_practice_count": overlay["overlay"]["speaking_practice_count"],
        "candidate_checksum_verified": True,
        "r01_atomic_update_acceptance_pass": update_result.get("status") == "PASS_ATOMIC_UPDATE_ACTIVATED",
        "isolated_local_product_acceptance_pass": True,
        "production_shared_state_unchanged": production_after == production_before,
        "production_response_contracts_unchanged": production_contract_after == source["unit01_contract_sha256"],
        "acceptance_shared_state_preserved_during_update": acceptance_after_update == acceptance_before,
        "acceptance_response_contracts_preserved_during_update": acceptance_contract_after == acceptance_contract_before,
        "installer_created": installer.is_file(),
    }
    receipt_core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "product_status": PRODUCT_STATUS,
        "release_id": RELEASE_ID,
        "source_identity": {
            "r01_product_id": r01.PRODUCT_ID,
            "source_product_version": SOURCE_PRODUCT_VERSION,
            "source_release_manifest_sha256": digest(source["manifest"]),
            "source_bundle_sha256": digest(source["bundles"]),
            "source_unit01_response_contract_sha256": source["unit01_contract_sha256"],
            "m01_approved_content_sha256": overlay["approved"]["artifact_sha256"],
        },
        "runtime_outputs": {
            "package_root": str(package_root),
            "m01_materialization_root": str(overlay["root"]),
            "candidate_root": str(candidate_root),
            "candidate_manifest_path": str(candidate_root / "release_manifest.json"),
            "candidate_checksums_path": str(candidate_root / "checksums.json"),
            "update_package_manifest_path": str(package_manifest_path),
            "installer_path": str(installer),
            "acceptance_root": str(acceptance_root),
        },
        "release_summary": release_summary,
        "local_acceptance": local_acceptance,
        "production_shared_state_before": production_before,
        "production_shared_state_after": production_after,
        "boundaries": {
            "production_product_root_updated": False,
            "production_learner_state_mutated": False,
            "production_auth_state_mutated": False,
            "production_response_contract_mutated": False,
            "parallel_curriculum_created": False,
            "parallel_state_engine_created": False,
            "parallel_scoring_engine_created": False,
            "parallel_mastery_engine_created": False,
            "parallel_dashboard_engine_created": False,
            "listening_enabled": False,
            "audio_enabled": False,
            "speaking_capture_enabled": False,
            "a2_unlocked": False,
            "external_network_binding_allowed": False,
        },
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    receipt = {**receipt_core, "artifact_sha256": digest(receipt_core)}
    safe_core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "product_status": PRODUCT_STATUS,
        "release_id": RELEASE_ID,
        "release_summary": deepcopy(release_summary),
        "local_acceptance": deepcopy(local_acceptance),
        "boundaries": deepcopy(receipt_core["boundaries"]),
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    safe = {**safe_core, "report_sha256": digest(safe_core)}
    write_json(output_path, receipt, private=True)
    write_json(report_path, safe)
    return receipt, safe


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    build = parser.add_subparsers(dest="command", required=True).add_parser("materialize")
    build.add_argument("--product-root", type=Path, required=True)
    build.add_argument("--code-root", type=Path, default=Path(__file__).resolve().parents[2])
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        receipt, safe = materialize(
            product_root=args.product_root,
            code_root=args.code_root,
            output_path=args.output,
            report_path=args.report,
        )
        from ulga.validators import validate_a1fs_v1_1_m02_unit01_local_product_acceptance_release as validator

        validation = validator.validate_outputs(
            receipt=receipt,
            safe_report=safe,
            output_root=args.output.parent,
            product_root=args.product_root,
        )
        if validation["error_count"]:
            raise M02ReleaseError("validation_failed:" + "|".join(validation["errors"]))
        print(json.dumps(safe, ensure_ascii=False, indent=2))
        return 0
    except (
        M02ReleaseError,
        core.ReleaseCoreError,
        acceptance.AcceptanceError,
        r01.ProductRootError,
        sqlite3.Error,
        OSError,
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
