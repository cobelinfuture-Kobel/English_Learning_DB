#!/usr/bin/env python3
"""Build 24 shared A1/A1+ four-skill LearningUnit envelopes.

The builder composes existing operator-approved text-mode content, candidate
four-skill paths, and the unified M01 authority scope. It does not invent
per-unit vocabulary/chunk/pattern/theme mappings or a canonical EGP row for the
approved rowless structural unit.
"""
from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_grammar_cross_skill_closure import (
    build_and_validate_from_repo as build_cross_skill_closure,
)
from ulga.builders.build_a1_grammar_text_mode_private_pilot_package import (
    build_and_validate_from_repo as build_text_mode_package,
)
from ulga.query.a1_a1plus_authority_scope_query import build_scope

TASK_ID = "E4S-A1V1-M02_CrossSkillLearningUnitContractAndBuilder"
EPIC_ID = "E4S-A1V1_A1A1PlusCompleteFourSkillLearningSystem"
ARTIFACT_ID = "e4s_a1v1_cross_skill_learning_units"
SCHEMA_VERSION = "e4s.a1v1.cross_skill_learning_unit.v1"
SCHEMA_PATH = (
    REPO_ROOT
    / "ulga/schemas/learning_units/a1_a1plus_cross_skill_learning_unit.schema.json"
)
OUTPUT_PATH = REPO_ROOT / "ulga/graph/e4s_a1v1_cross_skill_learning_units.json"
REPORT_PATH = (
    REPO_ROOT / "ulga/reports/e4s_a1v1_cross_skill_learning_units_validation.json"
)
NEXT_SHORT_STEP = "E4S-A1V1-M03_SharedItemAnswerScoringMediaContract"
SKILLS = ("reading", "listening", "speaking", "writing")
ROWLESS_STRUCTURAL_UNIT_ID = "GRAMMAR_DEMONSTRATIVES_CONTRAST"


def _normalize_stage(value: str) -> str:
    normalized = str(value).upper().replace("+", "_PLUS")
    if normalized not in {"A1", "A1_PLUS"}:
        raise ValueError(f"cross_skill_unit_stage_out_of_scope:{value}")
    return normalized


def _authority_pool(scope: Mapping[str, Any], authority: str) -> tuple[list[str], int]:
    rows = scope.get("authorities", {}).get(authority, [])
    refs = [str(row.get("id")) for row in rows if row.get("id")]
    if len(refs) != len(set(refs)) or not refs:
        raise ValueError(f"authority_pool_invalid:{authority}")
    return refs, len(refs)


def _pending_binding(
    scope: Mapping[str, Any], authority: str, source_query_ref: str
) -> dict[str, Any]:
    refs, count = _authority_pool(scope, authority)
    return {
        "selection_status": "PENDING_CONTENT_BINDING",
        "selected_refs": [],
        "allowed_pool_count": count,
        "allowed_pool_refs": refs,
        "source_query_ref": source_query_ref,
        "reason": "NO_DIRECT_PER_UNIT_SOURCE_EVIDENCE_DO_NOT_INVENT_MAPPING",
    }


def _normalize_skill_path(path: Mapping[str, Any]) -> dict[str, Any]:
    result = {
        "activity_ids": list(path.get("activity_ids", [])),
        "assessment_ids": list(path.get("assessment_ids", [])),
        "candidate_path_status": path.get("candidate_path_status"),
        "actual_evidence_status": path.get("actual_evidence_status", "NOT_COLLECTED"),
    }
    for field in ("audio_asset_status", "audio_capture_status", "asr_status"):
        if field in path:
            result[field] = path[field]
    return result


def _error_tags(rows: list[Mapping[str, Any]]) -> list[str]:
    tags = []
    for row in rows:
        value = row.get("tag") if isinstance(row, Mapping) else None
        if value and value not in tags:
            tags.append(str(value))
    if not tags:
        raise ValueError("learning_unit_error_tags_missing")
    return tags


def _coverage_binding(grammar_id: str, row_ids: list[str]) -> dict[str, Any]:
    if row_ids:
        return {
            "mode": "DIRECT_CANONICAL_ROWS",
            "structural_unit": False,
            "package_canonical_row_count": 109,
            "package_coverage_status": "PASS_ALL_CANONICAL_ROWS_COVERED",
        }
    if grammar_id != ROWLESS_STRUCTURAL_UNIT_ID:
        raise ValueError(f"unexpected_rowless_learning_unit:{grammar_id}")
    return {
        "mode": "ROWLESS_STRUCTURAL_PACKAGE_GATE",
        "structural_unit": True,
        "package_canonical_row_count": 109,
        "package_coverage_status": "PASS_ALL_CANONICAL_ROWS_COVERED",
    }


