import json
from pathlib import Path

from tests.ulga.test_m105r1_browser_export_review_importer import (
    FIXTURE as ATTEMPT2_FIXTURE,
    PREFIX,
    UNIT,
    latest_attempts,
    setup_projection,
)
from ulga.builders.import_a1_grammar_text_mode_browser_review_export import (
    run_browser_review_import,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
ATTEMPT3_FIXTURE = (
    REPO_ROOT
    / "tests/fixtures/a1_grammar_text_mode/browser_review_regular_plurals_attempt3.json"
)


def test_operator_approved_attempt3_reaches_retention_candidate():
    package, source1, normalized1, projection1 = setup_projection()
    attempt2 = json.loads(ATTEMPT2_FIXTURE.read_text(encoding="utf-8"))

    bundle2, report2 = run_browser_review_import(
        grammar_unit_id=UNIT,
        previous_source=source1,
        previous_normalized=normalized1,
        previous_projection=projection1,
        browser_export=attempt2,
        package=package,
    )
    assert report2["validation_status"] == "PASS"
    assert report2["projection_status"] == "REVIEW_REQUIRED"

    attempt3 = json.loads(ATTEMPT3_FIXTURE.read_text(encoding="utf-8"))
    bundle3, report3 = run_browser_review_import(
        grammar_unit_id=UNIT,
        previous_source=bundle2["combined_source"],
        previous_normalized=bundle2["normalized"],
        previous_projection=bundle2["projection"],
        browser_export=attempt3,
        package=package,
    )

    assert report3["validation_status"] == "PASS"
    assert report3["review_item_ids"] == [f"{PREFIX}P06", f"{PREFIX}A02"]
    assert report3["browser_retry_attempt_count"] == 2
    assert report3["projection_status"] == "MASTERY_CANDIDATE_PENDING_RETENTION"
    assert report3["review_required"] is False
    assert report3["retention_candidate"] is True
    assert report3["final_mastery_claimed"] is False
    assert report3["retention_resume_task"] is not None

    latest = latest_attempts(bundle3["normalized"])
    assert latest[f"{PREFIX}P06"]["attempt_sequence"] == 3
    assert latest[f"{PREFIX}P06"]["passed"] is True
    assert latest[f"{PREFIX}A02"]["attempt_sequence"] == 3
    assert latest[f"{PREFIX}A02"]["passed"] is True

    unit_projection = bundle3["projection"]["by_grammar_unit_id"][UNIT]
    assert unit_projection["unresolved_failure_item_ids"] == []


def test_attempt3_fixture_is_two_item_anonymous_normalization_only():
    payload = json.loads(ATTEMPT3_FIXTURE.read_text(encoding="utf-8"))
    assert payload["session"]["learner_ref"] == "learner-local-01"
    assert payload["session"]["operator_ref"] == "operator-local-01"
    assert [record["item_id"] for record in payload["responses"]] == [
        f"{PREFIX}P06",
        f"{PREFIX}A02",
    ]
    assert {record["attempt_sequence"] for record in payload["responses"]} == {3}
    assert "@" not in json.dumps(payload, ensure_ascii=False)
