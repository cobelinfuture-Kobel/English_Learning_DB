#!/usr/bin/env python3
"""Build the metadata-only A1/A1+ four-skill contract closure.

This milestone closes the Reading, Writing, Listening, and Speaking contract
matrix without treating real learner Speaking recordings as a prerequisite.
Speaking capture/review infrastructure remains available, while actual learner
audio evidence is explicitly deferred by operator policy.
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

from ulga.builders.build_a1_a1plus_shared_item_contract import (  # noqa: E402
    TASK_ID as M03_TASK_ID,
    build_artifact as build_shared_contract,
)
from ulga.builders.build_a1_grammar_text_mode_private_pilot_package import (  # noqa: E402
    build_and_validate_from_repo as build_text_mode_source,
)

TASK_ID = "E4S-A1V1-M07_FourSkillContractClosureAndSystemIntegration_NoAudioEvidence"
EPIC_ID = "E4S-A1V1_A1A1PlusCompleteFourSkillLearningSystem"
ARTIFACT_ID = "e4s_a1v1_four_skill_contract_closure"
SCHEMA_VERSION = "e4s.a1v1.four_skill_contract_closure.v1"
PASS_STATUS = "PASS_M07_FOUR_SKILL_CONTRACT_CLOSURE_NO_AUDIO_EVIDENCE"
NEXT_SHORT_STEP = "E4S-A1V1-M08_TextModeLearnerSessionAndProgressEvidenceIntegration"
SKILLS = ("reading", "writing", "listening", "speaking")
EXPECTED_SKILL_COUNTS = {skill: 96 for skill in SKILLS}
EXPECTED_PRACTICE_COUNTS = {skill: 72 for skill in SKILLS}
EXPECTED_ASSESSMENT_COUNTS = {skill: 24 for skill in SKILLS}
M05_RECEIPT_PATH = REPO_ROOT / "ulga/reports/e4s_a1v1_m05_listening_v1_closeout.json"
M06_RECEIPT_PATH = REPO_ROOT / "ulga/reports/e4s_a1v1_m06_speaking_v1_closeout.json"
OUTPUT_PATH = REPO_ROOT / "ulga/graph/e4s_a1v1_four_skill_contract_closure.json"
REPORT_PATH = REPO_ROOT / "ulga/reports/e4s_a1v1_m07_four_skill_contract_closure.json"

PRIVATE_KEYS = {
    "prompt",
    "prompt_text",
    "prompt_contract",
    "answer",
    "answer_key",
    "answer_contract",
    "accepted_texts",
    "model_answer",
    "model_text",
    "model_texts",
    "transcript",
    "transcript_text",
    "manual_transcript",
    "asr_transcript",
    "review_notes",
    "operator_notes",
    "source_payload",
    "private_prompt_contract",
    "private_response_contract",
    "private_answer_contract",
    "private_scoring_contract",
}


class FourSkillClosureError(ValueError):
    """Fail-closed M07 contract-closure error."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise FourSkillClosureError(f"json_root_not_object:{path}")
    return value


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def safe_scan(value: Any, *, name: str) -> None:
    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                lowered = str(key).casefold()
                if (
                    lowered in PRIVATE_KEYS
                    or lowered.endswith("_notes")
                    or lowered.endswith("_absolute_path")
                ):
                    raise FourSkillClosureError(f"private_field_leak:{name}:{key}")
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
        elif isinstance(node, str):
            if Path(node).is_absolute() or (
                len(node) > 2 and node[1:3] in {":\\", ":/"}
            ):
                raise FourSkillClosureError(f"absolute_path_leak:{name}")

    walk(value)


def _require(actual: Any, expected: Any, code: str) -> None:
    if actual != expected:
        raise FourSkillClosureError(
            f"{code}:expected={expected!r}:actual={actual!r}"
        )


def _counter_map(
    items: Iterable[Mapping[str, Any]],
    key: str,
    values: Iterable[str],
) -> dict[str, int]:
    counts = Counter(str(item.get(key)) for item in items)
    return {value: counts[value] for value in values}


