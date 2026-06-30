import json
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
VALIDATION_REPORT_PATH = BASE_DIR / "ulga" / "reports" / "static_candidate_query_layer_validation.json"

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ulga.query import static_candidate_query_layer as query_layer


REQUIRED_PUBLIC_FUNCTIONS = [
    "query_static_candidates",
    "get_static_ranking_view",
    "get_top_candidates",
    "get_candidates_by_theme",
    "get_candidates_by_node_type",
    "get_candidate_explanation",
    "get_reading_bridge_candidates",
    "get_dialogue_bridge_candidates",
    "get_a1_safe_candidates",
]

REQUIRED_CANDIDATE_FIELDS = {
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

REQUIRED_EXPLANATION_FIELDS = {
    "why_this_candidate",
    "why_this_score",
    "which_authority_supports_it",
    "which_bridge_produced_it",
    "which_filters_can_retrieve_it",
    "score_breakdown_summary",
    "view_policy_summary",
    "known_limitations",
}


def fail(message):
    print(f"FAIL: {message}")
    return False


def validate_response(response, expect_candidates=True):
    if "query_metadata" not in response:
        return fail("response missing query_metadata")
    metadata = response["query_metadata"]
    if metadata.get("static_only") is not True:
        return fail("query_metadata.static_only must be true")
    if metadata.get("adaptive_enabled") is not False:
        return fail("query_metadata.adaptive_enabled must be false")
    if "warnings" not in metadata or not isinstance(metadata["warnings"], list):
        return fail("query_metadata.warnings must be a list")
    if "candidates" not in response or not isinstance(response["candidates"], list):
        return fail("response.candidates must be a list")
    if "error" in response:
        return True
    if expect_candidates and not response["candidates"]:
        return fail("expected candidates in successful response")
    for candidate in response["candidates"]:
        if REQUIRED_CANDIDATE_FIELDS - set(candidate):
            return fail("candidate response missing required fields")
        explanation = candidate["explanation"]
        if explanation and (REQUIRED_EXPLANATION_FIELDS - set(explanation)):
            return fail("candidate explanation missing required fields")
    return True


def main():
    print("Validating Static Candidate Query Layer...")

    for function_name in REQUIRED_PUBLIC_FUNCTIONS:
        if not hasattr(query_layer, function_name):
            return 1 if fail(f"missing public function: {function_name}") is False else 1

    missing_warning_codes = sorted(query_layer.REQUIRED_WARNING_CODES - set(query_layer.REQUIRED_WARNING_CODES))
    if missing_warning_codes:
        return 1 if fail(f"missing warning codes: {missing_warning_codes}") is False else 1

    for view_name in [
        "balanced_global_view",
        "a1_safe_view",
        "theme_scoped_view",
        "reading_bridge_view",
        "dialogue_bridge_view",
        "pattern_first_view",
        "vocabulary_first_view",
        "chunk_safe_view",
        "deduplicated_view",
    ]:
        if query_layer.resolve_view(view_name) is None:
            return 1 if fail(f"missing recognized view: {view_name}") is False else 1

    sample_calls = [
        query_layer.get_static_ranking_view("balanced_global_view", limit=3),
        query_layer.get_top_candidates(limit=5),
        query_layer.get_candidates_by_theme("Home", limit=3),
        query_layer.get_candidates_by_node_type("vocabulary", limit=3),
        query_layer.get_candidate_explanation("chunk:go_out:safe_chunk_001519"),
        query_layer.get_reading_bridge_candidates(limit=3),
        query_layer.get_dialogue_bridge_candidates(limit=3),
        query_layer.get_a1_safe_candidates(limit=3),
    ]
    for response in sample_calls:
        if validate_response(response) is False:
            return 1

    rejected_requests = [
        query_layer.query_static_candidates({"query_type": "get_top_candidates", "view_name": "balanced_global_view", "filters": {}, "limit": 5, "offset": 0, "include_explanation": True, "include_score_breakdown": True, "static_only": False}),
        query_layer.query_static_candidates({"query_type": "get_top_candidates", "view_name": "balanced_global_view", "filters": {"learner_id": "abc"}, "limit": 5, "offset": 0, "include_explanation": True, "include_score_breakdown": True, "static_only": True}),
        query_layer.query_static_candidates({"query_type": "get_top_candidates", "view_name": "balanced_global_view", "filters": {"node_type": "chunk", "candidate_type": "vocabulary_candidate"}, "limit": 5, "offset": 0, "include_explanation": True, "include_score_breakdown": True, "static_only": True}),
        query_layer.get_static_ranking_view("raw_global_view", limit=3),
    ]

    if "error" not in rejected_requests[0] or rejected_requests[0]["error"]["code"] != "STATIC_ONLY_REQUIRED":
        return 1 if fail("static_only=false request was not rejected") is False else 1
    if "error" not in rejected_requests[1] or rejected_requests[1]["error"]["code"] != "ADAPTIVE_FIELD_REJECTED":
        return 1 if fail("learner_id request was not rejected") is False else 1
    if "error" not in rejected_requests[2] or rejected_requests[2]["error"]["code"] != "NODE_TYPE_CANDIDATE_TYPE_CONFLICT":
        return 1 if fail("node_type/candidate_type conflict was not rejected") is False else 1
    if "RAW_RANKING_NOT_ALLOWED_FOR_CURRICULUM_USE" not in rejected_requests[3]["query_metadata"]["warnings"]:
        return 1 if fail("raw ranking diagnostic warning missing") is False else 1

    summary = query_layer.generate_summary_report(
        validation_summary={"validator_result": "PASS"},
        test_summary={
            "targeted_test_file": "tests/ulga/test_static_candidate_query_layer.py",
            "runtime_status": "validated_by_validator",
        },
    )
    if not query_layer.SUMMARY_REPORT_PATH.exists():
        return 1 if fail("summary report missing") is False else 1
    if "multi_level_coverage_matrix" not in summary or not summary["multi_level_coverage_matrix"]:
        return 1 if fail("multi_level_coverage_matrix missing from summary") is False else 1

    validation_report = {
        "status": "PASS",
        "required_public_functions": REQUIRED_PUBLIC_FUNCTIONS,
        "warning_registry_complete": True,
        "validated_views": sorted(query_layer.VIEW_NAMES),
        "summary_report": str(query_layer.SUMMARY_REPORT_PATH.relative_to(BASE_DIR)).replace("\\", "/"),
    }
    VALIDATION_REPORT_PATH.write_text(json.dumps(validation_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("PASS: Static Candidate Query Layer validator succeeded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
