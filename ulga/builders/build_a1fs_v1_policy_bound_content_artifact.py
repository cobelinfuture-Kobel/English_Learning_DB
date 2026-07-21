#!/usr/bin/env python3
"""Create policy-bound A1FS-V1 content artifacts and enforce legal transitions."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
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

PASS_STATUS = "PASS"
HEX_DIGEST_LENGTH = 64
A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"


class ContentPolicyBuildError(RuntimeError):
    """Raised when a builder attempts an illegal content transition."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def load_policy(path: Path = POLICY_PATH) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ContentPolicyBuildError("policy_object_required")
    return value


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ContentPolicyBuildError(message)


def _policy_digest(policy: Mapping[str, Any]) -> str:
    return digest(policy)


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == HEX_DIGEST_LENGTH
        and all(char in "0123456789abcdef" for char in value)
    )


def _normalize_level_scope(level_scope: Sequence[str], policy: Mapping[str, Any]) -> list[str]:
    _require(
        isinstance(level_scope, Sequence) and not isinstance(level_scope, (str, bytes)),
        "level_scope_list_required",
    )
    values = list(level_scope)
    _require(values, "level_scope_required")
    _require(len(values) == len(set(values)), "duplicate_level_scope")
    allowed = list(policy.get("level_scope", []))
    _require(all(value in allowed for value in values), "level_scope_outside_a1_a1plus")
    return [value for value in allowed if value in values]


def _normalize_source_bindings(source_bindings: Mapping[str, Any]) -> dict[str, Any]:
    _require(isinstance(source_bindings, Mapping), "source_bindings_object_required")
    value = deepcopy(dict(source_bindings))
    _require(bool(value), "source_bindings_required")
    return value