def _validate_m05(receipt: Mapping[str, Any]) -> None:
    _require(
        receipt.get("task_id"),
        "E4S-A1V1-M05_ListeningV1CompletionAndIntegration",
        "m05_task_id",
    )
    _require(
        receipt.get("local_validation_status"),
        "PASS_M05_LISTENING_V1_VALIDATED",
        "m05_local_status",
    )
    preflight = receipt.get("m04_preflight", {})
    _require(preflight.get("reading_v1_complete"), True, "m04_reading_complete")
    _require(preflight.get("m05_progression_allowed"), True, "m04_progression")
    _require(preflight.get("review_entry_count"), 281, "m04_review_entries")
    _require(preflight.get("reviewed_item_count"), 81, "m04_reviewed_items")
    _require(preflight.get("pending_decision_count"), 0, "m04_pending")
    completion = receipt.get("completion", {})
    for key, expected in {
        "listening_items": 96,
        "rendered_audio": 96,
        "practice_items": 72,
        "assessment_items": 24,
        "grammar_units": 24,
        "canonical_egp_rows": 109,
        "rows_with_listening_path": 109,
        "rows_with_listening_assessment": 109,
        "private_delivery": "PASS",
        "query_consumer": "PASS",
        "metadata_deterministic_rebuild": "PASS",
    }.items():
        _require(completion.get(key), expected, f"m05_{key}")
    boundaries = receipt.get("claim_boundaries", {})
    for key, expected in {
        "canonical_authority_writes": 0,
        "public_delivery_count": 0,
        "actual_learner_evidence_count": 0,
        "learner_mastery_claimed": False,
        "persistent_learner_state_writes": 0,
        "production_runtime_enabled": False,
        "a2_a2plus_in_scope": False,
    }.items():
        _require(boundaries.get(key), expected, f"m05_boundary_{key}")


def _validate_m06(receipt: Mapping[str, Any]) -> None:
    _require(
        receipt.get("task_id"),
        "E4S-A1V1-M06_SpeakingV1CompletionAndIntegration",
        "m06_task_id",
    )
    _require(
        receipt.get("local_validation_status"),
        "PASS_M06_SPEAKING_CAPTURE_REVIEW_ENGINE_READY",
        "m06_local_status",
    )
    implementation = receipt.get("implementation", {})
    for key, expected in {
        "speaking_items": 96,
        "practice_items": 72,
        "assessment_items": 24,
        "grammar_units": 24,
        "canonical_egp_rows": 109,
        "capture_queue": "PASS_READY",
        "local_recording_ui": "PASS_READY",
        "browser_evidence_registry_assembler": "PASS_READY",
        "audio_file_intake": "PASS_READY",
        "manual_review_path": "PASS_READY",
        "private_review_bank": "PASS_READY",
        "query_consumer": "PASS_READY",
        "independent_validator": "PASS_READY",
        "capture_review_engine": "PASS_READY",
    }.items():
        _require(implementation.get(key), expected, f"m06_{key}")
    evidence = receipt.get("evidence_state", {})
    for key in (
        "captured_audio",
        "manual_transcripts",
        "operator_reviewed_items",
        "asr_transcripts",
        "actual_speaking_attempts",
        "actual_speaking_mastery_evidence",
    ):
        _require(evidence.get(key), 0, f"m06_evidence_{key}")
    boundaries = receipt.get("claim_boundaries", {})
    for key, expected in {
        "canonical_authority_writes": 0,
        "public_delivery_count": 0,
        "learner_mastery_claimed": False,
        "persistent_learner_state_writes": 0,
        "asr_enabled": False,
        "production_runtime_enabled": False,
        "a2_a2plus_in_scope": False,
    }.items():
        _require(boundaries.get(key), expected, f"m06_boundary_{key}")


