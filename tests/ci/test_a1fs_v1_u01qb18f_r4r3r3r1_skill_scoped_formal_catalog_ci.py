from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from product import a1fs_v1_2_1 as product_package  # noqa: F401
from ulga.builders import _u01qb18f_r4r3r3_formal_learner_visible_donor_admission_fullfix as r4r3r3
from ulga.builders import _u01qb18f_r4r3r3r1_skill_scoped_formal_catalog_adapter as r4r3r3r1


def _runtime_db(path: Path) -> Path:
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE u01qb02_item_catalog(
              item_id TEXT PRIMARY KEY,
              lesson_id TEXT NOT NULL,
              capture_enabled INTEGER NOT NULL,
              asset_key TEXT NOT NULL
            );
            CREATE TABLE response_contracts(
              asset_key TEXT PRIMARY KEY,
              contract_json TEXT NOT NULL
            );
            """
        )
        rows = [
            ("R-1", "A1FS_ONLINE_V1:GRAMMAR_ARTICLES_BASIC:READING", 1, "ASSET-R"),
            ("W-1", "A1FS_ONLINE_V1:GRAMMAR_ARTICLES_BASIC:WRITING", 1, "ASSET-W"),
            ("S-1", "A1FS_ONLINE_V1:GRAMMAR_ARTICLES_BASIC:SPEAKING", 0, "ASSET-S"),
        ]
        connection.executemany(
            "INSERT INTO u01qb02_item_catalog VALUES(?,?,?,?)",
            rows,
        )
        connection.executemany(
            "INSERT INTO response_contracts VALUES(?,?)",
            [
                ("ASSET-R", json.dumps({"scoring_mode": "EXACT"})),
                ("ASSET-W", json.dumps({"scoring_mode": "FEATURE_RUBRIC"})),
                ("ASSET-S", json.dumps({"scoring_mode": ""})),
            ],
        )
    return path


def test_skill_scoped_runtime_state_accepts_three_unit01_skill_lessons(tmp_path: Path) -> None:
    database = _runtime_db(tmp_path / "runtime.sqlite3")
    catalogs, scoring = r4r3r3r1._skill_scoped_formal_runtime_state(database)
    assert sorted(catalogs) == ["READING", "SPEAKING", "WRITING"]
    assert [row["item_id"] for row in catalogs["READING"]] == ["R-1"]
    assert [row["item_id"] for row in catalogs["WRITING"]] == ["W-1"]
    assert [row["item_id"] for row in catalogs["SPEAKING"]] == ["S-1"]
    assert scoring["READING"]["R-1"] == "AUTO"
    assert scoring["WRITING"]["W-1"] == "HUMAN_REVIEW"
    assert scoring["SPEAKING"]["S-1"] == "PRACTICE_ONLY"


def test_formal_pair_routes_reading_and_writing_to_their_own_catalogs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[tuple[str, tuple[str, ...]]] = []
    monkeypatch.setattr(
        r4r3r3,
        "_effective_reading_rows",
        lambda *args, **kwargs: [{"activity_id": "READ"}],
    )

    def formal_assignment(_activities, *, catalog, scoring, form_ordinal, skill):
        seen.append((skill, tuple(str(row["item_id"]) for row in catalog)))
        return True

    def writing_form(_all_rows, *, form_ordinal, catalog, scoring):
        seen.append(("WRITING", tuple(str(row["item_id"]) for row in catalog)))
        return True

    monkeypatch.setattr(r4r3r3, "_formal_assignment_exists", formal_assignment)
    monkeypatch.setattr(r4r3r3, "_writing_form_exists", writing_form)
    assert r4r3r3r1._skill_scoped_formal_pair_passes(
        simulated=[],
        current_form=8,
        donor_form=12,
        current_choices={"READING": {}, "WRITING": {}, "SPEAKING": {}},
        donor_choices={"READING": {}, "WRITING": {}, "SPEAKING": {}},
        catalog={
            "READING": [{"item_id": "R-ONLY"}],
            "WRITING": [{"item_id": "W-ONLY"}],
        },
        scoring={"READING": {}, "WRITING": {}},
    ) is True
    assert seen == [
        ("READING", ("R-ONLY",)),
        ("READING", ("R-ONLY",)),
        ("WRITING", ("W-ONLY",)),
        ("WRITING", ("W-ONLY",)),
    ]


def test_r4r3r3r1_is_installed_as_private_probe_extension() -> None:
    assert r4r3r3r1.installed() is True
    assert r4r3r3._formal_runtime_state is r4r3r3r1._skill_scoped_formal_runtime_state
    assert r4r3r3._formal_pair_passes is r4r3r3r1._skill_scoped_formal_pair_passes
    assert r4r3r3.installed() is True


def test_r4r3r3r1_scope_is_non_content_producer() -> None:
    assert r4r3r3r1.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert "authors no content" in r4r3r3r1.A1FS_CONTENT_POLICY_EXEMPTION
    assert r4r3r3r1.NEXT_SHORT_STEP == r4r3r3.NEXT_SHORT_STEP
