#!/usr/bin/env python3
"""Backfill existing admitted content references into the canonical 24 units.

This is a metadata-only composition step. It does not author content or change
canonical grammar, EGP, admission, or runtime state. Candidate and admitted
states remain separate so a complete four-skill contract cannot be mistaken
for complete four-skill admitted content.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1_a1plus_cross_skill_learning_units as m02  # noqa: E402
from ulga.builders import build_a1_a1plus_shared_item_contract as m03  # noqa: E402
from ulga.builders import build_e4s_a1v1_m11b_authority_exception_resolution as m11b  # noqa: E402

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Metadata-only backfill of existing item IDs and admission evidence; "
    "no candidate or canonical learner content is produced."
)

TASK_ID = "A1FS-V1-CP01_Existing24UnitCurriculumContractAndContentBackfill"
PROGRAM_ID = "A1FS-V1_A1A1PlusFourSkillUnitCurriculumPlanningAndPopulation"
SCHEMA_VERSION = "a1fs.v1.cp01.existing_content_backfill.v1"
PASS_STATUS = "PASS_CP01_EXISTING_CONTENT_BACKFILLED_AND_GAPS_MEASURED"
NEXT_SHORT_STEP = "A1FS-V1-CP02_PerUnitAuthorityBackedContentBinding"
OUTPUT_PATH = REPO_ROOT / "ulga/graph/a1fs_v1_cp01_existing_content_backfill.json"
REPORT_PATH = REPO_ROOT / "ulga/reports/a1fs_v1_cp01_existing_content_backfill_validation.json"
SKILLS = ("reading", "writing", "listening", "speaking")
PENDING_AUTHORITIES = ("vocabulary", "chunk", "pattern", "theme_situation")
SPIRAL_ROLES = ("focus", "recycle", "contrast", "transfer")
FOLLOWUP_POOLS = ("remediation", "reassessment", "retention")
M11B_PASS_STATUS = "PASS_M11B_AUTHORITY_EXCEPTIONS_RESOLVED"
DEFERRED_GRAMMAR_ID = "GRAMMAR_WILL_FUTURE_A1"


class CurriculumBackfillError(ValueError):
    """Fail-closed CP01 composition error."""


def sha256_value(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _require(actual: Any, expected: Any, code: str) -> None:
    if actual != expected:
        raise CurriculumBackfillError(
            f"{code}:expected={expected!r}:actual={actual!r}"
        )


def _safe_scan(value: Any) -> None:
    forbidden = {
        "prompt",
        "prompt_text",
        "answer",
        "answer_key",
        "accepted_texts",
        "model_text",
        "transcript",
        "learner_response",
        "final_private_unit_payload",
    }

    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                if str(key).casefold() in forbidden:
                    raise CurriculumBackfillError(f"private_content_leak:{key}")
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(value)


def _ids_by_unit_skill(
    items: Iterable[Mapping[str, Any]],
) -> dict[str, dict[str, dict[str, list[str]]]]:
    result: defaultdict[str, defaultdict[str, defaultdict[str, list[str]]]] = (
        defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    )
    for item in items:
        unit_id = str(item.get("grammar_unit_id") or "")
        skill = str(item.get("skill") or "")
        role = str(item.get("item_role") or "")
        item_id = str(item.get("shared_item_id") or "")
        if not unit_id or skill not in SKILLS or role not in {"practice", "assessment"}:
            raise CurriculumBackfillError("candidate_item_identity_invalid")
        result[unit_id][skill][role].append(item_id)
    return {
        unit_id: {
            skill: {
                role: sorted(ids)
                for role, ids in sorted(role_map.items())
            }
            for skill, role_map in sorted(skill_map.items())
        }
        for unit_id, skill_map in sorted(result.items())
    }


def _admitted_unit_allowlist(bank: Mapping[str, Any]) -> set[str]:
    admitted_units: set[str] = set()
    for reviewed in bank.get("reviewed_units", []):
        unit_id = str(reviewed.get("grammar_unit_id") or "")
        payload = reviewed.get("final_private_unit_payload")
        if not unit_id or not isinstance(payload, Mapping):
            raise CurriculumBackfillError("reviewed_unit_payload_invalid")
        if reviewed.get("private_learning_ready") is not True:
            raise CurriculumBackfillError(f"reviewed_unit_not_private_ready:{unit_id}")
        admitted_units.add(unit_id)
        if len(payload.get("practice_items", [])) != 6 or len(
            payload.get("assessment_items", [])
        ) != 2:
            raise CurriculumBackfillError(f"reviewed_unit_item_count_drift:{unit_id}")
    return admitted_units


def _authority_state(unit: Mapping[str, Any]) -> dict[str, Any]:
    bindings = unit.get("authority_bindings", {})
    grammar = bindings.get("grammar", {})
    result = {
        "grammar": {
            "selection_status": grammar.get("selection_status"),
            "selected_refs": list(grammar.get("selected_refs", [])),
            "source_query_ref": grammar.get("source_query_ref"),
        }
    }
    for authority in PENDING_AUTHORITIES:
        source = bindings.get(authority, {})
        result[authority] = {
            "selection_status": source.get("selection_status"),
            "selected_refs": list(source.get("selected_refs", [])),
            "allowed_pool_count": source.get("allowed_pool_count"),
            "source_query_ref": source.get("source_query_ref"),
            "reason": source.get("reason"),
        }
    return result


def build_artifact() -> dict[str, Any]:
    units = m02.build_artifact()
    candidates = m03.build_artifact()
    resolution, admitted_bank, admission_report = m11b.build_artifacts()

    _require(units.get("coverage_summary", {}).get("learning_unit_count"), 24, "unit_count")
    _require(units.get("coverage_summary", {}).get("canonical_egp_row_count"), 109, "egp_count")
    _require(candidates.get("coverage_summary", {}).get("shared_item_count"), 384, "candidate_count")
    _require(admission_report.get("validation_status"), M11B_PASS_STATUS, "m11b_status")
    _require(admitted_bank.get("reviewed_unit_count"), 23, "admitted_unit_count")
    _require(admitted_bank.get("deferred_unit_count"), 1, "deferred_unit_count")

    candidate_items = list(candidates.get("shared_items", []))
    candidate_index = _ids_by_unit_skill(candidate_items)
    admitted_units = _admitted_unit_allowlist(admitted_bank)
    admitted_shared_ids = {
        str(item["shared_item_id"])
        for item in candidate_items
        if item["grammar_unit_id"] in admitted_units
        and item["skill"] in {"reading", "writing"}
    }
    _require(len(admitted_shared_ids), 184, "admitted_shared_item_count")

    deferred = {
        str(row.get("grammar_unit_id")): str(row.get("resolution_status"))
        for row in resolution.get("records", [])
        if row.get("private_learning_ready") is False
    }
    _require(deferred, {DEFERRED_GRAMMAR_ID: "DEFERRED_CAMBRIDGE_CEILING"}, "deferred_partition")

    rows: list[dict[str, Any]] = []
    admitted_skill_counts: Counter[str] = Counter()
    admitted_lane_count = 0
    for unit in units.get("learning_units", []):
        grammar_id = str(unit["grammar_unit_id"])
        lane_rows: dict[str, Any] = {}
        for skill in SKILLS:
            role_map = candidate_index.get(grammar_id, {}).get(skill, {})
            candidate_ids = sorted(role_map.get("practice", []) + role_map.get("assessment", []))
            admitted_ids = sorted(set(candidate_ids) & admitted_shared_ids)
            if admitted_ids:
                admission_state = "ADMITTED_PRIVATE_BY_UNIT_ALLOWLIST"
                admitted_lane_count += 1
                admitted_skill_counts[skill] += len(admitted_ids)
            else:
                admission_state = "CANDIDATE_ONLY"
            lane_rows[skill] = {
                "candidate_item_ids": candidate_ids,
                "candidate_item_count": len(candidate_ids),
                "admitted_item_ids": admitted_ids,
                "admitted_item_count": len(admitted_ids),
                "admission_state": admission_state,
                "admission_basis": (
                    "M11B_AUTHORITY_REVIEWED_UNIT_ALLOWLIST_M11C_RUNTIME_PROJECTION"
                    if admitted_ids
                    else None
                ),
                "practice_candidate_count": len(role_map.get("practice", [])),
                "assessment_candidate_count": len(role_map.get("assessment", [])),
                "spiral_role_bindings": {
                    role: "MISSING_EXPLICIT_ACTIVITY_ROLE_BINDING"
                    for role in SPIRAL_ROLES
                },
            }
        rows.append(
            {
                "learning_unit_id": unit["learning_unit_id"],
                "grammar_unit_id": grammar_id,
                "sequence_index": unit["sequence_index"],
                "internal_stage": unit["internal_stage"],
                "canonical_egp_row_ids": list(unit["canonical_egp_row_ids"]),
                "prerequisite_unit_ids": list(unit["prerequisite_unit_ids"]),
                "authority_bindings": _authority_state(unit),
                "skill_lanes": lane_rows,
                "followup_content_pools": {
                    pool: "MISSING_EXPLICIT_CONTENT_POOL_BINDING"
                    for pool in FOLLOWUP_POOLS
                },
                "unit_population_status": (
                    "PARTIAL_ADMITTED_PRIVATE"
                    if grammar_id in admitted_units
                    else "CANDIDATE_ONLY_DEFERRED"
                ),
                "four_skill_admitted_population_complete": all(
                    lane_rows[skill]["admission_state"]
                    == "ADMITTED_PRIVATE_BY_UNIT_ALLOWLIST"
                    for skill in SKILLS
                ),
                "deferred_reason": deferred.get(grammar_id),
            }
        )

    _require(len(rows), 24, "backfill_unit_count")
    candidate_total = sum(
        lane["candidate_item_count"]
        for row in rows for lane in row["skill_lanes"].values()
    )
    admitted_total = sum(
        lane["admitted_item_count"]
        for row in rows for lane in row["skill_lanes"].values()
    )
    pending_authority_count = sum(
        row["authority_bindings"][name]["selection_status"]
        == "PENDING_CONTENT_BINDING"
        for row in rows for name in PENDING_AUTHORITIES
    )
    summary = {
        "learning_unit_count": 24,
        "canonical_egp_row_count": 109,
        "candidate_item_count": candidate_total,
        "unit_assigned_candidate_item_count": candidate_total,
        "admitted_private_item_count": admitted_total,
        "candidate_only_item_count": candidate_total - admitted_total,
        "admitted_private_unit_count": len(admitted_units),
        "deferred_unit_count": len(deferred),
        "skill_lane_count": 24 * len(SKILLS),
        "admitted_skill_lane_count": admitted_lane_count,
        "admission_gap_skill_lane_count": 24 * len(SKILLS) - admitted_lane_count,
        "four_skill_admitted_unit_count": sum(
            row["four_skill_admitted_population_complete"] for row in rows
        ),
        "pending_content_authority_binding_count": pending_authority_count,
        "explicit_spiral_role_binding_count": 0,
        "missing_spiral_role_binding_count": 24 * len(SPIRAL_ROLES),
        "explicit_followup_content_pool_binding_count": 0,
        "missing_followup_content_pool_binding_count": 24 * len(FOLLOWUP_POOLS),
        "admitted_private_item_counts_by_skill": {
            skill: admitted_skill_counts[skill] for skill in SKILLS
        },
    }
    _require(candidate_total, 384, "reconciled_candidate_total")
    _require(admitted_total, 184, "reconciled_admitted_total")
    _require(summary["admitted_private_item_counts_by_skill"], {
        "reading": 92, "writing": 92, "listening": 0, "speaking": 0
    }, "admitted_skill_distribution")
    _require(pending_authority_count, 96, "pending_authority_binding_count")

    artifact = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "metadata_only_existing_content_unit_backfill_and_gap_matrix",
        "scope": "A1_A1_PLUS_ONLY",
        "source_identity": {
            "unit_contract_task_id": units["task_id"],
            "unit_contract_sha256": sha256_value(units),
            "four_skill_candidate_task_id": candidates["task_id"],
            "four_skill_candidate_sha256": sha256_value(candidates),
            "admission_task_id": admitted_bank["task_id"],
            "admission_bank_sha256": sha256_value(admitted_bank),
            "admission_projection_rule": (
                "M11C filters M08 text items by the M11B private-ready unit allowlist"
            ),
        },
        "coverage_summary": summary,
        "learning_units": rows,
        "claim_boundaries": {
            "canonical_unit_identity_changed": False,
            "canonical_egp_mapping_changed": False,
            "admission_decision_changed": False,
            "candidate_items_claimed_as_admitted": False,
            "four_skill_population_claimed_complete": False,
            "runtime_publication_claimed": False,
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
            "a2_a2plus_in_scope": False,
        },
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    _safe_scan(artifact)
    return artifact


def build_report(artifact: Mapping[str, Any]) -> dict[str, Any]:
    from ulga.validators.validate_a1fs_v1_cp01_existing_24_unit_curriculum_backfill import validate_artifact

    return validate_artifact(artifact)


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    args = parser.parse_args(argv)
    artifact = build_artifact()
    report = build_report(artifact)
    write_json(args.output, artifact)
    write_json(args.report, report)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["validation_status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
