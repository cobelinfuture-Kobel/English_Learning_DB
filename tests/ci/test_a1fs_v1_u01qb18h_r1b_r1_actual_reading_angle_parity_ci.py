from __future__ import annotations

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


def test_actual_angle_parity_layer_is_presentation_only() -> None:
    assert r1.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert "474-item QuestionBank" in r1.A1FS_CONTENT_POLICY_EXEMPTION
    assert "private_item_json" in r1.A1FS_CONTENT_POLICY_EXEMPTION
    assert r1.NEXT_SHORT_STEP.startswith("A1FS-V1-U01QB18H-R1C_")
