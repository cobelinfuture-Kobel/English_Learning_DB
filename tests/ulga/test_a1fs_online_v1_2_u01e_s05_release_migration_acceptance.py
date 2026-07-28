from __future__ import annotations

import sqlite3
from pathlib import Path

from tests.ulga._a1fs_online_v1_2_u01e_s05_release_migration_acceptance_core import *  # noqa: F401,F403
from ulga.builders import build_a1fs_online_v1_s05_private_learner_identity_progress_persistence as v1_s05


def test_real_runtime_login_scored_journeys_coverage_and_rollback(tmp_path: Path) -> None:
    root = source_v111_root(tmp_path)
    with sqlite3.connect(root / "shared/database/learner_runtime.sqlite3") as connection:
        connection.executescript(v1_s05.PERSISTENCE_SQL)
        connection.commit()
    receipt, safe = builder.materialize(
        product_root=root,
        code_root=Path(__file__).resolve().parents[2],
        output_path=tmp_path / "real/out/s05.private.json",
        report_path=tmp_path / "real/out/s05.safe.json",
    )
    report = validator.validate_outputs(receipt, safe)
    assert report["error_count"] == 0, report
    acceptance = receipt["acceptance_summary"]
    assert acceptance["reading"]["contract_count"] == 10
    assert acceptance["reading"]["session_completed"] is True
    assert acceptance["writing"]["contract_count"] == 8
    assert acceptance["writing"]["session_completed"] is True
    assert acceptance["speaking_practice_card_count"] == 6
    assert acceptance["coverage_before_practised_item_count"] == 0
    assert acceptance["coverage_after_practised_item_count"] == 18
    assert acceptance["http"] == {
        "authenticated_login_pass": True,
        "bootstrap_pass": True,
        "progress_pass": True,
        "coverage_endpoint_pass": True,
        "unit_count": 24,
        "unit01_activity_count": 24,
        "practised_item_count": 18,
    }
    assert acceptance["visual"]["dom_contract_pass"] is True
    assert acceptance["visual"]["status"] in {
        "PASS_HEADLESS_CHROMIUM_SCREENSHOT",
        "NOT_AVAILABLE_IN_EXECUTION_ENVIRONMENT",
    }
    assert acceptance["rollback"]["v1_1_version_loaded"] is True
    assert acceptance["rollback"]["post_migration_database_readable"] is True
    assert acceptance["rollback"]["forward_switch_back_to_v1_2_pass"] is True
    assert receipt["recovery_summary"]["failed_update_automatic_rollback_pass"] is True
    assert receipt["production_safety"] == {
        "production_current_version_unchanged": True,
        "production_shared_state_unchanged": True,
        "production_legacy_rows_unchanged": True,
        "source_database_mutated": False,
        "existing_11_asset_identities_changed": False,
        "other_69_lessons_changed": False,
    }
