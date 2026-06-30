import json
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

BUILDER_PATH = BASE_DIR / "ulga" / "builders" / "build_opportunity_ranking.py"
VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_opportunity_ranking.py"
RANKED_PATH = BASE_DIR / "ulga" / "graph" / "ranked_learning_opportunities.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "opportunity_ranking_summary.json"
LEARNING_OPPORTUNITIES_PATH = BASE_DIR / "ulga" / "graph" / "learning_opportunities.json"
REQUIRED_BREAKDOWN_KEYS = {
    "dependency_score",
    "mastery_gap_score",
    "reinforcement_score",
    "theme_continuity_score",
    "frequency_score",
    "pattern_utility_score",
    "spiral_weight_score",
}


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def run_command(args):
    return subprocess.run(args, cwd=BASE_DIR, capture_output=True, text=True)


def test_builder_runs():
    result = run_command([sys.executable, str(BUILDER_PATH)])
    assert result.returncode == 0, result.stdout + result.stderr
    assert RANKED_PATH.exists()
    assert SUMMARY_PATH.exists()


def test_validator_passes():
    result = run_command([sys.executable, str(VALIDATOR_PATH)])
    assert result.returncode == 0, result.stdout + result.stderr


def test_rank_ordering_stable():
    ranked = load_json(RANKED_PATH)
    assert ranked
    assert [item["rank"] for item in ranked] == list(range(1, len(ranked) + 1))
    sorted_copy = sorted(ranked, key=lambda item: (-item["candidate_score"], item["opportunity_id"]))
    assert ranked == sorted_copy


def test_score_range_valid():
    ranked = load_json(RANKED_PATH)
    for item in ranked:
        assert 0 <= item["candidate_score"] <= 1
        assert item["ranking_mode"] == "static_offline"
        assert set(item["score_breakdown"]) == REQUIRED_BREAKDOWN_KEYS
        for value in item["score_breakdown"].values():
            assert 0 <= value <= 1


def test_adaptive_fields_are_neutralized():
    ranked = load_json(RANKED_PATH)
    assert ranked
    for item in ranked:
        assert item["score_breakdown"]["mastery_gap_score"] == 0.0
        assert item["score_breakdown"]["reinforcement_score"] == 0.0


def test_top_rank_exists():
    ranked = load_json(RANKED_PATH)
    top = ranked[0]
    assert top["rank"] == 1
    assert top["opportunity_id"]
    assert top["explanation"]


def test_report_exists():
    summary = load_json(SUMMARY_PATH)
    opportunities = load_json(LEARNING_OPPORTUNITIES_PATH)
    assert summary["status"] in {"PASS", "PASS_WITH_WARNINGS"}
    assert summary["ranking_mode"] == "static_offline"
    assert summary["adaptive_inputs_used"] == []
    assert summary["total_ranked"] == len(opportunities)
    assert isinstance(summary["top_10_levels"], dict)
    assert isinstance(summary["top_10_themes"], dict)
    assert isinstance(summary["score_distribution"], dict)
    assert isinstance(summary["dependency_distribution"], dict)
    assert isinstance(summary["theme_source_distribution"], dict)
    assert isinstance(summary["warnings"], list)


def test_deterministic_output():
    first_result = run_command([sys.executable, str(BUILDER_PATH)])
    assert first_result.returncode == 0, first_result.stdout + first_result.stderr
    first_ranked = RANKED_PATH.read_bytes()
    first_summary = SUMMARY_PATH.read_bytes()

    second_result = run_command([sys.executable, str(BUILDER_PATH)])
    assert second_result.returncode == 0, second_result.stdout + second_result.stderr
    assert RANKED_PATH.read_bytes() == first_ranked
    assert SUMMARY_PATH.read_bytes() == first_summary


def test_builder_does_not_reference_learner_state():
    content = BUILDER_PATH.read_text(encoding="utf-8")
    assert "learner_state" not in content
