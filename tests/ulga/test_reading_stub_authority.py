import hashlib
import json
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

BUILDER_PATH = BASE_DIR / "ulga" / "builders" / "build_reading_stub_authority.py"
VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_reading_stub_authority.py"
READINGS_PATH = BASE_DIR / "ulga" / "graph" / "reading_stub_authority.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "reading_stub_summary.json"
OPPORTUNITIES_PATH = BASE_DIR / "ulga" / "graph" / "learning_opportunities.json"
UPSTREAM_PATHS = [
    BASE_DIR / "ulga" / "graph" / "learning_opportunities.json",
    BASE_DIR / "ulga" / "graph" / "ranked_learning_opportunities.json",
    BASE_DIR / "ulga" / "graph" / "theme_nodes.json",
    BASE_DIR / "ulga" / "graph" / "vocabulary_nodes.json",
    BASE_DIR / "ulga" / "graph" / "sentence_patterns.json",
]


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
    assert READINGS_PATH.exists()
    assert SUMMARY_PATH.exists()


def test_validator_can_pass():
    result = run_command([sys.executable, str(VALIDATOR_PATH)])
    assert result.returncode == 0, result.stdout + result.stderr


def test_reading_count_positive_and_full_coverage():
    readings = load_json(READINGS_PATH)
    opportunities = load_json(OPPORTUNITIES_PATH)
    summary = load_json(SUMMARY_PATH)
    assert readings
    assert len(readings) == len(opportunities)
    assert summary["coverage_ratio"] == 1.0


def test_reading_ids_unique():
    readings = load_json(READINGS_PATH)
    ids = [item["reading_id"] for item in readings]
    assert len(ids) == len(set(ids))


def test_all_linked_opportunities_exist_once():
    readings = load_json(READINGS_PATH)
    opportunities = load_json(OPPORTUNITIES_PATH)
    opportunity_ids = {item["opportunity_id"] for item in opportunities}
    linked_ids = [linked for reading in readings for linked in reading["linked_opportunities"]]
    assert set(linked_ids) == opportunity_ids
    assert len(linked_ids) == len(set(linked_ids))


def test_schema_required_fields_present():
    readings = load_json(READINGS_PATH)
    required = {
        "reading_id",
        "title",
        "level",
        "theme_refs",
        "linked_opportunities",
        "focus_vocabulary",
        "focus_grammar",
        "focus_patterns",
        "estimated_word_count",
        "difficulty_profile",
        "content_status",
        "delivery_ready",
        "source",
    }
    for reading in readings:
        assert required <= set(reading)
        assert reading["content_status"] == "stub"
        assert reading["delivery_ready"] is True
        assert reading["source"] == "READING_STUB_AUTHORITY"
        assert reading["theme_refs"]
        assert len(reading["linked_opportunities"]) == 1
        assert reading["estimated_word_count"] > 0
        assert reading["difficulty_profile"]["cefr"] == reading["level"]


def test_planner_readiness_metrics():
    readings = load_json(READINGS_PATH)
    opportunities = load_json(OPPORTUNITIES_PATH)
    summary = load_json(SUMMARY_PATH)
    assert summary["planner_readiness"] == {
        "opportunity_count": len(opportunities),
        "reading_count": len(readings),
        "coverage_ratio": 1.0,
        "delivery_ready_ratio": 1.0,
    }


def test_deterministic_output():
    first_result = run_command([sys.executable, str(BUILDER_PATH)])
    assert first_result.returncode == 0, first_result.stdout + first_result.stderr
    first_readings = READINGS_PATH.read_bytes()
    first_summary = SUMMARY_PATH.read_bytes()

    second_result = run_command([sys.executable, str(BUILDER_PATH)])
    assert second_result.returncode == 0, second_result.stdout + second_result.stderr
    assert READINGS_PATH.read_bytes() == first_readings
    assert SUMMARY_PATH.read_bytes() == first_summary


def test_summary_exists():
    summary = load_json(SUMMARY_PATH)
    assert summary["status"] in {"PASS", "PASS_WITH_WARNINGS"}
    assert summary["total_readings"] > 0
    assert summary["linked_opportunities"] == summary["planner_readiness"]["opportunity_count"]
    assert isinstance(summary["by_level"], dict)
    assert isinstance(summary["by_theme"], dict)
    assert summary["content_status_distribution"] == {"stub": summary["total_readings"]}
    assert isinstance(summary["warnings"], list)


def test_no_upstream_files_modified():
    before = {path: file_hash(path) for path in UPSTREAM_PATHS if path.exists()}
    result = run_command([sys.executable, str(BUILDER_PATH)])
    assert result.returncode == 0, result.stdout + result.stderr
    after = {path: file_hash(path) for path in UPSTREAM_PATHS if path.exists()}
    assert after == before
