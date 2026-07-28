#!/usr/bin/env python3
"""Independently validate U01E S04 multi-standard coverage readback."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import (
    build_a1fs_online_v1_2_u01e_s04_multistandard_coverage_readback as builder,
)

VALIDATOR_ID = (
    "A1FS-ONLINE-V1.2-U01E-S04_"
    "MultiStandardCoverageReadbackIndependentValidator"
)
FORBIDDEN_SAFE_KEYS = (
    '"learner_id"',
    '"item_key"',
    '"asset_key"',
    '"attempt_id"',
    '"response_json"',
    '"accepted_texts"',
    '"accepted_sequence"',
    '"correct_answer"',
    '"learner_database_sha256"',
    '"staged_database_sha256"',
)


class S04ValidationError(ValueError):
    """Fail-closed S04 validation error."""


def _expect(condition: bool, code: str, errors: list[str]) -> None:
    if not condition:
        errors.append(code)


def _validate_digest(value: Mapping[str, Any], field: str, errors: list[str]) -> None:
    expected = builder.digest({key: child for key, child in value.items() if key != field})
    _expect(value.get(field) == expected, f"{field}_mismatch", errors)


def _validate_domain(name: str, row: Any, errors: list[str]) -> None:
    if not isinstance(row, Mapping):
        errors.append(f"domain_not_object:{name}")
        return
    denominator = row.get("denominator_count")
    _expect(isinstance(denominator, int) and denominator >= 0, f"denominator_invalid:{name}", errors)
    for field in (
        "selected_count",
        "exposed_count",
        "practised_count",
        "assessed_count",
        "passed_count",
        "weak_count",
        "unresolved_count",
    ):
        value = row.get(field)
        _expect(isinstance(value, int) and value >= 0, f"domain_count_invalid:{name}:{field}", errors)
        if isinstance(value, int) and isinstance(denominator, int) and denominator > 0:
            _expect(value <= denominator, f"domain_count_exceeds_denominator:{name}:{field}", errors)
    if isinstance(row.get("practised_count"), int) and isinstance(row.get("assessed_count"), int):
        _expect(row["assessed_count"] <= row["practised_count"], f"assessed_exceeds_practised:{name}", errors)
    if isinstance(row.get("passed_count"), int) and isinstance(row.get("assessed_count"), int):
        _expect(row["passed_count"] <= row["assessed_count"], f"passed_exceeds_assessed:{name}", errors)
    _expect(row.get("stable_count") is None, f"stable_count_overclaimed:{name}", errors)
    _expect(row.get("mastered_count") is None, f"mastered_count_overclaimed:{name}", errors)
    _expect(row.get("transfer_proven_count") is None, f"transfer_count_overclaimed:{name}", errors)
    _expect(
        row.get("mastery_status") == "NOT_AVAILABLE_FROM_CURRENT_ITEM_LEVEL_EVIDENCE",
        f"mastery_status_invalid:{name}",
        errors,
    )


def validate_artifact(
    artifact: Mapping[str, Any], safe_report: Mapping[str, Any]
) -> dict[str, Any]:
    errors: list[str] = []
    _expect(artifact.get("task_id") == builder.TASK_ID, "artifact_task_id_invalid", errors)
    _expect(artifact.get("program_id") == builder.PROGRAM_ID, "artifact_program_id_invalid", errors)
    _expect(artifact.get("schema_version") == builder.SCHEMA_VERSION, "artifact_schema_version_invalid", errors)
    _expect(artifact.get("validation_status") == builder.PASS_STATUS, "artifact_status_invalid", errors)
    _expect(artifact.get("unit_id") == builder.UNIT_ID, "artifact_unit_id_invalid", errors)
    _validate_digest(artifact, "artifact_sha256", errors)
    _expect(safe_report.get("task_id") == builder.TASK_ID, "safe_task_id_invalid", errors)
    _expect(safe_report.get("validation_status") == builder.PASS_STATUS, "safe_status_invalid", errors)
    _expect(safe_report.get("unit_id") == builder.UNIT_ID, "safe_unit_id_invalid", errors)
    _validate_digest(safe_report, "report_sha256", errors)

    registry = artifact.get("target_registry")
    if not isinstance(registry, list):
        errors.append("registry_not_list")
        registry = []
    _expect(len(registry) == builder.EXPECTED_TOTAL_COUNT, "registry_count_invalid", errors)
    item_keys = [row.get("item_key") for row in registry if isinstance(row, Mapping)]
    signatures = [row.get("semantic_signature") for row in registry if isinstance(row, Mapping)]
    _expect(len(item_keys) == len(set(item_keys)), "registry_item_key_duplicate", errors)
    _expect(len(signatures) == len(set(signatures)), "registry_signature_duplicate", errors)
    statuses = CounterLike(row.get("runtime_status") for row in registry if isinstance(row, Mapping))
    _expect(statuses.get("RUNTIME_EXISTING") == builder.EXPECTED_EXISTING_COUNT, "existing_runtime_count_invalid", errors)
    _expect(
        statuses.get("APPROVED_PENDING_RUNTIME_MATERIALIZATION") == builder.EXPECTED_NEW_COUNT,
        "pending_runtime_count_invalid",
        errors,
    )
    _expect(len({row.get("question_type") for row in registry if isinstance(row, Mapping)}) == builder.EXPECTED_ASSESSMENT_PATTERN_COUNT, "question_type_count_invalid", errors)
    for row in registry:
        if not isinstance(row, Mapping):
            errors.append("registry_row_not_object")
            continue
        targets = row.get("targets")
        if not isinstance(targets, Mapping):
            errors.append(f"registry_targets_missing:{row.get('item_key')}")
            continue
        _expect(
            set(targets) == set(builder.TARGET_FIELD_BY_DOMAIN.values()),
            f"registry_target_fields_invalid:{row.get('item_key')}",
            errors,
        )
        _expect(
            targets.get("target_ket_prerequisite_node_ids") == [],
            f"ket_activity_ref_invented:{row.get('item_key')}",
            errors,
        )
        _expect(row.get("cambridge_stage") == "STARTERS", f"cambridge_stage_invalid:{row.get('item_key')}", errors)

    denominators = artifact.get("denominators")
    if not isinstance(denominators, Mapping):
        errors.append("denominators_missing")
        denominators = {}
    expected_denominators = {
        "evp_senses": 784,
        "egp_rows": 109,
        "canonical_chunks": 76,
        "patterns": 27,
        "ket_prerequisites": 553,
        "assessment_patterns": 8,
        "cambridge_capabilities": 0,
        "flyers_a2_handoff": 1,
    }
    for key, expected in expected_denominators.items():
        _expect(
            isinstance(denominators.get(key), Mapping)
            and denominators[key].get("count") == expected,
            f"denominator_drift:{key}",
            errors,
        )
    _expect(
        denominators.get("cambridge_capabilities", {}).get("status")
        == "NOT_AVAILABLE_GRANULAR_CAPABILITY_DENOMINATOR",
        "cambridge_capability_overclaim",
        errors,
    )
    _expect(
        denominators.get("flyers_a2_handoff", {}).get("status")
        == "HANDOFF_ONLY_EXCLUDED_FROM_CURRENT_COMPLETION",
        "flyers_handoff_boundary_invalid",
        errors,
    )

    readback = artifact.get("coverage_readback")
    if not isinstance(readback, Mapping):
        errors.append("coverage_readback_missing")
        readback = {}
    _expect(readback.get("curriculum_item_count") == builder.EXPECTED_TOTAL_COUNT, "readback_item_count_invalid", errors)
    _expect(readback.get("existing_runtime_item_count") == builder.EXPECTED_EXISTING_COUNT, "readback_existing_count_invalid", errors)
    _expect(readback.get("approved_pending_runtime_item_count") == builder.EXPECTED_NEW_COUNT, "readback_pending_count_invalid", errors)
    _expect(readback.get("question_type_count") == builder.EXPECTED_ASSESSMENT_PATTERN_COUNT, "readback_question_type_count_invalid", errors)
    _expect(readback.get("cambridge_stage") == "STARTERS", "readback_cambridge_stage_invalid", errors)
    evidence = readback.get("learner_evidence_summary", {})
    _expect(isinstance(evidence.get("attempt_count"), int), "attempt_count_invalid", errors)
    _expect(isinstance(evidence.get("distinct_attempted_item_count"), int), "distinct_attempt_count_invalid", errors)
    if isinstance(evidence.get("attempt_count"), int) and isinstance(evidence.get("distinct_attempted_item_count"), int):
        _expect(evidence["distinct_attempted_item_count"] <= evidence["attempt_count"], "distinct_attempt_exceeds_total", errors)
    domains = readback.get("coverage_by_domain")
    if not isinstance(domains, Mapping):
        errors.append("coverage_domains_missing")
        domains = {}
    for name in (
        "evp_senses",
        "evp_unique_lemmas",
        "egp_rows",
        "canonical_chunks",
        "context_phrases",
        "sentences",
        "patterns",
        "ket_prerequisites",
        "assessment_patterns",
    ):
        _validate_domain(name, domains.get(name), errors)
    ket = readback.get("ket_prerequisite_readback", {})
    _expect(ket.get("denominator_count") == 553, "ket_readback_denominator_invalid", errors)
    _expect(ket.get("selected_count") == 0, "ket_selected_overclaim", errors)
    _expect(ket.get("practised_count") == 0, "ket_practised_overclaim", errors)
    _expect(ket.get("coverage_claim_allowed") is False, "ket_coverage_claim_allowed", errors)
    _expect(
        ket.get("activity_bridge_status")
        == "UNRESOLVED_NO_EVIDENCE_BACKED_UNIT01_ACTIVITY_BRIDGE",
        "ket_bridge_status_invalid",
        errors,
    )
    cambridge = readback.get("cambridge_readback", {})
    _expect(cambridge.get("stage") == "STARTERS", "cambridge_readback_stage_invalid", errors)
    _expect(cambridge.get("flyers_a2_handoff_excluded") is True, "flyers_exclusion_missing", errors)
    _expect(
        cambridge.get("granular_capability_status")
        == "NOT_AVAILABLE_DO_NOT_DERIVE_CAPABILITY_PERCENTAGE_FROM_UNIT_STAGE_LABELS",
        "cambridge_granular_overclaim",
        errors,
    )
    _expect(
        readback.get("mastery_bridge_status")
        == "NOT_AVAILABLE_NO_ITEM_TARGET_TO_M7_M8_NODE_BRIDGE",
        "mastery_bridge_overclaim",
        errors,
    )

    safe_expected = builder.safe_readback(readback)
    _expect(safe_report.get("coverage_readback") == safe_expected, "safe_readback_drift", errors)
    safe_encoded = json.dumps(safe_report, ensure_ascii=False, sort_keys=True)
    for forbidden in FORBIDDEN_SAFE_KEYS:
        _expect(forbidden not in safe_encoded, f"safe_private_key_leaked:{forbidden}", errors)

    compatibility = artifact.get("compatibility_contract", {})
    _expect(compatibility.get("source_database_read_only") is True, "source_database_read_only_missing", errors)
    _expect(compatibility.get("allowed_migration_mode") == "ADDITIVE_TABLES_ONLY", "migration_mode_invalid", errors)
    _expect(compatibility.get("existing_table_shape_change_allowed") is False, "legacy_shape_change_allowed", errors)
    _expect(compatibility.get("existing_response_contract_change_allowed") is False, "response_contract_change_allowed", errors)
    _expect(compatibility.get("existing_attempt_change_allowed") is False, "attempt_change_allowed", errors)
    staging = artifact.get("staging_readback")
    if not isinstance(staging, Mapping):
        errors.append("staging_readback_missing")
        staging = {}
    _expect(staging.get("source_database_preserved") is True, "source_database_not_preserved", errors)
    _expect(staging.get("legacy_schema_unchanged") is True, "legacy_schema_changed", errors)
    _expect(set(staging.get("additive_tables", [])) == builder.ADDITIVE_TABLES, "additive_tables_invalid", errors)
    counts = staging.get("additive_table_row_counts", {})
    _expect(counts.get("u01e_asset_target_bindings") == builder.EXPECTED_TOTAL_COUNT, "staged_binding_count_invalid", errors)
    _expect(counts.get("u01e_learner_coverage_snapshots") == 1, "staged_snapshot_count_invalid", errors)
    _expect(staging.get("v1_1_backward_compatible_schema") is True, "v1_1_compatibility_invalid", errors)
    safe_staging = safe_report.get("staging_readback", {})
    _expect(safe_staging.get("source_database_preserved") is True, "safe_source_preservation_missing", errors)
    _expect(safe_staging.get("legacy_schema_unchanged") is True, "safe_legacy_schema_status_invalid", errors)

    boundaries = artifact.get("claim_boundaries", {})
    for key in (
        "learner_response_included",
        "attempt_id_included",
        "hidden_answer_included",
        "source_database_written",
        "runtime_item_bank_installed",
        "new_item_attempts_fabricated",
        "stable_or_mastery_inferred",
        "ket_coverage_claimed",
        "cambridge_granular_capability_claimed",
        "unit02_modified",
        "audio_enabled",
        "speaking_capture_enabled",
        "a2_unlocked",
    ):
        _expect(boundaries.get(key) is False, f"claim_boundary_invalid:{key}", errors)
    _expect(artifact.get("stop_reason") == "NONE", "stop_reason_invalid", errors)
    _expect(artifact.get("next_short_step") == builder.NEXT_SHORT_STEP, "next_short_step_invalid", errors)

    status = builder.PASS_STATUS if not errors else "FAIL"
    report_core = {
        "validator_id": VALIDATOR_ID,
        "validation_status": status,
        "error_count": len(errors),
        "errors": errors,
        "target_registry_count": len(registry),
        "question_type_count": len({row.get("question_type") for row in registry if isinstance(row, Mapping)}),
        "source_database_preserved": staging.get("source_database_preserved") is True,
        "legacy_schema_unchanged": staging.get("legacy_schema_unchanged") is True,
        "additive_tables_only": set(staging.get("additive_tables", [])) == builder.ADDITIVE_TABLES,
        "ket_coverage_claimed": False,
        "mastery_inferred": False,
        "a2_unlocked": False,
        "next_short_step": builder.NEXT_SHORT_STEP,
    }
    return {**report_core, "report_sha256": builder.digest(report_core)}


def CounterLike(values: Iterable[Any]) -> dict[Any, int]:
    result: dict[Any, int] = {}
    for value in values:
        result[value] = result.get(value, 0) + 1
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("safe_report", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    artifact = json.loads(args.artifact.read_text(encoding="utf-8"))
    safe = json.loads(args.safe_report.read_text(encoding="utf-8"))
    report = validate_artifact(artifact, safe)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
