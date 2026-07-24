#!/usr/bin/env python3
"""Materialize the governed private chain required by the KET99 M4D canary.

The runner reuses the existing CP03-CP07D and M3/M4 builders. It creates a
separate canary learner-state database, never edits an operator learner state,
and never changes canonical curriculum, lesson selection policy, mastery, or
A2 boundaries.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1_a1plus_cross_skill_learning_units as unit_contract
from ulga.builders import build_a1fs_v1_cp01_existing_24_unit_curriculum_backfill as cp01
from ulga.builders import build_a1fs_v1_cp02_per_unit_authority_bindings as cp02
from ulga.builders import build_a1fs_v1_cp03_unified_existing_24_unit_binding as cp03
from ulga.builders import build_a1fs_v1_cp04_unified_content_exercise_scene_candidates as cp04
from ulga.builders import build_a1fs_v1_cp05_private_candidate_materialization_and_admission as cp05
from ulga.builders import build_a1fs_v1_cp06_grammar_spiral_role_population_and_content_capacity as cp06
from ulga.builders import build_a1fs_v1_cp07a_unified_runtime_activity_contract_and_lineage_adapter as cp07a
from ulga.builders import build_a1fs_v1_cp07c_unified_m4_lesson_composition as cp07c
from ulga.builders import build_a1fs_v1_cp07d_private_four_skill_delivery_consumer as cp07d
from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.builders import build_a1fs_v1_m4_lesson_planner_selection_a2_lock as m4
from ulga.builders import build_ket99_pku_selected_reading_asset_consumer_activation_canary as m4d
from ulga.builders import build_ket99_pku_selected_reading_teacher_delivery_remediation_assets as m4c
from ulga.builders import build_raz_ai_acl_v1_s02_semantic_dedup as raz_dedup
from ulga.builders import build_raz_ai_acl_v1_s05_material_registry as raz_registry

ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "KET99-PK-M4D1_PrivateRuntimeChainMaterializationAndCanaryReplay"
SCHEMA_VERSION = "ket99.pku.m4d1.private_runtime_chain_materialization.v1"
PASS_STATUS = "PASS_KET99_PK_M4D1_PRIVATE_RUNTIME_CHAIN_AND_CANARY_READY"
NEXT_SHORT_STEP = "KET99-PK-M4E_SelectedReadingRemediationTriggerBindingAndPrivateErrorCanary"
CANARY_LEARNER_ID = "ket99_m4d_chain_canary"
CANARY_PLAN_ID = "KET99-M4D-CHAIN-CANARY-PLAN"
STAGE_ORDER = (
    "CP03",
    "CP04",
    "CP05",
    "CP06",
    "CP07A",
    "M3",
    "M4",
    "CP07C",
    "CP07D",
    "M4D",
)
DEFAULT_OUTPUT = ROOT / ".local/a1fs_v1/ket99_pku_m4d1/private_chain_materialization.safe.json"
DEFAULT_REPORT = ROOT / ".local/a1fs_v1/ket99_pku_m4d1/private_chain_materialization.validation.json"
DEFAULT_STATE_DB = ROOT / ".local/a1fs_v1/ket99_pku_m4d1/canary_learner_state.sqlite3"
DEFAULT_M4_PLAN = ROOT / ".local/a1fs_v1/ket99_pku_m4d1/canary_lesson_plan.private.json"


class ChainMaterializationError(ValueError):
    """Fail-closed private-chain input, subprocess, or lineage error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ChainMaterializationError(f"json_object_required:{path}")
    return value


