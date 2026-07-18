#!/usr/bin/env python3
"""Independent validator for the complete A1FS V1 breadth ontology and contracts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator

from ulga.builders import build_a1fs_v1_r2_complete_breadth_ontology_deployment_contract as r2


def _empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def validate_ontology(ontology: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    core = {key: value for key, value in ontology.items() if key != "ontology_sha256"}
    if ontology.get("task_id") != r2.TASK_ID or ontology.get("schema_version") != r2.SCHEMA_VERSION:
        errors.append("ontology_identity_invalid")
    if ontology.get("validation_status") != r2.STATUS:
        errors.append("ontology_status_invalid")
    if ontology.get("ontology_sha256") != r2.digest(core):
        errors.append("ontology_digest_invalid")
    if ontology.get("field_groups") != r2.FIELD_GROUPS:
        errors.append("field_groups_drift")
    required = ontology.get("required_contract_fields")
    if required != r2.REQUIRED_CONTRACT_FIELDS or len(required or []) != len(set(required or [])):
        errors.append("required_contract_fields_invalid")
    if ontology.get("enums") != r2.ENUMS:
        errors.append("enum_registry_drift")
    if set(ontology.get("field_state_policy", {}).get("states", [])) != set(r2.MISSING_STATES):
        errors.append("missing_state_registry_invalid")
    expected_scope = {
        "levels": ["A1", "A1_PLUS"], "architecture_complete_in_v1": True,
        "data_population_milestone_based": True, "a2_locked": True,
        "qwen_required": False, "audio_population_required_now": False,
    }
    if ontology.get("scope") != expected_scope:
        errors.append("scope_boundary_invalid")
    domain_ids = [row.get("domain_id") for row in ontology.get("domain_definitions", [])]
    if domain_ids != r2.ENUMS["domains"] or len(domain_ids) != len(set(domain_ids)):
        errors.append("domain_definition_denominator_invalid")
    for name, values in ontology.get("enums", {}).items():
        if not isinstance(values, list) or not values or len(values) != len(set(values)):
            errors.append(f"enum_values_invalid:{name}")
    for name, progression in r2.PROGRESSION_CONTRACTS.items():
        if ontology.get("progression_contracts", {}).get(name) != progression:
            errors.append(f"progression_contract_invalid:{name}")
    boundaries = ontology.get("claim_boundaries", {})
    for key in (
        "canonical_graph_modified", "a2_content_included", "a2_unlocked",
        "qwen_dependency_added", "audio_files_required", "mastery_claimed", "coverage_claimed",
    ):
        if boundaries.get(key) is not False:
            errors.append(f"claim_boundary_broken:{key}")
    if ontology.get("next_short_step") != r2.NEXT_SHORT_STEP:
        errors.append("next_short_step_invalid")
    return errors


def validate_contract(contract: Mapping[str, Any], schema: Mapping[str, Any] | None = None) -> list[str]:
    errors: list[str] = []
    schema = schema or r2.build_contract_schema()
    for error in Draft202012Validator(schema).iter_errors(contract):
        path = ".".join(str(value) for value in error.path)
        errors.append(f"schema:{path}:{error.message}")
    if errors:
        return errors
    states = contract["field_states"]
    justifications = contract["field_justifications"]
    if set(states) != set(r2.REQUIRED_CONTRACT_FIELDS):
        return ["field_state_denominator_invalid"]
    for field in r2.REQUIRED_CONTRACT_FIELDS:
        state, value = states[field], contract[field]
        if state == "POPULATED" and _empty(value):
            errors.append(f"populated_field_empty:{field}")
        if state != "POPULATED" and not _empty(value):
            allowed_marker = (
                state == "DEFERRED_MEDIA_PAYLOAD"
                and value == "DEFERRED_MEDIA_PAYLOAD"
                and field in {"media_payload_state", "recording_state"}
            )
            if not allowed_marker:
                errors.append(f"unpopulated_field_has_value:{field}:{state}")
        if state == "NOT_APPLICABLE_WITH_JUSTIFICATION" and not str(justifications.get(field, "")).strip():
            errors.append(f"not_applicable_justification_missing:{field}")
        if state != "NOT_APPLICABLE_WITH_JUSTIFICATION" and field in justifications:
            errors.append(f"unexpected_field_justification:{field}")
    for field in ("deployment_id", "capability_id", "life_task_id", "contract_version"):
        if states[field] != "POPULATED":
            errors.append(f"identity_field_not_populated:{field}")
    if contract["level"] not in {None, "A1", "A1_PLUS"}:
        errors.append("level_scope_invalid")
    if contract["transfer_distance"] not in {None, "NONE"} and not contract["transfer_dimensions_changed"]:
        errors.append("transfer_dimensions_required")
    if contract["unexpected_event"] in {"PARTNER_MISUNDERSTANDS", "LEARNER_MISUNDERSTANDS"}:
        if contract["repair_requirement"] in {None, "NONE"}:
            errors.append("misunderstanding_requires_repair")
    if contract["media_payload_state"] == "DEFERRED_MEDIA_PAYLOAD" and states["media_payload_state"] != "DEFERRED_MEDIA_PAYLOAD":
        errors.append("media_deferred_state_mismatch")
    if contract["recording_state"] == "DEFERRED_MEDIA_PAYLOAD" and states["recording_state"] != "DEFERRED_MEDIA_PAYLOAD":
        errors.append("recording_deferred_state_mismatch")
    legacy = contract.get("legacy_source")
    if legacy:
        safe_populated = {
            "deployment_id", "capability_id", "life_task_id", "contract_version", "level", "skill", "source_refs",
        }
        for field, state in states.items():
            if state == "POPULATED" and field not in safe_populated:
                errors.append(f"legacy_adapter_false_population:{field}")
        for field in (
            "evidence_level", "accuracy_result", "meaning_result", "task_completion_result",
            "transfer_distance", "retention_stage", "evidence_validity",
        ):
            if states[field] == "POPULATED":
                errors.append(f"legacy_adapter_false_claim:{field}")
    return errors


def validate_files(ontology_path: Path, schema_path: Path, contract_path: Path | None = None) -> dict[str, Any]:
    errors: list[str] = []
    try:
        ontology = json.loads(Path(ontology_path).read_text(encoding="utf-8"))
        schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"validation_status": "FAIL", "error_count": 1, "errors": [f"source_unreadable:{exc}"]}
    if ontology != r2.build_ontology():
        errors.append("generated_ontology_drift")
    if schema != r2.build_contract_schema():
        errors.append("generated_schema_drift")
    errors.extend(validate_ontology(ontology))
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as exc:
        errors.append(f"schema_invalid:{exc}")
    if contract_path:
        try:
            contract = json.loads(Path(contract_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"contract_unreadable:{exc}")
        else:
            errors.extend(validate_contract(contract, schema))
    return {
        "validation_status": r2.STATUS if not errors else "FAIL_A1FS_V1_R2_BREADTH_CONTRACT",
        "error_count": len(errors), "errors": errors,
        "required_contract_field_count": len(r2.REQUIRED_CONTRACT_FIELDS),
        "enum_group_count": len(r2.ENUMS), "domain_count": len(r2.DOMAIN_DEFINITIONS),
        "next_short_step": r2.NEXT_SHORT_STEP if not errors else r2.TASK_ID,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ontology", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--contract", type=Path)
    args = parser.parse_args()
    result = validate_files(args.ontology, args.schema, args.contract)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
