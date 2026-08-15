from __future__ import annotations

from product.a1fs_v1_2_1 import (
    u01qb18h_r1b_unit01_form01_reading_task_angle_answer_position_and_orphan_heading_fullfix
    as r1b,
)


def _student_form() -> dict:
    scenes = [
        {"scene_number": index, "scene_ref_id": f"SCENE-{index}", "setting": f"PLACE_{index}"}
        for index in range(1, 5)
    ]
    activities = []
    number = 0
    for scene in scenes:
        ref = scene["scene_ref_id"]
        for skill, mode, stimulus, prompt, options in (
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
                "Target phrase: ___ bag.",
                "Choose the correct article.",
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
        ):
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


def test_form01_task_angles_are_derived_from_existing_u01qb09_owner() -> None:
    enriched = r1b._enrich_form01_task_angles(_student_form())
    for start in (0, 5, 10, 15):
        rows = enriched["activities"][start : start + 5]
        assert [row["task_angle"] for row in rows] == [
            "ARTICLE_CONTROL",
            "FIRST_MENTION_CONTEXT",
            "PHRASE_CONSTRUCTION",
            "WORD_ORDER",
            "SCENE_DESCRIPTION",
        ]


def test_reading_choice_positions_rotate_without_answer_metadata() -> None:
    student = r1b._enrich_form01_task_angles(_student_form())
    q01 = r1b._rotate_reading_options(student["activities"][0])
    q02 = r1b._rotate_reading_options(student["activities"][1])
    q06 = r1b._rotate_reading_options(student["activities"][5])
    assert q01["options"] == ["a", "an", "the"]
    assert q02["options"] == ["an", "the", "a"]
    assert q06["options"] == ["the", "a", "an"]
    for row in (q01, q02, q06):
        assert set(row["options"]) == {"a", "an", "the"}
        assert not any("answer" in str(key).casefold() for key in row)


def test_form01_html_has_distinct_guided_reading_cues_and_no_raw_task_ids() -> None:
    document = r1b.render_form_html(_student_form())
    assert document.count("Phrase check: choose the article that fits this phrase.") == 4
    assert document.count("First mention: this is a new thing in the scene.") == 4
    assert "ARTICLE_CONTROL" not in document
    assert "FIRST_MENTION_CONTEXT" not in document
    assert "article_control" not in document.casefold()
    assert "first_mention_context" not in document.casefold()


def test_form01_scene_heading_is_bound_to_first_activity_for_print() -> None:
    document = r1b.render_form_html(_student_form())
    assert document.count('class="scene-lead"') == 4
    assert ".scene-lead{break-inside:avoid;page-break-inside:avoid}" in document
    assert "break-after:avoid-page;page-break-after:avoid" in document
    for index in range(1, 5):
        marker = f"Scene {index}</span>"
        assert marker in document


def test_r1b_is_presentation_only_and_keeps_r1_as_materialization_owner() -> None:
    assert r1b.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert "474-item QuestionBank" in r1b.A1FS_CONTENT_POLICY_EXEMPTION
    assert "never reads or exports correct answers" in r1b.A1FS_CONTENT_POLICY_EXEMPTION
    assert r1b.base.render_form_html is r1b._ORIGINAL_RENDER_FORM_HTML
    assert r1b.NEXT_SHORT_STEP.startswith("A1FS-V1-U01QB18H-R1C_")
