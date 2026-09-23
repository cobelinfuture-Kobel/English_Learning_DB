#!/usr/bin/env python3
"""A1FS-V1 Unit05 final learner PDF materialization.

Presentation-only consumer over the three merged FAR7 canonical JSON
authorities.

This v2 renderer intentionally changes only PDF presentation:
- learner-facing worksheet hierarchy
- readable reading/stimulus panels
- explicit writing space
- learner-friendly task titles/categories
- compact two-column answer key

It does NOT modify learner English in the canonical JSON, author new practice,
generate audio/visual assets, reopen Reader360/Q10, or unlock A2/A2+ grammar.
"""
from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from product.a1fs_v1_2_1 import (
    u01qb18h_r1_unit01_twelve_form_learner_pdf_materialization as u01_pdf,
)
from ulga.builders import (
    build_a1fs_ops_v1_unit01_student_package_chromium_main_product_entry_acceptance
    as chromium_acceptance,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Presentation-only Unit05 PDF delivery consumer over the merged FAR7 "
    "canonical JSON authorities. It does not author or mutate learner-facing "
    "English, QuestionBank items, Reader360, media assets, scoring, grammar, "
    "vocabulary, Unit06, A2 or A2+ authority."
)

TASK_ID = "A1FS-V1-U05FINAL_CanonicalJSONToPDFMaterialization"
PASS_STATUS = "PASS_A1FS_V1_U05FINAL_CANONICAL_JSON_TO_PDF_V2"
ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "product/a1fs_v1_2_1/data"
DEFAULT_OUTPUT = ROOT / "product/a1fs_v1_2_1/pdf/unit05"

CORE = DATA / "unit05_core_practice_480.json"
KET = DATA / "unit05_ket_adapted_practice_672.json"
DICTATION = DATA / "unit05_dictation_practice_480.json"

PRACTICE_PDF_NAME = "unit05_executable_practice_816.pdf"
ANSWER_PDF_NAME = "unit05_answer_key_816.pdf"
PRACTICE_HTML_NAME = "unit05_executable_practice_816.html"
ANSWER_HTML_NAME = "unit05_answer_key_816.html"

FAMILY_TITLES = {
    "BE_FORM_SELECTION": "Choose the correct be form",
    "ONE_WORD_BE_COMPLETION": "Complete with one be word",
    "AFFIRMATIVE_NEGATIVE_CONTRAST": "Affirmative or negative?",
    "SUBJECT_BE_AGREEMENT": "Match the subject and be",
    "SENTENCE_CORRECTION": "Fix the be form",
    "CONTROLLED_SELF_PRODUCTION": "Write your own sentence",
    "SHORT_MESSAGE_MEANING": "Read a short message",
    "PERSON_TEXT_DETAIL_MATCHING": "Match details to texts",
    "LONG_TEXT_DETAIL_INFERENCE": "Find the supported detail",
    "LEXICAL_CLOZE": "Complete the source sentence",
    "OPEN_CLOZE": "Open cloze",
    "SHORT_COMMUNICATIVE_EMAIL": "Write a short message",
    "PERSONAL_INTERVIEW": "Speak: personal answer",
}

STAGE_LABELS = {
    "GUIDED": "Guided",
    "REDUCED_SUPPORT": "Reduced Support",
    "INDEPENDENT": "Independent",
    "UNSEEN_TRANSFER": "Unseen Transfer",
    "DELAYED_RETENTION": "Delayed Retention",
}

MEDIA_PENDING_FAMILIES = {
    "PICTURE_SEQUENCE_STORY",
    "AUDIO_PICTURE_DETAIL_SELECTION",
    "AUDIO_NOTE_COMPLETION",
    "AUDIO_CONVERSATION_DETAIL",
    "SHORT_AUDIO_GIST_INTENT_DETAIL",
    "AUDIO_LIST_MATCHING",
    "COLLABORATIVE_VISUAL_DISCUSSION",
    "DELAYED_DICTATION",
}

