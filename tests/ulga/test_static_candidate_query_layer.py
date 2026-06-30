import json
import subprocess
import sys
from pathlib import Path

from ulga.query import static_candidate_query_layer as query_layer


BASE_DIR = Path(__file__).resolve().parents[2]
RAW_RANKING_PATH = BASE_DIR / "ulga" / "graph" / "static_candidate_ranking.json"
VIEWS_PATH = BASE_DIR / "ulga" / "graph" / "static_candidate_ranking_views.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "static_candidate_query_layer_summary.json"
VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_static_candidate_query_layer.py"


def load_json(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def run_command(args):
    return subprocess.run(args, cwd=BASE_DIR, capture_output=True, text=True)


def ensure_summary_report():
    summary = query_layer.generate_summary_report()
    assert SUMMARY_PATH.exists()
    return summary


def assert_success_response(response):
    assert "error" not in response
    assert response["query_metadata"]["static_only"] is True
    assert response["query_metadata"]["adaptive_enabled"] is False
    assert isinstance(response["query_metadata"]["warnings"], list)
    assert isinstance(response["candidates"], list)


def assert_candidate_shape(candidate):
    required = {
        "candidate_id",
        "raw_candidate_id",
        "label",
        "node_type",
        "candidate_type",
        "level",
        "cefr",
        "internal_level",
        "level_family",
        "level_band",
        "level_source",
        "theme_refs",
        "view_rank",
        "raw_rank",
        "raw_static_score",
        "view_score",
        "score_type",
        "source_artifact",
        "bridge_reason",
        "supporting_authority_layer",
        "explanation",
        "warnings",
    }
    assert required.issubset(candidate)


def test_module_import():
    assert query_layer is not None


def test_all_public_query_functions_exist():
    for name in query_layer.PUBLIC_QUERY_FUNCTIONS:
        assert hasattr(query_layer, name)


def test_get_static_ranking_view_returns_canonical_response():
    response = query_layer.get_static_ranking_view("balanced_global_view", limit=5)
    assert_success_response(response)
    assert response["query_metadata"]["view_name"] == "balanced_global_view"
    assert len(response["candidates"]) == 5
    for candidate in response["candidates"]:
        assert_candidate_shape(candidate)


def test_get_top_candidates_default_behavior():
    response = query_layer.get_top_candidates(limit=5)
    assert_success_response(response)
    assert response["query_metadata"]["view_name"] == "balanced_global_view"
    assert response["query_metadata"]["query_type"] == "get_top_candidates"


def test_get_candidates_by_theme_warning_behavior():
    response = query_layer.get_candidates_by_theme("Home", limit=5)
    assert_success_response(response)
    assert "THEME_SCOPED_VIEW_HEURISTIC_RELEVANCE_WARNING" in response["query_metadata"]["warnings"]


def test_get_candidates_by_node_type_normalization():
    response = query_layer.get_candidates_by_node_type("vocabulary", limit=5)
    assert_success_response(response)
    assert response["candidates"]
    assert all(candidate["node_type"] == "vocabulary" for candidate in response["candidates"])


def test_get_candidate_explanation_schema():
    response = query_layer.get_candidate_explanation("chunk:go_out:safe_chunk_001519")
    assert_success_response(response)
    explanation = response["candidates"][0]["explanation"]
    assert query_layer.EXPLANATION_FIELDS.issubset(explanation)


def test_reading_bridge_warning():
    response = query_layer.get_reading_bridge_candidates(limit=5)
    assert_success_response(response)
    assert "READING_BRIDGE_VIEW_NEEDS_TUNING" in response["query_metadata"]["warnings"]


def test_dialogue_bridge_warning():
    response = query_layer.get_dialogue_bridge_candidates(limit=5)
    assert_success_response(response)
    assert "DIALOGUE_BRIDGE_VIEW_NEEDS_TUNING" in response["query_metadata"]["warnings"]


def test_a1_safe_retrieval():
    response = query_layer.get_a1_safe_candidates(limit=5)
    assert_success_response(response)
    assert all(candidate["cefr"] == "A1" for candidate in response["candidates"])


def test_static_only_false_rejection():
    response = query_layer.get_top_candidates(limit=5, static_only=False)
    assert response["error"]["code"] == "STATIC_ONLY_REQUIRED"


def test_learner_id_rejection():
    request = {
        "query_type": "get_top_candidates",
        "view_name": "balanced_global_view",
        "filters": {"learner_id": "abc"},
        "limit": 5,
        "offset": 0,
        "include_explanation": True,
        "include_score_breakdown": True,
        "static_only": True,
    }
    response = query_layer.query_static_candidates(request)
    assert response["error"]["code"] == "ADAPTIVE_FIELD_REJECTED"


def test_mastery_rejection():
    request = {
        "query_type": "get_top_candidates",
        "view_name": "balanced_global_view",
        "filters": {"mastery": "weak"},
        "limit": 5,
        "offset": 0,
        "include_explanation": True,
        "include_score_breakdown": True,
        "static_only": True,
    }
    response = query_layer.query_static_candidates(request)
    assert response["error"]["code"] == "ADAPTIVE_FIELD_REJECTED"


def test_adaptive_rejection():
    request = {
        "query_type": "get_top_candidates",
        "view_name": "balanced_global_view",
        "filters": {"adaptive": True},
        "limit": 5,
        "offset": 0,
        "include_explanation": True,
        "include_score_breakdown": True,
        "static_only": True,
    }
    response = query_layer.query_static_candidates(request)
    assert response["error"]["code"] == "ADAPTIVE_FIELD_REJECTED"


def test_node_type_candidate_type_conflict_rejection():
    response = query_layer.get_top_candidates(node_type="chunk", candidate_type="vocabulary_candidate", limit=5)
    assert response["error"]["code"] == "NODE_TYPE_CANDIDATE_TYPE_CONFLICT"


def test_limit_clamp_behavior():
    response = query_layer.get_top_candidates(limit=1000)
    assert_success_response(response)
    assert response["query_metadata"]["limit"] == query_layer.MAX_LIMIT
    assert "LIMIT_CLAMPED_TO_MAXIMUM" in response["query_metadata"]["warnings"]


def test_raw_ranking_curriculum_use_blocked():
    response = query_layer.get_static_ranking_view("raw_global_view", limit=5)
    assert_success_response(response)
    assert "RAW_RANKING_NOT_ALLOWED_FOR_CURRICULUM_USE" in response["query_metadata"]["warnings"]


def test_response_candidate_required_fields():
    response = query_layer.get_top_candidates(limit=3)
    for candidate in response["candidates"]:
        assert_candidate_shape(candidate)


def test_explanation_required_fields():
    response = query_layer.get_top_candidates(limit=3)
    for candidate in response["candidates"]:
        assert query_layer.EXPLANATION_FIELDS.issubset(candidate["explanation"])


def test_multi_level_coverage_matrix_includes_all_levels():
    matrix = query_layer.build_multi_level_coverage_matrix()
    assert [row["level"] for row in matrix] == ["A1", "A1+", "A2", "A2+", "B1", "B1+", "B2", "B2+", "C1", "C2"]


def test_plus_bands_mark_requires_internal_band_mapping():
    matrix = query_layer.build_multi_level_coverage_matrix()
    plus_rows = [row for row in matrix if row["level"].endswith("+")]
    assert plus_rows
    assert all(row["status"] == "requires_internal_band_mapping" for row in plus_rows)


def test_no_mutation_of_static_candidate_ranking():
    before = load_json(RAW_RANKING_PATH)
    query_layer.get_top_candidates(limit=5)
    after = load_json(RAW_RANKING_PATH)
    assert before == after


def test_no_mutation_of_static_candidate_ranking_views():
    before = load_json(VIEWS_PATH)
    query_layer.get_top_candidates(limit=5)
    after = load_json(VIEWS_PATH)
    assert before == after


def test_summary_report_exists():
    summary = ensure_summary_report()
    assert summary["task"] == "ULGA-S10J_StaticCandidateQueryLayer_ContractImplementation"
    assert "multi_level_coverage_matrix" in summary
    assert SUMMARY_PATH.exists()


def test_validator_runs():
    ensure_summary_report()
    result = run_command([sys.executable, str(VALIDATOR_PATH)])
    assert result.returncode == 0, result.stdout + result.stderr
