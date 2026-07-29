from __future__ import annotations

from copy import deepcopy

import pytest

from ulga.builders import build_a1fs_v1_razq01b_unit01_content_contract as contract_builder
from ulga.builders import build_a1fs_v1_razq01c_unit01_three_skill_candidate_selection_coverage_balancing as selection
from ulga.validators import validate_a1fs_v1_razq01c_unit01_three_skill_candidate_selection_coverage_balancing as validator


def _candidate(
    identity: str,
    text: str,
    *,
    nouns: list[str],
    adjectives: list[str] | None = None,
    direct_phrases: list[str] | None = None,
    adjective_phrases: list[str] | None = None,
    skills: list[str] | None = None,
) -> dict:
    return {
        "classification": "PASS",
        "source_record_id": f"SRC_{identity}",
        "semantic_identity": identity,
        "source_level": "A",
        "source_type": "page_unit",
        "text_excerpt": text,
        "skill_eligibility": skills
        or [
            "READING_SOURCE_ELIGIBLE",
            "SPEAKING_PROMPT_ELIGIBLE",
            "WRITING_SEED_ELIGIBLE",
        ],
        "contract_gate": {
            "classification": "PASS",
            "active_noun_hits": nouns,
            "active_adjective_hits": adjectives or [],
            "direct_noun_phrases": direct_phrases or [],
            "adjective_noun_phrases": adjective_phrases or [],
            "very_adjective_noun_phrases": [],
        },
    }


def _report() -> dict:
    candidates = [
        _candidate(
            "s1",
            "This is a book.",
            nouns=["book"],
            direct_phrases=["a book"],
        ),
        _candidate(
            "s2",
            "The big cat runs.",
            nouns=["cat"],
            adjectives=["big"],
            adjective_phrases=["the big cat"],
        ),
        _candidate(
            "s3",
            "She shops for a book.",
            nouns=["book"],
            direct_phrases=["a book"],
        ),
        _candidate(
            "s4",
            "The first egg is in the tree.",
            nouns=["egg", "tree"],
            direct_phrases=["the tree"],
        ),
        _candidate(
            "s5",
            '"Do not eat the tree!',
            nouns=["tree"],
            direct_phrases=["the tree"],
        ),
    ]
    return {
        "schema_version": selection.replay_v2.SCHEMA_VERSION,
        "task_id": selection.replay_v2.TASK_ID,
        "status": selection.replay_v2.PASS_STATUS,
        "scope": {
            "allowed_units": [selection.UNIT_ID],
            "blocked_units": "UNIT_02_TO_UNIT_24",
            "canonical_promotion": False,
            "learner_facing_content_write": False,
            "a2_status": "LOCKED",
        },
        "inputs": {
            "approved_contract_sha256": selection.APPROVED_CONTRACT_SHA256
        },
        "records_scanned": 5,
        "unit": {
            "filter_funnel": {"pass_count": len(candidates)},
            "samples": {"PASS": candidates},
        },
    }


def test_all_selection_classes_are_deterministic() -> None:
    result = selection.build_selection(
        _report(), contract_builder.build_contract()
    )
    classes = [
        row["selection_class"] for row in result["selected_candidates"]
    ]
    assert classes == [
        "DIRECT_MODEL",
        "CONTROLLED_PRACTICE_SOURCE",
        "CONTROLLED_PRACTICE_SOURCE",
        "REWRITE_REQUIRED",
        "REJECT",
    ]
    assert result["selection_summary"]["strict_candidate_count"] == 5
    assert (
        sum(result["selection_summary"]["classification_counts"].values())
        == 5
    )


def test_incomplete_strict_manifest_fails_closed() -> None:
    report = _report()
    report["unit"]["samples"]["PASS"].pop()
    with pytest.raises(
        selection.SelectionError,
        match="COMPLETE_STRICT_CANDIDATE_MANIFEST_REQUIRED",
    ):
        selection.build_selection(report, contract_builder.build_contract())


def test_gap_specs_balance_all_contract_dimensions_without_learner_text() -> None:
    result = selection.build_selection(
        _report(), contract_builder.build_contract()
    )
    coverage = result["coverage"]
    assert coverage["source_coverage_complete"] is False
    assert coverage["planned_coverage_complete"] is True
    for dimension in (
        "active_nouns",
        "active_adjectives",
        "articles",
        "sentence_frames",
    ):
        assert (
            coverage["planned_coverage_after_gap_specs"][dimension][
                "missing_after_gap_specs"
            ]
            == []
        )
    assert coverage["project_authored_gap_specs"]
    assert all(
        spec["candidate_only"] is True
        for spec in coverage["project_authored_gap_specs"]
    )
    assert all(
        not ({"text", "prompt", "answer", "answer_key"} & set(spec))
        for spec in coverage["project_authored_gap_specs"]
    )


def test_validator_accepts_selection_and_preserves_listening_boundary() -> None:
    result = selection.build_selection(
        _report(), contract_builder.build_contract()
    )
    validated = validator.validate_report(result)
    assert validated["validation_status"] == validator.PASS_STATUS
    assert validated["strict_candidate_count"] == 5
    assert (
        validated["listening_status"]
        == "DEFERRED_NO_LISTENING_LESSON_IN_UNIT01_RUNTIME"
    )


def test_validator_fails_closed_on_canonical_or_listening_drift() -> None:
    result = selection.build_selection(
        _report(), contract_builder.build_contract()
    )
    drifted = deepcopy(result)
    drifted["scope"]["canonical_promotion"] = True
    with pytest.raises(
        validator.SelectionValidationError,
        match="canonical_promotion_forbidden",
    ):
        validator.validate_report(drifted)
    drifted = deepcopy(result)
    drifted["listening_readback"]["listening_task_candidate_count"] = 1
    with pytest.raises(
        validator.SelectionValidationError,
        match="listening_candidate_count_nonzero",
    ):
        validator.validate_report(drifted)
