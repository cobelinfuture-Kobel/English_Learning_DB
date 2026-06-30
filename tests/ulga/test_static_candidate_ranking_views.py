import json
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
RAW_RANKING_PATH = BASE_DIR / "ulga" / "graph" / "static_candidate_ranking.json"
VIEWS_PATH = BASE_DIR / "ulga" / "graph" / "static_candidate_ranking_views.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "static_candidate_ranking_views_summary.json"
BUILDER_PATH = BASE_DIR / "ulga" / "builders" / "build_static_candidate_ranking_views.py"
VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_static_candidate_ranking_views.py"


def run_command(args):
    return subprocess.run(args, cwd=BASE_DIR, capture_output=True, text=True)


def ensure_views():
    build_result = run_command([sys.executable, str(BUILDER_PATH)])
    assert build_result.returncode == 0, build_result.stdout + build_result.stderr
    validate_result = run_command([sys.executable, str(VALIDATOR_PATH)])
    assert validate_result.returncode == 0, validate_result.stdout + validate_result.stderr
    assert VIEWS_PATH.exists()
    assert SUMMARY_PATH.exists()


def load_json(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_views():
    ensure_views()
    return load_json(VIEWS_PATH)


def load_summary():
    ensure_views()
    return load_json(SUMMARY_PATH)


def duplicate_top20(candidates):
    normalized = []
    for candidate in candidates[:20]:
        label = candidate["label"].lower().replace("_", " ")
        normalized.append(label.split(":safe_chunk_")[0].strip())
    return len(normalized) != len(set(normalized))


def test_views_file_exists():
    ensure_views()


def test_views_schema_contract():
    payload = load_views()
    assert payload["schema_version"] == "ULGA_S10F_STATIC_CANDIDATE_RANKING_VIEWS_V1"
    assert payload["generation_mode"] == "static_offline_view_construction"
    assert payload["principles"]["raw_static_score_preserved"] is True


def test_views_static_offline_mode():
    payload = load_views()
    assert payload["adaptive_enabled"] is False
    assert payload["principles"]["adaptive_enabled"] is False


def test_views_adaptive_leakage_false():
    payload = load_views()
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
        "planner",
    ]:
        assert forbidden not in dumped


def test_required_views_exist():
    payload = load_views()
    expected = {
        "raw_global_view",
        "balanced_global_view",
        "a1_safe_view",
        "theme_scoped_view",
        "reading_bridge_view",
        "dialogue_bridge_view",
        "pattern_first_view",
        "vocabulary_first_view",
        "chunk_safe_view",
        "deduplicated_view",
    }
    assert expected.issubset(payload["views"])
    assert set(payload["views"]["theme_scoped_view"]) == {"Home", "Food", "School", "Travel", "Health", "Personal", "Daily Life"}


def test_view_candidates_preserve_raw_traceability():
    payload = load_views()
    raw_payload = load_json(RAW_RANKING_PATH)
    raw_ids = {candidate["candidate_id"] for candidate in raw_payload["candidates"]}
    for view_name, view_value in payload["views"].items():
        if view_name == "theme_scoped_view":
            iterables = view_value.values()
        else:
            iterables = [view_value]
        for candidates in iterables:
            for candidate in candidates:
                assert candidate["raw_candidate_id"] in raw_ids
                assert candidate["raw_rank"] >= 1
                assert candidate["raw_static_score"] >= 0.0
                assert candidate["source_explain"]


def test_a1_safe_view_level_ceiling():
    payload = load_views()
    assert payload["views"]["a1_safe_view"]
    for candidate in payload["views"]["a1_safe_view"]:
        assert candidate["level"] == "A1"


def test_balanced_global_view_not_single_type_top_20():
    payload = load_views()
    top20 = payload["views"]["balanced_global_view"][:20]
    assert len({candidate["candidate_type"] for candidate in top20}) > 1
    assert sum(1 for candidate in top20 if candidate["candidate_type"] == "pattern_candidate") >= 4
    assert sum(1 for candidate in top20 if candidate["candidate_type"] == "vocabulary_candidate") >= 6
    assert sum(1 for candidate in top20 if candidate["candidate_type"] == "chunk_candidate") <= 7


def test_deduplicated_view_no_duplicate_top_20():
    payload = load_views()
    assert duplicate_top20(payload["views"]["deduplicated_view"]) is False


def test_a1_safe_view_no_duplicate_top_20():
    payload = load_views()
    assert duplicate_top20(payload["views"]["a1_safe_view"]) is False
    top20 = payload["views"]["a1_safe_view"][:20]
    assert sum(1 for candidate in top20 if candidate["candidate_type"] == "pattern_candidate") >= 5
    assert sum(1 for candidate in top20 if candidate["candidate_type"] == "vocabulary_candidate") >= 5


def test_view_scores_are_valid_range():
    payload = load_views()
    for view_name, view_value in payload["views"].items():
        if view_name == "theme_scoped_view":
            iterables = view_value.values()
        else:
            iterables = [view_value]
        for candidates in iterables:
            expected_ranks = list(range(1, len(candidates) + 1))
            assert [candidate["view_rank"] for candidate in candidates] == expected_ranks
            for candidate in candidates:
                assert 0.0 <= candidate["view_score"] <= 1.0


def test_raw_ranking_not_modified():
    before = load_json(RAW_RANKING_PATH)
    ensure_views()
    after = load_json(RAW_RANKING_PATH)
    assert before == after


def test_summary_report_exists():
    summary = load_summary()
    assert summary["schema_version"] == "ULGA_S10F_STATIC_CANDIDATE_RANKING_VIEWS_SUMMARY_V1"
    assert "balanced_global_view" in summary["views"]


def test_summary_status_valid():
    summary = load_summary()
    assert summary["status"] in {"PASS", "PASS_WITH_WARNINGS", "FAIL"}
    assert summary["next_recommended_task"] == "ULGA-S10G_StaticCandidateRankingViews_QA_Audit"
