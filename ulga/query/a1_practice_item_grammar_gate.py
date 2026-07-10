#!/usr/bin/env python3
"""Read-only A1 grammar gate for ReadingV1 PracticeItem consumers.

The gate consumes canonical ``grammar_id + text`` targets declared by a
PracticeItem and delegates sentence matching to the unified A1 dispatcher.
It is fail-closed, does not mutate the PracticeItem, does not write learner
state, and is not a production runtime validator.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.query.a1_canonical_validator_dispatcher import validate as dispatch_validate


TASK_ID = "R7-M104E23A_A1PracticeItemGrammarGateIntegration"
GATE_VERSION = "a1_practice_item_grammar_gate.v1"
VALIDATOR_MODE = "OFFLINE_STATIC_PROTOTYPE"

ERR_GRAMMAR_FOCUS_MISSING = "A1_PI_GRAMMAR_GATE_ERR_GRAMMAR_FOCUS_MISSING"
ERR_GRAMMAR_FOCUS_DUPLICATE = "A1_PI_GRAMMAR_GATE_ERR_GRAMMAR_FOCUS_DUPLICATE"
ERR_GATE_MISSING = "A1_PI_GRAMMAR_GATE_ERR_GATE_MISSING"
ERR_GATE_VERSION = "A1_PI_GRAMMAR_GATE_ERR_GATE_VERSION"
ERR_TARGETS_MISSING = "A1_PI_GRAMMAR_GATE_ERR_TARGETS_MISSING"
ERR_TARGET_INVALID = "A1_PI_GRAMMAR_GATE_ERR_TARGET_INVALID"
ERR_TARGET_DUPLICATE = "A1_PI_GRAMMAR_GATE_ERR_TARGET_DUPLICATE"
ERR_FOCUS_TARGET_MISMATCH = "A1_PI_GRAMMAR_GATE_ERR_FOCUS_TARGET_MISMATCH"
ERR_UNKNOWN_GRAMMAR_ID = "A1_PI_GRAMMAR_GATE_ERR_UNKNOWN_GRAMMAR_ID"
ERR_NO_MATCH = "A1_PI_GRAMMAR_GATE_ERR_NO_MATCH"
ERR_UNSAFE_BOUNDARY = "A1_PI_GRAMMAR_GATE_ERR_UNSAFE_BOUNDARY"


def _error(code: str, message: str, path: str) -> dict[str, str]:
    return {"code": code, "message": message, "path": path}


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [entry.strip() for entry in value if isinstance(entry, str) and entry.strip()]


def validate_practice_item(item: Mapping[str, Any], index: int | None = None) -> dict[str, Any]:
    """Validate one PracticeItem grammar gate without mutating ``item``."""

    errors: list[dict[str, str]] = []
    item_id = item.get("item_id") or (f"index:{index}" if index is not None else None)

    content_binding = item.get("content_binding")
    grammar_focus = _normalize_string_list(
        content_binding.get("grammar_focus") if isinstance(content_binding, Mapping) else None
    )
    if not grammar_focus:
        errors.append(
            _error(
                ERR_GRAMMAR_FOCUS_MISSING,
                "content_binding.grammar_focus must contain at least one canonical A1 grammar ID.",
                "content_binding.grammar_focus",
            )
        )
    if len(grammar_focus) != len(set(grammar_focus)):
        errors.append(
            _error(
                ERR_GRAMMAR_FOCUS_DUPLICATE,
                "content_binding.grammar_focus must not contain duplicate grammar IDs.",
                "content_binding.grammar_focus",
            )
        )

    gate = item.get("grammar_gate")
    if not isinstance(gate, Mapping):
        errors.append(
            _error(
                ERR_GATE_MISSING,
                "PracticeItem grammar_gate object is required.",
                "grammar_gate",
            )
        )
        gate = {}

    if gate.get("gate_version") != GATE_VERSION:
        errors.append(
            _error(
                ERR_GATE_VERSION,
                f"grammar_gate.gate_version must be {GATE_VERSION!r}.",
                "grammar_gate.gate_version",
            )
        )

    if gate.get("require_all_focus_matches") is not True:
        errors.append(
            _error(
                ERR_UNSAFE_BOUNDARY,
                "grammar_gate.require_all_focus_matches must be true.",
                "grammar_gate.require_all_focus_matches",
            )
        )
    if gate.get("validator_mode") != VALIDATOR_MODE:
        errors.append(
            _error(
                ERR_UNSAFE_BOUNDARY,
                f"grammar_gate.validator_mode must be {VALIDATOR_MODE!r}.",
                "grammar_gate.validator_mode",
            )
        )
    if gate.get("production_runtime_validator") is not False:
        errors.append(
            _error(
                ERR_UNSAFE_BOUNDARY,
                "grammar_gate.production_runtime_validator must be false.",
                "grammar_gate.production_runtime_validator",
            )
        )
    if gate.get("learner_state_write") is not False:
        errors.append(
            _error(
                ERR_UNSAFE_BOUNDARY,
                "grammar_gate.learner_state_write must be false.",
                "grammar_gate.learner_state_write",
            )
        )

    targets = gate.get("validation_targets")
    if not isinstance(targets, list) or not targets:
        errors.append(
            _error(
                ERR_TARGETS_MISSING,
                "grammar_gate.validation_targets must contain at least one grammar_id + text target.",
                "grammar_gate.validation_targets",
            )
        )
        targets = []

    normalized_targets: list[dict[str, str]] = []
    for target_index, target in enumerate(targets):
        path = f"grammar_gate.validation_targets[{target_index}]"
        if not isinstance(target, Mapping):
            errors.append(_error(ERR_TARGET_INVALID, "Each validation target must be an object.", path))
            continue
        grammar_id = target.get("grammar_id")
        text = target.get("text")
        target_role = target.get("target_role", "practice_item_text")
        if not isinstance(grammar_id, str) or not grammar_id.strip():
            errors.append(_error(ERR_TARGET_INVALID, "validation target grammar_id is required.", f"{path}.grammar_id"))
            continue
        if not isinstance(text, str) or not text.strip():
            errors.append(_error(ERR_TARGET_INVALID, "validation target text is required.", f"{path}.text"))
            continue
        if not isinstance(target_role, str) or not target_role.strip():
            errors.append(_error(ERR_TARGET_INVALID, "validation target target_role must be a non-empty string.", f"{path}.target_role"))
            continue
        normalized_targets.append(
            {
                "grammar_id": grammar_id.strip(),
                "text": text.strip(),
                "target_role": target_role.strip(),
            }
        )

    target_ids = [target["grammar_id"] for target in normalized_targets]
    if len(target_ids) != len(set(target_ids)):
        errors.append(
            _error(
                ERR_TARGET_DUPLICATE,
                "grammar_gate.validation_targets must not repeat a grammar_id.",
                "grammar_gate.validation_targets",
            )
        )

    if set(grammar_focus) != set(target_ids):
        errors.append(
            _error(
                ERR_FOCUS_TARGET_MISMATCH,
                "The canonical grammar_focus set must equal the validation target grammar_id set.",
                "grammar_gate.validation_targets",
            )
        )

    dispatcher_results: list[dict[str, Any]] = []
    for target in normalized_targets:
        result = dispatch_validate(target["grammar_id"], target["text"])
        dispatcher_result = dict(result)
        dispatcher_result["target_role"] = target["target_role"]
        dispatcher_results.append(dispatcher_result)
        if result.get("dispatch_status") != "VALIDATOR_EXECUTED":
            errors.append(
                _error(
                    ERR_UNKNOWN_GRAMMAR_ID,
                    f"Unknown canonical A1 grammar ID: {target['grammar_id']!r}.",
                    "grammar_gate.validation_targets",
                )
            )
        elif result.get("match") is not True:
            errors.append(
                _error(
                    ERR_NO_MATCH,
                    f"Grammar target did not match its declared canonical grammar: {target['grammar_id']!r}.",
                    "grammar_gate.validation_targets",
                )
            )

    gate_status = "PASS" if not errors else "FAIL"
    return {
        "task_id": TASK_ID,
        "gate_version": GATE_VERSION,
        "item_id": item_id,
        "gate_status": gate_status,
        "practice_item_gate_pass": gate_status == "PASS",
        "grammar_focus_count": len(grammar_focus),
        "validation_target_count": len(normalized_targets),
        "matched_target_count": sum(
            result.get("dispatch_status") == "VALIDATOR_EXECUTED" and result.get("match") is True
            for result in dispatcher_results
        ),
        "dispatcher_results": dispatcher_results,
        "errors": errors,
        "validator_mode": VALIDATOR_MODE,
        "production_runtime_validator": False,
        "learner_state_write": False,
        "input_mutated": False,
    }


def validate_practice_items(items: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Validate a sequence of PracticeItems and return deterministic accounting."""

    item_reports = [validate_practice_item(item, index) for index, item in enumerate(items)]
    pass_count = sum(report["practice_item_gate_pass"] for report in item_reports)
    return {
        "task_id": TASK_ID,
        "gate_version": GATE_VERSION,
        "item_count": len(item_reports),
        "pass_count": pass_count,
        "fail_count": len(item_reports) - pass_count,
        "all_items_pass": pass_count == len(item_reports),
        "item_reports": item_reports,
        "validator_mode": VALIDATOR_MODE,
        "production_runtime_validator": False,
        "learner_state_write": False,
    }


def _load_items(path: Path) -> list[Mapping[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, Mapping) and isinstance(payload.get("items"), list):
        return payload["items"]
    if isinstance(payload, Mapping):
        return [payload]
    raise ValueError("Input JSON must be one PracticeItem or a PracticeBank object with items.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate A1 PracticeItem grammar gates.")
    parser.add_argument("input_json", type=Path)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()

    report = validate_practice_items(_load_items(args.input_json))
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0 if report["all_items_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
