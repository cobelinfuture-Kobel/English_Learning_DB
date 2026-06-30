import hashlib
import json
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

BUILDER_PATH = BASE_DIR / "ulga" / "builders" / "build_learning_opportunities.py"
VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_learning_opportunities.py"
OPPORTUNITIES_PATH = BASE_DIR / "ulga" / "graph" / "learning_opportunities.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "learning_opportunity_summary.json"
UPSTREAM_PATHS = [
    BASE_DIR / "ulga" / "graph" / "sentence_patterns.json",
    BASE_DIR / "ulga" / "graph" / "pattern_vocabulary_constraints.json",
    BASE_DIR / "ulga" / "graph" / "pattern_vocabulary_candidate_query_contract.json",
    BASE_DIR / "ulga" / "graph" / "dependency_graph.json",
    BASE_DIR / "ulga" / "graph" / "theme_spiral_graph.json",
    BASE_DIR / "ulga" / "graph" / "theme_nodes.json",
    BASE_DIR / "ulga" / "graph" / "vocabulary_nodes.json",
    BASE_DIR / "ulga" / "schema" / "learning_signal_policy.json",
    BASE_DIR / "ulga" / "learner_state" / "learner_state.json",
]
REQUIRED_RANKING_FEATURES = {
    "dependency_score",
    "mastery_gap_score",
    "reinforcement_score",
    "theme_continuity_score",
    "frequency_score",
    "pattern_utility_score",
}
REQUIRED_POLICY_FLAGS = {
    "generator_ready",
    "requires_learner_state",
    "has_theme",
    "has_pattern",
    "has_vocabulary",
    "has_grammar",
}
ALLOWED_THEME_SOURCES = {
    "pattern_theme_ref",
    "pattern_slot_gate",
    "vocabulary_theme",
    "chunk_theme_hint",
    "theme_consensus",
    "general_fallback",
}


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_command(args):
    return subprocess.run(args, cwd=BASE_DIR, capture_output=True, text=True)


def test_builder_can_run():
    result = run_command([sys.executable, str(BUILDER_PATH)])
    assert result.returncode == 0, result.stdout + result.stderr
    assert OPPORTUNITIES_PATH.exists()
    assert SUMMARY_PATH.exists()


def test_validator_can_pass():
    result = run_command([sys.executable, str(VALIDATOR_PATH)])
    assert result.returncode == 0, result.stdout + result.stderr


def test_opportunity_id_unique():
    opportunities = load_json(OPPORTUNITIES_PATH)
    ids = [item["opportunity_id"] for item in opportunities]
    assert len(ids) == len(set(ids))


def test_schema_required_fields_present():
    opportunities = load_json(OPPORTUNITIES_PATH)
    assert opportunities
    required = {
        "opportunity_id",
        "source_pattern_id",
        "candidate_type",
        "level",
        "focus_nodes",
        "theme_refs",
        "theme_confidence",
        "reinforces",
        "dependency",
        "ranking_features",
        "policy_flags",
        "source",
    }
    for item in opportunities:
        assert required <= set(item)
        assert item["candidate_type"] == "learning_opportunity"
        assert item["source"] == "ULGA_S10B_LEARNING_OPPORTUNITY_AUTHORITY"
        assert {"vocabulary", "grammar", "pattern", "chunk"} <= set(item["focus_nodes"])
        assert item["focus_nodes"]["pattern"] or item["focus_nodes"]["vocabulary"]
        assert item["theme_refs"]
        assert set(item["theme_confidence"]) == {"source", "confidence"}
        assert item["theme_confidence"]["source"] in ALLOWED_THEME_SOURCES
        assert 0 <= item["theme_confidence"]["confidence"] <= 1
        assert item["dependency"]["status"] in {"ready", "blocked", "unknown"}
        assert REQUIRED_RANKING_FEATURES <= set(item["ranking_features"])
        assert REQUIRED_POLICY_FLAGS <= set(item["policy_flags"])


def test_deterministic_output():
    first_result = run_command([sys.executable, str(BUILDER_PATH)])
    assert first_result.returncode == 0, first_result.stdout + first_result.stderr
    first_opportunities = OPPORTUNITIES_PATH.read_bytes()
    first_summary = SUMMARY_PATH.read_bytes()

    second_result = run_command([sys.executable, str(BUILDER_PATH)])
    assert second_result.returncode == 0, second_result.stdout + second_result.stderr
    assert OPPORTUNITIES_PATH.read_bytes() == first_opportunities
    assert SUMMARY_PATH.read_bytes() == first_summary


def test_summary_report_exists():
    summary = load_json(SUMMARY_PATH)
    opportunities = load_json(OPPORTUNITIES_PATH)
    assert summary["status"] in {"PASS", "PASS_WITH_WARNINGS"}
    assert summary["total_opportunities"] == len(opportunities)
    assert isinstance(summary["by_level"], dict)
    assert isinstance(summary["by_theme"], dict)
    assert isinstance(summary["theme_source_distribution"], dict)
    assert isinstance(summary["theme_specificity"], dict)
    assert isinstance(summary["dependency_status_counts"], dict)
    assert isinstance(summary["policy_flag_counts"], dict)
    assert isinstance(summary["missing_optional_inputs"], list)
    assert isinstance(summary["warnings"], list)


def test_theme_specificity_above_threshold():
    summary = load_json(SUMMARY_PATH)
    opportunities = load_json(OPPORTUNITIES_PATH)
    general_count = sum(1 for item in opportunities if item["theme_refs"] == ["General"])
    specific_ratio = summary["theme_specificity"]["specific_ratio"]
    assert summary["theme_specificity"]["general_count"] == general_count
    assert general_count / len(opportunities) < 0.30
    assert specific_ratio > 0.70


def test_theme_refs_not_empty_and_general_is_last_resort():
    opportunities = load_json(OPPORTUNITIES_PATH)
    for item in opportunities:
        assert item["theme_refs"]
        source = item["theme_confidence"]["source"]
        if item["theme_refs"] == ["General"]:
            assert source == "general_fallback"
        else:
            assert source != "general_fallback"


def test_no_upstream_files_modified():
    before = {path: file_hash(path) for path in UPSTREAM_PATHS if path.exists()}
    result = run_command([sys.executable, str(BUILDER_PATH)])
    assert result.returncode == 0, result.stdout + result.stderr
    after = {path: file_hash(path) for path in UPSTREAM_PATHS if path.exists()}
    assert after == before
