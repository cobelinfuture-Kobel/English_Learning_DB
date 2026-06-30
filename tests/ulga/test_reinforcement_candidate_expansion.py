import hashlib
import json
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

BUILDER_PATH = BASE_DIR / "ulga" / "builders" / "build_reinforcement_candidate_expansion.py"
VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_reinforcement_candidate_expansion.py"
EXPANSION_PATH = BASE_DIR / "ulga" / "graph" / "reinforcement_candidate_expansion.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "reinforcement_candidate_expansion_summary.json"
UPSTREAM_PATHS = [
    BASE_DIR / "ulga" / "graph" / "learning_opportunities.json",
    BASE_DIR / "ulga" / "graph" / "ranked_learning_opportunities.json",
    BASE_DIR / "ulga" / "graph" / "reinforcement_signal.json",
    BASE_DIR / "ulga" / "graph" / "dependency_readiness_resolution.json",
    BASE_DIR / "ulga" / "graph" / "antigravity_plan.json",
    BASE_DIR / "ulga" / "graph" / "dependency_graph.json",
    BASE_DIR / "ulga" / "graph" / "reading_stub_authority.json",
    BASE_DIR / "ulga" / "learner_state" / "learner_state.json",
    BASE_DIR / "ulga" / "graph" / "learner_exposure_evidence.json",
]
VALID_SOURCES = {"direct_review", "dependency_parent", "theme_revisit", "exposure_evidence"}


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
    assert EXPANSION_PATH.exists()
    assert SUMMARY_PATH.exists()


def test_validator_passes():
    result = run_command([sys.executable, str(VALIDATOR_PATH)])
    assert result.returncode == 0, result.stdout + result.stderr


def test_candidate_count_gt_zero():
    payload = load_json(EXPANSION_PATH)
    assert len(payload["candidates"]) > 0


def test_source_valid():
    payload = load_json(EXPANSION_PATH)
    for candidate in payload["candidates"]:
        assert candidate["candidate_source"] in VALID_SOURCES
        assert isinstance(candidate["planner_eligible"], bool)
        assert candidate["dependency_status"] in {"ready", "blocked", "unknown"}
        assert isinstance(candidate["reading_ready"], bool)
        assert isinstance(candidate["level_safe"], bool)
        assert 0 <= candidate["confidence"] <= 1
        assert candidate["ineligible_reason"] in {
            None,
            "dependency_blocked",
            "dependency_unknown",
            "reading_missing",
            "no_prior_exposure",
            "level_blocked",
        }


def test_summary_exists():
    payload = load_json(EXPANSION_PATH)
    summary = load_json(SUMMARY_PATH)
    assert summary["status"] in {"PASS", "PASS_WITH_WARNINGS", "BLOCKED"}
    assert summary["candidate_count"] == len(payload["candidates"])
    assert "planner_eligible_count" in summary
    assert isinstance(summary["source_distribution"], dict)
    assert isinstance(summary["ineligible_reason_distribution"], dict)
    assert "exposure_evidence_used_count" in summary
    assert "dependency_ready_count" in summary
    assert "reading_ready_count" in summary
    assert isinstance(summary["warnings"], list)


def test_planner_eligible_candidates_are_ready_and_reading_ready():
    payload = load_json(EXPANSION_PATH)
    for candidate in payload["candidates"]:
        if candidate["planner_eligible"]:
            assert candidate["dependency_status"] == "ready"
            assert candidate["reading_ready"] is True
            assert candidate["prior_exposure"] is True
            assert candidate["level_safe"] is True
            assert candidate["ineligible_reason"] is None


def test_exposure_evidence_source_supported():
    payload = load_json(EXPANSION_PATH)
    exposure_candidates = [
        candidate for candidate in payload["candidates"] if candidate["candidate_source"] == "exposure_evidence"
    ]
    assert exposure_candidates
    for candidate in exposure_candidates:
        assert candidate["learner_id"]
        assert candidate["evidence_refs"]
        assert candidate["prior_exposure"] is True


def test_dependency_overlay_applied():
    payload = load_json(EXPANSION_PATH)
    blocked_candidates = [candidate for candidate in payload["candidates"] if candidate["dependency_status"] == "blocked"]
    assert blocked_candidates
    for candidate in blocked_candidates:
        assert candidate["planner_eligible"] is False
        assert candidate["ineligible_reason"] == "dependency_blocked"


def test_deterministic_output():
    first_result = run_command([sys.executable, str(BUILDER_PATH)])
    assert first_result.returncode == 0, first_result.stdout + first_result.stderr
    first_expansion = EXPANSION_PATH.read_bytes()
    first_summary = SUMMARY_PATH.read_bytes()

    second_result = run_command([sys.executable, str(BUILDER_PATH)])
    assert second_result.returncode == 0, second_result.stdout + second_result.stderr
    assert EXPANSION_PATH.read_bytes() == first_expansion
    assert SUMMARY_PATH.read_bytes() == first_summary


def test_no_upstream_files_modified():
    before = {path: file_hash(path) for path in UPSTREAM_PATHS if path.exists()}
    result = run_command([sys.executable, str(BUILDER_PATH)])
    assert result.returncode == 0, result.stdout + result.stderr
    after = {path: file_hash(path) for path in UPSTREAM_PATHS if path.exists()}
    assert after == before
