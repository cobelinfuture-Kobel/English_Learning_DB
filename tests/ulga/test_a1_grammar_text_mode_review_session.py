from __future__ import annotations

import json
from datetime import datetime, timezone

from ulga.builders.import_a1_grammar_text_mode_private_pilot_real_attempts import (
    _evaluate_record,
)
from ulga.builders.run_a1_grammar_text_mode_private_pilot_next_unit import (
    _collect_response,
    _contains_linguistic_content,
    _learner_task_material,
    _learner_visible_context,
)
from ulga.builders.run_a1_grammar_text_mode_review_session import (
    build_combined_review_source,
    build_preview_report,
    find_latest_source_snapshot,
    select_review_item_ids,
    suspicious_productive_pass_item_ids,
)


def _package_fixture():
    target_items = [
        {
            "item_id": "UNIT_A_P01",
            "skill": "reading",
            "item_role": "practice",
            "task_type": "form_choice",
            "options": ["cats", "child"],
        },
        {
            "item_id": "UNIT_A_P02",
            "skill": "reading",
            "item_role": "practice",
            "task_type": "context_choice",
            "options": ["boxes", "child"],
        },
        {
            "item_id": "UNIT_A_P03",
            "skill": "reading",
            "item_role": "practice",
            "task_type": "form_choice",
            "options": ["buses", "child"],
        },
        {
            "item_id": "UNIT_A_P04",
            "skill": "writing",
            "item_role": "practice",
            "task_type": "structured_gap_fill",
        },
        {
            "item_id": "UNIT_A_P05",
            "skill": "writing",
            "item_role": "practice",
            "task_type": "structured_morphology_build",
        },
        {
            "item_id": "UNIT_A_P06",
            "skill": "writing",
            "item_role": "practice",
            "task_type": "guided_contextual_writing",
            "scoring_rubric": {"minimum_score": 0.8},
        },
        {
            "item_id": "UNIT_A_A01",
            "skill": "reading",
            "item_role": "assessment",
            "task_type": "context_choice",
            "options": ["cats", "child"],
        },
        {
            "item_id": "UNIT_A_A02",
            "skill": "writing",
            "item_role": "assessment",
            "task_type": "text_mode_writing_checkpoint",
            "scoring_rubric": {"minimum_score": 0.8},
        },
    ]
    filler_items = [
        {
            "item_id": f"FILLER_{index:03d}",
            "skill": "reading",
            "item_role": "practice",
            "task_type": "form_choice",
        }
        for index in range(184)
    ]
    return {
        "learning_units": [
            {
                "grammar_unit_id": "UNIT_A",
                "delivery_plan": {
                    "practice_item_ids": [
                        "UNIT_A_P01",
                        "UNIT_A_P02",
                        "UNIT_A_P03",
                        "UNIT_A_P04",
                        "UNIT_A_P05",
                        "UNIT_A_P06",
                    ],
                    "assessment_item_ids": [
                        "UNIT_A_A01",
                        "UNIT_A_A02",
                    ],
                },
            }
        ],
        "item_bank": target_items + filler_items,
    }


def _normalized_fixture():
    return {
        "accepted_attempts": [
            {
                "item_id": "UNIT_A_P04",
                "attempt_sequence": 1,
                "response_text": "1",
                "score": 0.0,
                "passed": False,
                "evaluator_type": "RULE",
            },
            {
                "item_id": "UNIT_A_P05",
                "attempt_sequence": 1,
                "response_text": "2",
                "score": 0.0,
                "passed": False,
                "evaluator_type": "RULE",
            },
            {
                "item_id": "UNIT_A_P06",
                "attempt_sequence": 1,
                "response_text": "3",
                "score": 1.0,
                "passed": True,
                "evaluator_type": "MANUAL",
            },
            {
                "item_id": "UNIT_A_A02",
                "attempt_sequence": 1,
                "response_text": "1",
                "score": 1.0,
                "passed": True,
                "evaluator_type": "MANUAL",
            },
        ]
    }


def _projection_fixture():
    return {
        "by_grammar_unit_id": {
            "UNIT_A": {
                "projection_status": "REVIEW_REQUIRED",
                "unresolved_failure_item_ids": [
                    "UNIT_A_P04",
                    "UNIT_A_P05",
                ],
                "review_reasons": [
                    "WRITING_SCORE_BELOW_THRESHOLD",
                    "UNRESOLVED_LATEST_FAILURE",
                ],
            }
        }
    }


