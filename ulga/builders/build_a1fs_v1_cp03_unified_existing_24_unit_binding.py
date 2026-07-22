#!/usr/bin/env python3
"""Bind M11B reviewed content and admitted RAZ assets to the existing 24 units.

This metadata-only composition step has exactly one course container: the
canonical A1/A1+ 24-unit curriculum already used by CP01 and CP02.  It does not
create RAZ-specific units, a parallel curriculum, learner-facing content, or a
new admission decision.  Every RAZ material must already be promoted by
RAZ-AI-ACL S05 and must carry a verified GRAMMAR authority reference that joins
to an existing grammar_unit_id.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_cp01_existing_24_unit_curriculum_backfill as cp01  # noqa: E402
from ulga.builders import build_a1fs_v1_cp02_per_unit_authority_bindings as cp02  # noqa: E402
from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep  # noqa: E402
from ulga.builders import build_raz_ai_acl_v1_s05_material_registry as raz_registry  # noqa: E402

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Metadata-only join of existing M11B item IDs and already-promoted RAZ material IDs into the existing 24-unit identity set; no learner content is produced."

TASK_ID = "A1FS-V1-CP03_M11BReviewedAndRAZAdmittedExisting24UnitBinding"
PROGRAM_ID = cp02.PROGRAM_ID
SCHEMA_VERSION = "a1fs.v1.cp03.unified_existing_24_unit_binding.v1"
PASS_STATUS = "PASS_CP03_M11B_AND_RAZ_BOUND_TO_EXISTING_24_UNITS"
NEXT_SHORT_STEP = "A1FS-V1-CP04_UnifiedContentExerciseAndSceneCandidateBuild"

CP01_PATH = cp01.OUTPUT_PATH
CP02_PATH = cp02.OUTPUT_PATH
RAZ_REGISTRY_PATH = raz_registry.DEFAULT_OUTPUT
OUTPUT_PATH = REPO_ROOT / ".local/a1fs_v1/cp03/unified_existing_24_unit_bindings.safe.json"
REPORT_PATH = REPO_ROOT / ".local/a1fs_v1/cp03/unified_existing_24_unit_bindings.validation.json"
SKILLS = ("reading", "writing", "listening", "speaking")


class UnifiedBindingError(ValueError):
    """Fail-closed source, admission, identity, or binding error."""


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_value(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _verify_package_hash(package: Mapping[str, Any]) -> None:
    claimed = package.get("package_sha256")
    if not isinstance(claimed, str) or len(claimed) != 64:
        raise UnifiedBindingError("raz_registry_package_sha256_invalid")
    core = dict(package)
    core.pop("package_sha256", None)
    if deep.sha256_value(core) != claimed:
        raise UnifiedBindingError("raz_registry_package_sha256_mismatch")


def _verify_curriculum_sources(
    cp01_artifact: Mapping[str, Any], cp02_artifact: Mapping[str, Any]
) -> tuple[list[Mapping[str, Any]], dict[str, Mapping[str, Any]]]:
    if cp01_artifact.get("task_id") != cp01.TASK_ID:
        raise UnifiedBindingError("cp01_task_id_mismatch")
    if cp02_artifact.get("task_id") != cp02.TASK_ID:
        raise UnifiedBindingError("cp02_task_id_mismatch")
    cp01_units = cp01_artifact.get("learning_units")
    cp02_units = cp02_artifact.get("learning_units")
    if not isinstance(cp01_units, list) or not isinstance(cp02_units, list):
        raise UnifiedBindingError("curriculum_units_invalid")
    if len(cp01_units) != 24 or len(cp02_units) != 24:
        raise UnifiedBindingError("canonical_learning_unit_count_not_24")
    cp02_by_grammar = {
        str(row.get("grammar_unit_id") or ""): row
        for row in cp02_units
        if isinstance(row, Mapping)
    }
    if len(cp02_by_grammar) != 24 or "" in cp02_by_grammar:
        raise UnifiedBindingError("cp02_grammar_unit_identity_invalid")
    for index, row in enumerate(cp01_units, start=1):
        grammar_id = str(row.get("grammar_unit_id") or "")
        peer = cp02_by_grammar.get(grammar_id)
        if peer is None:
            raise UnifiedBindingError(f"cp01_cp02_unit_set_mismatch:{grammar_id}")
        expected = (
            row.get("learning_unit_id"),
            row.get("sequence_index"),
            row.get("internal_stage"),
            row.get("canonical_egp_row_ids"),
        )
        actual = (
            peer.get("learning_unit_id"),
            peer.get("sequence_index"),
            peer.get("internal_stage"),
            peer.get("canonical_egp_row_ids"),
        )
        if expected != actual or row.get("sequence_index") != index:
            raise UnifiedBindingError(f"cp01_cp02_unit_identity_drift:{grammar_id}")
    return cp01_units, cp02_by_grammar


def _verified_promoted_materials(
    package: Mapping[str, Any], allowed_grammar_ids: set[str]
) -> tuple[list[Mapping[str, Any]], dict[str, list[dict[str, str]]]]:
    if package.get("task_id") != raz_registry.TASK_ID:
        raise UnifiedBindingError("raz_registry_task_id_mismatch")
    if package.get("validation_status") != raz_registry.PASS_STATUS:
        raise UnifiedBindingError("raz_registry_validation_status_not_pass")
    if package.get("errors") != []:
        raise UnifiedBindingError("raz_registry_errors_not_empty")
    _verify_package_hash(package)
    gate = package.get("material_registry_gate")
    if not isinstance(gate, Mapping) or (
        gate.get("decision") != "A1_A1PLUS_MATERIAL_REGISTRY_READY"
        or gate.get("ready_for_final_coverage_reconciliation") is not True
    ):
        raise UnifiedBindingError("raz_registry_gate_not_ready")
    promoted = package.get("promoted_material_registry")
    if not isinstance(promoted, list) or not promoted:
        raise UnifiedBindingError("raz_promoted_material_registry_empty_or_invalid")
    summary = package.get("aggregate_summary")
    if not isinstance(summary, Mapping) or summary.get("final_promoted_material_count") != len(promoted):
        raise UnifiedBindingError("raz_promoted_material_count_mismatch")

    assignments: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    material_ids: set[str] = set()
    for material in promoted:
        if not isinstance(material, Mapping):
            raise UnifiedBindingError("raz_promoted_material_row_invalid")
        material_id = str(material.get("material_id") or "")
        if not material_id.startswith("RAZ_A1A1PLUS_MATERIAL_") or material_id in material_ids:
            raise UnifiedBindingError("raz_material_id_missing_or_duplicate")
        if material.get("registry_status") != "PROMOTED_TO_A1_A1PLUS_MATERIAL_REGISTRY":
            raise UnifiedBindingError(f"raz_material_not_promoted:{material_id}")
        if material.get("candidate_cefr_scope") not in {"A1", "A1_PLUS"}:
            raise UnifiedBindingError(f"raz_material_scope_invalid:{material_id}")
        links = material.get("authority_links")
        if not isinstance(links, list):
            raise UnifiedBindingError(f"raz_authority_links_invalid:{material_id}")
        grammar_refs = sorted(
            {
                str(link.get("authority_ref") or "")
                for link in links
                if isinstance(link, Mapping)
                and link.get("authority_type") == "GRAMMAR"
                and link.get("link_status") == "VERIFIED_EXISTING_AUTHORITY_MATCH"
            }
        )
        if not grammar_refs:
            raise UnifiedBindingError(f"raz_verified_grammar_link_missing:{material_id}")
        unknown = set(grammar_refs) - allowed_grammar_ids
        if unknown:
            raise UnifiedBindingError(
                f"raz_parallel_or_unknown_unit_forbidden:{material_id}:{','.join(sorted(unknown))}"
            )
        material_ids.add(material_id)
        for grammar_id in grammar_refs:
            assignments[grammar_id].append(
                {
                    "material_id": material_id,
                    "grammar_authority_ref": grammar_id,
                    "registry_status": "PROMOTED_TO_A1_A1PLUS_MATERIAL_REGISTRY",
                    "candidate_cefr_scope": str(material["candidate_cefr_scope"]),
                }
            )
    for rows in assignments.values():
        rows.sort(key=lambda row: row["material_id"])
    return promoted, dict(assignments)


def _m11b_binding(unit: Mapping[str, Any], admission_task_id: str) -> dict[str, Any]:
    by_skill: dict[str, list[str]] = {}
    for skill in SKILLS:
        lane = unit.get("skill_lanes", {}).get(skill, {})
        ids = lane.get("admitted_item_ids", [])
        if not isinstance(ids, list) or len(ids) != len(set(ids)):
            raise UnifiedBindingError(
                f"m11b_admitted_item_ids_invalid:{unit.get('grammar_unit_id')}:{skill}"
            )
        by_skill[skill] = list(ids)
    count = sum(len(ids) for ids in by_skill.values())
    return {
        "source_task_id": admission_task_id,
        "admission_basis": unit.get("skill_lanes", {}).get("reading", {}).get("admission_basis"),
        "admitted_item_ids_by_skill": by_skill,
        "admitted_item_count": count,
        "binding_status": (
            "BOUND_EXISTING_M11B_REVIEWED_CONTENT"
            if count
            else "DEFERRED_NO_M11B_ADMISSION"
        ),
    }


def build_artifact(
    cp01_artifact: Mapping[str, Any],
    cp02_artifact: Mapping[str, Any],
    raz_registry_package: Mapping[str, Any],
) -> dict[str, Any]:
    units, cp02_by_grammar = _verify_curriculum_sources(cp01_artifact, cp02_artifact)
    grammar_ids = {str(row["grammar_unit_id"]) for row in units}
    promoted, raz_assignments = _verified_promoted_materials(
        raz_registry_package, grammar_ids
    )

    output_units: list[dict[str, Any]] = []
    m11b_item_count = 0
    m11b_unit_count = 0
    raz_assignment_count = 0
    raz_covered_units = 0
    m11b_admission_task_id = str(
        cp01_artifact["source_identity"]["admission_task_id"]
    )
    for unit in units:
        grammar_id = str(unit["grammar_unit_id"])
        m11b = _m11b_binding(unit, m11b_admission_task_id)
        raz_rows = raz_assignments.get(grammar_id, [])
        m11b_item_count += m11b["admitted_item_count"]
        m11b_unit_count += m11b["admitted_item_count"] > 0
        raz_assignment_count += len(raz_rows)
        raz_covered_units += bool(raz_rows)
        output_units.append(
            {
                "learning_unit_id": unit["learning_unit_id"],
                "grammar_unit_id": grammar_id,
                "sequence_index": unit["sequence_index"],
                "internal_stage": unit["internal_stage"],
                "canonical_egp_row_ids": list(unit["canonical_egp_row_ids"]),
                "cp02_authority_bindings": cp02_by_grammar[grammar_id]["authority_bindings"],
                "m11b_reviewed_content_binding": m11b,
                "raz_admitted_asset_binding": {
                    "materials": raz_rows,
                    "material_count": len(raz_rows),
                    "binding_status": (
                        "BOUND_EXISTING_RAZ_ADMITTED_ASSETS"
                        if raz_rows
                        else "NO_RAZ_ADMITTED_ASSET_FOR_EXISTING_UNIT"
                    ),
                },
            }
        )

    distinct_bound_material_ids = {
        row["material_id"]
        for rows in raz_assignments.values()
        for row in rows
    }
    if len(distinct_bound_material_ids) != len(promoted):
        raise UnifiedBindingError("not_every_promoted_raz_material_bound")

    artifact = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "metadata_only_unified_existing_24_unit_content_source_bindings",
        "scope": "A1_A1_PLUS_ONLY",
        "binding_contract": {
            "course_container": "EXISTING_24_CANONICAL_UNITS_ONLY",
            "unit_identity_source": cp02.TASK_ID,
            "content_sources": [
                "M11B_REVIEWED_CONTENT",
                "RAZ_AI_ACL_S05_PROMOTED_MATERIAL_REGISTRY",
            ],
            "raz_join_key": "VERIFIED_GRAMMAR_AUTHORITY_REF_EQUALS_EXISTING_GRAMMAR_UNIT_ID",
            "new_unit_creation_allowed": False,
            "raz_specific_parallel_curriculum_allowed": False,
            "unpromoted_raz_asset_binding_allowed": False,
        },
        "source_identity": {
            "cp01_task_id": cp01_artifact["task_id"],
            "cp01_sha256": _sha256_value(cp01_artifact),
            "cp02_task_id": cp02_artifact["task_id"],
            "cp02_sha256": _sha256_value(cp02_artifact),
            "m11b_admission_task_id": cp01_artifact["source_identity"]["admission_task_id"],
            "m11b_admission_bank_sha256": cp01_artifact["source_identity"]["admission_bank_sha256"],
            "raz_registry_task_id": raz_registry_package["task_id"],
            "raz_registry_package_sha256": raz_registry_package["package_sha256"],
        },
        "coverage_summary": {
            "existing_learning_unit_count": len(output_units),
            "new_learning_unit_count": 0,
            "parallel_curriculum_count": 0,
            "m11b_reviewed_content_unit_count": m11b_unit_count,
            "m11b_reviewed_content_item_count": m11b_item_count,
            "raz_promoted_material_input_count": len(promoted),
            "raz_distinct_bound_material_count": len(distinct_bound_material_ids),
            "raz_material_unit_binding_count": raz_assignment_count,
            "raz_covered_existing_unit_count": raz_covered_units,
        },
        "learning_units": output_units,
        "claim_boundaries": {
            "canonical_unit_identity_changed": False,
            "canonical_egp_mapping_changed": False,
            "second_unit_system_created": False,
            "raz_parallel_curriculum_created": False,
            "raz_admission_decision_changed": False,
            "unpromoted_raz_asset_consumed": False,
            "learner_facing_content_created": False,
            "exercise_or_scene_candidate_created": False,
            "runtime_publication_claimed": False,
            "a2_a2plus_in_scope": False,
        },
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    _safe_scan(artifact)
    return artifact


def _safe_scan(value: Any) -> None:
    forbidden = {"text", "title", "payload", "prompt", "answer", "answer_key", "transcript"}

    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                if str(key).casefold() in forbidden:
                    raise UnifiedBindingError(f"private_or_learner_content_leak:{key}")
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(value)


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cp01", type=Path, default=CP01_PATH)
    parser.add_argument("--cp02", type=Path, default=CP02_PATH)
    parser.add_argument("--raz-registry", type=Path, default=RAZ_REGISTRY_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    args = parser.parse_args(argv)
    try:
        cp01_artifact = _read(args.cp01)
        cp02_artifact = _read(args.cp02)
        registry_package = _read(args.raz_registry)
        artifact = build_artifact(cp01_artifact, cp02_artifact, registry_package)
        from ulga.validators.validate_a1fs_v1_cp03_unified_existing_24_unit_binding import validate_artifact

        report = validate_artifact(
            artifact, cp01_artifact, cp02_artifact, registry_package
        )
        write_json(args.output, artifact)
        write_json(args.report, report)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0 if report["validation_status"] == PASS_STATUS else 1
    except (OSError, KeyError, TypeError, ValueError, UnifiedBindingError) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
