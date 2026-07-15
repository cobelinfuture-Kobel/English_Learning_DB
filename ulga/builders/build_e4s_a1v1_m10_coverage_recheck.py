#!/usr/bin/env python3
"""Recalculate A1/A1+ EGP structural coverage and actionable backlog.

This report deliberately separates structural/content/runtime-path coverage from
actual learner evidence and mastery. It reads existing canonical artifacts and
rebuilds current candidates; it does not create a new canonical graph, copy EGP
text, enter A2/A2+, or process audio/recording files.
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
    build_artifact as build_shared_contract,
)
from ulga.builders.build_a1_grammar_full_teachable_candidate_coverage import (  # noqa: E402
    build_and_validate_from_repo as build_candidate_coverage,
)
from ulga.builders.build_a1_grammar_text_mode_private_pilot_package import (  # noqa: E402
    build_and_validate_from_repo as build_text_package,
)
from ulga.builders.build_e4s_a1v1_m07_four_skill_contract_closure import (  # noqa: E402
    build_artifact as build_four_skill_closure,
)
from ulga.builders.build_e4s_a1v1_m08_text_mode_learner_session import (  # noqa: E402
    build_session_bank,
)

TASK_ID = "E4S-A1V1-M10_A1A1PlusCoverageRecheckAndBacklogClosure_NoNewDesignDocs"
EPIC_ID = "E4S-A1V1_A1A1PlusCompleteFourSkillLearningSystem"
SCHEMA_VERSION = "e4s.a1v1.a1_a1plus_coverage_recheck.v1"
PASS_STATUS = "PASS_M10_A1A1PLUS_STRUCTURAL_COVERAGE_RECHECK_COMPLETE"
NEXT_SHORT_STEP = "E4S-A1V1-M11_A1A1PlusCandidateContentReviewAndPrivatePromotion"
OUTPUT_PATH = REPO_ROOT / "ulga/reports/e4s_a1v1_m10_coverage_recheck.json"
VALIDATION_PATH = REPO_ROOT / "ulga/reports/e4s_a1v1_m10_coverage_recheck_validation.json"
RULE_INDEX_PATH = REPO_ROOT / "ulga/graph/a1_canonical_rule_validator_index.json"
M05_RECEIPT_PATH = REPO_ROOT / "ulga/reports/e4s_a1v1_m05_listening_v1_closeout.json"
M06_RECEIPT_PATH = REPO_ROOT / "ulga/reports/e4s_a1v1_m06_speaking_v1_closeout.json"
M07_RECEIPT_PATH = REPO_ROOT / "ulga/reports/e4s_a1v1_m07_four_skill_contract_closure.json"
M08_RECEIPT_PATH = REPO_ROOT / "ulga/reports/e4s_a1v1_m08_text_mode_session_closeout.json"
M09_RECEIPT_PATH = REPO_ROOT / "ulga/reports/e4s_a1v1_m09_private_runtime_closeout.json"
SKILLS = ("reading", "writing", "listening", "speaking")
CLASSIFICATIONS = ("COVERED", "DRAFT_ONLY", "MISSING")
COVERAGE_LAYERS = (
    "canonical_mapping",
    "rule_validator",
    "teaching_candidate",
    "practice_candidate",
    "assessment_candidate",
    "four_skill_contract",
    "private_text_runtime",
    "listening_delivery_contract",
    "speaking_contract_engine",
)
SAFE_FORBIDDEN_KEYS = {
    "prompt",
    "prompt_text",
    "answer",
    "answer_key",
    "answer_contract",
    "accepted_texts",
    "model_text",
    "model_texts",
    "transcript",
    "transcript_text",
    "manual_transcript",
    "asr_transcript",
    "source_payload",
    "review_notes",
    "operator_notes",
    "learner_response",
    "learner_responses",
}


class CoverageRecheckError(ValueError):
    """Fail-closed M10 coverage error."""


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
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise CoverageRecheckError(f"json_unreadable:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise CoverageRecheckError(f"json_root_not_object:{path}")
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
                if lowered in SAFE_FORBIDDEN_KEYS or lowered.endswith("_absolute_path"):
                    raise CoverageRecheckError(f"private_field_leak:{name}:{key}")
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
        elif isinstance(node, str):
            if Path(node).is_absolute() or (
                len(node) > 2 and node[1:3] in {":\\", ":/"}
            ):
                raise CoverageRecheckError(f"absolute_path_leak:{name}")

    walk(value)


def _require(actual: Any, expected: Any, code: str) -> None:
    if actual != expected:
        raise CoverageRecheckError(
            f"{code}:expected={expected!r}:actual={actual!r}"
        )


def _percent(count: int, total: int) -> float:
    return round(count * 100.0 / total, 2) if total else 0.0


def _validate_receipts(receipts: Mapping[str, Mapping[str, Any]]) -> None:
    m05 = receipts["m05"]
    _require(
        m05.get("task_id"),
        "E4S-A1V1-M05_ListeningV1CompletionAndIntegration",
        "m05_task_id",
    )
    _require(m05.get("local_validation_status"), "PASS_M05_LISTENING_V1_VALIDATED", "m05_status")
    for key, expected in {
        "listening_items": 96,
        "rendered_audio": 96,
        "grammar_units": 24,
        "canonical_egp_rows": 109,
    }.items():
        _require(m05.get("completion", {}).get(key), expected, f"m05_{key}")

    m06 = receipts["m06"]
    _require(
        m06.get("task_id"),
        "E4S-A1V1-M06_SpeakingV1CompletionAndIntegration",
        "m06_task_id",
    )
    _require(
        m06.get("local_validation_status"),
        "PASS_M06_SPEAKING_CAPTURE_REVIEW_ENGINE_READY",
        "m06_status",
    )
    for key, expected in {
        "speaking_items": 96,
        "grammar_units": 24,
        "canonical_egp_rows": 109,
        "capture_review_engine": "PASS_READY",
    }.items():
        _require(m06.get("implementation", {}).get(key), expected, f"m06_{key}")
    _require(m06.get("evidence_state", {}).get("captured_audio"), 0, "m06_audio_count")

    m07 = receipts["m07"]
    _require(
        m07.get("validation_status"),
        "PASS_M07_FOUR_SKILL_CONTRACT_CLOSURE_NO_AUDIO_EVIDENCE",
        "m07_status",
    )
    for key, expected in {
        "shared_items": 384,
        "learning_units": 24,
        "canonical_egp_rows": 109,
        "skills_closed": 4,
    }.items():
        _require(m07.get("completion", {}).get(key), expected, f"m07_{key}")

    m08 = receipts["m08"]
    _require(
        m08.get("validation_status"),
        "PASS_M08_TEXT_MODE_SESSION_AND_PROGRESS_ENGINE_READY",
        "m08_status",
    )
    for key, expected in {
        "available_items": 192,
        "reading_items": 96,
        "writing_items": 96,
        "grammar_units": 24,
        "canonical_egp_rows": 109,
        "independent_validation_errors": 0,
    }.items():
        _require(m08.get("completion", {}).get(key), expected, f"m08_{key}")

    m09 = receipts["m09"]
    _require(
        m09.get("validation_status"),
        "PASS_M09_PRIVATE_LEARNING_RUNTIME_ACCEPTED",
        "m09_status",
    )
    for key, expected in {
        "runtime_status": "PASS_PRIVATE_RUNTIME_READY",
        "available_items": 192,
        "grammar_units": 24,
        "canonical_egp_rows": 109,
        "health_failures": 0,
        "independent_validation_errors": 0,
    }.items():
        _require(m09.get("completion", {}).get(key), expected, f"m09_{key}")
    _require(m09.get("recording_enabled"), False, "m09_recording_enabled")
    _require(m09.get("new_audio_processing_performed"), False, "m09_audio_processing")
    _require(m09.get("stop_reason"), "NONE", "m09_stop_reason")
    _require(m09.get("next_short_step"), TASK_ID, "m09_next_step")


def _row_unit_index(units: Iterable[Mapping[str, Any]]) -> dict[str, list[str]]:
    result: defaultdict[str, set[str]] = defaultdict(set)
    for unit in units:
        grammar_id = str(unit.get("grammar_unit_id") or "")
        for row_id in unit.get("canonical_egp_row_ids", []):
            result[str(row_id)].add(grammar_id)
    return {row_id: sorted(values) for row_id, values in sorted(result.items())}


def _m08_row_counts(bank: Mapping[str, Any]) -> dict[str, dict[str, int]]:
    work: defaultdict[str, Counter[str]] = defaultdict(Counter)
    for item in bank.get("items", []):
        for row_id in item.get("canonical_egp_row_ids", []):
            work[str(row_id)][str(item.get("skill"))] += 1
    return {
        row_id: {skill: counts[skill] for skill in ("reading", "writing")}
        for row_id, counts in sorted(work.items())
    }


def _unit_readiness(unit: Mapping[str, Any], key: str) -> bool:
    return unit.get("readiness", {}).get(key) is True


def build_report() -> dict[str, Any]:
    candidate, candidate_validation = build_candidate_coverage()
    _require(candidate_validation.get("validation_status"), "PASS", "candidate_validation")
    _require(candidate.get("coverage_summary", {}).get("canonical_unit_count"), 24, "candidate_units")
    _require(candidate.get("coverage_summary", {}).get("canonical_unique_egp_row_count"), 109, "candidate_rows")

    rule_index = read_json(RULE_INDEX_PATH)
    _require(rule_index.get("coverage_summary", {}).get("canonical_mapping_unit_count"), 24, "rule_units")
    _require(rule_index.get("coverage_summary", {}).get("canonical_mapping_unique_egp_rows"), 109, "rule_rows")
    _require(rule_index.get("coverage_summary", {}).get("executable_sentence_validator_unit_count"), 24, "validator_units")
    _require(rule_index.get("coverage_summary", {}).get("dispatcher_registered_unit_count"), 24, "dispatcher_units")

    four_skill = build_four_skill_closure()
    _require(four_skill.get("closure_summary", {}).get("shared_item_count"), 384, "four_skill_items")
    _require(four_skill.get("closure_summary", {}).get("canonical_egp_row_count"), 109, "four_skill_rows")

    m07_receipt = read_json(M07_RECEIPT_PATH)
    text_package, text_validation = build_text_package()
    _require(text_validation.get("validation_status"), "PASS", "text_package_validation")
    shared = build_shared_contract()
    session_bank = build_session_bank(m07_receipt, text_package, shared)
    _require(session_bank.get("item_count"), 192, "session_items")
    _require(session_bank.get("canonical_egp_row_count"), 109, "session_rows")

    receipts = {
        "m05": read_json(M05_RECEIPT_PATH),
        "m06": read_json(M06_RECEIPT_PATH),
        "m07": m07_receipt,
        "m08": read_json(M08_RECEIPT_PATH),
        "m09": read_json(M09_RECEIPT_PATH),
    }
    _validate_receipts(receipts)

    units = candidate.get("learning_units", [])
    unit_by_id = {str(unit["grammar_unit_id"]): unit for unit in units}
    _require(len(unit_by_id), 24, "candidate_unit_identity")
    candidate_row_units = _row_unit_index(units)
    canonical_rows = sorted(candidate.get("by_egp_row_id", {}))
    _require(len(canonical_rows), 109, "canonical_row_universe")

    rule_by_unit = rule_index.get("by_grammar_id", {})
    four_skill_by_row = {
        str(row["canonical_egp_row_id"]): row
        for row in four_skill.get("by_canonical_egp_row_id", [])
    }
    session_by_row = _m08_row_counts(session_bank)
    row_records: list[dict[str, Any]] = []

    listening_ready = receipts["m05"]["completion"]["listening_items"] == 96
    speaking_engine_ready = receipts["m06"]["implementation"]["capture_review_engine"] == "PASS_READY"
    runtime_ready = receipts["m09"]["completion"]["runtime_status"] == "PASS_PRIVATE_RUNTIME_READY"

    for row_id in canonical_rows:
        grammar_ids = candidate_row_units.get(row_id, [])
        row_units = [unit_by_id[grammar_id] for grammar_id in grammar_ids if grammar_id in unit_by_id]
        rule_rows = [rule_by_unit.get(grammar_id) for grammar_id in grammar_ids]
        four_skill_row = four_skill_by_row.get(row_id, {})
        four_skill_counts = four_skill_row.get("skill_item_counts", {})
        session_counts = session_by_row.get(row_id, {})

        layers = {
            "canonical_mapping": bool(grammar_ids)
            and all(
                isinstance(rule, Mapping)
                and row_id in rule.get("canonical_egp_row_ids", [])
                and rule.get("canonical_mapping_status") == "VERIFIED_CANONICAL_MAPPING"
                for rule in rule_rows
            ),
            "rule_validator": bool(rule_rows)
            and all(
                isinstance(rule, Mapping)
                and rule.get("executable_sentence_validator") is True
                and rule.get("dispatcher_route_status") == "REGISTERED"
                and rule.get("schema_validation_status") == "PASS"
                for rule in rule_rows
            ),
            "teaching_candidate": bool(row_units)
            and all(_unit_readiness(unit, "candidate_teachable") for unit in row_units),
            "practice_candidate": bool(row_units)
            and all(_unit_readiness(unit, "candidate_practice_ready") for unit in row_units),
            "assessment_candidate": bool(row_units)
            and all(_unit_readiness(unit, "candidate_assessment_ready") for unit in row_units),
            "four_skill_contract": set(four_skill_counts) == set(SKILLS)
            and all(isinstance(four_skill_counts[skill], int) and four_skill_counts[skill] > 0 for skill in SKILLS),
            "private_text_runtime": runtime_ready
            and session_counts.get("reading", 0) > 0
            and session_counts.get("writing", 0) > 0,
            "listening_delivery_contract": listening_ready
            and four_skill_counts.get("listening", 0) > 0,
            "speaking_contract_engine": speaking_engine_ready
            and four_skill_counts.get("speaking", 0) > 0,
        }
        if all(layers.values()):
            classification = "COVERED"
        elif layers["canonical_mapping"] and any(
            layers[key]
            for key in (
                "teaching_candidate",
                "practice_candidate",
                "assessment_candidate",
                "four_skill_contract",
                "private_text_runtime",
            )
        ):
            classification = "DRAFT_ONLY"
        else:
            classification = "MISSING"

        row_records.append(
            {
                "canonical_egp_row_id": row_id,
                "grammar_unit_ids": grammar_ids,
                "internal_stages": sorted({str(unit.get("internal_stage")) for unit in row_units}),
                "classification": classification,
                "coverage_layers": layers,
                "four_skill_item_counts": {skill: int(four_skill_counts.get(skill, 0)) for skill in SKILLS},
                "text_runtime_item_counts": {
                    "reading": int(session_counts.get("reading", 0)),
                    "writing": int(session_counts.get("writing", 0)),
                },
                "content_review_state": "OPERATOR_REVIEW_PENDING"
                if any(unit.get("content_review_status") == "OPERATOR_REVIEW_NOT_COMPLETED" for unit in row_units)
                else "COMPLETE",
                "learner_evidence_state": "NOT_COLLECTED",
                "learner_mastery_state": "NOT_CLAIMED",
                "speaking_real_audio_evidence_state": "DEFERRED_BY_OPERATOR",
            }
        )

    classification_counts = Counter(row["classification"] for row in row_records)
    layer_counts = {
        layer: sum(row["coverage_layers"][layer] for row in row_records)
        for layer in COVERAGE_LAYERS
    }
    covered_rows = [row["canonical_egp_row_id"] for row in row_records if row["classification"] == "COVERED"]
    draft_rows = [row["canonical_egp_row_id"] for row in row_records if row["classification"] == "DRAFT_ONLY"]
    missing_rows = [row["canonical_egp_row_id"] for row in row_records if row["classification"] == "MISSING"]
    pending_units = sorted(
        grammar_id
        for grammar_id, unit in unit_by_id.items()
        if unit.get("content_review_status") == "OPERATOR_REVIEW_NOT_COMPLETED"
    )
    all_rows = [row["canonical_egp_row_id"] for row in row_records]

    report = {
        "task_id": TASK_ID,
        "epic_id": EPIC_ID,
        "artifact_type": "metadata_only_a1_a1plus_coverage_recheck_and_backlog",
        "schema_version": SCHEMA_VERSION,
        "scope": "A1_A1_PLUS_ONLY",
        "mode": "RECHECK_ONLY_NO_NEW_DESIGN_DOCS_NO_CANONICAL_GRAPH_WRITE",
        "source_hashes": {
            "rule_validator_index_sha256": sha256_value(rule_index),
            "candidate_coverage_sha256": sha256_value(candidate),
            "candidate_validation_sha256": sha256_value(candidate_validation),
            "four_skill_closure_sha256": sha256_value(four_skill),
            "text_session_bank_sha256": sha256_value(session_bank),
            "m05_receipt_sha256": sha256_value(receipts["m05"]),
            "m06_receipt_sha256": sha256_value(receipts["m06"]),
            "m07_receipt_sha256": sha256_value(receipts["m07"]),
            "m08_receipt_sha256": sha256_value(receipts["m08"]),
            "m09_receipt_sha256": sha256_value(receipts["m09"]),
        },
        "coverage_summary": {
            "canonical_grammar_unit_count": 24,
            "canonical_egp_row_count": 109,
            "covered_row_count": classification_counts["COVERED"],
            "draft_only_row_count": classification_counts["DRAFT_ONLY"],
            "missing_row_count": classification_counts["MISSING"],
            "structural_coverage_percent": _percent(classification_counts["COVERED"], 109),
            "candidate_teaching_row_coverage_percent": _percent(layer_counts["teaching_candidate"], 109),
            "candidate_practice_row_coverage_percent": _percent(layer_counts["practice_candidate"], 109),
            "candidate_assessment_row_coverage_percent": _percent(layer_counts["assessment_candidate"], 109),
            "four_skill_contract_row_coverage_percent": _percent(layer_counts["four_skill_contract"], 109),
            "private_text_runtime_row_coverage_percent": _percent(layer_counts["private_text_runtime"], 109),
            "actual_learner_evidence_row_coverage_percent": 0.0,
            "learner_mastery_row_coverage_percent": 0.0,
            "operator_reviewed_candidate_unit_count": 0,
            "operator_review_pending_candidate_unit_count": len(pending_units),
            "reading_reviewed_private_item_count": receipts["m05"].get("m04_preflight", {}).get("reviewed_item_count", 81),
            "listening_rendered_asset_count": receipts["m05"]["completion"]["rendered_audio"],
            "speaking_captured_audio_count": receipts["m06"]["evidence_state"]["captured_audio"],
        },
        "coverage_layer_counts": layer_counts,
        "classification_lists": {
            "covered_row_ids": covered_rows,
            "draft_only_row_ids": draft_rows,
            "missing_row_ids": missing_rows,
        },
        "rows": row_records,
        "backlog": {
            "structural_missing_row_ids": missing_rows,
            "draft_only_row_ids": draft_rows,
            "operator_content_review_pending_unit_ids": pending_units,
            "actual_learner_evidence_pending_row_ids": all_rows,
            "learner_mastery_unclaimed_row_ids": all_rows,
            "speaking_real_audio_deferred_row_ids": all_rows,
            "source_grounded_reading_row_audit": {
                "status": "NOT_AUDITABLE_FROM_COMMITTED_METADATA",
                "reason": "Committed Reading closeout exposes reviewed-item accounting but not a row-level source-text audit matrix.",
                "structural_coverage_impact": "NONE",
            },
        },
        "claim_boundaries": {
            "metadata_only_report": True,
            "new_design_docs_created": False,
            "new_planning_docs_created": False,
            "canonical_graph_written": False,
            "a2_a2plus_in_scope": False,
            "private_content_included": False,
            "source_text_included": False,
            "audio_bytes_included": False,
            "recording_files_processed": False,
            "learner_responses_included": False,
            "canonical_authority_writes": 0,
            "public_delivery_count": 0,
            "actual_learner_evidence_complete": False,
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
        },
        "validation_status": PASS_STATUS,
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    safe_scan(report, name="m10_coverage_recheck")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args(argv)
    try:
        report = build_report()
        write_json(args.output, report)
        print(
            json.dumps(
                {
                    "validation_status": report["validation_status"],
                    "canonical_egp_rows": report["coverage_summary"]["canonical_egp_row_count"],
                    "covered": report["coverage_summary"]["covered_row_count"],
                    "draft_only": report["coverage_summary"]["draft_only_row_count"],
                    "missing": report["coverage_summary"]["missing_row_count"],
                    "actual_learner_evidence_percent": report["coverage_summary"]["actual_learner_evidence_row_coverage_percent"],
                    "next_short_step": report["next_short_step"],
                },
                sort_keys=True,
            )
        )
        return 0
    except (CoverageRecheckError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
