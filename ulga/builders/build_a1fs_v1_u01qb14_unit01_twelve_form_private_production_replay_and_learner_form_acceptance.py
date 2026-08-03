#!/usr/bin/env python3
"""Replay the real Unit01 twelve-form blueprint on a disposable learner DB copy.

U01QB14 is an acceptance runner, not a new planner or runtime. It consumes the
real U01QB08 rotation, U01QB09 allocation, and an already-active U01QB12 learner
runtime database. The canonical learner database is never opened for write.
Instead, the source must be offline (no non-empty WAL/journal), is copied byte for
byte to a distinct disposable path, and all U01QB13 install/session/exposure/M6
work happens only on that copy.

One disposable learner executes all twelve forms in order so prior exposure is
real when Forms 10-12 enter assessment-transfer mode. Only blueprint-bound form
activities are exposed. U01QB02 support fillers remain unexposed and are not
assessment evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.builders import build_a1fs_v1_u01qb02_unit01_approved_variant_session_runtime as qb02
from ulga.builders import build_a1fs_v1_u01qb08_unit01_twelve_form_scene_rotation as u01qb08
from ulga.builders import build_a1fs_v1_u01qb09_unit01_scene_skill_task_angle_support_allocation as u01qb09
from ulga.builders import build_a1fs_v1_u01qb12_unit01_reference_evidence_and_phrase_construction_partial_coverage_fullfix as u01qb12
from ulga.builders import build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration as u01qb13
from ulga.validators import validate_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration as u01qb13_validator

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Read-only offline copy of the canonical learner database followed by U01QB13 replay on a disposable copy only; no canonical learner state, learner content, second planner, second runtime, or parallel scoring authority is created."
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB14_Unit01TwelveFormPrivateProductionReplayAndLearnerFormAcceptance"
SCHEMA_VERSION = "a1fs.v1.u01qb14.unit01_twelve_form_private_production_replay.v1"
PASS_STATUS = "PASS_A1FS_V1_U01QB14_UNIT01_TWELVE_FORM_PRIVATE_PRODUCTION_REPLAY_AND_LEARNER_FORM_ACCEPTANCE"
FORM_COUNT = 12
SKILLS = ("READING", "WRITING", "SPEAKING")
EXPECTED_SESSION_COUNT = 36
EXPECTED_BLUEPRINT_EXPOSURES = 240
EXPECTED_SCORED_ATTEMPTS = 192
EXPECTED_SPEAKING_EXPOSURES = 48
EXPECTED_RUNTIME_SESSION_ITEMS = 360
EXPECTED_SUPPORT_FILLERS = 120
EXPECTED_AUTO_PASS = 156
EXPECTED_PENDING_HUMAN = 36
EXPECTED_ASSESSMENT_SCORED = 48
EXPECTED_ASSESSMENT_SPEAKING = 12
EXPECTED_RUNTIME_ITEMS = 474
EXPECTED_EXTENSION_ITEMS = 186
DEFAULT_REPORT = Path(".local/a1fs_v1/u01qb14/u01qb14_private_production_replay.json")
NEXT_SHORT_STEP = "A1FS-V1-U01QB15_Unit01LearnerFormReleaseAcceptanceAndUnit01CloseoutReadback"


class PrivateProductionReplayError(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def file_digest(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path: Path) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PrivateProductionReplayError(f"UNREADABLE_JSON:{path}:{exc}") from exc


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _source_sidecar(path: Path, suffix: str) -> Path:
    return Path(str(path) + suffix)


def _assert_source_offline(path: Path) -> None:
    for suffix in ("-wal", "-journal"):
        sidecar = _source_sidecar(path, suffix)
        if sidecar.exists() and sidecar.stat().st_size > 0:
            raise PrivateProductionReplayError(
                f"CANONICAL_DATABASE_NOT_OFFLINE:{sidecar}:close_the_canonical_runtime_before_replay"
            )


def _source_snapshot(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "sha256": file_digest(path),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def _prepare_disposable_copy(
    canonical_database: Path,
    disposable_database: Path,
    *,
    replace_disposable: bool,
) -> tuple[dict[str, Any], str]:
    source = canonical_database.resolve(strict=True)
    destination = disposable_database.resolve(strict=False)
    if source == destination:
        raise PrivateProductionReplayError("DISPOSABLE_DATABASE_MUST_DIFFER_FROM_CANONICAL")
    if not source.is_file():
        raise PrivateProductionReplayError("CANONICAL_DATABASE_MISSING")
    _assert_source_offline(source)
    before = _source_snapshot(source)

    if destination.exists():
        try:
            if os.path.samefile(source, destination):
                raise PrivateProductionReplayError("DISPOSABLE_DATABASE_ALIASES_CANONICAL")
        except OSError:
            pass
        if not replace_disposable:
            raise PrivateProductionReplayError("DISPOSABLE_DATABASE_EXISTS_USE_REPLACE_FLAG")
        destination.unlink()
    for suffix in ("-wal", "-shm", "-journal"):
        sidecar = _source_sidecar(destination, suffix)
        if sidecar.exists():
            if not replace_disposable:
                raise PrivateProductionReplayError(f"DISPOSABLE_SIDECAR_EXISTS:{sidecar}")
            sidecar.unlink()

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    copied_sha = file_digest(destination)
    if copied_sha != before["sha256"]:
        raise PrivateProductionReplayError("DISPOSABLE_INITIAL_COPY_SHA_MISMATCH")
    return before, copied_sha


def _verify_u01qb12_runtime(database: Path) -> dict[str, Any]:
    with sqlite3.connect(database) as connection:
        tables = {
            str(row[0])
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        required = {
            "u01qb02_item_catalog",
            "u01qb02_session_plans",
            "u01qb02_session_items",
            "u01qb02_item_exposures",
            "razq01e_extension_items",
            "u01qb12_metadata",
            "response_contracts",
            "response_attempts",
            "scoring_results",
        }
        missing = sorted(required - tables)
        if missing:
            raise PrivateProductionReplayError("U01QB12_RUNTIME_TABLES_MISSING:" + ",".join(missing))
        u12_meta = dict(connection.execute("SELECT key,value FROM u01qb12_metadata"))
        if u12_meta.get("validation_status") != u01qb12.PASS_STATUS:
            raise PrivateProductionReplayError("U01QB12_RUNTIME_NOT_ACTIVE")
        runtime_count = int(connection.execute("SELECT COUNT(*) FROM u01qb02_item_catalog").fetchone()[0])
        extension_count = int(connection.execute("SELECT COUNT(*) FROM razq01e_extension_items").fetchone()[0])
    if runtime_count != EXPECTED_RUNTIME_ITEMS or extension_count != EXPECTED_EXTENSION_ITEMS:
        raise PrivateProductionReplayError(
            f"RUNTIME_DENOMINATOR_INVALID:{runtime_count}:{extension_count}"
        )
    return {
        "runtime_item_count": runtime_count,
        "extension_item_count": extension_count,
        "u01qb12_validation_status": u12_meta["validation_status"],
    }


def _build_approved_blueprint(rotation: Mapping[str, Any], allocation: Mapping[str, Any]) -> dict[str, Any]:
    # U01QB13 independently validates U01QB08/U01QB09 before materialization.
    candidate = u01qb13.build_candidate(rotation, allocation)
    approved = u01qb13.admit_candidate(candidate)
    validation = u01qb13_validator.validate_approved(candidate, approved)
    if validation.get("error_count"):
        raise PrivateProductionReplayError(
            "U01QB13_BLUEPRINT_VALIDATION_FAILED:" + "|".join(validation.get("errors") or [])
        )
    payload = approved.get("payload") or {}
    if (
        payload.get("coverage_readback", {}).get("activity_count") != EXPECTED_BLUEPRINT_EXPOSURES
        or payload.get("coverage_readback", {}).get("scored_activity_count") != EXPECTED_SCORED_ATTEMPTS
        or payload.get("coverage_readback", {}).get("speaking_practice_activity_count") != EXPECTED_SPEAKING_EXPOSURES
    ):
        raise PrivateProductionReplayError("BLUEPRINT_DENOMINATOR_INVALID")
    return approved


def _accepted_response(database: Path, item_id: str) -> tuple[Any, str]:
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """SELECT c.private_item_json,r.contract_json
               FROM u01qb02_item_catalog c
               JOIN response_contracts r USING(asset_key)
               WHERE c.item_id=?""",
            (item_id,),
        ).fetchone()
    if row is None:
        raise PrivateProductionReplayError(f"RUNTIME_ITEM_MISSING:{item_id}")
    item = json.loads(str(row["private_item_json"]))
    contract = json.loads(str(row["contract_json"]))
    mode = str(contract.get("scoring_mode") or "")
    if mode == "EXACT_SEQUENCE":
        answer = list(contract.get("accepted_sequence") or [])
        if not answer:
            raise PrivateProductionReplayError(f"ACCEPTED_SEQUENCE_MISSING:{item_id}")
        return answer, mode
    texts = list(contract.get("accepted_texts") or [])
    if texts:
        return str(texts[0]), mode
    answer = item.get("correct_answer")
    if isinstance(answer, str) and answer.strip():
        return answer, mode
    raise PrivateProductionReplayError(f"ACCEPTED_RESPONSE_MISSING:{item_id}")


def _profile_version(snapshot: Mapping[str, Any]) -> int:
    profile = snapshot.get("profile")
    if not isinstance(profile, Mapping):
        raise PrivateProductionReplayError("PROFILE_SNAPSHOT_INVALID")
    return int(profile["profile_version"])


def _session_counts(database: Path, learner_id: str) -> dict[str, int]:
    with sqlite3.connect(database) as connection:
        sessions = int(
            connection.execute(
                "SELECT COUNT(*) FROM learning_sessions WHERE learner_id=?",
                (learner_id,),
            ).fetchone()[0]
        )
        session_items = int(
            connection.execute(
                """SELECT COUNT(*) FROM u01qb02_session_items i
                   JOIN u01qb02_session_plans p USING(session_id)
                   WHERE p.learner_id=?""",
                (learner_id,),
            ).fetchone()[0]
        )
        bindings = int(
            connection.execute(
                """SELECT COUNT(*) FROM u01qb13_session_bindings b
                   JOIN u01qb02_session_plans p USING(session_id)
                   WHERE p.learner_id=?""",
                (learner_id,),
            ).fetchone()[0]
        )
        exposures = int(
            connection.execute(
                "SELECT COUNT(*) FROM u01qb02_item_exposures WHERE learner_id=?",
                (learner_id,),
            ).fetchone()[0]
        )
        attempts = int(
            connection.execute(
                "SELECT COUNT(*) FROM response_attempts WHERE learner_id=?",
                (learner_id,),
            ).fetchone()[0]
        )
        filler_exposures = int(
            connection.execute(
                """SELECT COUNT(*)
                   FROM u01qb02_item_exposures e
                   JOIN u01qb02_session_plans p USING(session_id)
                   LEFT JOIN u01qb13_session_bindings b
                     ON b.session_id=e.session_id AND b.item_id=e.item_id
                   WHERE p.learner_id=? AND b.activity_id IS NULL""",
                (learner_id,),
            ).fetchone()[0]
        )
        assessment_bindings = int(
            connection.execute(
                """SELECT COUNT(*) FROM u01qb13_session_bindings b
                   JOIN u01qb02_session_plans p USING(session_id)
                   WHERE p.learner_id=? AND b.is_assessment_evidence=1""",
                (learner_id,),
            ).fetchone()[0]
        )
    return {
        "session_count": sessions,
        "runtime_session_item_count": session_items,
        "blueprint_binding_count": bindings,
        "blueprint_exposure_count": exposures,
        "response_attempt_count": attempts,
        "support_filler_exposure_count": filler_exposures,
        "assessment_binding_count": assessment_bindings,
    }


def _execute_twelve_forms(database: Path, *, learner_id: str) -> dict[str, Any]:
    state = m3.LearnerStateStore(database)
    try:
        state.create_profile(
            learner_id=learner_id,
            display_label="U01QB14 Disposable Twelve Form Acceptance",
        )
    except m3.StateStoreError as exc:
        raise PrivateProductionReplayError(f"DISPOSABLE_LEARNER_ID_NOT_FRESH:{learner_id}:{exc}") from exc

    runtime = qb02.Unit01ApprovedVariantSessionRuntime(database)
    outcome_counts: Counter[str] = Counter()
    scoring_mode_counts: Counter[str] = Counter()
    binding_quality_counts: Counter[str] = Counter()
    skill_exposures: Counter[str] = Counter()
    assessment_scored = 0
    assessment_speaking = 0
    assessment_transfer = 0
    form_rows: list[dict[str, Any]] = []

    for form_ordinal in range(1, FORM_COUNT + 1):
        per_form = {
            "form_ordinal": form_ordinal,
            "form_id": f"U01-FORM-{form_ordinal:02d}",
            "blueprint_exposures": 0,
            "scored_attempts": 0,
            "speaking_practice_exposures": 0,
            "assessment_scored_attempts": 0,
            "sessions": [],
        }
        for skill in SKILLS:
            profile = state.profile_snapshot(learner_id)
            session_id = f"u01qb14-f{form_ordinal:02d}-{skill.casefold()}"
            state.start_session(
                learner_id=learner_id,
                lesson_id=qb02.UNIT01_LESSONS[skill],
                session_id=session_id,
                expected_profile_version=_profile_version(profile),
            )
            component = u01qb13.assemble_form_component(
                database,
                learner_id=learner_id,
                session_id=session_id,
                form_ordinal=form_ordinal,
            )
            if component["form_ordinal"] != form_ordinal or component["skill"] != skill:
                raise PrivateProductionReplayError(f"FORM_COMPONENT_IDENTITY_INVALID:{form_ordinal}:{skill}")
            expected_activities = {"READING": 8, "WRITING": 8, "SPEAKING": 4}[skill]
            if component["blueprint_activity_count"] != expected_activities:
                raise PrivateProductionReplayError(f"FORM_COMPONENT_COUNT_INVALID:{form_ordinal}:{skill}")

            session_scored = 0
            session_speaking = 0
            for item in component["items"]:
                snapshot = state.session_snapshot(session_id)
                exposed = runtime.record_item_exposure(
                    session_id=session_id,
                    item_id=str(item["item_id"]),
                    expected_session_version=int(snapshot["session_version"]),
                )
                per_form["blueprint_exposures"] += 1
                skill_exposures[skill] += 1
                binding_quality_counts[str(item["binding_quality"])] += 1

                if skill == "SPEAKING":
                    if item["scored"] or item["capture_enabled"] or not item["practice_only"]:
                        raise PrivateProductionReplayError(f"SPEAKING_BOUNDARY_INVALID:{item['activity_id']}")
                    per_form["speaking_practice_exposures"] += 1
                    session_speaking += 1
                    if form_ordinal in u01qb13.ASSESSMENT_FORM_ORDINALS:
                        assessment_speaking += 1
                    continue

                if not item["scored"] or not item["capture_enabled"]:
                    raise PrivateProductionReplayError(f"SCORED_CAPTURE_BOUNDARY_INVALID:{item['activity_id']}")
                answer, mode = _accepted_response(database, str(item["item_id"]))
                attempted = runtime.capture_response(
                    learner_id=learner_id,
                    session_id=session_id,
                    item_id=str(item["item_id"]),
                    response=answer,
                    expected_session_version=int(exposed["session_version"]),
                )
                outcome = str(attempted["outcome"])
                expected_outcome = "PENDING_HUMAN_REVIEW" if mode == "FEATURE_RUBRIC" else "AUTO_PASS"
                if outcome != expected_outcome:
                    raise PrivateProductionReplayError(
                        f"M6_REPLAY_OUTCOME_INVALID:{item['item_id']}:{mode}:{outcome}"
                    )
                outcome_counts[outcome] += 1
                scoring_mode_counts[mode] += 1
                per_form["scored_attempts"] += 1
                session_scored += 1
                if item["assessment_candidate"]:
                    if form_ordinal not in u01qb13.ASSESSMENT_FORM_ORDINALS:
                        raise PrivateProductionReplayError("ASSESSMENT_CANDIDATE_OUTSIDE_ASSESSMENT_FORMS")
                    assessment_scored += 1
                    per_form["assessment_scored_attempts"] += 1
                    if item["selection_reason"] == "TRANSFER":
                        assessment_transfer += 1

            final_snapshot = state.session_snapshot(session_id)
            state.end_session(
                session_id=session_id,
                outcome="COMPLETED",
                expected_session_version=int(final_snapshot["session_version"]),
            )
            per_form["sessions"].append(
                {
                    "skill": skill,
                    "session_id": session_id,
                    "blueprint_activity_count": component["blueprint_activity_count"],
                    "support_filler_count": component["support_filler_count"],
                    "scored_attempt_count": session_scored,
                    "speaking_practice_exposure_count": session_speaking,
                }
            )

        if (
            per_form["blueprint_exposures"] != 20
            or per_form["scored_attempts"] != 16
            or per_form["speaking_practice_exposures"] != 4
        ):
            raise PrivateProductionReplayError(f"FORM_ACCEPTANCE_DENOMINATOR_INVALID:{form_ordinal}")
        if form_ordinal in u01qb13.ASSESSMENT_FORM_ORDINALS:
            if per_form["assessment_scored_attempts"] != 16:
                raise PrivateProductionReplayError(f"ASSESSMENT_FORM_DENOMINATOR_INVALID:{form_ordinal}")
        elif per_form["assessment_scored_attempts"] != 0:
            raise PrivateProductionReplayError(f"NON_ASSESSMENT_FORM_EVIDENCE_INVALID:{form_ordinal}")
        form_rows.append(per_form)

    counts = _session_counts(database, learner_id)
    expected_counts = {
        "session_count": EXPECTED_SESSION_COUNT,
        "runtime_session_item_count": EXPECTED_RUNTIME_SESSION_ITEMS,
        "blueprint_binding_count": EXPECTED_BLUEPRINT_EXPOSURES,
        "blueprint_exposure_count": EXPECTED_BLUEPRINT_EXPOSURES,
        "response_attempt_count": EXPECTED_SCORED_ATTEMPTS,
        "support_filler_exposure_count": 0,
        "assessment_binding_count": EXPECTED_ASSESSMENT_SCORED,
    }
    if counts != expected_counts:
        raise PrivateProductionReplayError(f"DATABASE_EXECUTION_COUNTS_INVALID:{counts}")
    if dict(outcome_counts) != {
        "AUTO_PASS": EXPECTED_AUTO_PASS,
        "PENDING_HUMAN_REVIEW": EXPECTED_PENDING_HUMAN,
    }:
        raise PrivateProductionReplayError(f"SCORING_OUTCOME_COUNTS_INVALID:{dict(outcome_counts)}")
    if assessment_scored != EXPECTED_ASSESSMENT_SCORED or assessment_speaking != EXPECTED_ASSESSMENT_SPEAKING:
        raise PrivateProductionReplayError(
            f"ASSESSMENT_DENOMINATOR_INVALID:{assessment_scored}:{assessment_speaking}"
        )
    if assessment_transfer != EXPECTED_ASSESSMENT_SCORED:
        raise PrivateProductionReplayError(f"ASSESSMENT_TRANSFER_SELECTION_INVALID:{assessment_transfer}")

    return {
        "learner_id": learner_id,
        "form_count": len(form_rows),
        **counts,
        "skill_exposure_counts": dict(sorted(skill_exposures.items())),
        "outcome_counts": dict(sorted(outcome_counts.items())),
        "scoring_mode_counts": dict(sorted(scoring_mode_counts.items())),
        "binding_quality_counts": dict(sorted(binding_quality_counts.items())),
        "assessment_scored_attempt_count": assessment_scored,
        "assessment_speaking_practice_count": assessment_speaking,
        "assessment_transfer_selection_count": assessment_transfer,
        "forms": form_rows,
    }


def run_private_replay(
    *,
    rotation_path: Path,
    allocation_path: Path,
    canonical_database: Path,
    disposable_database: Path,
    replace_disposable: bool = False,
    learner_id: str = "u01qb14-disposable-learner",
) -> dict[str, Any]:
    rotation_path = Path(rotation_path).resolve(strict=True)
    allocation_path = Path(allocation_path).resolve(strict=True)
    canonical_database = Path(canonical_database).resolve(strict=True)
    disposable_database = Path(disposable_database).resolve(strict=False)

    rotation = read_json(rotation_path)
    allocation = read_json(allocation_path)
    approved = _build_approved_blueprint(rotation, allocation)

    source_before, copied_sha = _prepare_disposable_copy(
        canonical_database,
        disposable_database,
        replace_disposable=replace_disposable,
    )
    runtime_before = _verify_u01qb12_runtime(disposable_database)
    installed = u01qb13.install_blueprint(disposable_database, approved)
    execution = _execute_twelve_forms(disposable_database, learner_id=learner_id)
    runtime_after = _verify_u01qb12_runtime(disposable_database)

    source_after = _source_snapshot(canonical_database)
    if source_after != source_before:
        raise PrivateProductionReplayError(
            f"CANONICAL_DATABASE_CHANGED_DURING_REPLAY:{source_before}:{source_after}"
        )
    if runtime_before != runtime_after:
        raise PrivateProductionReplayError(f"RUNTIME_DENOMINATOR_DRIFT:{runtime_before}:{runtime_after}")

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "unit_id": u01qb13.UNIT_ID,
        "input_authority": {
            "rotation_path": str(rotation_path),
            "rotation_file_sha256": file_digest(rotation_path),
            "rotation_sha256": str(rotation["rotation_sha256"]),
            "allocation_path": str(allocation_path),
            "allocation_file_sha256": file_digest(allocation_path),
            "allocation_sha256": str(allocation["allocation_sha256"]),
            "u01qb13_blueprint_artifact_sha256": str(approved["artifact_sha256"]),
            "active_question_bank_revision": u01qb12.CANONICAL_REVISION,
        },
        "canonical_database_safety": {
            "canonical_database": str(canonical_database),
            "canonical_sha256_before": source_before["sha256"],
            "canonical_sha256_after": source_after["sha256"],
            "canonical_size_before": source_before["size"],
            "canonical_size_after": source_after["size"],
            "canonical_mtime_ns_before": source_before["mtime_ns"],
            "canonical_mtime_ns_after": source_after["mtime_ns"],
            "canonical_database_unchanged": source_before == source_after,
            "canonical_database_opened_for_write": False,
            "canonical_learner_state_modified": False,
        },
        "disposable_copy": {
            "database": str(disposable_database),
            "initial_copy_sha256": copied_sha,
            "initial_copy_matches_canonical": copied_sha == source_before["sha256"],
            "final_sha256": file_digest(disposable_database),
            "copy_modified_by_replay": file_digest(disposable_database) != copied_sha,
            "replace_disposable_requested": replace_disposable,
        },
        "runtime_before": runtime_before,
        "u01qb13_installation": installed,
        "execution_acceptance": execution,
        "runtime_after": runtime_after,
        "boundaries": {
            "disposable_copy_used": True,
            "canonical_database_mutated": False,
            "question_bank_total_expanded": False,
            "real62_extension_modified": False,
            "second_planner_created": False,
            "second_runtime_created": False,
            "parallel_database_authority_created": False,
            "parallel_scoring_created": False,
            "support_fillers_exposed": False,
            "speaking_capture_enabled": False,
            "speaking_scoring_enabled": False,
            "unit02_to_unit24_modified": False,
            "a2_unlocked": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    report["readback_sha256"] = digest(report)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rotation", type=Path, required=True)
    parser.add_argument("--allocation", type=Path, required=True)
    parser.add_argument("--canonical-database", type=Path, required=True)
    parser.add_argument("--disposable-database", type=Path, required=True)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--replace-disposable", action="store_true")
    parser.add_argument("--learner-id", default="u01qb14-disposable-learner")
    args = parser.parse_args(argv)
    try:
        report = run_private_replay(
            rotation_path=args.rotation,
            allocation_path=args.allocation,
            canonical_database=args.canonical_database,
            disposable_database=args.disposable_database,
            replace_disposable=args.replace_disposable,
            learner_id=args.learner_id,
        )
        from ulga.validators import validate_a1fs_v1_u01qb14_unit01_twelve_form_private_production_replay_and_learner_form_acceptance as validator

        validator.validate_report(report)
        write_json(args.report.resolve(), report)
    except (
        PrivateProductionReplayError,
        u01qb13.BlueprintIntegrationError,
        m3.StateStoreError,
        qb02.SessionRuntimeError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
        sqlite3.Error,
    ) as exc:
        print("STATUS=FAIL_A1FS_V1_U01QB14_UNIT01_TWELVE_FORM_PRIVATE_PRODUCTION_REPLAY")
        print(f"ERROR={exc}")
        return 1
    acceptance = report["execution_acceptance"]
    print(f"STATUS={PASS_STATUS}")
    print(f"CANONICAL_DATABASE_UNCHANGED={report['canonical_database_safety']['canonical_database_unchanged']}")
    print(f"FORMS={acceptance['form_count']}")
    print(f"SESSIONS={acceptance['session_count']}")
    print(f"BLUEPRINT_EXPOSURES={acceptance['blueprint_exposure_count']}")
    print(f"SCORED_ATTEMPTS={acceptance['response_attempt_count']}")
    print(f"AUTO_PASS={acceptance['outcome_counts'].get('AUTO_PASS', 0)}")
    print(f"PENDING_HUMAN_REVIEW={acceptance['outcome_counts'].get('PENDING_HUMAN_REVIEW', 0)}")
    print(f"ASSESSMENT_SCORED={acceptance['assessment_scored_attempt_count']}")
    print(f"SUPPORT_FILLER_EXPOSURES={acceptance['support_filler_exposure_count']}")
    print(f"REPORT={args.report.resolve()}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
