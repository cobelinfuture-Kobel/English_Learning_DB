#!/usr/bin/env python3
"""Validate A1FS-V1 canonical content production governance and CI wiring."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

POLICY_REL = Path("ulga/contracts/a1fs_v1_canonical_content_production_policy.json")
GOVERNANCE_REL = Path("docs/governance/A1FS_V1_CANONICAL_CONTENT_PRODUCTION_GOVERNANCE.md")
AGENTS_REL = Path("AGENTS.md")
TEST_REL = Path("tests/ulga/test_a1fs_v1_canonical_content_production_policy.py")
WORKFLOW_REL = Path(".github/workflows/a1fs-v1-canonical-content-governance.yml")
VALIDATOR_REL = Path("ulga/validators/validate_a1fs_v1_canonical_content_production_policy.py")
ARTIFACT_BUILDER_REL = Path("ulga/builders/build_a1fs_v1_policy_bound_content_artifact.py")
ARTIFACT_VALIDATOR_REL = Path("ulga/validators/validate_a1fs_v1_policy_bound_content_artifact.py")
ARTIFACT_SCHEMA_REL = Path("ulga/schemas/a1fs_v1_policy_bound_content_artifact.schema.json")
ARTIFACT_TEST_REL = Path("tests/ulga/test_a1fs_v1_policy_bound_content_artifact.py")

EXPECTED_TEXT_PIPELINE = (
    "AUTHORITY_QUERY",
    "CANDIDATE_JSON_BUILD",
    "SCHEMA_VALIDATION",
    "LEVEL_VALIDATION",
    "LANGUAGE_AUTHORITY_VALIDATION",
    "SEMANTIC_VALIDATION",
    "ANSWERABILITY_VALIDATION",
    "ADMISSION_DECISION",
    "APPROVED_CANONICAL_JSON",
    "FOUR_SKILL_PROJECTION_JSON",
    "RUNTIME_CONSUMPTION",
    "EXCEL_REFERENCE_EXPORT",
)

EXPECTED_MULTIMODAL_PIPELINE = (
    "APPROVED_CANONICAL_JSON",
    "VISUALIZABILITY_VALIDATION",
    "SCENE_CONTRACT_JSON",
    "IMAGE_GENERATION",
    "IMAGE_SCENE_CONSISTENCY_VALIDATION",
    "APPROVED_MEDIA_MANIFEST_JSON",
    "FOUR_SKILL_PROJECTION_JSON",
    "RUNTIME_CONSUMPTION",
    "EXCEL_REFERENCE_EXPORT",
)

EXPECTED_SKILLS = {"LISTENING", "SPEAKING", "READING", "WRITING"}
EXPECTED_IMAGE_GATES = {"SEMANTIC_PASS", "ANSWERABILITY_PASS", "VISUALIZABILITY_PASS"}
EXPECTED_PROJECTION_FIELDS = {
    "skill",
    "prompt",
    "response_mode",
    "support_level",
    "initiative_level",
    "scoring_contract",
    "evidence_level",
    "source_bindings",
    "content_identity",
}
EXPECTED_FORBIDDEN_FLOWS = {
    "EXCEL_TO_CANONICAL_JSON",
    "CSV_TO_CANONICAL_JSON",
    "PREVIEW_TO_CANONICAL_JSON",
    "GENERATED_IMAGE_TO_CANONICAL_CONTENT_AUTHORITY",
    "UNVALIDATED_CANDIDATE_TO_FOUR_SKILL_RUNTIME",
    "FAILED_CANDIDATE_TO_FOUR_SKILL_PROJECTION",
    "VALIDATOR_TO_CANDIDATE_CONTENT_GENERATION",
}
EXPECTED_ARTIFACT_ROLES = {
    "CANDIDATE_JSON",
    "APPROVED_CANONICAL_JSON",
    "FOUR_SKILL_PROJECTION_JSON",
    "APPROVED_MEDIA_MANIFEST_JSON",
    "EXCEL_REFERENCE_EXPORT_MANIFEST",
}
EXPECTED_BINDING_FIELDS = {
    "policy_id",
    "policy_schema_version",
    "policy_sha256",
    "artifact_role",
    "canonical_source",
    "four_skill_source",
    "excel_role",
    "excel_export_direction",
    "excel_writeback_allowed",
    "a2_unlocked",
}
EXPECTED_GUARD_PREFIXES = {
    "build_a1fs_v1_",
    "build_e4s_a1v1_",
    "build_a1_a1plus_",
}
EXPECTED_GUARD_MODES = {
    "POLICY_BOUND",
    "NOT_CONTENT_PRODUCER",
    "POLICY_ENFORCER",
}


class GovernanceValidationError(RuntimeError):
    """Raised when the committed governance contract is not enforceable."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise GovernanceValidationError(message)


