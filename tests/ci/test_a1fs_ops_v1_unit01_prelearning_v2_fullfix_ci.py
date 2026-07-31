from __future__ import annotations

from ulga.builders import (
    build_a1fs_ops_v1_unit01_prelearning_v2_fullfix as fullfix,
)
from ulga.builders import (
    build_a1fs_ops_v1_unit01_questionbank_student_package_phrase_to_sentence
    as student_builder,
)
from ulga.validators import (
    validate_a1fs_ops_v1_unit01_prelearning_v2_fullfix as validator,
)


def _noun(lemma: str, article: str, gloss: str) -> dict[str, str]:
    return {
        "lemma": lemma,
        "memory_form_indefinite": f"{article} {lemma}",
        "memory_form_definite": f"the {lemma}",
        "zh_tw_gloss": gloss,
    }


def _adjective(lemma: str, phrase: str, gloss: str) -> dict[str, str]:
    return {
        "lemma": lemma,
        "memory_phrase": phrase,
        "zh_tw_gloss": gloss,
    }


def _fixture() -> tuple[dict, dict, dict]:
    nouns = [
        _noun("apple", "an", "蘋果"),
        _noun("bag", "a", "袋子；書包"),
        _noun("bed", "a", "床"),
        _noun("book", "a", "書"),
        _noun("box", "a", "盒子"),
        _noun("cat", "a", "貓"),
        _noun("classroom", "a", "教室"),
        _noun("desk", "a", "書桌；課桌"),
        _noun("dog", "a", "狗"),
        _noun("door", "a", "門"),
        _noun("egg", "an", "蛋"),
        _noun("park", "a", "公園"),
        _noun("room", "a", "房間"),
        _noun("shop", "a", "商店"),
        _noun("tree", "a", "樹"),
        _noun("window", "a", "窗戶"),
    ]
    adjectives = [
        _adjective("big", "a big box", "大的"),
        _adjective("blue", "a blue bag", "藍色的"),
        _adjective("new", "a new book", "新的"),
        _adjective("old", "an old book", "舊的"),
        _adjective("red", "a red book", "紅色的"),
        _adjective("small", "a small bag", "小的"),
    ]
    phrases = [
        "an apple",
        "a bag",
        "a book",
        "a box",
        "a cat",
        "a desk",
        "a door",
        "an egg",
        "a big box",
        "a small bag",
        "a very big box",
        "a very small room",
        "a new book",
        "an old book",
        "a very old book",
        "a red book",
        "a blue bag",
        "a classroom",
        "a room",
        "a window",
        "a bed",
    ]
    phrase_rows = [{"surface_form": phrase} for phrase in phrases]
    frames = [
        {"frame_id": f"U01-F{index:02d}", "template": "template"}
        for index in range(1, 7)
    ]
    adjective_frames = [
        {"frame_id": f"U01-AF{index:02d}", "template": "template"}
        for index in range(1, 4)
    ]
    scaffold_frames = [
        {"frame_id": f"U01-SF{index:02d}", "template": "template"}
        for index in range(1, 3)
    ]
    return (
        {
            "active_vocabulary": nouns,
            "active_adjectives": adjectives,
        },
        {
            "instructional_phrases": phrase_rows[:8],
            "adjective_instructional_phrases": phrase_rows[8:],
        },
        {
            "core_frames": frames,
            "adjective_expansion_frames": adjective_frames,
            "scaffold_only_frames": scaffold_frames,
        },
    )


def test_prelearning_v2_is_seven_page_child_readable_and_keeps_very() -> None:
    vocabulary, chunks, frames = _fixture()
    payload = fullfix._prelearning_payload_v2(
        vocabulary=vocabulary,
        chunks=chunks,
        frames=frames,
    )
    rendered = fullfix._prelearning_html_v2(payload)
    result = validator.validate_payload(payload, rendered)

    assert result["validation_status"] == validator.PASS_STATUS, result["errors"]
    assert result["error_count"] == 0
    assert result["print_page_count"] == 7
    assert result["child_frame_count"] == 4
    assert result["mention_context_count"] == 3
    assert result["guided_check_count"] == 6
    assert result["ready_check_count"] == 4
    assert result["authority_sentence_frame_count"] == 11
    assert "very = 很／非常" in rendered
    assert "不是數量很多" in rendered
    assert "a very old book" in rendered
    assert "a very old book。" in rendered
    assert "The cat is near the door." in rendered
    assert "Worked example" in rendered
    assert "PRELEARNING_READY" in rendered
    assert "the old book" in rendered
    assert "the blue bag" in rendered
    assert "{ARTICLE}" not in rendered
    assert "{THING}" not in rendered
    assert "U01-F01" not in rendered
    assert "<img" not in rendered.casefold()


def test_prelearning_v2_preserves_authority_and_questionbank_boundaries() -> None:
    original_payload = student_builder._prelearning_payload
    original_html = student_builder._prelearning_html
    original_css = student_builder.STUDENT_CSS
    original_safe_questions = student_builder._safe_questions
    original_questionbank_html = student_builder._questionbank_html
    original_stage_definitions = student_builder.STAGE_DEFINITIONS
    try:
        previous = fullfix.install_fullfix()
        assert previous["payload"] is original_payload
        assert previous["html"] is original_html
        assert student_builder._prelearning_payload is fullfix._prelearning_payload_v2
        assert student_builder._prelearning_html is fullfix._prelearning_html_v2
        assert "UNIT01_PRELEARNING_V2" in student_builder.STUDENT_CSS
        assert student_builder._safe_questions is original_safe_questions
        assert student_builder._questionbank_html is original_questionbank_html
        assert student_builder.STAGE_DEFINITIONS is original_stage_definitions
        assert len(student_builder.STAGE_DEFINITIONS) == 7
        assert len(student_builder.EXPECTED_FAMILIES) == 12
    finally:
        student_builder._prelearning_payload = original_payload
        student_builder._prelearning_html = original_html
        student_builder.STUDENT_CSS = original_css
