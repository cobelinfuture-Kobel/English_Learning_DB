from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from tests.ulga import (
    _a1fs_online_v1_2_u01e_s05_release_migration_acceptance_core as fixture,
)
from ulga.builders import (
    build_a1fs_ops_v1_upg01_python_upgrade_fullfix_residual_canonical_rebase as fix,
)


def _migration_fixture(tmp_path: Path) -> tuple[Path, dict, Path]:
    root = fixture.source_v111_root(tmp_path)
    source = fix.s05.source_product(root)
    overlay = fix.s05.build_runtime_overlay(source)
    manifest = fix.s05.r01.validate_release(
        root / f"releases/{fix.s05.SOURCE_VERSION}"
    )
    graph = fix.s05.r01._resolve(root, str(manifest["graph_path"]))
    database = root / "shared/database/learner_runtime.sqlite3"
    fix.replay_safe_migrate_database(
        database_path=database,
        overlay=overlay,
        m1_graph_path=graph,
    )
    return database, overlay, graph


def _expected_asset(overlay: dict, key: str) -> tuple:
    row = next(item for item in overlay["assets"] if item["asset_key"] == key)
    return (
        row["asset_key"],
        row["asset_id"],
        row["lesson_id"],
        row["role"],
        row["content_digest"],
    )


def _expected_contract(overlay: dict, key: str) -> tuple:
    row = next(item for item in overlay["contracts"] if item["asset_key"] == key)
    return (
        row["asset_key"],
        row["lesson_id"],
        row["skill"],
        row["role"],
        row["contract_digest"],
        fix.s05._core.canonical(row["contract"]),
        int(bool(row["capture_enabled"])),
    )


def test_real_residual_digest_and_contract_drift_rebases_to_current_overlay(
    tmp_path: Path,
) -> None:
    database, overlay, graph = _migration_fixture(tmp_path)
    key = str(overlay["assets"][0]["asset_key"])
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE lesson_assets SET role='OLD_ROLE',content_digest='old-approved-sha-digest' "
            "WHERE asset_key=?",
            (key,),
        )
        connection.execute(
            "UPDATE response_contracts SET role='OLD_ROLE',contract_digest=?,"
            "contract_json=?,capture_enabled=0 WHERE asset_key=?",
            ("old-contract", '{"old":true}', key),
        )
        connection.commit()

    result = fix.replay_safe_migrate_database(
        database_path=database,
        overlay=overlay,
        m1_graph_path=graph,
    )

    with sqlite3.connect(database) as connection:
        asset = connection.execute(
            "SELECT asset_key,asset_id,lesson_id,role,content_digest "
            "FROM lesson_assets WHERE asset_key=?",
            (key,),
        ).fetchone()
        contract = connection.execute(
            "SELECT asset_key,lesson_id,skill,role,contract_digest,contract_json,"
            "capture_enabled FROM response_contracts WHERE asset_key=?",
            (key,),
        ).fetchone()
    assert tuple(asset) == _expected_asset(overlay, key)
    assert tuple(contract) == _expected_contract(overlay, key)
    assert result["migration_replay_mode"] == "RESIDUAL_CANONICAL_REBASE"
    assert result["lesson_asset_rows_rebased_to_canonical"] == 1
    assert result["response_contract_rows_rebased_to_canonical"] == 1
    assert result["residual_rows_deleted"] is False


def test_residual_rebase_fails_closed_when_learner_attempt_exists(
    tmp_path: Path,
) -> None:
    database, overlay, graph = _migration_fixture(tmp_path)
    key = str(overlay["assets"][0]["asset_key"])
    lesson_id = str(overlay["assets"][0]["lesson_id"])
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE lesson_assets SET content_digest='drift' WHERE asset_key=?",
            (key,),
        )
        connection.execute(
            "INSERT INTO response_attempts("
            "attempt_id,learner_id,session_id,lesson_id,asset_key,attempt_sequence,"
            "response_json,submitted_at,previous_hash,attempt_hash"
            ") VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                "ATTEMPT:RESIDUAL:001",
                "LEARNER:RESIDUAL",
                "SESSION:RESIDUAL",
                lesson_id,
                key,
                1,
                "{}",
                "2026-07-29T00:00:00Z",
                "GENESIS",
                "attempt-hash-residual-001",
            ),
        )
        connection.commit()

    with pytest.raises(
        fix.PythonUpgradeFullFixError,
        match=f"migration_residual_identity_has_learner_attempts:lesson_assets:{key}",
    ):
        fix.replay_safe_migrate_database(
            database_path=database,
            overlay=overlay,
            m1_graph_path=graph,
        )


def test_residual_rebase_fails_closed_on_stable_identity_drift(
    tmp_path: Path,
) -> None:
    database, overlay, graph = _migration_fixture(tmp_path)
    key = str(overlay["assets"][0]["asset_key"])
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE lesson_assets SET asset_id='DIFFERENT-ASSET-ID',content_digest='drift' "
            "WHERE asset_key=?",
            (key,),
        )
        connection.commit()

    with pytest.raises(
        fix.PythonUpgradeFullFixError,
        match=f"migration_stable_identity_conflict:lesson_assets:{key}",
    ):
        fix.replay_safe_migrate_database(
            database_path=database,
            overlay=overlay,
            m1_graph_path=graph,
        )


def test_python_operator_routes_through_canonical_rebase_adapter() -> None:
    repository = Path(__file__).resolve().parents[2]
    text = (repository / "scripts/UPGRADE_A1FS.py").read_text(encoding="utf-8")
    assert (
        "build_a1fs_ops_v1_upg01_python_upgrade_fullfix_"
        "residual_canonical_rebase"
    ) in text
    assert ".ps1" not in text.casefold()
    assert "subprocess" not in text.casefold()
