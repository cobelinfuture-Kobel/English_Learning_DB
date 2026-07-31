#!/usr/bin/env python3
"""Install the approved Unit01 learner-facing Pre-Learning V2 renderer.

The existing Unit01 vocabulary, phrase, sentence-frame, QuestionBank, teacher
files, and runtime authority remain unchanged. This FullFix replaces only the
learner-facing Pre-Learning payload projection, seven-page HTML, and supporting
CSS. It adds child-readable article guidance, first-mention/repeated-mention
mini-contexts, a bounded four-frame learner scaffold, support language, a
worked phrase-to-sentence bridge, separate noun/adjective references, readiness
checks, and a clear ``very`` degree-intensifier explanation.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from ulga.builders import (
    build_a1fs_ops_v1_unit01_questionbank_student_package_phrase_to_sentence
    as student_builder,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Reprojects only already approved Unit01 nouns, adjectives, phrases, article "
    "rules, and sentence frames into a clearer learner-facing seven-page "
    "Pre-Learning scaffold. It creates no canonical content, question, answer, "
    "QuestionBank, scoring authority, learner state, teacher output, image asset, "
    "audio, production activation, Unit02-24 artifact, or A2 content."
)
PROGRAM_ID = "A1FS-OPS-V1"
TASK_ID = "A1FS-OPS-V1_Unit01PreLearningV2FullFix"
SCHEMA_VERSION = "a1fs.ops.v1.unit01_prelearning.v2"
PASS_STATUS = "PASS_A1FS_OPS_V1_UNIT01_PRELEARNING_V2"
EXPECTED_PRINT_PAGE_COUNT = 7
EXPECTED_CHILD_FRAME_COUNT = 4
EXPECTED_MENTION_CONTEXT_COUNT = 3
EXPECTED_GUIDED_CHECK_COUNT = 6
EXPECTED_READY_CHECK_COUNT = 4

_ORIGINAL_PAYLOAD = student_builder._prelearning_payload
_ORIGINAL_HTML = student_builder._prelearning_html
_ORIGINAL_CSS = student_builder.STUDENT_CSS

FULL_NOUN_GROUPS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "CLASSROOM_ROOM",
        "教室與房間",
        ("bag", "book", "box", "desk", "door", "classroom", "room", "window"),
    ),
    ("HOME", "家中物品", ("bed",)),
    ("ANIMAL_OUTDOOR", "動物與戶外", ("cat", "dog", "park", "tree")),
    ("FOOD_SHOP", "食物與商店", ("apple", "egg", "shop")),
)

VISUAL_CUES = {
    "apple": "🍎",
    "bag": "🎒",
    "book": "📘",
    "box": "📦",
    "cat": "🐱",
    "desk": "🪑",
    "door": "🚪",
    "egg": "🥚",
}

V2_CSS = """
/* UNIT01_PRELEARNING_V2 */
.prelearning-goal{font-weight:700}.routine-list{margin:8px 0 14px;padding-left:24px}.routine-list li{margin:3px 0}.scope-note{border:1px solid #c9ced5;border-radius:7px;padding:10px 12px;background:#f8fafb}.visual-card{display:grid;grid-template-columns:46px 1fr auto;align-items:center;gap:10px}.visual-cue{font-size:30px;line-height:1}.category-card{border:1px solid #c9ced5;border-radius:7px;padding:12px;break-inside:avoid}.category-card h3{margin-top:0}.degree-card{border:2px solid #2f4054;border-radius:7px;padding:12px;margin-top:14px;background:#f3f5f7}.degree-card strong{font-size:22px}.context-grid{display:grid;grid-template-columns:1fr;gap:10px}.context-card{border:1px solid #c9ced5;border-radius:7px;padding:11px;break-inside:avoid}.context-card p{margin:5px 0}.mention-first,.mention-repeat{font-weight:700}.learner-frame-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.learner-frame{border:1px solid #c9ced5;border-radius:7px;padding:10px;break-inside:avoid}.learner-frame .frame-model{font-size:19px;font-weight:700}.support-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.support-card{border-left:5px solid #2f4054;background:#f3f5f7;padding:10px 12px}.guided-check{border:1px solid #c9ced5;border-radius:7px;padding:10px 12px;margin:9px 0;break-inside:avoid}.worked-example{border:2px solid #2f4054;border-radius:7px;padding:12px;background:#f3f5f7}.practice-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.writing-step{border:1px solid #c9ced5;border-radius:7px;padding:11px;break-inside:avoid}.checklist{display:grid;grid-template-columns:1fr 1fr;gap:7px;border-top:1px solid #c9ced5;margin-top:12px;padding-top:10px}.reference-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:9px;align-items:start}.reference-grid h3{margin:0 0 5px}.compact-table{font-size:13px}.compact-table th,.compact-table td{padding:4px}.ready-check{border:2px solid #2f4054;border-radius:7px;padding:10px 12px;margin-top:12px}.ready-check p{margin:5px 0}.teacher-system-note{font-size:12px;color:#66717f}
"""


def _esc(value: Any) -> str:
    return student_builder._esc(value)


def _table(headers: Sequence[str], rows: Sequence[Sequence[Any]], *, css_class: str = "") -> str:
    rendered = student_builder._table(headers, rows)
    if css_class:
        rendered = rendered.replace("<table>", f'<table class="{_esc(css_class)}">', 1)
    return rendered


def _lemma_map(rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row.get("lemma") or ""): dict(row) for row in rows}


def _memory_form(row: Mapping[str, Any]) -> str:
    return student_builder._memory_form(row)


def _definite_form(row: Mapping[str, Any]) -> str:
    return student_builder._definite_form(row)


def _gloss(row: Mapping[str, Any]) -> str:
    return student_builder._gloss(row)


def _phrase_to_definite(phrase: str) -> str:
    value = str(phrase or "").strip()
    if value.startswith("an "):
        return "the " + value[3:]
    if value.startswith("a "):
        return "the " + value[2:]
    return value


def _prelearning_payload_v2(
    *,
    vocabulary: Mapping[str, Any],
    chunks: Mapping[str, Any],
    frames: Mapping[str, Any],
) -> dict[str, Any]:
    payload = dict(
        _ORIGINAL_PAYLOAD(
            vocabulary=vocabulary,
            chunks=chunks,
            frames=frames,
        )
    )
    noun_map = _lemma_map(payload["reference_nouns"])
    adjective_map = _lemma_map(payload["reference_adjectives"])
    grouped_nouns = [
        {
            "group_id": group_id,
            "title": title,
            "items": [noun_map[lemma] for lemma in lemmas],
        }
        for group_id, title, lemmas in FULL_NOUN_GROUPS
    ]
    grouped_count = sum(len(group["items"]) for group in grouped_nouns)
    grouped_lemmas = [
        str(row.get("lemma") or "")
        for group in grouped_nouns
        for row in group["items"]
    ]
    if grouped_count != 16 or len(set(grouped_lemmas)) != 16:
        raise ValueError("prelearning_v2_grouped_noun_denominator_invalid")

    payload.update(
        {
            "prelearning_schema_version": SCHEMA_VERSION,
            "prelearning_status": PASS_STATUS,
            "print_page_count_target": EXPECTED_PRINT_PAGE_COUNT,
            "learner_scope": {
                "focus": "a_an_the_with_singular_countable_nouns",
                "guide": "本課先學一個可以數的東西；a / an 後面接單數名詞。",
                "out_of_scope": [
                    "plural_nouns",
                    "uncountable_nouns",
                    "zero_article",
                ],
            },
            "learning_routine": [
                "看圖或看中文。",
                "大聲說完整片語。",
                "遮住英文，再說一次。",
                "把片語放進完整句子。",
            ],
            "visual_cues": dict(VISUAL_CUES),
            "grouped_nouns_v2": grouped_nouns,
            "adjective_categories": [
                {
                    "category_id": "SIZE",
                    "title": "Size｜大小",
                    "words": [adjective_map["big"], adjective_map["small"]],
                    "examples": ["a big box", "a small bag"],
                },
                {
                    "category_id": "AGE_CONDITION",
                    "title": "Age / condition｜新舊狀態",
                    "words": [adjective_map["new"], adjective_map["old"]],
                    "examples": ["a new book", "an old book"],
                },
                {
                    "category_id": "COLOUR",
                    "title": "Colour｜顏色",
                    "words": [adjective_map["red"], adjective_map["blue"]],
                    "examples": ["a red book", "a blue bag"],
                },
            ],
            "degree_intensifier": {
                "word": "very",
                "zh_tw": "很／非常",
                "guide": "放在形容詞前面，表示程度更多、更強；不是數量很多。",
                "examples": [
                    "a very big box",
                    "a very small room",
                    "a very old book",
                ],
                "article_sound_note": (
                    "a / an 仍然看冠詞後面第一個聲音：very 的第一個聲音是 /v/，"
                    "所以說 a very old book。"
                ),
            },
            "mention_contexts": [
                {
                    "context_id": "CAT_DOOR",
                    "first": "I can see a cat.",
                    "repeat": "The cat is near the door.",
                    "guide": "第一次介紹 a cat；第二句再說同一隻貓，用 the cat。",
                },
                {
                    "context_id": "MIA_BAG",
                    "first": "Mia has a bag.",
                    "repeat": "The bag is blue.",
                    "guide": "第一次介紹 a bag；第二句再說同一個袋子，用 the bag。",
                },
                {
                    "context_id": "APPLE_BOX",
                    "first": "There is an apple in the box.",
                    "repeat": "The apple is red.",
                    "guide": "第一次介紹 an apple；第二句再說同一顆蘋果，用 the apple。",
                },
            ],
            "learner_frames": [
                {
                    "frame_id": "LEARNER_FRAME_01",
                    "model": "This is a/an ______.",
                    "example": "This is an old book.",
                },
                {
                    "frame_id": "LEARNER_FRAME_02",
                    "model": "I have a/an ______.",
                    "example": "I have a blue bag.",
                },
                {
                    "frame_id": "LEARNER_FRAME_03",
                    "model": "I can see a/an ______.",
                    "example": "I can see a cat.",
                },
                {
                    "frame_id": "LEARNER_FRAME_04",
                    "model": "The ______ is in/near the ______.",
                    "example": "The cat is near the door.",
                },
            ],
            "support_language": [
                {"form": "in the room", "zh_tw": "在房間裡"},
                {"form": "in the box", "zh_tw": "在盒子裡"},
                {"form": "on the desk", "zh_tw": "在桌上"},
                {"form": "near the door", "zh_tw": "在門附近"},
            ],
            "recycled_helpers": [
                "I have ...",
                "I can see ...",
                "There is ...",
            ],
            "guided_checks": [
                {
                    "prompt": "1. 一顆蘋果",
                    "options": ["a apple", "an apple"],
                },
                {
                    "prompt": "2. 一個藍色的袋子",
                    "options": ["a blue bag", "an blue bag"],
                },
                {
                    "prompt": "3. 一本舊書",
                    "options": ["a old book", "an old book"],
                },
                {
                    "prompt": "4. I can see a cat. ___ cat is near the door.",
                    "options": ["A", "The"],
                },
                {
                    "prompt": "5. a book → a new book → ?",
                    "options": ["a old book", "an old book"],
                },
                {
                    "prompt": "6. very + old + book",
                    "options": ["an very old book", "a very old book"],
                },
            ],
            "worked_example": {
                "input": "old + book",
                "phrase": "an old book",
                "sentence": "This is an old book.",
            },
            "guided_production": [
                {"input": "red + book", "label": "Guided practice 1"},
                {"input": "blue + bag", "label": "Guided practice 2"},
            ],
            "independent_transfer": {
                "guide": "選一個名詞和一個形容詞。先寫完整片語，再選一個句型寫完整句子。"
            },
            "writing_checklist": [
                "有選對 a / an / the。",
                "冠詞後面的完整片語正確。",
                "句首大寫。",
                "句尾有句點。",
            ],
            "ready_check": [
                "我能說出8個核心片語。",
                "我知道a和an要看下一個聲音。",
                "我知道第一次說用a/an，再說同一個東西可以用the。",
                "我能把一個片語放進完整句子。",
            ],
        }
    )
    return payload


def _noun_card_v2(row: Mapping[str, Any], visual_cues: Mapping[str, str]) -> str:
    lemma = str(row.get("lemma") or "")
    cue = str(visual_cues.get(lemma) or "•")
    return (
        '<div class="phrase-card visual-card">'
        f'<span class="visual-cue" aria-hidden="true">{_esc(cue)}</span>'
        f'<strong>{_esc(_memory_form(row))}</strong>'
        f'<span>{_esc(_gloss(row))}</span>'
        "</div>"
    )


def _guided_check_html(row: Mapping[str, Any]) -> str:
    options = "".join(
        f'<span>○ {_esc(option)}</span>' for option in row.get("options") or []
    )
    return (
        '<div class="guided-check">'
        f'<p>{_esc(row.get("prompt"))}</p>{options}'
        "</div>"
    )


def _prelearning_html_v2(payload: Mapping[str, Any]) -> str:
    rules = "".join(
        '<div class="rule-card">'
        f'<strong>{_esc(row["article"])}</strong>'
        f'<p>{_esc(row["guide"])}</p>'
        + "".join(f"<p>{_esc(example)}</p>" for example in row["examples"])
        + "</div>"
        for row in payload["article_rules"]
    )
    core = "".join(
        _noun_card_v2(row, payload["visual_cues"])
        for row in payload["core_nouns"]
    )
    routine = "".join(
        f"<li>{_esc(step)}</li>" for step in payload["learning_routine"]
    )
    groups = "".join(
        '<div class="learning-group">'
        f'<h3>{_esc(group["title"])}</h3>'
        + _table(
            ("第一次說", "再說一次", "中文"),
            [
                (_memory_form(row), _definite_form(row), _gloss(row))
                for row in group["items"]
            ],
            css_class="compact-table",
        )
        + "</div>"
        for group in payload["grouped_nouns_v2"]
    )
    adjective_categories = "".join(
        '<div class="category-card">'
        f'<h3>{_esc(category["title"])}</h3>'
        + "".join(
            f'<p><strong>{_esc(example)}</strong></p>'
            for example in category["examples"]
        )
        + "</div>"
        for category in payload["adjective_categories"]
    )
    very = payload["degree_intensifier"]
    very_examples = "".join(
        f'<p><strong>{_esc(example)}</strong></p>' for example in very["examples"]
    )
    contexts = "".join(
        '<div class="context-card">'
        f'<p class="mention-first">第一次：{_esc(row["first"])}</p>'
        f'<p class="mention-repeat">再說一次：{_esc(row["repeat"])}</p>'
        f'<p>{_esc(row["guide"])}</p>'
        "</div>"
        for row in payload["mention_contexts"]
    )
    learner_frames = "".join(
        '<div class="learner-frame">'
        f'<div class="frame-model">{_esc(row["model"])}</div>'
        f'<p>Example: {_esc(row["example"])}</p>'
        "</div>"
        for row in payload["learner_frames"]
    )
    support_rows = _table(
        ("Support phrase", "中文"),
        [(row["form"], row["zh_tw"]) for row in payload["support_language"]],
        css_class="compact-table",
    )
    helpers = " / ".join(payload["recycled_helpers"])
    guided_checks = "".join(
        _guided_check_html(row) for row in payload["guided_checks"]
    )
    worked = payload["worked_example"]
    guided_production = "".join(
        '<div class="writing-step">'
        f'<p><strong>{_esc(row["label"])}</strong></p>'
        f'<p>{_esc(row["input"])}</p>'
        '<p>Phrase:</p><div class="answer-line"></div>'
        '<p>Sentence:</p><div class="answer-line"></div>'
        "</div>"
        for row in payload["guided_production"]
    )
    checklist = "".join(
        f'<span>□ {_esc(item)}</span>' for item in payload["writing_checklist"]
    )
    ready = "".join(
        f'<p>□ {_esc(item)}</p>' for item in payload["ready_check"]
    )
    noun_rows = [
        (
            row.get("lemma"),
            _memory_form(row),
            _definite_form(row),
            _gloss(row),
        )
        for row in payload["reference_nouns"]
    ]
    noun_midpoint = len(noun_rows) // 2
    adjective_rows = [
        (
            row.get("lemma"),
            _memory_form(row),
            _phrase_to_definite(_memory_form(row)),
            _gloss(row),
        )
        for row in payload["reference_adjectives"]
    ]
    support_reference = [
        ("very", "程度加強詞", "很／非常；不是數量很多"),
        *[
            (row["form"], "位置片語", row["zh_tw"])
            for row in payload["support_language"]
        ],
    ]
    rendered = f"""<!doctype html><html lang="zh-Hant"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Unit 01 Pre-learning V2</title><link rel="stylesheet" href="student.css"></head><body>
<div class="toolbar no-print"><a href="index.html">返回</a><button type="button" onclick="window.print()">列印／另存 PDF</button></div>
<section class="print-page"><h1>Unit 01 Pre-learning</h1><h2>a, an, the</h2>
<p class="prelearning-goal">先記完整片語，再進入句子。</p>
<div class="scope-note"><strong>本課範圍：</strong>{_esc(payload["learner_scope"]["guide"])}</div>
<h3>四步學習法</h3><ol class="routine-list">{routine}</ol><div class="grid3">{rules}</div>
<h2>Part 1｜8個核心片語</h2><div class="grid2">{core}</div></section>
<section class="print-page"><h1>Part 2｜名詞依情境分組</h1><p>同一個名詞先用a/an介紹，再用the說同一個東西。</p>{groups}</section>
<section class="print-page"><h1>Part 3｜形容詞分類與very</h1><div class="grid3">{adjective_categories}</div>
<div class="callout"><strong>a / an看後面第一個聲音：</strong> a book → a new book → an old book</div>
<div class="degree-card"><strong>very = 很／非常</strong><p>{_esc(very["guide"])}</p>{very_examples}<p>{_esc(very["article_sound_note"])}</p></div></section>
<section class="print-page"><h1>Part 4｜第一次說與再說一次</h1><div class="context-grid">{contexts}</div>
<h2>兒童版Sentence Frames</h2><div class="learner-frame-grid">{learner_frames}</div>
<h2>句子小幫手</h2><div class="support-grid"><div class="support-card">{support_rows}</div><div class="support-card"><strong>已學句型，這一課拿來放入新的a/an/the片語：</strong><p>{_esc(helpers)}</p></div></div>
<p class="teacher-system-note">完整11個authority frames仍保留在系統資料中，不在學生主頁顯示技術ID或placeholder。</p></section>
<section class="print-page"><h1>Part 5｜Guided recognition</h1><p>這是進入QuestionBank前的輕量確認，不代表已經熟練。</p>{guided_checks}</section>
<section class="print-page"><h1>Part 6｜Phrase → Sentence</h1>
<div class="worked-example"><h2>Worked example</h2><p>{_esc(worked["input"])} → <strong>{_esc(worked["phrase"])}</strong> → <strong>{_esc(worked["sentence"])}</strong></p></div>
<div class="practice-grid">{guided_production}</div>
<div class="writing-step"><p><strong>Independent transfer</strong></p><p>{_esc(payload["independent_transfer"]["guide"])}</p><p>Phrase:</p><div class="answer-line"></div><p>Sentence:</p><div class="answer-line"></div></div>
<div class="checklist">{checklist}</div><div class="ready-check"><strong>PRELEARNING_READY</strong>{ready}<p>這只代表可以進入正式QuestionBank，不代表已經mastery。</p></div></section>
<section class="print-page"><h1>Unit 01 Vocabulary Reference</h1><p>完整22詞放在最後查閱，不作為第一個學習畫面。</p>
<div class="reference-grid"><div><h3>Nouns 1</h3>{_table(("Word","一起記","再說一次","中文"), noun_rows[:noun_midpoint], css_class="compact-table")}</div>
<div><h3>Nouns 2</h3>{_table(("Word","一起記","再說一次","中文"), noun_rows[noun_midpoint:], css_class="compact-table")}</div>
<div><h3>Adjectives</h3>{_table(("Word","Example phrase","再說一次","中文"), adjective_rows, css_class="compact-table")}
<h3>Support language</h3>{_table(("Form","Role","中文"), support_reference, css_class="compact-table")}</div></div></section>
<script src="student.js"></script></body></html>"""
    errors = validate_contract(payload, rendered)
    if errors:
        raise ValueError("prelearning_v2_contract_failed:" + ",".join(errors))
    return rendered


def validate_contract(payload: Mapping[str, Any], rendered_html: str) -> list[str]:
    errors: list[str] = []
    html = str(rendered_html or "")
    if payload.get("prelearning_schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_invalid")
    if html.count('class="print-page"') != EXPECTED_PRINT_PAGE_COUNT:
        errors.append("print_page_count_invalid")
    if len(payload.get("learner_frames") or []) != EXPECTED_CHILD_FRAME_COUNT:
        errors.append("child_frame_count_invalid")
    if len(payload.get("mention_contexts") or []) != EXPECTED_MENTION_CONTEXT_COUNT:
        errors.append("mention_context_count_invalid")
    if len(payload.get("guided_checks") or []) != EXPECTED_GUIDED_CHECK_COUNT:
        errors.append("guided_check_count_invalid")
    if len(payload.get("ready_check") or []) != EXPECTED_READY_CHECK_COUNT:
        errors.append("ready_check_count_invalid")
    required_markers = (
        "very = 很／非常",
        "不是數量很多",
        "a very old book",
        "The cat is near the door.",
        "Worked example",
        "PRELEARNING_READY",
        "Nouns 1",
        "Adjectives",
        "Support language",
    )
    for marker in required_markers:
        if marker not in html:
            errors.append("required_marker_missing:" + marker)
    forbidden_markers = (
        "{ARTICLE}",
        "{THING}",
        "{PLACE}",
        "{ADJECTIVE}",
        "U01-F01",
        "U01-AF01",
        "U01-SF01",
    )
    for marker in forbidden_markers:
        if marker in html:
            errors.append("technical_marker_exposed:" + marker)
    if "<img" in html.casefold():
        errors.append("external_image_element_forbidden")
    adjective_definites = {
        _phrase_to_definite(_memory_form(row))
        for row in payload.get("reference_adjectives") or []
    }
    if "the old book" not in adjective_definites or "the blue bag" not in adjective_definites:
        errors.append("adjective_definite_reference_incomplete")
    grouped_lemmas = [
        str(row.get("lemma") or "")
        for group in payload.get("grouped_nouns_v2") or []
        for row in group.get("items") or []
    ]
    if len(grouped_lemmas) != 16 or len(set(grouped_lemmas)) != 16:
        errors.append("grouped_noun_coverage_invalid")
    if len(payload.get("sentence_frames") or []) != student_builder.master.EXPECTED_SENTENCE_FRAMES:
        errors.append("authority_sentence_frame_count_changed")
    return errors


def install_fullfix() -> dict[str, Any]:
    previous = {
        "payload": student_builder._prelearning_payload,
        "html": student_builder._prelearning_html,
        "css": student_builder.STUDENT_CSS,
    }
    student_builder._prelearning_payload = _prelearning_payload_v2
    student_builder._prelearning_html = _prelearning_html_v2
    if "UNIT01_PRELEARNING_V2" not in student_builder.STUDENT_CSS:
        student_builder.STUDENT_CSS = student_builder.STUDENT_CSS + "\n" + V2_CSS
    return previous


if __name__ == "__main__":
    install_fullfix()
    print(PASS_STATUS)