def _build_matrices(
    items: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int], dict[str, int]]:
    unit_work: dict[str, dict[str, Any]] = {}
    unit_order: list[str] = []
    row_work: dict[str, dict[str, Any]] = {}
    stage_items: Counter[str] = Counter()
    stage_units: defaultdict[str, set[str]] = defaultdict(set)

    for item in items:
        grammar_id = str(item["grammar_unit_id"])
        if grammar_id not in unit_work:
            unit_order.append(grammar_id)
            unit_work[grammar_id] = {
                "grammar_unit_id": grammar_id,
                "learning_unit_id": str(item["learning_unit_id"]),
                "internal_stage": str(item["internal_stage"]),
                "canonical_egp_row_ids": list(
                    item.get("content_binding", {}).get(
                        "canonical_egp_row_ids", []
                    )
                ),
                "skill_item_counts": {skill: 0 for skill in SKILLS},
                "skill_practice_counts": {skill: 0 for skill in SKILLS},
                "skill_assessment_counts": {skill: 0 for skill in SKILLS},
                "shared_item_count": 0,
            }
        unit = unit_work[grammar_id]
        expected_rows = unit["canonical_egp_row_ids"]
        actual_rows = list(
            item.get("content_binding", {}).get("canonical_egp_row_ids", [])
        )
        _require(item["learning_unit_id"], unit["learning_unit_id"], "unit_learning_id_drift")
        _require(item["internal_stage"], unit["internal_stage"], "unit_stage_drift")
        _require(actual_rows, expected_rows, "unit_row_binding_drift")

        skill = str(item["skill"])
        role = str(item["item_role"])
        unit["skill_item_counts"][skill] += 1
        unit[f"skill_{role}_counts"][skill] += 1
        unit["shared_item_count"] += 1
        stage_items[str(item["internal_stage"])] += 1
        stage_units[str(item["internal_stage"])].add(grammar_id)

        for row_id in actual_rows:
            row = row_work.setdefault(
                str(row_id),
                {
                    "canonical_egp_row_id": str(row_id),
                    "grammar_unit_ids": set(),
                    "skill_item_counts": {name: 0 for name in SKILLS},
                    "shared_item_count": 0,
                },
            )
            row["grammar_unit_ids"].add(grammar_id)
            row["skill_item_counts"][skill] += 1
            row["shared_item_count"] += 1

    unit_rows: list[dict[str, Any]] = []
    for sequence_index, grammar_id in enumerate(unit_order, start=1):
        unit = unit_work[grammar_id]
        _require(unit["shared_item_count"], 16, f"unit_item_count:{grammar_id}")
        _require(
            unit["skill_item_counts"],
            {skill: 4 for skill in SKILLS},
            f"unit_skill_count:{grammar_id}",
        )
        _require(
            unit["skill_practice_counts"],
            {skill: 3 for skill in SKILLS},
            f"unit_practice_count:{grammar_id}",
        )
        _require(
            unit["skill_assessment_counts"],
            {skill: 1 for skill in SKILLS},
            f"unit_assessment_count:{grammar_id}",
        )
        unit_rows.append({"sequence_index": sequence_index, **unit})

    row_rows: list[dict[str, Any]] = []
    for row_id in sorted(row_work):
        row = row_work[row_id]
        counts = row["skill_item_counts"]
        if any(counts[skill] <= 0 for skill in SKILLS):
            raise FourSkillClosureError(f"row_missing_skill:{row_id}:{counts}")
        if len(set(counts.values())) != 1:
            raise FourSkillClosureError(f"row_skill_matrix_unbalanced:{row_id}:{counts}")
        row_rows.append(
            {
                "canonical_egp_row_id": row_id,
                "grammar_unit_ids": sorted(row["grammar_unit_ids"]),
                "skill_item_counts": counts,
                "shared_item_count": row["shared_item_count"],
            }
        )

    return (
        unit_rows,
        row_rows,
        dict(sorted(stage_items.items())),
        {key: len(value) for key, value in sorted(stage_units.items())},
    )


