import json
from pathlib import Path

from ulga.query import static_candidate_query_layer as query_layer


BASE_DIR = Path(__file__).resolve().parents[2]
PROTECTED_FILES = [
    "ulga/graph/static_candidate_ranking.json",
    "ulga/graph/static_candidate_ranking_views.json",
]


def load_json(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def required_files():
    return [
        BASE_DIR / "ulga" / "query" / "__init__.py",
        BASE_DIR / "ulga" / "query" / "static_candidate_query_layer.py",
        BASE_DIR / "ulga" / "validators" / "validate_static_candidate_query_layer.py",
        BASE_DIR / "tests" / "ulga" / "test_static_candidate_query_layer.py",
        BASE_DIR / "docs" / "ulga" / "ULGA_S10J_STATIC_CANDIDATE_QUERY_LAYER_CONTRACT_IMPLEMENTATION.md",
        BASE_DIR / "ulga" / "reports" / "static_candidate_query_layer_summary.json",
        BASE_DIR / "ulga" / "reports" / "static_candidate_query_layer_validation.json",
    ]


def assert_error(response, code):
    assert "error" in response
    assert response["error"]["code"] == code
    assert {"code", "message", "details"}.issubset(response["error"])
    assert "query_metadata" in response
    assert "candidates" in response


def test_all_required_s10j_files_exist():
    for path in required_files():
        assert path.exists()


def test_query_module_imports():
    assert query_layer is not None


def test_all_nine_query_functions_exist():
    assert len(query_layer.PUBLIC_QUERY_FUNCTIONS) == 9
    for name in query_layer.PUBLIC_QUERY_FUNCTIONS:
        assert hasattr(query_layer, name)


def test_get_static_ranking_view_schema():
    response = query_layer.get_static_ranking_view("balanced_global_view", limit=3)
    assert "query_metadata" in response
    assert "candidates" in response
    assert response["query_metadata"]["query_type"] == "get_static_ranking_view"


def test_get_top_candidates_schema():
    response = query_layer.get_top_candidates(limit=3)
    assert "query_metadata" in response
    assert "candidates" in response
    assert response["query_metadata"]["query_type"] == "get_top_candidates"


def test_theme_query_warning():
    response = query_layer.get_candidates_by_theme("Home", limit=3)
    assert "THEME_SCOPED_VIEW_HEURISTIC_RELEVANCE_WARNING" in response["query_metadata"]["warnings"]


def test_reading_bridge_warning():
    response = query_layer.get_reading_bridge_candidates(limit=3)
    assert "READING_BRIDGE_VIEW_NEEDS_TUNING" in response["query_metadata"]["warnings"]


def test_dialogue_bridge_warning():
    response = query_layer.get_dialogue_bridge_candidates(limit=3)
    assert "DIALOGUE_BRIDGE_VIEW_NEEDS_TUNING" in response["query_metadata"]["warnings"]


def test_a1_safe_query_no_raw_fallback():
    response = query_layer.get_a1_safe_candidates(limit=3)
    assert response["query_metadata"]["view_name"] == "a1_safe_view"
    assert "RAW_RANKING_NOT_ALLOWED_FOR_CURRICULUM_USE" not in response["query_metadata"]["warnings"]


def test_candidate_explanation_schema():
    response = query_layer.get_candidate_explanation("chunk:go_out:safe_chunk_001519")
    explanation = response["candidates"][0]["explanation"]
    assert query_layer.EXPLANATION_FIELDS.issubset(explanation)


def test_unknown_candidate_returns_structured_error():
    response = query_layer.get_candidate_explanation("missing:candidate")
    assert_error(response, "CANDIDATE_NOT_FOUND")


def test_unknown_view_returns_structured_error():
    response = query_layer.get_static_ranking_view("missing_view", limit=2)
    assert_error(response, "UNKNOWN_VIEW_NAME")


def test_static_only_false_rejected():
    response = query_layer.get_top_candidates(limit=2, static_only=False)
    assert_error(response, "STATIC_ONLY_REQUIRED")


def test_learner_id_rejected():
    response = query_layer.query_static_candidates(
        {
            "query_type": "get_top_candidates",
            "view_name": "balanced_global_view",
            "filters": {"learner_id": "abc"},
            "limit": 2,
            "offset": 0,
            "include_explanation": True,
            "include_score_breakdown": True,
            "static_only": True,
        }
    )
    assert_error(response, "ADAPTIVE_FIELD_REJECTED")


def test_student_id_rejected():
    response = query_layer.query_static_candidates(
        {
            "query_type": "get_top_candidates",
            "view_name": "balanced_global_view",
            "filters": {"student_id": "abc"},
            "limit": 2,
            "offset": 0,
            "include_explanation": True,
            "include_score_breakdown": True,
            "static_only": True,
        }
    )
    assert_error(response, "ADAPTIVE_FIELD_REJECTED")


def test_mastery_rejected():
    response = query_layer.query_static_candidates(
        {
            "query_type": "get_top_candidates",
            "view_name": "balanced_global_view",
            "filters": {"mastery": "weak"},
            "limit": 2,
            "offset": 0,
            "include_explanation": True,
            "include_score_breakdown": True,
            "static_only": True,
        }
    )
    assert_error(response, "ADAPTIVE_FIELD_REJECTED")


def test_adaptive_rejected():
    response = query_layer.query_static_candidates(
        {
            "query_type": "get_top_candidates",
            "view_name": "balanced_global_view",
            "filters": {"adaptive": True},
            "limit": 2,
            "offset": 0,
            "include_explanation": True,
            "include_score_breakdown": True,
            "static_only": True,
        }
    )
    assert_error(response, "ADAPTIVE_FIELD_REJECTED")


def test_node_type_candidate_type_conflict_rejected():
    response = query_layer.get_top_candidates(node_type="chunk", candidate_type="vocabulary_candidate", limit=2)
    assert_error(response, "NODE_TYPE_CANDIDATE_TYPE_CONFLICT")


def test_warning_registry_complete():
    assert len(query_layer.REQUIRED_WARNING_CODES) == 20


def test_derived_fields_present():
    response = query_layer.get_top_candidates(limit=1)
    candidate = response["candidates"][0]
    for field in ["node_type", "source_artifact", "bridge_reason", "supporting_authority_layer"]:
        assert field in candidate


def test_level_fields_present():
    response = query_layer.get_top_candidates(limit=1)
    candidate = response["candidates"][0]
    for field in ["cefr", "level", "internal_level", "level_family", "level_band", "level_source"]:
        assert field in candidate


def test_multi_level_coverage_includes_required_levels():
    matrix = query_layer.build_multi_level_coverage_matrix()
    assert [row["level"] for row in matrix] == ["A1", "A1+", "A2", "A2+", "B1", "B1+", "B2", "B2+", "C1", "C2"]


def test_c2_missing_is_known_gap_not_crash():
    matrix = query_layer.build_multi_level_coverage_matrix()
    c2 = next(row for row in matrix if row["level"] == "C2")
    assert c2["status"] == "missing"


def test_view_score_and_raw_static_score_both_present():
    response = query_layer.get_top_candidates(limit=1)
    candidate = response["candidates"][0]
    assert candidate["raw_static_score"] is not None
    assert candidate["view_score"] is not None


def test_response_ordering_preserves_view_rank():
    response = query_layer.get_static_ranking_view("balanced_global_view", limit=5)
    ranks = [candidate["view_rank"] for candidate in response["candidates"]]
    assert ranks == sorted(ranks)


def test_protected_upstream_files_not_mutated_by_query_calls():
    before = {rel: load_json(BASE_DIR / rel) for rel in PROTECTED_FILES}
    query_layer.get_top_candidates(limit=3)
    query_layer.get_candidates_by_theme("Home", limit=3)
    after = {rel: load_json(BASE_DIR / rel) for rel in PROTECTED_FILES}
    assert before == after


def test_s10k_safe_test_plan_exists():
    path = BASE_DIR / "ulga" / "reports" / "static_candidate_query_layer_safe_test_plan.json"
    assert path.exists()
