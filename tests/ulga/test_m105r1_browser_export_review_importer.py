import json
from copy import deepcopy
from pathlib import Path

from ulga.builders.build_a1_grammar_text_mode_private_pilot_package import (
    build_and_validate_from_repo,
)
from ulga.builders.import_a1_grammar_text_mode_browser_review_export import (
    run_browser_review_import,
)
from ulga.builders.import_a1_grammar_text_mode_private_pilot_real_attempts import (
    IMPORT_SCHEMA_VERSION,
    run_import,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = (
    REPO_ROOT
    / "tests/fixtures/a1_grammar_text_mode/browser_review_regular_plurals_attempt2.json"
)
UNIT = "GRAMMAR_REGULAR_PLURAL_NOUNS"
PREFIX = f"{UNIT}__TFX_"


def baseline_source():
    submitted = "2026-07-12T22:42:06+08:00"
    source_ref = "approved-anonymous-test:regular-plurals-attempt1"

    def record(code, response, **extra):
        item_id = f"{PREFIX}{code}"
        return {
            "item_id": item_id,
            "response_text": response,
            "attempt_sequence": 1,
            "submitted_at": submitted,
            "evidence_ref": f"{source_ref}/item/{item_id}/attempt/1",
            **extra,
        }

    return {
        "import_schema_version": IMPORT_SCHEMA_VERSION,
        "session": {
            "session_id": "approved-anonymous-regular-plurals-attempt1",
            "learner_ref": "learner-local-01",
            "operator_ref": "operator-local-01",
            "started_at": submitted,
            "completed_at": submitted,
            "evidence_source_ref": source_ref,
        },
        "responses": [
            record("P01", "cats"),
            record("P02", "boxes"),
            record("P03", "buses"),
            record("P04", "1"),
            record("P05", "2"),
            record(
                "P06",
                "3",
                score=1.0,
                passed=True,
                evaluator_type="MANUAL",
                evaluator_ref="operator-local-01",
            ),
            record("A01", "cats"),
            record(
                "A02",
                "1",
                score=1.0,
                passed=True,
                evaluator_type="MANUAL",
                evaluator_ref="operator-local-01",
            ),
        ],
    }


def setup_projection():
    package, package_report = build_and_validate_from_repo()
    assert package_report["validation_status"] == "PASS"
    source = baseline_source()
    evidence, report, normalized, intake, projection_bundle = run_import(
        source, package=package
    )
    assert report["validation_status"] == "PASS"
    assert intake["validation_status"] == "PASS"
    assert projection_bundle["report"]["validation_status"] == "PASS"
    assert (
        projection_bundle["artifact"]["by_grammar_unit_id"][UNIT][
            "projection_status"
        ]
        == "REVIEW_REQUIRED"
    )
    return package, source, normalized, projection_bundle["artifact"]


def latest_attempts(normalized):
    latest = {}
    for attempt in normalized["accepted_attempts"]:
        item_id = attempt["item_id"]
        if attempt["attempt_sequence"] > latest.get(item_id, {}).get(
            "attempt_sequence", 0
        ):
            latest[item_id] = attempt
    return latest


def test_approved_browser_export_merges_attempt2_and_projects_review_required():
    package, source, normalized, projection = setup_projection()
    browser_export = json.loads(FIXTURE.read_text(encoding="utf-8"))

    bundle, report = run_browser_review_import(
        grammar_unit_id=UNIT,
        previous_source=source,
        previous_normalized=normalized,
        previous_projection=projection,
        browser_export=browser_export,
        package=package,
    )

    assert report["validation_status"] == "PASS"
    assert report["review_item_ids"] == [
        f"{PREFIX}P04",
        f"{PREFIX}P05",
        f"{PREFIX}P06",
        f"{PREFIX}A02",
    ]
    assert report["browser_retry_attempt_count"] == 4
    assert report["projection_status"] == "REVIEW_REQUIRED"
    assert report["review_required"] is True
    assert report["retention_candidate"] is False
    assert report["final_mastery_claimed"] is False
    assert report["next_short_step"].startswith("R7-M105R_")

    latest = latest_attempts(bundle["normalized"])
    assert latest[f"{PREFIX}P04"]["attempt_sequence"] == 2
    assert latest[f"{PREFIX}P04"]["passed"] is True
    assert latest[f"{PREFIX}P05"]["passed"] is True
    assert latest[f"{PREFIX}P06"]["score"] == 0.5
    assert latest[f"{PREFIX}P06"]["passed"] is False
    assert latest[f"{PREFIX}A02"]["score"] == 0.5
    assert latest[f"{PREFIX}A02"]["passed"] is False

    unit_projection = bundle["projection"]["by_grammar_unit_id"][UNIT]
    unresolved = set(unit_projection["unresolved_failure_item_ids"])
    assert f"{PREFIX}P04" not in unresolved
    assert f"{PREFIX}P05" not in unresolved
    assert f"{PREFIX}P06" in unresolved
    assert f"{PREFIX}A02" in unresolved


def test_browser_export_rejects_wrong_attempt_sequence():
    package, source, normalized, projection = setup_projection()
    browser_export = json.loads(FIXTURE.read_text(encoding="utf-8"))
    browser_export["responses"][0]["attempt_sequence"] = 3

    bundle, report = run_browser_review_import(
        grammar_unit_id=UNIT,
        previous_source=source,
        previous_normalized=normalized,
        previous_projection=projection,
        browser_export=browser_export,
        package=package,
    )

    assert bundle == {}
    assert report["validation_status"] == "FAIL"
    assert any(
        error.startswith("browser_export_attempt_sequence_mismatch:")
        for error in report["errors"]
    )


def test_browser_export_rejects_identity_mismatch():
    package, source, normalized, projection = setup_projection()
    browser_export = json.loads(FIXTURE.read_text(encoding="utf-8"))
    browser_export = deepcopy(browser_export)
    browser_export["session"]["learner_ref"] = "another-tester"

    bundle, report = run_browser_review_import(
        grammar_unit_id=UNIT,
        previous_source=source,
        previous_normalized=normalized,
        previous_projection=projection,
        browser_export=browser_export,
        package=package,
    )

    assert bundle == {}
    assert report["validation_status"] == "FAIL"
    assert "browser_export_identity_mismatch:learner_ref" in report["errors"]


def test_public_fixture_is_explicitly_anonymous_and_contains_no_email():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert payload["session"]["learner_ref"] == "learner-local-01"
    assert payload["session"]["operator_ref"] == "operator-local-01"
    assert "@" not in json.dumps(payload, ensure_ascii=False)