def build_artifact() -> dict[str, Any]:
    shared = build_shared_contract()
    if shared.get("task_id") != M03_TASK_ID:
        raise FourSkillClosureError("m03_task_id_drift")
    summary = shared.get("coverage_summary", {})
    _require(summary.get("learning_unit_count"), 24, "m03_learning_units")
    _require(summary.get("canonical_egp_row_count"), 109, "m03_rows")
    _require(summary.get("shared_item_count"), 384, "m03_items")
    _require(summary.get("items_per_unit"), 16, "m03_items_per_unit")
    _require(summary.get("skill_item_counts"), EXPECTED_SKILL_COUNTS, "m03_skill_counts")
    _require(
        summary.get("skill_practice_counts"),
        EXPECTED_PRACTICE_COUNTS,
        "m03_practice_counts",
    )
    _require(
        summary.get("skill_assessment_counts"),
        EXPECTED_ASSESSMENT_COUNTS,
        "m03_assessment_counts",
    )

    items = shared.get("shared_items")
    if not isinstance(items, list):
        raise FourSkillClosureError("m03_shared_items_missing")
    _require(len(items), 384, "m03_shared_item_length")
    shared_ids = [str(item.get("shared_item_id")) for item in items]
    _require(len(set(shared_ids)), 384, "m03_shared_item_identity")

    text_source, text_report = build_text_mode_source()
    _require(text_report.get("validation_status"), "PASS", "text_mode_status")
    text_summary = text_report.get("coverage_summary", {})
    for key, expected in {
        "unit_count": 24,
        "canonical_row_count": 109,
        "item_count": 192,
        "reading_item_count": 96,
        "writing_item_count": 96,
        "actual_learner_attempt_count": 0,
    }.items():
        _require(text_summary.get(key), expected, f"text_mode_{key}")

    m05 = read_json(M05_RECEIPT_PATH)
    m06 = read_json(M06_RECEIPT_PATH)
    _validate_m05(m05)
    _validate_m06(m06)

    skill_counts = _counter_map(items, "skill", SKILLS)
    practice_counts = {
        skill: sum(
            item.get("skill") == skill and item.get("item_role") == "practice"
            for item in items
        )
        for skill in SKILLS
    }
    assessment_counts = {
        skill: sum(
            item.get("skill") == skill and item.get("item_role") == "assessment"
            for item in items
        )
        for skill in SKILLS
    }
    _require(skill_counts, EXPECTED_SKILL_COUNTS, "item_skill_counts")
    _require(practice_counts, EXPECTED_PRACTICE_COUNTS, "item_practice_counts")
    _require(assessment_counts, EXPECTED_ASSESSMENT_COUNTS, "item_assessment_counts")

    unit_rows, row_rows, stage_item_counts, stage_unit_counts = _build_matrices(items)
    _require(len(unit_rows), 24, "unit_matrix_count")
    _require(len(row_rows), 109, "row_matrix_count")

    m04 = m05["m04_preflight"]
    artifact = {
        "task_id": TASK_ID,
        "epic_id": EPIC_ID,
        "artifact_id": ARTIFACT_ID,
        "artifact_type": "metadata_only_a1_a1plus_four_skill_contract_closure",
        "schema_version": SCHEMA_VERSION,
        "scope": "A1_A1_PLUS_ONLY",
        "mode": "NO_NEW_SPEAKING_AUDIO_EVIDENCE",
        "upstream_hashes": {
            "m03_shared_contract_sha256": sha256_value(shared),
            "text_mode_source_sha256": sha256_value(text_source),
            "text_mode_report_sha256": sha256_value(text_report),
            "m05_closeout_receipt_sha256": sha256_value(m05),
            "m06_closeout_receipt_sha256": sha256_value(m06),
        },
        "closure_summary": {
            "learning_unit_count": 24,
            "canonical_egp_row_count": 109,
            "shared_item_count": 384,
            "items_per_unit": 16,
            "skill_item_counts": skill_counts,
            "skill_practice_counts": practice_counts,
            "skill_assessment_counts": assessment_counts,
            "units_with_all_four_skills": len(unit_rows),
            "rows_with_all_four_skills": len(row_rows),
            "internal_stage_item_counts": stage_item_counts,
            "internal_stage_unit_counts": stage_unit_counts,
        },
        "skill_states": {
            "reading": {
                "contract_item_count": 96,
                "practice_item_count": 72,
                "assessment_item_count": 24,
                "contract_state": "COMPLETE",
                "content_state": "SOURCE_GROUNDED_PRIVATE_REVIEW_BANK_COMPLETE",
                "review_entry_count": m04["review_entry_count"],
                "reviewed_item_count": m04["reviewed_item_count"],
                "pending_decision_count": m04["pending_decision_count"],
                "actual_learner_evidence_count": 0,
            },
            "writing": {
                "contract_item_count": 96,
                "practice_item_count": 72,
                "assessment_item_count": 24,
                "contract_state": "COMPLETE",
                "content_state": "TEXT_MODE_CONTRACT_READY",
                "actual_learner_evidence_count": 0,
            },
            "listening": {
                "contract_item_count": 96,
                "practice_item_count": 72,
                "assessment_item_count": 24,
                "contract_state": "COMPLETE",
                "delivery_state": "LOCAL_PRIVATE_DELIVERY_COMPLETE",
                "rendered_audio_asset_count": m05["completion"]["rendered_audio"],
                "actual_learner_evidence_count": 0,
            },
            "speaking": {
                "contract_item_count": 96,
                "practice_item_count": 72,
                "assessment_item_count": 24,
                "contract_state": "COMPLETE",
                "capture_review_engine_state": "COMPLETE",
                "real_audio_evidence_state": "DEFERRED_BY_OPERATOR",
                "real_audio_evidence_blocks_m07": False,
                "captured_audio_count": 0,
                "operator_reviewed_item_count": 0,
                "actual_learner_evidence_count": 0,
            },
        },
        "by_grammar_unit_id": unit_rows,
        "by_canonical_egp_row_id": row_rows,
        "query_surfaces": [
            "summary",
            "skill",
            "grammar_unit_id",
            "canonical_egp_row_id",
            "internal_stage",
            "system_gate",
        ],
        "system_gate": {
            "four_skill_contract_matrix_complete": True,
            "four_skill_structure_complete": True,
            "reading_v1_completion_gate": True,
            "writing_contract_completion_gate": True,
            "listening_local_delivery_gate": True,
            "speaking_contract_and_engine_gate": True,
            "speaking_real_audio_evidence_required_for_m07": False,
            "speaking_real_audio_evidence_state": "DEFERRED_BY_OPERATOR",
            "actual_learner_evidence_complete": False,
            "learner_mastery_claimed": False,
            "m08_progression_allowed": True,
        },
        "claim_boundaries": {
            "metadata_only_artifact": True,
            "private_content_included": False,
            "audio_bytes_included": False,
            "learner_responses_included": False,
            "canonical_authority_writes": 0,
            "public_delivery_count": 0,
            "persistent_learner_state_writes": 0,
            "actual_learner_evidence_complete": False,
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
            "production_runtime_enabled": False,
            "a2_a2plus_in_scope": False,
        },
        "last_completed_status": PASS_STATUS,
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    safe_scan(artifact, name="m07_closure")
    return artifact


def build_report(artifact: Mapping[str, Any]) -> dict[str, Any]:
    report = {
        "task_id": TASK_ID,
        "epic_id": EPIC_ID,
        "artifact_type": "metadata_only_m07_four_skill_contract_closure_receipt",
        "schema_version": "e4s.a1v1.m07_four_skill_contract_closure_receipt.v1",
        "scope": "A1_A1_PLUS_ONLY",
        "validation_status": PASS_STATUS,
        "closure_artifact_sha256": sha256_value(artifact),
        "completion": {
            "shared_items": artifact["closure_summary"]["shared_item_count"],
            "learning_units": artifact["closure_summary"]["learning_unit_count"],
            "canonical_egp_rows": artifact["closure_summary"]["canonical_egp_row_count"],
            "skills_closed": 4,
            "units_with_all_four_skills": artifact["closure_summary"][
                "units_with_all_four_skills"
            ],
            "rows_with_all_four_skills": artifact["closure_summary"][
                "rows_with_all_four_skills"
            ],
        },
        "skill_completion_states": {
            skill: artifact["skill_states"][skill].get(
                "content_state",
                artifact["skill_states"][skill].get(
                    "delivery_state",
                    artifact["skill_states"][skill].get(
                        "capture_review_engine_state", "COMPLETE"
                    ),
                ),
            )
            for skill in SKILLS
        },
        "operator_deferred_conditions": {
            "speaking_real_audio_evidence": "DEFERRED_BY_OPERATOR",
            "blocks_contract_closure": False,
            "blocks_m08_progression": False,
        },
        "claim_boundaries": dict(artifact["claim_boundaries"]),
        "last_completed_status": PASS_STATUS,
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    safe_scan(report, name="m07_report")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    args = parser.parse_args(argv)
    artifact = build_artifact()
    report = build_report(artifact)
    write_json(args.output, artifact)
    write_json(args.report, report)
    print(
        json.dumps(
            {
                "validation_status": PASS_STATUS,
                "shared_items": artifact["closure_summary"]["shared_item_count"],
                "learning_units": artifact["closure_summary"]["learning_unit_count"],
                "canonical_egp_rows": artifact["closure_summary"][
                    "canonical_egp_row_count"
                ],
                "speaking_real_audio_evidence_state": artifact["system_gate"][
                    "speaking_real_audio_evidence_state"
                ],
                "next_short_step": NEXT_SHORT_STEP,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
