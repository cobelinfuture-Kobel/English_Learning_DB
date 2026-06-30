import hashlib
import json
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

BUILDER_PATH = BASE_DIR / "ulga" / "builders" / "build_exposure_mapping_bridge.py"
VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_exposure_mapping_bridge.py"
BRIDGE_PATH = BASE_DIR / "ulga" / "graph" / "exposure_mapping_bridge.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "exposure_mapping_bridge_summary.json"
S9Y_SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "learner_exposure_evidence_summary.json"
UPSTREAM_PATHS = [
    BASE_DIR / "ulga" / "learner_state" / "learner_state.json",
    BASE_DIR / "ulga" / "graph" / "learning_opportunities.json",
    BASE_DIR / "ulga" / "graph" / "vocabulary_nodes.json",
    BASE_DIR / "ulga" / "graph" / "sentence_patterns.json",
    BASE_DIR / "ulga" / "graph" / "theme_nodes.json",
    BASE_DIR / "ulga" / "graph" / "dependency_graph.json",
    BASE_DIR / "ulga" / "graph" / "dependency_readiness_resolution.json",
    BASE_DIR / "ulga" / "graph" / "reinforcement_signal.json",
    BASE_DIR / "ulga" / "graph" / "reinforcement_candidate_expansion.json",
    BASE_DIR / "ulga" / "graph" / "antigravity_plan.json",
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
    assert BRIDGE_PATH.exists()
    assert SUMMARY_PATH.exists()


def test_validator_passes():
    result = run_command([sys.executable, str(VALIDATOR_PATH)])
    assert result.returncode == 0, result.stdout + result.stderr


def test_bridge_count_gt_zero():
    payload = load_json(BRIDGE_PATH)
    assert len(payload["bridges"]) > 0


def test_multiple_bridge_types_supported():
    summary = load_json(SUMMARY_PATH)
    assert len(summary["bridge_distribution"]) >= 2
    assert "direct_focus_node_bridge" in summary["bridge_distribution"]
    assert "theme_bridge" in summary["bridge_distribution"]


def test_coverage_improves_vs_s9y_baseline():
    # S9Y baseline before S9Z1 was 2 mapped opportunities at 0.001488 coverage.
    result = run_command([sys.executable, str(BASE_DIR / "ulga" / "builders" / "build_learner_exposure_evidence.py")])
    assert result.returncode == 0, result.stdout + result.stderr
    summary = load_json(S9Y_SUMMARY_PATH)
    assert summary["opportunity_mapping_count"] > 2
    assert summary["coverage_rate"] > 0.001488


def test_theme_bridge_not_planner_safe():
    payload = load_json(BRIDGE_PATH)
    theme_bridges = [bridge for bridge in payload["bridges"] if bridge["bridge_type"] == "theme_bridge"]
    assert theme_bridges
    for bridge in theme_bridges:
        assert bridge["planner_safe"] is False


def test_deterministic_output():
    first_result = run_command([sys.executable, str(BUILDER_PATH)])
    assert first_result.returncode == 0, first_result.stdout + first_result.stderr
    first_bridge = BRIDGE_PATH.read_bytes()
    first_summary = SUMMARY_PATH.read_bytes()
    second_result = run_command([sys.executable, str(BUILDER_PATH)])
    assert second_result.returncode == 0, second_result.stdout + second_result.stderr
    assert BRIDGE_PATH.read_bytes() == first_bridge
    assert SUMMARY_PATH.read_bytes() == first_summary


def test_no_upstream_files_modified():
    before = {path: file_hash(path) for path in UPSTREAM_PATHS if path.exists()}
    result = run_command([sys.executable, str(BUILDER_PATH)])
    assert result.returncode == 0, result.stdout + result.stderr
    after = {path: file_hash(path) for path in UPSTREAM_PATHS if path.exists()}
    assert after == before