def _normalize_receipts(receipts: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    _require(
        isinstance(receipts, Sequence) and not isinstance(receipts, (str, bytes)),
        "validation_receipts_list_required",
    )
    rows: list[dict[str, Any]] = []
    for index, receipt in enumerate(receipts):
        _require(isinstance(receipt, Mapping), f"validation_receipt_object_required:{index}")
        validator_id = receipt.get("validator_id")
        status = receipt.get("status")
        receipt_sha256 = receipt.get("receipt_sha256")
        _require(isinstance(validator_id, str) and validator_id.strip(), f"validator_id_required:{index}")
        _require(status == PASS_STATUS, f"validation_receipt_not_pass:{index}")
        _require(
            isinstance(receipt_sha256, str)
            and len(receipt_sha256) == HEX_DIGEST_LENGTH
            and all(char in "0123456789abcdef" for char in receipt_sha256),
            f"validation_receipt_sha256_invalid:{index}",
        )
        rows.append(
            {
                "validator_id": validator_id.strip(),
                "status": PASS_STATUS,
                "receipt_sha256": receipt_sha256,
            }
        )
    return rows


def _governance_binding(policy: Mapping[str, Any], artifact_role: str) -> dict[str, Any]:
    binding = policy.get("artifact_binding", {})
    roles = binding.get("artifact_roles", [])
    _require(artifact_role in roles, "artifact_role_not_allowed_by_policy")
    return {
        "policy_id": policy["policy_id"],
        "policy_schema_version": policy["schema_version"],
        "policy_sha256": _policy_digest(policy),
        "artifact_role": artifact_role,
        "canonical_source": policy["authoritative_source"],
        "four_skill_source": policy["four_skill_source"],
        "excel_role": policy["excel"]["role"],
        "excel_export_direction": policy["excel"]["export_direction"],
        "excel_writeback_allowed": policy["excel"]["canonical_writeback_allowed"],
        "a2_unlocked": policy["a2_unlocked"],
    }


def _finalize(core: Mapping[str, Any], policy: Mapping[str, Any]) -> dict[str, Any]:
    value = deepcopy(dict(core))
    value["content_governance"] = _governance_binding(policy, str(value["artifact_role"]))
    value["artifact_sha256"] = digest(value)
    return value


def verify_artifact_digest(artifact: Mapping[str, Any]) -> str:
    actual = artifact.get("artifact_sha256")
    _require(
        isinstance(actual, str)
        and len(actual) == HEX_DIGEST_LENGTH
        and all(char in "0123456789abcdef" for char in actual),
        "artifact_sha256_invalid",
    )
    expected = digest({key: value for key, value in artifact.items() if key != "artifact_sha256"})
    _require(actual == expected, "artifact_sha256_mismatch")
    return actual


def _require_bound_source(
    artifact: Mapping[str, Any],
    *,
    expected_role: str,
    policy: Mapping[str, Any],
) -> None:
    _require(isinstance(artifact, Mapping), "source_artifact_object_required")
    _require(artifact.get("schema_version") == ARTIFACT_SCHEMA_VERSION, "source_schema_version_invalid")
    _require(artifact.get("artifact_role") == expected_role, "illegal_source_artifact_role")
    verify_artifact_digest(artifact)
    governance = artifact.get("content_governance")
    _require(isinstance(governance, Mapping), "source_governance_binding_required")
    _require(governance.get("policy_id") == policy.get("policy_id"), "source_policy_id_mismatch")
    _require(
        governance.get("policy_schema_version") == policy.get("schema_version"),
        "source_policy_schema_mismatch",
    )
    _require(governance.get("policy_sha256") == _policy_digest(policy), "source_policy_sha256_mismatch")
    _require(governance.get("a2_unlocked") is False, "source_a2_unlock_detected")


def build_candidate(
    *,
    payload: Mapping[str, Any],
    producer_id: str,
    level_scope: Sequence[str],
    source_bindings: Mapping[str, Any],
    policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    policy = deepcopy(dict(policy or load_policy()))
    _require(isinstance(payload, Mapping), "candidate_payload_object_required")
    _require(isinstance(producer_id, str) and producer_id.strip(), "producer_id_required")
    core = {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "artifact_role": CANDIDATE_ROLE,
        "producer_id": producer_id.strip(),
        "level_scope": _normalize_level_scope(level_scope, policy),
        "source_bindings": _normalize_source_bindings(source_bindings),
        "validation_receipts": [],
        "admission": {"status": "PENDING_VALIDATION", "decision_ref": None},
        "learner_facing": False,
        "payload": deepcopy(dict(payload)),
    }
    return _finalize(core, policy)


def admit_candidate(
    candidate: Mapping[str, Any],
    *,
    validation_receipts: Sequence[Mapping[str, Any]],
    decision_ref: str,
    producer_id: str,
    policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    policy = deepcopy(dict(policy or load_policy()))
    _require_bound_source(candidate, expected_role=CANDIDATE_ROLE, policy=policy)
    receipts = _normalize_receipts(validation_receipts)
    _require(receipts, "approved_artifact_requires_validation_receipts")
    _require(isinstance(decision_ref, str) and decision_ref.strip(), "decision_ref_required")
    _require(isinstance(producer_id, str) and producer_id.strip(), "producer_id_required")
    core = {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "artifact_role": APPROVED_ROLE,
        "producer_id": producer_id.strip(),
        "level_scope": list(candidate["level_scope"]),
        "source_bindings": {
            "candidate_artifact_sha256": candidate["artifact_sha256"],
            "candidate_source_bindings": deepcopy(dict(candidate["source_bindings"])),
        },
        "validation_receipts": receipts,
        "admission": {"status": "APPROVED", "decision_ref": decision_ref.strip()},
        "learner_facing": False,
        "payload": deepcopy(dict(candidate["payload"])),
    }
    return _finalize(core, policy)


def build_four_skill_projection(
    approved: Mapping[str, Any],
    *,
    skill: str,
    projection_payload: Mapping[str, Any],
    producer_id: str,
    policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    policy = deepcopy(dict(policy or load_policy()))
    _require_bound_source(approved, expected_role=APPROVED_ROLE, policy=policy)
    _require(isinstance(projection_payload, Mapping), "projection_payload_object_required")
    normalized_skill = str(skill).upper()
    _require(normalized_skill in policy.get("four_skill_projections", []), "projection_skill_invalid")
    payload = deepcopy(dict(projection_payload))
    required = set(policy.get("required_projection_fields", []))
    _require(required.issubset(payload), "projection_required_fields_missing")
    _require(str(payload.get("skill")).upper() == normalized_skill, "projection_skill_binding_mismatch")
    _require(isinstance(payload.get("prompt"), str) and payload["prompt"].strip(), "projection_prompt_required")
    _require(isinstance(payload.get("scoring_contract"), Mapping), "projection_scoring_contract_required")
    _require(isinstance(payload.get("source_bindings"), Mapping), "projection_source_bindings_required")
    _require(isinstance(producer_id, str) and producer_id.strip(), "producer_id_required")
    core = {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "artifact_role": PROJECTION_ROLE,
        "producer_id": producer_id.strip(),
        "level_scope": list(approved["level_scope"]),
        "source_bindings": {
            "approved_canonical_artifact_sha256": approved["artifact_sha256"],
            "approved_content_identity": deepcopy(payload["content_identity"]),
        },
        "validation_receipts": deepcopy(list(approved["validation_receipts"])),
        "admission": {"status": "APPROVED_SOURCE_BOUND", "decision_ref": approved["admission"]["decision_ref"]},
        "learner_facing": True,
        "payload": payload,
    }
    return _finalize(core, policy)


def build_approved_media_manifest(
    approved: Mapping[str, Any],
    *,
    media_payload: Mapping[str, Any],
    scene_consistency_receipt: Mapping[str, Any],
    producer_id: str,
    policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    policy = deepcopy(dict(policy or load_policy()))
    _require_bound_source(approved, expected_role=APPROVED_ROLE, policy=policy)
    _require(isinstance(media_payload, Mapping), "media_payload_object_required")
    payload = deepcopy(dict(media_payload))
    _require(_is_sha256(payload.get("scene_contract_sha256")), "scene_contract_sha256_invalid")
    _require(_is_sha256(payload.get("image_sha256")), "image_sha256_invalid")
    expected_status = policy["image_generation_gate"]["learner_facing_media_requires"]
    _require(
        payload.get("image_scene_consistency_status") == expected_status,
        "image_scene_consistency_pass_required",
    )
    receipts = _normalize_receipts([scene_consistency_receipt])
    _require(isinstance(producer_id, str) and producer_id.strip(), "producer_id_required")
    core = {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "artifact_role": MEDIA_ROLE,
        "producer_id": producer_id.strip(),
        "level_scope": list(approved["level_scope"]),
        "source_bindings": {
            "approved_canonical_artifact_sha256": approved["artifact_sha256"],
            "scene_contract_sha256": payload.get("scene_contract_sha256"),
        },
        "validation_receipts": receipts,
        "admission": {"status": "APPROVED_MEDIA", "decision_ref": approved["admission"]["decision_ref"]},
        "learner_facing": True,
        "payload": payload,
    }
    return _finalize(core, policy)


def build_excel_reference_manifest(
    source_json_artifact: Mapping[str, Any],
    *,
    workbook_filename: str,
    workbook_sha256: str,
    producer_id: str,
    policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    policy = deepcopy(dict(policy or load_policy()))
    role = source_json_artifact.get("artifact_role")
    _require(role in {APPROVED_ROLE, PROJECTION_ROLE, MEDIA_ROLE}, "excel_source_must_be_approved_json")
    _require_bound_source(source_json_artifact, expected_role=str(role), policy=policy)
    _require(
        isinstance(workbook_filename, str)
        and workbook_filename.lower().endswith(".xlsx")
        and Path(workbook_filename).name == workbook_filename,
        "excel_filename_invalid",
    )
    _require(
        isinstance(workbook_sha256, str)
        and len(workbook_sha256) == HEX_DIGEST_LENGTH
        and all(char in "0123456789abcdef" for char in workbook_sha256),
        "excel_workbook_sha256_invalid",
    )
    _require(isinstance(producer_id, str) and producer_id.strip(), "producer_id_required")
    core = {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "artifact_role": EXCEL_ROLE,
        "producer_id": producer_id.strip(),
        "level_scope": list(source_json_artifact["level_scope"]),
        "source_bindings": {
            "source_json_artifact_sha256": source_json_artifact["artifact_sha256"],
            "source_json_artifact_role": role,
        },
        "validation_receipts": [],
        "admission": {"status": "DERIVED_REFERENCE_ONLY", "decision_ref": None},
        "learner_facing": False,
        "payload": {
            "workbook_filename": workbook_filename,
            "workbook_sha256": workbook_sha256,
            "role": policy["excel"]["role"],
            "export_direction": policy["excel"]["export_direction"],
            "canonical_writeback_allowed": policy["excel"]["canonical_writeback_allowed"],
            "source_artifact_role": role,
        },
    }
    return _finalize(core, policy)