PRACTICE_CSS = r"""
@page {
  size: A4;
  margin: 13mm 13mm 15mm 13mm;
  @bottom-left {
    content: "A1FS-V1 · Unit05";
    color: #667085;
    font-size: 8pt;
  }
  @bottom-right {
    content: "Page " counter(page) " of " counter(pages);
    color: #667085;
    font-size: 8pt;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: Arial, Helvetica, sans-serif;
  color: #172033;
  font-size: 11pt;
  line-height: 1.42;
}
.cover {
  min-height: 250mm;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 14mm;
  border: 1.5px solid #203a67;
}
.cover h1 {
  font-size: 28pt;
  line-height: 1.05;
  margin: 0 0 5mm;
  color: #203a67;
}
.kicker {
  font-size: 10pt;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1.4px;
  color: #64748b;
  margin-bottom: 2mm;
}
.cover-meta {
  margin-top: 8mm;
  padding: 6mm;
  background: #f4f7fb;
  border-left: 4px solid #203a67;
  border-radius: 4px;
}
.stage-break {
  break-before: page;
  padding: 5mm 0 3mm;
  border-bottom: 2px solid #203a67;
  margin-bottom: 5mm;
}
.stage-break .stage {
  color: #203a67;
  font-size: 17pt;
  font-weight: 700;
}
.stage-break .sub {
  color: #667085;
  font-size: 9.5pt;
  margin-top: 1mm;
}
.section-banner {
  margin: 0 0 3mm;
  padding: 2.2mm 3mm;
  background: #203a67;
  color: white;
  font-size: 9.5pt;
  font-weight: 700;
  letter-spacing: .3px;
  border-radius: 4px;
}
.card {
  break-inside: avoid;
  border: 1px solid #d5dce8;
  border-radius: 7px;
  margin: 0 0 3.2mm;
  overflow: hidden;
}
.cardhead {
  display: flex;
  gap: 2.5mm;
  align-items: center;
  background: #f2f6fb;
  border-bottom: 1px solid #dce3ee;
  padding: 2mm 2.5mm;
}
.qnum {
  min-width: 11mm;
  height: 7mm;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4mm;
  background: #203a67;
  color: white;
  font-weight: 700;
  font-size: 8.5pt;
}
.qtitle {
  font-weight: 700;
  font-size: 10.7pt;
  color: #203a67;
}
.skill {
  margin-left: auto;
  font-size: 7.8pt;
  padding: 1mm 2.2mm;
  border: 1px solid #b8c5d9;
  color: #44546f;
  border-radius: 4mm;
  background: white;
  white-space: nowrap;
}
.content { padding: 2.6mm 3mm 3mm; }
.instruction {
  color: #475467;
  font-size: 9.3pt;
  margin-bottom: 2mm;
}
.example, .stimulus {
  background: #f8fafc;
  border-left: 3px solid #8ba2c7;
  padding: 2mm 2.5mm;
  margin: 2mm 0 2.5mm;
  border-radius: 2px;
}
.example b, .stimulus b {
  color: #475467;
  font-size: 8pt;
  text-transform: uppercase;
  letter-spacing: .5px;
}
.prompt {
  font-size: 11pt;
  font-weight: 700;
  margin: 2mm 0 2.3mm;
}
.options {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.6mm;
}
.option {
  display: flex;
  gap: 2mm;
  align-items: flex-start;
  border: 1px solid #d8dee9;
  border-radius: 5px;
  padding: 1.7mm 2.2mm;
}
.letter {
  flex: 0 0 5.5mm;
  height: 5.5mm;
  border-radius: 3mm;
  background: #e7edf6;
  color: #203a67;
  font-size: 8pt;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}
.answerline {
  border-bottom: 1px solid #8390a3;
  height: 7mm;
  margin-top: 1mm;
}
.answerlines .answerline { height: 7mm; }
.textblock {
  background: #fbfcfe;
  border: 1px solid #e3e8ef;
  border-radius: 5px;
  padding: 2mm 2.3mm;
  margin: 1.5mm 0;
}
.textlabel {
  font-weight: 700;
  color: #203a67;
  margin-right: 1.5mm;
}
.statement {
  padding: 1.4mm 0;
  border-bottom: 1px dotted #ccd4df;
}
.plan {
  padding: 2mm 2.5mm;
  border: 1px dashed #a9b6c8;
  border-radius: 5px;
  margin: 2mm 0;
}
.plan div { margin: .8mm 0; }
.speakbox {
  border: 1px solid #d8dee9;
  background: #fff;
  border-radius: 5px;
  padding: 2.4mm;
}
.small {
  font-size: 8.3pt;
  color: #667085;
}
"""

