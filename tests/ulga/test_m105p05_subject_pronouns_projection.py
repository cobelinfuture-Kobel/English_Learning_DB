import json
from pathlib import Path

from ulga.builders.build_a1_grammar_text_mode_private_pilot_package import build_and_validate_from_repo
from ulga.builders.import_a1_grammar_text_mode_private_pilot_real_attempts import run_import

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = REPO_ROOT / "tests/fixtures/a1_grammar_text_mode/subject_pronouns_attempt1_normalized.json"
UNIT = "GRAMMAR_SUBJECT_PRONOUNS"
P03 = f"{UNIT}__TFX_P03"


def test_normalized_subject_pronouns_projects_only_p03_review_required():
    package, package_report = build_and_validate_from_repo()
    assert package_report["validation_status"] == "PASS"
    source = json.loads(FIXTURE.read_text(encoding="utf-8"))
    evidence, report, normalized, intake, projection_bundle = run_import(source, package=package)
    assert report["validation_status"] == "PASS"
    assert intake["validation_status"] == "PASS"
    assert projection_bundle["report"]["validation_status"] == "PASS"
    unit = projection_bundle["artifact"]["by_grammar_unit_id"][UNIT]
    assert unit["attempted_item_count"] == 8
    assert unit["projection_status"] == "REVIEW_REQUIRED"
    assert unit["unresolved_failure_item_ids"] == [P03]
    latest = {item["item_id"]: item for item in normalized["accepted_attempts"]}
    assert latest[P03]["response_text"] == "Her book is red."
    assert latest[P03]["passed"] is False
    assert projection_bundle["artifact"].get("final_mastery_claimed", False) is False


def test_fixture_is_anonymous_and_contains_no_email():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert payload["session"]["learner_ref"] == "learner-local-01"
    assert payload["session"]["operator_ref"] == "operator-local-01"
    assert "@" not in json.dumps(payload, ensure_ascii=False)
