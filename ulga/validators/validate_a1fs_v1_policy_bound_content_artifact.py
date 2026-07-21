#!/usr/bin/env python3
"""Independently validate policy-bound A1FS-V1 content artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = REPO_ROOT / "ulga/contracts/a1fs_v1_canonical_content_production_policy.json"

ARTIFACT_SCHEMA_VERSION = "a1fs.v1.policy_bound_content_artifact.v1"
CANDIDATE_ROLE = "CANDIDATE_JSON"
APPROVED_ROLE = "APPROVED_CANONICAL_JSON"
PROJECTION_ROLE = "FOUR_SKILL_PROJECTION_JSON"
MEDIA_ROLE = "APPROVED_MEDIA_MANIFEST_JSON"
EXCEL_ROLE = "EXCEL_REFERENCE_EXPORT_MANIFEST"
PASS_STATUS = "PASS_A1FS_V1_POLICY_BOUND_CONTENT_ARTIFACT"
HEX = set("0123456789abcdef")

REQUIRED_TOP_LEVEL = {
    "schema_version",
    "artifact_role",
    "producer_id",
    "level_scope",
    "source_bindings",
    "validation_receipts",
    "admission",
    "learner_facing",
    "payload",
    "content_governance",
    "artifact_sha256",
}


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= HEX


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("json_object_required")
    return value


def _validate_receipts(receipts: Any, *, require_nonempty: bool, errors: list[str]) -> None:
    if not isinstance(receipts, list):
        errors.append("validation_receipts_list_required")
        return
    if require_nonempty and not receipts:
        errors.append("validation_receipts_required")
    for index, receipt in enumerate(receipts):
        if not isinstance(receipt, Mapping):
            errors.append(f"validation_receipt_object_required:{index}")
            continue
        if set(receipt) != {"validator_id", "status", "receipt_sha256"}:
            errors.append(f"validation_receipt_fields_invalid:{index}")
        if not isinstance(receipt.get("validator_id"), str) or not receipt.get("validator_id"):
            errors.append(f"validation_receipt_validator_id_invalid:{index}")
        if receipt.get("status") != "PASS":
            errors.append(f"validation_receipt_not_pass:{index}")
        if not _is_sha256(receipt.get("receipt_sha256")):
            errors.append(f"validation_receipt_sha256_invalid:{index}")


def _validate_binding(
    artifact: Mapping[str, Any],
    policy: Mapping[str, Any],
    *,
    role: str,
    errors: list[str],
) -> None:
    governance = artifact.get("content_governance")
    if not isinstance(governance, Mapping):
        errors.append("content_governance_object_required")
        return
    expected = {
        "policy_id": policy.get("policy_id"),
        "policy_schema_version": policy.get("schema_version"),
        "policy_sha256": digest(policy),
        "artifact_role": role,
        "canonical_source": policy.get("authoritative_source"),
        "four_skill_source": policy.get("four_skill_source"),
        "excel_role": policy.get("excel", {}).get("role"),
        "excel_export_direction": policy.get("excel", {}).get("export_direction"),
        "excel_writeback_allowed": policy.get("excel", {}).get("canonical_writeback_allowed"),
        "a2_unlocked": policy.get("a2_unlocked"),
    }
    if dict(governance) != expected:
        errors.append("content_governance_binding_mismatch")


def validate_artifact(
    artifact: Mapping[str, Any],
    *,
    policy: Mapping[str, Any] | None = None,
    expected_role: str | None = None,
) -> dict[str, Any]:
    policy = dict(policy or load_json(POLICY_PATH))
    errors: list[str] = []

    if set(artifact) != REQUIRED_TOP_LEVEL:
        errors.append("top_level_fields_invalid")
    if artifact.get("schema_version") != ARTIFACT_SCHEMA_VERSION:
        errors.append("schema_version_invalid")

    role = artifact.get("artifact_role")
    allowed_roles = policy.get("artifact_binding", {}).get("artifact_roles", [])
    if role not in allowed_roles:
        errors.append("artifact_role_invalid")
    if expected_role is not None and role != expected_role:
        errors.append("expected_artifact_role_mismatch")

    if not isinstance(artifact.get("producer_id"), str) or not artifact.get("producer_id"):
        errors.append("producer_id_invalid")

    level_scope = artifact.get("level_scope")
    allowed_levels = policy.get("level_scope", [])
    if (
        not isinstance(level_scope, list)
        or not level_scope
        or len(level_scope) != len(set(level_scope))
        or any(level not in allowed_levels for level in level_scope)
    ):
        errors.append("level_scope_invalid")

    if not isinstance(artifact.get("source_bindings"), Mapping) or not artifact.get("source_bindings"):
        errors.append("source_bindings_invalid")
    if not isinstance(artifact.get("admission"), Mapping):
        errors.append("admission_object_required")
    if not isinstance(artifact.get("learner_facing"), bool):
        errors.append("learner_facing_boolean_required")
    if not isinstance(artifact.get("payload"), Mapping):
        errors.append("payload_object_required")

    actual_sha = artifact.get("artifact_sha256")
    if not _is_sha256(actual_sha):
        errors.append("artifact_sha256_invalid")
    else:
        expected_sha = digest(
            {key: value for key, value in artifact.items() if key != "artifact_sha256"}
        )
        if actual_sha != expected_sha:
            errors.append("artifact_sha256_mismatch")

    if isinstance(role, str):
        _validate_binding(artifact, policy, role=role, errors=errors)

    admission_value = artifact.get("admission")
    admission = admission_value if isinstance(admission_value, Mapping) else {}
    receipts = artifact.get("validation_receipts")
    source_value = artifact.get("source_bindings")
    source_bindings = source_value if isinstance(source_value, Mapping) else {}
    payload_value = artifact.get("payload")
    payload = payload_value if isinstance(payload_value, Mapping) else {}

    if role == CANDIDATE_ROLE:
        _validate_receipts(receipts, require_nonempty=False, errors=errors)
        if receipts not in ([], None):
            errors.append("candidate_validation_receipts_must_be_empty")
        if admission.get("status") != "PENDING_VALIDATION" or admission.get("decision_ref") is not None:
            errors.append("candidate_admission_state_invalid")
        if artifact.get("learner_facing") is not False:
            errors.append("candidate_learner_facing_forbidden")

    elif role == APPROVED_ROLE:
        _validate_receipts(receipts, require_nonempty=True, errors=errors)
        if admission.get("status") != "APPROVED":
            errors.append("approved_admission_status_invalid")
        if not isinstance(admission.get("decision_ref"), str) or not admission.get("decision_ref"):
            errors.append("approved_decision_ref_required")
        if not _is_sha256(source_bindings.get("candidate_artifact_sha256")):
            errors.append("candidate_artifact_binding_invalid")
        if artifact.get("learner_facing") is not False:
            errors.append("approved_canonical_direct_learner_facing_forbidden")

    elif role == PROJECTION_ROLE:
        _validate_receipts(receipts, require_nonempty=True, errors=errors)
        if admission.get("status") != "APPROVED_SOURCE_BOUND":
            errors.append("projection_admission_status_invalid")
        if not _is_sha256(source_bindings.get("approved_canonical_artifact_sha256")):
            errors.append("projection_approved_source_binding_invalid")
        required = set(policy.get("required_projection_fields", []))
        if not isinstance(payload, Mapping) or not required.issubset(payload):
            errors.append("projection_required_fields_missing")
        else:
            skill = str(payload.get("skill", "")).upper()
            if skill not in policy.get("four_skill_projections", []):
                errors.append("projection_skill_invalid")
            if not isinstance(payload.get("prompt"), str) or not payload.get("prompt"):
                errors.append("projection_prompt_invalid")
            if not isinstance(payload.get("scoring_contract"), Mapping):
                errors.append("projection_scoring_contract_invalid")
            if not isinstance(payload.get("source_bindings"), Mapping):
                errors.append("projection_payload_source_bindings_invalid")
        if artifact.get("learner_facing") is not True:
            errors.append("projection_must_be_learner_facing")

    elif role == MEDIA_ROLE:
        _validate_receipts(receipts, require_nonempty=True, errors=errors)
        if admission.get("status") != "APPROVED_MEDIA":
            errors.append("media_admission_status_invalid")
        if not _is_sha256(source_bindings.get("approved_canonical_artifact_sha256")):
            errors.append("media_approved_source_binding_invalid")
        expected_status = policy.get("image_generation_gate", {}).get(
            "learner_facing_media_requires"
        )
        if payload.get("image_scene_consistency_status") != expected_status:
            errors.append("image_scene_consistency_pass_required")
        if not _is_sha256(source_bindings.get("scene_contract_sha256")):
            errors.append("scene_contract_binding_invalid")
        if artifact.get("learner_facing") is not True:
            errors.append("approved_media_must_be_learner_facing")

    elif role == EXCEL_ROLE:
        _validate_receipts(receipts, require_nonempty=False, errors=errors)
        if receipts not in ([], None):
            errors.append("excel_validation_receipts_must_be_empty")
        if admission.get("status") != "DERIVED_REFERENCE_ONLY":
            errors.append("excel_admission_status_invalid")
        if not _is_sha256(source_bindings.get("source_json_artifact_sha256")):
            errors.append("excel_source_json_binding_invalid")
        if source_bindings.get("source_json_artifact_role") not in {
            APPROVED_ROLE,
            PROJECTION_ROLE,
            MEDIA_ROLE,
        }:
            errors.append("excel_source_role_invalid")
        if payload.get("role") != policy.get("excel", {}).get("role"):
            errors.append("excel_role_invalid")
        if payload.get("export_direction") != policy.get("excel", {}).get("export_direction"):
            errors.append("excel_export_direction_invalid")
        if payload.get("canonical_writeback_allowed") is not False:
            errors.append("excel_writeback_forbidden")
        filename = payload.get("workbook_filename")
        if (
            not isinstance(filename, str)
            or not filename.lower().endswith(".xlsx")
            or Path(filename).name != filename
        ):
            errors.append("excel_workbook_filename_invalid")
        if not _is_sha256(payload.get("workbook_sha256")):
            errors.append("excel_workbook_sha256_invalid")
        if artifact.get("learner_facing") is not False:
            errors.append("excel_manifest_learner_facing_forbidden")

    return {
        "schema_version": "a1fs.v1.policy_bound_content_artifact_validation.v1",
        "validation_status": PASS_STATUS if not errors else "FAIL",
        "artifact_role": role,
        "artifact_sha256": actual_sha,
        "error_count": len(errors),
        "errors": errors,
        "a2_unlocked": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--policy", type=Path, default=POLICY_PATH)
    parser.add_argument("--expected-role")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)

    artifact = load_json(args.artifact)
    policy = load_json(args.policy)
    report = validate_artifact(
        artifact,
        policy=policy,
        expected_role=args.expected_role,
    )
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if report["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