ANSWER_CSS = r"""
@page {
  size: A4;
  margin: 12mm 12mm 14mm 12mm;
  @bottom-left {
    content: "A1FS-V1 · Unit05 Answer Key";
    color: #667085;
    font-size: 8pt;
  }
  @bottom-right {
    content: "Page " counter(page) " of " counter(pages);
    color: #667085;
    font-size: 8pt;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: Arial, Helvetica, sans-serif;
  color: #172033;
  font-size: 9.3pt;
  line-height: 1.3;
}
.cover {
  min-height: 250mm;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 14mm;
  border: 1.5px solid #203a67;
}
.cover h1 {
  font-size: 28pt;
  margin: 0 0 5mm;
  color: #203a67;
}
.kicker {
  font-size: 10pt;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1.4px;
  color: #64748b;
}
.answer-grid {
  columns: 2;
  column-gap: 5mm;
}
.stage-title, .section-title {
  break-inside: avoid;
  column-span: all;
  background: #203a67;
  color: white;
  padding: 2mm 2.5mm;
  border-radius: 4px;
  font-weight: 700;
  margin: 2mm 0 2.2mm;
}
.answer-card {
  break-inside: avoid;
  border: 1px solid #d5dce8;
  border-radius: 5px;
  margin: 0 0 2mm;
  padding: 2mm 2.3mm;
}
.answer-head {
  color: #203a67;
  font-weight: 700;
  margin-bottom: 1mm;
}
.answer-text { color: #172033; }
.focus {
  margin-top: 1mm;
  color: #667085;
  font-size: 8pt;
}
"""


class Unit05FinalPdfError(ValueError):
    pass


