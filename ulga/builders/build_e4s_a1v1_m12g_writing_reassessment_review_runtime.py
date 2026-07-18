#!/usr/bin/env python3
"""Run reviewed M12G writing candidates against a hash-bound private DB overlay.

The Authority-review builder creates a private consumer overlay whose digest must
not be written into the original M12F SQLite database. This wrapper intercepts the
existing M12G prepare call, copies the source database, rebinds only the copied
metadata to the reviewed consumer, validates SQLite integrity, and then delegates
to the unchanged M12G fullfix pipeline.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_e4s_a1v1_m12g_dedicated_writing_reassessment_authority_review as core  # noqa: E402
from ulga.builders import build_e4s_a1v1_m12g_remediation_reassessment_execution as base  # noqa: E402

TASK_ID = core.TASK_ID
QUEUE_SCHEMA = core.QUEUE_SCHEMA
DECISION_SCHEMA = core.DECISION_SCHEMA
STATUS_PENDING = core.STATUS_PENDING
STATUS_READY = core.STATUS_READY
REVIEW_CRITERIA = core.REVIEW_CRITERIA
TARGET_DEFAULT = core.TARGET_DEFAULT
WritingReviewError = core.WritingReviewError
fullfix = core.fullfix
prepare_review = core.prepare_review

DATABASE_OVERLAY_FILENAME = "m12f_source_database.reviewed_consumer_overlay.private.sqlite3"


def _copy_and_rebind_database(
    *, source_database_path: Path, overlay_database_path: Path, consumer_path: Path
) -> Path:
    source = base.local_path(source_database_path, "source_database")
    overlay = base.local_path(
        overlay_database_path, "source_database_overlay", must_exist=False
    )
    if overlay.exists():
        raise WritingReviewError("source_database_overlay_already_exists")
    overlay.parent.mkdir(parents=True, exist_ok=True)

    source_connection = sqlite3.connect(source)
    overlay_connection = sqlite3.connect(overlay)
    try:
        source_connection.backup(overlay_connection)
        cursor = overlay_connection.execute(
            "UPDATE metadata SET value=? WHERE key='consumer_sha256'",
            (base.file_sha(consumer_path),),
        )
        if cursor.rowcount != 1:
            raise WritingReviewError("database_consumer_metadata_missing")
        if overlay_connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise WritingReviewError("database_overlay_integrity_failed")
        if overlay_connection.execute("PRAGMA foreign_key_check").fetchall():
            raise WritingReviewError("database_overlay_foreign_key_failed")
        overlay_connection.commit()
    finally:
        overlay_connection.close()
        source_connection.close()
    return overlay


@contextmanager
def _patched_fullfix_database(target_root: Path) -> Iterator[dict[str, Path]]:
    original_prepare = core.fullfix.prepare
    state: dict[str, Path] = {}

    def prepare_with_overlay(**kwargs: Any) -> dict[str, Any]:
        consumer_path = Path(kwargs["base_consumer_path"])
        overlay_database_path = target_root / DATABASE_OVERLAY_FILENAME
        overlay_database = _copy_and_rebind_database(
            source_database_path=Path(kwargs["source_database_path"]),
            overlay_database_path=overlay_database_path,
            consumer_path=consumer_path,
        )
        state["database_overlay_path"] = overlay_database
        delegated = dict(kwargs)
        delegated["source_database_path"] = overlay_database
        return original_prepare(**delegated)

    core.fullfix.prepare = prepare_with_overlay
    try:
        yield state
    finally:
        core.fullfix.prepare = original_prepare


def apply_review_and_prepare(**kwargs: Any) -> dict[str, Any]:
    target_root = base.output_root(Path(kwargs["target_root"]))
    delegated = dict(kwargs)
    delegated["target_root"] = target_root
    with _patched_fullfix_database(target_root) as state:
        result = core.apply_review_and_prepare(**delegated)

    overlay_path = state.get("database_overlay_path")
    if overlay_path is None or not overlay_path.is_file():
        raise WritingReviewError("database_overlay_not_materialized")
    report = dict(result["report"])
    report.update(
        {
            "private_database_overlay_rebound": True,
            "source_database_original_modified": False,
            "private_database_overlay_integrity": "PASS",
        }
    )
    core._write(Path(result["report_path"]), report)
    result["report"] = report
    result["source_database_overlay_path"] = overlay_path
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare-review")
    prepare.add_argument("--source-bank", type=Path, required=True)
    prepare.add_argument("--target-item-id", default=TARGET_DEFAULT)
    prepare.add_argument("--output-root", type=Path, required=True)

    apply = commands.add_parser("apply-review")
    for name in (
        "source-bank",
        "base-consumer",
        "base-graph",
        "source-database",
        "resolved-root",
        "m12e1-root",
        "review-queue",
        "decision-registry",
        "output-root",
    ):
        apply.add_argument(f"--{name}", type=Path, required=True)
    apply.add_argument("--learner-id", required=True)
    apply.add_argument("--display-label", required=True)
    args = parser.parse_args(argv)

    try:
        if args.command == "prepare-review":
            result = prepare_review(
                source_bank_path=args.source_bank,
                target_item_id=args.target_item_id,
                target_root=args.output_root,
            )
            report = result["report"]
            payload = {
                "validation_status": report["validation_status"],
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
            result = apply_review_and_prepare(
                source_bank_path=args.source_bank,
                base_consumer_path=args.base_consumer,
                base_graph_path=args.base_graph,
                source_database_path=args.source_database,
                resolved_root=args.resolved_root,
                m12e1_root=args.m12e1_root,
                review_queue_path=args.review_queue,
                decision_registry_path=args.decision_registry,
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
        WritingReviewError,
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
