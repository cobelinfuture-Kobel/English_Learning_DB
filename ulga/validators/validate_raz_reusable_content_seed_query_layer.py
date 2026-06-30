from __future__ import annotations

import json
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
VALIDATION_REPORT_PATH = BASE_DIR / "ulga" / "reports" / "raz_reusable_content_seed_query_layer_validation.json"

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ulga.builders import build_raz_level_discovery as level_discovery  # noqa: E402
from ulga.query import raz_reusable_content_seed_query_layer as query_layer  # noqa: E402


REQUIRED_PUBLIC_FUNCTIONS = [
    "query_reusable_content_seeds",
    "find_reusable_seeds",
    "find_short_reading_seeds",
    "find_exercise_seeds",
    "find_dialogue_rewrite_seeds",
    "find_picture_prompt_seeds",
    "find_theme_seeds",
    "explain_seed",
    "load_seed_cards",
    "generate_summary_report",
]


def fail(message: str) -> bool:
    print(f"FAIL: {message}")
    return False


def validate_response(response: dict, expect_results: bool = True) -> bool:
    if "query_metadata" not in response:
        return fail("response missing query_metadata")
    metadata = response["query_metadata"]
    if metadata.get("static_only") is not True:
        return fail("query_metadata.static_only must be true")
    if metadata.get("adaptive_enabled") is not False:
        return fail("query_metadata.adaptive_enabled must be false")
    if metadata.get("authority_promotion_allowed") is not False:
        return fail("authority promotion must not be allowed")
    if metadata.get("generated_content_returned") is not False:
        return fail("generated content must not be returned")
    if "warnings" not in metadata or not isinstance(metadata["warnings"], list):
        return fail("query_metadata.warnings must be a list")
    if "results" not in response or not isinstance(response["results"], list):
        return fail("response.results must be a list")
    if "error" in response:
        return True
    if expect_results and not response["results"]:
        return fail("expected query results")
    for card in response["results"]:
        missing = query_layer.REQUIRED_SEED_CARD_FIELDS - set(card)
        if missing:
            return fail(f"seed card missing required fields: {sorted(missing)}")
        if card["qa"].get("authority_status") != "candidate_only":
            return fail("seed card authority_status must remain candidate_only")
        if card["qa"].get("final_eligible") is not False:
            return fail("seed card final_eligible must be false")
    return True


def main() -> int:
    print("Validating RAZ Reusable Content Seed Query Layer...")

    for function_name in REQUIRED_PUBLIC_FUNCTIONS:
        if not hasattr(query_layer, function_name):
            return 1 if fail(f"missing public function: {function_name}") is False else 1

    if not query_layer.REQUIRED_WARNING_CODES:
        return 1 if fail("warning code registry is empty") is False else 1

    cards = query_layer.load_seed_cards(include_text=False)
    if not cards:
        return 1 if fail("no seed cards loaded") is False else 1

    matrix = query_layer.build_seed_coverage_matrix(cards=cards)
    discovered_levels = level_discovery.discover_queryable_levels()
    if not discovered_levels:
        return 1 if fail("no queryable levels discovered") is False else 1
    for level in discovered_levels:
        if matrix[level]["total"] <= 0:
            return 1 if fail(f"missing seed coverage for level {level}") is False else 1

    sample_calls = [
        query_layer.find_reusable_seeds(limit=5),
        query_layer.find_short_reading_seeds(limit=5),
        query_layer.find_exercise_seeds({"question_type_candidates": ["reading_comprehension"]}, limit=5),
        query_layer.find_theme_seeds("Science", {"record_types": ["page_unit", "reuse_unit"]}, limit=5),
        query_layer.find_picture_prompt_seeds(limit=5),
    ]
    for response in sample_calls:
        if validate_response(response) is False:
            return 1

    first_seed_id = sample_calls[0]["results"][0]["seed_id"]
    if validate_response(query_layer.explain_seed(first_seed_id), expect_results=True) is False:
        return 1

    rejected_requests = [
        query_layer.query_reusable_content_seeds({"query_type": "find_reusable_seeds", "static_only": False}),
        query_layer.query_reusable_content_seeds({"query_type": "find_reusable_seeds", "filters": {"learner_id": "abc"}, "static_only": True}),
        query_layer.query_reusable_content_seeds({"query_type": "find_reusable_seeds", "filters": {"record_types": ["bad_type"]}, "static_only": True}),
        query_layer.query_reusable_content_seeds({"query_type": "unknown", "filters": {}, "static_only": True}),
    ]

    expected_codes = [
        "STATIC_ONLY_REQUIRED",
        "ADAPTIVE_FIELD_REJECTED",
        "INVALID_RECORD_TYPE_FILTER",
        "UNKNOWN_QUERY_TYPE",
    ]
    for response, code in zip(rejected_requests, expected_codes):
        if "error" not in response or response["error"].get("code") != code:
            return 1 if fail(f"expected rejection code {code}") is False else 1

    summary = query_layer.generate_summary_report(
        validation_summary={"status": "PASS", "validator": "validate_raz_reusable_content_seed_query_layer.py"},
        write_report=True,
    )
    if not query_layer.SUMMARY_REPORT_PATH.exists():
        return 1 if fail("summary report missing") is False else 1
    if summary["total_seed_cards"] != len(cards):
        return 1 if fail("summary seed card count mismatch") is False else 1

    validation_report = {
        "status": "PASS",
        "required_public_functions": REQUIRED_PUBLIC_FUNCTIONS,
        "warning_registry_complete": True,
        "total_seed_cards_checked": len(cards),
        "discovered_queryable_levels": discovered_levels,
        "coverage_matrix": matrix,
        "sample_query_count": len(sample_calls),
        "rejected_request_checks": expected_codes,
        "summary_report": str(query_layer.SUMMARY_REPORT_PATH.relative_to(BASE_DIR)).replace("\\", "/"),
    }
    VALIDATION_REPORT_PATH.write_text(json.dumps(validation_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("PASS: RAZ Reusable Content Seed Query Layer validator succeeded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
