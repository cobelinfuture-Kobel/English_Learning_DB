import hashlib
import json
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

BUILDER_PATH = BASE_DIR / "ulga" / "builders" / "build_dependency_readiness_resolution.py"
VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_dependency_readiness_resolution.py"
RESOLUTION_PATH = BASE_DIR / "ulga" / "graph" / "dependency_readiness_resolution.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "dependency_readiness_resolution_summary.json"
LEARNING_OPPORTUNITIES_PATH = BASE_DIR / "ulga" / "graph" / "learning_opportunities.json"
REINFORCEMENT_SIGNAL_PATH = BASE_DIR / "ulga" / "graph" / "reinforcement_signal.json"
UPSTREAM_PATHS = [
    BASE_DIR / "ulga" / "graph" / "learning_opportunities.json",
    BASE_DIR / "ulga" / "graph" / "reinforcement_signal.json",
    BASE_DIR / "ulga" / "graph" / "dependency_graph.json",
    BASE_DIR / "ulga" / "graph" / "ranked_learning_opportunities.json",
    BASE_DIR / "ulga" / "graph" / "antigravity_plan.json",
    BASE_DIR / "ulga" / "learner_state" / "learner_state.json",
    BASE_DIR / "ulga" / "schema" / "learning_signal_policy.json",
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
    assert RESOLUTION_PATH.exists()
    assert SUMMARY_PATH.exists()


def test_validator_passes():
    result = run_command([sys.executable, str(VALIDATOR_PATH)])
    assert result.returncode == 0, result.stdout + result.stderr


def test_summary_exists():
    summary = load_json(SUMMARY_PATH)
    assert summary["status"] in {"PASS", "PASS_WITH_WARNINGS"}
    assert "total_unknown_inputs" in summary
    assert "resolved_ready_count" in summary
    assert "resolved_blocked_count" in summary
    assert "still_unknown_count" in summary
    assert isinstance(summary["resolution_type_distribution"], dict)
    assert isinstance(summary["missing_optional_inputs"], list)
    assert isinstance(summary["warnings"], list)


def test_resolution_ids_unique():
    payload = load_json(RESOLUTION_PATH)
    ids = [item["resolution_id"] for item in payload["resolutions"]]
    assert len(ids) == len(set(ids))


def test_all_resolved_opportunity_ids_exist():
    payload = load_json(RESOLUTION_PATH)
    opportunities = load_json(LEARNING_OPPORTUNITIES_PATH)
    opportunity_ids = {item["opportunity_id"] for item in opportunities}
    unknown_ids = {
        item["opportunity_id"]
        for item in opportunities
        if item.get("dependency", {}).get("status") == "unknown"
    }
    for resolution in payload["resolutions"]:
        assert resolution["opportunity_id"] in opportunity_ids
        assert resolution["opportunity_id"] in unknown_ids
        assert resolution["previous_dependency_status"] == "unknown"


def test_no_missing_ref_marked_ready():
    payload = load_json(RESOLUTION_PATH)
    for resolution in payload["resolutions"]:
        evidence = resolution["evidence"]
        if evidence["missing_required_refs"]:
            assert resolution["resolved_dependency_status"] != "ready"
            assert resolution["planner_eligible_after_resolution"] is False
        if resolution["resolution_type"] == "missing_required_ref":
            assert resolution["resolved_dependency_status"] == "blocked"


def test_level_blocked_not_planner_eligible():
    payload = load_json(RESOLUTION_PATH)
    for resolution in payload["resolutions"]:
        if resolution["resolution_type"] == "explicit_requires_level_blocked":
            assert resolution["resolved_dependency_status"] == "blocked"
            assert resolution["planner_eligible_after_resolution"] is False
            assert resolution["evidence"]["level_ceiling_passed"] is False


def test_ready_resolution_planner_eligible():
    payload = load_json(RESOLUTION_PATH)
    for resolution in payload["resolutions"]:
        if resolution["resolved_dependency_status"] == "ready":
            assert resolution["planner_eligible_after_resolution"] is True
            assert not resolution["evidence"]["missing_required_refs"]


def test_deterministic_output():
    first_result = run_command([sys.executable, str(BUILDER_PATH)])
    assert first_result.returncode == 0, first_result.stdout + first_result.stderr
    first_resolution = RESOLUTION_PATH.read_bytes()
    first_summary = SUMMARY_PATH.read_bytes()

    second_result = run_command([sys.executable, str(BUILDER_PATH)])
    assert second_result.returncode == 0, second_result.stdout + second_result.stderr
    assert RESOLUTION_PATH.read_bytes() == first_resolution
    assert SUMMARY_PATH.read_bytes() == first_summary


def test_reinforcement_positive_dependency_unknown_records_are_covered():
    payload = load_json(RESOLUTION_PATH)
    reinforcement = load_json(REINFORCEMENT_SIGNAL_PATH)
    resolved_ids = {item["opportunity_id"] for item in payload["resolutions"]}
    positive_unknown_ids = {
        signal["target_id"]
        for signal in reinforcement["signals"]
        if signal["signal_score"] > 0 and signal["ineligible_reason"] == "dependency_unknown"
    }
    assert positive_unknown_ids
    assert positive_unknown_ids <= resolved_ids


def test_no_upstream_files_modified():
    before = {path: file_hash(path) for path in UPSTREAM_PATHS if path.exists()}
    result = run_command([sys.executable, str(BUILDER_PATH)])
    assert result.returncode == 0, result.stdout + result.stderr
    after = {path: file_hash(path) for path in UPSTREAM_PATHS if path.exists()}
    assert after == before
