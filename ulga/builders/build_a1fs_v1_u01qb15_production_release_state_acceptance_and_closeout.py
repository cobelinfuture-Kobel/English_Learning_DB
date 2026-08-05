#!/usr/bin/env python3
"""Validate and close the Unit01 U01QB15 production learner release state."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from product.a1fs_v1_2_1 import u01qb15_runtime_server as runtime
from product.a1fs_v1_2_1 import u01qb15_runtime_server_e2e as e2e
from ulga.builders import (
    build_a1fs_v1_u01qb15_learner_facing_e2e_private_browser_readback as browser_runner,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Validates already-produced Unit01 U01QB15 release metadata and operator Edge "
    "acceptance evidence. It creates no learner content, QuestionBank, scoring rule, "
    "learner-state mutation, Unit02-24 replacement, audio, speaking scoring, or A2 content."
)

PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB15_ProductionReleaseStateAcceptanceAndUnit01NewQuestionBankCloseout"
PASS_STATUS = "PASS_A1FS_V1_U01QB15_PRODUCTION_RELEASE_STATE_ACCEPTED_AND_UNIT01_NEW_QUESTIONBANK_CLOSED_OUT"
PRODUCT_STATUS = "UNIT01_U01QB15_R1_PRODUCTION_LEARNER_VERTICAL_ACCEPTED"
REQUIRED_MAIN_MERGE_SHA = "dda7b06a106c52c9a83e61476839aa548fa4c9fa"
REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "product/a1fs_v1_2_1/product_manifest.json"
EVIDENCE_PATH = REPO_ROOT / "product/a1fs_v1_2_1/release_evidence/u01qb15_operator_edge_acceptance.safe.json"
NEXT_SHORT_STEP = "UNIT01_SCOPE_COMPLETE__NEXT_UNIT_OR_SCOPE_REQUIRES_SEPARATE_APPROVAL"


class ProductionReleaseCloseoutError(ValueError):
    """Fail-closed Unit01 production release acceptance error."""


def _load_object(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProductionReleaseCloseoutError(f"{code}_UNREADABLE:{type(exc).__name__}") from exc
    if not isinstance(value, dict):
        raise ProductionReleaseCloseoutError(f"{code}_NOT_OBJECT")
    return value


def _expect(errors: list[str], actual: Any, expected: Any, code: str) -> None:
    if actual != expected:
        errors.append(f"{code}:{actual!r}:{expected!r}")


def validate_release_state(
    *,
    manifest_path: Path = MANIFEST_PATH,
    evidence_path: Path = EVIDENCE_PATH,
) -> dict[str, Any]:
    manifest = _load_object(manifest_path, "PRODUCT_MANIFEST")
    evidence = _load_object(evidence_path, "EDGE_ACCEPTANCE_EVIDENCE")
    observed = evidence.get("console_observed")
    assertions = evidence.get("pass_contract_assertions")
    if not isinstance(observed, Mapping) or not isinstance(assertions, Mapping):
        raise ProductionReleaseCloseoutError("EDGE_ACCEPTANCE_EVIDENCE_SHAPE_INVALID")

    errors: list[str] = []

    expected_manifest = {
        "product_id": "A1FS_A1_A1PLUS_LOCAL_NOAUDIO",
        "product_version": "1.2.1",
        "serve_module": e2e.MODULE,
        "unit_count": 24,
        "lesson_count": 72,
        "asset_count": 277,
        "unit01_activity_count": 24,
        "unit01_reading_activity_count": 10,
        "unit01_writing_activity_count": 8,
        "unit01_speaking_practice_count": 6,
        "unit01_questionbank_revision": "U01QB15-R1",
        "unit01_questionbank_runtime_item_count": runtime.EXPECTED_RUNTIME_ITEMS,
        "unit01_questionbank_form_count": runtime.EXPECTED_FORMS,
        "unit01_questionbank_blueprint_activity_count": runtime.EXPECTED_BLUEPRINT_ACTIVITIES,
        "unit01_questionbank_cutover_required": True,
        "unit01_questionbank_learner_ui_adapter": "runtime/secure_static/u01qb15.js",
        "unit01_questionbank_form_selection_mode": e2e.FORM_SELECTION_MODE,
        "listening_enabled": False,
        "audio_enabled": False,
        "speaking_capture_enabled": False,
        "public_delivery_enabled": False,
    }
    for key, expected in expected_manifest.items():
        _expect(errors, manifest.get(key), expected, f"MANIFEST_{key.upper()}_INVALID")

    _expect(errors, runtime.EXPECTED_RUNTIME_ITEMS, 474, "RUNTIME_ITEM_DENOMINATOR_INVALID")
    _expect(errors, runtime.EXPECTED_EXTENSION_ITEMS, 186, "REAL62_EXTENSION_DENOMINATOR_INVALID")
    _expect(errors, runtime.EXPECTED_FORMS, 12, "FORM_DENOMINATOR_INVALID")
    _expect(errors, runtime.EXPECTED_BLUEPRINT_ACTIVITIES, 240, "BLUEPRINT_ACTIVITY_DENOMINATOR_INVALID")
    _expect(errors, browser_runner.WINDOWS_EXECUTION_ROOT_MAX, 96, "WINDOWS_EXECUTION_ROOT_BUDGET_DRIFT")
    _expect(errors, browser_runner.WINDOWS_PROJECTED_PATH_MAX, 220, "WINDOWS_PROJECTED_PATH_BUDGET_DRIFT")
    _expect(errors, browser_runner.SHORT_EXECUTION_NAMESPACE, "a1u01", "SHORT_EXECUTION_NAMESPACE_DRIFT")

    expected_observed = {
        "status": browser_runner.PASS_STATUS,
        "browser": "MICROSOFT_EDGE",
        "questionbank_revision": "U01QB15-R1",
        "runtime_items": 474,
        "reading_form": 1,
        "reading_blueprint_cards": 8,
        "reading_next_form": 2,
        "writing_form": 1,
        "writing_outcome": "AUTO_PASS",
        "speaking_form": 1,
        "speaking_blueprint_cards": 4,
        "speaking_next_form": 2,
        "support_filler_exposures": 0,
        "canonical_source_state_unchanged": True,
        "short_execution_root_observed": True,
        "short_execution_namespace": browser_runner.SHORT_EXECUTION_NAMESPACE,
    }
    for key, expected in expected_observed.items():
        _expect(errors, observed.get(key), expected, f"EDGE_{key.upper()}_INVALID")

    required_assertions = {
        "reading_all_accepted_responses_auto_pass": True,
        "writing_scoring_or_human_review_path_exercised": True,
        "speaking_capture_enabled": False,
        "speaking_scoring_enabled": False,
        "legacy_non_unit01_route_smoke_passed": True,
        "unit02_to_unit24_runtime_replaced": False,
        "support_fillers_exposed_to_learner": False,
        "a2_unlocked": False,
        "listening_enabled": False,
        "canonical_source_database_and_state_tree_unchanged": True,
        "disposable_execution_state_used": True,
    }
    for key, expected in required_assertions.items():
        _expect(errors, assertions.get(key), expected, f"EDGE_CONTRACT_{key.upper()}_INVALID")

    _expect(errors, evidence.get("program_id"), PROGRAM_ID, "EVIDENCE_PROGRAM_ID_INVALID")
    _expect(errors, evidence.get("task_id"), TASK_ID, "EVIDENCE_TASK_ID_INVALID")
    _expect(errors, evidence.get("required_main_merge_sha"), REQUIRED_MAIN_MERGE_SHA, "EVIDENCE_REQUIRED_MERGE_SHA_INVALID")

    if errors:
        raise ProductionReleaseCloseoutError(";".join(errors))

    return {
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "product_status": PRODUCT_STATUS,
        "release_authority": {
            "product_version": manifest["product_version"],
            "serve_module": manifest["serve_module"],
            "unit_count": 24,
            "lesson_count": 72,
            "static_asset_count": 277,
            "unit01_questionbank_revision": "U01QB15-R1",
            "unit01_runtime_item_count": 474,
            "unit01_extension_item_count": 186,
            "unit01_form_count": 12,
            "unit01_blueprint_activity_count": 240,
        },
        "learner_vertical_acceptance": {
            "browser": "MICROSOFT_EDGE",
            "reading_form_1_to_2": True,
            "reading_blueprint_cards": 8,
            "writing_form_1_scoring_outcome": observed["writing_outcome"],
            "speaking_form_1_to_2": True,
            "speaking_blueprint_cards": 4,
            "support_filler_exposures": 0,
            "legacy_unit02_to_unit24_route_preserved": True,
            "canonical_source_state_unchanged": True,
        },
        "claim_boundaries": {
            "a2_unlocked": False,
            "listening_enabled": False,
            "audio_enabled": False,
            "speaking_capture_enabled": False,
            "speaking_scoring_enabled": False,
            "public_delivery_enabled": False,
        },
        "windows_private_acceptance": {
            "short_execution_namespace": browser_runner.SHORT_EXECUTION_NAMESPACE,
            "execution_root_budget": browser_runner.WINDOWS_EXECUTION_ROOT_MAX,
            "projected_path_budget": browser_runner.WINDOWS_PROJECTED_PATH_MAX,
            "real_m7_m8_filesystem_refresh_ci_required": True,
            "operator_edge_replay_passed": True,
        },
        "unit01_closeout_complete": True,
        "next_short_step": NEXT_SHORT_STEP,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--evidence", type=Path, default=EVIDENCE_PATH)
    args = parser.parse_args(argv)
    try:
        result = validate_release_state(manifest_path=args.manifest, evidence_path=args.evidence)
    except Exception as exc:
        print(f"STATUS=FAIL_A1FS_V1_U01QB15_PRODUCTION_RELEASE_STATE_ACCEPTANCE:{exc}")
        return 1
    print(f"STATUS={result['status']}")
    print(f"PRODUCT_STATUS={result['product_status']}")
    print("UNIT01_CLOSEOUT_COMPLETE=True")
    print("RUNTIME_ITEMS=474")
    print("FORMS=12")
    print("BLUEPRINT_ACTIVITIES=240")
    print("CANONICAL_SOURCE_STATE_UNCHANGED=True")
    print("A2_UNLOCKED=False")
    print("LISTENING_ENABLED=False")
    print("SPEAKING_SCORING_ENABLED=False")
    print(f"NEXT_SHORT_STEP={result['next_short_step']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
