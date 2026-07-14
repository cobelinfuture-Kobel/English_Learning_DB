#!/usr/bin/env python3
"""Independently reconstruct and validate the 54-record S12D consumer overlay."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_raz_af_a1_a1plus_observational_consumer import (  # noqa: E402
    CLAIM_BOUNDARIES,
    PASS_STATUS,
    ConsumerBuildError,
    build_artifacts,
    canonical_json,
    load_s12b_records,
    read_json,
    schema_validators,
    selected_records,
    sha256_file,
    sha256_text,
)
from ulga.builders.build_raz_af_full_language_pedagogy_observations import load_authorities  # noqa: E402
from ulga.validators.validate_a1_a1plus_local_reading_practice_bank import validate_materialization  # noqa: E402
from ulga.validators.validate_raz_af_full_language_pedagogy_observations import (  # noqa: E402
    _authority_reference_errors,
)

TASK_ID = "RAZ-AF-S12D_A1A1PlusObservationalConsumerAndM04B2CompatibilityQA"
FORBIDDEN_KEYS = {
    "text", "source_text", "source_sentences", "sentence", "sentences", "passage", "prompt", "answer",
    "answer_text", "accepted_answers", "surface_form", "normalized_form", "lemma_candidate", "observed_chunk",
    "source_payload", "record_payload", "learner_facing_text", "canonical_write", "authority_write",
}


def safe_scan(value: Any, path: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            lowered = str(key).lower()
            if lowered in FORBIDDEN_KEYS:
                errors.append(f"forbidden_safe_key:{path}.{key}")
            errors.extend(safe_scan(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(safe_scan(child, f"{path}[{index}]"))
    return errors


def _schema_errors(artifact: Mapping[str, Any], report: Mapping[str, Any]) -> list[str]:
    binding_validator, report_validator = schema_validators()
    errors = []
    for index, binding in enumerate(artifact.get("bindings", [])):
        errors.extend(
            f"binding_schema:{index}:{'.'.join(map(str, error.absolute_path)) or '$'}:{error.message}"
            for error in binding_validator.iter_errors(binding)
        )
    errors.extend(
        f"safe_schema:{'.'.join(map(str, error.absolute_path)) or '$'}:{error.message}"
        for error in report_validator.iter_errors(report)
    )
    return errors


def validate_consumer(
    artifact: Mapping[str, Any],
    report: Mapping[str, Any],
    selected: list[Mapping[str, Any]],
    m04b2_private: Mapping[str, Any],
    m04b2_safe: Mapping[str, Any],
    s12b_records: Mapping[str, Mapping[str, Any]],
    s12b_inventory: Mapping[str, Any],
    s12b_safe: Mapping[str, Any],
    query_index: Mapping[str, Any],
    coverage: Mapping[str, Any],
    upstream_hashes: Mapping[str, Any],
) -> dict[str, Any]:
    errors = _schema_errors(artifact, report)
    errors.extend(safe_scan(artifact, "$.artifact"))
    errors.extend(safe_scan(report, "$.safe_report"))
    m04b2_validation = validate_materialization(m04b2_private, m04b2_safe)
    if m04b2_validation.get("validation_status") != "PASS_LOCAL_READING_PRACTICE_BANK":
        errors.append("m04b2_independent_validation_failed")
    try:
        expected_artifact, expected_report = build_artifacts(
            selected, m04b2_safe, s12b_records, s12b_inventory, s12b_safe,
            query_index, coverage, upstream_hashes,
        )
    except (ConsumerBuildError, KeyError, TypeError, ValueError) as exc:
        errors.append(f"independent_reconstruction_failed:{exc}")
        expected_artifact, expected_report = {}, {}
    declared_bindings = artifact.get("bindings", [])
    refs = [
        binding.get("selection_identity", {}).get("source_unit_ref")
        for binding in declared_bindings if isinstance(binding, Mapping)
    ]
    expected_refs = {row["source_unit_ref"] for row in selected}
    missing, extra = expected_refs - set(refs), set(refs) - expected_refs
    duplicate_count = len(refs) - len(set(refs))
    if missing:
        errors.append(f"missing_bindings:{len(missing)}")
    if extra:
        errors.append(f"extra_bindings:{len(extra)}")
    if duplicate_count:
        errors.append(f"duplicate_bindings:{duplicate_count}")
    if artifact != expected_artifact:
        errors.append("binding_artifact_reconstruction_mismatch")
    if report != expected_report:
        errors.append("safe_report_reconstruction_mismatch")
    if artifact.get("bindings_sha256") != sha256_text(canonical_json(declared_bindings)):
        errors.append("bindings_sha256_mismatch")
    if report.get("bindings_sha256") != artifact.get("bindings_sha256"):
        errors.append("safe_bindings_sha256_mismatch")
    authority_data = load_authorities()
    authority_errors = []
    for ref in sorted(expected_refs & set(s12b_records)):
        authority_errors.extend(_authority_reference_errors(ref, s12b_records[ref]["observations"], authority_data))
    if authority_errors:
        errors.append(f"invalid_authority_refs:{len(authority_errors)}")
    if report.get("claim_boundaries") != CLAIM_BOUNDARIES:
        errors.append("claim_boundary_mismatch")
    boundaries = report.get("claim_boundaries", {})
    if boundaries.get("learner_facing_material_created") is not False:
        errors.append("learner_facing_material_claim")
    if boundaries.get("canonical_authority_write_performed") is not False:
        errors.append("canonical_authority_write_claim")
    if boundaries.get("promotion_performed") is not False:
        errors.append("promotion_claim")
    for binding in declared_bindings:
        decision = binding.get("consumer_decision", {}) if isinstance(binding, Mapping) else {}
        canonical = binding.get("canonical_consumer_state", {}) if isinstance(binding, Mapping) else {}
        identity = binding.get("selection_identity", {}) if isinstance(binding, Mapping) else {}
        selected_row = next((row for row in selected if row["source_unit_ref"] == identity.get("source_unit_ref")), None)
        if decision.get("promotion_status") != "not_promoted":
            errors.append(f"promotion_status_invalid:{identity.get('source_unit_ref')}")
        if selected_row and canonical.get("e4s_situation_domain") != selected_row["e4s_situation_domain"]:
            errors.append(f"situation_domain_silent_overwrite:{identity.get('source_unit_ref')}")
        if decision.get("canonical_eligibility_status") in {"BLOCKED_SOURCE_INTEGRITY", "BLOCKED_CANONICAL_CONTRACT"}:
            expected_binding = next((item for item in expected_artifact.get("bindings", []) if item["selection_identity"]["source_unit_ref"] == identity.get("source_unit_ref")), None)
            if expected_binding and expected_binding["consumer_decision"]["canonical_eligibility_status"] != decision.get("canonical_eligibility_status"):
                errors.append(f"observational_eligibility_override:{identity.get('source_unit_ref')}")
    return {
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "selected_source_count": len(selected),
        "binding_count": len(declared_bindings),
        "missing_binding_count": len(missing),
        "extra_binding_count": len(extra),
        "duplicate_binding_count": duplicate_count,
        "invalid_authority_ref_count": len(authority_errors),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--s12b-root", type=Path, required=True)
    parser.add_argument("--s12c-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--m04b2-private", type=Path, required=True)
    parser.add_argument("--m04b2-safe", type=Path, required=True)
    parser.add_argument("--selected-index", type=Path, default=REPO_ROOT / "ulga/graph/reading_sources/a1_a1plus_selected/index.json")
    parser.add_argument("--validation-report", type=Path)
    args = parser.parse_args(argv)
    try:
        selected, manifest_hashes = selected_records(args.selected_index)
        m04b2_private, m04b2_safe = read_json(args.m04b2_private), read_json(args.m04b2_safe)
        records, inventory, s12b_safe = load_s12b_records(args.s12b_root)
        query_index, coverage = read_json(args.s12c_root / "query_index.json"), read_json(args.s12c_root / "coverage.json")
        artifact, safe_report = read_json(args.output_root / "bindings.json"), read_json(args.output_root / "safe_report.json")
        hashes = {
            "m04b1_manifest_and_shards": manifest_hashes,
            "m04b2_private_sha256": sha256_file(args.m04b2_private),
            "m04b2_safe_sha256": sha256_file(args.m04b2_safe),
            "s12b_inventory_sha256": sha256_file(args.s12b_root / "inventory.json"),
            "s12b_safe_sha256": sha256_file(args.s12b_root / "validation.json"),
            "s12c_query_index_sha256": sha256_file(args.s12c_root / "query_index.json"),
            "s12c_coverage_sha256": sha256_file(args.s12c_root / "coverage.json"),
        }
        result = validate_consumer(
            artifact, safe_report, selected, m04b2_private, m04b2_safe, records,
            inventory, s12b_safe, query_index, coverage, hashes,
        )
    except (ConsumerBuildError, OSError, KeyError, TypeError, ValueError) as exc:
        result = {"task_id": TASK_ID, "validation_status": "FAIL", "error_count": 1, "errors": [str(exc)]}
    if args.validation_report:
        args.validation_report.parent.mkdir(parents=True, exist_ok=True)
        args.validation_report.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0 if result["validation_status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