def test_contains_linguistic_content_requires_letters():
    assert _contains_linguistic_content("cats") is True
    assert _contains_linguistic_content("3 cats") is True
    assert _contains_linguistic_content("1") is False
    assert _contains_linguistic_content("...") is False


def test_numeric_productive_response_is_forced_fail_without_score_prompt():
    prompts = iter(["3"])

    def fake_input(prompt):
        return next(prompts)

    item = {
        "item_id": "UNIT_A_P06",
        "task_type": "guided_contextual_writing",
        "scoring_rubric": {"minimum_score": 0.8},
    }
    record = _collect_response(
        item,
        operator_ref="operator:test",
        input_func=fake_input,
    )

    assert record["response_text"] == "3"
    assert record["score"] == 0.0
    assert record["passed"] is False
    assert record["evaluator_type"] == "HYBRID"
    assert record["error_tags"] == ["ERR_UNCLASSIFIED_GRAMMAR_FAILURE"]


def test_linguistic_productive_response_still_uses_operator_score():
    prompts = iter(["Three cats.", "1"])

    def fake_input(prompt):
        return next(prompts)

    item = {
        "item_id": "UNIT_A_P06",
        "task_type": "guided_contextual_writing",
        "scoring_rubric": {"minimum_score": 0.8},
    }
    record = _collect_response(
        item,
        operator_ref="operator:test",
        input_func=fake_input,
    )

    assert record["response_text"] == "Three cats."
    assert record["score"] == 1.0
    assert record["passed"] is True
    assert record["evaluator_type"] == "MANUAL"


def test_suspicious_productive_pass_detects_numeric_manual_passes():
    package = _package_fixture()
    item_index = {
        item["item_id"]: item for item in package["item_bank"]
    }

    suspicious = suspicious_productive_pass_item_ids(
        _normalized_fixture(),
        item_index,
    )

    assert suspicious == ["UNIT_A_A02", "UNIT_A_P06"]


def test_review_selection_includes_failed_and_suspicious_writing_items():
    review_items, reasons, suspicious = select_review_item_ids(
        _package_fixture(),
        _projection_fixture(),
        _normalized_fixture(),
        "UNIT_A",
    )

    assert review_items == [
        "UNIT_A_P04",
        "UNIT_A_P05",
        "UNIT_A_P06",
        "UNIT_A_A02",
    ]
    assert "WRITING_SCORE_BELOW_THRESHOLD" in reasons
    assert suspicious == ["UNIT_A_A02", "UNIT_A_P06"]


def test_build_combined_review_source_preserves_prior_attempts():
    previous = {
        "session": {
            "learner_ref": "learner:test",
            "operator_ref": "operator:test",
            "evidence_source_ref": "local_private_pilot://session:baseline",
        },
        "responses": [
            {
                "item_id": "UNIT_A_P04",
                "response_text": "1",
                "attempt_sequence": 1,
                "submitted_at": "2026-07-12T22:00:00+08:00",
            }
        ],
    }
    retry = {
        "item_id": "UNIT_A_P04",
        "response_text": "cats",
        "attempt_sequence": 2,
        "submitted_at": "2026-07-12T23:00:00+08:00",
    }
    started = datetime(2026, 7, 12, 23, 0, tzinfo=timezone.utc)
    completed = datetime(2026, 7, 12, 23, 5, tzinfo=timezone.utc)

    combined = build_combined_review_source(
        previous,
        [retry],
        grammar_unit_id="UNIT_A",
        started_at=started,
        completed_at=completed,
    )

    assert combined["import_schema_version"].endswith(".v1")
    assert len(combined["responses"]) == 2
    assert combined["responses"][0]["attempt_sequence"] == 1
    assert combined["responses"][0]["evidence_ref"].startswith(
        "local_private_pilot://session:baseline/item/"
    )
    assert combined["responses"][1]["attempt_sequence"] == 2
    assert combined["session"]["learner_ref"] == "learner:test"


def test_find_latest_source_snapshot_uses_latest_valid_directory(tmp_path):
    unit_root = tmp_path / ".local" / "units" / "UNIT_A"
    older = unit_root / "20260712T220000+0800"
    newer = unit_root / "20260712T230000+0800_review"
    invalid = unit_root / "20260712T235000+0800"
    for path in (older, newer, invalid):
        path.mkdir(parents=True)
    for path in (older, newer):
        for name in ("responses.json", "normalized.json", "projection.json"):
            (path / name).write_text("{}", encoding="utf-8")
    (invalid / "responses.json").write_text("{}", encoding="utf-8")

    latest = find_latest_source_snapshot(
        tmp_path / ".local" / "units",
        "UNIT_A",
    )

    assert latest == newer


