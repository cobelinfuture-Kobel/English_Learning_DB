import hashlib
import json
import subprocess
import sys
from pathlib import Path

from ulga.builders.build_reinforcement_signal import build_signal


BASE_DIR = Path(__file__).resolve().parents[2]

BUILDER_PATH = BASE_DIR / "ulga" / "builders" / "build_reinforcement_signal.py"
VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_reinforcement_signal.py"
SIGNAL_PATH = BASE_DIR / "ulga" / "graph" / "reinforcement_signal.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "reinforcement_signal_summary.json"
LEARNING_OPPORTUNITIES_PATH = BASE_DIR / "ulga" / "graph" / "learning_opportunities.json"
UPSTREAM_PATHS = [
    BASE_DIR / "ulga" / "graph" / "learning_opportunities.json",
    BASE_DIR / "ulga" / "graph" / "ranked_learning_opportunities.json",
    BASE_DIR / "ulga" / "graph" / "antigravity_plan.json",
    BASE_DIR / "ulga" / "learner_state" / "learner_state.json",
    BASE_DIR / "ulga" / "graph" / "dependency_graph.json",
    BASE_DIR / "ulga" / "graph" / "theme_spiral_graph.json",
    BASE_DIR / "ulga" / "graph" / "reading_stub_authority.json",
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
    assert SIGNAL_PATH.exists()
    assert SUMMARY_PATH.exists()


def test_validator_passes():
    result = run_command([sys.executable, str(VALIDATOR_PATH)])
    assert result.returncode == 0, result.stdout + result.stderr


def test_signal_count_matches_learning_opportunities():
    payload = load_json(SIGNAL_PATH)
    opportunities = load_json(LEARNING_OPPORTUNITIES_PATH)
    assert len(payload["signals"]) == len(opportunities)


def test_score_range_valid():
    payload = load_json(SIGNAL_PATH)
    for signal in payload["signals"]:
        assert 0 <= signal["signal_score"] <= 1
        for value in signal["score_breakdown"].values():
            assert 0 <= value <= 1


def test_unknown_dependency_cannot_be_planner_eligible():
    payload = load_json(SIGNAL_PATH)
    unknown_signals = [signal for signal in payload["signals"] if signal["dependency"]["status"] == "unknown"]
    assert unknown_signals
    for signal in unknown_signals:
        assert signal["planner_eligible"] is False
        assert signal["ineligible_reason"] == "dependency_unknown"


def test_ready_dependency_with_positive_signal_may_be_planner_eligible():
    opportunity = {
        "opportunity_id": "LO_TEST_READY",
        "focus_nodes": {
            "vocabulary": ["vocabulary:test"],
            "grammar": [],
            "pattern": [],
            "chunk": [],
        },
        "reinforces": {
            "vocabulary": ["vocabulary:test"],
            "grammar": [],
            "pattern": [],
            "chunk": [],
        },
        "theme_confidence": {"source": "pattern_theme_ref"},
        "dependency": {"status": "ready"},
    }
    state_index = {
        "vocabulary:test": [
            {
                "mastery_score": 0.4,
                "review_due_at": "2026-06-17T00:00:00Z",
                "last_seen_at": "2026-06-01T00:00:00Z",
            }
        ]
    }
    signal = build_signal(1, opportunity, {}, state_index)
    assert signal["signal_score"] > 0
    assert signal["planner_eligible"] is True
    assert signal["ineligible_reason"] is None


def test_summary_exists():
    summary = load_json(SUMMARY_PATH)
    assert summary["status"] in {"PASS", "PASS_WITH_WARNINGS"}
    assert isinstance(summary["signal_band_distribution"], dict)
    assert isinstance(summary["ineligible_reason_distribution"], dict)
    assert isinstance(summary["warnings"], list)
    assert "signals_with_score_gt_zero" in summary
    assert "eligible_with_score_gt_zero" in summary
    assert "dependency_unknown_blocked_count" in summary


def test_deterministic_output():
    first_result = run_command([sys.executable, str(BUILDER_PATH)])
    assert first_result.returncode == 0, first_result.stdout + first_result.stderr
    first_signal = SIGNAL_PATH.read_bytes()
    first_summary = SUMMARY_PATH.read_bytes()

    second_result = run_command([sys.executable, str(BUILDER_PATH)])
    assert second_result.returncode == 0, second_result.stdout + second_result.stderr
    assert SIGNAL_PATH.read_bytes() == first_signal
    assert SUMMARY_PATH.read_bytes() == first_summary


def test_no_upstream_files_modified():
    before = {path: file_hash(path) for path in UPSTREAM_PATHS if path.exists()}
    result = run_command([sys.executable, str(BUILDER_PATH)])
    assert result.returncode == 0, result.stdout + result.stderr
    after = {path: file_hash(path) for path in UPSTREAM_PATHS if path.exists()}
    assert after == before
