#!/usr/bin/env python3
"""Validate the Unit01 cumulative reusable language-asset registry."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_u01data01_unit01_cumulative_reusable_language_asset_registry as builder

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Validates Unit01 reference bindings and cumulative reuse boundaries only; no learner content, questions, answers, scoring, state, audio, A2 targets, or parallel curriculum is created."
PASS_STATUS = "PASS_A1FS_V1_U01DATA01_UNIT01_CUMULATIVE_REUSABLE_LANGUAGE_ASSET_REGISTRY_VALIDATION"
DEFAULT_REPORT = builder.DEFAULT_OUTPUT
EXPECTED = {"active_vocabulary": 22, "active_nouns": 16, "active_adjectives": 6, "receptive_vocabulary": 9, "canonical_chunks": 3, "instructional_phrases_distinct": 46, "target_sentence_frames": 9, "scaffold_sentence_frames": 2, "total_language_asset_bindings": 91}


class RegistryValidationError(ValueError):
    pass


def _forbidden(value: Any) -> bool:
    if isinstance(value, Mapping):
        return bool(builder.FORBIDDEN_CONTENT_KEYS & set(value)) or any(_forbidden(child) for child in value.values())
    if isinstance(value, list):
        return any(_forbidden(child) for child in value)
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
    unit, authority, policy = report.get("unit") or {}, report.get("source_authority") or {}, report.get("cumulative_reuse_policy") or {}
    check(unit.get("unit_id") == builder.UNIT_ID and unit.get("unit_sequence") == 1 and unit.get("introduced_assets_are_reusable") is True, "unit_scope_invalid")
    check(authority.get("approved_contract_sha256") == builder.APPROVED_CONTRACT_SHA256 and authority.get("approval_status") == "APPROVED_AS_RECONCILED", "approval_invalid")
    check(policy.get("later_units_may_reference_unit01_assets") is True, "later_unit_reference_disabled")
    check(policy.get("copy_records_into_later_units") is False, "copy_on_reuse_forbidden")
    check(policy.get("identity_mode") == "REFERENCE_BY_STABLE_ASSET_ID", "identity_mode_invalid")
    check(tuple(policy.get("future_unit_roles") or []) == builder.FUTURE_ROLES, "future_roles_invalid")
    check(tuple(policy.get("selection_gates") or []) == builder.SELECTION_GATES, "selection_gates_invalid")
    groups = report.get("asset_bindings") or {}
    vocabulary, chunks, phrases, frames = (groups.get(name) or [] for name in ("vocabulary", "canonical_chunks", "instructional_phrases", "sentence_frames"))
    all_rows = vocabulary + chunks + phrases + frames
    binding_ids = [row.get("binding_id") for row in all_rows]
    check(len(binding_ids) == len(set(binding_ids)) and all(binding_ids), "binding_ids_invalid")
    for row in all_rows:
        check(row.get("introduced_unit_id") == builder.UNIT_ID and row.get("introduced_unit_sequence") == 1 and row.get("available_from_unit_sequence") == 1, "binding_unit_invalid")
        check(row.get("copy_on_reuse") is False and row.get("reusable_in_later_units") is True, "binding_reuse_invalid")
        check(tuple(row.get("eligible_future_unit_roles") or []) == builder.FUTURE_ROLES, "binding_future_roles_invalid")
    check(report.get("denominators") == EXPECTED, "denominators_invalid")
    check((len(vocabulary), len(chunks), len(phrases), len(frames)) == (31, 3, 46, 11), "binding_counts_invalid")
    check(len({row.get("normalized_surface") for row in phrases}) == 46, "phrase_dedup_invalid")
    a2 = [row for row in vocabulary if row.get("cefr_level") == "A2"]
    check(len(a2) == 1 and a2[0].get("a2_bridge") is True and a2[0].get("production_allowed") is False and a2[0].get("direct_assessment_allowed") is False, "a2_bridge_invalid")
    ice = [row for row in chunks if row.get("asset_id") == "EVP_CHUNK_000054"]
    check(len(ice) == 1 and ice[0].get("production_allowed") is False and ice[0].get("direct_assessment_allowed") is False, "countability_sensitive_chunk_invalid")
    scaffold = [row for row in frames if row.get("frame_role") == "SCAFFOLD_ONLY"]
    check(len(scaffold) == 2 and all(row.get("direct_assessment_allowed") is False for row in scaffold), "scaffold_frame_invalid")
    check(not _forbidden(report), "forbidden_content_keys")
    check(all(value is False for value in (report.get("boundaries") or {}).values()), "boundary_drift")
    unsigned = dict(report); unsigned.pop("registry_sha256", None)
    check(report.get("registry_sha256") == builder.digest(unsigned), "registry_digest_invalid")
    check(report.get("next_short_step") == builder.NEXT_SHORT_STEP, "next_short_step_invalid")
    if errors:
        raise RegistryValidationError(";".join(errors))
    return {"validation_status": PASS_STATUS, "unit_id": builder.UNIT_ID, "registry_sha256": report["registry_sha256"], "denominators": report["denominators"], "next_short_step": builder.NEXT_SHORT_STEP}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    try:
        report = json.loads(args.report.resolve().read_text(encoding="utf-8"))
        result = validate_report(report)
    except (OSError, json.JSONDecodeError, RegistryValidationError, ValueError, KeyError, TypeError) as exc:
        print("STATUS=FAIL_A1FS_V1_U01DATA01_UNIT01_CUMULATIVE_REUSABLE_LANGUAGE_ASSET_REGISTRY_VALIDATION")
        print(f"ERROR={exc}")
        return 1
    print(f"STATUS={result['validation_status']}")
    print(f"UNIT={result['unit_id']}")
    for key, value in result["denominators"].items():
        print(f"{key.upper()}={value}")
    print(f"REGISTRY_SHA256={result['registry_sha256']}")
    print(f"NEXT_SHORT_STEP={result['next_short_step']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
