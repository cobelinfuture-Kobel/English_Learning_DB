from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_grammar_learning_unit_core import (  # noqa: E402
    AUTHORITY_PATH,
    CANONICAL_PATH,
    QUERY_PATH,
    RULE_PATH,
    build_artifact,
    load_json,
    validate_artifact,
)

SCHEMA_PATH = REPO_ROOT / "ulga/schemas/a1_grammar_learning_units.schema.json"


def sources():
    return (
        load_json(CANONICAL_PATH),
        load_json(QUERY_PATH),
        load_json(RULE_PATH),
        load_json(AUTHORITY_PATH),
    )


def built():
    canonical, query, rules, authority = sources()
    artifact = build_artifact(canonical, query, rules, authority)
    report = validate_artifact(artifact, canonical, query, rules, authority)
    return artifact, report, (canonical, query, rules, authority)


def test_authority_is_fail_closed_and_a1_only():
    authority = load_json(AUTHORITY_PATH)
    policy = authority["source_use_policy"]
    boundaries = authority["claim_boundaries"]

    assert authority["authority_status"] == (
        "ACTIVE_FOR_STRUCTURAL_LEARNING_CONTENT"
    )
    assert authority["official_level"] == "A1"
    assert authority["internal_stages"] == ["A1", "A1+"]
    assert policy["egp_row_ids_only"] is True
    assert policy["official_egp_text_copied"] is False
    assert policy["raw_external_source_text_copied"] is False
    assert policy["restricted_source_payload_persisted"] is False
    assert boundaries["teaching_content_complete"] is False
    assert boundaries["no_a2_a2plus_expansion"] is True
    assert boundaries["no_learner_state_write"] is True


def test_build_materializes_24_units_and_109_rows():
    artifact, report, _ = built()
    summary = artifact["coverage_summary"]

    assert report["validation_status"] == "PASS"
    assert len(artifact["learning_units"]) == 24
    assert len(artifact["by_egp_row_id"]) == 109
    assert summary["structural_learning_unit_count"] == 24
    assert summary["traceable_unique_egp_row_count"] == 109
    assert summary["structural_unit_coverage_percent"] == 100.0
    assert summary["row_traceability_percent"] == 100.0
    assert summary["teaching_ready_unit_count"] == 0
    assert summary["teachable_unit_coverage_percent"] == 0.0


def test_all_rows_are_traceable_without_egp_text_copy():
    artifact, _, _ = built()

    for row_id, row in artifact["by_egp_row_id"].items():
        assert row["egp_row_id"] == row_id
        assert row["grammar_unit_ids"]
        assert row["internal_stages"]
        assert row["effective_internal_stage"] in {"A1", "A1+"}
        assert row["traceability_status"] == (
            "TRACEABLE_TO_CANONICAL_GRAMMAR_LEARNING_UNIT"
        )
        assert row["official_egp_text_copied"] is False


def test_structural_units_do_not_claim_teaching_readiness():
    artifact, _, _ = built()

    for unit in artifact["learning_units"]:
        assert unit["content_authority"]["authority_status"] == (
            "STRUCTURAL_SCAFFOLD"
        )
        assert unit["readiness"]["structural_learning_unit_status"] == "READY"
        assert unit["readiness"]["teachable"] is False
        assert unit["readiness"]["practice_ready"] is False
        assert unit["readiness"]["assessment_ready"] is False
        assert unit["readiness"]["mastery_trackable"] is False
        assert all(
            value == "NOT_STARTED"
            for value in unit["content_section_status"].values()
        )


def test_schema_accepts_built_artifact():
    jsonschema = pytest.importorskip("jsonschema")
    artifact, _, _ = built()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    jsonschema.validate(instance=artifact, schema=schema)


def test_builder_does_not_mutate_authority_sources():
    canonical, query, rules, authority = sources()
    before = copy.deepcopy((canonical, query, rules, authority))

    build_artifact(canonical, query, rules, authority)

    assert (canonical, query, rules, authority) == before


def test_missing_row_fails_closed():
    artifact, _, source_values = built()
    canonical, query, rules, authority = source_values
    unit = next(
        item for item in artifact["learning_units"]
        if item["canonical_egp_row_ids"]
    )
    removed = unit["canonical_egp_row_ids"].pop()
    unit["canonical_egp_row_count"] -= 1
    artifact["by_egp_row_id"].pop(removed, None)

    report = validate_artifact(artifact, canonical, query, rules, authority)

    assert report["validation_status"] == "FAIL"
    assert any(
        error.startswith("row_set_mismatch")
        or error == "row_traceability_not_109_of_109"
        for error in report["errors"]
    )


def test_false_teaching_readiness_fails_closed():
    artifact, _, source_values = built()
    canonical, query, rules, authority = source_values
    artifact["learning_units"][0]["readiness"]["teachable"] = True
    artifact["coverage_summary"]["teaching_ready_unit_count"] = 1
    artifact["coverage_summary"]["teachable_unit_coverage_percent"] = 4.17

    report = validate_artifact(artifact, canonical, query, rules, authority)

    assert report["validation_status"] == "FAIL"
    assert any(
        error.startswith("false_readiness_claim")
        for error in report["errors"]
    )


def test_prerequisite_cycle_fails_closed():
    artifact, _, source_values = built()
    canonical, query, rules, authority = source_values
    by_id = {
        unit["grammar_unit_id"]: unit
        for unit in artifact["learning_units"]
    }
    by_id["GRAMMAR_SUBJECT_PRONOUNS"]["prerequisite_unit_ids"] = [
        "GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS"
    ]

    report = validate_artifact(artifact, canonical, query, rules, authority)

    assert report["validation_status"] == "FAIL"
    assert any(
        error.startswith("prerequisite_cycle")
        for error in report["errors"]
    )


def test_rule_source_trace_tamper_fails_closed():
    artifact, _, source_values = built()
    canonical, query, rules, authority = source_values
    artifact["learning_units"][0]["source_trace"]["rule_source_path"] = (
        "ulga/rules/not_the_authority.json"
    )

    report = validate_artifact(artifact, canonical, query, rules, authority)

    assert report["validation_status"] == "FAIL"
    assert any(
        error.startswith("source_trace_mismatch")
        for error in report["errors"]
    )
