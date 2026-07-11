from __future__ import annotations

import copy
import json
from pathlib import Path

from ulga.builders.build_a1_grammar_text_mode_private_pilot_evidence_intake import (
    INTAKE_PATH,
)
from ulga.builders.build_a1_grammar_text_mode_private_pilot_package import (
    build_and_validate_from_repo as build_package_source,
)
from ulga.builders.import_a1_grammar_text_mode_private_pilot_real_attempts import (
    IMPORT_SCHEMA_VERSION,
    OPEN_PRODUCTIVE_TASK_TYPES,
    REPO_ROOT,
    _private_path_error,
    build_evidence_payload,
    run_import,
)


def package():
    artifact, report = build_package_source()
    assert report["validation_status"] == "PASS"
    return artifact


def template():
    return json.loads(Path(INTAKE_PATH).read_text(encoding="utf-8"))


def source(records):
    return {
        "import_schema_version": IMPORT_SCHEMA_VERSION,
        "session": {
            "session_id": "session:A1_REAL_IMPORT_001",
            "learner_ref": "learner:PRIVATE_001",
            "operator_ref": "operator:cobelinfuture-Kobel",
            "started_at": "2026-07-11T16:00:00+08:00",
            "completed_at": None,
            "evidence_source_ref": "local_private_pilot://A1_REAL_IMPORT_001",
        },
        "responses": records,
    }


def response(item, text, **overrides):
    record = {
        "item_id": item["item_id"],
        "response_text": text,
        "attempt_sequence": 1,
        "submitted_at": "2026-07-11T16:05:00+08:00",
    }
    record.update(overrides)
    return record


def fixed_item(source_package):
    return next(
        item
        for item in source_package["item_bank"]
        if item.get("task_type") not in OPEN_PRODUCTIVE_TASK_TYPES
    )


def productive_item(source_package):
    return next(
        item
        for item in source_package["item_bank"]
        if item.get("task_type") in OPEN_PRODUCTIVE_TASK_TYPES
    )


def canonical(item):
    return item["answer_key"]["canonical_target"]


def test_exact_fixed_response_is_rule_evaluated_and_normalized():
    source_package = package()
    item = fixed_item(source_package)

    evidence, report = build_evidence_payload(
        source([response(item, canonical(item))]),
        source_package,
        template(),
    )

    assert report["validation_status"] == "PASS"
    assert report["rule_evaluated_attempt_count"] == 1
    attempt = evidence["attempts"][0]
    assert attempt["passed"] is True
    assert attempt["score"] == 1.0
    assert attempt["outcome"] == "PASS"
    assert attempt["error_tags"] == []
    assert attempt["synthetic_fixture"] is False
    assert attempt["persistent_learner_state_write"] is False
    assert attempt["production_runtime_event"] is False


def test_incorrect_fixed_response_gets_generic_failure_tag():
    source_package = package()
    item = fixed_item(source_package)

    evidence, report = build_evidence_payload(
        source([response(item, "definitely not the accepted answer")]),
        source_package,
        template(),
    )

    assert report["validation_status"] == "PASS"
    attempt = evidence["attempts"][0]
    assert attempt["passed"] is False
    assert attempt["score"] == 0.0
    assert attempt["error_tags"] == ["ERR_UNCLASSIFIED_GRAMMAR_FAILURE"]


def test_non_exact_productive_response_requires_manual_evaluation():
    source_package = package()
    item = productive_item(source_package)

    _, report = build_evidence_payload(
        source([response(item, "A different but potentially valid learner sentence.")]),
        source_package,
        template(),
    )

    assert report["validation_status"] == "FAIL"
    assert any("manual_evaluation_required" in error for error in report["errors"])


def test_manually_scored_productive_response_is_accepted_at_rubric_threshold():
    source_package = package()
    item = productive_item(source_package)
    threshold = item["scoring_rubric"]["minimum_score"]

    evidence, report = build_evidence_payload(
        source(
            [
                response(
                    item,
                    "A different but valid learner sentence.",
                    score=threshold,
                    passed=True,
                    evaluator_type="MANUAL",
                    evaluator_ref="operator:cobelinfuture-Kobel",
                )
            ]
        ),
        source_package,
        template(),
    )

    assert report["validation_status"] == "PASS"
    attempt = evidence["attempts"][0]
    assert attempt["evaluator_type"] == "MANUAL"
    assert attempt["passed"] is True
    assert attempt["score"] == threshold


