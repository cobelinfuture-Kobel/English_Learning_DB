from __future__ import annotations

import importlib.util
import sqlite3
from pathlib import Path

import pytest

from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.builders import (
    build_a1fs_ops_v1_unit01_identity_scoped_fair_question_selection as fair,
)
from ulga.builders import (
    build_a1fs_v1_razq01e_unit01_approved_content_existing_qb_learner_stimulus_runtime
    as extension_runtime,
)
from ulga.validators import (
    validate_a1fs_ops_v1_unit01_identity_scoped_fair_question_selection as validator,
)


def load_fixture():
    path = Path(__file__).with_name(
        "test_a1fs_v1_razq01f_unit01_multisession_reconciliation_ci.py"
    )
    spec = importlib.util.spec_from_file_location("_identity_fair_fixture", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def start_and_plan(
    *,
    database: Path,
    runtime,
    learner_id: str,
    skill: str,
    session_id: str,
    at: str,
    selection_mode: str | None = None,
) -> dict:
    session = m3.LearnerStateStore(database).start_session(
        learner_id=learner_id,
        lesson_id=extension_runtime.qb02.UNIT01_LESSONS[skill],
        session_id=session_id,
        at=at,
    )
    plan = runtime.assemble_session(
        learner_id=learner_id,
        session_id=session_id,
        selected_at=at,
        selection_mode=selection_mode,
    )
    m3.LearnerStateStore(database).end_session(
        session_id=session_id,
        outcome="COMPLETED",
        expected_session_version=session["session_version"],
        at=at,
    )
    return plan


def family_ranks(plan: dict) -> list[int]:
    return [
        fair._pedagogical_rank(plan["skill"], row["pattern_family_id"])
        for row in plan["items"]
    ]


def test_unit01_identity_scoped_fair_selection_tracks_login_and_guest_history(
    tmp_path: Path,
) -> None:
    fixture = load_fixture()
    database = tmp_path / "learner_progress.sqlite3"
    fixture.setup_database(database)
    approved_content = fixture.approved_real44()
    fair.install_fullfix()
    _candidate, approved_extension, _safe = (
        extension_runtime.build_extension_package(approved_content)
    )
    materialized = extension_runtime.materialize_runtime(database, approved_extension)
    assert materialized["combined_runtime_item_count"] == 474

    runtime = extension_runtime.qb02.Unit01ApprovedVariantSessionRuntime(database)
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM u01qb02_item_catalog"
        ).fetchone()[0] == 474
        assert connection.execute(
            """SELECT 1 FROM sqlite_master
            WHERE type='table' AND name='u01qb02_identity_scopes'"""
        ).fetchone()

    authenticated = fair.bind_authenticated_identity(
        runtime,
        learner_id="identity-auth-learner",
        subject_key="AUTH-SUBJECT-2026-UNIT01-LEARNER-001",
        display_label="Authenticated learner",
        at="2026-07-31T10:00:00Z",
    )
    authenticated_relogin = fair.bind_authenticated_identity(
        runtime,
        learner_id="identity-auth-learner",
        subject_key="AUTH-SUBJECT-2026-UNIT01-LEARNER-001",
        display_label="Authenticated learner",
        at="2026-07-31T11:00:00Z",
    )
    assert authenticated_relogin["identity_reused"] is True
    assert authenticated_relogin["learner_id"] == authenticated["learner_id"]

    auth_plans = []
    for index in range(1, 4):
        auth_plans.append(
            start_and_plan(
                database=database,
                runtime=runtime,
                learner_id=authenticated["learner_id"],
                skill="WRITING",
                session_id=f"identity-fair-auth-{index}",
                at=f"2026-07-31T1{index}:10:00Z",
                selection_mode="FRESH",
            )
        )
    auth_sets = [{row["item_id"] for row in plan["items"]} for plan in auth_plans]
    assert len(set.union(*auth_sets)) == 30
    assert all(family_ranks(plan) == sorted(family_ranks(plan)) for plan in auth_plans)
    assert all(plan["phrase_before_sentence_order"] is True for plan in auth_plans)

    guest_token = "GUEST-TOKEN-UNIT01-CURRENT-LOGIN-20260731-A"
    guest = fair.open_guest_identity(
        runtime,
        guest_token=guest_token,
        display_label="Guest learner",
        at="2026-07-31T14:00:00Z",
    )
    guest_reuse = fair.open_guest_identity(
        runtime,
        guest_token=guest_token,
        at="2026-07-31T14:05:00Z",
    )
    assert guest_reuse["identity_reused"] is True
    assert guest_reuse["learner_id"] == guest["learner_id"]

    guest_first = start_and_plan(
        database=database,
        runtime=runtime,
        learner_id=guest["learner_id"],
        skill="READING",
        session_id="identity-fair-guest-a-1",
        at="2026-07-31T14:10:00Z",
    )
    guest_second = start_and_plan(
        database=database,
        runtime=runtime,
        learner_id=guest["learner_id"],
        skill="READING",
        session_id="identity-fair-guest-a-2",
        at="2026-07-31T14:20:00Z",
    )
    first_ids = {row["item_id"] for row in guest_first["items"]}
    second_ids = {row["item_id"] for row in guest_second["items"]}
    assert not first_ids.intersection(second_ids)
    assert guest_first["selection_mode"] == "FRESH"
    assert guest_second["selection_mode"] == "FRESH"
    assert all(
        row["selection_reason"] == "NEW_OR_UNSEEN"
        for row in guest_second["items"]
    )

    guest_readback = fair.fairness_readback(
        database, learner_id=guest["learner_id"], skill="READING"
    )
    assert guest_readback["distinct_planned_item_count"] == 20
    assert guest_readback["unplanned_item_count"] == 208

    closed = fair.close_guest_identity(
        runtime,
        scope_id=guest["scope_id"],
        at="2026-07-31T14:30:00Z",
    )
    assert closed["closed"] is True
    with pytest.raises(fair.IdentityFairSelectionError, match="new_token_required"):
        fair.open_guest_identity(
            runtime,
            guest_token=guest_token,
            at="2026-07-31T14:31:00Z",
        )
    m3.LearnerStateStore(database).start_session(
        learner_id=guest["learner_id"],
        lesson_id=extension_runtime.qb02.UNIT01_LESSONS["READING"],
        session_id="identity-fair-guest-a-closed",
        at="2026-07-31T14:32:00Z",
    )
    with pytest.raises(fair.IdentityFairSelectionError, match="guest_scope_not_active"):
        runtime.assemble_session(
            learner_id=guest["learner_id"],
            session_id="identity-fair-guest-a-closed",
            selected_at="2026-07-31T14:32:00Z",
        )

    second_guest_token = "GUEST-TOKEN-UNIT01-NEW-LOGIN-20260731-B"
    second_guest = fair.open_guest_identity(
        runtime,
        guest_token=second_guest_token,
        at="2026-07-31T15:00:00Z",
    )
    assert second_guest["learner_id"] != guest["learner_id"]
    before = fair.fairness_readback(
        database, learner_id=second_guest["learner_id"], skill="READING"
    )
    assert before["distinct_planned_item_count"] == 0
    second_guest_plan = start_and_plan(
        database=database,
        runtime=runtime,
        learner_id=second_guest["learner_id"],
        skill="READING",
        session_id="identity-fair-guest-b-1",
        at="2026-07-31T15:10:00Z",
    )
    assert second_guest_plan["item_count"] == 10

    result = validator.validate(
        database,
        expected_runtime_items=474,
        session_prefix="identity-fair-",
        forbidden_subject_values=(guest_token, second_guest_token),
    )
    assert result["validation_status"] == validator.PASS_STATUS
    assert result["error_count"] == 0, result["errors"]
    assert result["runtime_item_count"] == 474
    assert result["authenticated_scope_count"] == 1
    assert result["guest_scope_count"] == 2
    assert result["closed_guest_scope_count"] == 1
    assert result["raw_guest_token_persisted"] is False
    assert result["phrase_before_sentence_order"] is True
    assert result["parallel_question_bank_created"] is False
    assert result["parallel_selector_created"] is False

    with sqlite3.connect(database) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                """SELECT name FROM sqlite_master
                WHERE type='table' AND name LIKE 'u01qb02_identity_%'"""
            )
        }
    assert tables == {"u01qb02_identity_scopes"}
