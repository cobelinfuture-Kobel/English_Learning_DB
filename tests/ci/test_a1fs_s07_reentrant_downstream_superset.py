from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from ulga.runners import run_a1fs_s07_with_explicit_sqlite_close as runner

s07 = runner.s07


BASE_LESSON = "A1FS_ONLINE_V1:GRAMMAR_ARTICLES_BASIC:READING"
BASE_ASSET = "E4S_A1V1_ITEM:GRAMMAR_ARTICLES_BASIC:TEST_BASE"


def _consumer() -> dict:
    asset = {
        "asset_key": BASE_ASSET,
        "asset_id": "ASSET:GRAMMAR_ARTICLES_BASIC:TEST_BASE",
        "lesson_id": BASE_LESSON,
        "skill": "READING",
        "role": "CHK",
        "content_digest": "a" * 64,
        "payload": {
            "prompt": "Choose yes.",
            "response_capture_enabled": True,
            "private_scoring_contract": {
                "scoring_mode": "EXACT_OPTION",
                "accepted_texts": ["Yes"],
                "case_insensitive": True,
                "punctuation_tolerance": True,
            },
        },
    }
    return {
        "task_id": s07.m2.TASK_ID,
        "schema_version": s07.m2.SCHEMA_VERSION,
        "validation_status": s07.m2.STATUS,
        "asset_records": [asset],
        "lesson_catalog": [
            {
                "lesson_id": BASE_LESSON,
                "lesson_node_id": "RUNTIME_PROJECTION:READING:GRAMMAR_ARTICLES_BASIC",
                "skill": "READING",
                "level": "A1",
                "roles": ["CHK"],
                "requirement_node_ids": ["EGP_A1_TEST"],
            }
        ],
        "counts": {
            "asset_record_count": 1,
            "lesson_count": 1,
            "learning_lesson_count": 1,
            "a2_handoff_lesson_count": 0,
        },
        "s07_runtime_projection": {
            "admitted_unit_count": 1,
        },
    }


