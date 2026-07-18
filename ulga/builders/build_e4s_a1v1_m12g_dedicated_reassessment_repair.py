#!/usr/bin/env python3
"""Repair insufficient M12G reassessment coverage with private derived tasks.

This module does not loosen the M12G assessment-validity gate. It derives an
ordered-token reassessment only when an Authority-reviewed structured gap item
contains one exact private answer and a visible gap template that can be
reconstructed into a complete target sequence. Duplicate reconstructed targets
remain fail-closed.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterator, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_e4s_a1v1_m12g_learner_contract_assessment_validity_fullfix as fullfix  # noqa: E402
from ulga.builders import build_e4s_a1v1_m12g_remediation_reassessment_execution as base  # noqa: E402

TASK_ID = "E4S-A1V1-M12G_DedicatedReassessmentRepair"
SCHEMA_VERSION = "e4s.a1v1.m12g.dedicated_reassessment_repair.v1"
STATUS = "PASS_M12G_DEDICATED_REASSESSMENT_REPAIR_READY"
REPORT_FILENAME = "m12g_dedicated_reassessment_repair.safe.json"
DERIVED_SUFFIX = "__M12G_DEDICATED_ORDER"
TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?|[^\w\s]", re.UNICODE)

_REPAIRS: list[dict[str, Any]] = []


class DedicatedRepairError(fullfix.AssessmentValidityError):
    """Fail-closed dedicated reassessment derivation error."""


def _one_text(value: Any, code: str) -> str:
    if not isinstance(value, list) or len(value) != 1:
        raise DedicatedRepairError(code)
    text = value[0]
    if not isinstance(text, str) or not text.strip():
        raise DedicatedRepairError(code)
    return text.strip()


def _reconstruct_sequence(item: Mapping[str, Any]) -> list[str]:
    item_id = str(item.get("item_id") or "")
    if str(item.get("task_type") or "") != "structured_gap_fill":
        raise DedicatedRepairError(f"repair_task_type_unsupported:{item_id}")

    learner = item.get("learner_contract")
    scoring = item.get("private_scoring_contract")
    if not isinstance(learner, Mapping) or not isinstance(scoring, Mapping):
        raise DedicatedRepairError(f"repair_contract_missing:{item_id}")

    accepted = _one_text(scoring.get("accepted_texts"), f"repair_exact_answer_required:{item_id}")
    gap_tokens = learner.get("gap_display_tokens")
    if not isinstance(gap_tokens, list) or not gap_tokens or not all(
        isinstance(token, str) and token.strip() for token in gap_tokens
    ):
        raise DedicatedRepairError(f"repair_gap_tokens_missing:{item_id}")

    blank_count = 0
    rendered: list[str] = []
    for token in gap_tokens:
        matches = list(fullfix.BLANK_RE.finditer(token))
        blank_count += len(matches)
        rendered.append(fullfix.BLANK_RE.sub(accepted, token))
    if blank_count != 1:
        raise DedicatedRepairError(f"repair_exactly_one_gap_required:{item_id}")

    sequence = TOKEN_RE.findall(" ".join(rendered))
    if len(sequence) < 2:
        raise DedicatedRepairError(f"repair_sequence_too_short:{item_id}")
    if not any(character.isalpha() for token in sequence for character in token):
        raise DedicatedRepairError(f"repair_sequence_has_no_language:{item_id}")
    return sequence


def _target_fingerprint(item: Mapping[str, Any]) -> str | None:
    scoring = item.get("private_scoring_contract")
    if not isinstance(scoring, Mapping):
        return None
    sequence = scoring.get("accepted_sequence")
    if isinstance(sequence, list) and sequence and all(isinstance(token, str) for token in sequence):
        return base.digest([str(token).casefold() for token in sequence])
    try:
        reconstructed = _reconstruct_sequence(item)
    except DedicatedRepairError:
        return None
    return base.digest([token.casefold() for token in reconstructed])


def _scramble(sequence: list[str], source_item_id: str, used_visible: set[str]) -> list[str]:
    candidates: list[list[str]] = []
    if len(sequence) > 1:
        candidates.append(list(reversed(sequence)))
        for offset in range(1, len(sequence)):
            candidates.append(sequence[offset:] + sequence[:offset])
        swapped = list(sequence)
        swapped[0], swapped[1] = swapped[1], swapped[0]
        candidates.append(swapped)

    unique: dict[str, list[str]] = {}
    for candidate in candidates:
        if candidate == sequence:
            continue
        fingerprint = base.digest(candidate)
        if fingerprint not in used_visible:
            unique[fingerprint] = candidate
    if not unique:
        raise DedicatedRepairError(f"repair_distinct_visible_order_unavailable:{source_item_id}")

    ordered = sorted(
        unique.items(),
        key=lambda pair: base.digest([source_item_id, pair[0]]),
    )
    fingerprint, selected = ordered[0]
    used_visible.add(fingerprint)
    return selected


def derive_ordered_repair(
    item: Mapping[str, Any],
    *,
    used_targets: set[str],
    used_visible: set[str],
) -> dict[str, Any]:
    source_item_id = str(item.get("item_id") or "")
    target_sequence = _reconstruct_sequence(item)
    target_fingerprint = base.digest([token.casefold() for token in target_sequence])
    if target_fingerprint in used_targets:
        raise DedicatedRepairError(f"repair_duplicate_target_sequence:{source_item_id}")

    supplied_tokens = _scramble(target_sequence, source_item_id, used_visible)
    repaired = deepcopy(dict(item))
    repaired["item_id"] = source_item_id + DERIVED_SUFFIX
    repaired["task_type"] = "ordering"
    repaired["learner_contract"] = {
        "prompt": "Put the supplied tokens in the correct order to make the complete target sentence or phrase.",
        "response_mode": "ordered_tokens",
        "supplied_tokens": supplied_tokens,
        "assessment_derivation": {
            "type": "FULL_TARGET_SEQUENCE_FROM_AUTHORITY_GAP",
            "source_item_id": source_item_id,
            "private_local_only": True,
        },
    }
    repaired["private_scoring_contract"] = {
        "scoring_mode": "EXACT_SEQUENCE",
        "response_type": "string_array",
        "accepted_sequence": target_sequence,
        "case_insensitive": True,
        "punctuation_tolerance": True,
        "human_review_fallback": False,
    }
    repaired["m12g_dedicated_reassessment_derivation"] = {
        "source_item_id": source_item_id,
        "source_item_sha256": base.digest(item),
        "derivation_type": "FULL_TARGET_SEQUENCE_FROM_AUTHORITY_GAP",
        "target_sequence_sha256": target_fingerprint,
        "private_local_only": True,
        "canonical_authority_modified": False,
    }

    learner, _ = fullfix.learner_item(repaired)
    visible_fingerprint = fullfix._contract_fingerprint(learner)
    if visible_fingerprint in used_visible:
        raise DedicatedRepairError(f"repair_duplicate_learner_stimulus:{source_item_id}")
    used_visible.add(visible_fingerprint)
    used_targets.add(target_fingerprint)
    return repaired


def choose_source_items(
    source_item: Mapping[str, Any],
    bank_items: Mapping[str, Mapping[str, Any]],
    required_count: int,
) -> list[dict[str, Any]]:
    item_id = str(source_item.get("item_id") or "")
    grammar_unit = str(source_item.get("grammar_unit_id") or "")
    skill = str(source_item.get("skill") or "").casefold()
    candidates = [
        row
        for row in bank_items.values()
        if str(row.get("grammar_unit_id") or "") == grammar_unit
        and str(row.get("skill") or "").casefold() == skill
    ]
    candidates.sort(key=lambda row: (str(row.get("item_id")) == item_id, str(row.get("item_id"))))

    selected: list[dict[str, Any]] = []
    rejected: dict[str, str] = {}
    used_visible: set[str] = set()
    used_targets: set[str] = set()

    for row in candidates:
        candidate_id = str(row.get("item_id") or "")
        try:
            learner, _ = fullfix.learner_item(row)
        except fullfix.AssessmentValidityError as exc:
            rejected[candidate_id] = str(exc).split(":", 1)[0]
            continue
        visible_fingerprint = fullfix._contract_fingerprint(learner)
        if visible_fingerprint in used_visible:
            rejected[candidate_id] = "duplicate_learner_stimulus"
            continue
        used_visible.add(visible_fingerprint)
        target_fingerprint = _target_fingerprint(row)
        if target_fingerprint:
            used_targets.add(target_fingerprint)
        selected.append(dict(row))

    if len(selected) < required_count:
        for row in candidates:
            candidate_id = str(row.get("item_id") or "")
            if candidate_id not in rejected:
                continue
            try:
                repaired = derive_ordered_repair(
                    row,
                    used_targets=used_targets,
                    used_visible=used_visible,
                )
            except DedicatedRepairError as exc:
                rejected[candidate_id] = str(exc).split(":", 1)[0]
                continue
            selected.append(repaired)
            _REPAIRS.append({
                "source_item_id": candidate_id,
                "derived_item_id": str(repaired["item_id"]),
                "grammar_unit_id": grammar_unit,
                "skill": skill,
                "derivation_type": "FULL_TARGET_SEQUENCE_FROM_AUTHORITY_GAP",
                "source_item_sha256": base.digest(row),
                "target_sequence_sha256": repaired["m12g_dedicated_reassessment_derivation"]["target_sequence_sha256"],
            })
            if len(selected) >= required_count:
                break

    if len(selected) < required_count:
        detail = ",".join(f"{key}={value}" for key, value in sorted(rejected.items()))
        raise DedicatedRepairError(
            f"dedicated_reassessment_repair_insufficient:{item_id}:"
            f"required={required_count}:valid_or_repaired={len(selected)}:rejected={detail}"
        )

    return selected[:required_count]


@contextmanager
def patched_selector() -> Iterator[None]:
    original = fullfix.choose_source_items
    fullfix.choose_source_items = choose_source_items
    try:
        yield
    finally:
        fullfix.choose_source_items = original


def prepare(**kwargs: Any) -> dict[str, Any]:
    _REPAIRS.clear()
    with patched_selector():
        result = fullfix.prepare(**kwargs)

    if not _REPAIRS:
        raise DedicatedRepairError("dedicated_reassessment_repair_not_required")

    package = base.read_json(result["package_path"], "package")
    tasks = package.get("tasks")
    if not isinstance(tasks, list):
        raise DedicatedRepairError("prepared_tasks_invalid")
    derived_ids = {row["derived_item_id"] for row in _REPAIRS}
    package_derived_ids = {
        str(task.get("source_item_id"))
        for task in tasks
        if str(task.get("source_item_id") or "").endswith(DERIVED_SUFFIX)
    }
    if package_derived_ids != derived_ids:
        raise DedicatedRepairError("prepared_repair_partition_invalid")

    report = dict(result["report"])
    report.update({
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": STATUS,
        "dedicated_repair_count": len(_REPAIRS),
        "dedicated_repairs": sorted(_REPAIRS, key=lambda row: row["derived_item_id"]),
        "derivation_policy": "EXACT_PRIVATE_ANSWER_PLUS_VISIBLE_SINGLE_GAP_TO_ORDERED_SEQUENCE",
        "duplicate_target_sequences_allowed": False,
        "canonical_authority_modified": False,
        "generated_learner_answers": False,
        "legacy_incomplete_package_reusable": False,
    })
    report_path = Path(kwargs["target_root"]) / REPORT_FILENAME
    base.write_private(report_path, report)
    result["report"] = report
    result["report_path"] = report_path
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_cmd = commands.add_parser("prepare")
    for name in (
        "source-bank",
        "base-consumer",
        "base-graph",
        "source-database",
        "resolved-root",
        "m12e1-root",
        "output-root",
    ):
        prepare_cmd.add_argument(f"--{name}", type=Path, required=True)
    prepare_cmd.add_argument("--learner-id", required=True)
    prepare_cmd.add_argument("--display-label", required=True)
    args = parser.parse_args(argv)

    try:
        result = prepare(
            source_bank_path=args.source_bank,
            base_consumer_path=args.base_consumer,
            base_graph_path=args.base_graph,
            source_database_path=args.source_database,
            resolved_root=args.resolved_root,
            m12e1_root=args.m12e1_root,
            learner_id=args.learner_id,
            display_label=args.display_label,
            target_root=args.output_root,
        )
        report = result["report"]
        print(json.dumps({
            "validation_status": report["validation_status"],
            "pending_node_count": report["pending_node_count"],
            "required_attempt_count": report["required_attempt_count"],
            "learner_contract_valid_count": report["learner_contract_valid_count"],
            "dedicated_repair_count": report["dedicated_repair_count"],
            "a2_lock_state": report["a2_lock_state"],
            "stop_reason": report["stop_reason"],
            "html": str(result["html_path"]),
            "package": str(result["package_path"]),
            "database": str(result["database_path"]),
            "report": str(result["report_path"]),
        }, ensure_ascii=False, sort_keys=True))
        return 0
    except (
        DedicatedRepairError,
        fullfix.AssessmentValidityError,
        base.ReassessmentError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
