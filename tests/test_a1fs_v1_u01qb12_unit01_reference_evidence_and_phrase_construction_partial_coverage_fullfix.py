from __future__ import annotations

import sqlite3
from copy import deepcopy
from pathlib import Path

from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.builders import build_a1fs_v1_u01qb02_unit01_approved_variant_session_runtime as qb02
from ulga.builders import build_a1fs_v1_u01qb12_unit01_reference_evidence_and_phrase_construction_partial_coverage_fullfix as builder
from ulga.builders import _razq01e_existing_qb_runtime_core as razq01e
from ulga.validators import validate_a1fs_v1_u01qb12_unit01_reference_evidence_and_phrase_construction_partial_coverage_fullfix as validator

EXTENSION_SHA = "c" * 64


def _prepare_m3_database(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.executescript(m3.SCHEMA_SQL)
        connection.execute("INSERT INTO metadata(key,value) VALUES('validation_status',?)", (m3.STATUS,))
        for skill, lesson_id in qb02.UNIT01_LESSONS.items():
            connection.execute(
                """INSERT INTO lesson_catalog
                (lesson_id,lesson_node_id,skill,level,roles_json,requirement_node_ids_json,payload_access_allowed)
                VALUES(?,?,?,?,?,?,1)""",
                (lesson_id, f"NODE:{lesson_id}", skill, "A1", "[]", "[]"),
            )


def _fixture_extension_items() -> list[dict]:
    _approved, base_items = qb02.approved_bank()
    by_skill = {
        skill: [deepcopy(row) for row in base_items if row["skill"] == skill]
        for skill in ("READING", "WRITING", "SPEAKING")
    }
    result: list[dict] = []
    for index in range(62):
        content_asset_id = f"FIXTURE-REAL62-{index:03d}"
        for skill in ("READING", "WRITING", "SPEAKING"):
            source = deepcopy(by_skill[skill][index % len(by_skill[skill])])
            source["item_id"] = f"U01QB01-RAZQ01E-{skill}-FIXTURE-{index:03d}"
            source["content_asset_id"] = content_asset_id
            source["semantic_signature"] = qb02.digest(
                {
                    "fixture": "REAL62-U01QB12",
                    "content_asset_id": content_asset_id,
                    "skill": skill,
                    "source": source["semantic_signature"],
                }
            )
            result.append(source)
    return result


def _install_legacy_474(path: Path) -> None:
    _prepare_m3_database(path)
    runtime = qb02.Unit01ApprovedVariantSessionRuntime(path)
    initialized = runtime.initialize()
    assert initialized["registered_item_count"] == 288
    items = _fixture_extension_items()
    assert len(items) == 186
    with runtime.write() as connection:
        connection.executescript(razq01e.EXTENSION_SQL)
        for item in items:
            razq01e._register_item(connection, item, approved_extension_sha256=EXTENSION_SHA)
        connection.executemany(
            "INSERT OR REPLACE INTO razq01e_metadata(key,value) VALUES(?,?)",
            {
                "task_id": razq01e.TASK_ID,
                "schema_version": razq01e.SCHEMA_VERSION,
                "validation_status": razq01e.PASS_STATUS,
                "approved_extension_artifact_sha256": EXTENSION_SHA,
                "extension_item_count": "186",
                "base_item_count": "288",
                "combined_runtime_item_count": "474",
                "existing_u01qb02_runtime_reused": "true",
                "parallel_runtime_created": "false",
                "a2_unlocked": "false",
            }.items(),
        )
        connection.executemany(
            "INSERT OR REPLACE INTO u01qb02_metadata(key,value) VALUES(?,?)",
            {
                "razq01e_extension_artifact_sha256": EXTENSION_SHA,
                "razq01e_extension_item_count": "186",
                "razq01e_combined_runtime_item_count": "474",
            }.items(),
        )
        assert connection.execute("SELECT COUNT(*) FROM u01qb02_item_catalog").fetchone()[0] == 474
        assert connection.execute("SELECT COUNT(*) FROM razq01e_extension_items").fetchone()[0] == 186


def test_u01qb12_reconciles_36_partial_slots_without_expanding_bank() -> None:
    candidate = builder.build_candidate()
    approved = builder.admit_candidate(candidate)
    report = validator.validate_approved(candidate, approved)
    assert report["error_count"] == 0
    payload = approved["payload"]
    assert payload["count_preservation"] == {
        "source_base_count": 288,
        "retained_base_count": 252,
        "retired_partial_support_count": 36,
        "exact_support_items_added": 36,
        "reconciled_base_count": 288,
        "unchanged_real62_extension_count": 186,
        "projected_runtime_total_count": 474,
    }
    coverage = payload["scored_task_angle_coverage"]
    assert coverage["scored_partial_support_before"] == 36
    assert coverage["scored_partial_support_after"] == 0
    assert coverage["reading_reference_evidence_exact_support_after"] == 24
    assert coverage["writing_phrase_construction_exact_support_after"] == 12
    assert coverage["scored_question_bank_full_alignment_ready"] is True
    family = payload["distribution_counts"]["family"]
    assert family[builder.PF16] == 24
    assert family[builder.PF17] == 12
    assert family[builder.SOURCE_REFERENCE_FAMILY] == 11
    assert family[builder.SOURCE_PHRASE_FAMILY] == 13


def test_u01qb12_migrates_existing_runtime_in_place_and_preserves_real62(tmp_path: Path) -> None:
    database = tmp_path / "learner_runtime.sqlite3"
    _install_legacy_474(database)
    with sqlite3.connect(database) as connection:
        before = connection.execute(
            "SELECT item_id,extension_item_sha256 FROM razq01e_extension_items ORDER BY item_id"
        ).fetchall()
    migration = builder.migrate_runtime(database)
    assert migration["already_migrated"] is False
    assert migration["retired_partial_support_item_count"] == 36
    assert migration["exact_support_item_added_count"] == 36
    assert migration["base_item_count"] == 288
    assert migration["extension_item_count"] == 186
    assert migration["combined_runtime_item_count"] == 474
    with sqlite3.connect(database) as connection:
        after = connection.execute(
            "SELECT item_id,extension_item_sha256 FROM razq01e_extension_items ORDER BY item_id"
        ).fetchall()
        assert before == after
        assert connection.execute("SELECT COUNT(*) FROM u01qb02_item_catalog").fetchone()[0] == 474
        assert connection.execute("SELECT COUNT(*) FROM response_contracts WHERE asset_key LIKE 'U01QB02:%'").fetchone()[0] == 558
        family_counts = dict(connection.execute(
            "SELECT pattern_family_id,COUNT(*) FROM u01qb02_item_catalog GROUP BY pattern_family_id"
        ).fetchall())
    assert family_counts[builder.PF16] == 24
    assert family_counts[builder.PF17] == 12


def test_u01qb12_real_474_replay_and_two_exact_support_attempts(tmp_path: Path) -> None:
    database = tmp_path / "learner_runtime.sqlite3"
    _install_legacy_474(database)
    report = builder.run_acceptance(database, run_attempt_canary=True)
    validated = validator.validate_report(report)
    assert validated["runtime_item_count"] == 474
    assert validated["scored_partial_support_after"] == 0
    replay = report["replay_474"]
    assert replay["skill_distribution"] == {"READING": 192, "SPEAKING": 87, "WRITING": 195}
    assert replay["deterministic_auto_pass_replay_count"] == 351
    assert replay["feature_rubric_pending_human_replay_count"] == 36
    assert replay["speaking_practice_only_count"] == 87
    assert replay["exact_support_family_counts"] == {builder.PF16: 24, builder.PF17: 12}
    canary = report["exact_support_attempt_canary"]
    assert canary["attempt_count"] == 2
    assert canary["all_auto_pass"] is True
    assert {row["family"] for row in canary["results"]} == {builder.PF16, builder.PF17}


def test_u01qb12_migration_is_idempotent(tmp_path: Path) -> None:
    database = tmp_path / "learner_runtime.sqlite3"
    _install_legacy_474(database)
    first = builder.migrate_runtime(database)
    second = builder.migrate_runtime(database)
    assert first["already_migrated"] is False
    assert second["already_migrated"] is True
    assert second["retired_partial_support_item_count"] == 0
    assert second["exact_support_item_added_count"] == 0
    assert second["real62_extension_identity_sha256"] == first["real62_extension_identity_sha256"]
    assert builder.replay_474(database)["runtime_item_count"] == 474


def test_u01qb12_validator_rejects_false_partial_closeout(tmp_path: Path) -> None:
    database = tmp_path / "learner_runtime.sqlite3"
    _install_legacy_474(database)
    report = builder.run_acceptance(database, run_attempt_canary=True)
    drifted = deepcopy(report)
    drifted["coverage_closeout"]["scored_partial_support_count"] = 1
    unsigned = dict(drifted)
    unsigned.pop("readback_sha256", None)
    drifted["readback_sha256"] = builder.digest(unsigned)
    try:
        validator.validate_report(drifted)
    except validator.PartialCoverageFullFixValidationError as exc:
        assert "CLOSEOUT_PARTIAL_INVALID" in str(exc)
    else:
        raise AssertionError("validator accepted false partial closeout")
