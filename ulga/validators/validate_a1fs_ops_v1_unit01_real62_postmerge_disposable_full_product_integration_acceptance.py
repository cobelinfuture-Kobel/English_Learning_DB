#!/usr/bin/env python3
"""Independently validate disposable full-product Real62 Unit01 integration."""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import (
    build_a1fs_ops_v1_unit01_real62_postmerge_disposable_full_product_integration_acceptance
    as builder,
)
from ulga.validators import (
    validate_a1fs_v1_razq01g_unit01_real_content_learner_product_release_readiness_acceptance
    as razq01g_validator,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Independently reads the disposable Real62 integration report, external hash-bound prerequisite evidence, disposable-internal multisession authority, product roots, SQLite denominators, and existing RAZQ01G release candidate; it creates no content, bank, planner, runtime, learner state, scoring authority, audio, A2, or Unit02-Unit24 artifact."
PASS_STATUS = "PASS_A1FS_OPS_V1_UNIT01_REAL62_DISPOSABLE_FULL_PRODUCT_INTEGRATION_VALIDATION"
FAIL_STATUS = "FAIL_A1FS_OPS_V1_UNIT01_REAL62_DISPOSABLE_FULL_PRODUCT_INTEGRATION_VALIDATION"


def _count(database: Path, table: str) -> int:
    with sqlite3.connect(Path(database)) as connection:
        row = connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()
    return int(row[0])


def validate(
    *,
    source_product_root: Path,
    disposable_product_root: Path,
    approved_content: Mapping[str, Any],
    multisession_root: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    source_product_root = Path(source_product_root).resolve()
    disposable_product_root = Path(disposable_product_root).resolve()
    multisession_root = Path(multisession_root).resolve()
    report_path = disposable_product_root / "shared/reports" / builder.REPORT_NAME
    try:
        report = builder.load(report_path)
        core = {k: v for k, v in report.items() if k != "readback_sha256"}
        if report.get("readback_sha256") != builder.digest(core):
            raise ValueError("readback_digest_invalid")
        if report.get("status") != builder.PASS_STATUS:
            raise ValueError("readback_status_invalid")
        if Path(report.get("source_product_root", "")).resolve() != source_product_root:
            raise ValueError("source_product_root_identity_invalid")
        if Path(report.get("disposable_product_root", "")).resolve() != disposable_product_root:
            raise ValueError("disposable_product_root_identity_invalid")

        prior = builder._validate_prior_multisession(
            multisession_root,
            approved_content,
        )
        if report.get("prior_multisession_readback_sha256") != prior.get(
            "readback_sha256"
        ):
            raise ValueError("prior_multisession_readback_identity_invalid")

        source = builder._product_identity(source_product_root)
        if source["release_manifest_sha256"] != report.get(
            "source_release_manifest_sha256"
        ):
            raise ValueError("source_release_manifest_drift")
        if source["database_projection"]["sha256"] != report.get(
            "source_database_projection_sha256"
        ):
            raise ValueError("source_database_projection_drift")

        database = disposable_product_root / "shared/database/learner_runtime.sqlite3"
        if _count(database, "u01qb02_item_catalog") != 474:
            raise ValueError("combined_runtime_item_count_invalid")
        if _count(database, "razq01e_extension_items") != 186:
            raise ValueError("extension_item_count_invalid")
        if report.get("idempotent_materialization_reused") is not True:
            raise ValueError("idempotent_materialization_not_proven")
        if report.get("source_product_root_unchanged") is not True:
            raise ValueError("source_product_root_not_preserved")
        if report.get("learner_owned_state_preserved_during_materialization") is not True:
            raise ValueError("learner_owned_state_preservation_not_proven")
        if report.get("activation_simulation_pass") is not True:
            raise ValueError("activation_simulation_not_proven")
        if report.get("rollback_simulation_pass") is not True:
            raise ValueError("rollback_simulation_not_proven")
        if report.get("formal_production_activation_approved") is not False:
            raise ValueError("production_activation_boundary_invalid")
        if report.get("production_root_mutated") is not False:
            raise ValueError("production_root_mutation_boundary_invalid")
        if report.get("unit02_to_unit24_modified") is not False:
            raise ValueError("unit_scope_boundary_invalid")
        if report.get("a2_unlocked") is not False:
            raise ValueError("a2_boundary_invalid")

        expected_internal_multisession_root = (
            disposable_product_root / "shared/real62_unit01_multisession_evidence"
        ).resolve()
        internal_multisession_root = Path(
            report.get("disposable_multisession_root", "")
        ).resolve()
        if internal_multisession_root != expected_internal_multisession_root:
            raise ValueError("disposable_multisession_root_identity_invalid")
        if report.get("disposable_multisession_status") != builder.razq01f.PASS_STATUS:
            raise ValueError("disposable_multisession_status_invalid")
        internal_readback = builder.load(
            internal_multisession_root / builder.PRIOR_READBACK_NAME
        )
        if internal_readback.get("readback_sha256") != report.get(
            "disposable_multisession_readback_sha256"
        ):
            raise ValueError("disposable_multisession_readback_identity_invalid")

        builder.razq01f.install_fullfix()
        release_root = (
            disposable_product_root / "shared/real62_unit01_release_candidate"
        )
        release_result = razq01g_validator.validate(
            database=database,
            approved_content=approved_content,
            multisession_root=internal_multisession_root,
            release_root=release_root,
        )
        if release_result.get("validation_status") != razq01g_validator.PASS_STATUS:
            raise ValueError("razq01g_release_validation_failed")
        if (
            release_result.get("exposure_count") != 1
            or release_result.get("attempt_count") != 1
        ):
            raise ValueError("release_canary_denominator_invalid")

        with sqlite3.connect(database) as connection:
            parallel = connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name LIKE 'a1fs_ops_real62%'"
            ).fetchall()
        if parallel:
            raise ValueError("parallel_runtime_table_created")
    except Exception as exc:
        errors.append(str(exc))

    return {
        "validation_status": PASS_STATUS if not errors else FAIL_STATUS,
        "error_count": len(errors),
        "errors": errors,
        "source_product_root": str(source_product_root),
        "disposable_product_root": str(disposable_product_root),
        "combined_runtime_item_count": 0 if errors else 474,
        "extension_item_count": 0 if errors else 186,
        "production_root_mutated": False,
        "formal_production_activation_approved": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-product-root", type=Path, required=True)
    parser.add_argument("--disposable-product-root", type=Path, required=True)
    parser.add_argument("--approved-content", type=Path, required=True)
    parser.add_argument("--multisession-root", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = validate(
        source_product_root=args.source_product_root,
        disposable_product_root=args.disposable_product_root,
        approved_content=builder.load(args.approved_content),
        multisession_root=args.multisession_root,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["validation_status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
