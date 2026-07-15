#!/usr/bin/env python3
"""Build local/private Reading-Writing sessions and progress evidence.

The engine consumes the approved 192-item A1/A1+ text-mode package. It creates a
learner-safe local session UI, accepts typed/select/order responses, performs only
contract-supported deterministic scoring, and routes productive writing to an
explicit human-review fallback. Evidence remains private under `.local/`; no
mastery, retention, public delivery, Authority write, audio work, or A2 expansion
is claimed.
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

from ulga.builders.build_a1_a1plus_shared_item_contract import (  # noqa: E402
    build_artifact as build_shared_contract,
)
from ulga.builders.build_a1_grammar_text_mode_private_pilot_package import (  # noqa: E402
    build_and_validate_from_repo as build_text_package,
)

TASK_ID = "E4S-A1V1-M08_TextModeLearnerSessionAndProgressEvidenceIntegration"
EPIC_ID = "E4S-A1V1_A1A1PlusCompleteFourSkillLearningSystem"
SESSION_SCHEMA_VERSION = "e4s.a1v1.text_mode_session_bank.v1"
ATTEMPT_SCHEMA_VERSION = "e4s.a1v1.text_mode_attempt_registry.v1"
LEDGER_SCHEMA_VERSION = "e4s.a1v1.text_mode_progress_ledger.v1"
SAFE_REPORT_SCHEMA_VERSION = "e4s.a1v1.text_mode_progress_safe_report.v1"
ZERO_STATUS = "PASS_AWAITING_TEXT_MODE_LEARNER_ATTEMPTS"
PARTIAL_STATUS = "PASS_PARTIAL_TEXT_MODE_PROGRESS_EVIDENCE"
COMPLETE_STATUS = "PASS_TEXT_MODE_SESSION_EVIDENCE_COMPLETE"
NEXT_SHORT_STEP = "E4S-A1V1-M09_A1A1PlusPrivateLearningRuntimeAcceptanceAndCloseout"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / ".local/e4s_a1v1/text_mode/m08"
M07_RECEIPT_PATH = REPO_ROOT / "ulga/reports/e4s_a1v1_m07_four_skill_contract_closure.json"
SCHEMA_DIR = SOURCE_REPO_ROOT / "ulga/schemas"
SKILLS = ("reading", "writing")
OUTCOMES = (
    "AUTO_PASS",
    "AUTO_FAIL",
    "PENDING_HUMAN_REVIEW",
    "HUMAN_APPROVE",
    "HUMAN_REJECT",
    "HUMAN_DEFER",
)
REVIEW_DECISIONS = {"PENDING", "APPROVE", "REJECT", "DEFER"}
LEARNER_FORBIDDEN_KEYS = {
    "answer",
    "answer_key",
    "answer_contract",
    "accepted_texts",
    "accepted_sequence",
    "accepted_missing_tokens",
    "canonical_target",
    "correct_token_sequence",
    "correct_morphology_parts",
    "private_scoring_contract",
    "scoring_rubric",
    "model_answer",
    "model_text",
    "model_texts",
    "source_payload",
    "review_notes",
    "operator_notes",
}
SAFE_REPORT_FORBIDDEN_KEYS = LEARNER_FORBIDDEN_KEYS | {
    "prompt",
    "context",
    "response",
    "learner_ref",
    "session_id",
    "submitted_at",
    "reviewer_id",
    "reviewed_at",
}


class TextModeSessionError(ValueError):
    """Fail-closed M08 session/evidence error."""


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
        raise TextModeSessionError(f"json_unreadable:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise TextModeSessionError(f"json_root_not_object:{path}")
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
        raise TextModeSessionError(
            f"schema_validation_failed:{name}:{location}:{first.message}"
        )


def _safe_output_root(path: Path) -> Path:
    resolved = path.resolve()
    approved = (REPO_ROOT / ".local").resolve()
    if not resolved.is_relative_to(approved):
        raise TextModeSessionError(f"output_root_outside_local:{resolved}")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _safe_scan(value: Any, *, name: str, forbidden: set[str]) -> None:
    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                lowered = str(key).casefold()
                if lowered in forbidden or lowered.endswith("_absolute_path"):
                    raise TextModeSessionError(
                        f"private_field_leak:{name}:{key}"
                    )
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
        elif isinstance(node, str):
            if Path(node).is_absolute() or (
                len(node) > 2 and node[1:3] in {":\\", ":/"}
            ):
                raise TextModeSessionError(f"absolute_path_leak:{name}")

    walk(value)


def _require(actual: Any, expected: Any, code: str) -> None:
    if actual != expected:
        raise TextModeSessionError(
            f"{code}:expected={expected!r}:actual={actual!r}"
        )


def _parse_timezone_timestamp(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TextModeSessionError(code)
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise TextModeSessionError(code) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise TextModeSessionError(code)
    return value


def _validate_m07(receipt: Mapping[str, Any]) -> None:
    _require(
        receipt.get("task_id"),
        "E4S-A1V1-M07_FourSkillContractClosureAndSystemIntegration_NoAudioEvidence",
        "m07_task_id",
    )
    _require(
        receipt.get("validation_status"),
        "PASS_M07_FOUR_SKILL_CONTRACT_CLOSURE_NO_AUDIO_EVIDENCE",
        "m07_status",
    )
    completion = receipt.get("completion", {})
    for key, expected in {
        "shared_items": 384,
        "learning_units": 24,
        "canonical_egp_rows": 109,
        "skills_closed": 4,
        "units_with_all_four_skills": 24,
        "rows_with_all_four_skills": 109,
    }.items():
        _require(completion.get(key), expected, f"m07_{key}")
    deferred = receipt.get("operator_deferred_conditions", {})
    _require(
        deferred.get("speaking_real_audio_evidence"),
        "DEFERRED_BY_OPERATOR",
        "m07_speaking_audio_state",
    )
    _require(
        deferred.get("blocks_m08_progression"),
        False,
        "m07_speaking_audio_blocks_m08",
    )
    _require(
        receipt.get("next_short_step"),
        TASK_ID,
        "m07_next_short_step",
    )
    boundaries = receipt.get("claim_boundaries", {})
    for key, expected in {
        "canonical_authority_writes": 0,
        "public_delivery_count": 0,
        "persistent_learner_state_writes": 0,
        "actual_learner_evidence_complete": False,
        "learner_mastery_claimed": False,
        "production_runtime_enabled": False,
        "a2_a2plus_in_scope": False,
    }.items():
        _require(boundaries.get(key), expected, f"m07_boundary_{key}")


def _learner_contract(item: Mapping[str, Any]) -> dict[str, Any]:
    response_mode = str(item.get("response_mode") or "short_text")
    contract: dict[str, Any] = {
        "prompt": str(item.get("prompt") or "Complete the item."),
        "response_mode": response_mode,
    }
    context = item.get("context")
    if isinstance(context, Mapping):
        contract["context"] = deepcopy(dict(context))
    if response_mode == "select_one":
        contract["options"] = list(item.get("options", []))
    elif response_mode == "ordered_tokens":
        contract["supplied_tokens"] = list(item.get("token_sequence", []))
    elif response_mode == "ordered_morphemes":
        contract["supplied_morphemes"] = list(
            item.get("morphology_parts", [])
        )
    elif item.get("task_type") == "structured_gap_fill":
        gap = item.get("gap_spec", {})
        contract["gap_display_tokens"] = list(gap.get("display_tokens", []))
    return contract


def _private_scoring_contract(item: Mapping[str, Any]) -> dict[str, Any]:
    response_mode = str(item.get("response_mode") or "short_text")
    accepted = list(item.get("answer_key", {}).get("accepted_texts", []))
    task_type = str(item.get("task_type") or "")
    if response_mode == "select_one":
        return {
            "scoring_mode": "EXACT_OPTION",
            "response_type": "string",
            "accepted_texts": accepted,
            "human_review_fallback": False,
        }
    if response_mode == "ordered_tokens":
        return {
            "scoring_mode": "EXACT_SEQUENCE",
            "response_type": "string_array",
            "accepted_sequence": list(item.get("correct_token_sequence", [])),
            "human_review_fallback": False,
        }
    if response_mode == "ordered_morphemes":
        return {
            "scoring_mode": "EXACT_SEQUENCE",
            "response_type": "string_array",
            "accepted_sequence": list(
                item.get("correct_morphology_parts", [])
            ),
            "human_review_fallback": False,
        }
    if task_type == "structured_gap_fill":
        gap = item.get("gap_spec", {})
        accepted_missing = list(gap.get("accepted_missing_tokens", []))
        return {
            "scoring_mode": "NORMALIZED_TEXT",
            "response_type": "string",
            "accepted_texts": accepted_missing + accepted,
            "case_insensitive": bool(
                item.get("accepted_variation_policy", {}).get(
                    "case_insensitive", True
                )
            ),
            "punctuation_tolerance": True,
            "human_review_fallback": False,
        }
    if isinstance(item.get("scoring_rubric"), Mapping):
        return {
            "scoring_mode": "FEATURE_RUBRIC",
            "response_type": "string",
            "model_texts": accepted,
            "rubric": deepcopy(dict(item["scoring_rubric"])),
            "human_review_fallback": True,
        }
    return {
        "scoring_mode": "NORMALIZED_TEXT",
        "response_type": "string",
        "accepted_texts": accepted,
        "case_insensitive": True,
        "punctuation_tolerance": True,
        "human_review_fallback": False,
    }


def build_session_bank(
    m07_receipt: Mapping[str, Any],
    text_package: Mapping[str, Any],
    shared_contract: Mapping[str, Any],
) -> dict[str, Any]:
    _validate_m07(m07_receipt)
    manifest = text_package.get("package_manifest", {})
    for key, expected in {
        "unit_count": 24,
        "canonical_row_count": 109,
        "item_count": 192,
        "practice_item_count": 144,
        "assessment_item_count": 48,
        "reading_item_count": 96,
        "writing_item_count": 96,
        "pilot_started": False,
    }.items():
        _require(manifest.get(key), expected, f"text_package_{key}")
    _require(
        text_package.get("release_gates", {}).get(
            "text_mode_private_pilot_package_gate"
        ),
        "PASS_READY",
        "text_package_gate",
    )

    shared_items = [
        item
        for item in shared_contract.get("shared_items", [])
        if item.get("skill") in SKILLS
    ]
    _require(len(shared_items), 192, "shared_text_item_count")
    shared_by_source = {
        str(item["source_item_id"]): item for item in shared_items
    }
    _require(len(shared_by_source), 192, "shared_text_identity_count")

    units = {
        str(unit["grammar_unit_id"]): unit
        for unit in text_package.get("learning_units", [])
    }
    _require(len(units), 24, "text_package_unit_count")

    session_items: list[dict[str, Any]] = []
    for item in text_package.get("item_bank", []):
        item_id = str(item.get("item_id") or "")
        shared = shared_by_source.get(item_id)
        if not shared:
            raise TextModeSessionError(f"shared_item_join_missing:{item_id}")
        grammar_focus = item.get("content_binding", {}).get(
            "grammar_focus", []
        )
        if len(grammar_focus) != 1:
            raise TextModeSessionError(f"grammar_focus_invalid:{item_id}")
        grammar_id = str(grammar_focus[0])
        unit = units.get(grammar_id)
        if not unit:
            raise TextModeSessionError(f"unit_join_missing:{item_id}")
        rows = list(
            item.get("content_binding", {}).get(
                "canonical_egp_row_ids", []
            )
        )
        _require(
            rows,
            list(shared.get("content_binding", {}).get(
                "canonical_egp_row_ids", []
            )),
            f"row_join_drift:{item_id}",
        )
        session_items.append(
            {
                "session_item_id": f"M08_SESSION:{item_id}",
                "item_id": item_id,
                "shared_item_id": shared["shared_item_id"],
                "learning_unit_id": shared["learning_unit_id"],
                "grammar_unit_id": grammar_id,
                "canonical_egp_row_ids": rows,
                "internal_stage": shared["internal_stage"],
                "skill": item["skill"],
                "item_role": item["item_role"],
                "evidence_dimension": item["evidence_dimension"],
                "task_type": item["task_type"],
                "learner_contract": _learner_contract(item),
                "private_scoring_contract": _private_scoring_contract(item),
                "session_status": "READY_FOR_LOCAL_TEXT_SESSION",
            }
        )

    sequence = {
        grammar_id: int(unit["sequence_index"])
        for grammar_id, unit in units.items()
    }
    session_items.sort(
        key=lambda row: (
            sequence[row["grammar_unit_id"]],
            SKILLS.index(row["skill"]),
            0 if row["item_role"] == "practice" else 1,
            row["item_id"],
        )
    )
    _require(len(session_items), 192, "session_item_count")
    _require(
        len({row["item_id"] for row in session_items}),
        192,
        "session_item_identity_count",
    )
    _require(
        len(
            {
                row_id
                for row in session_items
                for row_id in row["canonical_egp_row_ids"]
            }
        ),
        109,
        "session_row_coverage",
    )

    bank = {
        "task_id": TASK_ID,
        "schema_version": SESSION_SCHEMA_VERSION,
        "private_local_only": True,
        "source_hashes": {
            "m07_receipt_sha256": sha256_value(m07_receipt),
            "text_package_sha256": sha256_value(text_package),
            "shared_contract_sha256": sha256_value(shared_contract),
        },
        "item_count": 192,
        "unit_count": 24,
        "canonical_egp_row_count": 109,
        "items": session_items,
        "items_sha256": sha256_value(session_items),
        "claim_boundaries": {
            "private_local_only": True,
            "audio_required": False,
            "canonical_authority_write": False,
            "public_delivery": False,
            "persistent_learner_state_write": False,
            "learner_mastery_claimed": False,
        },
    }
    _assert_schema("e4s_a1v1_text_mode_session_bank.schema.json", bank)
    return bank


def build_learner_safe_payload(bank: Mapping[str, Any]) -> dict[str, Any]:
    items = [
        {
            "item_id": item["item_id"],
            "shared_item_id": item["shared_item_id"],
            "grammar_unit_id": item["grammar_unit_id"],
            "internal_stage": item["internal_stage"],
            "skill": item["skill"],
            "item_role": item["item_role"],
            "evidence_dimension": item["evidence_dimension"],
            "task_type": item["task_type"],
            **deepcopy(item["learner_contract"]),
        }
        for item in bank["items"]
    ]
    payload = {
        "task_id": TASK_ID,
        "schema_version": "e4s.a1v1.text_mode_learner_safe_payload.v1",
        "session_bank_sha256": sha256_value(bank),
        "item_count": len(items),
        "audio_required": False,
        "network_submission_enabled": False,
        "items": items,
    }
    _safe_scan(
        payload,
        name="learner_safe_payload",
        forbidden=LEARNER_FORBIDDEN_KEYS,
    )
    return payload


def empty_attempt_registry(bank: Mapping[str, Any]) -> dict[str, Any]:
    registry = {
        "task_id": TASK_ID,
        "schema_version": ATTEMPT_SCHEMA_VERSION,
        "private_local_only": True,
        "session_bank_sha256": sha256_value(bank),
        "session_id": "local-session-001",
        "learner_ref": "learner-local-001",
        "attempts": [],
    }
    _assert_schema(
        "e4s_a1v1_text_mode_attempt_registry.schema.json", registry
    )
    return registry


def _empty_review() -> dict[str, Any]:
    return {
        "decision": "PENDING",
        "reviewer_id": None,
        "reviewed_at": None,
        "criteria": {
            "grammar_target_match": None,
            "meaning_matches_context": None,
            "complete_response": None,
        },
        "notes": None,
    }


def _normalize_text(
    value: str,
    *,
    case_insensitive: bool = True,
    punctuation_tolerance: bool = True,
) -> str:
    normalized = re.sub(r"\s+", " ", value.strip())
    if punctuation_tolerance:
        normalized = re.sub(r"[.!?]+$", "", normalized).strip()
    return normalized.casefold() if case_insensitive else normalized


def _validate_review(review: Mapping[str, Any], *, item_id: str) -> None:
    decision = review.get("decision")
    if decision not in REVIEW_DECISIONS:
        raise TextModeSessionError(f"review_decision_invalid:{item_id}")
    if decision == "PENDING":
        if review.get("reviewer_id") is not None:
            raise TextModeSessionError(f"pending_review_has_reviewer:{item_id}")
        if review.get("reviewed_at") is not None:
            raise TextModeSessionError(f"pending_review_has_timestamp:{item_id}")
        return
    if not isinstance(review.get("reviewer_id"), str) or not str(
        review.get("reviewer_id")
    ).strip():
        raise TextModeSessionError(f"reviewer_missing:{item_id}")
    _parse_timezone_timestamp(
        review.get("reviewed_at"), f"review_timestamp_invalid:{item_id}"
    )
    criteria = review.get("criteria")
    if not isinstance(criteria, Mapping):
        raise TextModeSessionError(f"review_criteria_missing:{item_id}")
    expected = {
        "grammar_target_match",
        "meaning_matches_context",
        "complete_response",
    }
    if set(criteria) != expected:
        raise TextModeSessionError(f"review_criteria_keys_invalid:{item_id}")
    if decision == "APPROVE" and not all(
        criteria.get(key) is True for key in expected
    ):
        raise TextModeSessionError(
            f"approved_review_criteria_not_all_true:{item_id}"
        )


def _score_attempt(
    item: Mapping[str, Any],
    attempt: Mapping[str, Any],
) -> tuple[str, float | None, str]:
    contract = item["private_scoring_contract"]
    mode = str(contract["scoring_mode"])
    response = attempt["response"]
    review = attempt["operator_review"]
    _validate_review(review, item_id=str(item["item_id"]))

    if mode == "EXACT_OPTION":
        if not isinstance(response, str):
            raise TextModeSessionError(
                f"response_type_invalid:{item['item_id']}:string"
            )
        if review.get("decision") != "PENDING":
            raise TextModeSessionError(
                f"deterministic_item_review_override_forbidden:{item['item_id']}"
            )
        actual = _normalize_text(response)
        accepted = {
            _normalize_text(value)
            for value in contract.get("accepted_texts", [])
        }
        passed = actual in accepted
        return (
            "AUTO_PASS" if passed else "AUTO_FAIL",
            1.0 if passed else 0.0,
            mode,
        )

    if mode == "EXACT_SEQUENCE":
        if not isinstance(response, list) or not all(
            isinstance(value, str) for value in response
        ):
            raise TextModeSessionError(
                f"response_type_invalid:{item['item_id']}:string_array"
            )
        if review.get("decision") != "PENDING":
            raise TextModeSessionError(
                f"deterministic_item_review_override_forbidden:{item['item_id']}"
            )
        actual = [_normalize_text(value) for value in response]
        expected = [
            _normalize_text(value)
            for value in contract.get("accepted_sequence", [])
        ]
        passed = actual == expected
        return (
            "AUTO_PASS" if passed else "AUTO_FAIL",
            1.0 if passed else 0.0,
            mode,
        )

    if mode == "NORMALIZED_TEXT":
        if not isinstance(response, str):
            raise TextModeSessionError(
                f"response_type_invalid:{item['item_id']}:string"
            )
        if review.get("decision") != "PENDING":
            raise TextModeSessionError(
                f"deterministic_item_review_override_forbidden:{item['item_id']}"
            )
        actual = _normalize_text(
            response,
            case_insensitive=bool(contract.get("case_insensitive", True)),
            punctuation_tolerance=bool(
                contract.get("punctuation_tolerance", True)
            ),
        )
        accepted = {
            _normalize_text(
                value,
                case_insensitive=bool(
                    contract.get("case_insensitive", True)
                ),
                punctuation_tolerance=bool(
                    contract.get("punctuation_tolerance", True)
                ),
            )
            for value in contract.get("accepted_texts", [])
        }
        passed = actual in accepted and bool(actual)
        return (
            "AUTO_PASS" if passed else "AUTO_FAIL",
            1.0 if passed else 0.0,
            mode,
        )

    if mode != "FEATURE_RUBRIC":
        raise TextModeSessionError(
            f"unsupported_scoring_mode:{item['item_id']}:{mode}"
        )
    if not isinstance(response, str) or not response.strip():
        raise TextModeSessionError(
            f"productive_response_empty:{item['item_id']}"
        )
    decision = str(review["decision"])
    if decision == "PENDING":
        return "PENDING_HUMAN_REVIEW", None, mode
    if decision == "DEFER":
        return "HUMAN_DEFER", None, mode
    if decision == "REJECT":
        return "HUMAN_REJECT", 0.0, mode
    return "HUMAN_APPROVE", 1.0, mode


def build_progress_artifacts(
    bank: Mapping[str, Any],
    registry: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    _assert_schema("e4s_a1v1_text_mode_session_bank.schema.json", bank)
    _assert_schema(
        "e4s_a1v1_text_mode_attempt_registry.schema.json", registry
    )
    _require(
        registry.get("session_bank_sha256"),
        sha256_value(bank),
        "attempt_registry_session_hash",
    )
    if not isinstance(registry.get("session_id"), str) or not registry[
        "session_id"
    ].strip():
        raise TextModeSessionError("session_id_invalid")
    if not isinstance(registry.get("learner_ref"), str) or not registry[
        "learner_ref"
    ].strip():
        raise TextModeSessionError("learner_ref_invalid")

    item_by_id = {str(item["item_id"]): item for item in bank["items"]}
    seen_items: set[str] = set()
    entries: list[dict[str, Any]] = []
    for attempt in registry.get("attempts", []):
        item_id = str(attempt.get("item_id") or "")
        item = item_by_id.get(item_id)
        if not item:
            raise TextModeSessionError(f"unknown_attempt_item:{item_id}")
        if item_id in seen_items:
            raise TextModeSessionError(f"duplicate_attempt_item:{item_id}")
        seen_items.add(item_id)
        _parse_timezone_timestamp(
            attempt.get("submitted_at"),
            f"submitted_at_invalid:{item_id}",
        )
        outcome, score, scoring_mode = _score_attempt(item, attempt)
        entries.append(
            {
                "evidence_id": (
                    f"M08_EVIDENCE:{item_id}:"
                    f"{attempt['attempt_sequence']}"
                ),
                "item_id": item_id,
                "shared_item_id": item["shared_item_id"],
                "grammar_unit_id": item["grammar_unit_id"],
                "canonical_egp_row_ids": list(
                    item["canonical_egp_row_ids"]
                ),
                "skill": item["skill"],
                "item_role": item["item_role"],
                "attempt_sequence": attempt["attempt_sequence"],
                "response": deepcopy(attempt["response"]),
                "submitted_at": attempt["submitted_at"],
                "scoring_mode": scoring_mode,
                "outcome": outcome,
                "score": score,
                "operator_review": deepcopy(attempt["operator_review"]),
                "mastery_claimed": False,
            }
        )

    entries.sort(key=lambda row: (row["item_id"], row["attempt_sequence"]))
    outcome_counter = Counter(row["outcome"] for row in entries)
    attempted_units = {row["grammar_unit_id"] for row in entries}
    attempted_rows = {
        row_id
        for row in entries
        for row_id in row["canonical_egp_row_ids"]
    }
    ledger = {
        "task_id": TASK_ID,
        "schema_version": LEDGER_SCHEMA_VERSION,
        "private_local_only": True,
        "session_bank_sha256": sha256_value(bank),
        "attempt_registry_sha256": sha256_value(registry),
        "session_id": registry["session_id"],
        "learner_ref": registry["learner_ref"],
        "attempt_count": len(entries),
        "outcome_counts": {
            outcome: outcome_counter[outcome] for outcome in OUTCOMES
        },
        "attempted_unit_count": len(attempted_units),
        "attempted_row_count": len(attempted_rows),
        "entries": entries,
        "entries_sha256": sha256_value(entries),
        "claim_boundaries": {
            "private_local_only": True,
            "canonical_authority_write": False,
            "public_delivery": False,
            "persistent_learner_state_write": False,
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
            "audio_evidence_used": False,
        },
    }
    _assert_schema(
        "e4s_a1v1_text_mode_progress_ledger.schema.json", ledger
    )

    status = (
        ZERO_STATUS
        if not entries
        else COMPLETE_STATUS
        if len(entries) == 192
        else PARTIAL_STATUS
    )
    skill_attempt_counts = Counter(row["skill"] for row in entries)
    role_attempt_counts = Counter(row["item_role"] for row in entries)
    mode_counts = Counter(row["scoring_mode"] for row in entries)
    report = {
        "task_id": TASK_ID,
        "epic_id": EPIC_ID,
        "schema_version": SAFE_REPORT_SCHEMA_VERSION,
        "report_mode": "TEXT_MODE_SESSION_PROGRESS",
        "source_hashes": dict(bank["source_hashes"]),
        "session_bank_sha256": sha256_value(bank),
        "attempt_registry_sha256": sha256_value(registry),
        "progress_ledger_sha256": sha256_value(ledger),
        "available_item_count": 192,
        "attempt_count": len(entries),
        "unattempted_item_count": 192 - len(entries),
        "skill_attempt_counts": {
            skill: skill_attempt_counts[skill] for skill in SKILLS
        },
        "role_attempt_counts": {
            role: role_attempt_counts[role]
            for role in ("practice", "assessment")
        },
        "scoring_mode_counts": dict(sorted(mode_counts.items())),
        "outcome_counts": dict(ledger["outcome_counts"]),
        "attempted_unit_count": len(attempted_units),
        "attempted_row_count": len(attempted_rows),
        "pending_human_review_count": outcome_counter[
            "PENDING_HUMAN_REVIEW"
        ],
        "actual_learner_evidence_count": len(entries),
        "validation_status": status,
        "claim_boundaries": {
            "metadata_only_report": True,
            "private_responses_included": False,
            "audio_evidence_used": False,
            "speaking_audio_evidence_state": "DEFERRED_BY_OPERATOR",
            "canonical_authority_writes": 0,
            "public_delivery_count": 0,
            "persistent_learner_state_writes": 0,
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
            "production_runtime_enabled": False,
            "a2_a2plus_in_scope": False,
        },
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
        "errors": [],
    }
    _safe_scan(
        report,
        name="progress_safe_report",
        forbidden=SAFE_REPORT_FORBIDDEN_KEYS,
    )

    query_items = [
        {
            "item_id": item["item_id"],
            "shared_item_id": item["shared_item_id"],
            "grammar_unit_id": item["grammar_unit_id"],
            "canonical_egp_row_ids": list(
                item["canonical_egp_row_ids"]
            ),
            "internal_stage": item["internal_stage"],
            "skill": item["skill"],
            "item_role": item["item_role"],
            "evidence_dimension": item["evidence_dimension"],
            "task_type": item["task_type"],
            "scoring_mode": item["private_scoring_contract"][
                "scoring_mode"
            ],
            "attempted": item["item_id"] in seen_items,
            "outcome": next(
                (
                    entry["outcome"]
                    for entry in entries
                    if entry["item_id"] == item["item_id"]
                ),
                None,
            ),
        }
        for item in bank["items"]
    ]
    query_index = {
        "task_id": TASK_ID,
        "schema_version": "e4s.a1v1.text_mode_progress_query.v1",
        "item_count": len(query_items),
        "attempt_count": len(entries),
        "items": query_items,
    }
    _safe_scan(
        query_index,
        name="progress_query_index",
        forbidden=SAFE_REPORT_FORBIDDEN_KEYS,
    )
    return ledger, report, query_index


def _local_session_html() -> str:
    return """<!doctype html>
