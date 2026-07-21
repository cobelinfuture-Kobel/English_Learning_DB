#!/usr/bin/env python3
"""Validate the RAZ A-W minimal derived-material extraction package."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_aw_derived_material_extraction_minimal as builder

PASS_STATUS = "PASS_RAZ_AW_DERIVED_MATERIAL_EXTRACTION_MINIMAL_VALIDATION"


def validate_package(
    package: Mapping[str, Any],
    *,
    expected_counts: Mapping[str, int] = builder.EXPECTED_COUNTS,
    levels: Sequence[str] = builder.LEVELS,
) -> list[str]:
    errors: list[str] = []

    def require(condition: bool, code: str) -> None:
        if not condition:
            errors.append(code)

    require(package.get("task_id") == builder.TASK_ID, "task_id_mismatch")
    require(
        package.get("schema_version") == builder.SCHEMA_VERSION,
        "schema_version_mismatch",
    )
    require(
        package.get("validation_status") == builder.PASS_STATUS,
        "builder_status_not_pass",
    )
    stored_hash = package.get("package_sha256")
    without_hash = dict(package)
    without_hash.pop("package_sha256", None)
    require(
        isinstance(stored_hash, str)
        and stored_hash == deep.sha256_value(without_hash),
        "package_hash_mismatch",
    )

    scope = package.get("source_scope")
    require(isinstance(scope, Mapping), "source_scope_missing")
    if isinstance(scope, Mapping):
        for key, expected in expected_counts.items():
            require(scope.get(key) == expected, f"count_mismatch:{key}")

    reality = package.get("source_reality")
    require(isinstance(reality, Mapping), "source_reality_missing")
    if isinstance(reality, Mapping):
        require(
            reality.get("audited_levels") == list(levels),
            "audited_levels_mismatch",
        )
        require(
            reality.get("audited_registry_counts") == dict(expected_counts),
            "audited_registry_counts_mismatch",
        )
        require(
            reality.get("scene_evidence_mode")
            == "DERIVED_SCENE_STRUCTURE_ONLY",
            "scene_mode_mismatch",
        )
        require(
            reality.get("theme_granularity")
            == {
                "A_I": "BOOK_AND_UNIT",
                "J_W": "BOOK_ONLY_WITH_UNIT_PROJECTION",
            },
            "theme_granularity_mismatch",
        )

    page_rows = package.get("page_unit_evidence")
    require(isinstance(page_rows, list), "page_unit_evidence_missing")
    if isinstance(page_rows, list):
        require(
            len(page_rows) == expected_counts["page_unit_count"],
            "page_unit_evidence_count_mismatch",
        )
        require(
            all(
                isinstance(row, Mapping)
                and row.get("scene_evidence_status")
                == "DERIVED_SCENE_STRUCTURE_ONLY"
                for row in page_rows
            ),
            "direct_image_claim_detected",
        )

    require(
        package.get("claim_boundaries") == builder.CLAIM_BOUNDARIES,
        "claim_boundaries_mismatch",
    )
    gate = package.get("extraction_gate")
    require(isinstance(gate, Mapping), "extraction_gate_missing")
    if isinstance(gate, Mapping):
        require(
            gate.get("decision")
            == "DERIVED_MATERIAL_READY_FOR_GOVERNANCE_BINDING",
            "gate_not_ready",
        )
        require(
            gate.get("ready_for_review_bridge_linkage_binding") is True,
            "governance_binding_not_ready",
        )
        require(
            gate.get("ready_for_canonical_promotion") is False,
            "canonical_promotion_opened",
        )
        require(
            gate.get("ready_for_learning_unit_population") is False,
            "unit_population_opened",
        )

    errors.extend(builder.base.scan_forbidden_safe_keys(package))
    return errors


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=builder.DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        payload = deep.read_json(args.input)
        if not isinstance(payload, Mapping):
            raise ValueError("package_not_object")
        errors = validate_package(payload)
        print(
            json.dumps(
                {
                    "task_id": builder.TASK_ID,
                    "validation_status": PASS_STATUS if not errors else "FAIL",
                    "decision": payload.get("extraction_gate", {}).get("decision"),
                    "error_count": len(errors),
                    "errors": errors,
                    "package_sha256": payload.get("package_sha256"),
                },
                sort_keys=True,
            )
        )
        return 0 if not errors else 1
    except (OSError, ValueError, TypeError, KeyError, deep.AlignmentError) as exc:
        print(
            json.dumps(
                {
                    "task_id": builder.TASK_ID,
                    "validation_status": "FAIL",
                    "error_count": 1,
                    "errors": [str(exc)],
                },
                sort_keys=True,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