def _load(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise Unit05FinalPdfError(f"NOT_OBJECT:{path}")
    return obj


def _family(item: Mapping[str, Any]) -> str:
    return str(
        item.get("target_archetype")
        or item.get("task_family")
        or item.get("slot_category")
        or "Practice"
    )


def _title(item: Mapping[str, Any]) -> str:
    return FAMILY_TITLES.get(_family(item), "Unit05 practice")


def _category(item: Mapping[str, Any]) -> str:
    family = _family(item)
    if family in {"CONTROLLED_SELF_PRODUCTION", "SHORT_COMMUNICATIVE_EMAIL"}:
        return "Writing"
    if family == "PERSONAL_INTERVIEW":
        return "Speaking"
    if family in {
        "SHORT_MESSAGE_MEANING",
        "PERSON_TEXT_DETAIL_MATCHING",
        "LONG_TEXT_DETAIL_INFERENCE",
        "LEXICAL_CLOZE",
        "OPEN_CLOZE",
    }:
        return "Reading & Use of English"
    return "Grammar Practice"


def _stage(item: Mapping[str, Any]) -> str:
    return STAGE_LABELS.get(str(item.get("stage") or ""), str(item.get("stage") or ""))


def _escape(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def _items() -> tuple[list[dict[str, Any]], dict[str, int]]:
    core, ket, dictation = map(_load, (CORE, KET, DICTATION))
    core_exec = [
        row for row in core["items"]
        if row.get("execution_status") == "EXECUTABLE_TEXT_ONLY"
    ]
    ket_exec = [
        row for row in ket["items"]
        if row.get("execution_status") == "EXECUTABLE_TEXT_ONLY"
    ]
    ket_pending = [
        row for row in ket["items"]
        if row.get("execution_status") == "NOT_EXECUTABLE_ASSET_PENDING"
    ]
    dictation_pending = [
        row for row in dictation["items"]
        if row.get("execution_status") == "NOT_EXECUTABLE_ASSET_PENDING"
    ]
    counts = (
        len(core_exec),
        len(ket_exec),
        len(ket_pending),
        len(dictation_pending),
    )
    if counts != (480, 336, 336, 480):
        raise Unit05FinalPdfError(f"DENOMINATOR_DRIFT:{counts}")
    if any(row.get("asset_preconditions") for row in ket_exec):
        raise Unit05FinalPdfError("EXECUTABLE_KET_HAS_ASSET_PRECONDITION")
    for row in ket_pending:
        if not row.get("asset_preconditions"):
            raise Unit05FinalPdfError(
                f"MEDIA_PENDING_WITHOUT_ASSET_GATE:{row.get('practice_id')}"
            )
    return core_exec + ket_exec, {
        "core": 480,
        "ket_text": 336,
        "ket_media_pending": 336,
        "dictation_pending": 480,
    }


def _option(option: Any, index: int) -> tuple[str, str]:
    if isinstance(option, str):
        return chr(65 + index), option
    return (
        str(option.get("id") or option.get("label") or chr(65 + index)),
        str(option.get("text") or option.get("description") or ""),
    )


def _stimulus_html(item: Mapping[str, Any]) -> str:
    content = dict(item.get("learner_facing_content") or {})
    stimulus = dict(content.get("stimulus") or {})
    parts: list[str] = []

    example = dict(content.get("source_example") or {})
    if content.get("source_example_visible_during_attempt") and example.get("text"):
        parts.append(
            '<div class="example"><b>Example</b><br>'
            + _escape(example["text"])
            + "</div>"
        )

    if stimulus.get("text"):
        parts.append(
            '<div class="stimulus"><b>Read</b><br>'
            + _escape(stimulus["text"])
            + "</div>"
        )

    for row in stimulus.get("texts") or []:
        parts.append(
            '<div class="textblock"><span class="textlabel">'
            + _escape(row.get("label"))
            + "</span>"
            + _escape(row.get("text"))
            + "</div>"
        )

    if stimulus.get("source_context"):
        parts.append(
            '<div class="stimulus"><b>Read</b><br>'
            + _escape(stimulus["source_context"])
            + "</div>"
        )

    plan = list(stimulus.get("content_point_plan") or [])
    if plan:
        plan_html = ['<div class="plan"><b>Sentence plan</b>']
        for row in plan:
            plan_html.append(
                "<div><b>"
                + _escape(row.get("sentence"))
                + ".</b> "
                + _escape(row.get("source_fact"))
                + "</div>"
            )
        plan_html.append("</div>")
        parts.append("".join(plan_html))

    return "".join(parts)


def _response_html(item: Mapping[str, Any]) -> str:
    response = dict(item.get("response_contract") or {})
    parts: list[str] = []

    statements = list(response.get("statements") or [])
    for row in statements:
        parts.append(
            '<div class="statement"><b>'
            + _escape(row.get("id"))
            + ".</b> "
            + _escape(row.get("text"))
            + " &nbsp; → ______</div>"
        )

    options = list(response.get("options") or [])
    if options:
        parts.append('<div class="options">')
        for index, option in enumerate(options):
            label, text = _option(option, index)
            parts.append(
                '<div class="option"><span class="letter">'
                + _escape(label)
                + "</span><span>"
                + _escape(text)
                + "</span></div>"
            )
        parts.append("</div>")

    for row in response.get("fields") or []:
        parts.append(
            '<div class="statement"><b>'
            + _escape(row.get("id"))
            + ".</b> "
            + _escape(row.get("label"))
            + " &nbsp; __________</div>"
        )

    response_type = str(response.get("type") or "")
    if response_type == "ONE_WORD_ENTRY":
        parts.append('<div class="answerline"></div>')
    elif response_type == "CORRECTION":
        parts.append(
            '<div class="small">Write the corrected sentence.</div>'
            '<div class="answerline"></div>'
        )
    elif response_type == "FREE_TEXT":
        parts.append(
            '<div class="answerlines">'
            '<div class="answerline"></div>'
            '<div class="answerline"></div>'
            '<div class="answerline"></div>'
            "</div>"
        )
    elif response_type == "SPEAK":
        parts.append(
            '<div class="speakbox"><b>Say it aloud.</b><br>'
            '<span class="small">Optional note:</span>'
            '<div class="answerline"></div></div>'
        )

    return "".join(parts)


def render_practice_html(items: Sequence[Mapping[str, Any]]) -> str:
    parts = [
        '<!doctype html><html><head><meta charset="utf-8"><style>',
        PRACTICE_CSS,
        "</style></head><body>",
        '<section class="cover">',
        '<div class="kicker">A1FS-V1 · Unit05</div>',
        "<h1>Present be Practice</h1>",
        "<div>Printable worksheet edition</div>",
        '<div class="cover-meta"><b>816 executable text-only activities</b><br>'
        "Core grammar 480 + KET-adapted text practice 336.<br><br>"
        "Media-bound activities are intentionally deferred until approved "
        "audio/visual assets exist.</div>",
        "</section>",
    ]

    previous_stage = ""
    previous_category = ""
    for number, item in enumerate(items, start=1):
        stage = _stage(item)
        category = _category(item)
        if stage != previous_stage:
            parts.append(
                '<div class="stage-break"><div class="stage">'
                + _escape(stage)
                + '</div><div class="sub">Unit05 present-be practice</div></div>'
            )
            previous_stage = stage
            previous_category = ""
        if category != previous_category:
            parts.append(
                '<div class="section-banner">'
                + _escape(category)
                + "</div>"
            )
            previous_category = category

        content = dict(item.get("learner_facing_content") or {})
        parts.extend(
            [
                '<article class="card">',
                '<div class="cardhead">',
                '<div class="qnum">Q'
                + f"{number:03d}"
                + "</div>",
                '<div class="qtitle">'
                + _escape(_title(item))
                + "</div>",
                '<div class="skill">'
                + _escape(category)
                + "</div>",
                "</div>",
                '<div class="content">',
                '<div class="instruction">'
                + _escape(content.get("instruction_text"))
                + "</div>",
                _stimulus_html(item),
                '<div class="prompt">'
                + _escape(content.get("prompt"))
                + "</div>",
                _response_html(item),
                "</div></article>",
            ]
        )

    parts.append("</body></html>")
    return "".join(parts)


def _answer_summary(item: Mapping[str, Any]) -> str:
    answer = dict(item.get("answer_binding_or_rubric") or {})
    if "correct_option" in answer:
        return "Answer: " + str(answer["correct_option"])
    if "correct_option_id" in answer:
        return "Answer: " + str(answer["correct_option_id"])
    if answer.get("accepted_answers"):
        return "Accepted: " + ", ".join(
            str(value) for value in answer["accepted_answers"]
        )
    if answer.get("accepted_full_answers"):
        return "Accepted: " + " / ".join(
            str(value) for value in answer["accepted_full_answers"]
        )
    if "accepted_word" in answer:
        return "Accepted: " + str(answer["accepted_word"])
    if isinstance(answer.get("matches"), dict):
        return "Matches: " + ", ".join(
            f"{key}-{value}" for key, value in answer["matches"].items()
        )
    if isinstance(answer.get("answers"), dict):
        rows: list[str] = []
        for key, value in answer["answers"].items():
            rendered = (
                "/".join(str(part) for part in value)
                if isinstance(value, list)
                else str(value)
            )
            rows.append(f"{key}: {rendered}")
        return "Answers: " + "; ".join(rows)
    if "model_response_example" in answer:
        return "Model: " + str(answer["model_response_example"])
    if answer.get("rubric_dimensions"):
        return "Rubric: " + "; ".join(
            str(value) for value in answer["rubric_dimensions"]
        )
    return "Answer guidance: see canonical rubric."


def render_answer_html(items: Sequence[Mapping[str, Any]]) -> str:
    parts = [
        '<!doctype html><html><head><meta charset="utf-8"><style>',
        ANSWER_CSS,
        "</style></head><body>",
        '<section class="cover">',
        '<div class="kicker">A1FS-V1 · Unit05</div>',
        "<h1>Answer Key 816</h1>",
        "<div>Compact two-column teacher reference</div>",
        "<p>Answers follow the exact learner PDF numbering Q001-Q816. "
        "Deferred media-bound slots are not represented as executable.</p>",
        "</section>",
        '<div class="answer-grid">',
    ]

    previous_stage = ""
    previous_category = ""
    for number, item in enumerate(items, start=1):
        stage = _stage(item)
        category = _category(item)
        if stage != previous_stage:
            parts.append(
                '<div class="stage-title">'
                + _escape(stage)
                + "</div>"
            )
            previous_stage = stage
            previous_category = ""
        if category != previous_category:
            parts.append(
                '<div class="section-title">'
                + _escape(category)
                + "</div>"
            )
            previous_category = category

        focus = str(
            (item.get("answer_binding_or_rubric") or {}).get("correction_focus")
            or ""
        )
        parts.extend(
            [
                '<article class="answer-card">',
                '<div class="answer-head">Q'
                + f"{number:03d}"
                + " · "
                + _escape(_title(item))
                + "</div>",
                '<div class="answer-text">'
                + _escape(_answer_summary(item))
                + "</div>",
            ]
        )
        if focus:
            parts.append(
                '<div class="focus">Focus: '
                + _escape(focus)
                + "</div>"
            )
        parts.append("</article>")

    parts.append("</div></body></html>")
    return "".join(parts)


def materialize(
    output_dir: Path = DEFAULT_OUTPUT,
    *,
    chromium_path: Path | None = None,
    browser_runner: Callable[..., Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    items, counts = _items()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    practice_html = output_dir / PRACTICE_HTML_NAME
    answer_html = output_dir / ANSWER_HTML_NAME
    practice_pdf = output_dir / PRACTICE_PDF_NAME
    answer_pdf = output_dir / ANSWER_PDF_NAME

    practice_html.write_text(
        render_practice_html(items),
        encoding="utf-8",
    )
    answer_html.write_text(
        render_answer_html(items),
        encoding="utf-8",
    )

    chromium = (
        Path(chromium_path).resolve(strict=True)
        if chromium_path is not None
        else chromium_acceptance.discover_chromium()
    )
    run_browser = browser_runner or u01_pdf._run_pdf_browser_headerless

    for source_html, output_pdf in (
        (practice_html, practice_pdf),
        (answer_html, answer_pdf),
    ):
        run_browser(
            chromium,
            source_html=source_html,
            output_path=output_pdf,
            mode="PDF",
        )
        if not output_pdf.is_file() or output_pdf.stat().st_size < 1024:
            raise Unit05FinalPdfError(
                f"PDF_OUTPUT_INVALID:{output_pdf}"
            )

    return {
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "executable_count": 816,
        "asset_pending_count": 816,
        **counts,
        "practice_pdf": str(practice_pdf),
        "answer_pdf": str(answer_pdf),
        "practice_html": str(practice_html),
        "answer_html": str(answer_html),
        "audio_generated": False,
        "visual_generated": False,
        "engineering_family_labels_visible": False,
        "unit05_closeout_ready": True,
    }


def main(argv: Sequence[str] | None = None) -> int:
    report = materialize()
    for key, value in report.items():
        print(f"{key.upper()}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