<html lang="en"><meta charset="utf-8"><title>A1/A1+ Text Session</title>
<body><h1>A1/A1+ Local Text Session</h1>
<p>Local-only. No network submission. No audio is used.</p>
<label>Learner ref <input id="learner" value="learner-local-001"></label>
<label>Session ID <input id="session" value="local-session-001"></label>
<select id="item"></select><div id="meta"></div><h2 id="prompt"></h2>
<div id="context"></div><div id="response"></div>
<button id="save">Save attempt</button><button id="export">Download attempt registry</button>
<pre id="status"></pre><script>
let payload; const attempts=new Map();
async function load(){payload=await (await fetch('./payload.json')).json();const s=document.querySelector('#item');payload.items.forEach((x,i)=>{const o=document.createElement('option');o.value=i;o.textContent=`${i+1}. ${x.skill} | ${x.item_role} | ${x.grammar_unit_id}`;s.appendChild(o)});s.onchange=render;render();}
function current(){return payload.items[Number(document.querySelector('#item').value)]}
function render(){const x=current();document.querySelector('#meta').textContent=`${x.internal_stage} | ${x.evidence_dimension} | ${x.task_type}`;document.querySelector('#prompt').textContent=x.prompt;document.querySelector('#context').textContent=x.context?JSON.stringify(x.context):'';const r=document.querySelector('#response');r.innerHTML='';if(x.response_mode==='select_one'){x.options.forEach(v=>{const l=document.createElement('label');const i=document.createElement('input');i.type='radio';i.name='response';i.value=v;l.append(i,document.createTextNode(v));r.append(l,document.createElement('br'))})}else if(x.response_mode==='ordered_tokens'||x.response_mode==='ordered_morphemes'){const source=x.supplied_tokens||x.supplied_morphemes||[];const p=document.createElement('p');p.textContent='Supplied: '+source.join(' | ');const t=document.createElement('textarea');t.id='text-response';t.placeholder='Enter the ordered parts separated by |';r.append(p,t)}else{const t=document.createElement('textarea');t.id='text-response';t.placeholder='Type your response';r.append(t)}}
function readResponse(){const x=current();if(x.response_mode==='select_one'){const i=document.querySelector('input[name=response]:checked');return i?i.value:''}const v=(document.querySelector('#text-response')||{}).value||'';return (x.response_mode==='ordered_tokens'||x.response_mode==='ordered_morphemes')?v.split('|').map(s=>s.trim()).filter(Boolean):v}
function emptyReview(){return {decision:'PENDING',reviewer_id:null,reviewed_at:null,criteria:{grammar_target_match:null,meaning_matches_context:null,complete_response:null},notes:null}}
function save(){const x=current();const row={item_id:x.item_id,attempt_sequence:1,response:readResponse(),submitted_at:new Date().toISOString(),operator_review:emptyReview()};attempts.set(x.item_id,row);localStorage.setItem('e4s-a1v1-m08-attempts',JSON.stringify([...attempts.values()]));document.querySelector('#status').textContent=`Saved ${attempts.size} attempt(s).`;}
function exportRegistry(){const value={task_id:payload.task_id,schema_version:'e4s.a1v1.text_mode_attempt_registry.v1',private_local_only:true,session_bank_sha256:payload.session_bank_sha256,session_id:document.querySelector('#session').value,learner_ref:document.querySelector('#learner').value,attempts:[...attempts.values()]};const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));a.download='m08_text_mode_attempt_registry.private.json';a.click();}
document.querySelector('#save').onclick=save;document.querySelector('#export').onclick=exportRegistry;load();
</script></body></html>"""


def prepare_artifacts(
    output_root: Path,
    m07_receipt_path: Path = M07_RECEIPT_PATH,
) -> dict[str, Any]:
    root = _safe_output_root(output_root)
    m07 = read_json(m07_receipt_path)
    text_package, text_report = build_text_package()
    _require(text_report.get("validation_status"), "PASS", "text_package_status")
    shared = build_shared_contract()
    bank = build_session_bank(m07, text_package, shared)
    payload = build_learner_safe_payload(bank)
    registry = empty_attempt_registry(bank)
    ledger, report, query = build_progress_artifacts(bank, registry)

    write_json_atomic(root / "text_mode_session_bank.private.json", bank)
    write_json_atomic(root / "text_mode_learner_safe_payload.json", payload)
    write_json_atomic(root / "text_mode_attempt_registry.template.json", registry)
    write_json_atomic(root / "text_mode_attempt_registry.private.json", registry)
    write_json_atomic(root / "text_mode_progress_ledger.private.json", ledger)
    write_json_atomic(root / "text_mode_progress_safe_report.json", report)
    write_json_atomic(root / "text_mode_progress_query_index.json", query)
    player = root / "local_session"
    player.mkdir(parents=True, exist_ok=True)
    (player / "index.html").write_text(
        _local_session_html(), encoding="utf-8"
    )
    write_json_atomic(player / "payload.json", payload)
    return {
        "bank": bank,
        "payload": payload,
        "registry": registry,
        "ledger": ledger,
        "safe_report": report,
        "query": query,
    }


def materialize_attempts(
    output_root: Path,
    attempt_registry_path: Path,
) -> dict[str, Any]:
    root = _safe_output_root(output_root)
    bank = read_json(root / "text_mode_session_bank.private.json")
    registry = read_json(attempt_registry_path)
    ledger, report, query = build_progress_artifacts(bank, registry)
    write_json_atomic(root / "text_mode_attempt_registry.private.json", registry)
    write_json_atomic(root / "text_mode_progress_ledger.private.json", ledger)
    write_json_atomic(root / "text_mode_progress_safe_report.json", report)
    write_json_atomic(root / "text_mode_progress_query_index.json", query)
    return {
        "ledger": ledger,
        "safe_report": report,
        "query": query,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    prepare.add_argument("--m07-receipt", type=Path, default=M07_RECEIPT_PATH)
    materialize = sub.add_parser("materialize")
    materialize.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    materialize.add_argument("--attempt-registry", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare_artifacts(args.output_root, args.m07_receipt)
        else:
            result = materialize_attempts(
                args.output_root, args.attempt_registry
            )
        print(
            json.dumps(
                {
                    "available_items": 192,
                    "attempt_count": result["safe_report"]["attempt_count"],
                    "validation_status": result["safe_report"][
                        "validation_status"
                    ],
                    "next_short_step": NEXT_SHORT_STEP,
                },
                sort_keys=True,
            )
        )
        return 0
    except (TextModeSessionError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
