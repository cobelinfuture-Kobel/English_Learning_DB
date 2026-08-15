from __future__ import annotations

import json

from product.a1fs_v1_2_1 import (
    u01qb18h_r1b_r1_unit01_form01_actual_reading_angle_parity_fullfix as r1,
)


def _student_form_with_actual_q07() -> dict:
    scenes = [
        {
            "scene_number": index,
            "scene_ref_id": (
                "U01-C2-HOME-TOY-BOX" if index == 2 else f"SCENE-{index}"
            ),
            "setting": "HOME" if index == 2 else f"PLACE_{index}",
        }
        for index in range(1, 5)
    ]
    activities = []
    number = 0
    for scene_index, scene in enumerate(scenes, start=1):
        ref = scene["scene_ref_id"]
        rows = [
            (
                "READING",
                "select_one",
                "Target phrase: ___ bag.",
                "Choose the correct article.",
                ["a", "an", "the"],
            ),
            (
                "READING",
                "select_one",
                "I can see a bag. | Target phrase: ___ bag.",
                "Choose the article for the same thing again.",
                ["a", "an", "the"],
            ),
            (
                "WRITING",
                "short_text",
                "Word: bag",
                "Write the phrase.",
                [],
            ),
            (
                "WRITING",
                "short_text",
                "Words: bag | a",
                "Put the words in order.",
                [],
            ),
            (
                "SPEAKING",
                "practice_only",
                "Your turn: This is ___ ______. | Word: bag",
                "Complete the sentence frame, then say it aloud.",
                [],
            ),
        ]
        if scene_index == 2:
            rows[1] = (
                "READING",
                "select_one",
                (
                    "Scene: Home | Scene words: bed, box, cd_player, living_room, robot, toy | "
                    "Relationship: in, near | There is ___ room at home."
                ),
                "Choose the article for the first mention.",
                ["a", "an", "the"],
            )
        for skill, mode, stimulus, prompt, options in rows:
            number += 1
            activities.append(
                {
                    "question_number": f"Q{number:02d}",
                    "skill": skill,
                    "scene_ref_id": ref,
                    "setting": scene["setting"],
                    "stimulus": stimulus,
                    "prompt": prompt,
                    "options": options,
                    "response_mode": mode,
                    "capture_enabled": skill != "SPEAKING",
                    "practice_only": skill == "SPEAKING",
                }
            )
    return {
        "unit_id": "UNIT01",
        "form_id": "U01-FORM-01",
        "form_ordinal": 1,
        "learner_mode": "FRESH_SEQUENTIAL_REPLAY",
        "learner_id": "PRIVATE_REVIEW_ONLY",
        "scene_count": 4,
        "learner_visible_activity_count": 20,
        "skill_counts": {"READING": 8, "WRITING": 8, "SPEAKING": 4},
        "scenes": scenes,
        "activities": activities,
    }


def _student_form_with_cross_activity_leak() -> dict:
    value = _student_form_with_actual_q07()

    q04 = value["activities"][3]
    q04["response_mode"] = "ordered_tokens"
    q04["stimulus"] = "Words: apple | an"
    q04["prompt"] = "Put the target phrase in the correct order."

    q05 = value["activities"][4]
    q05["stimulus"] = (
        "Example: This is an apple. | Your turn: This is ___ ______. | Word: bag"
    )

    q09 = value["activities"][8]
    q09["response_mode"] = "ordered_tokens"
    q09["stimulus"] = "Words: bed | a"
    q09["prompt"] = "Put the target phrase in the correct order."

    q10 = value["activities"][9]
    q10["stimulus"] = (
        "Example: This is a bed. | Your turn: This is ___ ______. | Word: room"
    )

    q14 = value["activities"][13]
    q14["response_mode"] = "ordered_tokens"
    q14["stimulus"] = "Words: cat | a"
    q14["prompt"] = "Put the target phrase in the correct order."

    q15 = value["activities"][14]
    q15["stimulus"] = (
        "Example: This is a cat. | Your turn: This is ___ ______. | Word: tree"
    )

    q19 = value["activities"][18]
    q19["response_mode"] = "ordered_tokens"
    q19["stimulus"] = "Words: park | a"
    q19["prompt"] = "Put the target phrase in the correct order."

    q20 = value["activities"][19]
    q20["stimulus"] = (
        "Example: This is a dog. | Your turn: This is ___ ______. | Word: park"
    )
    return value


def test_actual_q07_first_mention_overrides_positional_known_reference_fallback() -> None:
    student = _student_form_with_actual_q07()
    q07 = student["activities"][6]
    assert q07["question_number"] == "Q07"
    assert q07["prompt"] == "Choose the article for the first mention."
    assert r1._learner_safe_reading_angle(
        q07,
        positional_fallback="KNOWN_REFERENCE_CONTEXT",
    ) == "FIRST_MENTION_CONTEXT"


def test_actual_form01_q07_renders_without_false_known_reference_context_failure() -> None:
    document = r1.render_form_html(_student_form_with_actual_q07())
    assert "First mention: choose the article for something introduced now." in document
    assert "There is ___ room at home." in document
    assert "Context: I can see a bag." in document
    assert "KNOWN_REFERENCE_CONTEXT" not in document
    assert "FIRST_MENTION_CONTEXT" not in document


def test_cross_activity_example_that_reproduces_prior_token_phrase_is_suppressed() -> None:
    student = _student_form_with_cross_activity_leak()
    sanitized, suppressed = r1._sanitize_cross_activity_answer_demonstrations(student)

    assert suppressed == 3
    assert "Example: This is an apple." not in sanitized["activities"][4]["stimulus"]
    assert "Example: This is a bed." not in sanitized["activities"][9]["stimulus"]
    assert "Example: This is a cat." not in sanitized["activities"][14]["stimulus"]
    assert "Your turn: This is ___ ______." in sanitized["activities"][4]["stimulus"]
    assert "Example: This is a dog." in sanitized["activities"][19]["stimulus"]


def test_cross_activity_leak_is_absent_from_rendered_form01_html() -> None:
    document = r1.render_form_html(_student_form_with_cross_activity_leak())
    assert "Example: This is an apple." not in document
    assert "Example: This is a bed." not in document
    assert "Example: This is a cat." not in document
    assert "Example: This is a dog." in document


def test_manifest_provenance_is_stamped_to_current_fullfix(tmp_path) -> None:
    path = tmp_path / r1.r1b.base.MANIFEST_NAME
    path.write_text(
        json.dumps(
            {
                "task_id": r1.r1b.base.TASK_ID,
                "latest_fullfix_task_id": r1.r1b.base.R1A_TASK_ID,
                "next_short_step": r1.r1b.base.NEXT_SHORT_STEP,
            }
        ),
        encoding="utf-8",
    )
    value = r1._stamp_manifest_provenance(path)
    assert value["latest_fullfix_task_id"] == r1.TASK_ID
    assert value["latest_fullfix_validation_status"] == r1.PASS_STATUS
    assert value["next_short_step"] == r1.NEXT_SHORT_STEP


def test_actual_angle_parity_layer_is_presentation_only() -> None:
    assert r1.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert "474-item QuestionBank" in r1.A1FS_CONTENT_POLICY_EXEMPTION
    assert "private_item_json" in r1.A1FS_CONTENT_POLICY_EXEMPTION
    assert "manifest" in r1.A1FS_CONTENT_POLICY_EXEMPTION
    assert r1.NEXT_SHORT_STEP.startswith("A1FS-V1-U01QB18H-R1C_")
