from __future__ import annotations

import json
from pathlib import Path

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import build_a1fs_v1_u01qb15_actual_real62_fresh474_r2_private_acceptance_runner as runner


def _approved_fixture() -> dict:
    candidate = policy_artifact.build_candidate(
        payload={"content_assets": []},
        producer_id="test-real62-candidate",
        level_scope=["A1"],
        source_bindings={"test_fixture": True},
    )
    return policy_artifact.admit_candidate(
        candidate,
        validation_receipts=[
            {
                "validator_id": "test-real62-validator",
                "status": "PASS",
                "receipt_sha256": "0" * 64,
            }
        ],
        decision_ref="TEST:REAL62",
        producer_id="test-real62-approved",
    )


def test_actual_real62_acceptance_runner_uses_canonical_artifact_identity_not_raw_file_sha(
    tmp_path: Path, monkeypatch
) -> None:
    real62 = tmp_path / "real62.private.json"
    approved_fixture = _approved_fixture()
    real62.write_text(
        json.dumps(approved_fixture, ensure_ascii=False, indent=4) + "\n\n",
        encoding="utf-8",
    )
    expected_artifact_sha = approved_fixture["artifact_sha256"]
    raw_file_sha = runner.file_sha256(real62)
    assert raw_file_sha != expected_artifact_sha
    calls: list[str] = []

    def fake_bootstrap(database: Path, approved_content):
        calls.append("bootstrap")
        assert approved_content["artifact_sha256"] == expected_artifact_sha
        database.write_bytes(b"fresh-474")
        return {
            "status": "PASS_FRESH_ACTUAL_REAL62_474_BASELINE",
            "base_item_count": 288,
            "extension_item_count": 186,
            "runtime_item_count": 474,
        }

    def fake_migrate(database: Path, paths):
        calls.append("migrate")
        migration = {
            "base_item_count": 288,
            "extension_item_count": 186,
            "runtime_item_count": 474,
            "real62_extension_modified": False,
            "per_scene_runtime_capacity": {
                "all_36_skill_sessions_distinct_item_capacity_proven": True,
                "verified_activity_count": 240,
                "runtime_capacity_reuse_excluded_scene_refs": ["U01-C3-PICNIC-FOOD"],
                "runtime_capacity_reuse_selected_scene_count": 17,
                "runtime_bindable_scene_count": 31,
                "deferred_scene_refs": ["U01-MA-FOOD-04"],
            },
        }
        approved = {"artifact_sha256": "2" * 64}
        runner.write_json(paths["migration"], migration)
        return migration, approved

    def fake_materialize(database: Path, paths, migration):
        calls.append("rotation_allocation")
        allocation = {
            "runtime_task_bindability": {
                "verified_activity_count": 240,
                "all_36_skill_sessions_distinct_item_capacity_proven": True,
            }
        }
        runner.write_json(paths["rotation"], {"forms": [], "scene_usage_summary": []})
        runner.write_json(paths["allocation"], allocation)
        return {}, allocation

    def fake_replay(source_database: Path, paths, *, learner_id: str):
        calls.append("replay")
        report = {
            "canonical_database_safety": {"canonical_database_unchanged": True},
            "execution_acceptance": {
                "form_count": 12,
                "session_count": 36,
                "blueprint_exposure_count": 240,
                "response_attempt_count": 192,
                "outcome_counts": {"AUTO_PASS": 156, "PENDING_HUMAN_REVIEW": 36},
                "assessment_scored_attempt_count": 48,
                "support_filler_exposure_count": 0,
            },
        }
        runner.write_json(paths["replay_report"], report)
        return report

    monkeypatch.setattr(runner, "_bootstrap_fresh_474", fake_bootstrap)
    monkeypatch.setattr(runner, "_migrate_u01qb15", fake_migrate)
    monkeypatch.setattr(runner, "_materialize_r2_and_allocation", fake_materialize)
    monkeypatch.setattr(runner, "_run_private_replay", fake_replay)

    report = runner.run_acceptance(
        real62_path=real62,
        output_dir=tmp_path / "out",
        replace=True,
        learner_id="ci-learner",
        expected_real62_artifact_sha256=expected_artifact_sha,
    )

    assert calls == ["bootstrap", "migrate", "rotation_allocation", "replay"]
    assert report["status"] == runner.PASS_STATUS
    assert report["actual_real62_artifact_sha256"] == expected_artifact_sha
    assert report["actual_real62_file_sha256"] == raw_file_sha
    assert report["actual_real62_file_sha256"] != report["actual_real62_artifact_sha256"]
    assert report["fresh_runtime"]["runtime_item_count"] == 474
    assert report["execution_acceptance"]["session_count"] == 36
    assert report["real_canonical_learner_state_touched"] is False


def test_actual_real62_acceptance_runner_rejects_wrong_canonical_artifact_identity(tmp_path: Path) -> None:
    real62 = tmp_path / "real62.private.json"
    approved_fixture = _approved_fixture()
    real62.write_text(json.dumps(approved_fixture, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        runner.run_acceptance(
            real62_path=real62,
            output_dir=tmp_path / "out",
            replace=True,
            learner_id="ci-learner",
            expected_real62_artifact_sha256="0" * 64,
        )
    except runner.ActualReal62AcceptanceError as exc:
        assert str(exc).startswith("REAL62_ARTIFACT_SHA256_INVALID:")
    else:
        raise AssertionError("wrong canonical Real62 artifact SHA was not rejected")


def test_actual_real62_acceptance_runner_rejects_tampered_artifact_even_if_embedded_sha_is_present(tmp_path: Path) -> None:
    real62 = tmp_path / "real62.private.json"
    approved_fixture = _approved_fixture()
    approved_fixture["payload"]["tampered"] = True
    real62.write_text(json.dumps(approved_fixture, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        runner.run_acceptance(
            real62_path=real62,
            output_dir=tmp_path / "out",
            replace=True,
            learner_id="ci-learner",
            expected_real62_artifact_sha256=approved_fixture["artifact_sha256"],
        )
    except runner.ActualReal62AcceptanceError as exc:
        assert str(exc).startswith("REAL62_CANONICAL_ARTIFACT_INVALID:")
    else:
        raise AssertionError("tampered Real62 artifact was not rejected")
