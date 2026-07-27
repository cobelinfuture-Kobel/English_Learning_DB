#!/usr/bin/env python3
'''Independent validator for the R01 self-contained V1 product root.'''
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from ulga.builders import build_a1fs_online_v1_r01_self_contained_product_root_update_channel as r01

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Validates the packaged existing V1 runtime, persistent shared-state boundary, relative-path "
    "manifest, ASCII launchers, checksums, atomic update and rollback contracts; it creates no content."
)
VALIDATION_STATUS = "PASS_A1FS_ONLINE_V1_R01_SELF_CONTAINED_PRODUCT_ROOT_VALIDATED"


def _inside(path: Path, root: Path) -> bool:
    try:
        Path(path).resolve().relative_to(Path(root).resolve())
        return True
    except ValueError:
        return False


def _exact_private_keys(value: Any) -> set[str]:
    forbidden = {
        "attempt_id", "session_id", "asset_key", "response", "response_json",
        "review_queue", "database_path", "auth_state_path", "state_root",
        "product_root", "release_root",
    }
    found: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                if str(key).casefold() in forbidden:
                    found.add(str(key).casefold())
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(value)
    return found


def validate_outputs(*, receipt: Mapping[str, Any], safe_report: Mapping[str, Any],
                     output_root: Path, s19_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    if (
        receipt.get("task_id"), receipt.get("schema_version"),
        receipt.get("validation_status"), receipt.get("product_status"),
        receipt.get("product_id"), receipt.get("product_version"),
    ) != (
        r01.TASK_ID, r01.SCHEMA_VERSION, r01.PASS_STATUS, r01.PRODUCT_STATUS,
        r01.PRODUCT_ID, r01.PRODUCT_VERSION,
    ):
        errors.append("r01_receipt_identity_invalid")
    body = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if receipt.get("artifact_sha256") != r01.s19.digest(body):
        errors.append("r01_receipt_digest_invalid")
    safe_body = {key: value for key, value in safe_report.items() if key != "report_sha256"}
    if safe_report.get("report_sha256") != r01.s19.digest(safe_body):
        errors.append("r01_safe_digest_invalid")
    for key in sorted(_exact_private_keys(safe_report)):
        errors.append(f"r01_safe_private_key_present:{key}")

    outputs = receipt.get("runtime_outputs", {})
    product_root = Path(str(outputs.get("product_root") or "")).resolve()
    release_root = Path(str(outputs.get("release_root") or "")).resolve()
    if not _inside(product_root, output_root):
        errors.append("r01_product_root_outside_authority_root")
    for name in (
        "release_manifest_path", "checksum_manifest_path", "shared_database_path",
        "shared_auth_state_path", "shared_learner_state_root", "current_version_path",
        "product_manifest_path",
    ):
        if not _inside(Path(str(outputs.get(name) or "")), product_root):
            errors.append(f"r01_output_outside_product_root:{name}")
    if not product_root.is_dir() or not release_root.is_dir():
        errors.append("r01_product_or_release_root_missing")
    else:
        try:
            manifest = r01.validate_release(release_root)
            if manifest.get("product_version") != r01.PRODUCT_VERSION:
                errors.append("r01_release_version_invalid")
            if any(manifest.get(key) is not False for key in (
                "external_network_binding_allowed", "public_delivery_enabled",
                "cloudflare_enabled", "listening_enabled", "audio_enabled",
                "speaking_capture_enabled", "a2_session_enabled",
            )):
                errors.append("r01_release_boundary_invalid")
        except (r01.ProductRootError, OSError, KeyError, ValueError) as exc:
            errors.append(str(exc))

    current = product_root / "current_version.txt"
    if not current.is_file() or current.read_text(encoding="ascii").strip() != r01.PRODUCT_VERSION:
        errors.append("r01_current_version_invalid")
    product_manifest = product_root / "product.json"
    if not product_manifest.is_file():
        errors.append("r01_product_manifest_missing")
    else:
        value = r01.read_json(product_manifest, "r01_product")
        if (
            value.get("product_id") != r01.PRODUCT_ID
            or value.get("update_policy") != "STAGE_VALIDATE_BACKUP_ATOMIC_SWITCH_ROLLBACK"
            or value.get("github_code_authority") != "cobelinfuture-Kobel/English_Learning_DB:main"
            or value.get("external_network_binding_allowed") is not False
        ):
            errors.append("r01_product_manifest_invalid")

    operator = outputs.get("operator_paths", {})
    required = {
        "OPEN_A1FS_V1.bat": (" start ", "http://127.0.0.1:8765"),
        "STOP_A1FS_V1.bat": (" stop ",),
        "STATUS_A1FS_V1.bat": (" status ",),
        "UPDATE_A1FS_V1.bat": (" update ", "--candidate", "--version"),
        "ROLLBACK_A1FS_V1.bat": (" rollback ",),
    }
    for name, tokens in required.items():
        path = Path(str(operator.get(name) or ""))
        if not path.is_file():
            errors.append(f"r01_operator_missing:{name}")
            continue
        data = path.read_bytes()
        if data.startswith(b"\xef\xbb\xbf") or any(byte > 127 for byte in data):
            errors.append(f"r01_operator_not_ascii_no_bom:{name}")
        if b"\r\n" not in data:
            errors.append(f"r01_operator_not_crlf:{name}")
        text = data.decode("ascii", errors="replace")
        if not all(token in text for token in tokens):
            errors.append(f"r01_operator_contract_invalid:{name}")

    summary = receipt.get("product_root_summary", {})
    expected = {
        "product_id": r01.PRODUCT_ID, "product_version": r01.PRODUCT_VERSION,
        "unit_count": 24, "lesson_count": 72, "asset_count": 264,
        "scored_lesson_count": 48, "speaking_practice_lesson_count": 24,
        "dashboard_role_count": 3,
        "self_contained_product_root_created": True,
        "immutable_release_directory_created": True,
        "shared_persistent_state_created": True,
        "relative_path_manifest_created": True,
        "ascii_crlf_bat_bundle_created": True,
        "atomic_update_channel_created": True,
        "automatic_rollback_on_update_failure": True,
        "explicit_rollback_command_created": True,
        "shared_state_preserved_across_updates": True,
        "release_checksum_verified": True,
        "external_deployment_enabled": False, "public_delivery_enabled": False,
        "cloudflare_enabled": False, "listening_enabled": False,
        "audio_enabled": False, "speaking_capture_enabled": False,
        "a2_session_enabled": False,
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            errors.append(f"r01_summary_invalid:{key}")
    capability = receipt.get("capability_contract", {})
    if capability != {
        "s19_release_candidate_reused": True, "s17_runtime_reused": True,
        "m6_scoring_review_reused": True,
        "m7_m8_canonical_learning_reused": True,
        "m9_dashboard_projection_reused": True,
        "parallel_curriculum_created": False,
        "parallel_learner_state_engine_created": False,
        "parallel_scoring_engine_created": False,
        "parallel_mastery_engine_created": False,
        "parallel_dashboard_engine_created": False,
        "parallel_review_engine_created": False,
    }:
        errors.append("r01_capability_contract_invalid")
    if receipt.get("stop_reason") != "NONE" or receipt.get("next_short_step") != r01.NEXT_SHORT_STEP:
        errors.append("r01_transition_contract_invalid")
    if not str(Path(s19_path)):
        errors.append("r01_source_s19_binding_invalid")
    return {
        "task_id": r01.TASK_ID,
        "validation_status": VALIDATION_STATUS if not errors else "FAIL_A1FS_ONLINE_V1_R01_VALIDATION",
        "error_count": len(errors), "errors": errors,
    }