def _object(value: Any, field: str) -> Mapping[str, Any]:
    _require(isinstance(value, Mapping), f"object_required:{field}")
    return value


def _sequence(value: Any, field: str) -> Sequence[Any]:
    _require(isinstance(value, list), f"list_required:{field}")
    return value


def load_policy(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), "policy_object_required")
    return value


def validate_policy(policy: Mapping[str, Any]) -> None:
    _require(
        policy.get("schema_version") == "a1fs.v1.canonical_content_production_policy.v1",
        "schema_version_invalid",
    )
    _require(
        policy.get("policy_id") == "A1FS_V1_CANONICAL_CONTENT_PRODUCTION_GOVERNANCE",
        "policy_id_invalid",
    )
    _require(policy.get("level_scope") == ["A1", "A1+"], "level_scope_invalid")
    _require(policy.get("a2_unlocked") is False, "a2_must_remain_locked")
    _require(policy.get("authoritative_source") == "APPROVED_CANONICAL_JSON", "canonical_source_invalid")
    _require(policy.get("four_skill_source") == "VALIDATED_APPROVED_JSON", "four_skill_source_invalid")

    candidate = _object(policy.get("candidate_generation"), "candidate_generation")
    _require(candidate.get("producer") == "BUILDER_OR_GENERATOR", "candidate_producer_invalid")
    _require(candidate.get("artifact") == "CANDIDATE_JSON", "candidate_artifact_invalid")
    _require(
        candidate.get("validator_may_generate_candidate_content") is False,
        "validator_candidate_generation_forbidden",
    )
    _require(candidate.get("learner_facing_before_admission") is False, "candidate_learners_forbidden")

    admission = _object(policy.get("validation_and_admission"), "validation_and_admission")
    _require(admission.get("validator_role") == "INDEPENDENT_GATE", "validator_role_invalid")
    _require(
        admission.get("admission_requires_all_required_validators_pass") is True,
        "admission_must_require_validator_pass",
    )
    _require(admission.get("approved_status") == "APPROVED", "approved_status_invalid")
    _require(
        set(_sequence(admission.get("rejected_statuses"), "rejected_statuses"))
        == {"REJECTED", "NEEDS_REVISION", "VALIDATION_FAILED"},
        "rejected_statuses_invalid",
    )

    excel = _object(policy.get("excel"), "excel")
    _require(excel.get("role") == "DERIVED_REFERENCE_ONLY", "excel_role_invalid")
    _require(excel.get("export_direction") == "JSON_TO_EXCEL_ONLY", "excel_direction_invalid")
    _require(excel.get("canonical_writeback_allowed") is False, "excel_writeback_forbidden")
    _require(
        excel.get("finding_resolution") == "REVISION_REQUEST_TO_CANDIDATE_JSON_PIPELINE",
        "excel_finding_resolution_invalid",
    )

    _require(
        tuple(_sequence(policy.get("text_pipeline"), "text_pipeline")) == EXPECTED_TEXT_PIPELINE,
        "text_pipeline_order_invalid",
    )
    _require(
        tuple(_sequence(policy.get("multimodal_pipeline"), "multimodal_pipeline"))
        == EXPECTED_MULTIMODAL_PIPELINE,
        "multimodal_pipeline_order_invalid",
    )

    image_gate = _object(policy.get("image_generation_gate"), "image_generation_gate")
    _require(
        set(_sequence(image_gate.get("required_statuses"), "image_generation_gate.required_statuses"))
        == EXPECTED_IMAGE_GATES,
        "image_generation_gate_invalid",
    )
    _require(
        image_gate.get("learner_facing_media_requires") == "IMAGE_SCENE_CONSISTENCY_PASS",
        "image_admission_gate_invalid",
    )

    _require(
        set(_sequence(policy.get("four_skill_projections"), "four_skill_projections"))
        == EXPECTED_SKILLS,
        "four_skill_projection_set_invalid",
    )
    _require(
        set(_sequence(policy.get("required_projection_fields"), "required_projection_fields"))
        == EXPECTED_PROJECTION_FIELDS,
        "required_projection_fields_invalid",
    )
    _require(
        set(_sequence(policy.get("forbidden_flows"), "forbidden_flows"))
        == EXPECTED_FORBIDDEN_FLOWS,
        "forbidden_flows_invalid",
    )

    binding = _object(policy.get("artifact_binding"), "artifact_binding")
    _require(
        binding.get("schema_version") == "a1fs.v1.policy_bound_content_artifact.v1",
        "artifact_binding_schema_invalid",
    )
    _require(binding.get("binding_field") == "content_governance", "artifact_binding_field_invalid")
    _require(binding.get("artifact_digest_field") == "artifact_sha256", "artifact_digest_field_invalid")
    _require(
        set(_sequence(binding.get("artifact_roles"), "artifact_binding.artifact_roles"))
        == EXPECTED_ARTIFACT_ROLES,
        "artifact_roles_invalid",
    )
    _require(
        set(_sequence(binding.get("required_binding_fields"), "artifact_binding.required_binding_fields"))
        == EXPECTED_BINDING_FIELDS,
        "artifact_binding_fields_invalid",
    )
    _require(binding.get("builder") == ARTIFACT_BUILDER_REL.as_posix(), "artifact_builder_path_invalid")
    _require(binding.get("validator") == ARTIFACT_VALIDATOR_REL.as_posix(), "artifact_validator_path_invalid")
    _require(binding.get("schema") == ARTIFACT_SCHEMA_REL.as_posix(), "artifact_schema_path_invalid")
    _require(binding.get("tests") == ARTIFACT_TEST_REL.as_posix(), "artifact_tests_path_invalid")

    guard = _object(policy.get("builder_change_guard"), "builder_change_guard")
    _require(
        set(_sequence(guard.get("protected_filename_prefixes"), "builder_change_guard.protected_filename_prefixes"))
        == EXPECTED_GUARD_PREFIXES,
        "builder_guard_prefixes_invalid",
    )
    _require(guard.get("required_mode_field") == "A1FS_CONTENT_POLICY_MODE", "builder_guard_mode_field_invalid")
    _require(
        set(_sequence(guard.get("allowed_modes"), "builder_change_guard.allowed_modes"))
        == EXPECTED_GUARD_MODES,
        "builder_guard_modes_invalid",
    )
    _require(
        guard.get("exemption_field") == "A1FS_CONTENT_POLICY_EXEMPTION",
        "builder_guard_exemption_field_invalid",
    )
    _require(
        guard.get("policy_bound_import_marker") == "build_a1fs_v1_policy_bound_content_artifact",
        "builder_guard_import_marker_invalid",
    )
    calls = _sequence(guard.get("required_transition_calls"), "builder_change_guard.required_transition_calls")
    _require(
        set(calls)
        == {
            "build_candidate(",
            "admit_candidate(",
            "build_four_skill_projection(",
            "build_approved_media_manifest(",
            "build_excel_reference_manifest(",
        },
        "builder_guard_transition_calls_invalid",
    )

    enforcement = _object(policy.get("enforcement"), "enforcement")
    expected_enforcement = {
        "governance_document": GOVERNANCE_REL.as_posix(),
        "agent_entrypoint": AGENTS_REL.as_posix(),
        "validator": VALIDATOR_REL.as_posix(),
        "tests": TEST_REL.as_posix(),
        "artifact_builder": ARTIFACT_BUILDER_REL.as_posix(),
        "artifact_validator": ARTIFACT_VALIDATOR_REL.as_posix(),
        "artifact_schema": ARTIFACT_SCHEMA_REL.as_posix(),
        "artifact_tests": ARTIFACT_TEST_REL.as_posix(),
        "workflow": WORKFLOW_REL.as_posix(),
    }
    _require(dict(enforcement) == expected_enforcement, "enforcement_paths_invalid")