def write_json(path: Path, value: Mapping[str, Any], *, private: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
        if private:
            os.chmod(path, 0o600)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def discover_artifact(
    *,
    explicit: Path | None,
    filename: str,
    roots: Sequence[Path],
    preferred_relatives: Sequence[str] = (),
) -> Path:
    if explicit is not None:
        path = explicit.resolve()
        if not path.is_file():
            raise ChainMaterializationError(f"explicit_artifact_missing:{filename}:{path}")
        return path
    for root in roots:
        for relative in preferred_relatives:
            candidate = (root / relative).resolve()
            if candidate.is_file():
                return candidate
    matches: list[Path] = []
    for root in roots:
        if root.is_dir():
            matches.extend(path.resolve() for path in root.rglob(filename) if path.is_file())
    if not matches:
        raise ChainMaterializationError(f"artifact_not_found:{filename}")
    matches.sort(key=lambda path: (path.stat().st_mtime_ns, str(path)), reverse=True)
    return matches[0]


def module_command(module: str, *arguments: str | Path) -> list[str]:
    return [sys.executable, "-m", module, *(str(value) for value in arguments)]


def build_command_plan(paths: Mapping[str, Path]) -> list[tuple[str, list[str]]]:
    """Return the governed stage order; useful for audit and focused tests."""
    return [
        (
            "CP03",
            module_command(
                "ulga.builders.build_a1fs_v1_cp03_unified_existing_24_unit_binding",
                "--cp01", paths["cp01"], "--cp02", paths["cp02"],
                "--raz-registry", paths["registry"], "--output", paths["cp03"],
                "--report", paths["cp03_report"],
            ),
        ),
        (
            "CP04",
            module_command(
                "ulga.builders.build_a1fs_v1_cp04_unified_content_exercise_scene_candidates",
                "--cp03", paths["cp03"], "--output", paths["cp04"],
                "--report", paths["cp04_report"],
            ),
        ),
        (
            "CP05",
            module_command(
                "ulga.builders.build_a1fs_v1_cp05_private_candidate_materialization_and_admission",
                "--cp04", paths["cp04"], "--raz-registry", paths["registry"],
                "--semantic-dedup", paths["dedup"], "--source-root", paths["raz_source_root"],
                "--candidate-output", paths["cp05_candidate"],
                "--approved-output", paths["cp05_approved"],
                "--safe-output", paths["cp05_safe"],
                "--report-output", paths["cp05_report"],
            ),
        ),
        (
            "CP06",
            module_command(
                "ulga.builders.build_a1fs_v1_cp06_grammar_spiral_role_population_and_content_capacity",
                "--cp05-approved", paths["cp05_approved"], "--cp04", paths["cp04"],
                "--raz-registry", paths["registry"], "--unit-contract", paths["unit_contract"],
                "--output", paths["cp06"], "--report", paths["cp06_report"],
            ),
        ),
        (
            "CP07A",
            module_command(
                "ulga.builders.build_a1fs_v1_cp07a_unified_runtime_activity_contract_and_lineage_adapter",
                "build", "--m2-consumer", paths["m2"],
                "--cp05-approved", paths["cp05_approved"], "--cp06", paths["cp06"],
                "--output", paths["cp07a"], "--report", paths["cp07a_report"],
            ),
        ),
        (
            "M3",
            module_command(
                "ulga.builders.build_a1fs_v1_m3_learner_profile_session_state_storage",
                "init", "--database", paths["state_db"], "--consumer", paths["m2"],
            ),
        ),
        (
            "M4",
            module_command(
                "ulga.builders.build_a1fs_v1_m4_lesson_planner_selection_a2_lock",
                "plan", "--database", paths["state_db"], "--consumer", paths["m2"],
                "--graph", paths["m1"], "--learner-id", CANARY_LEARNER_ID,
                "--plan-id", CANARY_PLAN_ID,
            ),
        ),
        (
            "CP07C",
            module_command(
                "ulga.builders.build_a1fs_v1_cp07c_unified_m4_lesson_composition",
                "--m4-plan", paths["m4_plan"], "--m2-consumer", paths["m2"],
                "--m1-graph", paths["m1"], "--cp07a-index", paths["cp07a"],
                "--cp07b-overlay", paths["cp07b"], "--output", paths["cp07c"],
                "--report", paths["cp07c_report"],
            ),
        ),
        (
            "CP07D",
            module_command(
                "ulga.builders.build_a1fs_v1_cp07d_private_four_skill_delivery_consumer",
                "--m2-consumer", paths["m2"], "--cp05-approved", paths["cp05_approved"],
                "--cp07c-plan", paths["cp07c"], "--output", paths["cp07d"],
                "--report", paths["cp07d_report"],
            ),
        ),
        (
            "M4D",
            module_command(
                "ulga.builders.build_ket99_pku_selected_reading_asset_consumer_activation_canary",
                "--m4c-assets", paths["m4c"], "--cp07d-consumer", paths["cp07d"],
                "--output", paths["m4d"], "--report", paths["m4d_report"],
            ),
        ),
    ]


def run_command(command: Sequence[str], *, capture_json: bool = False) -> dict[str, Any] | None:
    completed = subprocess.run(
        list(command), cwd=ROOT, text=True, capture_output=True, check=False
    )
    if completed.returncode != 0:
        output = (completed.stdout + "\n" + completed.stderr).strip()
        raise ChainMaterializationError(
            f"subprocess_failed:{' '.join(command[2:4])}:{output[-2000:]}"
        )
    if not capture_json:
        return None
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ChainMaterializationError("subprocess_json_output_invalid") from exc
    if not isinstance(value, dict):
        raise ChainMaterializationError("subprocess_json_object_required")
    return value


def resolve_paths(args: argparse.Namespace) -> dict[str, Path]:
    input_roots = [ROOT / ".local"]
    if args.private_root is not None:
        input_roots.insert(0, args.private_root.resolve() / ".local")
    m1_path = discover_artifact(
        explicit=args.m1_graph,
        filename="a1a1plus_prerequisite_graph_and_coverage.private.json",
        roots=input_roots,
        preferred_relatives=(
            "a1fs_v1/runtime/m1/a1a1plus_prerequisite_graph_and_coverage.private.json",
            "a1fs_v1/m1/a1a1plus_prerequisite_graph_and_coverage.private.json",
        ),
    )
    m2_path = discover_artifact(
        explicit=args.m2_consumer,
        filename="four_skill_asset_body_consumer.private.json",
        roots=input_roots,
        preferred_relatives=(
            "a1fs_v1/runtime/m2/four_skill_asset_body_consumer.private.json",
            "a1fs_v1/m2/four_skill_asset_body_consumer.private.json",
        ),
    )
    cp07b_path = discover_artifact(
        explicit=args.cp07b_overlay,
        filename="ket99_instructional_sequence_overlay.safe.json",
        roots=input_roots,
        preferred_relatives=(
            "a1fs_v1/cp07f/r3g-precision-production/cp07b/ket99_instructional_sequence_overlay.safe.json",
            "a1fs_v1/cp07b/ket99_instructional_sequence_overlay.safe.json",
        ),
    )
    m4c_path = discover_artifact(
        explicit=args.m4c_assets,
        filename=m4c.DEFAULT_OUTPUT.name,
        roots=[ROOT / ".local", *input_roots],
        preferred_relatives=(
            "a1fs_v1/ket99_pku_m4c/selected_reading_teacher_delivery_remediation_assets.safe.json",
        ),
    )
    paths = {
        "cp01": cp01.OUTPUT_PATH,
        "cp02": cp02.OUTPUT_PATH,
        "registry": raz_registry.DEFAULT_OUTPUT,
        "dedup": raz_dedup.DEFAULT_OUTPUT,
        "unit_contract": unit_contract.OUTPUT_PATH,
        "raz_source_root": args.raz_source_root.resolve(),
        "m1": m1_path,
        "m2": m2_path,
        "cp07b": cp07b_path,
        "m4c": m4c_path,
        "cp03": cp03.OUTPUT_PATH,
        "cp03_report": cp03.REPORT_PATH,
        "cp04": cp04.OUTPUT_PATH,
        "cp04_report": cp04.REPORT_PATH,
        "cp05_candidate": cp05.DEFAULT_CANDIDATE_OUTPUT,
        "cp05_approved": cp05.DEFAULT_APPROVED_OUTPUT,
        "cp05_safe": cp05.DEFAULT_SAFE_OUTPUT,
        "cp05_report": cp05.DEFAULT_REPORT_OUTPUT,
        "cp06": cp06.DEFAULT_OUTPUT,
        "cp06_report": cp06.DEFAULT_REPORT,
        "cp07a": cp07a.DEFAULT_OUTPUT,
        "cp07a_report": cp07a.DEFAULT_REPORT,
        "state_db": args.state_db.resolve(),
        "m4_plan": args.m4_plan.resolve(),
        "cp07c": cp07c.DEFAULT_OUTPUT,
        "cp07c_report": cp07c.DEFAULT_REPORT,
        "cp07d": cp07d.DEFAULT_OUTPUT,
        "cp07d_report": cp07d.DEFAULT_REPORT,
        "m4d": m4d.DEFAULT_OUTPUT,
        "m4d_report": m4d.DEFAULT_REPORT,
    }
    for label in ("cp01", "cp02", "registry", "dedup", "unit_contract", "raz_source_root", "m1", "m2", "cp07b", "m4c"):
        if not paths[label].exists():
            raise ChainMaterializationError(f"required_input_missing:{label}:{paths[label]}")
    return paths


def materialize(paths: Mapping[str, Path]) -> dict[str, Any]:
    if paths["state_db"].exists():
        paths["state_db"].unlink()
    stages: list[dict[str, Any]] = []
    for stage, command in build_command_plan(paths):
        if stage == "M3":
            run_command(command)
            run_command(
                module_command(
                    "ulga.builders.build_a1fs_v1_m3_learner_profile_session_state_storage",
                    "create-profile", "--database", paths["state_db"],
                    "--learner-id", CANARY_LEARNER_ID,
                    "--display-label", "KET99 M4D Chain Canary",
                    "--locale", "zh-TW", "--timezone", "Asia/Taipei",
                )
            )
        elif stage == "M4":
            run_command(
                module_command(
                    "ulga.builders.build_a1fs_v1_m4_lesson_planner_selection_a2_lock",
                    "init", "--database", paths["state_db"], "--consumer", paths["m2"],
                    "--graph", paths["m1"],
                )
            )
            plan = run_command(command, capture_json=True)
            assert plan is not None
            if plan.get("plan_status") not in {"PLAN_LEARNING_LESSON", "RESUME_ACTIVE_SESSION"}:
                raise ChainMaterializationError(f"m4_plan_not_composable:{plan.get('plan_status')}")
            write_json(paths["m4_plan"], plan, private=True)
        else:
            run_command(command)
        artifact_path = {
            "CP03": paths["cp03"], "CP04": paths["cp04"], "CP05": paths["cp05_approved"],
            "CP06": paths["cp06"], "CP07A": paths["cp07a"], "M3": paths["state_db"],
            "M4": paths["m4_plan"], "CP07C": paths["cp07c"], "CP07D": paths["cp07d"],
            "M4D": paths["m4d"],
        }[stage]
        if not artifact_path.is_file():
            raise ChainMaterializationError(f"stage_artifact_missing:{stage}:{artifact_path}")
        stages.append({"stage": stage, "status": "PASS", "artifact_sha256": file_digest(artifact_path)})

    plan = read_json(paths["m4_plan"])
    m4d_value = read_json(paths["m4d"])
    canary = m4d_value.get("m4d_private_canary", {})
    counts = m4d_value.get("m4d_counts", {})
    if canary.get("canary_status") not in {
        "PASS_REFERENCED_READING_ASSET_PRIVATE_CANARY",
        "PASS_NON_BLOCKING_NO_SELECTED_READING_ASSET",
    }:
        raise ChainMaterializationError("m4d_canary_status_invalid")
    if any(counts.get(key) != 0 for key in (
        "composition_item_delta", "required_delivery_asset_delta", "asset_record_delta",
        "response_capture_contract_delta", "mastery_evidence_delta", "canonical_coverage_delta",
        "a2_unlock_count",
    )):
        raise ChainMaterializationError("m4d_mutation_boundary_invalid")
    summary = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "scope": "A1_A1_PLUS_ONLY",
        "stage_order": list(STAGE_ORDER),
        "stages": stages,
        "selected_lesson": {
            "lesson_id": plan.get("selected_lesson", {}).get("lesson_id"),
            "skill": plan.get("selected_lesson", {}).get("skill"),
            "level": plan.get("selected_lesson", {}).get("level"),
            "planner_selection_preserved": True,
            "preferred_skill_override_used": False,
        },
        "m4d_private_canary": {
            "canary_status": canary.get("canary_status"),
            "selected_lesson_has_authored_assets": canary.get("selected_lesson_has_authored_assets"),
            "teacher_delivery_asset_count": canary.get("teacher_delivery_asset_count"),
            "remediation_asset_count": canary.get("remediation_asset_count"),
        },
        "source_identity": {
            "m1_sha256": file_digest(paths["m1"]),
            "m2_sha256": file_digest(paths["m2"]),
            "cp07b_sha256": file_digest(paths["cp07b"]),
            "m4c_sha256": file_digest(paths["m4c"]),
            "m4d_sha256": file_digest(paths["m4d"]),
        },
        "claim_boundaries": {
            "canonical_data_modified": False,
            "operator_learner_state_modified": False,
            "planner_preferred_skill_forced": False,
            "synthetic_lesson_composition_created": False,
            "learner_facing_content_added": False,
            "mastery_or_retention_claimed": False,
            "a2_unlocked": False,
        },
        "errors": [],
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    summary["artifact_sha256"] = digest(summary)
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-root", type=Path)
    parser.add_argument("--m1-graph", type=Path)
    parser.add_argument("--m2-consumer", type=Path)
    parser.add_argument("--cp07b-overlay", type=Path)
    parser.add_argument("--m4c-assets", type=Path)
    parser.add_argument("--raz-source-root", type=Path, default=ROOT / "raz_output_jsons")
    parser.add_argument("--state-db", type=Path, default=DEFAULT_STATE_DB)
    parser.add_argument("--m4-plan", type=Path, default=DEFAULT_M4_PLAN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    try:
        paths = resolve_paths(args)
        artifact = materialize(paths)
        from ulga.validators import validate_ket99_pku_m4d_private_chain_materialization as validator

        report = validator.validate_artifact(artifact, read_json(paths["m4d"]))
        write_json(args.output, artifact)
        write_json(args.report, report)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0 if report["error_count"] == 0 else 1
    except (
        ChainMaterializationError,
        OSError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