def _source_reports_pass(
    package_report: Mapping[str, Any], cross_skill_report: Mapping[str, Any]
) -> None:
    if package_report.get("validation_status") != "PASS":
        raise RuntimeError("text_mode_package_source_validation_failed")
    if cross_skill_report.get("validation_status") != "PASS":
        raise RuntimeError("cross_skill_closure_source_validation_failed")


def build_artifact() -> dict[str, Any]:
    package, package_report = build_text_mode_package()
    cross_skill, cross_skill_report = build_cross_skill_closure()
    _source_reports_pass(package_report, cross_skill_report)

    a1_scope = build_scope("A1")
    a1_plus_scope = build_scope("A1_PLUS")
    if (
        a1_scope.get("validation_status") != "PASS_AUTHORITY_SCOPE_QUERY_COMPLETE"
        or a1_plus_scope.get("validation_status")
        != "PASS_AUTHORITY_SCOPE_QUERY_COMPLETE"
    ):
        raise RuntimeError("m01_authority_scope_not_complete")

    package_units = package.get("learning_units", [])
    cross_units = cross_skill.get("by_grammar_unit_id", {})
    if len(package_units) != 24 or len(cross_units) != 24:
        raise ValueError("cross_skill_learning_unit_source_count_not_24")

    units: list[dict[str, Any]] = []
    by_grammar_unit_id: dict[str, str] = {}
    by_egp_row_id: dict[str, list[str]] = {}
    for source_unit in package_units:
        grammar_id = str(source_unit["grammar_unit_id"])
        cross_unit = cross_units.get(grammar_id)
        if not cross_unit:
            raise ValueError(f"cross_skill_unit_source_missing:{grammar_id}")
        stage = _normalize_stage(source_unit["internal_stage"])
        scope = a1_scope if stage == "A1" else a1_plus_scope
        skill_paths = cross_unit.get("skill_paths", {})
        if set(skill_paths) != set(SKILLS):
            raise ValueError(f"cross_skill_path_set_invalid:{grammar_id}")
        skill_bindings = {
            skill: _normalize_skill_path(skill_paths[skill]) for skill in SKILLS
        }
        assessment_ids_by_skill = {
            skill: list(skill_bindings[skill]["assessment_ids"]) for skill in SKILLS
        }
        activity_and_assessment_refs = []
        for skill in SKILLS:
            activity_and_assessment_refs.extend(skill_bindings[skill]["activity_ids"])
            activity_and_assessment_refs.extend(skill_bindings[skill]["assessment_ids"])
        activity_and_assessment_refs = list(dict.fromkeys(activity_and_assessment_refs))

        content = source_unit.get("learning_content", {})
        unit_id = f"E4S_A1V1_UNIT:{grammar_id}"
        row_ids = list(source_unit.get("canonical_egp_row_ids", []))
        unit = {
            "learning_unit_id": unit_id,
            "grammar_unit_id": grammar_id,
            "schema_version": SCHEMA_VERSION,
            "official_cefr_level": "A1",
            "internal_stage": stage,
            "sequence_index": source_unit["sequence_index"],
            "status": "OPERATOR_APPROVED_TEXT_MODE_CANDIDATE",
            "canonical_egp_row_ids": row_ids,
            "coverage_binding": _coverage_binding(grammar_id, row_ids),
            "prerequisite_unit_ids": list(source_unit.get("prerequisite_unit_ids", [])),
            "learning_content": {
                "title_en": content.get("title_en"),
                "title_zh_tw": content.get("title_zh_tw"),
                "learning_objectives": deepcopy(content.get("learning_objectives", [])),
                "form_rules": deepcopy(content.get("form_rules", [])),
                "meaning_functions": deepcopy(content.get("meaning_functions", [])),
                "usage_conditions": deepcopy(content.get("usage_conditions", [])),
                "positive_examples": deepcopy(content.get("positive_examples", [])),
                "negative_examples": deepcopy(content.get("negative_examples", [])),
                "common_error_tags": deepcopy(content.get("common_error_tags", [])),
                "contrast_unit_ids": list(content.get("contrast_unit_ids", [])),
            },
            "authority_bindings": {
                "grammar": {
                    "selection_status": "SELECTED",
                    "selected_refs": [grammar_id],
                    "allowed_pool_count": scope["counts"]["grammar"],
                    "source_query_ref": scope["source_paths"]["grammar"],
                },
                "vocabulary": _pending_binding(scope, "vocabulary", scope["source_paths"]["vocabulary"]),
                "chunk": _pending_binding(scope, "chunk", scope["source_paths"]["chunk"]),
                "pattern": _pending_binding(scope, "pattern", scope["source_paths"]["pattern"]),
                "theme_situation": _pending_binding(scope, "theme", scope["source_paths"]["theme"]),
            },
            "skill_bindings": skill_bindings,
            "assessment_binding": {
                "assessment_ids_by_skill": assessment_ids_by_skill,
                "mixed_assessment_status": "M08_NOT_CERTIFIED",
            },
            "answer_scoring_binding": {
                "shared_contract_status": "M03_NOT_CERTIFIED",
                "current_item_source_refs": activity_and_assessment_refs,
            },
            "media_binding": {
                "text_mode_status": "AVAILABLE",
                "listening_audio_status": "NOT_RENDERED",
                "speaking_capture_status": "NOT_IMPLEMENTED",
                "image_asset_status": "NOT_REQUIRED_BY_CURRENT_SOURCE_PATH",
            },
            "error_remediation_binding": {
                "error_tags": _error_tags(content.get("common_error_tags", [])),
                "error_diagnosis_status": "SOURCE_TAGS_AVAILABLE_M12_NOT_CERTIFIED",
                "remediation_status": "M13_NOT_CERTIFIED",
                "remediation_refs": [],
            },
            "source_evidence": {
                "source_artifact_ids": [
                    package["artifact_id"],
                    cross_skill["artifact_id"],
                    "a1_a1plus_authority_scope_query",
                ],
                "source_paths": [
                    "ulga/builders/build_a1_grammar_text_mode_private_pilot_package.py",
                    "ulga/builders/build_a1_grammar_cross_skill_closure.py",
                    "ulga/query/a1_a1plus_authority_scope_query.py",
                    str(SCHEMA_PATH.relative_to(REPO_ROOT)),
                ],
                "operator_approval_status": source_unit["operator_approval_status"],
            },
            "readiness": {
                "learning_unit_contract_complete": True,
                "candidate_four_skill_paths_complete": True,
                "selected_content_authority_bindings_complete": False,
                "shared_item_contract_complete": False,
                "learner_delivery_complete": False,
                "actual_learner_evidence_complete": False,
            },
            "claim_boundaries": {
                "candidate_paths_are_real_skill_evidence": False,
                "learner_mastery_claimed": False,
                "retention_confirmed": False,
                "persistent_learner_state_write": False,
                "production_runtime_event": False,
                "a2_a2plus_in_scope": False,
            },
        }
        units.append(unit)
        by_grammar_unit_id[grammar_id] = unit_id
        for row_id in row_ids:
            by_egp_row_id.setdefault(row_id, []).append(unit_id)

    units.sort(key=lambda row: row["sequence_index"])
    by_egp_row_id = {
        row_id: sorted(unit_ids)
        for row_id, unit_ids in sorted(by_egp_row_id.items())
    }
    return {
        "task_id": TASK_ID,
        "epic_id": EPIC_ID,
        "artifact_id": ARTIFACT_ID,
        "artifact_type": "a1_a1plus_shared_cross_skill_learning_units",
        "schema_version": SCHEMA_VERSION,
        "schema_path": str(SCHEMA_PATH.relative_to(REPO_ROOT)),
        "scope": "A1_A1_PLUS_ONLY",
        "coverage_summary": {
            "learning_unit_count": len(units),
            "canonical_egp_row_count": len(by_egp_row_id),
            "direct_canonical_unit_count": sum(
                unit["coverage_binding"]["mode"] == "DIRECT_CANONICAL_ROWS"
                for unit in units
            ),
            "rowless_structural_unit_count": sum(
                unit["coverage_binding"]["mode"]
                == "ROWLESS_STRUCTURAL_PACKAGE_GATE"
                for unit in units
            ),
            "candidate_four_skill_path_complete_unit_count": sum(
                unit["readiness"]["candidate_four_skill_paths_complete"]
                for unit in units
            ),
            "operator_approved_text_mode_unit_count": sum(
                bool(unit["source_evidence"]["operator_approval_status"])
                for unit in units
            ),
            "selected_grammar_binding_unit_count": sum(
                unit["authority_bindings"]["grammar"]["selection_status"] == "SELECTED"
                for unit in units
            ),
            "pending_content_authority_binding_unit_count": sum(
                all(
                    unit["authority_bindings"][authority]["selection_status"]
                    == "PENDING_CONTENT_BINDING"
                    for authority in ("vocabulary", "chunk", "pattern", "theme_situation")
                )
                for unit in units
            ),
        },
        "authority_scope_counts": {
            "A1": deepcopy(a1_scope["counts"]),
            "A1_PLUS": deepcopy(a1_plus_scope["counts"]),
        },
        "learning_units": units,
        "by_grammar_unit_id": by_grammar_unit_id,
        "by_egp_row_id": by_egp_row_id,
        "claim_boundaries": {
            "m02_learning_unit_contract_complete": True,
            "rowless_structural_unit_preserved_without_fake_row": True,
            "per_unit_content_authority_selection_complete": False,
            "shared_item_contract_complete": False,
            "candidate_paths_are_real_skill_evidence": False,
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
            "persistent_learner_state_write": False,
            "production_runtime_event": False,
            "a2_a2plus_in_scope": False,
        },
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()
    artifact = build_artifact()
    write_json(args.output, artifact)
    print(json.dumps(artifact["coverage_summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