def is_protected_builder(path: str, policy: Mapping[str, Any]) -> bool:
    relative = Path(path)
    if relative.parent.as_posix() != "ulga/builders" or relative.suffix != ".py":
        return False
    prefixes = policy["builder_change_guard"]["protected_filename_prefixes"]
    return any(relative.name.startswith(prefix) for prefix in prefixes)


def validate_builder_source_binding(
    *,
    path: str,
    source: str,
    policy: Mapping[str, Any],
) -> None:
    if not is_protected_builder(path, policy):
        return
    guard = policy["builder_change_guard"]
    mode_field = guard["required_mode_field"]
    match = re.search(
        rf'(?m)^\s*{re.escape(mode_field)}\s*=\s*["\']([^"\']+)["\']\s*$',
        source,
    )
    _require(match is not None, f"builder_policy_mode_missing:{path}")
    mode = match.group(1)
    _require(mode in guard["allowed_modes"], f"builder_policy_mode_invalid:{path}:{mode}")

    if mode == "POLICY_BOUND":
        _require(
            guard["policy_bound_import_marker"] in source,
            f"policy_bound_builder_import_missing:{path}",
        )
        _require(
            any(marker in source for marker in guard["required_transition_calls"]),
            f"policy_bound_builder_transition_missing:{path}",
        )
    elif mode == "NOT_CONTENT_PRODUCER":
        exemption = guard["exemption_field"]
        exemption_match = re.search(
            rf'(?m)^\s*{re.escape(exemption)}\s*=\s*["\']([^"\']+)["\']\s*$',
            source,
        )
        _require(
            exemption_match is not None and exemption_match.group(1).strip(),
            f"builder_policy_exemption_missing:{path}",
        )
    elif mode == "POLICY_ENFORCER":
        _require(
            Path(path).as_posix() == ARTIFACT_BUILDER_REL.as_posix(),
            f"policy_enforcer_path_invalid:{path}",
        )


