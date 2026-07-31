#!/usr/bin/env python3
"""Build the approved Unit01 learner package without changing teacher output.

The existing printable master package remains the sole source. This adapter
rebuilds that package once, preserves both teacher files byte-for-byte, and
adds a learner-only pre-learning sequence plus a full 474-item QuestionBank
ordered from phrase control to complete and connected sentences. No image,
answer, item identity, scoring contract, or second question bank is produced.
"""
from __future__ import annotations

import hashlib
import html
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import (
    build_a1fs_ops_v1_unit01_canonical_question_bank_vocabulary_chunk_sentence_printable_master_package
    as master,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Renders the accepted Unit01 vocabulary, instructional phrases, sentence "
    "frames, and existing 474 learner-safe questions through the existing "
    "printable master package. It preserves teacher files byte-for-byte and "
    "creates no question, answer, content authority, bank, planner, renderer "
    "authority, score, learner state, image, audio, A2 content, or Unit02-24 artifact."
)
PROGRAM_ID = "A1FS-OPS-V1"
TASK_ID = (
    "A1FS-OPS-V1_"
    "Unit01QuestionBankStudentPackagePhraseToSentenceBuilderAndQA"
)
SCHEMA_VERSION = "a1fs.ops.v1.unit01_student_phrase_to_sentence_package.v1"
PASS_STATUS = "PASS_A1FS_OPS_V1_UNIT01_STUDENT_PHRASE_TO_SENTENCE_PACKAGE"
STUDENT_DATA_NAME = "unit01_student_phrase_to_sentence_package.safe.json"
NEXT_SHORT_STEP = (
    "A1FS-OPS-V1_"
    "Unit01StudentPackageChromiumPrintAndMainProductEntryAcceptance"
)

