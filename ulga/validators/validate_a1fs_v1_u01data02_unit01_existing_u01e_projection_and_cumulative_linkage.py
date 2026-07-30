#!/usr/bin/env python3
"""Validate Unit01 cumulative linkage to the existing U01E context and activity pipeline."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_u01data02_unit01_existing_u01e_projection_and_cumulative_linkage as builder

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Validates reference-only Unit01 linkage and identity preservation; no learner-facing text, questions, answers, scoring, state, audio, A2 target, or parallel bank is created."
PASS_STATUS = "PASS_A1FS_V1_U01DATA02_UNIT01_EXISTING_U01E_PROJECTION_AND_CUMULATIVE_LINKAGE_VALIDATION"
DEFAULT_REPORT = builder.DEFAULT_OUTPUT
EXPECTED_SKILLS = {"READING": 10, "SPEAKING": 6, "WRITING": 8}
FORBIDDEN_KEYS = frozenset({"prompt", "correct_answer", "acceptable_variants", "explanation", "response_contract", "options", "stimulus", "learner_id", "score"})


class ProjectionValidationError(ValueError):
    pass


def forbidden(value: Any) -> bool:
    if isinstance(value, Mapping):
        return bool(FORBIDDEN_KEYS & set(value)) or any(forbidden(child) for child in value.values())
    if isinstance(value, list):
        return any(forbidden(child) for child in value)
    return False


def validate_report(report: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    def check(condition: bool, code: str) -> None:
        if not condition:
            errors.append(code)
    check(report.get("schema_version") == builder.SCHEMA_VERSION, "schema_version_invalid")
    check(report.get("program_id") == builder.PROGRAM_ID, "program_id_invalid")
    check(report.get("task_id") == builder.TASK_ID, "task_id_invalid")
    check(report.get("status") == builder.PASS_STATUS, "status_invalid")
    unit = report.get("unit") or {}
    check(unit == {"unit_id": builder.UNIT_ID, "unit_sequence": 1, "level_scope": ["A1"]}, "unit_scope_invalid")
    source = report.get("source_identity") or {}
    for key in ("u01data01_registry_sha256", "s01_approved_sha256", "s02_safe_pack_sha256", "s03_approved_sha256"):
        check(isinstance(source.get(key), str) and len(source[key]) == 64, f"source_digest_invalid:{key}")
    check(source.get("s03_item_bank_id") == builder.s03.ITEM_BANK_ID, "item_bank_id_invalid")
    check(source.get("s03_item_bank_version") == builder.s03.ITEM_BANK_VERSION, "item_bank_version_invalid")
    ownership = report.get("ownership_contract") or {}
    check(ownership.get("context_and_sentence_owner") == builder.s01.TASK_ID, "sentence_owner_invalid")
    check(ownership.get("existing_activity_owner") == builder.s01.m01.TASK_ID, "existing_activity_owner_invalid")
    check(ownership.get("fixed_item_bank_owner") == builder.s03.TASK_ID, "item_bank_owner_invalid")
    check(ownership.get("projection_creates_parallel_content") is False, "parallel_content_forbidden")
    check(ownership.get("projection_copies_question_or_answer_content") is False, "question_copy_forbidden")
    check(ownership.get("later_units_reference_existing_ids") is True and ownership.get("later_units_copy_records") is False, "later_unit_identity_policy_invalid")
    registry = report.get("registry_summary") or {}
    check(registry.get("total_language_asset_bindings") == 91, "registry_binding_denominator_invalid")
    contexts = report.get("context_projections") or []
    sentences = report.get("sentence_asset_projections") or []
    activity_groups = report.get("activity_projections") or {}
    existing = activity_groups.get("existing_response_contract_activities") or []
    fixed = activity_groups.get("fixed_admitted_items") or []
    activities = existing + fixed
    check(len(contexts) == 5 and len({row.get("context_id") for row in contexts}) == 5, "context_projection_count_invalid")
    check(len(sentences) == 18 and len({row.get("sentence_id") for row in sentences}) == 18, "sentence_projection_count_invalid")
    check(len(existing) == 11 and len(fixed) == 13 and len(activities) == 24, "activity_projection_count_invalid")
    check(len({row.get("activity_id") for row in activities}) == 24, "activity_identity_duplicate")
    sentence_ids = {str(row.get("sentence_id")) for row in sentences}
    context_ids = {str(row.get("context_id")) for row in contexts}
    binding_ids: set[str] = set()
    for group in report.get("registry_summary", {}),:
        del group
    for row in contexts:
        check(row.get("introduced_unit_id") == builder.UNIT_ID and row.get("copy_on_reuse") is False and row.get("future_unit_reference_allowed") is True, "context_reuse_invalid")
        check(set(row.get("sentence_ids") or []).issubset(sentence_ids), "context_sentence_ref_invalid")
        check(tuple(row.get("eligible_future_unit_roles") or []) == builder.FUTURE_ROLES, "context_future_roles_invalid")
    for row in sentences:
        check(row.get("context_id") in context_ids, "sentence_context_invalid")
        check(row.get("introduced_unit_id") == builder.UNIT_ID and row.get("copy_on_reuse") is False and row.get("future_unit_reference_allowed") is True, "sentence_reuse_invalid")
        check(tuple(row.get("eligible_future_unit_roles") or []) == builder.FUTURE_ROLES, "sentence_future_roles_invalid")
        binding_ids.update(str(value) for value in row.get("linked_registry_binding_ids", []))
    for row in activities:
        check(row.get("context_id") in context_ids, "activity_context_invalid")
        check(set(row.get("target_sentence_ids") or []).issubset(sentence_ids), "activity_sentence_ref_invalid")
        check(row.get("introduced_unit_id") == builder.UNIT_ID and row.get("copy_on_reuse") is False and row.get("future_unit_reference_allowed") is True, "activity_reuse_invalid")
        check(tuple(row.get("eligible_future_unit_roles") or []) == builder.FUTURE_ROLES, "activity_future_roles_invalid")
        check(row.get("content_copied_into_projection") is False and row.get("answer_contract_copied_into_projection") is False, "activity_content_copy_invalid")
        check(row.get("canonical_activity_identity_preserved") is True, "activity_identity_not_preserved")
        check(bool(row.get("linked_registry_binding_ids")), "activity_registry_link_missing")
        check(row.get("linkage_status") in {"LINKED_TO_CUMULATIVE_REGISTRY", "LINKED_WITH_EXTERNAL_SUPPORT"}, "activity_linkage_status_invalid")
        binding_ids.update(str(value) for value in row.get("linked_registry_binding_ids", []))
    check(bool(binding_ids), "no_registry_bindings_linked")
    summary = report.get("linkage_summary") or {}
    check(summary.get("context_count") == 5, "summary_context_count_invalid")
    check(summary.get("sentence_asset_count") == 18, "summary_sentence_count_invalid")
    check(summary.get("existing_activity_count") == 11 and summary.get("fixed_admitted_item_count") == 13 and summary.get("total_activity_count") == 24, "summary_activity_count_invalid")
    check(summary.get("activity_count_by_skill") == EXPECTED_SKILLS, "summary_skill_count_invalid")
    check(sum((summary.get("activity_linkage_status_counts") or {}).values()) == 24, "summary_linkage_count_invalid")
    check(summary.get("unlinked_external_support_is_promoted_to_registry") is False, "external_support_promotion_forbidden")
    check(summary.get("canonical_pattern_to_unit_frame_bridge_status") == "UNRESOLVED_RECORDED_NOT_INFERRED", "pattern_frame_overclaim")
    reuse = report.get("cumulative_reuse_contract") or {}
    check(reuse.get("sentence_assets_reusable_from_unit_sequence") == 1 and reuse.get("activity_identities_reusable_from_unit_sequence") == 1, "reuse_sequence_invalid")
    check(tuple(reuse.get("future_unit_roles") or []) == builder.FUTURE_ROLES, "reuse_roles_invalid")
    check(reuse.get("selection_requires_new_unit_compatibility_gate") is True and reuse.get("selection_requires_learner_state_or_scheduled_review_reason") is True, "reuse_selection_gate_invalid")
    check(reuse.get("full_cumulative_pool_may_not_be_assigned_as_one_lesson") is True, "full_pool_assignment_forbidden")
    check(not forbidden(report), "forbidden_content_keys")
    check(all(value is False for value in (report.get("boundaries") or {}).values()), "boundary_drift")
    unsigned = dict(report); unsigned.pop("projection_sha256", None)
    check(report.get("projection_sha256") == builder.digest(unsigned), "projection_digest_invalid")
    check(report.get("next_short_step") == builder.NEXT_SHORT_STEP, "next_short_step_invalid")
    if errors:
        raise ProjectionValidationError(";".join(errors))
    return {"validation_status": PASS_STATUS, "unit_id": builder.UNIT_ID, "projection_sha256": report["projection_sha256"], "registry_binding_count": registry["total_language_asset_bindings"], "context_count": len(contexts), "sentence_count": len(sentences), "activity_count": len(activities), "activity_count_by_skill": summary["activity_count_by_skill"], "next_short_step": builder.NEXT_SHORT_STEP}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    try:
        report = json.loads(args.report.resolve().read_text(encoding="utf-8"))
        result = validate_report(report)
    except (OSError, json.JSONDecodeError, ProjectionValidationError, ValueError, KeyError, TypeError) as exc:
        print("STATUS=FAIL_A1FS_V1_U01DATA02_UNIT01_EXISTING_U01E_PROJECTION_AND_CUMULATIVE_LINKAGE_VALIDATION")
        print(f"ERROR={exc}")
        return 1
    print(f"STATUS={result['validation_status']}")
    print(f"UNIT={result['unit_id']}")
    print(f"REGISTRY_BINDINGS={result['registry_binding_count']}")
    print(f"CONTEXTS={result['context_count']}")
    print(f"SENTENCES={result['sentence_count']}")
    print(f"ACTIVITIES={result['activity_count']}")
    print(f"ACTIVITY_COUNT_BY_SKILL={json.dumps(result['activity_count_by_skill'], sort_keys=True)}")
    print(f"PROJECTION_SHA256={result['projection_sha256']}")
    print(f"NEXT_SHORT_STEP={result['next_short_step']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
