#!/usr/bin/env python3
"""A1FS-V1 Unit05 final PDF materialization from merged FAR7 authorities.

Scope:
- render only currently executable text-only practice:
  Core 480 + KET-adapted text 336 = 816
- keep KET media 336 + delayed dictation 480 deferred in canonical JSON
- generate no audio, visual, new learner English, QuestionBank, selector, or A2 grammar
"""
from __future__ import annotations

import json
import textwrap
import unicodedata
from pathlib import Path
from typing import Any

TASK_ID = "A1FS-V1-U05FINAL_CanonicalJSONToPDFMaterialization"
PASS_STATUS = "PASS_A1FS_V1_U05FINAL_CANONICAL_JSON_TO_PDF"
ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "product/a1fs_v1_2_1/data"
DEFAULT_OUTPUT = ROOT / "product/a1fs_v1_2_1/pdf/unit05"
CORE = DATA / "unit05_core_practice_480.json"
KET = DATA / "unit05_ket_adapted_practice_672.json"
DICTATION = DATA / "unit05_dictation_practice_480.json"

PW, PH = 595, 842
ML, MR, TOP, BOTTOM = 48, 48, 54, 44


class Unit05FinalPdfError(ValueError):
    pass


def _load(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise Unit05FinalPdfError(f"NOT_OBJECT:{path}")
    return obj


def _norm(value: Any) -> str:
    if value is None:
        return ""
    return (
        str(value)
        .replace("\u2018", "'").replace("\u2019", "'")
        .replace("\u201c", '"').replace("\u201d", '"')
        .replace("\u2013", "-").replace("\u2014", "-")
        .replace("\u2026", "...").replace("\u00a0", " ")
        .replace("\r\n", "\n").replace("\r", "\n")
    )


def _pdf_escape(value: Any) -> str:
    out: list[str] = []
    for ch in _norm(value):
        code = ord(ch)
        if ch == "\\":
            out.append("\\\\")
        elif ch == "(":
            out.append("\\(")
        elif ch == ")":
            out.append("\\)")
        elif 32 <= code <= 126:
            out.append(ch)
        elif code <= 255:
            out.append("\\%03o" % code)
        else:
            decomp = unicodedata.normalize("NFKD", ch)
            ascii_text = "".join(
                x for x in decomp
                if ord(x) < 128 and not unicodedata.combining(x)
            )
            out.append(ascii_text or "?")
    return "".join(out)


def _wrap(value: Any, size: float = 10, indent: float = 0) -> list[str]:
    width = max(22, int((PW - ML - MR - indent) / (size * 0.52)))
    result: list[str] = []
    for paragraph in _norm(value).split("\n"):
        result.extend(
            textwrap.wrap(
                paragraph,
                width=width,
                break_long_words=False,
                break_on_hyphens=False,
            )
            or [""]
        )
    return result


def _option_text(option: Any, index: int) -> str:
    if isinstance(option, str):
        return f"{chr(65 + index)}. {_norm(option)}"
    label = _norm(option.get("id", option.get("label", chr(65 + index))))
    return f"{label}. {_norm(option.get('text', option.get('description', '')))}"


def _stimulus_lines(item: dict[str, Any]) -> list[str]:
    content = dict(item.get("learner_facing_content") or {})
    stimulus = dict(content.get("stimulus") or {})
    lines: list[str] = []
    example = content.get("source_example") or {}
    if content.get("source_example_visible_during_attempt") and example.get("text"):
        lines.append("Example: " + _norm(example["text"]))
    if stimulus.get("text"):
        lines.append("Text: " + _norm(stimulus["text"]))
    for row in stimulus.get("texts") or []:
        lines.append(f"{_norm(row.get('label'))}. {_norm(row.get('text'))}")
    if stimulus.get("source_context"):
        lines.append("Source context: " + _norm(stimulus["source_context"]))
    for row in stimulus.get("content_point_plan") or []:
        lines.append(
            f"Sentence {_norm(row.get('sentence'))}: "
            f"{_norm(row.get('source_fact'))}"
        )
    return lines


def _response_lines(item: dict[str, Any]) -> list[tuple[str, str]]:
    response = dict(item.get("response_contract") or {})
    lines: list[tuple[str, str]] = []
    for index, option in enumerate(response.get("options") or []):
        lines.append(("option", _option_text(option, index)))
    stimulus = ((item.get("learner_facing_content") or {}).get("stimulus") or {})
    if response.get("texts") and not stimulus.get("texts"):
        for row in response["texts"]:
            lines.append(("body", f"{_norm(row.get('label'))}. {_norm(row.get('text'))}"))
    if response.get("statements"):
        lines.append(("label", "Statements:"))
        for row in response["statements"]:
            lines.append(
                ("option", f"{_norm(row.get('id'))}. {_norm(row.get('text'))}  -> ____")
            )
    for row in response.get("fields") or []:
        lines.append(
            ("option", f"{_norm(row.get('id'))}. {_norm(row.get('label'))}  __________")
        )
    response_type = _norm(response.get("type"))
    if response_type == "ONE_WORD_ENTRY":
        lines.append(("answer", "Answer: ____________________"))
    elif response_type == "CORRECTION":
        lines.extend(
            [
                ("label", "Correct sentence:"),
                ("answer", "____________________________________________________________"),
            ]
        )
    elif response_type == "FREE_TEXT":
        lines.extend(
            [
                ("label", "Your final answer:"),
                ("answer", "____________________________________________________________"),
                ("answer", "____________________________________________________________"),
            ]
        )
        if (
            "TWO" in _norm(response.get("output_level"))
            or item.get("task_family") == "SHORT_COMMUNICATIVE_EMAIL"
        ):
            lines.append(("answer", "____________________________________________________________"))
    elif response_type == "SPEAK":
        lines.extend(
            [
                ("label", "Say your answer aloud. Optional note:"),
                ("answer", "____________________________________________________________"),
            ]
        )
    return lines


def _answer_summary(item: dict[str, Any]) -> str:
    answer = dict(item.get("answer_binding_or_rubric") or {})
    if "correct_option" in answer:
        return "Answer: " + _norm(answer["correct_option"])
    if "correct_option_id" in answer:
        return "Answer: " + _norm(answer["correct_option_id"])
    if answer.get("accepted_answers"):
        return "Accepted: " + ", ".join(map(_norm, answer["accepted_answers"]))
    if answer.get("accepted_full_answers"):
        return "Accepted: " + " / ".join(map(_norm, answer["accepted_full_answers"]))
    if "accepted_word" in answer:
        return "Accepted: " + _norm(answer["accepted_word"])
    if isinstance(answer.get("matches"), dict):
        return "Matches: " + ", ".join(
            f"{key}-{value}" for key, value in answer["matches"].items()
        )
    if isinstance(answer.get("answers"), dict):
        parts = []
        for key, value in answer["answers"].items():
            rendered = "/".join(map(_norm, value)) if isinstance(value, list) else _norm(value)
            parts.append(f"{key}: {rendered}")
        return "Answers: " + "; ".join(parts)
    if "model_response_example" in answer:
        return "Model example: " + _norm(answer["model_response_example"])
    if answer.get("rubric_dimensions"):
        return "Rubric: " + "; ".join(map(_norm, answer["rubric_dimensions"]))
    return "Answer guidance: see canonical rubric."


def _label(item: dict[str, Any]) -> str:
    return _norm(
        item.get("target_archetype")
        or item.get("task_family")
        or item.get("slot_category")
        or "Practice"
    )


class _Composer:
    def __init__(self, title: str, subtitle: str):
        self.title = title
        self.subtitle = subtitle
        self.pages: list[list[tuple[Any, ...]]] = []
        self.page: list[tuple[Any, ...]]
        self.y = 0.0
        self.new_page(cover=True)

    def new_page(self, cover: bool = False) -> None:
        self.page = []
        self.pages.append(self.page)
        self.y = PH - TOP
        if not cover:
            self.text(self.title, size=8, bold=True, leading=10)
            self.rule()
            self.space(6)

    def ensure(self, height: float) -> None:
        if self.y - height < BOTTOM + 18:
            self.new_page(cover=False)

    def text(
        self,
        value: Any,
        *,
        size: float = 10,
        bold: bool = False,
        indent: float = 0,
        leading: float | None = None,
    ) -> None:
        lead = leading or max(11, size * 1.25)
        lines = _wrap(value, size, indent)
        self.ensure(len(lines) * lead + 2)
        for line in lines:
            self.page.append(("text", ML + indent, self.y, size, bold, line))
            self.y -= lead

    def space(self, height: float = 6) -> None:
        self.ensure(height)
        self.y -= height

    def rule(self) -> None:
        self.ensure(7)
        self.page.append(("line", ML, self.y, PW - MR, self.y))
        self.y -= 7

    def cover(self) -> None:
        self.text("A1FS-V1 Unit05", size=22, bold=True, leading=28)
        self.text(self.title, size=18, bold=True, leading=23)
        self.space(10)
        self.text(self.subtitle, size=11, leading=15)
        self.space(12)
        self.text(
            "Canonical source: unit05_core_practice_480.json + "
            "unit05_ket_adapted_practice_672.json + "
            "unit05_dictation_practice_480.json",
            size=9,
        )
        self.space(8)
        self.text(
            "Executable now: 816 items (Core 480 + KET text-only 336).",
            size=11,
            bold=True,
        )
        self.text(
            "Deferred media-bound slots: 816 items "
            "(KET media 336 + Dictation 480).",
            size=10,
        )
        self.text(
            "Audio and visual assets are not fabricated in this PDF. "
            "Their reserved bindings remain in the canonical JSON authorities.",
            size=10,
        )
        self.space(12)
        self.text(
            "Unit05 scope remains A1/A1+. No A2 grammar is unlocked.",
            size=10,
        )

    def practice(self, item: dict[str, Any], number: int) -> None:
        self.ensure(110)
        self.text(f"Q{number}. {_label(item)}", size=11, bold=True, leading=14)
        content = dict(item.get("learner_facing_content") or {})
        self.text(content.get("instruction_text", ""), size=9.5)
        for line in _stimulus_lines(item):
            self.text(line, size=9.5, indent=10)
        prompt = _norm(content.get("prompt", ""))
        if prompt:
            self.text("Task: " + prompt, size=10, bold=True)
        for kind, line in _response_lines(item):
            self.text(
                line,
                size=9 if kind == "label" else 9.5,
                bold=kind == "label",
                indent=12 if kind == "option" else 0,
                leading=11.5,
            )
        self.space(4)
        self.rule()
        self.space(3)

    def answer(self, item: dict[str, Any], number: int) -> None:
        self.ensure(42)
        self.text(
            f"Q{number}. {_label(item)}  [{_norm(item.get('practice_id'))}]",
            size=9.5,
            bold=True,
            leading=12,
        )
        self.text(_answer_summary(item), size=9, indent=10, leading=11)
        focus = (item.get("answer_binding_or_rubric") or {}).get("correction_focus")
        if focus:
            self.text("Focus: " + _norm(focus), size=8.5, indent=10, leading=10.5)
        self.space(3)


def _pdf(composer: _Composer) -> bytes:
    for number, page in enumerate(composer.pages, start=1):
        page.append(("text", ML, 24, 8, False, f"Page {number} of {len(composer.pages)}"))

    objects: dict[int, str] = {
        1: "<< /Type /Catalog /Pages 2 0 R >>",
        3: "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        4: "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
    }
    kids: list[str] = []
    next_object = 5

    for page in composer.pages:
        page_object = next_object
        content_object = next_object + 1
        next_object += 2
        kids.append(f"{page_object} 0 R")
        stream: list[str] = []
        for operation in page:
            if operation[0] == "text":
                _, x, y, size, bold, text = operation
                stream.append(
                    f"BT /{'F2' if bold else 'F1'} {size} Tf "
                    f"1 0 0 1 {x:.2f} {y:.2f} Tm "
                    f"({_pdf_escape(text)}) Tj ET\n"
                )
            else:
                _, x1, y1, x2, y2 = operation
                stream.append(
                    f"0.65 G 0.6 w {x1:.2f} {y1:.2f} m "
                    f"{x2:.2f} {y2:.2f} l S 0 G\n"
                )
        stream_text = "".join(stream)
        objects[page_object] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PW} {PH}] "
            f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> "
            f"/Contents {content_object} 0 R >>"
        )
        objects[content_object] = (
            f"<< /Length {len(stream_text.encode('latin-1', 'replace'))} >>\n"
            f"stream\n{stream_text}endstream"
        )

    objects[2] = (
        f"<< /Type /Pages /Kids [{' '.join(kids)}] "
        f"/Count {len(composer.pages)} >>"
    )

    # Pure ASCII PDF so the checked-in PDF can travel safely through the high-level
    # GitHub contents API. All non-ASCII learner text is escaped/transliterated.
    output = bytearray(b"%PDF-1.4\n%ASCII\n")
    offsets: dict[int, int] = {}
    for object_id in range(1, next_object):
        offsets[object_id] = len(output)
        output.extend(f"{object_id} 0 obj\n".encode("ascii"))
        output.extend(objects[object_id].encode("latin-1", "replace"))
        output.extend(b"\nendobj\n")

    xref = len(output)
    output.extend(
        f"xref\n0 {next_object}\n0000000000 65535 f \n".encode("ascii")
    )
    for object_id in range(1, next_object):
        output.extend(
            f"{offsets[object_id]:010d} 00000 n \n".encode("ascii")
        )
    output.extend(
        (
            f"trailer\n<< /Size {next_object} /Root 1 0 R >>\n"
            f"startxref\n{xref}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(output)


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
    return core_exec + ket_exec, {
        "core": 480,
        "ket_text": 336,
        "ket_media_pending": 336,
        "dictation_pending": 480,
    }


def materialize(output_dir: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    items, counts = _items()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    practice = _Composer(
        "Unit05 Executable Practice 816",
        "Printable text-only practice bank from the final FAR7 canonical authorities.",
    )
    practice.cover()
    practice.new_page(cover=False)
    last_set = ""
    for number, item in enumerate(items, start=1):
        if item.get("practice_set_id") != last_set:
            last_set = str(item.get("practice_set_id") or "")
            practice.ensure(52)
            practice.text(
                f"{_norm(item.get('stage'))} - {_norm(last_set)}",
                size=13,
                bold=True,
                leading=16,
            )
            practice.rule()
        practice.practice(item, number)

    answers = _Composer(
        "Unit05 Answer Key 816",
        "Answer keys, accepted responses, and model/rubric guidance "
        "for the executable text-only practice bank.",
    )
    answers.cover()
    answers.new_page(cover=False)
    last_set = ""
    for number, item in enumerate(items, start=1):
        if item.get("practice_set_id") != last_set:
            last_set = str(item.get("practice_set_id") or "")
            answers.ensure(48)
            answers.text(
                f"{_norm(item.get('stage'))} - {_norm(last_set)}",
                size=12,
                bold=True,
                leading=15,
            )
            answers.rule()
        answers.answer(item, number)

    practice_path = output_dir / "unit05_executable_practice_816.pdf"
    answer_path = output_dir / "unit05_answer_key_816.pdf"
    practice_path.write_bytes(_pdf(practice))
    answer_path.write_bytes(_pdf(answers))

    for path in (practice_path, answer_path):
        raw = path.read_bytes()
        if (
            not raw.startswith(b"%PDF-1.4")
            or not raw.rstrip().endswith(b"%%EOF")
            or len(raw) < 100_000
        ):
            raise Unit05FinalPdfError(f"PDF_PREFLIGHT_FAIL:{path}")

    return {
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "executable_count": 816,
        "asset_pending_count": 816,
        **counts,
        "practice_pdf": str(practice_path),
        "answer_pdf": str(answer_path),
        "practice_pages": len(practice.pages),
        "answer_pages": len(answers.pages),
        "audio_generated": False,
        "visual_generated": False,
        "unit05_closeout_ready": True,
    }


def main() -> int:
    report = materialize()
    for key, value in report.items():
        print(f"{key.upper()}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