def changed_paths(repo_root: Path, base_ref: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base_ref}...HEAD"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    _require(result.returncode == 0, f"git_diff_failed:{result.stderr.strip()}")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def validate_changed_builders(
    repo_root: Path,
    *,
    policy: Mapping[str, Any],
    paths: Sequence[str],
) -> list[str]:
    checked: list[str] = []
    for path in paths:
        if not is_protected_builder(path, policy):
            continue
        source_path = repo_root / path
        _require(source_path.is_file(), f"changed_builder_missing:{path}")
        validate_builder_source_binding(
            path=path,
            source=source_path.read_text(encoding="utf-8"),
            policy=policy,
        )
        checked.append(path)
    return checked


def validate_repository(
    repo_root: Path,
    *,
    changed_from: str | None = None,
) -> dict[str, Any]:
    required_paths = (
        POLICY_REL,
        GOVERNANCE_REL,
        AGENTS_REL,
        VALIDATOR_REL,
        TEST_REL,
        WORKFLOW_REL,
        ARTIFACT_BUILDER_REL,
        ARTIFACT_VALIDATOR_REL,
        ARTIFACT_SCHEMA_REL,
        ARTIFACT_TEST_REL,
    )
    for relative in required_paths:
        _require((repo_root / relative).is_file(), f"required_file_missing:{relative.as_posix()}")

    policy = load_policy(repo_root / POLICY_REL)
    validate_policy(policy)

    governance = (repo_root / GOVERNANCE_REL).read_text(encoding="utf-8")
    for marker in (
        "CANONICAL_SOURCE = APPROVED_CANONICAL_JSON",
        "FOUR_SKILL_SOURCE = VALIDATED_APPROVED_JSON",
        "EXCEL_ROLE = DERIVED_REFERENCE_ONLY",
        "EXCEL_TO_CANONICAL_WRITEBACK = FORBIDDEN",
        "POLICY_BOUND_ARTIFACT_REQUIRED = TRUE",
    ):
        _require(marker in governance, f"governance_marker_missing:{marker}")

    agents = (repo_root / AGENTS_REL).read_text(encoding="utf-8")
    for marker in (
        GOVERNANCE_REL.as_posix(),
        VALIDATOR_REL.as_posix(),
        ARTIFACT_BUILDER_REL.as_posix(),
        ARTIFACT_VALIDATOR_REL.as_posix(),
    ):
        _require(marker in agents, f"agents_reference_missing:{marker}")

    schema = json.loads((repo_root / ARTIFACT_SCHEMA_REL).read_text(encoding="utf-8"))
    _require(schema.get("additionalProperties") is False, "artifact_schema_must_be_closed")
    _require(
        set(schema.get("required", []))
        == {
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
        },
        "artifact_schema_required_fields_invalid",
    )

    workflow = (repo_root / WORKFLOW_REL).read_text(encoding="utf-8")
    for marker in (
        POLICY_REL.as_posix(),
        GOVERNANCE_REL.as_posix(),
        AGENTS_REL.as_posix(),
        VALIDATOR_REL.as_posix(),
        TEST_REL.as_posix(),
        ARTIFACT_BUILDER_REL.as_posix(),
        ARTIFACT_VALIDATOR_REL.as_posix(),
        ARTIFACT_SCHEMA_REL.as_posix(),
        ARTIFACT_TEST_REL.as_posix(),
        "python ulga/validators/validate_a1fs_v1_canonical_content_production_policy.py",
        "python -m pytest -q tests/ulga/test_a1fs_v1_canonical_content_production_policy.py",
        "python -m pytest -q tests/ulga/test_a1fs_v1_policy_bound_content_artifact.py",
        "--changed-from",
    ):
        _require(marker in workflow, f"workflow_enforcement_missing:{marker}")

    checked_builders: list[str] = []
    if changed_from:
        checked_builders = validate_changed_builders(
            repo_root,
            policy=policy,
            paths=changed_paths(repo_root, changed_from),
        )

    return {
        "policy_id": policy["policy_id"],
        "schema_version": policy["schema_version"],
        "validation_status": "PASS_A1FS_V1_CANONICAL_CONTENT_PRODUCTION_GOVERNANCE",
        "canonical_source": policy["authoritative_source"],
        "four_skill_source": policy["four_skill_source"],
        "excel_role": policy["excel"]["role"],
        "excel_writeback_allowed": policy["excel"]["canonical_writeback_allowed"],
        "policy_bound_artifact_required": True,
        "artifact_roles": sorted(policy["artifact_binding"]["artifact_roles"]),
        "changed_builder_binding_check_count": len(checked_builders),
        "changed_builder_binding_checks": checked_builders,
        "a2_unlocked": policy["a2_unlocked"],
        "error_count": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--report", type=Path)
    parser.add_argument("--changed-from")
    args = parser.parse_args()

    report = validate_repository(
        args.repo_root.resolve(),
        changed_from=args.changed_from,
    )
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
