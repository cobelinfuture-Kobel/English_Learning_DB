import json
import subprocess
import sys
from pathlib import Path

from ulga.builders.build_static_candidate_ranking import (
    OUTPUT_PATH,
    build_ranking_payload,
    candidate_sort_key,
    compute_static_score,
)


BASE_DIR = Path(__file__).resolve().parents[2]
FIXTURE_PATH = BASE_DIR / "tests" / "fixtures" / "ulga" / "static_candidate_ranking_fixture.json"
BUILDER_PATH = BASE_DIR / "ulga" / "builders" / "build_static_candidate_ranking.py"
VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_static_candidate_ranking.py"


def load_fixture():
    with FIXTURE_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def build_fixture_payload():
    return build_ranking_payload(load_fixture())


def candidate_by_id(payload, candidate_id):
    for candidate in payload["candidates"]:
        if candidate["candidate_id"] == candidate_id:
            return candidate
    raise KeyError(candidate_id)


def run_command(args):
    return subprocess.run(args, cwd=BASE_DIR, capture_output=True, text=True)


def test_static_ranking_schema_contract():
    payload = build_fixture_payload()
    assert payload["schema_version"] == "ULGA_S10C_STATIC_CANDIDATE_RANKING_V1"
    assert payload["ranking_mode"] == "static_offline"
    assert payload["adaptive_enabled"] is False
    assert isinstance(payload["candidates"], list)
    assert isinstance(payload["blocked_candidates"], list)
    assert payload["candidates"]


def test_static_ranking_disallows_adaptive_fields():
    payload = build_fixture_payload()
    dumped = json.dumps(payload, ensure_ascii=False).lower()
    for forbidden in [
        "learner_state",
        "mastery",
        "retention",
        "assessment",
        "review_queue",
        "learner_id",
        "james",
        "cyndi",
    ]:
        assert forbidden not in dumped


def test_static_score_recomputes_correctly():
    payload = build_fixture_payload()
    for candidate in payload["candidates"]:
        assert compute_static_score(candidate["score_breakdown"]) == candidate["static_score"]


def test_candidates_sorted_deterministically():
    payload = build_fixture_payload()
    assert payload["candidates"] == sorted(payload["candidates"], key=candidate_sort_key)
    assert [candidate["rank"] for candidate in payload["candidates"]] == list(range(1, len(payload["candidates"]) + 1))


def test_blocked_candidates_are_excluded():
    payload = build_fixture_payload()
    active_ids = {candidate["candidate_id"] for candidate in payload["candidates"]}
    blocked_ids = {candidate["candidate_id"] for candidate in payload["blocked_candidates"]}
    assert "pattern:blocked_pattern" in blocked_ids
    assert "chunk:blocked_chunk" in blocked_ids
    assert active_ids.isdisjoint(blocked_ids)


def test_explain_required_for_active_candidates():
    payload = build_fixture_payload()
    for candidate in payload["candidates"]:
        assert candidate["blocked"] is False
        assert candidate["block_reasons"] == []
        assert candidate["explain"]


def test_frequency_priority_fixture():
    payload = build_fixture_payload()
    assert candidate_by_id(payload, "vocabulary:water")["static_score"] > candidate_by_id(payload, "vocabulary:disposable_income")["static_score"]
    assert candidate_by_id(payload, "vocabulary:water")["score_breakdown"]["frequency_score"] > candidate_by_id(payload, "vocabulary:disposable_income")["score_breakdown"]["frequency_score"]


def test_dependency_priority_fixture():
    payload = build_fixture_payload()
    assert candidate_by_id(payload, "pattern:there_is")["static_score"] > candidate_by_id(payload, "pattern:present_perfect_conditional")["static_score"]
    assert candidate_by_id(payload, "pattern:there_is")["score_breakdown"]["dependency_readiness_score"] > candidate_by_id(payload, "pattern:present_perfect_conditional")["score_breakdown"]["dependency_readiness_score"]


def test_theme_spiral_priority_fixture():
    payload = build_fixture_payload()
    assert candidate_by_id(payload, "vocabulary:kitchen")["static_score"] > candidate_by_id(payload, "vocabulary:airport")["static_score"]
    assert candidate_by_id(payload, "vocabulary:kitchen")["score_breakdown"]["theme_spiral_score"] > candidate_by_id(payload, "vocabulary:airport")["score_breakdown"]["theme_spiral_score"]


def test_reinforcement_priority_fixture():
    payload = build_fixture_payload()
    assert candidate_by_id(payload, "pattern:i_like")["static_score"] > candidate_by_id(payload, "pattern:i_would_have_liked")["static_score"]
    assert candidate_by_id(payload, "pattern:i_like")["score_breakdown"]["reinforcement_score"] >= candidate_by_id(payload, "pattern:i_would_have_liked")["score_breakdown"]["reinforcement_score"]


def test_builder_and_validator_run():
    build_result = run_command([sys.executable, str(BUILDER_PATH)])
    assert build_result.returncode == 0, build_result.stdout + build_result.stderr
    assert OUTPUT_PATH.exists()
    validate_result = run_command([sys.executable, str(VALIDATOR_PATH)])
    assert validate_result.returncode == 0, validate_result.stdout + validate_result.stderr
