from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from ulga.builders import build_a1fs_online_v1_s05_private_learner_identity_progress_persistence as s05
from ulga.validators import validate_a1fs_online_v1_s05_private_learner_identity_progress_persistence as validator


def _asset(index: int, *, skill: str) -> dict:
    asset_key = f"S03:{skill}:BASELINE_{index:02d}"
    return {
        "asset_key": asset_key,
        "lesson_id": f"A1FS_ONLINE_V1:GRAMMAR_ARTICLES_BASIC:{skill}",
        "skill": skill,
        "role": "PRD",
        "payload": {
            "prompt": f"Complete baseline item {index}.",
            "response_capture_enabled": skill != "SPEAKING",
            "answer_contract": {
                "scoring_mode": "NORMALIZED_TEXT",
                "accepted_texts": [f"answer-{index}"],
                "case_insensitive": True,
                "punctuation_tolerance": True,
            },
        },
    }


def _write_contract(connection: sqlite3.Connection, asset: dict) -> None:
    contract = s05.m6.derive_contract(asset)
    connection.execute(
        "INSERT INTO response_contracts VALUES(?,?,?,?,?,?,?)",
        (
            contract["asset_key"],
            contract["lesson_id"],
            contract["skill"],
            contract["role"],
            s05.m6.canonical(contract),
            s05.m6.sha(contract),
            int(contract["capture_enabled"]),
        ),
    )


def _fixture(tmp_path: Path) -> tuple[Path, Path, list[dict]]:
    assets = [
        *[_asset(index, skill="READING") for index in range(1, 5)],
        *[_asset(index, skill="WRITING") for index in range(5, 9)],
        *[_asset(index, skill="SPEAKING") for index in range(9, 12)],
    ]
    consumer_path = tmp_path / "unified_runtime_consumer.private.json"
    consumer_path.write_text(
        json.dumps({"asset_records": assets}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    database_path = tmp_path / "learner_progress.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.executescript(s05.m6.SQL)
        for asset in assets:
            _write_contract(connection, asset)
        _write_contract(
            connection,
            {
                "asset_key": "S07:READING:DOWNSTREAM_EXTRA",
                "lesson_id": "A1FS_ONLINE_V1:GRAMMAR_REGULAR_PLURAL_NOUNS:READING",
                "skill": "READING",
                "role": "PRD",
                "payload": {
                    "prompt": "Complete the downstream item.",
                    "response_capture_enabled": True,
                    "answer_contract": {
                        "scoring_mode": "NORMALIZED_TEXT",
                        "accepted_texts": ["books"],
                    },
                },
            },
        )
        connection.commit()
    return database_path, consumer_path, assets


def test_s05_accepts_downstream_expansion_when_all_baseline_contracts_are_preserved(
    tmp_path: Path,
) -> None:
    database_path, consumer_path, _ = _fixture(tmp_path)
    result = validator._baseline_response_contract_readback(
        database_path=database_path,
        consumer_path=consumer_path,
    )
    assert result["errors"] == []
    assert result["baseline_response_contract_count"] == 11
    assert result["total_response_contract_count"] == 12
    assert result["downstream_response_contract_count"] == 1


def test_s05_still_fails_closed_when_a_baseline_contract_drifts(tmp_path: Path) -> None:
    database_path, consumer_path, assets = _fixture(tmp_path)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "UPDATE response_contracts SET contract_digest=? WHERE asset_key=?",
            ("0" * 64, assets[0]["asset_key"]),
        )
        connection.commit()
    result = validator._baseline_response_contract_readback(
        database_path=database_path,
        consumer_path=consumer_path,
    )
    assert result["errors"] == [
        f"s05_baseline_response_contract_drift:{assets[0]['asset_key']}"
    ]
