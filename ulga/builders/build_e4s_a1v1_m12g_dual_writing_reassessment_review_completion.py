#!/usr/bin/env python3
"""Complete both deficient M12G A1 writing cohorts through private review.

The real M12G reassessment requires four learner-valid attempts for each of two
pending writing nodes. The adverb-phrase cohort and adjective-phrase cohort each
contain only two unique learner-valid source items. This builder prepares two
additional adjective-phrase candidates for explicit private developer review,
then combines that review with the already-reviewed adverb candidates and invokes
the unchanged fail-closed M12G pipeline.

No original M08 source bank, canonical Authority, frozen graph, original M12F
SQLite database, or A2 lock is modified.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_e4s_a1v1_m08_text_mode_learner_session as m08  # noqa: E402
from ulga.builders import build_e4s_a1v1_m12g_dedicated_writing_reassessment_authority_review as core  # noqa: E402
from ulga.builders import build_e4s_a1v1_m12g_remediation_reassessment_execution as base  # noqa: E402
from ulga.builders import build_e4s_a1v1_m12g_writing_reassessment_review_runtime as runtime  # noqa: E402

TASK_ID = core.TASK_ID
QUEUE_SCHEMA = core.QUEUE_SCHEMA
DECISION_SCHEMA = core.DECISION_SCHEMA
STATUS_PENDING = core.STATUS_PENDING
STATUS_READY = core.STATUS_READY
REVIEW_CRITERIA = core.REVIEW_CRITERIA

ADVERB_GRAMMAR_UNIT = "GRAMMAR_ADVERB_PHRASES_A1"
ADJECTIVE_GRAMMAR_UNIT = "GRAMMAR_ADJECTIVE_PHRASES_A1"
ADJECTIVE_TARGET_DEFAULT = "GRAMMAR_ADJECTIVE_PHRASES_A1__TFX_P04"

ADJECTIVE_QUEUE_FILENAME = (
    "m12g_adjective_writing_reassessment_review_queue.private.json"
)
ADJECTIVE_DECISION_FILENAME = (
    "m12g_adjective_writing_reassessment_decisions.private.json"
)
ADJECTIVE_HTML_FILENAME = (
    "m12g_adjective_writing_reassessment_review.private.html"
)
ADJECTIVE_REPORT_FILENAME = (
    "m12g_adjective_writing_reassessment_authority_review.safe.json"
)
DUAL_REPORT_FILENAME = "m12g_dual_writing_reassessment_authority_review.safe.json"

ADJECTIVE_CANDIDATE_SPECS = (
    {
        "suffix": "M12G_WRA01",
        "prompt": (
            "Write one complete A1 sentence for the situation. "
            "Use an adjective phrase to describe how the girl feels."
        ),
        "context": {
            "situation": "A girl gets a birthday card and smiles.",
            "required_target": "Use very plus an adjective to describe her feeling.",
        },
        "model_text": "The girl is very happy.",
    },
    {
        "suffix": "M12G_WRA02",
        "prompt": (
            "Write one complete A1 sentence for the situation. "
            "Use an adjective phrase to describe how the boy feels."
        ),
        "context": {
            "situation": "A boy finishes a long walk and wants to sit down.",
            "required_target": "Use very plus an adjective to describe his feeling.",
        },
        "model_text": "The boy is very tired.",
    },
)


class DualWritingReviewError(core.WritingReviewError):
    """Fail-closed dual-cohort writing review error."""


def _write(path: Path, value: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)
    os.chmod(path, 0o600)
    return path


def _shortage_diagnosis(
    bank_items: Mapping[str, Mapping[str, Any]],
    target_item_id: str,
    *,
    expected_grammar_unit: str,
) -> dict[str, Any]:
    target = bank_items.get(target_item_id)
    if not target:
        raise DualWritingReviewError(f"target_item_missing:{target_item_id}")
    grammar_unit = str(target.get("grammar_unit_id") or "")
    skill = str(target.get("skill") or "").casefold()
    if grammar_unit != expected_grammar_unit:
        raise DualWritingReviewError(
            f"target_grammar_unit_invalid:{grammar_unit}:{expected_grammar_unit}"
        )
    if skill != "writing":
        raise DualWritingReviewError(f"target_skill_not_writing:{skill}")

    cohort = [
        row
        for row in bank_items.values()
        if str(row.get("grammar_unit_id") or "") == grammar_unit
        and str(row.get("skill") or "").casefold() == skill
    ]
    cohort.sort(key=lambda row: str(row.get("item_id") or ""))
    valid: list[dict[str, Any]] = []
    rejected: dict[str, str] = {}
    fingerprints: set[str] = set()
    for row in cohort:
        item_id = str(row.get("item_id") or "")
        try:
            learner, _ = core.fullfix.learner_item(row)
        except core.fullfix.AssessmentValidityError as exc:
            rejected[item_id] = str(exc).split(":", 1)[0]
            continue
        fingerprint = core.fullfix._contract_fingerprint(learner)
        if fingerprint in fingerprints:
            rejected[item_id] = "duplicate_learner_stimulus"
            continue
        fingerprints.add(fingerprint)
        valid.append(dict(row))

    reasons = set(rejected.values())
    required_reasons = {
        "duplicate_learner_stimulus",
        "gap_disambiguating_stimulus_missing",
    }
    if len(cohort) != 4 or len(valid) != 2 or not required_reasons.issubset(reasons):
        raise DualWritingReviewError(
            "writing_shortage_shape_changed:"
            f"unit={grammar_unit}:cohort={len(cohort)}:valid={len(valid)}:"
            f"reasons={','.join(sorted(reasons))}"
        )

    rubric_templates = [
        row
        for row in cohort
        if isinstance(row.get("private_scoring_contract"), Mapping)
        and row["private_scoring_contract"].get("scoring_mode") == "FEATURE_RUBRIC"
        and isinstance(row["private_scoring_contract"].get("rubric"), Mapping)
        and row["private_scoring_contract"]["rubric"]
    ]
    if not rubric_templates:
        raise DualWritingReviewError("writing_feature_rubric_template_missing")
    rubric_templates.sort(key=lambda row: str(row.get("item_id") or ""))
    return {
        "target": target,
        "grammar_unit_id": grammar_unit,
        "skill": skill,
        "cohort_count": len(cohort),
        "valid_unique_count": len(valid),
        "rejected": rejected,
        "template": rubric_templates[0],
    }


def prepare_adjective_review(
    *, source_bank_path: Path, target_item_id: str, target_root: Path
) -> dict[str, Any]:
    target_root = base.output_root(target_root)
    bank, bank_hash, bank_items = base.load_bank(source_bank_path)
    diagnosis = _shortage_diagnosis(
        bank_items,
        target_item_id,
        expected_grammar_unit=ADJECTIVE_GRAMMAR_UNIT,
    )
    candidates = [
        core._candidate_item(
            diagnosis["template"], diagnosis["grammar_unit_id"], spec
        )
        for spec in ADJECTIVE_CANDIDATE_SPECS
    ]
    fingerprints = {
        core.fullfix._contract_fingerprint(core.fullfix.learner_item(item)[0])
        for item in candidates
    }
    if len(fingerprints) != 2:
        raise DualWritingReviewError("candidate_stimulus_not_distinct")

    entries = [
        {
            "review_entry_id": f"M12G_ADJ_REVIEW_{index:02d}",
            "candidate_sha256": base.digest(item),
            "candidate": item,
            "review_criteria": list(REVIEW_CRITERIA),
        }
        for index, item in enumerate(candidates, 1)
    ]
    queue_core = {
        "task_id": TASK_ID,
        "schema_version": QUEUE_SCHEMA,
        "private_local_only": True,
        "source_session_bank_sha256": bank_hash,
        "target_item_id": target_item_id,
        "grammar_unit_id": diagnosis["grammar_unit_id"],
        "skill": diagnosis["skill"],
        "source_cohort_count": diagnosis["cohort_count"],
        "source_valid_unique_count": diagnosis["valid_unique_count"],
        "candidate_count": 2,
        "candidates": entries,
        "claim_boundaries": {
            "candidates_approved": False,
            "canonical_authority_modified": False,
            "source_bank_modified": False,
            "a2_content_included": False,
        },
    }
    queue = {**queue_core, "review_queue_sha256": base.digest(queue_core)}
    decisions = {
        "task_id": TASK_ID,
        "schema_version": DECISION_SCHEMA,
        "private_local_only": True,
        "review_queue_sha256": queue["review_queue_sha256"],
        "decision_count": 2,
        "decisions": [
            {
                "review_entry_id": entry["review_entry_id"],
                "candidate_item_id": entry["candidate"]["item_id"],
                "candidate_sha256": entry["candidate_sha256"],
                "decision": "PENDING",
                "reviewer_id": None,
                "reviewed_at": None,
                "criteria": {key: None for key in REVIEW_CRITERIA},
                "notes": None,
            }
            for entry in entries
        ],
    }

    queue_path = _write(target_root / ADJECTIVE_QUEUE_FILENAME, queue)
    decision_path = _write(target_root / ADJECTIVE_DECISION_FILENAME, decisions)
    html_path = target_root / ADJECTIVE_HTML_FILENAME
    html = core._queue_html(queue).replace(
        core.DECISION_FILENAME, ADJECTIVE_DECISION_FILENAME
    )
    html_path.write_text(html, encoding="utf-8")
    os.chmod(html_path, 0o600)
    runtime._repair_review_html(html_path)

    report = {
        "task_id": TASK_ID,
        "validation_status": STATUS_PENDING,
        "grammar_unit_id": ADJECTIVE_GRAMMAR_UNIT,
        "source_valid_unique_count": 2,
        "candidate_count": 2,
        "approved_candidate_count": 0,
        "canonical_authority_modified": False,
        "a2_lock_state": "LOCKED_BY_DESIGN",
        "stop_reason": "PRIVATE_AUTHORITY_REVIEW_REQUIRED",
    }
    report_path = _write(target_root / ADJECTIVE_REPORT_FILENAME, report)
    return {
        "report": report,
        "queue_path": queue_path,
        "decision_path": decision_path,
        "html_path": html_path,
        "report_path": report_path,
    }


def _approved_for_queue(
    *,
    bank_items: Mapping[str, Mapping[str, Any]],
    bank_hash: str,
    queue_path: Path,
    decision_path: Path,
    expected_grammar_unit: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    queue = base.read_json(base.local_path(queue_path, "review_queue"), "review_queue")
    decisions = base.read_json(
        base.local_path(decision_path, "decision_registry"), "decision_registry"
    )
    if queue.get("source_session_bank_sha256") != bank_hash:
        raise DualWritingReviewError("review_queue_source_bank_hash_mismatch")
    if queue.get("grammar_unit_id") != expected_grammar_unit:
        raise DualWritingReviewError(
            f"review_queue_grammar_unit_invalid:{queue.get('grammar_unit_id')}"
        )
    _shortage_diagnosis(
        bank_items,
        str(queue.get("target_item_id") or ""),
        expected_grammar_unit=expected_grammar_unit,
    )
    approved, receipts = core._approved_candidates(queue, decisions)
    return approved, receipts, queue


def apply_dual_reviews_and_prepare(
    *,
    source_bank_path: Path,
    base_consumer_path: Path,
    base_graph_path: Path,
    source_database_path: Path,
    resolved_root: Path,
    m12e1_root: Path,
    adverb_review_queue_path: Path,
    adverb_decision_registry_path: Path,
    adjective_review_queue_path: Path,
    adjective_decision_registry_path: Path,
    learner_id: str,
    display_label: str,
    target_root: Path,
) -> dict[str, Any]:
    target_root = base.output_root(target_root)
    bank, bank_hash, bank_items = base.load_bank(source_bank_path)

    adverb_approved, adverb_receipts, adverb_queue = _approved_for_queue(
        bank_items=bank_items,
        bank_hash=bank_hash,
        queue_path=adverb_review_queue_path,
        decision_path=adverb_decision_registry_path,
        expected_grammar_unit=ADVERB_GRAMMAR_UNIT,
    )
    adjective_approved, adjective_receipts, adjective_queue = _approved_for_queue(
        bank_items=bank_items,
        bank_hash=bank_hash,
        queue_path=adjective_review_queue_path,
        decision_path=adjective_decision_registry_path,
        expected_grammar_unit=ADJECTIVE_GRAMMAR_UNIT,
    )
    approved = adverb_approved + adjective_approved
    receipts = adverb_receipts + adjective_receipts
    approved_ids = {item["item_id"] for item in approved}
    if len(approved) != 4 or len(approved_ids) != 4:
        raise DualWritingReviewError("dual_approved_candidate_partition_invalid")

    overlay_root = target_root / "approved_overlay"
    overlay_root.mkdir(parents=True, exist_ok=True)
    overlay_bank = deepcopy(bank)
    existing_ids = {str(row.get("item_id")) for row in overlay_bank["items"]}
    if approved_ids.intersection(existing_ids):
        raise DualWritingReviewError("approved_candidate_identity_collision")
    overlay_bank["items"].extend(approved)
    overlay_bank["items"] = sorted(
        overlay_bank["items"], key=lambda row: str(row["item_id"])
    )
    overlay_bank["item_count"] = len(overlay_bank["items"])
    overlay_bank["items_sha256"] = m08.sha256_value(overlay_bank["items"])
    overlay_bank["m12g_dual_writing_reassessment_overlay"] = {
        "task_id": TASK_ID,
        "review_queue_sha256": sorted(
            [
                adverb_queue["review_queue_sha256"],
                adjective_queue["review_queue_sha256"],
            ]
        ),
        "approved_candidate_count": 4,
        "private_local_only": True,
        "canonical_authority_modified": False,
    }
    overlay_bank_hash = m08.sha256_value(overlay_bank)
    overlay_bank_path = _write(
        overlay_root / "text_mode_session_bank.m12g_dual_writing_reviewed.private.json",
        overlay_bank,
    )

    consumer = base.read_json(
        base.local_path(base_consumer_path, "base_consumer"), "base_consumer"
    )
    for asset in consumer.get("asset_records", []):
        payload = asset.get("payload")
        if isinstance(payload, dict) and "m12_session_bank_sha256" in payload:
            payload["m12_session_bank_sha256"] = overlay_bank_hash
            asset["content_digest"] = base.digest(payload)
    overlay_contract = consumer.get("m12f_dedicated_private_bridge_overlay")
    if not isinstance(overlay_contract, dict):
        raise DualWritingReviewError("consumer_bridge_overlay_missing")
    overlay_contract["source_session_bank_sha256"] = overlay_bank_hash
    consumer["m12g_dual_writing_reassessment_authority_review"] = {
        "task_id": TASK_ID,
        "approved_candidate_count": 4,
        "private_local_only": True,
    }
    overlay_consumer_path = _write(
        overlay_root / "four_skill_asset_body_consumer.m12g_dual_writing_reviewed.private.json",
        consumer,
    )

    source_m12e1 = base.local_path(m12e1_root, "m12e1_root")
    source_resolved = base.local_path(resolved_root, "resolved_root")
    try:
        resolved_relative = source_resolved.relative_to(source_m12e1)
    except ValueError as exc:
        raise DualWritingReviewError("resolved_root_not_inside_m12e1_root") from exc
    overlay_m12e1 = overlay_root / "m12e1"
    shutil.copytree(source_m12e1, overlay_m12e1)
    overlay_resolved = overlay_m12e1 / resolved_relative
    registry_path = overlay_resolved / "cumulative_attempt_registry.private.json"
    ledger_path = overlay_resolved / "cumulative_progress_ledger.private.json"
    registry = base.read_json(registry_path, "overlay_registry")
    ledger = base.read_json(ledger_path, "overlay_ledger")
    registry["session_bank_sha256"] = overlay_bank_hash
    _write(registry_path, registry)
    ledger["session_bank_sha256"] = overlay_bank_hash
    ledger["attempt_registry_sha256"] = m08.sha256_value(registry)
    _write(ledger_path, ledger)

    with runtime._patched_fullfix_database(target_root) as state:
        prepared = core.fullfix.prepare(
            source_bank_path=overlay_bank_path,
            base_consumer_path=overlay_consumer_path,
            base_graph_path=base_graph_path,
            source_database_path=source_database_path,
            resolved_root=overlay_resolved,
            m12e1_root=overlay_m12e1,
            learner_id=learner_id,
            display_label=display_label,
            target_root=target_root / "m12g",
        )

    database_overlay_path = state.get("database_overlay_path")
    if database_overlay_path is None or not database_overlay_path.is_file():
        raise DualWritingReviewError("database_overlay_not_materialized")

    report = prepared["report"]
    if report.get("validation_status") != core.fullfix.STATUS:
        raise DualWritingReviewError("prepared_fullfix_status_invalid")
    if report.get("required_attempt_count") != 8:
        raise DualWritingReviewError("prepared_attempt_count_invalid")
    if report.get("learner_contract_valid_count") != 8:
        raise DualWritingReviewError("prepared_learner_contract_count_invalid")

    package = base.read_json(prepared["package_path"], "prepared_package")
    selected_ids = {
        str(row.get("source_item_id")) for row in package.get("tasks", [])
    }
    if not approved_ids.issubset(selected_ids):
        raise DualWritingReviewError("approved_candidates_not_selected")

    safe_report = {
        "task_id": TASK_ID,
        "validation_status": STATUS_READY,
        "source_valid_unique_count": 4,
        "approved_candidate_count": 4,
        "approved_candidate_ids": sorted(approved_ids),
        "review_receipts": sorted(
            receipts, key=lambda row: row["candidate_item_id"]
        ),
        "pending_node_count": report["pending_node_count"],
        "required_attempt_count": report["required_attempt_count"],
        "learner_contract_valid_count": report["learner_contract_valid_count"],
        "a2_lock_state": report["a2_lock_state"],
        "canonical_authority_modified": False,
        "source_bank_original_modified": False,
        "private_database_overlay_rebound": True,
        "source_database_original_modified": False,
        "private_database_overlay_integrity": "PASS",
        "stop_reason": report["stop_reason"],
    }
    report_path = _write(target_root / DUAL_REPORT_FILENAME, safe_report)
    prepared.update(
        {
            "report": safe_report,
            "report_path": report_path,
            "overlay_bank_path": overlay_bank_path,
            "overlay_consumer_path": overlay_consumer_path,
            "source_database_overlay_path": database_overlay_path,
        }
    )
    return prepared


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    prepare = commands.add_parser("prepare-adjective-review")
    prepare.add_argument("--source-bank", type=Path, required=True)
    prepare.add_argument("--target-item-id", default=ADJECTIVE_TARGET_DEFAULT)
    prepare.add_argument("--output-root", type=Path, required=True)

    apply = commands.add_parser("apply-dual-review")
    for name in (
        "source-bank",
        "base-consumer",
        "base-graph",
        "source-database",
        "resolved-root",
        "m12e1-root",
        "adverb-review-queue",
        "adverb-decision-registry",
        "adjective-review-queue",
        "adjective-decision-registry",
        "output-root",
    ):
        apply.add_argument(f"--{name}", type=Path, required=True)
    apply.add_argument("--learner-id", required=True)
    apply.add_argument("--display-label", required=True)
    args = parser.parse_args(argv)

    try:
        if args.command == "prepare-adjective-review":
            result = prepare_adjective_review(
                source_bank_path=args.source_bank,
                target_item_id=args.target_item_id,
                target_root=args.output_root,
            )
            report = result["report"]
            payload = {
                "validation_status": report["validation_status"],
                "grammar_unit_id": report["grammar_unit_id"],
                "source_valid_unique_count": report["source_valid_unique_count"],
                "candidate_count": report["candidate_count"],
                "approved_candidate_count": report["approved_candidate_count"],
                "a2_lock_state": report["a2_lock_state"],
                "stop_reason": report["stop_reason"],
                "review_queue": str(result["queue_path"]),
                "decision_template": str(result["decision_path"]),
                "html": str(result["html_path"]),
            }
        else:
            result = apply_dual_reviews_and_prepare(
                source_bank_path=args.source_bank,
                base_consumer_path=args.base_consumer,
                base_graph_path=args.base_graph,
                source_database_path=args.source_database,
                resolved_root=args.resolved_root,
                m12e1_root=args.m12e1_root,
                adverb_review_queue_path=args.adverb_review_queue,
                adverb_decision_registry_path=args.adverb_decision_registry,
                adjective_review_queue_path=args.adjective_review_queue,
                adjective_decision_registry_path=args.adjective_decision_registry,
                learner_id=args.learner_id,
                display_label=args.display_label,
                target_root=args.output_root,
            )
            report = result["report"]
            payload = {
                "validation_status": report["validation_status"],
                "approved_candidate_count": report["approved_candidate_count"],
                "pending_node_count": report["pending_node_count"],
                "required_attempt_count": report["required_attempt_count"],
                "learner_contract_valid_count": report[
                    "learner_contract_valid_count"
                ],
                "a2_lock_state": report["a2_lock_state"],
                "private_database_overlay_rebound": report[
                    "private_database_overlay_rebound"
                ],
                "source_database_original_modified": report[
                    "source_database_original_modified"
                ],
                "stop_reason": report["stop_reason"],
                "html": str(result["html_path"]),
                "package": str(result["package_path"]),
                "database": str(result["database_path"]),
                "report": str(result["report_path"]),
            }
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return 0
    except (
        DualWritingReviewError,
        core.WritingReviewError,
        core.fullfix.AssessmentValidityError,
        base.ReassessmentError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
        sqlite3.Error,
    ) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
