#!/usr/bin/env python3
"""Validate Unit 01 safe and learner-private question-generation context packs."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import (
    build_a1fs_online_v1_2_u01e_s02_unit01_generation_context_pack as builder,
)

VALIDATOR_ID = (
    "A1FS-ONLINE-V1.2-U01E-S02_"
    "Unit01GenerationContextPackIndependentValidator"
)
FORBIDDEN_SERIALIZED_KEYS = (
    '"accepted_texts"',
    '"accepted_sequence"',
    '"response_json"',
    '"contract_json"',
    '"private_scoring_contract"',
)


class S02ValidationError(ValueError):
    """Fail-closed S02 pack validation error."""


def _digest_without(value: Mapping[str, Any], key: str) -> str:
    return builder.digest({name: child for name, child in value.items() if name != key})


def _validate_pack_digest(pack: Mapping[str, Any], errors: list[str], prefix: str) -> None:
    prompt = pack.get("prompt_text")
    if not isinstance(prompt, str) or not prompt.strip():
        errors.append(f"{prefix}:prompt_missing")
    elif hashlib.sha256(prompt.encode("utf-8")).hexdigest() != pack.get("prompt_sha256"):
        errors.append(f"{prefix}:prompt_sha256_mismatch")
    if _digest_without(pack, "pack_sha256") != pack.get("pack_sha256"):
        errors.append(f"{prefix}:pack_sha256_mismatch")


def _sum_budget(value: Any, code: str, errors: list[str]) -> None:
    if not isinstance(value, Mapping):
        errors.append(f"{code}:not_object")
        return
    try:
        total = sum(int(row) for row in value.values())
    except (TypeError, ValueError):
        errors.append(f"{code}:non_integer")
        return
    if total != 100:
        errors.append(f"{code}:sum_not_100:{total}")


def _validate_static_context(context: Any, errors: list[str], prefix: str) -> None:
    if not isinstance(context, Mapping):
        errors.append(f"{prefix}:generation_context_missing")
        return
    unit = context.get("unit", {})
    if unit.get("unit_id") != builder.s01.m01.UNIT_ID:
        errors.append(f"{prefix}:unit_identity_invalid")
    if unit.get("cambridge_stage") != "STARTERS":
        errors.append(f"{prefix}:cambridge_stage_invalid")
    if unit.get("a2_handoff_blocked") is not True:
        errors.append(f"{prefix}:a2_handoff_not_blocked")
    contexts = context.get("approved_contexts")
    if not isinstance(contexts, list) or len(contexts) != builder.EXPECTED_CONTEXT_COUNT:
        errors.append(f"{prefix}:context_denominator_invalid")
    else:
        roles = {row.get("role") for row in contexts if isinstance(row, Mapping)}
        expected_roles = {
            "ANCHOR_CONTEXT",
            "NEAR_TRANSFER",
            "EXTENDED_CONTEXT",
            "FUNCTIONAL_DIALOGUE_CONTEXT",
            "UNSEEN_TRANSFER",
        }
        if roles != expected_roles:
            errors.append(f"{prefix}:context_roles_invalid")
    targets = context.get("curriculum_targets", {})
    if not targets.get("new_productive_vocabulary"):
        errors.append(f"{prefix}:productive_vocabulary_missing")
    if not targets.get("new_receptive_vocabulary"):
        errors.append(f"{prefix}:receptive_vocabulary_missing")
    if not targets.get("egp_row_ids"):
        errors.append(f"{prefix}:egp_targets_missing")
    if not targets.get("patterns"):
        errors.append(f"{prefix}:pattern_targets_missing")
    if targets.get("ket_prerequisite_node_ids") != []:
        errors.append(f"{prefix}:ket_refs_invented")
    if (
        targets.get("ket_binding_status")
        != "UNRESOLVED_NO_EVIDENCE_BACKED_UNIT01_ACTIVITY_BRIDGE"
    ):
        errors.append(f"{prefix}:ket_binding_status_invalid")
    policy = context.get("assessment_policy", {})
    allowed = policy.get("allowed_pattern_refs")
    if not isinstance(allowed, list) or len(allowed) != builder.EXPECTED_CAMBRIDGE_PATTERN_COUNT:
        errors.append(f"{prefix}:assessment_pattern_denominator_invalid")
    if policy.get("minimum_distinct_question_types") != 8:
        errors.append(f"{prefix}:question_type_minimum_invalid")
    if policy.get("target_activity_range") != [20, 26]:
        errors.append(f"{prefix}:activity_range_invalid")
    if policy.get("no_filler_policy") is not True:
        errors.append(f"{prefix}:no_filler_policy_missing")
    dedup = context.get("existing_item_dedup", {})
    signatures = dedup.get("semantic_signatures")
    if not isinstance(signatures, list) or len(signatures) != builder.EXPECTED_EXISTING_ITEM_COUNT:
        errors.append(f"{prefix}:semantic_signature_denominator_invalid")
    elif len({row.get("semantic_signature") for row in signatures}) != len(signatures):
        errors.append(f"{prefix}:semantic_signature_collision")
    if dedup.get("reject_existing_semantic_signature") is not True:
        errors.append(f"{prefix}:semantic_dedup_not_enforced")
    budgets = context.get("generation_budget_contract", {})
    _sum_budget(budgets.get("support_level_percent"), f"{prefix}:support_budget", errors)
    _sum_budget(
        budgets.get("learning_role_percent_default"),
        f"{prefix}:default_learning_role_budget",
        errors,
    )
    _sum_budget(
        budgets.get("learning_role_percent_with_weak_items"),
        f"{prefix}:weak_learning_role_budget",
        errors,
    )
    active = budgets.get("active_learning_role_percent")
    if active is not None:
        _sum_budget(active, f"{prefix}:active_learning_role_budget", errors)
    output = context.get("candidate_output_contract", {})
    if output.get("artifact_role") != "CANDIDATE_JSON":
        errors.append(f"{prefix}:candidate_role_invalid")
    if output.get("format") != "JSON_ONLY":
        errors.append(f"{prefix}:output_format_invalid")
    if output.get("direct_canonical_write_allowed") is not False:
        errors.append(f"{prefix}:canonical_write_allowed")
    if output.get("admission_required_before_runtime") is not True:
        errors.append(f"{prefix}:admission_gate_missing")
    fields = output.get("required_fields")
    if not isinstance(fields, list) or set(builder.OUTPUT_FIELDS) - set(fields):
        errors.append(f"{prefix}:candidate_output_fields_missing")
    hard_rules = set(context.get("hard_rules", []))
    required_rules = {
        "DO_NOT_CLAIM_MASTERY",
        "DO_NOT_INVENT_AUTHORITY_IDS_OR_SOURCE_CLAIMS",
        "DO_NOT_REPEAT_EXISTING_SEMANTIC_SIGNATURES",
        "A2_AND_FLYERS_LANGUAGE_TARGETS_REMAIN_BLOCKED",
    }
    if not required_rules.issubset(hard_rules):
        errors.append(f"{prefix}:hard_rules_incomplete")


def validate_packs(
    safe: Mapping[str, Any], private: Mapping[str, Any]
) -> dict[str, Any]:
    errors: list[str] = []
    for prefix, pack, expected_type in (
        ("safe", safe, builder.SAFE_PACK_TYPE),
        ("private", private, builder.PRIVATE_PACK_TYPE),
    ):
        if not isinstance(pack, Mapping):
            errors.append(f"{prefix}:pack_not_object")
            continue
        if pack.get("task_id") != builder.TASK_ID:
            errors.append(f"{prefix}:task_id_invalid")
        if pack.get("program_id") != builder.PROGRAM_ID:
            errors.append(f"{prefix}:program_id_invalid")
        if pack.get("schema_version") != builder.SCHEMA_VERSION:
            errors.append(f"{prefix}:schema_version_invalid")
        if pack.get("validation_status") != builder.PASS_STATUS:
            errors.append(f"{prefix}:validation_status_invalid")
        if pack.get("pack_type") != expected_type:
            errors.append(f"{prefix}:pack_type_invalid")
        if pack.get("stop_reason") != "NONE":
            errors.append(f"{prefix}:stop_reason_invalid")
        if pack.get("next_short_step") != builder.NEXT_SHORT_STEP:
            errors.append(f"{prefix}:next_short_step_invalid")
        _validate_pack_digest(pack, errors, prefix)
        _validate_static_context(pack.get("generation_context"), errors, prefix)
        boundaries = pack.get("claim_boundaries", {})
        required_false = (
            "canonical_write_allowed",
            "learner_database_written",
            "hidden_answer_exposed",
            "learner_response_exposed",
            "mastery_inferred",
            "unit02_modified",
            "audio_enabled",
            "speaking_capture_enabled",
            "a2_unlocked",
        )
        if boundaries.get("candidate_generation_only") is not True:
            errors.append(f"{prefix}:candidate_generation_boundary_missing")
        for key in required_false:
            if boundaries.get(key) is not False:
                errors.append(f"{prefix}:claim_boundary_invalid:{key}")
        encoded = json.dumps(pack, ensure_ascii=False, sort_keys=True)
        for forbidden in FORBIDDEN_SERIALIZED_KEYS:
            if forbidden in encoded:
                errors.append(f"{prefix}:hidden_source_key_present:{forbidden}")

    safe_source = safe.get("source_identity", {}) if isinstance(safe, Mapping) else {}
    private_source = private.get("source_identity", {}) if isinstance(private, Mapping) else {}
    for key in (
        "s01_task_id",
        "s01_approved_artifact_sha256",
        "s01_approved_file_sha256",
    ):
        if safe_source.get(key) != private_source.get(key):
            errors.append(f"source_identity_mismatch:{key}")
    if "learner_database_sha256" in safe_source or "learner_state_sha256" in safe_source:
        errors.append("safe:private_source_identity_leaked")
    safe_context = safe.get("generation_context", {}) if isinstance(safe, Mapping) else {}
    private_context = private.get("generation_context", {}) if isinstance(private, Mapping) else {}
    if "learner_state" in safe_context:
        errors.append("safe:learner_state_leaked")
    learner = private_context.get("learner_state")
    if not isinstance(learner, Mapping):
        errors.append("private:learner_state_missing")
        learner = {}
    else:
        if not str(learner.get("learner_id") or "").strip():
            errors.append("private:learner_id_missing")
        if learner.get("mastery_state") != "NOT_INFERRED_FROM_ATTEMPT_OUTCOMES":
            errors.append("private:mastery_overclaim")
        if builder.digest(
            {key: value for key, value in learner.items() if key != "learner_state_sha256"}
        ) != learner.get("learner_state_sha256"):
            errors.append("private:learner_state_sha256_mismatch")
        _sum_budget(
            learner.get("generation_learning_role_percent"),
            "private:learner_budget",
            errors,
        )
    if private_source.get("learner_state_sha256") != learner.get("learner_state_sha256"):
        errors.append("private:learner_source_binding_mismatch")
    safe_stale = safe.get("stale_state_contract", {}) if isinstance(safe, Mapping) else {}
    private_stale = private.get("stale_state_contract", {}) if isinstance(private, Mapping) else {}
    if safe_stale.get("requires_exact_s01_approved_artifact_sha256") is not True:
        errors.append("safe:s01_stale_gate_missing")
    if private_stale.get("requires_exact_learner_database_sha256") is not True:
        errors.append("private:database_stale_gate_missing")
    if private_stale.get("rebuild_when_learner_evidence_changes") is not True:
        errors.append("private:learner_rebuild_gate_missing")

    safe_serialized = json.dumps(safe, ensure_ascii=False, sort_keys=True)
    for key in ('"learner_id"', '"attempt_id"', '"asset_key"', '"learner_database_sha256"'):
        if key in safe_serialized:
            errors.append(f"safe:private_identity_leaked:{key}")

    static_safe = dict(safe_context)
    static_private = dict(private_context)
    static_private.pop("learner_state", None)
    if isinstance(static_private.get("generation_budget_contract"), Mapping):
        budget = dict(static_private["generation_budget_contract"])
        budget.pop("active_learning_role_percent", None)
        static_private["generation_budget_contract"] = budget
    if static_safe != static_private:
        errors.append("safe_private_static_context_drift")

    status = builder.PASS_STATUS if not errors else "FAIL"
    return {
        "validator_id": VALIDATOR_ID,
        "validation_status": status,
        "error_count": len(errors),
        "errors": errors,
        "context_count": len(safe_context.get("approved_contexts", []))
        if isinstance(safe_context, Mapping)
        else 0,
        "existing_semantic_signature_count": len(
            safe_context.get("existing_item_dedup", {}).get("semantic_signatures", [])
        )
        if isinstance(safe_context, Mapping)
        else 0,
        "assessment_pattern_count": len(
            safe_context.get("assessment_policy", {}).get("allowed_pattern_refs", [])
        )
        if isinstance(safe_context, Mapping)
        else 0,
        "safe_private_separation": not any(error.startswith("safe:private") for error in errors),
        "candidate_only": True,
        "canonical_write_allowed": False,
        "mastery_inferred": False,
        "a2_unlocked": False,
        "next_short_step": builder.NEXT_SHORT_STEP,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("safe", type=Path)
    parser.add_argument("private", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    safe = json.loads(args.safe.read_text(encoding="utf-8"))
    private = json.loads(args.private.read_text(encoding="utf-8"))
    report = validate_packs(safe, private)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
