"""CI-safe tests for static GrammarSkillTree artifacts.

R6-M5 scope:
- Import and run the static artifact validator.
- Assert the current R6 A1/A1_PLUS expansion chain validates.
- Run under the repository's English DB CI-safe pytest target.
- Do not generate learner-facing practice.
- Do not read or write learner state.
"""

from __future__ import annotations

from ulga.validators.validate_static_grammar_artifacts import validate


EXPECTED_NODE_COUNT = 16
EXPECTED_EDGE_COUNT = 16


def test_static_grammar_artifacts_validate_successfully() -> None:
    report = validate()

    assert report["status"] == "PASS"
    assert report["summary"]["fail_count"] == 0
    assert report["summary"]["node_count"] == EXPECTED_NODE_COUNT
    assert report["summary"]["edge_count"] == EXPECTED_EDGE_COUNT
    assert report["summary"]["order_row_count"] == EXPECTED_NODE_COUNT
    assert report["summary"]["coverage_node_count"] == EXPECTED_NODE_COUNT
    assert report["summary"]["query_node_count"] == EXPECTED_NODE_COUNT
    assert report["scope"]["learner_facing_practice"] is False
    assert report["scope"]["learner_state_write"] is False


def test_static_grammar_artifact_validator_checks_expected_surfaces() -> None:
    report = validate()
    check_ids = {check["id"] for check in report["checks"]}

    required_checks = {
        "EDGE_REFS_RESOLVE",
        "ORDERING_CONSTRAINTS_SATISFIED",
        "COVERAGE_COVERS_NODES",
        "COVERAGE_STAGE_KEYS_COMPLETE",
        "COVERAGE_STAGE_ROLE_COUNTS",
        "QUERY_COVERS_NODES",
        "QUERY_STAGE_ROLE_SURFACE_COMPLETE",
        "LEARNER_STATE_WRITE_FALSE",
    }

    assert required_checks.issubset(check_ids)
