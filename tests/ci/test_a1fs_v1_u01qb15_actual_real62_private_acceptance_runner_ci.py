from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ulga.builders import build_a1fs_v1_u01qb15_actual_real62_fresh474_r2_private_acceptance_runner as runner


def test_actual_real62_acceptance_runner_orchestrates_existing_authorities_only(
    tmp_path: Path, monkeypatch
) -> None:
    real62 = tmp_path / "real62.private.json"
    real62.write_text("{}\n", encoding="utf-8")
    expected_sha = hashlib.sha256(real62.read_bytes()).hexdigest()
    calls: list[str] = []

    def fake_bootstrap(database: Path, real62_path: Path):
        calls.append("bootstrap")
        assert real62_path == real62.resolve()
        database.write_bytes(b"fresh-474")
        return {
            "status": "PASS_FRESH_ACTUAL_REAL62_474_BASELINE",
            "base_item_count": 288,
            "extension_item_count": 186,
            "runtime_item_count": 474,
            "extension_artifact_sha256": "1" * 64,
        }

    def fake_migrate(database: Path, paths):
        calls.append("migrate")
        assert database.exists()
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
        assert migration["runtime_item_count"] == 474
        rotation = {"forms": [], "scene_usage_summary": []}
        allocation = {
            "runtime_task_bindability": {
                "verified_activity_count": 240,
                "all_36_skill_sessions_distinct_item_capacity_proven": True,
            }
        }
        runner.write_json(paths["rotation"], rotation)
        runner.write_json(paths["allocation"], allocation)
        return rotation, allocation

    def fake_replay(source_database: Path, paths, *, learner_id: str):
        calls.append("replay")
        assert learner_id == "ci-learner"
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
        expected_real62_sha256=expected_sha,
    )

    assert calls == ["bootstrap", "migrate", "rotation_allocation", "replay"]
    assert report["status"] == runner.PASS_STATUS
    assert report["fresh_runtime"]["runtime_item_count"] == 474
    assert report["u01qb15"]["base_item_count"] == 288
    assert report["u01qb15"]["extension_item_count"] == 186
    assert report["u01qb14r2"]["reuse_excluded_scene_refs"] == ["U01-C3-PICNIC-FOOD"]
    assert report["u01qb14r2"]["selected_reuse_scene_count"] == 17
    assert report["runtime_task_allocation"]["verified_activity_count"] == 240
    assert report["execution_acceptance"]["session_count"] == 36
    assert report["execution_acceptance"]["response_attempt_count"] == 192
    assert report["source_test_baseline_unchanged_during_replay"] is True
    assert report["real_canonical_learner_state_touched"] is False
    assert Path(report["outputs"]["final"]).exists()
    persisted = json.loads(Path(report["outputs"]["final"]).read_text(encoding="utf-8"))
    assert persisted["status"] == runner.PASS_STATUS


def test_actual_real62_acceptance_runner_rejects_wrong_source_identity(tmp_path: Path) -> None:
    real62 = tmp_path / "real62.private.json"
    real62.write_text("{}\n", encoding="utf-8")
    try:
        runner.run_acceptance(
            real62_path=real62,
            output_dir=tmp_path / "out",
            replace=True,
            learner_id="ci-learner",
            expected_real62_sha256="0" * 64,
        )
    except runner.ActualReal62AcceptanceError as exc:
        assert str(exc).startswith("REAL62_SHA256_INVALID:")
    else:
        raise AssertionError("wrong Real62 SHA was not rejected")
