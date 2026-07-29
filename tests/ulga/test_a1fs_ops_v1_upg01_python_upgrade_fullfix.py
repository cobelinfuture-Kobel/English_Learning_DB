from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from tests.ulga.test_a1fs_online_v1_2_u01e_s01_unit01_five_context_authority_admission import (
    database,
)
from ulga.builders import (
    build_a1fs_ops_v1_upg01_python_upgrade_fullfix as fix,
)


def _add_residual_u01e_contracts(path: Path) -> None:
    lesson_ids = list(fix.s01.m01.LESSON_IDS.values())
    skills = ["READING", "WRITING", "SPEAKING"]
    rows = []
    for index in range(fix.MAX_GOVERNED_RESIDUAL_CONTRACT_COUNT):
        key = f"{fix.RESIDUAL_CONTRACT_PREFIX}{index + 1:02d}"
        lesson_index = index % len(lesson_ids)
        contract = {
            "scoring_mode": "EXACT_OPTION",
            "response_type": "string",
            "accepted_texts": ["residual"],
            "accepted_sequence": [],
        }
        rows.append(
            (
                key,
                lesson_ids[lesson_index],
                skills[lesson_index],
                "PRD",
                1,
                json.dumps(contract),
                f"digest:{key}",
            )
        )
    with sqlite3.connect(path) as connection:
        connection.executemany(
            "INSERT INTO response_contracts VALUES(?,?,?,?,?,?,?)",
            rows,
        )
        connection.commit()


def test_residual_v12_contracts_are_preserved_but_excluded_from_s01_legacy_intake(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = database(tmp_path / "learner.sqlite3")
    _add_residual_u01e_contracts(path)
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM response_contracts").fetchone()[0] == 24

    original_load = fix.s01.load_contracts
    original_stop = fix.runtime.core.r01.stop
    monkeypatch.setattr(fix.s01, "load_contracts", original_load)
    monkeypatch.setattr(fix.runtime.core.r01, "stop", original_stop)
    fix.activate()

    assets, contracts = fix.s01.load_contracts(path)
    candidate = fix.s01.build_candidate(path)

    assert len(assets) == fix.s01.EXPECTED_EXISTING_ASSET_COUNT == 11
    assert len(contracts) == 11
    assert all(
        not row["asset_key"].startswith(fix.RESIDUAL_CONTRACT_PREFIX)
        for row in assets
    )
    assert len(candidate["payload"]["existing_asset_target_index"]) == 11
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM response_contracts").fetchone()[0] == 24
        assert connection.execute(
            "SELECT COUNT(*) FROM response_contracts WHERE asset_key LIKE ?",
            (fix.RESIDUAL_CONTRACT_PREFIX + "%",),
        ).fetchone()[0] == 13


def test_unexpected_legacy_or_excess_residual_counts_fail_closed(tmp_path: Path) -> None:
    path = database(tmp_path / "learner.sqlite3")
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT INTO response_contracts VALUES(?,?,?,?,?,?,?)",
            (
                "UNEXPECTED-UNIT01-ASSET",
                fix.s01.m01.LESSON_IDS["READING"],
                "READING",
                "PRD",
                1,
                json.dumps({"accepted_texts": ["x"]}),
                "digest:unexpected",
            ),
        )
        connection.commit()
    with pytest.raises(
        fix.s01.S01AdmissionError,
        match="unit01_legacy_response_contract_count_invalid:12",
    ):
        fix.load_legacy_unit01_contracts(path)


def test_python_entry_metadata_and_upgrade_activation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        fix.runtime,
        "build_plan",
        lambda **_kwargs: {"validation_status": fix.PLAN_PASS_STATUS},
    )
    plan = fix.build_plan()
    assert plan["operator_entry"] == "PYTHON_ONLY"
    assert plan["powershell_required"] is False
    assert plan["residual_u01e_contract_compatibility"] == {
        "enabled": True,
        "legacy_contract_count": 11,
        "governed_residual_prefix": fix.RESIDUAL_CONTRACT_PREFIX,
        "residual_rows_deleted": False,
        "legacy_denominator_relaxed": False,
    }

    calls: list[str] = []
    monkeypatch.setattr(fix, "activate", lambda: calls.append("activate"))
    monkeypatch.setattr(
        fix.runtime,
        "upgrade",
        lambda **_kwargs: calls.append("upgrade")
        or {"validation_status": fix.PASS_STATUS},
    )
    result = fix.upgrade()
    assert calls == ["activate", "upgrade"]
    assert result["operator_entry"] == "PYTHON_ONLY"
    assert result["powershell_required"] is False


def test_operator_entry_is_direct_python_without_powershell_or_subprocess() -> None:
    repository = Path(__file__).resolve().parents[2]
    script = repository / "scripts" / "UPGRADE_A1FS.py"
    text = script.read_text(encoding="utf-8")
    lowered = text.casefold()
    assert "build_a1fs_ops_v1_upg01_python_upgrade_fullfix" in text
    assert "subprocess" not in lowered
    assert ".ps1" not in lowered
    assert "powershell" not in lowered
    assert "--plan-only" in text
    assert "runner.upgrade" in text
