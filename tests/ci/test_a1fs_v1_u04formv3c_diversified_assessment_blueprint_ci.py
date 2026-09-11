from product.a1fs_v1_2_1 import u04formv3c_diversified_assessment_blueprint_validator as target


def test_u04_formv3c_diversified_blueprint_is_gpt56_direct_designed_and_complete():
    report = target.validate_blueprint()

    assert report["status"] == target.STATUS
    assert report["form_count"] == 4
    assert report["task_count"] == 160
    assert report["response_mode_coverage_count"] == 22
    assert set(report["response_mode_coverage"]) == target.EXPECTED_RESPONSE_MODES
    assert report["fixed_response_mode_slot_count"] == 0
    assert report["python_blueprint_generation_used"] is False
    assert report["python_response_mode_assignment_used"] is False
    assert report["python_task_family_assignment_used"] is False
    assert report["python_learner_content_authoring_used"] is False
    assert report["legacy_python_task_builder_used"] is False
    assert report["learner_content_present"] is False
    assert report["current360_binding_status"] == "PENDING_GPT5_6_DIRECT_BINDING"
    assert report["a2_a2plus_unlocked"] is False
    assert report["listening_modified"] is False

    for form in report["forms"]:
        assert form["distinct_response_mode_count"] >= 20
        assert form["distinct_task_family_count"] >= 28
        assert form["distinct_capability_count"] >= 22
        assert form["response_field_count"] > 40
        assert form["picture_task_count"] >= 2

    assert max(row["same_slot_ratio"] for row in report["pairwise_response_signature"]) <= 0.25


def test_u04_formv3c_response_repertoire_contains_cambridge_compatible_and_visual_modes():
    report = target.validate_blueprint()
    modes = set(report["response_mode_coverage"])

    assert {
        "SELECT_ONE", "SHORT_ANSWER", "WRITE_SENTENCE",
        "ONE_WORD_GAP", "ONE_TO_THREE_WORDS", "SENTENCE_COMPLETION",
        "MATCHING", "MULTIPLE_MATCHING", "REFERENCE_MATCHING",
        "NOTE_COMPLETION", "TABLE_COMPLETION", "DIALOGUE_RESPONSE",
        "FACT_CORRECTION", "RECONSTRUCTION", "ORDER_SEQUENCE",
        "GIST_BEST_TITLE", "ASK_A_QUESTION", "SPEAK_SHORT_RESPONSE", "SHORT_RETELL",
        "PICTURE_POSITION", "PICTURE_DIFFERENCE", "PICTURE_LABEL",
    } == modes


def test_u04_formv3c_blueprint_has_no_learner_facing_question_or_answer_payloads():
    payload = target._load()
    for form in payload["forms"]:
        for task in form["tasks"]:
            assert not (target.LEARNER_CONTENT_KEYS_FORBIDDEN_IN_BLUEPRINT & set(task))
