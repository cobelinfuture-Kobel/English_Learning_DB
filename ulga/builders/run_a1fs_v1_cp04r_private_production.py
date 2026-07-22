#!/usr/bin/env python3
"""Run CP03 -> CP04 on private inputs and emit a safe 24-unit count readback."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_cp03_unified_existing_24_unit_binding as cp03  # noqa: E402
from ulga.builders import build_a1fs_v1_cp04_unified_content_exercise_scene_candidates as cp04  # noqa: E402
from ulga.validators import validate_a1fs_v1_cp03_unified_existing_24_unit_binding as cp03_validator  # noqa: E402
from ulga.validators import validate_a1fs_v1_cp04_unified_content_exercise_scene_candidates as cp04_validator  # noqa: E402

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Metadata-only private pipeline orchestration and aggregate/per-unit count readback; no source text, prompt, answer, transcript, learner response, or canonical Authority write is produced."

TASK_ID = "A1FS-V1-CP04R_RealPrivateCandidateBuildAnd24UnitCountReadback"
PROGRAM_ID = cp04.PROGRAM_ID
SCHEMA_VERSION = "a1fs.v1.cp04r.private_candidate_build_readback.v1"
PASS_STATUS = "PASS_CP04R_PRIVATE_PIPELINE_EXECUTED_AND_COUNTS_RECONCILED"
NEXT_SHORT_STEP = cp04.NEXT_SHORT_STEP

READBACK_PATH = REPO_ROOT / ".local/a1fs_v1/cp04r/real_private_candidate_build_readback.safe.json"
REPORT_PATH = REPO_ROOT / ".local/a1fs_v1/cp04r/real_private_candidate_build_readback.validation.json"
EXECUTION_MODES = {"REAL_PRIVATE_PRODUCTION", "SYNTHETIC_TEST"}


class PrivateProductionRunError(ValueError):
    """Fail-closed private input, validation, reconciliation, or safe-output error."""


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _require_pass(report: Mapping[str, Any], expected: str, stage: str) -> None:
    if report.get("validation_status") != expected or report.get("errors") != []:
        raise PrivateProductionRunError(f"{stage}_validation_failed:{report.get('errors')}")


def _safe_scan(value: Any) -> None:
    forbidden = {
        "text",
        "title",
        "payload",
        "prompt",
        "prompt_text",
        "answer",
        "answer_key",
        "accepted_texts",
        "transcript",
        "transcript_text",
        "learner_response",
    }

    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                if str(key).casefold() in forbidden:
                    raise PrivateProductionRunError(f"private_or_learner_content_leak:{key}")
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(value)


def build_readback(
    cp03_artifact: Mapping[str, Any],
    cp04_artifact: Mapping[str, Any],
    *,
    execution_mode: str,
) -> dict[str, Any]:
    if execution_mode not in EXECUTION_MODES:
        raise PrivateProductionRunError("execution_mode_invalid")
    if cp03_artifact.get("task_id") != cp03.TASK_ID:
        raise PrivateProductionRunError("cp03_task_id_mismatch")
    if cp04_artifact.get("task_id") != cp04.TASK_ID:
        raise PrivateProductionRunError("cp04_task_id_mismatch")
    if cp03_artifact.get("next_short_step") != cp04.TASK_ID:
        raise PrivateProductionRunError("cp03_cp04_lineage_mismatch")
    if cp04_artifact.get("next_short_step") != NEXT_SHORT_STEP:
        raise PrivateProductionRunError("cp04_next_short_step_mismatch")

    cp03_units = cp03_artifact.get("learning_units")
    cp04_units = cp04_artifact.get("learning_units")
    if not isinstance(cp03_units, list) or not isinstance(cp04_units, list):
        raise PrivateProductionRunError("learning_units_invalid")
    if len(cp03_units) != 24 or len(cp04_units) != 24:
        raise PrivateProductionRunError("existing_learning_unit_count_not_24")

    cp03_by_id = {str(row.get("learning_unit_id") or ""): row for row in cp03_units}
    cp04_by_id = {str(row.get("learning_unit_id") or ""): row for row in cp04_units}
    if "" in cp03_by_id or set(cp03_by_id) != set(cp04_by_id) or len(cp03_by_id) != 24:
        raise PrivateProductionRunError("existing_24_unit_identity_set_mismatch")

    unit_readback: list[dict[str, Any]] = []
    for sequence_index in range(1, 25):
        cp03_row = next(
            (row for row in cp03_units if row.get("sequence_index") == sequence_index), None
        )
        cp04_row = next(
            (row for row in cp04_units if row.get("sequence_index") == sequence_index), None
        )
        if cp03_row is None or cp04_row is None:
            raise PrivateProductionRunError(f"unit_sequence_missing:{sequence_index}")
        identity = (
            cp03_row.get("learning_unit_id"),
            cp03_row.get("grammar_unit_id"),
            cp03_row.get("internal_stage"),
            cp03_row.get("canonical_egp_row_ids"),
        )
        actual_identity = (
            cp04_row.get("learning_unit_id"),
            cp04_row.get("grammar_unit_id"),
            cp04_row.get("internal_stage"),
            cp04_row.get("canonical_egp_row_ids"),
        )
        if identity != actual_identity:
            raise PrivateProductionRunError(
                f"unit_identity_drift:{cp03_row.get('learning_unit_id')}"
            )

        cp03_raz_count = cp03_row.get("raz_admitted_asset_binding", {}).get(
            "material_count"
        )
        cp04_counts = cp04_row.get("candidate_counts")
        if not isinstance(cp04_counts, Mapping):
            raise PrivateProductionRunError(
                f"candidate_counts_missing:{cp04_row.get('learning_unit_id')}"
            )
        if cp04_counts.get("raz_content_candidate_count") != cp03_raz_count:
            raise PrivateProductionRunError(
                f"unit_raz_count_not_reconciled:{cp04_row.get('learning_unit_id')}"
            )

        unit_readback.append(
            {
                "learning_unit_id": cp04_row["learning_unit_id"],
                "grammar_unit_id": cp04_row["grammar_unit_id"],
                "sequence_index": sequence_index,
                "internal_stage": cp04_row["internal_stage"],
                "canonical_egp_row_count": len(cp04_row["canonical_egp_row_ids"]),
                "m11b_reviewed_content_item_count": cp03_row[
                    "m11b_reviewed_content_binding"
                ]["admitted_item_count"],
                "raz_material_binding_count": cp03_raz_count,
                "content_candidate_count": cp04_counts["content_candidate_count"],
                "exercise_candidate_count": cp04_counts["exercise_candidate_count"],
                "ready_reuse_exercise_candidate_count": cp04_counts[
                    "ready_reuse_exercise_candidate_count"
                ],
                "pending_raz_exercise_derivation_candidate_count": cp04_counts[
                    "pending_raz_exercise_derivation_candidate_count"
                ],
                "scene_candidate_count": cp04_counts["scene_candidate_count"],
                "candidate_population_status": cp04_row[
                    "candidate_population_status"
                ],
            }
        )

    cp03_summary = cp03_artifact.get("coverage_summary", {})
    cp04_summary = cp04_artifact.get("coverage_summary", {})
    if cp03_summary.get("existing_learning_unit_count") != 24:
        raise PrivateProductionRunError("cp03_summary_unit_count_not_24")
    if cp04_summary.get("existing_learning_unit_count") != 24:
        raise PrivateProductionRunError("cp04_summary_unit_count_not_24")
    if cp03_summary.get("new_learning_unit_count") != 0:
        raise PrivateProductionRunError("cp03_new_learning_unit_detected")
    if cp04_summary.get("new_learning_unit_count") != 0:
        raise PrivateProductionRunError("cp04_new_learning_unit_detected")
    if cp03_summary.get("raz_material_unit_binding_count") != cp04_summary.get(
        "raz_material_binding_candidate_count"
    ):
        raise PrivateProductionRunError("aggregate_raz_binding_count_not_reconciled")
    if cp03_summary.get("raz_distinct_bound_material_count") != cp04_summary.get(
        "distinct_raz_material_source_count"
    ):
        raise PrivateProductionRunError("aggregate_distinct_raz_count_not_reconciled")

    readback = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "safe_private_pipeline_aggregate_and_24_unit_count_readback",
        "scope": "A1_A1_PLUS_ONLY",
        "execution_mode": execution_mode,
        "pipeline_contract": {
            "stages": [cp03.TASK_ID, cp04.TASK_ID, TASK_ID],
            "course_container": "EXISTING_24_CANONICAL_UNITS_ONLY",
            "new_unit_creation_allowed": False,
            "private_source_payload_in_readback_allowed": False,
            "learner_facing_publication_allowed": False,
        },
        "source_identity": {
            "cp03_task_id": cp03_artifact["task_id"],
            "cp03_sha256": cp04._sha256_value(cp03_artifact),
            "cp04_task_id": cp04_artifact["task_id"],
            "cp04_sha256": cp04._sha256_value(cp04_artifact),
            "raz_registry_package_sha256": cp03_artifact["source_identity"][
                "raz_registry_package_sha256"
            ],
        },
        "coverage_summary": {
            "existing_learning_unit_count": 24,
            "new_learning_unit_count": 0,
            "m11b_reviewed_content_item_count": cp03_summary[
                "m11b_reviewed_content_item_count"
            ],
            "raz_promoted_material_input_count": cp03_summary[
                "raz_promoted_material_input_count"
            ],
            "raz_distinct_bound_material_count": cp03_summary[
                "raz_distinct_bound_material_count"
            ],
            "raz_material_unit_binding_count": cp03_summary[
                "raz_material_unit_binding_count"
            ],
            "raz_covered_existing_unit_count": cp03_summary[
                "raz_covered_existing_unit_count"
            ],
            "content_candidate_count": cp04_summary["content_candidate_count"],
            "exercise_candidate_count": cp04_summary["exercise_candidate_count"],
            "ready_reuse_exercise_candidate_count": cp04_summary[
                "ready_reuse_exercise_candidate_count"
            ],
            "pending_raz_exercise_derivation_candidate_count": cp04_summary[
                "pending_raz_exercise_derivation_candidate_count"
            ],
            "scene_candidate_count": cp04_summary["scene_candidate_count"],
            "authority_backed_scene_unit_count": cp04_summary[
                "authority_backed_scene_unit_count"
            ],
            "scene_authority_gap_unit_count": cp04_summary[
                "scene_authority_gap_unit_count"
            ],
            "candidate_envelope_complete_unit_count": cp04_summary[
                "candidate_envelope_complete_unit_count"
            ],
        },
        "unit_count_readback": unit_readback,
        "capability_delta": {
            "cp03_private_binding_rebuilt_and_validated": True,
            "cp04_private_candidate_envelopes_built_and_validated": True,
            "exact_24_unit_counts_emitted": True,
            "existing_24_unit_curriculum_preserved": True,
        },
        "claim_boundaries": {
            "canonical_authority_write_performed": False,
            "private_source_payload_included": False,
            "learner_facing_content_created": False,
            "candidate_admission_decision_created": False,
            "runtime_publication_claimed": False,
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
            "a2_a2plus_in_scope": False,
        },
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    _safe_scan(readback)
    return readback


def run_pipeline(
    cp01_path: Path,
    cp02_path: Path,
    registry_path: Path,
    *,
    cp03_output: Path,
    cp03_report: Path,
    cp04_output: Path,
    cp04_report: Path,
    readback_output: Path,
    readback_report: Path,
    execution_mode: str,
) -> dict[str, Any]:
    cp01_artifact = _read(cp01_path)
    cp02_artifact = _read(cp02_path)
    registry_package = _read(registry_path)

    cp03_artifact = cp03.build_artifact(cp01_artifact, cp02_artifact, registry_package)
    cp03_validation = cp03_validator.validate_artifact(
        cp03_artifact, cp01_artifact, cp02_artifact, registry_package
    )
    _require_pass(cp03_validation, cp03.PASS_STATUS, "cp03")

    cp04_artifact = cp04.build_artifact(cp03_artifact)
    cp04_validation = cp04_validator.validate_artifact(cp04_artifact, cp03_artifact)
    _require_pass(cp04_validation, cp04.PASS_STATUS, "cp04")

    readback = build_readback(
        cp03_artifact, cp04_artifact, execution_mode=execution_mode
    )
    from ulga.validators.validate_a1fs_v1_cp04r_real_private_candidate_build import validate_artifact

    validation = validate_artifact(readback, cp03_artifact, cp04_artifact)
    _require_pass(validation, PASS_STATUS, "cp04r")

    _write(cp03_output, cp03_artifact)
    _write(cp03_report, cp03_validation)
    _write(cp04_output, cp04_artifact)
    _write(cp04_report, cp04_validation)
    _write(readback_output, readback)
    _write(readback_report, validation)
    return validation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cp01", type=Path, default=cp03.CP01_PATH)
    parser.add_argument("--cp02", type=Path, default=cp03.CP02_PATH)
    parser.add_argument("--raz-registry", type=Path, default=cp03.RAZ_REGISTRY_PATH)
    parser.add_argument("--cp03-output", type=Path, default=cp03.OUTPUT_PATH)
    parser.add_argument("--cp03-report", type=Path, default=cp03.REPORT_PATH)
    parser.add_argument("--cp04-output", type=Path, default=cp04.OUTPUT_PATH)
    parser.add_argument("--cp04-report", type=Path, default=cp04.REPORT_PATH)
    parser.add_argument("--readback-output", type=Path, default=READBACK_PATH)
    parser.add_argument("--readback-report", type=Path, default=REPORT_PATH)
    parser.add_argument(
        "--execution-mode",
        choices=sorted(EXECUTION_MODES),
        default="REAL_PRIVATE_PRODUCTION",
    )
    args = parser.parse_args(argv)
    try:
        validation = run_pipeline(
            args.cp01,
            args.cp02,
            args.raz_registry,
            cp03_output=args.cp03_output,
            cp03_report=args.cp03_report,
            cp04_output=args.cp04_output,
            cp04_report=args.cp04_report,
            readback_output=args.readback_output,
            readback_report=args.readback_report,
            execution_mode=args.execution_mode,
        )
        print(json.dumps(validation, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, KeyError, TypeError, ValueError, PrivateProductionRunError) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