def test_manual_passed_value_must_match_item_threshold():
    source_package = package()
    item = productive_item(source_package)

    _, report = build_evidence_payload(
        source(
            [
                response(
                    item,
                    "A learner sentence.",
                    score=0.2,
                    passed=True,
                    evaluator_type="MANUAL",
                    evaluator_ref="operator:cobelinfuture-Kobel",
                )
            ]
        ),
        source_package,
        template(),
    )

    assert report["validation_status"] == "FAIL"
    assert any("manual_passed_score_mismatch" in error for error in report["errors"])


def test_unknown_item_and_external_identity_fields_fail_closed():
    source_package = package()
    item = fixed_item(source_package)
    raw = response(item, canonical(item))
    raw["grammar_unit_id"] = "FORGED_GRAMMAR_ID"

    _, report = build_evidence_payload(
        source([raw]),
        source_package,
        template(),
    )

    assert report["validation_status"] == "FAIL"
    assert any("external_identity_fields_forbidden" in error for error in report["errors"])

    unknown = response(item, canonical(item))
    unknown["item_id"] = "UNKNOWN_ITEM"
    _, unknown_report = build_evidence_payload(
        source([unknown]),
        source_package,
        template(),
    )
    assert unknown_report["validation_status"] == "FAIL"
    assert any("unknown_item_id:UNKNOWN_ITEM" in error for error in unknown_report["errors"])


def test_duplicate_item_attempt_sequence_is_rejected():
    source_package = package()
    item = fixed_item(source_package)
    records = [
        response(item, canonical(item)),
        response(item, canonical(item)),
    ]

    _, report = build_evidence_payload(
        source(records),
        source_package,
        template(),
    )

    assert report["validation_status"] == "FAIL"
    assert any("duplicate_item_attempt_sequence" in error for error in report["errors"])


def test_empty_response_source_cannot_open_real_import():
    evidence, report = build_evidence_payload(
        source([]),
        package(),
        template(),
    )

    assert report["validation_status"] == "FAIL"
    assert "import_real_responses_required" in report["errors"]
    assert evidence["attempts"] == []
    assert evidence["pilot_completion_claim"] == "NOT_STARTED"


def test_one_real_response_runs_m105p_and_m105q_without_final_mastery():
    source_package = package()
    item = fixed_item(source_package)

    evidence, import_report, normalized, intake_report, projection_bundle = run_import(
        source([response(item, canonical(item))]),
        source_package,
        template(),
    )

    assert import_report["validation_status"] == "PASS"
    assert evidence["pilot_completion_claim"] == "PARTIAL"
    assert intake_report["validation_status"] == "PASS"
    assert intake_report["intake_status"] == "PARTIAL_REAL_EVIDENCE_ACCEPTED"
    assert normalized["coverage_summary"]["actual_attempt_count"] == 1

    projection = projection_bundle["artifact"]
    projection_report = projection_bundle["report"]
    assert projection_report["validation_status"] == "PASS"
    assert projection["coverage_summary"]["actual_attempt_count"] == 1
    assert projection["coverage_summary"]["completion_route_count"] == 1
    assert projection["coverage_summary"]["final_mastered_unit_count"] == 0
    assert projection["coverage_summary"]["final_mastered_row_count"] == 0


def test_private_paths_must_be_under_dot_local_or_outside_repo(tmp_path):
    assert _private_path_error(REPO_ROOT / ".local/evidence.json") is None
    assert _private_path_error(tmp_path / "evidence.json") is None
    assert _private_path_error(REPO_ROOT / "ulga/evidence/private.json") is not None


def test_import_builder_is_deterministic_and_does_not_mutate_inputs():
    source_package = package()
    source_template = template()
    item = fixed_item(source_package)
    response_source = source([response(item, canonical(item))])
    before = copy.deepcopy((response_source, source_package, source_template))

    first = build_evidence_payload(response_source, source_package, source_template)
    second = build_evidence_payload(response_source, source_package, source_template)

    assert first == second
    assert (response_source, source_package, source_template) == before
