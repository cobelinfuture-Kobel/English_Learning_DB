import pytest

from ulga.query import a1_a1plus_authority_scope_query as query
from ulga.validators import validate_a1_a1plus_authority_scope_query as validator


@pytest.fixture(scope="module")
def a1_scope():
    return query.build_scope("A1")


@pytest.fixture(scope="module")
def a1_plus_scope():
    return query.build_scope("A1_PLUS")


def test_a1_authority_scope_has_expected_identity(a1_scope):
    assert a1_scope["validation_status"] == "PASS_AUTHORITY_SCOPE_QUERY_COMPLETE"
    assert a1_scope["scope"] == {
        "official_cefr_level": "A1",
        "internal_stage": "A1",
        "source_cefr_policy": "DIRECT_A1_AUTHORITY",
        "a2_a2plus_in_scope": False,
        "static_only": True,
    }
    assert a1_scope["counts"]["grammar"] == 109
    assert a1_scope["counts"]["vocabulary"] == 784
    assert a1_scope["counts"]["chunk"] == 76
    assert a1_scope["counts"]["pattern"] == 27
    assert a1_scope["counts"]["theme"] == 9
    assert a1_scope["counts"]["skill"] == 4
    assert a1_scope["counts"]["question_type"] > 0


def test_a1_plus_inherits_a1_authority_and_adds_only_approved_bridge_theme(
    a1_scope, a1_plus_scope
):
    assert a1_plus_scope["scope"]["source_cefr_policy"] == (
        "A1_PLUS_INHERITS_A1_AUTHORITY_WITH_APPROVED_BRIDGE_THEME"
    )
    for authority in ("grammar", "vocabulary", "chunk", "pattern", "skill"):
        assert a1_plus_scope["counts"][authority] == a1_scope["counts"][authority]
    assert a1_plus_scope["counts"]["theme"] == 10
    bridge_rows = [
        row for row in a1_plus_scope["authorities"]["theme"] if row["role"] == "bridge"
    ]
    assert len(bridge_rows) == 1
    assert bridge_rows[0]["theme_id"] == "a1_plus_spiral_expansion"


def test_query_surface_covers_all_required_authorities():
    for authority in query.AUTHORITIES:
        response = query.query_authority(authority, stage="A1", limit=2)
        assert "error" not in response
        assert response["query_metadata"]["static_only"] is True
        assert response["query_metadata"]["result_count"] >= 1
        assert len(response["results"]) <= 2


def test_query_filters_and_guardrails_fail_closed():
    home = query.query_authority("theme", query="居家", limit=20)
    assert home["query_metadata"]["total_match_count"] >= 1
    assert any(row["theme_id"] == "a1_homes_and_neighborhoods" for row in home["results"])

    clamped = query.query_authority("vocabulary", limit=999)
    assert clamped["query_metadata"]["limit"] == query.MAX_LIMIT
    assert "LIMIT_CLAMPED_TO_MAXIMUM" in clamped["query_metadata"]["warnings"]

    assert query.query_authority("grammar", stage="A2")["error"]["code"] == (
        "OUT_OF_SCOPE_LEVEL_STAGE:A2"
    )
    assert query.query_authority("grammar", static_only=False)["error"]["code"] == (
        "STATIC_ONLY_REQUIRED"
    )
    assert query.query_authority("unknown")["error"]["code"] == "UNKNOWN_AUTHORITY"
    assert query.query_authority("grammar", offset=-1)["error"]["code"] == (
        "INVALID_OFFSET"
    )


def test_m01_validator_passes_and_routes_to_m02():
    report = validator.validate()
    assert report["validation_status"] == validator.PASS_STATUS
    assert report["errors"] == []
    assert report["stop_reason"] == "NONE"
    assert report["next_short_step"] == (
        "E4S-A1V1-M02_CrossSkillLearningUnitContractAndBuilder"
    )
    assert report["claim_boundaries"] == {
        "query_validation_complete": True,
        "learner_mastery_claimed": False,
        "retention_confirmed": False,
        "persistent_learner_state_write": False,
        "production_runtime_event": False,
        "a2_a2plus_in_scope": False,
    }