def _write_consumer_and_bundle(root: Path, consumer: dict) -> tuple[Path, dict[str, str]]:
    consumer_path = root / "consumer.private.json"
    consumer_path.write_text(
        json.dumps(consumer, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    bundle_path = root / "lesson.private.json"
    bundle = {
        "validation_status": s07.m5.STATUS,
        "source_consumer_sha256": s07.m6.sha(consumer_path.read_bytes()),
        "lesson": {
            "lesson_id": BASE_LESSON,
            "skill": "READING",
            "level": "A1",
        },
        "assets": [{"asset_key": BASE_ASSET}],
    }
    bundle_path.write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return consumer_path, {BASE_LESSON: str(bundle_path)}


def _insert_contract(
    connection: sqlite3.Connection,
    *,
    asset_key: str,
    lesson_id: str,
    contract: dict,
    capture_enabled: int,
) -> None:
    connection.execute(
        "INSERT INTO response_contracts VALUES(?,?,?,?,?,?,?)",
        (
            asset_key,
            lesson_id,
            str(contract["skill"]),
            str(contract["role"]),
            s07.m6.canonical(contract),
            s07.m6.sha(contract),
            capture_enabled,
        ),
    )


def _build_s09_superset_database(path: Path, consumer: dict) -> None:
    baseline_asset = consumer["asset_records"][0]
    baseline_contract = s07.m6.derive_contract(baseline_asset)
    with sqlite3.connect(path) as connection:
        connection.executescript(s07.m3.SCHEMA_SQL)
        connection.executescript(s07.m6.SQL)
        metadata = {
            "task_id": s07.m3.TASK_ID,
            "schema_version": s07.m3.SCHEMA_VERSION,
            "validation_status": s07.m3.STATUS,
            "consumer_sha256": "preexisting-s09-consumer",
            "mastery_write_enabled": "false",
            "a2_session_enabled": "false",
            "learner_release_approved": "false",
            "s09_task_id": runner.S09_TASK_ID,
            "s09_schema_version": runner.S09_SCHEMA_VERSION,
            "s09_validation_status": runner.S09_PASS_STATUS,
            "s09_populated_unit_count": str(runner.S09_UNIT_COUNT),
            "s09_nonaudio_item_count": str(runner.S09_ASSET_COUNT),
        }
        connection.executemany(
            "INSERT INTO metadata(key,value) VALUES(?,?)",
            metadata.items(),
        )

        baseline_lesson = consumer["lesson_catalog"][0]
        connection.execute(
            "INSERT INTO lesson_catalog VALUES(?,?,?,?,?,?,?)",
            (
                baseline_lesson["lesson_id"],
                baseline_lesson["lesson_node_id"],
                baseline_lesson["skill"],
                baseline_lesson["level"],
                s07.canonical(sorted(baseline_lesson["roles"])),
                s07.canonical(sorted(baseline_lesson["requirement_node_ids"])),
                1,
            ),
        )
        connection.execute(
            "INSERT INTO lesson_assets VALUES(?,?,?,?,?)",
            (
                baseline_asset["asset_key"],
                baseline_asset["asset_id"],
                baseline_asset["lesson_id"],
                baseline_asset["role"],
                baseline_asset["content_digest"],
            ),
        )
        _insert_contract(
            connection,
            asset_key=BASE_ASSET,
            lesson_id=BASE_LESSON,
            contract=baseline_contract,
            capture_enabled=1,
        )

        extra_lessons: list[str] = []
        for index in range(1, runner.S09_LESSON_COUNT):
            lesson_id = f"A1FS_ONLINE_V1:GRAMMAR_EXTRA_{index:02d}:READING"
            extra_lessons.append(lesson_id)
            connection.execute(
                "INSERT INTO lesson_catalog VALUES(?,?,?,?,?,?,?)",
                (
                    lesson_id,
                    f"RUNTIME_PROJECTION:READING:GRAMMAR_EXTRA_{index:02d}",
                    "READING",
                    "A1",
                    '["CHK"]',
                    f'["EGP_EXTRA_{index:02d}"]',
                    1,
                ),
            )

        for index in range(1, runner.S09_ASSET_COUNT):
            lesson_id = extra_lessons[(index - 1) % len(extra_lessons)]
            asset_key = f"E4S_A1V1_ITEM:EXTRA:{index:03d}"
            connection.execute(
                "INSERT INTO lesson_assets VALUES(?,?,?,?,?)",
                (
                    asset_key,
                    f"ASSET:EXTRA:{index:03d}",
                    lesson_id,
                    "CHK",
                    f"{index:064x}",
                ),
            )
            contract = {
                "asset_key": asset_key,
                "lesson_id": lesson_id,
                "skill": "READING",
                "role": "CHK",
                "prompt": f"Extra prompt {index}",
                "capture_enabled": index < runner.S09_CAPTURE_ENABLED_COUNT,
                "response_type": "string",
                "scoring_mode": "NORMALIZED_TEXT",
                "accepted_texts": [f"extra-{index}"],
                "accepted_sequence": [],
                "case_insensitive": True,
                "punctuation_tolerance": True,
                "human_review_fallback": False,
                "rubric": {},
                "m12_item_id": f"M12:EXTRA:{index}",
                "m12_session_bank_sha256": None,
            }
            _insert_contract(
                connection,
                asset_key=asset_key,
                lesson_id=lesson_id,
                contract=contract,
                capture_enabled=int(contract["capture_enabled"]),
            )
        connection.commit()


def test_s07_reentry_preserves_authorized_s09_superset(tmp_path: Path) -> None:
    consumer = _consumer()
    consumer_path, bundle_paths = _write_consumer_and_bundle(tmp_path, consumer)
    source = tmp_path / "source.sqlite3"
    target = tmp_path / "target.sqlite3"
    _build_s09_superset_database(source, consumer)

    downstream_before = runner._snapshot_downstream_rows(source, consumer)
    counts = runner._reentrant_migrate_clone(
        source_database=source,
        target_database=target,
        consumer_path=consumer_path,
        consumer=consumer,
        bundle_paths=bundle_paths,
    )

    assert counts["lesson_count"] == 1
    assert counts["asset_count"] == 1
    assert counts["response_contract_count"] == 1
    assert counts["capture_enabled_contract_count"] == 1
    assert counts["authorized_s09_superset"] == 1
    assert counts["preserved_downstream_lesson_count"] == 71
    assert counts["preserved_downstream_asset_count"] == 263
    assert counts["preserved_downstream_response_contract_count"] == 263

    actual = runner._actual_database_counts(target)
    assert actual["lesson_count"] == 72
    assert actual["asset_count"] == 264
    assert actual["response_contract_count"] == 264
    assert actual["capture_enabled_contract_count"] == 192
    assert runner._snapshot_downstream_rows(target, consumer) == downstream_before
    state = runner._validate_runtime_baseline(target, consumer, require_complete=True)
    assert state["authorized_s09_superset"] is True


def test_s07_reentry_rejects_extra_rows_without_s09_authority(tmp_path: Path) -> None:
    consumer = _consumer()
    source = tmp_path / "unauthorized.sqlite3"
    _build_s09_superset_database(source, consumer)
    with sqlite3.connect(source) as connection:
        connection.execute("DELETE FROM metadata WHERE key LIKE 's09_%'")
        connection.commit()

    with pytest.raises(
        s07.MultiUnitExpansionError,
        match="unexpected_existing_runtime_row_without_s09_authority",
    ):
        runner._validate_runtime_baseline(source, consumer, require_complete=False)


def test_s07_reentry_rejects_baseline_contract_drift(tmp_path: Path) -> None:
    consumer = _consumer()
    source = tmp_path / "drift.sqlite3"
    _build_s09_superset_database(source, consumer)
    with sqlite3.connect(source) as connection:
        connection.execute(
            "UPDATE lesson_assets SET content_digest=? WHERE asset_key=?",
            ("f" * 64, BASE_ASSET),
        )
        connection.commit()

    with pytest.raises(
        s07.MultiUnitExpansionError,
        match="existing_asset_contract_drift",
    ):
        runner._validate_runtime_baseline(source, consumer, require_complete=True)
