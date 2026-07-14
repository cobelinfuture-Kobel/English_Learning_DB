import json
from copy import deepcopy
from pathlib import Path

from ulga.builders.build_a1_grammar_text_mode_private_pilot_package import build_and_validate_from_repo
from ulga.builders.import_a1_grammar_text_mode_private_pilot_real_attempts import run_import

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE = REPO_ROOT / "tests/fixtures/a1_grammar_text_mode/subject_pronouns_attempt1_normalized.json"
REVIEW = REPO_ROOT / "tests/fixtures/a1_grammar_text_mode/subject_pronouns_p03_attempt2.json"
UNIT = "GRAMMAR_SUBJECT_PRONOUNS"
P03 = f"{UNIT}__TFX_P03"


def combined_source():
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    review = json.loads(REVIEW.read_text(encoding="utf-8"))
    source = deepcopy(baseline)
    source["session"]["completed_at"] = review["session"]["completed_at"]
    source["responses"].extend(review["responses"])
    return source


def test_p03_attempt2_resolves_review_and_projects_retention_candidate():
    package, package_report = build_and_validate_from_repo()
    assert package_report["validation_status"] == "PASS"
    evidence, report, normalized, intake, projection_bundle = run_import(combined_source(), package=package)
    assert report["validation_status"] == "PASS"
    assert intake["validation_status"] == "PASS"
    assert projection_bundle["report"]["validation_status"] == "PASS"
    unit = projection_bundle["artifact"]["by_grammar_unit_id"][UNIT]
    assert unit["attempted_item_count"] >= 8
    assert unit["projection_status"] == "MASTERY_CANDIDATE_PENDING_RETENTION"
    assert unit["unresolved_failure_item_ids"] == []
    attempts = [item for item in normalized["accepted_attempts"] if item["item_id"] == P03]
    assert [item["attempt_sequence"] for item in attempts] == [1, 2]
    assert attempts[-1]["response_text"] == "They play football."
    assert attempts[-1]["passed"] is True
    assert projection_bundle["artifact"].get("final_mastery_claimed", False) is False


def test_attempt2_fixture_is_anonymous_and_exactly_one_item():
    payload = json.loads(REVIEW.read_text(encoding="utf-8"))
    assert payload["session"]["learner_ref"] == "learner-local-01"
    assert payload["session"]["operator_ref"] == "operator-local-01"
    assert len(payload["responses"]) == 1
    assert payload["responses"][0]["item_id"] == P03
    assert payload["responses"][0]["attempt_sequence"] == 2
    assert "@" not in json.dumps(payload, ensure_ascii=False)
