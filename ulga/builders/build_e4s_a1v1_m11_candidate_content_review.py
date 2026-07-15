#!/usr/bin/env python3
"""Build the A1/A1+ candidate-unit review and private promotion workflow.

The 24 project-authored candidate units are complete structurally but require
operator content review. This engine prepares a private queue, validates explicit
operator decisions, reruns the existing candidate validator for revisions, and
materializes reviewed private learning units. It never promotes to canonical
Authority, public delivery, learner mastery, or A2/A2+.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator

SOURCE_REPO_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = SOURCE_REPO_ROOT
if str(SOURCE_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_REPO_ROOT))

from ulga.builders import build_a1_grammar_full_teachable_candidate_coverage as candidate  # noqa: E402

TASK_ID = "E4S-A1V1-M11_A1A1PlusCandidateContentReviewAndPrivatePromotion"
SCHEMA_VERSION_QUEUE = "e4s.a1v1.candidate_unit_review_queue.v1"
SCHEMA_VERSION_DECISIONS = "e4s.a1v1.candidate_unit_operator_decisions.v1"
SCHEMA_VERSION_BANK = "e4s.a1v1.reviewed_private_learning_unit_bank.v1"
SCHEMA_VERSION_REPORT = "e4s.a1v1.candidate_unit_review_safe_report.v1"
PENDING_STATUS = "PASS_PENDING_OPERATOR_REVIEW"
PARTIAL_STATUS = "PASS_PARTIAL_OPERATOR_REVIEW"
COMPLETE_STATUS = "PASS_OPERATOR_REVIEW_COMPLETE"
NEXT_RESUME_TASK = TASK_ID
DEFAULT_OUTPUT_ROOT = REPO_ROOT / ".local/e4s_a1v1/content_review/m11"
SCHEMA_DIR = SOURCE_REPO_ROOT / "ulga/schemas"
DECISIONS = (
    "PENDING",
    "APPROVE_AS_IS",
    "APPROVE_WITH_REVISION",
    "REJECT",
    "DEFER",
)
REVIEW_REQUIREMENTS = (
    "canonical_mapping_verified",
    "validator_alignment_verified",
    "learning_objectives_clear",
    "form_rules_accurate",
    "meaning_and_usage_accurate",
    "positive_examples_natural_and_valid",
    "negative_examples_valid_and_explanatory",
    "practice_items_valid",
    "assessment_items_valid",
    "a1_a1plus_level_appropriate",
    "project_authored_content_boundary_verified",
    "no_a2_expansion",
)
SAFE_FORBIDDEN_KEYS = {
    "candidate_unit_payload",
    "final_private_unit_payload",
    "revision",
    "review_notes",
    "prompt",
    "prompt_text",
    "answer",
    "answer_key",
    "answer_contract",
    "accepted_texts",
    "model_text",
    "model_texts",
    "transcript",
    "source_payload",
}
FORBIDDEN_REASON_PARTS = ("PROMPT", "ANSWER", "TRANSCRIPT", "SOURCE_TEXT")


class CandidateReviewError(ValueError):
    """Fail-closed M11 review error."""


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
        raise CandidateReviewError(f"json_unreadable:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise CandidateReviewError(f"json_root_not_object:{path}")
    return value


def write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _schema(name: str) -> dict[str, Any]:
    return read_json(SCHEMA_DIR / name)


def _assert_schema(name: str, value: Mapping[str, Any]) -> None:
    errors = sorted(
        Draft202012Validator(_schema(name)).iter_errors(value),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "$"
        raise CandidateReviewError(
            f"schema_validation_failed:{name}:{location}:{first.message}"
        )


def _safe_output_root(path: Path) -> Path:
    resolved = path.resolve()
    approved = (REPO_ROOT / ".local").resolve()
    if not resolved.is_relative_to(approved):
        raise CandidateReviewError(f"output_root_outside_local:{resolved}")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _safe_scan(value: Any, *, name: str) -> None:
    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                lowered = str(key).casefold()
                if lowered in SAFE_FORBIDDEN_KEYS or lowered.endswith("_absolute_path"):
                    raise CandidateReviewError(f"private_field_leak:{name}:{key}")
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
        elif isinstance(node, str):
            if Path(node).is_absolute() or (
                len(node) > 2 and node[1:3] in {":\\", ":/"}
            ):
                raise CandidateReviewError(f"absolute_path_leak:{name}")

    walk(value)


def _parse_timestamp(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CandidateReviewError(code)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CandidateReviewError(code) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CandidateReviewError(code)
    return value


def _candidate_inputs() -> tuple[dict[str, Any], ...]:
    return (
        candidate.load_json(candidate.QUERY_PATH),
        candidate.load_json(candidate.RULE_INDEX_PATH),
        candidate.load_json(candidate.AUTHORITY_PATH),
        candidate.load_json(candidate.CAN_RULE_PATH),
        candidate.load_json(candidate.BATCH_01_PATH),
        candidate.load_json(candidate.BATCH_02_PATH),
    )


def _source_candidate() -> tuple[dict[str, Any], dict[str, Any]]:
    artifact, validation = candidate.build_and_validate_from_repo()
    if validation.get("validation_status") != "PASS":
        raise CandidateReviewError(
            f"candidate_source_validation_failed:{validation.get('errors')}"
        )
    summary = artifact.get("coverage_summary", {})
    expected = {
        "canonical_unit_count": 24,
        "canonical_unique_egp_row_count": 109,
        "candidate_teaching_ready_unit_count": 24,
        "candidate_practice_ready_unit_count": 24,
        "candidate_assessment_ready_unit_count": 24,
        "promoted_private_learning_unit_count": 0,
        "mastery_trackable_unit_count": 0,
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            raise CandidateReviewError(
                f"candidate_source_count_drift:{key}:{summary.get(key)}"
            )
    return artifact, validation


def _review_entry_id(grammar_unit_id: str) -> str:
    token = hashlib.sha256(grammar_unit_id.encode("utf-8")).hexdigest()[:20].upper()
    return f"M11_REVIEW_{token}"


def _unit_prechecks(unit: Mapping[str, Any]) -> dict[str, Any]:
    readiness = unit.get("readiness", {})
    checks = {
        "canonical_row_binding_valid": (
            isinstance(unit.get("canonical_egp_row_ids"), list)
            and all(
                isinstance(row_id, str) and bool(row_id)
                for row_id in unit.get("canonical_egp_row_ids", [])
            )
        ),
        "learning_objective_minimum": len(unit.get("learning_objectives", [])) >= 2,
        "form_rule_minimum": len(unit.get("form_rules", [])) >= 1,
        "meaning_function_minimum": len(unit.get("meaning_functions", [])) >= 1,
        "usage_condition_minimum": len(unit.get("usage_conditions", [])) >= 2,
        "positive_example_minimum": len(unit.get("positive_examples", [])) >= 2,
        "negative_example_minimum": len(unit.get("negative_examples", [])) >= 3,
        "practice_item_count": len(unit.get("practice_items", [])) >= 6,
        "assessment_item_count": len(unit.get("assessment_items", [])) >= 2,
        "candidate_teachable": readiness.get("candidate_teachable") is True,
        "candidate_practice_ready": readiness.get("candidate_practice_ready") is True,
        "candidate_assessment_ready": readiness.get("candidate_assessment_ready") is True,
        "not_pre_promoted": readiness.get("promoted_for_private_learning") is False,
        "not_mastery_trackable": readiness.get("mastery_trackable") is False,
        "a1_a1plus_stage": unit.get("internal_stage") in {"A1", "A1+"},
    }
    return {
        "overall_status": "PASS" if all(checks.values()) else "BLOCK",
        "checks": checks,
    }


def build_review_queue(candidate_artifact: Mapping[str, Any]) -> dict[str, Any]:
    units = list(candidate_artifact.get("learning_units", []))
    if len(units) != 24:
        raise CandidateReviewError("candidate_unit_count_not_24")
    entries: list[dict[str, Any]] = []
    for unit in units:
        grammar_id = str(unit["grammar_unit_id"])
        entries.append(
            {
                "review_entry_id": _review_entry_id(grammar_id),
                "grammar_unit_id": grammar_id,
                "internal_stage": unit["internal_stage"],
                "canonical_egp_row_ids": list(unit["canonical_egp_row_ids"]),
                "candidate_payload_sha256": sha256_value(unit),
                "candidate_unit_payload": deepcopy(unit),
                "automated_prechecks": _unit_prechecks(unit),
                "review_requirements": list(REVIEW_REQUIREMENTS),
            }
        )
    entries.sort(key=lambda row: (row["candidate_unit_payload"].get("sequence_index", 0), row["grammar_unit_id"]))
    if len({entry["review_entry_id"] for entry in entries}) != 24:
        raise CandidateReviewError("review_entry_identity_collision")
    queue = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION_QUEUE,
        "private_local_only": True,
        "source_candidate_sha256": sha256_value(candidate_artifact),
        "review_entry_count": 24,
        "review_entries": entries,
        "review_entries_sha256": sha256_value(entries),
        "claim_boundaries": {
            "private_local_only": True,
            "canonical_authority_promotion": False,
            "public_delivery": False,
            "learner_mastery_claimed": False,
            "a2_a2plus_in_scope": False,
        },
    }
    _assert_schema("e4s_a1v1_candidate_unit_review_queue.schema.json", queue)
    return queue


def build_decision_template(queue: Mapping[str, Any]) -> dict[str, Any]:
    decisions = [
        {
            "review_entry_id": entry["review_entry_id"],
            "grammar_unit_id": entry["grammar_unit_id"],
            "candidate_payload_sha256": entry["candidate_payload_sha256"],
            "decision": "PENDING",
            "reviewer_id": None,
            "reviewed_at": None,
            "criteria": {key: None for key in REVIEW_REQUIREMENTS},
            "revision": None,
            "reason_codes": [],
            "review_notes": None,
        }
        for entry in queue["review_entries"]
    ]
    registry = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION_DECISIONS,
        "private_local_only": True,
        "review_queue_sha256": sha256_value(queue),
        "decision_count": 24,
        "decisions": decisions,
    }
    _assert_schema(
        "e4s_a1v1_candidate_unit_operator_decisions.schema.json", registry
    )
    return registry


def _validate_reason_codes(codes: Any, *, entry_id: str) -> list[str]:
    if not isinstance(codes, list) or not all(isinstance(code, str) for code in codes):
        raise CandidateReviewError(f"reason_codes_invalid:{entry_id}")
    if len(set(codes)) != len(codes):
        raise CandidateReviewError(f"reason_codes_duplicate:{entry_id}")
    for code in codes:
        if not re.fullmatch(r"[A-Z0-9_]{3,80}", code):
            raise CandidateReviewError(f"reason_code_format_invalid:{entry_id}:{code}")
        if any(part in code for part in FORBIDDEN_REASON_PARTS):
            raise CandidateReviewError(f"reason_code_safe_report_forbidden:{entry_id}:{code}")
    return list(codes)


def _validate_decision(
    decision: Mapping[str, Any],
    entry: Mapping[str, Any],
) -> None:
    entry_id = str(entry["review_entry_id"])
    if decision.get("grammar_unit_id") != entry.get("grammar_unit_id"):
        raise CandidateReviewError(f"decision_unit_join_drift:{entry_id}")
    if decision.get("candidate_payload_sha256") != entry.get("candidate_payload_sha256"):
        raise CandidateReviewError(f"candidate_hash_drift:{entry_id}")
    value = decision.get("decision")
    if value not in DECISIONS:
        raise CandidateReviewError(f"decision_value_invalid:{entry_id}")
    criteria = decision.get("criteria")
    if not isinstance(criteria, Mapping) or set(criteria) != set(REVIEW_REQUIREMENTS):
        raise CandidateReviewError(f"criteria_keys_invalid:{entry_id}")
    reason_codes = _validate_reason_codes(decision.get("reason_codes"), entry_id=entry_id)
    if value == "PENDING":
        if decision.get("reviewer_id") is not None or decision.get("reviewed_at") is not None:
            raise CandidateReviewError(f"pending_decision_has_reviewer:{entry_id}")
        if any(criteria[key] is not None for key in REVIEW_REQUIREMENTS):
            raise CandidateReviewError(f"pending_decision_has_criteria:{entry_id}")
        if decision.get("revision") is not None or reason_codes:
            raise CandidateReviewError(f"pending_decision_has_payload:{entry_id}")
        return
    if not isinstance(decision.get("reviewer_id"), str) or not str(decision.get("reviewer_id")).strip():
        raise CandidateReviewError(f"reviewer_missing:{entry_id}")
    _parse_timestamp(decision.get("reviewed_at"), f"review_timestamp_invalid:{entry_id}")
    if not all(isinstance(criteria[key], bool) for key in REVIEW_REQUIREMENTS):
        raise CandidateReviewError(f"criteria_incomplete:{entry_id}")
    if value in {"APPROVE_AS_IS", "APPROVE_WITH_REVISION"}:
        if entry.get("automated_prechecks", {}).get("overall_status") == "BLOCK":
            raise CandidateReviewError(f"approved_blocked_unit:{entry_id}")
        if not all(criteria[key] is True for key in REVIEW_REQUIREMENTS):
            raise CandidateReviewError(f"approved_criteria_not_all_true:{entry_id}")
        if reason_codes:
            raise CandidateReviewError(f"approved_has_reason_codes:{entry_id}")
    if value == "APPROVE_AS_IS" and decision.get("revision") is not None:
        raise CandidateReviewError(f"approve_as_is_has_revision:{entry_id}")
    if value == "APPROVE_WITH_REVISION":
        revision = decision.get("revision")
        if not isinstance(revision, Mapping) or set(revision) != {"replacement_unit_payload"}:
            raise CandidateReviewError(f"revision_contract_invalid:{entry_id}")
        if not isinstance(revision.get("replacement_unit_payload"), Mapping):
            raise CandidateReviewError(f"revision_payload_invalid:{entry_id}")
    elif decision.get("revision") is not None:
        raise CandidateReviewError(f"non_revision_decision_has_revision:{entry_id}")
    if value in {"REJECT", "DEFER"} and not reason_codes:
        raise CandidateReviewError(f"non_approval_reason_required:{entry_id}")


def _validate_revised_candidate(
    source_candidate: Mapping[str, Any],
    replacements: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    revised = deepcopy(source_candidate)
    units: list[dict[str, Any]] = []
    for unit in revised["learning_units"]:
        grammar_id = str(unit["grammar_unit_id"])
        replacement = deepcopy(replacements.get(grammar_id, unit))
        if replacement.get("grammar_unit_id") != grammar_id:
            raise CandidateReviewError(f"revision_grammar_unit_drift:{grammar_id}")
        if replacement.get("canonical_egp_row_ids") != unit.get("canonical_egp_row_ids"):
            raise CandidateReviewError(f"revision_canonical_rows_drift:{grammar_id}")
        if replacement.get("internal_stage") != unit.get("internal_stage"):
            raise CandidateReviewError(f"revision_stage_drift:{grammar_id}")
        if replacement.get("prerequisite_unit_ids") != unit.get("prerequisite_unit_ids"):
            raise CandidateReviewError(f"revision_prerequisite_drift:{grammar_id}")
        units.append(replacement)
    revised["learning_units"] = units
    validation = candidate.validate_artifact(revised, *_candidate_inputs())
    if validation.get("validation_status") != "PASS":
        raise CandidateReviewError(
            "revised_candidate_validation_failed:"
            + ",".join(validation.get("errors", []))
        )
    return revised


def build_review_artifacts(
    queue: Mapping[str, Any],
    registry: Mapping[str, Any],
    source_candidate: Mapping[str, Any],
    *,
    report_mode: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _assert_schema("e4s_a1v1_candidate_unit_review_queue.schema.json", queue)
    _assert_schema(
        "e4s_a1v1_candidate_unit_operator_decisions.schema.json", registry
    )
    if registry.get("review_queue_sha256") != sha256_value(queue):
        raise CandidateReviewError("decision_registry_queue_hash_drift")
    if queue.get("source_candidate_sha256") != sha256_value(source_candidate):
        raise CandidateReviewError("queue_source_candidate_hash_drift")

    entries = list(queue["review_entries"])
    entry_by_id = {entry["review_entry_id"]: entry for entry in entries}
    if len(entry_by_id) != 24:
        raise CandidateReviewError("review_queue_duplicate_identity")
    decision_by_id: dict[str, Mapping[str, Any]] = {}
    for decision in registry["decisions"]:
        entry_id = str(decision.get("review_entry_id") or "")
        if entry_id not in entry_by_id:
            raise CandidateReviewError(f"unknown_decision:{entry_id}")
        if entry_id in decision_by_id:
            raise CandidateReviewError(f"duplicate_decision:{entry_id}")
        decision_by_id[entry_id] = decision
    if set(decision_by_id) != set(entry_by_id):
        missing = sorted(set(entry_by_id) - set(decision_by_id))
        raise CandidateReviewError("missing_decisions:" + ",".join(missing))

    replacements: dict[str, Mapping[str, Any]] = {}
    decision_counts: Counter[str] = Counter()
    reason_counts: Counter[str] = Counter()
    for entry in entries:
        decision = decision_by_id[entry["review_entry_id"]]
        _validate_decision(decision, entry)
        value = str(decision["decision"])
        decision_counts[value] += 1
        reason_counts.update(decision.get("reason_codes", []))
        if value == "APPROVE_WITH_REVISION":
            replacements[entry["grammar_unit_id"]] = decision["revision"]["replacement_unit_payload"]

    revised_candidate = _validate_revised_candidate(source_candidate, replacements)
    revised_by_id = {
        str(unit["grammar_unit_id"]): unit
        for unit in revised_candidate["learning_units"]
    }
    reviewed_units: list[dict[str, Any]] = []
    reviewed_rows: set[str] = set()
    for entry in entries:
        decision = decision_by_id[entry["review_entry_id"]]
        value = str(decision["decision"])
        if value not in {"APPROVE_AS_IS", "APPROVE_WITH_REVISION"}:
            continue
        grammar_id = str(entry["grammar_unit_id"])
        final_payload = deepcopy(revised_by_id[grammar_id])
        reviewed_rows.update(entry["canonical_egp_row_ids"])
        token = hashlib.sha256(grammar_id.encode("utf-8")).hexdigest()[:20].upper()
        reviewed_units.append(
            {
                "reviewed_unit_id": f"M11_UNIT_{token}",
                "status": "REVIEWED_PRIVATE_LEARNING_UNIT",
                "grammar_unit_id": grammar_id,
                "internal_stage": entry["internal_stage"],
                "canonical_egp_row_ids": list(entry["canonical_egp_row_ids"]),
                "final_private_unit_payload": final_payload,
                "reviewer_id": decision["reviewer_id"],
                "decision_timestamp": decision["reviewed_at"],
                "decision_record_sha256": sha256_value(decision),
                "candidate_payload_sha256": entry["candidate_payload_sha256"],
                "private_learning_ready": True,
                "mastery_trackable": False,
                "canonical_authority_promotion": False,
            }
        )
    reviewed_units.sort(key=lambda row: row["grammar_unit_id"])
    bank = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION_BANK,
        "private_local_only": True,
        "source_review_queue_sha256": sha256_value(queue),
        "source_decisions_sha256": sha256_value(registry),
        "reviewed_unit_count": len(reviewed_units),
        "canonical_egp_row_count": len(reviewed_rows),
        "reviewed_units": reviewed_units,
        "reviewed_units_sha256": sha256_value(reviewed_units),
        "claim_boundaries": {
            "private_local_only": True,
            "must_not_be_committed": True,
            "canonical_authority_promotion": False,
            "public_delivery": False,
            "learner_mastery_claimed": False,
            "persistent_learner_state_write": False,
            "a2_a2plus_in_scope": False,
        },
    }
    _assert_schema("e4s_a1v1_reviewed_private_learning_unit_bank.schema.json", bank)

    pending = decision_counts["PENDING"]
    completed_decisions = 24 - pending
    status = PENDING_STATUS if completed_decisions == 0 else PARTIAL_STATUS if pending else COMPLETE_STATUS
    precheck_counts = Counter(
        entry["automated_prechecks"]["overall_status"] for entry in entries
    )
    report = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION_REPORT,
        "report_mode": report_mode,
        "candidate_unit_count": 24,
        "canonical_egp_row_count": 109,
        "decision_counts": {value: decision_counts[value] for value in DECISIONS},
        "reviewed_unit_count": len(reviewed_units),
        "reviewed_row_count": len(reviewed_rows),
        "precheck_distribution": {
            value: precheck_counts[value] for value in ("PASS", "WARNING", "BLOCK")
        },
        "reason_code_counts": dict(sorted(reason_counts.items())),
        "claim_boundaries": {
            "metadata_only_report": True,
            "private_candidate_content_included": False,
            "canonical_authority_promotion": False,
            "public_delivery": False,
            "learner_mastery_claimed": False,
            "persistent_learner_state_write": False,
            "audio_or_recording_processed": False,
            "a2_a2plus_in_scope": False,
        },
        "validation_status": status,
        "stop_reason": "OPERATOR_CONTENT_REVIEW_DECISIONS_REQUIRED" if pending else "NONE",
        "next_resume_task": NEXT_RESUME_TASK,
        "errors": [],
    }
    _safe_scan(report, name="candidate_review_safe_report")
    _assert_schema("e4s_a1v1_candidate_unit_review_safe_report.schema.json", report)
    return bank, report


def prepare_review(output_root: Path) -> dict[str, Any]:
    root = _safe_output_root(output_root)
    source, _ = _source_candidate()
    queue = build_review_queue(source)
    decisions = build_decision_template(queue)
    bank, report = build_review_artifacts(
        queue, decisions, source, report_mode="PREPARE_REVIEW"
    )
    write_json_atomic(root / "candidate_unit_review_queue.private.json", queue)
    write_json_atomic(root / "candidate_unit_operator_decisions.template.json", decisions)
    write_json_atomic(root / "reviewed_private_learning_unit_bank.json", bank)
    write_json_atomic(root / "candidate_unit_review_safe_report.json", report)
    return {"queue": queue, "decisions": decisions, "bank": bank, "safe_report": report}


def apply_decisions(
    output_root: Path,
    decision_path: Path,
) -> dict[str, Any]:
    root = _safe_output_root(output_root)
    source, _ = _source_candidate()
    queue = read_json(root / "candidate_unit_review_queue.private.json")
    registry = read_json(decision_path)
    bank, report = build_review_artifacts(
        queue, registry, source, report_mode="APPLY_DECISIONS"
    )
    write_json_atomic(root / "candidate_unit_operator_decisions.private.json", registry)
    write_json_atomic(root / "reviewed_private_learning_unit_bank.json", bank)
    write_json_atomic(root / "candidate_unit_review_safe_report.json", report)
    return {"bank": bank, "safe_report": report}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare-review")
    prepare.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    apply = sub.add_parser("apply-decisions")
    apply.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    apply.add_argument("--decisions", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = prepare_review(args.output_root) if args.command == "prepare-review" else apply_decisions(args.output_root, args.decisions)
        print(json.dumps({
            "candidate_units": 24,
            "pending_decisions": result["safe_report"]["decision_counts"]["PENDING"],
            "reviewed_units": result["safe_report"]["reviewed_unit_count"],
            "reviewed_rows": result["safe_report"]["reviewed_row_count"],
            "validation_status": result["safe_report"]["validation_status"],
            "stop_reason": result["safe_report"]["stop_reason"],
        }, sort_keys=True))
        return 0
    except (CandidateReviewError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
