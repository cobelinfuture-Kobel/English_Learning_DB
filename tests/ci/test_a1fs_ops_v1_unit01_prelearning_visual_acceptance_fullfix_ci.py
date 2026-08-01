from __future__ import annotations

from ulga.builders import (
    build_a1fs_ops_v1_unit01_prelearning_visual_acceptance_fullfix as fullfix,
)
from ulga.builders import (
    build_a1fs_ops_v1_unit01_questionbank_student_package_phrase_to_sentence
    as student_builder,
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
        _noun("apple", "an", "蘋果"), _noun("bag", "a", "袋子；書包"),
        _noun("bed", "a", "床"), _noun("book", "a", "書"),
        _noun("box", "a", "盒子"), _noun("cat", "a", "貓"),
        _noun("classroom", "a", "教室"), _noun("desk", "a", "書桌；課桌"),
        _noun("dog", "a", "狗"), _noun("door", "a", "門"),
        _noun("egg", "an", "蛋"), _noun("park", "a", "公園"),
        _noun("room", "a", "房間"), _noun("shop", "a", "商店"),
        _noun("tree", "a", "樹"), _noun("window", "a", "窗戶"),
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
        "an apple", "a bag", "a book", "a box", "a cat", "a desk",
        "a door", "an egg", "a big box", "a small bag", "a very big box",
        "a very small room", "a new book", "an old book", "a very old book",
        "a red book", "a blue bag", "a classroom", "a room", "a window",
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
        {"active_vocabulary": nouns, "active_adjectives": adjectives},
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


def test_visual_projection_removes_system_language_and_aligns_support_frame() -> None:
    original_payload = student_builder._prelearning_payload
    original_html = student_builder._prelearning_html
    original_css = student_builder.STUDENT_CSS
    original_questions = student_builder._safe_questions
    original_qb_html = student_builder._questionbank_html
    try:
        fullfix.install_fullfix()
        vocabulary, chunks, frames = _fixture()
        payload = student_builder._prelearning_payload(
            vocabulary=vocabulary,
            chunks=chunks,
            frames=frames,
        )
        rendered = student_builder._prelearning_html(payload)
        assert fullfix.validate_learner_projection(rendered) == []
        assert "完整11個authority frames" not in rendered
        assert "placeholder" not in rendered
        assert "PRELEARNING_READY" not in rendered
        assert "mastery" not in rendered
        assert "Ready Check｜我準備好了嗎？" in rendered
        assert "The ______ is in/on/near the ______." in rendered
        assert "表示程度更強，意思是很／非常；不是數量很多。" in rendered
        assert "第一次介紹一個東西時常用a/an" in rendered
        assert "UNIT01_PRELEARNING_VISUAL_ACCEPTANCE" in student_builder.STUDENT_CSS
        assert ".guided-check span{display:inline-block;margin-right:24px}" in student_builder.STUDENT_CSS
        assert ".writing-step .answer-line{min-height:26px}" in student_builder.STUDENT_CSS
        assert student_builder._safe_questions is original_questions
        assert student_builder._questionbank_html is original_qb_html
    finally:
        student_builder._prelearning_payload = original_payload
        student_builder._prelearning_html = original_html
        student_builder.STUDENT_CSS = original_css


def test_visual_projection_fails_closed_if_system_marker_reappears() -> None:
    errors = fullfix.validate_learner_projection(
        '<section class="print-page"></section>' * 7
        + "PRELEARNING_READY mastery authority frames placeholder"
    )
    assert "system_marker_exposed:PRELEARNING_READY" in errors
    assert "system_marker_exposed:mastery" in errors
    assert "system_marker_exposed:authority frames" in errors
    assert "system_marker_exposed:placeholder" in errors


def test_main_wires_visual_projection_then_exact7_then_browser(monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(fullfix, "install_fullfix", lambda: calls.append("visual"))
    monkeypatch.setattr(
        fullfix.windows_fullfix,
        "install_exact_seven_page_print_layout",
        lambda: calls.append("exact7"),
    )
    monkeypatch.setattr(
        fullfix.windows_fullfix,
        "install_fullfix",
        lambda: calls.append("browser"),
    )
    monkeypatch.setattr(
        fullfix.windows_fullfix.local_operator,
        "main",
        lambda argv: calls.append("operator") or 0,
    )

    assert fullfix.main(["--fixture"]) == 0
    assert calls == ["visual", "exact7", "browser", "operator"]
