import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from ulga.builders.build_antigravity_plan import build_antigravity_plan


BASE_DIR = Path(__file__).resolve().parents[2]

BUILDER_PATH = BASE_DIR / "ulga" / "builders" / "build_antigravity_plan.py"
VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_antigravity_plan.py"
PLAN_PATH = BASE_DIR / "ulga" / "graph" / "antigravity_plan.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "antigravity_plan_summary.json"
OPPORTUNITIES_PATH = BASE_DIR / "ulga" / "graph" / "learning_opportunities.json"
READINGS_PATH = BASE_DIR / "ulga" / "graph" / "reading_stub_authority.json"
UPSTREAM_PATHS = [
    BASE_DIR / "ulga" / "graph" / "learning_opportunities.json",
    BASE_DIR / "ulga" / "graph" / "ranked_learning_opportunities.json",
    BASE_DIR / "ulga" / "graph" / "reading_stub_authority.json",
    BASE_DIR / "ulga" / "learner_state" / "learner_state.json",
    BASE_DIR / "ulga" / "graph" / "dependency_graph.json",
    BASE_DIR / "ulga" / "graph" / "theme_spiral_graph.json",
]


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_command(args):
    return subprocess.run(args, cwd=BASE_DIR, capture_output=True, text=True)


def test_builder_runs():
    result = run_command([sys.executable, str(BUILDER_PATH)])
    assert result.returncode == 0, result.stdout + result.stderr
    assert PLAN_PATH.exists()
    assert SUMMARY_PATH.exists()


def test_validator_passes():
    result = run_command([sys.executable, str(VALIDATOR_PATH)])
    assert result.returncode == 0, result.stdout + result.stderr


def test_session_exists_and_has_five_opportunities():
    plan = load_json(PLAN_PATH)
    assert plan["sessions"]
    assert len(plan["selected_opportunities"]) == 5
    block_counts = {block["block_type"]: len(block["opportunity_ids"]) for block in plan["sessions"][0]["blocks"]}
    assert block_counts == {
        "warm_up": 1,
        "core_learning": 2,
        "reinforcement": 1,
        "assessment": 1,
    }


def test_reading_delivery_rate_is_complete():
    summary = load_json(SUMMARY_PATH)
    assert summary["reading_delivery_rate"] == 1.0


def test_all_opportunities_exist():
    plan = load_json(PLAN_PATH)
    opportunity_ids = {item["opportunity_id"] for item in load_json(OPPORTUNITIES_PATH)}
    for item in plan["selected_opportunities"]:
        assert item["opportunity_id"] in opportunity_ids


def test_all_readings_exist():
    plan = load_json(PLAN_PATH)
    reading_ids = {item["reading_id"] for item in load_json(READINGS_PATH)}
    for item in plan["selected_opportunities"]:
        assert item["reading_id"] in reading_ids


def test_selected_ids_are_unique():
    plan = load_json(PLAN_PATH)
    opportunity_ids = [item["opportunity_id"] for item in plan["selected_opportunities"]]
    reading_ids = [item["reading_id"] for item in plan["selected_opportunities"]]
    assert len(opportunity_ids) == len(set(opportunity_ids))
    assert len(reading_ids) == len(set(reading_ids))


def test_reason_codes_exist():
    plan = load_json(PLAN_PATH)
    for item in plan["selected_opportunities"]:
        assert item["reason_codes"]
        assert "reading_available" in item["reason_codes"]
    for item in plan["explanations"]:
        assert item["reason_codes"]


def test_learner_mode_fail_closed_without_known_learner(tmp_path):
    summary = build_antigravity_plan(
        planner_mode="learner",
        learner_id="learner:missing",
        output_path=tmp_path / "plan.json",
        summary_path=tmp_path / "summary.json",
    )
    assert summary["status"] == "BLOCKED"
    assert "no learner_state records" in summary["warnings"][0]


def test_learner_mode_can_build_for_existing_learner(tmp_path):
    summary = build_antigravity_plan(
        planner_mode="learner",
        learner_id="learner:james",
        output_path=tmp_path / "plan.json",
        summary_path=tmp_path / "summary.json",
    )
    plan = load_json(tmp_path / "plan.json")
    assert summary["status"] in {"PASS", "PASS_WITH_WARNINGS"}
    assert plan["planner_mode"] == "learner"
    assert plan["learner_id"] == "learner:james"
    assert summary["selected_opportunities"] == 5


def test_deterministic_output():
    first_result = run_command([sys.executable, str(BUILDER_PATH)])
    assert first_result.returncode == 0, first_result.stdout + first_result.stderr
    first_plan = PLAN_PATH.read_bytes()
    first_summary = SUMMARY_PATH.read_bytes()

    second_result = run_command([sys.executable, str(BUILDER_PATH)])
    assert second_result.returncode == 0, second_result.stdout + second_result.stderr
    assert PLAN_PATH.read_bytes() == first_plan
    assert SUMMARY_PATH.read_bytes() == first_summary


def test_no_upstream_files_modified():
    before = {path: file_hash(path) for path in UPSTREAM_PATHS if path.exists()}
    result = run_command([sys.executable, str(BUILDER_PATH)])
    assert result.returncode == 0, result.stdout + result.stderr
    after = {path: file_hash(path) for path in UPSTREAM_PATHS if path.exists()}
    assert after == before