def test_review_preview_does_not_claim_new_evidence(tmp_path):
    report = build_preview_report(
        grammar_unit_id="UNIT_A",
        source_snapshot=tmp_path / "snapshot",
        review_item_ids=["UNIT_A_P04", "UNIT_A_P06"],
        review_reasons=["UNRESOLVED_LATEST_FAILURE"],
        suspicious_item_ids=["UNIT_A_P06"],
    )

    assert report["validation_status"] == "PASS"
    assert report["execution_status"] == "REVIEW_SESSION_READY"
    assert report["review_item_count"] == 2
    assert report["real_learner_evidence_created"] is False
    assert report["persistent_learner_state_write"] is False


def test_importer_forces_numeric_productive_manual_pass_to_fail():
    record = {
        "item_id": "UNIT_A_P06",
        "response_text": "3",
        "attempt_sequence": 1,
        "submitted_at": "2026-07-12T23:00:00+08:00",
        "score": 1.0,
        "passed": True,
        "evaluator_type": "MANUAL",
        "evaluator_ref": "operator:test",
        "error_tags": [],
    }
    item = {
        "item_id": "UNIT_A_P06",
        "task_type": "guided_contextual_writing",
        "scoring_rubric": {"minimum_score": 0.8},
    }
    session = {
        "session_id": "session:test",
        "evidence_source_ref": "local_private_pilot://session:test",
    }

    attempt, errors = _evaluate_record(
        record,
        item,
        session,
        index=0,
    )

    assert errors == []
    assert attempt is not None
    assert attempt["response_text"] == "3"
    assert attempt["score"] == 0.0
    assert attempt["passed"] is False
    assert attempt["outcome"] == "FAIL"
    assert attempt["evaluator_type"] == "HYBRID"
    assert attempt["evaluator_ref"] == (
        "hybrid:a1_productive_linguistic_guard.v1"
    )
    assert attempt["error_tags"] == ["ERR_UNCLASSIFIED_GRAMMAR_FAILURE"]


def test_importer_keeps_linguistic_productive_manual_evaluation():
    record = {
        "item_id": "UNIT_A_P06",
        "response_text": "Three cats.",
        "attempt_sequence": 1,
        "submitted_at": "2026-07-12T23:00:00+08:00",
        "score": 1.0,
        "passed": True,
        "evaluator_type": "MANUAL",
        "evaluator_ref": "operator:test",
        "error_tags": [],
    }
    item = {
        "item_id": "UNIT_A_P06",
        "task_type": "guided_contextual_writing",
        "scoring_rubric": {"minimum_score": 0.8},
    }
    session = {
        "session_id": "session:test",
        "evidence_source_ref": "local_private_pilot://session:test",
    }

    attempt, errors = _evaluate_record(
        record,
        item,
        session,
        index=0,
    )

    assert errors == []
    assert attempt is not None
    assert attempt["score"] == 1.0
    assert attempt["passed"] is True
    assert attempt["evaluator_type"] == "MANUAL"
    assert attempt["evaluator_ref"] == "operator:test"


def test_learner_visible_context_hides_legacy_model_target():
    item = {
        "context": {
            "situation": "Write about more than one animal.",
            "communicative_goal": "produce a plural noun",
            "grammar_clue": "Use regular -s.",
            "model_target": "cats",
            "internal_note": "not learner-facing",
        }
    }

    visible = _learner_visible_context(item)

    assert visible == {
        "situation": "Write about more than one animal.",
        "communicative_goal": "produce a plural noun",
        "grammar_clue": "Use regular -s.",
    }
    assert "model_target" not in visible


def test_learner_task_material_exposes_morphology_parts_not_answer():
    item = {
        "task_type": "structured_morphology_build",
        "morphology_parts": ["es", "box"],
        "correct_morphology_parts": ["box", "es"],
        "answer_key": {"canonical_target": "boxes"},
    }

    material = _learner_task_material(item)

    assert material == ("Supplied parts", ["es", "box"])
    assert "boxes" not in material[1]


def test_learner_task_material_exposes_word_order_tokens():
    item = {
        "task_type": "structured_word_order",
        "token_sequence": ["likes", "She", "cats"],
        "correct_token_sequence": ["She", "likes", "cats"],
    }

    assert _learner_task_material(item) == (
        "Supplied tokens",
        ["likes", "She", "cats"],
    )
