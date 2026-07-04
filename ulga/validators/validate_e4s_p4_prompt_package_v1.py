#!/usr/bin/env python3
"""Validate E4S P4 sample speaking prompt records and role-play prompt packages.

Scope:
- Contract coverage for E4S-P4-S2 prompt records.
- Contract coverage for E4S-P4-S3 role-play prompt packages.
- Candidate boundary rules for E4S-P4-S4.
- Validation target: E4S-P4-S5 sample prompt/package artifact.

This validator is intentionally offline and data-only. It does not generate prompts,
render role-play activities, call ASR, score speech, use audio, use UI runtime, or
touch learner-state.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ALLOWED_SOURCE_FAMILIES = {"AUX-S4", "AUX-S5", "AUX-S7"}

ALLOWED_PROMPT_TYPES = {
    "functional_response",
    "substitution_prompt",
    "role_response",
    "role_play_turn",
    "story_retell",
    "context_question",
    "oral_sentence_builder",
}

ALLOWED_SPEAKING_MODES = {
    "repeat_oral",
    "read_aloud",
    "guided_response",
    "short_answer",
    "substitution_drill",
    "role_play",
    "retell",
    "sentence_building",
}

ALLOWED_PACKAGE_TYPES = {
    "role_play_package",
    "role_response_package",
    "story_retell_package",
    "context_question_package",
    "substitution_role_play_package",
}

ALLOWED_PRACTICE_MODES = {
    "guided_role_play",
    "one_role_response",
    "teacher_student_role_play",
    "parent_child_role_play",
    "story_retell",
    "context_qna",
    "substitution_drill",
}

ALLOWED_AUTHORITY_STATUSES = {"candidate_only", "reviewed_candidate", "rejected"}
ALLOWED_REVIEW_STATUSES = {"pending", "reviewed", "needs_revision", "rejected"}

ALLOWED_APPLIES_TO_TYPES = {"speaking_prompt_record", "role_play_prompt_package"}
ALLOWED_CANDIDATE_ORIGINS = {
    "source_extracted",
    "derived_from_source",
    "generated_candidate",
    "mixed_source_and_generated",
    "manual_reviewed_candidate",
}
ALLOWED_DERIVATION_TYPES = {
    "none",
    "role_label_inferred",
    "turn_sequence_derived",
    "functional_sentence_to_role_prompt",
    "story_dialogue_to_prompt",
    "story_dialogue_to_package",
    "generated_variant",
    "generated_context_fill",
    "mixed_derivation",
}
ALLOWED_SOURCE_GROUNDING_STATUSES = {
    "source_grounded",
    "partially_source_grounded",
    "derived_with_trace",
    "generated_with_basis",
    "generated_without_sufficient_evidence",
    "missing_trace",
}
ALLOWED_PROMOTION_STATUSES = {
    "not_promoted",
    "promotion_blocked",
    "eligible_for_review",
    "reviewed_candidate_ready",
    "rejected",
}

BLOCKED_V1_STATUSES = {
    "authority_promoted",
    "learner_facing_final",
    "production_ready",
    "final_dialogue_authority",
}

GLOBAL_FALSE_CAPABILITIES = {
    "implements_generator",
    "implements_validator",
    "implements_renderer",
    "requires_recording",
    "requires_asr",
    "requires_scoring",
    "requires_audio",
    "requires_ui_renderer",
    "requires_learner_state",
    "claims_final_authority",
    "claims_production_ready",
    "claims_learner_facing_final",
}

PACKAGE_FALSE_CONSTRAINTS = {
    "requires_recording",
    "requires_asr",
    "requires_scoring",
    "requires_audio",
    "requires_ui_renderer",
}

PROMPT_REQUIRED_FIELDS = {
    "prompt_id",
    "source_family",
    "source_id",
    "source_trace",
    "prompt_type",
    "speaking_mode",
    "speaker_roles",
    "theme",
    "level_estimate",
    "input_text",
    "prompt_text",
    "expected_response_shape",
    "allowed_variation",
    "blocked_generation_behavior",
    "authority_status",
    "review_status",
    "validator_requirements",
    "candidate_boundary",
}

PACKAGE_REQUIRED_FIELDS = {
    "package_id",
    "package_type",
    "source_family",
    "source_ids",
    "source_trace",
    "scenario",
    "roles",
    "turn_sequence",
    "prompt_refs",
    "package_flow",
    "constraints",
    "authority_status",
    "review_status",
    "validator_requirements",
    "candidate_boundary",
}

BOUNDARY_REQUIRED_FIELDS = {
    "candidate_id",
    "applies_to_id",
    "applies_to_type",
    "source_family",
    "candidate_origin",
    "derivation_type",
    "generated",
    "source_grounding_status",
    "authority_status",
    "review_status",
    "promotion_status",
    "allowed_next_statuses",
    "blocked_next_statuses",
    "promotion_gate_results",
    "blocked_reasons",
}


class ValidationContext:
    """Collect blocking errors and warnings with stable codes."""

    def __init__(self) -> None:
        self.blocking_errors: list[dict[str, Any]] = []
        self.warnings: list[dict[str, Any]] = []

    def fail(self, code: str, path: str, message: str) -> None:
        self.blocking_errors.append({"code": code, "path": path, "message": message})

    def warn(self, code: str, path: str, message: str) -> None:
        self.warnings.append({"code": code, "path": path, "message": message})

    @property
    def passed(self) -> bool:
        return not self.blocking_errors


def is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def require_fields(ctx: ValidationContext, obj: dict[str, Any], required: set[str], path: str) -> None:
    for field in sorted(required):
        if field not in obj:
            ctx.fail("missing_required_field", f"{path}.{field}", f"Missing required field: {field}")


def require_bool_value(
    ctx: ValidationContext,
    obj: dict[str, Any],
    key: str,
    expected: bool,
    path: str,
) -> None:
    value = obj.get(key)
    if value is not expected:
        ctx.fail(
            "invalid_boolean_capability_flag",
            f"{path}.{key}",
            f"Expected {key}={expected!r}, got {value!r}",
        )


def validate_source_trace(ctx: ValidationContext, trace: Any, path: str, generated_expected: bool | None = None) -> None:
    if not isinstance(trace, dict):
        ctx.fail("source_trace_not_object", path, "source_trace must be an object.")
        return

    if not is_non_empty_string(trace.get("source_type")):
        ctx.fail("missing_source_trace_type", f"{path}.source_type", "source_trace.source_type is required.")

    # Prompt records use source_record_id, packages use source_record_ids. At least one is expected.
    has_single_record = is_non_empty_string(trace.get("source_record_id"))
    has_many_records = isinstance(trace.get("source_record_ids"), list) and bool(trace.get("source_record_ids"))
    if not (has_single_record or has_many_records):
        ctx.fail(
            "missing_source_record_reference",
            path,
            "source_trace must include source_record_id or non-empty source_record_ids.",
        )

    evidence = trace.get("evidence_text", None)
    evidences = trace.get("evidence_texts", None)
    has_evidence_text = is_non_empty_string(evidence)
    has_evidence_texts = isinstance(evidences, list) and any(is_non_empty_string(item) for item in evidences)
    if not (has_evidence_text or has_evidence_texts):
        ctx.fail("missing_source_evidence", path, "source_trace must include evidence_text or evidence_texts.")

    if generated_expected is not None and trace.get("generated") is not generated_expected:
        ctx.fail(
            "generated_trace_mismatch",
            f"{path}.generated",
            f"Expected generated={generated_expected!r} for this source trace.",
        )


def validate_boundary(
    ctx: ValidationContext,
    boundary: Any,
    *,
    applies_to_id: str,
    applies_to_type: str,
    source_family: str,
    path: str,
) -> None:
    if not isinstance(boundary, dict):
        ctx.fail("candidate_boundary_not_object", path, "candidate_boundary must be an object.")
        return

    require_fields(ctx, boundary, BOUNDARY_REQUIRED_FIELDS, path)

    if boundary.get("applies_to_id") != applies_to_id:
        ctx.fail(
            "boundary_applies_to_id_mismatch",
            f"{path}.applies_to_id",
            f"Boundary applies_to_id must match {applies_to_id}.",
        )

    if boundary.get("applies_to_type") != applies_to_type:
        ctx.fail(
            "boundary_applies_to_type_mismatch",
            f"{path}.applies_to_type",
            f"Boundary applies_to_type must be {applies_to_type}.",
        )

    if boundary.get("source_family") != source_family:
        ctx.fail(
            "boundary_source_family_mismatch",
            f"{path}.source_family",
            f"Boundary source_family must match {source_family}.",
        )

    if boundary.get("applies_to_type") not in ALLOWED_APPLIES_TO_TYPES:
        ctx.fail("invalid_applies_to_type", f"{path}.applies_to_type", "Unsupported applies_to_type.")

    if boundary.get("candidate_origin") not in ALLOWED_CANDIDATE_ORIGINS:
        ctx.fail("invalid_candidate_origin", f"{path}.candidate_origin", "Unsupported candidate_origin.")

    if boundary.get("derivation_type") not in ALLOWED_DERIVATION_TYPES:
        ctx.fail("invalid_derivation_type", f"{path}.derivation_type", "Unsupported derivation_type.")

    if boundary.get("source_grounding_status") not in ALLOWED_SOURCE_GROUNDING_STATUSES:
        ctx.fail(
            "invalid_source_grounding_status",
            f"{path}.source_grounding_status",
            "Unsupported source_grounding_status.",
        )

    if boundary.get("authority_status") not in ALLOWED_AUTHORITY_STATUSES:
        ctx.fail("invalid_boundary_authority_status", f"{path}.authority_status", "Unsupported authority_status.")

    if boundary.get("review_status") not in ALLOWED_REVIEW_STATUSES:
        ctx.fail("invalid_boundary_review_status", f"{path}.review_status", "Unsupported review_status.")

    if boundary.get("promotion_status") not in ALLOWED_PROMOTION_STATUSES:
        ctx.fail("invalid_promotion_status", f"{path}.promotion_status", "Unsupported promotion_status.")

    allowed_next = boundary.get("allowed_next_statuses")
    blocked_next = boundary.get("blocked_next_statuses")
    if not isinstance(allowed_next, list):
        ctx.fail("allowed_next_statuses_not_list", f"{path}.allowed_next_statuses", "Must be a list.")
    if not isinstance(blocked_next, list):
        ctx.fail("blocked_next_statuses_not_list", f"{path}.blocked_next_statuses", "Must be a list.")
    elif not BLOCKED_V1_STATUSES.intersection(set(blocked_next)):
        ctx.fail(
            "missing_blocked_v1_statuses",
            f"{path}.blocked_next_statuses",
            "Boundary must explicitly block V1 final/promotion statuses.",
        )

    if source_family == "AUX-S7":
        if boundary.get("generated") is not True:
            ctx.fail("aux_s7_boundary_generated_required", f"{path}.generated", "AUX-S7 boundary must be generated.")
        if boundary.get("authority_status") != "candidate_only":
            ctx.fail(
                "aux_s7_boundary_candidate_only_required",
                f"{path}.authority_status",
                "AUX-S7 boundary authority_status must remain candidate_only.",
            )
        if boundary.get("promotion_status") != "promotion_blocked":
            ctx.fail(
                "aux_s7_promotion_block_required",
                f"{path}.promotion_status",
                "AUX-S7 promotion_status must be promotion_blocked in P4 V1.",
            )
        if isinstance(allowed_next, list) and "reviewed_candidate" in allowed_next:
            ctx.fail(
                "aux_s7_review_transition_block_required",
                f"{path}.allowed_next_statuses",
                "AUX-S7 default P4-S6 validator blocks reviewed_candidate transition.",
            )

    if boundary.get("generated") is True and boundary.get("candidate_origin") not in {
        "generated_candidate",
        "mixed_source_and_generated",
    }:
        ctx.fail(
            "generated_origin_mismatch",
            f"{path}.candidate_origin",
            "Generated boundary must use generated_candidate or mixed_source_and_generated origin.",
        )


def validate_expected_response_shape(ctx: ValidationContext, shape: Any, path: str) -> None:
    if not isinstance(shape, dict):
        ctx.fail("expected_response_shape_not_object", path, "expected_response_shape must be an object.")
        return

    for field in ["response_type", "min_words", "max_words", "required_elements", "example_responses"]:
        if field not in shape:
            ctx.fail("missing_response_shape_field", f"{path}.{field}", f"Missing {field}.")

    min_words = shape.get("min_words")
    max_words = shape.get("max_words")
    if not isinstance(min_words, int) or min_words < 0:
        ctx.fail("invalid_min_words", f"{path}.min_words", "min_words must be a non-negative integer.")
    if not isinstance(max_words, int) or max_words <= 0:
        ctx.fail("invalid_max_words", f"{path}.max_words", "max_words must be a positive integer.")
    if isinstance(min_words, int) and isinstance(max_words, int) and min_words > max_words:
        ctx.fail("min_words_gt_max_words", path, "min_words cannot exceed max_words.")

    if max_words and isinstance(max_words, int) and max_words > 20:
        ctx.warn("a1_prompt_max_words_high", f"{path}.max_words", "max_words may be high for PreA1/A1 oral practice.")


def validate_prompt_record(ctx: ValidationContext, prompt: Any, index: int) -> None:
    path = f"speaking_prompt_records[{index}]"
    if not isinstance(prompt, dict):
        ctx.fail("prompt_record_not_object", path, "Prompt record must be an object.")
        return

    require_fields(ctx, prompt, PROMPT_REQUIRED_FIELDS, path)

    prompt_id = prompt.get("prompt_id")
    source_family = prompt.get("source_family")

    if not is_non_empty_string(prompt_id):
        ctx.fail("invalid_prompt_id", f"{path}.prompt_id", "prompt_id must be a non-empty string.")

    if source_family not in ALLOWED_SOURCE_FAMILIES:
        ctx.fail("invalid_prompt_source_family", f"{path}.source_family", "Unsupported source_family.")

    if prompt.get("prompt_type") not in ALLOWED_PROMPT_TYPES:
        ctx.fail("invalid_prompt_type", f"{path}.prompt_type", "Unsupported prompt_type.")

    if prompt.get("speaking_mode") not in ALLOWED_SPEAKING_MODES:
        ctx.fail("invalid_speaking_mode", f"{path}.speaking_mode", "Unsupported speaking_mode.")

    if prompt.get("authority_status") not in ALLOWED_AUTHORITY_STATUSES:
        ctx.fail("invalid_prompt_authority_status", f"{path}.authority_status", "Unsupported authority_status.")

    if prompt.get("review_status") not in ALLOWED_REVIEW_STATUSES:
        ctx.fail("invalid_prompt_review_status", f"{path}.review_status", "Unsupported review_status.")

    generated_expected = True if source_family == "AUX-S7" else None
    validate_source_trace(ctx, prompt.get("source_trace"), f"{path}.source_trace", generated_expected)

    validate_expected_response_shape(
        ctx,
        prompt.get("expected_response_shape"),
        f"{path}.expected_response_shape",
    )

    if source_family == "AUX-S4" and prompt.get("prompt_type") == "role_play_turn":
        ctx.fail(
            "aux_s4_role_play_turn_blocked",
            f"{path}.prompt_type",
            "AUX-S4 may not use role_play_turn without explicit derived package handling.",
        )

    if source_family == "AUX-S5":
        roles = prompt.get("speaker_roles")
        if isinstance(roles, list) and len(roles) == 0:
            ctx.warn(
                "aux_s5_speaker_roles_empty",
                f"{path}.speaker_roles",
                "AUX-S5 prompt has no speaker roles; verify source has no roles.",
            )

    if source_family == "AUX-S7":
        if prompt.get("authority_status") != "candidate_only":
            ctx.fail(
                "aux_s7_prompt_candidate_only_required",
                f"{path}.authority_status",
                "AUX-S7 prompt must remain candidate_only.",
            )
        if prompt.get("review_status") != "pending":
            ctx.fail(
                "aux_s7_prompt_pending_required",
                f"{path}.review_status",
                "AUX-S7 prompt must start as pending in P4 V1.",
            )

    validate_boundary(
        ctx,
        prompt.get("candidate_boundary"),
        applies_to_id=str(prompt_id),
        applies_to_type="speaking_prompt_record",
        source_family=str(source_family),
        path=f"{path}.candidate_boundary",
    )


def validate_package(
    ctx: ValidationContext,
    package: Any,
    index: int,
    prompt_by_id: dict[str, dict[str, Any]],
) -> None:
    path = f"role_play_prompt_packages[{index}]"
    if not isinstance(package, dict):
        ctx.fail("package_not_object", path, "Package must be an object.")
        return

    require_fields(ctx, package, PACKAGE_REQUIRED_FIELDS, path)

    package_id = package.get("package_id")
    source_family = package.get("source_family")

    if not is_non_empty_string(package_id):
        ctx.fail("invalid_package_id", f"{path}.package_id", "package_id must be a non-empty string.")

    if source_family not in ALLOWED_SOURCE_FAMILIES:
        ctx.fail("invalid_package_source_family", f"{path}.source_family", "Unsupported source_family.")

    if package.get("package_type") not in ALLOWED_PACKAGE_TYPES:
        ctx.fail("invalid_package_type", f"{path}.package_type", "Unsupported package_type.")

    if package.get("authority_status") not in ALLOWED_AUTHORITY_STATUSES:
        ctx.fail("invalid_package_authority_status", f"{path}.authority_status", "Unsupported authority_status.")

    if package.get("review_status") not in ALLOWED_REVIEW_STATUSES:
        ctx.fail("invalid_package_review_status", f"{path}.review_status", "Unsupported review_status.")

    validate_source_trace(ctx, package.get("source_trace"), f"{path}.source_trace", True if source_family == "AUX-S7" else None)

    constraints = package.get("constraints")
    if not isinstance(constraints, dict):
        ctx.fail("package_constraints_not_object", f"{path}.constraints", "constraints must be an object.")
    else:
        require_bool_value(ctx, constraints, "prompt_only", True, f"{path}.constraints")
        for key in sorted(PACKAGE_FALSE_CONSTRAINTS):
            require_bool_value(ctx, constraints, key, False, f"{path}.constraints")

    package_flow = package.get("package_flow")
    if not isinstance(package_flow, dict):
        ctx.fail("package_flow_not_object", f"{path}.package_flow", "package_flow must be an object.")
    else:
        if package_flow.get("practice_mode") not in ALLOWED_PRACTICE_MODES:
            ctx.fail("invalid_practice_mode", f"{path}.package_flow.practice_mode", "Unsupported practice_mode.")
        turn_count = package_flow.get("turn_count")
        if not isinstance(turn_count, int) or turn_count <= 0:
            ctx.fail("invalid_turn_count", f"{path}.package_flow.turn_count", "turn_count must be a positive integer.")
        elif turn_count > 8:
            ctx.warn("a1_turn_count_high", f"{path}.package_flow.turn_count", "turn_count may be high for A1.")

    roles = package.get("roles")
    role_ids: set[str] = set()
    if not isinstance(roles, list):
        ctx.fail("roles_not_list", f"{path}.roles", "roles must be a list.")
    else:
        for role_index, role in enumerate(roles):
            role_path = f"{path}.roles[{role_index}]"
            if not isinstance(role, dict):
                ctx.fail("role_not_object", role_path, "Role must be an object.")
                continue
            role_id = role.get("role_id")
            if not is_non_empty_string(role_id):
                ctx.fail("missing_role_id", f"{role_path}.role_id", "role_id is required.")
            else:
                role_ids.add(role_id)

    if package.get("package_type") == "role_play_package" and len(role_ids) < 2:
        ctx.fail("role_play_package_requires_two_roles", f"{path}.roles", "role_play_package needs at least two roles.")

    turns = package.get("turn_sequence")
    if not isinstance(turns, list) or not turns:
        ctx.fail("turn_sequence_missing_or_empty", f"{path}.turn_sequence", "turn_sequence must be a non-empty list.")
    else:
        expected_indices = list(range(1, len(turns) + 1))
        actual_indices: list[int] = []
        for turn_index, turn in enumerate(turns):
            turn_path = f"{path}.turn_sequence[{turn_index}]"
            if not isinstance(turn, dict):
                ctx.fail("turn_not_object", turn_path, "Turn must be an object.")
                continue

            actual_indices.append(turn.get("turn_index"))
            speaker_role_id = turn.get("speaker_role_id")
            if turn.get("turn_type") != "narration" and speaker_role_id not in role_ids:
                ctx.fail(
                    "turn_speaker_role_missing",
                    f"{turn_path}.speaker_role_id",
                    f"speaker_role_id {speaker_role_id!r} must exist in roles.",
                )

            student_action = turn.get("student_action")
            prompt_ref = turn.get("prompt_ref")
            if student_action in {"answer", "choose_role_response", "retell", "substitute"} and not is_non_empty_string(prompt_ref):
                ctx.fail("learner_output_turn_missing_prompt_ref", f"{turn_path}.prompt_ref", "Learner-output turn needs prompt_ref.")

            if is_non_empty_string(prompt_ref) and prompt_ref not in prompt_by_id:
                ctx.fail("unknown_prompt_ref", f"{turn_path}.prompt_ref", f"prompt_ref {prompt_ref!r} not found.")

        if actual_indices != expected_indices:
            ctx.fail(
                "turn_indices_not_continuous",
                f"{path}.turn_sequence",
                f"turn_index values must be continuous {expected_indices}; got {actual_indices}.",
            )

    prompt_refs = package.get("prompt_refs")
    has_learner_output = False
    if not isinstance(prompt_refs, list) or not prompt_refs:
        ctx.fail("prompt_refs_missing_or_empty", f"{path}.prompt_refs", "prompt_refs must be a non-empty list.")
    else:
        for ref_index, prompt_ref_obj in enumerate(prompt_refs):
            ref_path = f"{path}.prompt_refs[{ref_index}]"
            if not isinstance(prompt_ref_obj, dict):
                ctx.fail("prompt_ref_not_object", ref_path, "prompt_ref entry must be an object.")
                continue

            ref_id = prompt_ref_obj.get("prompt_ref")
            if prompt_ref_obj.get("prompt_role") == "learner_output":
                has_learner_output = True

            if not is_non_empty_string(ref_id) or ref_id not in prompt_by_id:
                ctx.fail("unknown_package_prompt_ref", f"{ref_path}.prompt_ref", f"prompt_ref {ref_id!r} not found.")
            else:
                child = prompt_by_id[ref_id]
                if child.get("source_family") == "AUX-S7":
                    boundary = package.get("candidate_boundary", {})
                    if isinstance(boundary, dict) and boundary.get("generated") is not True:
                        ctx.fail(
                            "package_with_aux_s7_child_must_be_generated_or_mixed",
                            f"{path}.candidate_boundary.generated",
                            "Package containing AUX-S7 child prompt must carry generated/mixed boundary metadata.",
                        )

    if not has_learner_output:
        ctx.fail("package_missing_learner_output_prompt", f"{path}.prompt_refs", "Package needs at least one learner_output prompt.")

    if source_family == "AUX-S7":
        if package.get("authority_status") != "candidate_only":
            ctx.fail(
                "aux_s7_package_candidate_only_required",
                f"{path}.authority_status",
                "AUX-S7 package must remain candidate_only.",
            )
        scenario = package.get("scenario")
        if isinstance(scenario, dict) and scenario.get("source_grounded") is not False:
            ctx.fail(
                "aux_s7_package_not_source_grounded",
                f"{path}.scenario.source_grounded",
                "AUX-S7 generated package must not claim source_grounded=true.",
            )

    validate_boundary(
        ctx,
        package.get("candidate_boundary"),
        applies_to_id=str(package_id),
        applies_to_type="role_play_prompt_package",
        source_family=str(source_family),
        path=f"{path}.candidate_boundary",
    )


def validate_artifact(artifact: Any) -> dict[str, Any]:
    ctx = ValidationContext()

    if not isinstance(artifact, dict):
        ctx.fail("artifact_not_object", "$", "Artifact root must be a JSON object.")
        return build_report(ctx, {}, {}, {})

    if artifact.get("artifact_type") != "sample_prompt_package":
        ctx.fail("invalid_artifact_type", "artifact_type", "Expected artifact_type=sample_prompt_package.")

    if artifact.get("status") != "SAMPLE_IMPLEMENTED_CONTRACT_ONLY":
        ctx.fail("invalid_artifact_status", "status", "Expected SAMPLE_IMPLEMENTED_CONTRACT_ONLY.")

    constraints = artifact.get("scope_constraints")
    if not isinstance(constraints, dict):
        ctx.fail("scope_constraints_missing", "scope_constraints", "scope_constraints must be an object.")
    else:
        require_bool_value(ctx, constraints, "prompt_only", True, "scope_constraints")
        for key in sorted(GLOBAL_FALSE_CAPABILITIES):
            require_bool_value(ctx, constraints, key, False, "scope_constraints")

    policies = artifact.get("source_family_policy")
    if not isinstance(policies, dict):
        ctx.fail("source_family_policy_missing", "source_family_policy", "source_family_policy must be an object.")
    else:
        for family in sorted(ALLOWED_SOURCE_FAMILIES):
            if family not in policies:
                ctx.fail("missing_source_family_policy", f"source_family_policy.{family}", f"Missing policy for {family}.")

    prompts = artifact.get("speaking_prompt_records")
    if not isinstance(prompts, list) or not prompts:
        ctx.fail("speaking_prompt_records_missing", "speaking_prompt_records", "Must contain prompt records.")
        prompts = []

    for index, prompt in enumerate(prompts):
        validate_prompt_record(ctx, prompt, index)

    prompt_by_id = {
        prompt["prompt_id"]: prompt
        for prompt in prompts
        if isinstance(prompt, dict) and is_non_empty_string(prompt.get("prompt_id"))
    }

    packages = artifact.get("role_play_prompt_packages")
    if not isinstance(packages, list) or not packages:
        ctx.fail("role_play_prompt_packages_missing", "role_play_prompt_packages", "Must contain packages.")
        packages = []

    for index, package in enumerate(packages):
        validate_package(ctx, package, index, prompt_by_id)

    summary = artifact.get("readback_summary")
    validate_readback_summary(ctx, summary, prompts, packages)

    return build_report(ctx, artifact, prompt_by_id, packages)


def validate_readback_summary(
    ctx: ValidationContext,
    summary: Any,
    prompts: list[Any],
    packages: list[Any],
) -> None:
    if not isinstance(summary, dict):
        ctx.warn("readback_summary_missing", "readback_summary", "readback_summary is recommended.")
        return

    expected_counts = {
        "prompt_record_count": len(prompts),
        "package_count": len(packages),
    }
    for key, expected in expected_counts.items():
        if summary.get(key) != expected:
            ctx.fail("readback_summary_count_mismatch", f"readback_summary.{key}", f"Expected {expected}.")

    zero_claim_keys = [
        "records_claiming_asr",
        "records_claiming_scoring",
        "records_claiming_audio",
        "records_claiming_ui_renderer",
        "records_claiming_final_authority",
        "records_claiming_production_ready",
        "records_claiming_learner_facing_final",
    ]
    for key in zero_claim_keys:
        if summary.get(key) != 0:
            ctx.fail("forbidden_claim_count_nonzero", f"readback_summary.{key}", f"{key} must be 0.")


def build_report(
    ctx: ValidationContext,
    artifact: dict[str, Any],
    prompt_by_id: dict[str, dict[str, Any]],
    packages: Any,
) -> dict[str, Any]:
    return {
        "validator_id": "E4S_P4_S6_PROMPT_VALIDATOR_V1",
        "task_id": "E4S-P4-S6_PromptValidator_Implementation",
        "target_artifact_id": artifact.get("artifact_id") if isinstance(artifact, dict) else None,
        "result": "PASS" if ctx.passed else "FAIL",
        "blocking_error_count": len(ctx.blocking_errors),
        "warning_count": len(ctx.warnings),
        "blocking_errors": ctx.blocking_errors,
        "warnings": ctx.warnings,
        "coverage": {
            "prompt_records_seen": len(prompt_by_id),
            "packages_seen": len(packages) if isinstance(packages, list) else 0,
            "checks": [
                "p4_s2_prompt_record_required_fields",
                "p4_s3_package_required_fields",
                "p4_s4_candidate_boundary_required_fields",
                "source_family_policy",
                "aux_s4_no_original_dialogue_authority",
                "aux_s5_role_order_context_preservation",
                "aux_s7_generated_candidate_only",
                "prompt_only_v1_capability_boundary",
                "package_prompt_ref_integrity",
                "readback_summary_counts",
            ],
        },
    }


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate E4S P4 S5 sample prompt package artifact.")
    parser.add_argument(
        "--input",
        default="ulga/samples/e4s_p4_s5_sample_prompt_package_v1.json",
        help="Path to the S5 sample prompt package JSON artifact.",
    )
    parser.add_argument(
        "--report",
        default="ulga/reports/e4s_p4_s6_sample_prompt_package_validation_report.json",
        help="Path to write the validation report JSON.",
    )
    parser.add_argument(
        "--print-report",
        action="store_true",
        help="Print the validation report JSON to stdout.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    input_path = Path(args.input)
    report_path = Path(args.report)

    try:
        artifact = load_json(input_path)
    except FileNotFoundError:
        report = {
            "validator_id": "E4S_P4_S6_PROMPT_VALIDATOR_V1",
            "task_id": "E4S-P4-S6_PromptValidator_Implementation",
            "target_artifact_id": None,
            "result": "FAIL",
            "blocking_error_count": 1,
            "warning_count": 0,
            "blocking_errors": [
                {
                    "code": "input_file_not_found",
                    "path": str(input_path),
                    "message": "Input JSON artifact was not found.",
                }
            ],
            "warnings": [],
            "coverage": {"prompt_records_seen": 0, "packages_seen": 0, "checks": []},
        }
    except json.JSONDecodeError as exc:
        report = {
            "validator_id": "E4S_P4_S6_PROMPT_VALIDATOR_V1",
            "task_id": "E4S-P4-S6_PromptValidator_Implementation",
            "target_artifact_id": None,
            "result": "FAIL",
            "blocking_error_count": 1,
            "warning_count": 0,
            "blocking_errors": [
                {
                    "code": "input_json_decode_error",
                    "path": str(input_path),
                    "message": f"Invalid JSON: {exc}",
                }
            ],
            "warnings": [],
            "coverage": {"prompt_records_seen": 0, "packages_seen": 0, "checks": []},
        }
    else:
        report = validate_artifact(artifact)

    write_report(report_path, report)

    if args.print_report:
        print(json.dumps(report, ensure_ascii=False, indent=2))

    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