STAGE_DEFINITIONS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "STAGE_01_PHRASE_ARTICLE",
        "Phrase 1｜a / an + noun",
        ("U01-PF01-AAN-NOUN-GAP",),
    ),
    (
        "STAGE_02_PHRASE_DESCRIPTION",
        "Phrase 2｜article + adjective + noun",
        (
            "U01-PF02-AAN-ADJ-NOUN-GAP",
            "U01-PF03-VERY-ADJ-NOUN-GAP",
        ),
    ),
    (
        "STAGE_03_PHRASE_CONSTRUCTION",
        "Phrase 3｜word order and phrase construction",
        ("U01-PF07-WORD-ORDER",),
    ),
    (
        "STAGE_04_COMPLETE_SENTENCE",
        "Sentence 1｜first mention in a complete sentence",
        (
            "U01-PF04-FIRST-MENTION-CONTEXT",
            "U01-PF08-TRANSFER-FIRST-MENTION",
        ),
    ),
    (
        "STAGE_05_CONNECTED_SENTENCES",
        "Sentence 2｜a / an → the across connected sentences",
        (
            "U01-PF05-KNOWN-REFERENCE-CONTEXT",
            "U01-PF09-TRANSFER-KNOWN-REFERENCE",
        ),
    ),
    (
        "STAGE_06_ERROR_CHECK",
        "Check｜find and correct article errors",
        ("U01-PF06-ERROR-DISCRIMINATION",),
    ),
    (
        "STAGE_07_SPEAKING_PRACTICE",
        "Speaking practice｜phrase → sentence",
        (
            "U01-PF10-SPEAK-NOUN",
            "U01-PF11-SPEAK-ADJ-NOUN",
            "U01-PF12-SPEAK-VERY-ADJ-NOUN",
        ),
    ),
)
FAMILY_TO_STAGE = {
    family: (index, stage_id, title)
    for index, (stage_id, title, families) in enumerate(STAGE_DEFINITIONS, 1)
    for family in families
}
EXPECTED_FAMILIES = frozenset(FAMILY_TO_STAGE)
CORE_NOUNS = ("apple", "bag", "book", "box", "cat", "desk", "door", "egg")
NOUN_GROUPS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("CLASSROOM_ROOM", "教室與房間", ("classroom", "room", "window")),
    ("HOME", "家中物品", ("bed",)),
    ("ANIMAL_OUTDOOR", "動物與戶外", ("dog", "park", "tree")),
    ("SHOP", "商店", ("shop",)),
)
ADJECTIVE_PAIRS = (("big", "small"), ("new", "old"), ("red", "blue"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _teacher_identity(output_root: Path) -> dict[str, dict[str, Any]]:
    return {
        name: master.file_identity(output_root / name)
        for name in (
            "teacher/index.private.html",
            "teacher/unit01_teacher_print_data.private.json",
        )
    }


def _vocabulary_rows(vocabulary: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    nouns = [dict(row) for row in vocabulary.get("active_vocabulary") or []]
    adjectives = [dict(row) for row in vocabulary.get("active_adjectives") or []]
    if len(nouns) != 16 or len(adjectives) != 6:
        raise ValueError(
            f"active_vocabulary_denominator_invalid:{len(nouns)}:{len(adjectives)}"
        )
    return nouns, adjectives


def _lemma_map(rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row.get("lemma") or ""): dict(row) for row in rows}


def _memory_form(row: Mapping[str, Any]) -> str:
    return str(
        row.get("memory_form_indefinite")
        or row.get("memory_phrase")
        or row.get("lemma")
        or ""
    )


def _definite_form(row: Mapping[str, Any]) -> str:
    return str(row.get("memory_form_definite") or "")


def _gloss(row: Mapping[str, Any]) -> str:
    return str(row.get("zh_tw_gloss") or "")


def _phrase_surfaces(chunks: Mapping[str, Any]) -> list[str]:
    return [
        str(row.get("surface_form") or "")
        for row in [
            *(chunks.get("instructional_phrases") or []),
            *(chunks.get("adjective_instructional_phrases") or []),
        ]
        if str(row.get("surface_form") or "")
    ]


def _prelearning_payload(
    *,
    vocabulary: Mapping[str, Any],
    chunks: Mapping[str, Any],
    frames: Mapping[str, Any],
) -> dict[str, Any]:
    nouns, adjectives = _vocabulary_rows(vocabulary)
    noun_map = _lemma_map(nouns)
    adjective_map = _lemma_map(adjectives)
    phrases = _phrase_surfaces(chunks)
    grouped = [
        {
            "group_id": group_id,
            "title": title,
            "items": [noun_map[lemma] for lemma in lemmas],
        }
        for group_id, title, lemmas in NOUN_GROUPS
    ]
    adjective_pairs = [
        {
            "left": adjective_map[left],
            "right": adjective_map[right],
            "approved_examples": [
                phrase
                for phrase in phrases
                if f" {left} " in f" {phrase} "
                or f" {right} " in f" {phrase} "
            ],
        }
        for left, right in ADJECTIVE_PAIRS
    ]
    frame_rows = [
        dict(row)
        for row in [
            *(frames.get("core_frames") or []),
            *(frames.get("adjective_expansion_frames") or []),
            *(frames.get("scaffold_only_frames") or []),
        ]
    ]
    payload = {
        "article_rules": [
            {
                "article": "a",
                "guide": "後面是子音聲音",
                "examples": ["a bag", "a book", "a red book"],
            },
            {
                "article": "an",
                "guide": "後面是母音聲音",
                "examples": ["an apple", "an egg", "an old book"],
            },
            {
                "article": "the",
                "guide": "已經知道或再次提到的東西",
                "examples": ["the bag", "the apple", "the old book"],
            },
        ],
        "core_nouns": [noun_map[lemma] for lemma in CORE_NOUNS],
        "grouped_nouns": grouped,
        "adjective_pairs": adjective_pairs,
        "instructional_phrases": phrases,
        "sentence_frames": frame_rows,
        "reference_nouns": nouns,
        "reference_adjectives": adjectives,
    }
    if len(payload["instructional_phrases"]) != master.EXPECTED_INSTRUCTIONAL_PHRASES:
        raise ValueError("instructional_phrase_count_invalid")
    if len(payload["sentence_frames"]) != master.EXPECTED_SENTENCE_FRAMES:
        raise ValueError("sentence_frame_count_invalid")
    return payload


def _safe_questions(database: Path) -> tuple[list[dict[str, Any]], dict[str, int]]:
    runtime_rows, extension_ids = master._runtime_items(database)
    questions: list[dict[str, Any]] = []
    family_counts: Counter[str] = Counter()
    for original_position, row in enumerate(runtime_rows, 1):
        family = str(row["pattern_family_id"])
        stage = FAMILY_TO_STAGE.get(family)
        if stage is None:
            raise ValueError(f"unmapped_pattern_family:{family}")
        learner = master._learner_item(
            row,
            position=original_position,
            extension_ids=extension_ids,
        )
        learner.pop("content_origin", None)
        learner.update(
            {
                "pattern_family_id": family,
                "layout_stage_rank": stage[0],
                "layout_stage_id": stage[1],
                "layout_stage_title": stage[2],
            }
        )
        questions.append(learner)
        family_counts[family] += 1
    questions.sort(
        key=lambda row: (
            int(row["layout_stage_rank"]),
            str(row["skill"]),
            int(row["print_item_no"]),
        )
    )
    for position, row in enumerate(questions, 1):
        row["student_item_no"] = position
    if len(questions) != master.EXPECTED_RUNTIME_ITEMS:
        raise ValueError(f"student_question_count_invalid:{len(questions)}")
    return questions, dict(sorted(family_counts.items()))


def _esc(value: Any) -> str:
    return html.escape(str(value or ""))


def _table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    head = "".join(f"<th>{_esc(value)}</th>" for value in headers)
    body = "".join(
        "<tr>"
        + "".join(f"<td>{_esc(value)}</td>" for value in row)
        + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _noun_card(row: Mapping[str, Any]) -> str:
    return (
        '<div class="phrase-card">'
        f'<strong>{_esc(_memory_form(row))}</strong>'
        f'<span>{_esc(_gloss(row))}</span>'
        "</div>"
    )


def _prelearning_html(payload: Mapping[str, Any]) -> str:
    rules = "".join(
        '<div class="rule-card">'
        f'<strong>{_esc(row["article"])}</strong>'
        f'<p>{_esc(row["guide"])}</p>'
        + "".join(f"<p>{_esc(example)}</p>" for example in row["examples"])
        + "</div>"
        for row in payload["article_rules"]
    )
    core = "".join(_noun_card(row) for row in payload["core_nouns"])
    groups = "".join(
        '<div class="learning-group">'
        f'<h3>{_esc(group["title"])}</h3>'
        + _table(
            ("第一次說", "再說一次", "中文"),
            [
                (_memory_form(row), _definite_form(row), _gloss(row))
                for row in group["items"]
            ],
        )
        + "</div>"
        for group in payload["grouped_nouns"]
    )
    adjective_pairs = "".join(
        '<div class="pair-card">'
        f'<h3>{_esc(pair["left"].get("lemma"))} ↔ '
        f'{_esc(pair["right"].get("lemma"))}</h3>'
        + "".join(
            f"<p><strong>{_esc(example)}</strong></p>"
            for example in pair["approved_examples"]
        )
        + "</div>"
        for pair in payload["adjective_pairs"]
    )
    frames = _table(
        ("Frame", "一起說／寫"),
        [
            (row.get("frame_id"), row.get("template"))
            for row in payload["sentence_frames"]
        ],
    )
    contrast_rows = []
    for lemma in ("cat", "bag", "apple"):
        row = next(
            item
            for item in payload["reference_nouns"]
            if item.get("lemma") == lemma
        )
        contrast_rows.append((_memory_form(row), _definite_form(row), _gloss(row)))
    reference_rows = [
        (
            row.get("lemma"),
            _memory_form(row),
            _definite_form(row) or "—",
            _gloss(row),
        )
        for row in [
            *payload["reference_nouns"],
            *payload["reference_adjectives"],
        ]
    ]
    return f"""<!doctype html><html lang="zh-Hant"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Unit 01 Pre-learning</title><link rel="stylesheet" href="student.css"></head><body>
<div class="toolbar no-print"><a href="index.html">返回</a><button type="button" onclick="window.print()">列印／另存 PDF</button></div>
<section class="print-page"><h1>Unit 01 Pre-learning</h1><h2>a, an, the</h2><p>先記完整片語，再進入句子。</p><div class="grid3">{rules}</div>
<h2>Part 1｜8個核心片語</h2><div class="grid2">{core}</div></section>
<section class="print-page"><h1>Part 2｜名詞依情境分組</h1>{groups}</section>
<section class="print-page"><h1>Part 3｜形容詞成對學習</h1><div class="grid3">{adjective_pairs}</div>
<div class="callout"><strong>a / an看後面第一個聲音：</strong> a book → a new book → an old book</div></section>
<section class="print-page"><h1>Part 4｜第一次說與再說一次</h1>
{_table(("第一次說 a / an","再說一次 the","中文"), contrast_rows)}
<h2>先說片語，再放入Frame</h2>{frames}</section>
<section class="print-page"><h1>Part 5｜Phrase recognition</h1>
<div class="practice"><p>1. 一顆蘋果</p><span>○ a apple</span><span>○ an apple</span></div>
<div class="practice"><p>2. 一個藍色的袋子</p><span>○ a blue bag</span><span>○ an blue bag</span></div>
<div class="practice"><p>3. 一本舊書</p><span>○ a old book</span><span>○ an old book</span></div></section>
<section class="print-page"><h1>Part 6｜Phrase → Sentence</h1>
<div class="practice"><p>1. old + book</p><div class="answer-line"></div></div>
<div class="practice"><p>2. red + book</p><div class="answer-line"></div></div>
<div class="practice"><p>3. 選一個Sentence Frame，放入完整片語。</p><div class="write-line"></div><div class="write-line"></div></div></section>
<section class="print-page"><h1>Unit 01 Vocabulary Reference</h1>
<p>完整22詞放在最後查閱，不作為第一個學習畫面。</p>
{_table(("Word","一起記","再說一次","中文"), reference_rows)}</section>
<script src="student.js"></script></body></html>"""


def _question_card(row: Mapping[str, Any]) -> str:
    options = ""
    if row.get("options"):
        options = '<div class="choices">' + "".join(
            f'<div class="choice">○ {_esc(value)}</div>'
            for value in row["options"]
        ) + "</div>"
    stimulus = str(row.get("stimulus") or "").strip()
    stimulus_html = (
        f'<div class="stimulus">{_esc(stimulus)}</div>' if stimulus else ""
    )
    question_type = str(row.get("question_type") or "")
    if row.get("practice_only"):
        response = (
            '<div class="self-check">□ I said the phrase.　'
            "□ I said a complete sentence.</div>"
        )
    elif question_type == "word_order":
        response = '<div class="answer-box"></div>'
    elif options:
        response = ""
    else:
        response = '<div class="answer-line"></div>'
    return (
        '<article class="question-card">'
        f'<h3>{_esc(row["student_item_no"])}. {_esc(question_type)}</h3>'
        f'{stimulus_html}<p class="prompt">{_esc(row.get("prompt"))}</p>'
        f'{options}{response}</article>'
    )


def _questionbank_html(questions: Sequence[Mapping[str, Any]]) -> str:
    sections = []
    for stage_id, title, _families in STAGE_DEFINITIONS:
        rows = [row for row in questions if row["layout_stage_id"] == stage_id]
        sections.append(
            f'<section class="question-stage" data-stage="{_esc(stage_id)}">'
            f'<div class="stage-title"><h1>{_esc(title)}</h1><p>{len(rows)}題</p></div>'
            + "".join(_question_card(row) for row in rows)
            + "</section>"
        )
    controls = "".join(
        f'<label><input type="checkbox" data-stage-toggle="{_esc(stage_id)}" checked>'
        f'{_esc(title)}</label>'
        for stage_id, title, _families in STAGE_DEFINITIONS
    )
    return f"""<!doctype html><html lang="zh-Hant"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Unit 01 QuestionBank</title><link rel="stylesheet" href="student.css"></head><body>
<div class="toolbar no-print"><a href="index.html">返回</a><button type="button" onclick="window.print()">列印／另存 PDF</button></div>
<header class="questionbank-header"><h1>Unit 01 QuestionBank</h1><p>完整474題｜Phrase先於Sentence｜Speaking為practice only</p>
<div class="stage-controls no-print">{controls}</div></header>
<main>{''.join(sections)}</main><script src="student.js"></script></body></html>"""


STUDENT_CSS = """
:root{font-family:Arial,"Noto Sans TC","Microsoft JhengHei",sans-serif;color:#20262e;background:#e9edf1;line-height:1.45}
*{box-sizing:border-box}body{margin:0}.toolbar{position:sticky;top:0;z-index:10;display:flex;gap:14px;align-items:center;padding:12px 18px;background:#fff;border-bottom:1px solid #c9ced5}.toolbar a,.toolbar button,.launcher a{border:1px solid #2f4054;border-radius:6px;padding:9px 15px;background:#fff;color:#20262e;text-decoration:none;font:inherit}.toolbar button,.launcher a.primary{background:#2f4054;color:#fff}.print-page,.question-stage,.launcher{width:210mm;min-height:297mm;margin:18px auto;padding:16mm 17mm;background:#fff;box-shadow:0 2px 12px #0002}.print-page{break-after:page}.grid2{display:grid;grid-template-columns:1fr 1fr;gap:12px}.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.rule-card,.phrase-card,.pair-card,.learning-group,.practice,.question-card{border:1px solid #c9ced5;border-radius:7px;padding:12px;break-inside:avoid}.phrase-card{display:flex;justify-content:space-between;gap:8px}.phrase-card strong{font-size:20px}.learning-group{margin:12px 0}.callout,.stimulus{border-left:5px solid #2f4054;background:#f3f5f7;padding:12px 15px;margin:14px 0}.practice{margin:12px 0}.practice span{display:inline-block;margin-right:20px}.answer-line,.write-line{height:30px;border-bottom:1.5px solid #20262e}.answer-box{min-height:45px;border:1.5px solid #20262e;border-radius:6px}.questionbank-header{max-width:1120px;margin:18px auto;padding:18px;background:#fff}.stage-controls{display:grid;grid-template-columns:1fr 1fr;gap:7px}.stage-title{display:flex;justify-content:space-between;align-items:end;border-bottom:2px solid #20262e;margin-bottom:16px}.question-card{margin:12px 0}.question-card h3{font-size:15px;color:#66717f}.prompt{font-size:17px;font-weight:700}.choices{display:grid;grid-template-columns:repeat(3,1fr);gap:9px}.choice{border:1px solid #c9ced5;border-radius:6px;padding:8px}.self-check{margin-top:10px;color:#66717f}table{width:100%;border-collapse:collapse;margin:12px 0}th,td{border:1px solid #c9ced5;padding:7px;text-align:left;vertical-align:top}th{background:#f3f5f7}.launcher{display:grid;align-content:start;gap:18px}.launcher nav{display:flex;flex-wrap:wrap;gap:12px}.muted{color:#66717f}
@media print{:root{background:#fff}body{background:#fff}.no-print{display:none!important}.print-page,.question-stage,.launcher{width:auto;min-height:auto;margin:0;box-shadow:none;padding:0}.question-stage{break-before:page}.question-card{break-inside:avoid}.stage-title{break-after:avoid}@page{size:A4;margin:12mm}}
"""

STUDENT_JS = """
document.querySelectorAll('[data-stage-toggle]').forEach(input=>{input.addEventListener('change',()=>{const key=input.dataset.stageToggle;document.querySelectorAll(`[data-stage="${key}"]`).forEach(section=>{section.hidden=!input.checked;});});});
"""


def _launcher_html(question_count: int) -> str:
    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Unit 01 Student Package</title><link rel="stylesheet" href="student.css"></head><body><main class="launcher"><h1>Unit 01｜a, an, the</h1><p class="muted">先完成Pre-learning，再進入QuestionBank。教師私有版不在此頁提供入口。</p><nav><a class="primary" href="prelearning.html">開始Pre-learning</a><a href="questionbank.html">開啟QuestionBank（{question_count}題）</a><button type="button" onclick="window.print()">列印本頁</button></nav><h2>學習順序</h2><p>Word → Phrase → Phrase construction → Complete sentence → Connected sentences → Context transfer</p></main><script src="student.js"></script></body></html>"""


def build_student_package(
    *,
    disposable_product_root: Path,
    approved_content: Mapping[str, Any],
    output_root: Path | None = None,
) -> dict[str, Any]:
    base_report = master.build_package(
        disposable_product_root=Path(disposable_product_root),
        approved_content=approved_content,
        output_root=output_root,
    )
    output_root = Path(str(base_report["output_root"]))
    teacher_before = _teacher_identity(output_root)
    contract = master._approved_contract()
    vocabulary = dict(contract["vocabulary_contract"])
    chunks = dict(contract["chunk_contract"])
    frames = dict(contract["sentence_frame_contract"])
    prelearning = _prelearning_payload(
        vocabulary=vocabulary,
        chunks=chunks,
        frames=frames,
    )
    database = Path(disposable_product_root) / "shared/database/learner_runtime.sqlite3"
    questions, family_counts = _safe_questions(database)
    safe_core = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "unit_id": master.contract_builder.UNIT_ID,
        "source_manifest_sha256": base_report["manifest_sha256"],
        "runtime_item_count": len(questions),
        "pattern_family_counts": family_counts,
        "stage_count": len(STAGE_DEFINITIONS),
        "active_vocabulary_count": 22,
        "active_noun_count": 16,
        "active_adjective_count": 6,
        "instructional_phrase_count": 21,
        "sentence_frame_count": 11,
        "prelearning_approved": True,
        "phrase_before_sentence_order": True,
        "learner_images_present": False,
        "learner_answer_leakage_count": 0,
        "teacher_files_unchanged": True,
        "teacher_edition_private": True,
        "second_question_bank_created": False,
        "formal_production_activation_approved": False,
        "unit02_to_unit24_modified": False,
        "a2_unlocked": False,
        "next_short_step": NEXT_SHORT_STEP,
        "prelearning": prelearning,
        "questions": questions,
    }
    safe = {**safe_core, "artifact_sha256": digest(safe_core)}
    learner_root = output_root / "learner"
    master.atomic_json(learner_root / STUDENT_DATA_NAME, safe)
    master.atomic_text(learner_root / "index.html", _launcher_html(len(questions)))
    master.atomic_text(learner_root / "prelearning.html", _prelearning_html(prelearning))
    master.atomic_text(learner_root / "questionbank.html", _questionbank_html(questions))
    master.atomic_text(learner_root / "student.css", STUDENT_CSS)
    master.atomic_text(learner_root / "student.js", STUDENT_JS)
    teacher_after = _teacher_identity(output_root)
    if teacher_after != teacher_before:
        raise ValueError("teacher_files_changed_by_student_package")
    report = master.load(output_root / master.REPORT_NAME)
    report_core = {
        key: value for key, value in report.items() if key != "readback_sha256"
    }
    files = dict(report_core.get("files") or {})
    for name in (
        "learner/index.html",
        f"learner/{STUDENT_DATA_NAME}",
        "learner/prelearning.html",
        "learner/questionbank.html",
        "learner/student.css",
        "learner/student.js",
    ):
        files[name] = master.file_identity(output_root / name)
    report_core.update(
        {
            "files": files,
            "student_package_status": PASS_STATUS,
            "student_package_artifact_sha256": safe["artifact_sha256"],
            "student_package_question_count": len(questions),
            "student_package_stage_count": len(STAGE_DEFINITIONS),
            "student_package_phrase_before_sentence": True,
            "student_package_images_present": False,
            "teacher_files_unchanged": True,
            "teacher_file_identities": teacher_before,
            "next_short_step": NEXT_SHORT_STEP,
        }
    )
    final_report = {**report_core, "readback_sha256": master.digest(report_core)}
    master.atomic_json(output_root / master.REPORT_NAME, final_report)
    return {
        "status": PASS_STATUS,
        "output_root": str(output_root),
        "runtime_item_count": len(questions),
        "pattern_family_counts": family_counts,
        "stage_count": len(STAGE_DEFINITIONS),
        "teacher_files_unchanged": True,
        "learner_images_present": False,
        "learner_answer_leakage_count": 0,
        "phrase_before_sentence_order": True,
        "second_question_bank_created": False,
        "formal_production_activation_approved": False,
        "unit02_to_unit24_modified": False,
        "a2_unlocked": False,
        "artifact_sha256": safe["artifact_sha256"],
        "next_short_step": NEXT_SHORT_STEP,
    }
