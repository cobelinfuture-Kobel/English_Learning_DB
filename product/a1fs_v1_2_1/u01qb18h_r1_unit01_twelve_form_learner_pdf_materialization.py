#!/usr/bin/env python3
"""Materialize Unit01 Forms01..12 as learner-safe HTML and Chromium PDFs.

R1 consumes the already-accepted U01QB18F-R4 private replay.  That replay is the
current-main learner-safe projection of the exact active 474-item runtime across
all 12 Forms.  This module adds only a shared printable consumer: it validates
that replay through the existing U01QB18G closeout gates, renders the existing
``student_form`` payloads, and delegates PDF creation to the already-approved
Chromium print helper.

It does not select questions, author learner content, mutate SQLite, create a
second QuestionBank/runtime/planner/scoring authority, modify scenes, touch
Unit02-24, enable audio/Speaking scoring, or unlock A2.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from product.a1fs_v1_2_1 import (
    u01qb18a_form01_fresh_learner_materialization_export as u18a,
)
from product.a1fs_v1_2_1 import (
    u01qb18f_r4_full_semantic_language_pedagogical_replay as r4,
)
from product.a1fs_v1_2_1 import (
    u01qb18g_unit01_twelve_form_learner_facing_pedagogical_review_and_closeout as u18g,
)
from ulga.builders import (
    build_a1fs_ops_v1_unit01_student_package_chromium_main_product_entry_acceptance
    as chromium_acceptance,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Read-only printable consumer over the already-accepted U01QB18F-R4 learner-safe "
    "Forms01-12 replay. It renders only whitelisted student_form fields and delegates "
    "PDF creation to the existing Chromium helper; it creates no learner content, "
    "QuestionBank item, scene, selector, planner, runtime, database, scoring authority, "
    "Unit02-24 content, audio/Speaking score, or A2 content."
)

PROGRAM_ID = "A1FS-V1"
TASK_ID = (
    "A1FS-V1-U01QB18H-R1_"
    "Unit01Form01ToForm12LearnerPdfMaterializationFullFix"
)
PASS_STATUS = (
    "PASS_A1FS_V1_U01QB18H_R1_"
    "UNIT01_FORM01_12_LEARNER_PDF_MATERIALIZATION"
)
FAIL_STATUS = (
    "FAIL_A1FS_V1_U01QB18H_R1_"
    "UNIT01_FORM01_12_LEARNER_PDF_MATERIALIZATION"
)
NEXT_SHORT_STEP = (
    "A1FS-V1-U01QB18H-R2_"
    "Unit01Form01ToForm12PdfHumanVisualPedagogicalAcceptance"
)

FORM_COUNT = 12
EXPECTED_ACTIVITY_COUNT = 20
EXPECTED_SCENE_COUNT = 4
EXPECTED_SKILL_COUNTS = {"READING": 8, "WRITING": 8, "SPEAKING": 4}
DEFAULT_R4_REPORT = Path(
    ".local/a1fs_v1/review/unit01_forms01_12_full_semantic_language_replay.json"
)
DEFAULT_OUTPUT_ROOT = Path(
    ".local/a1fs_v1/review/unit01_forms01_12_pdf_materialization"
)
MANIFEST_NAME = "unit01_form01_12_pdf_materialization_manifest.private.json"

_FORBIDDEN_HTML_MARKERS = (
    "correct_answer",
    "correct_answers",
    "answer_key",
    "expected_answer",
    "expected_response",
    "scoring_contract",
    "scoring_model",
    "private_item_json",
    "scene_ref_id",
    "learner_id",
    "item_id",
    "task_id",
    "artifact_sha256",
)
_ALLOWED_RESPONSE_MODES = frozenset(
    {"select_one", "ordered_tokens", "short_text", "practice_only"}
)


class TwelveFormPdfMaterializationError(ValueError):
    """Fail-closed printable materialization error."""


def _load_json(path: Path) -> dict[str, Any]:
    path = Path(path).resolve(strict=True)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TwelveFormPdfMaterializationError(
            f"R4_REPORT_UNREADABLE:{path}:{exc}"
        ) from exc
    if not isinstance(value, dict):
        raise TwelveFormPdfMaterializationError("R4_REPORT_OBJECT_REQUIRED")
    return value


def _file_identity(path: Path) -> dict[str, Any]:
    raw = Path(path).read_bytes()
    return {
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _atomic_text(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    _atomic_text(
        path,
        json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n",
    )
    try:
        Path(path).chmod(0o600)
    except OSError:
        pass


def _humanize(value: Any) -> str:
    text = str(value or "").strip().replace("_", " ")
    text = re.sub(r"\s+", " ", text)
    return text.title() if text else "Everyday scene"


def _safe_text(value: Any) -> str:
    return html.escape(str(value or "").strip(), quote=True)


def _validate_student_form(student: Mapping[str, Any], ordinal: int) -> None:
    if str(student.get("unit_id") or "") != "UNIT01":
        raise TwelveFormPdfMaterializationError(f"UNIT_ID_INVALID:F{ordinal:02d}")
    if int(student.get("form_ordinal", -1)) != ordinal:
        raise TwelveFormPdfMaterializationError(
            f"FORM_ORDINAL_INVALID:F{ordinal:02d}:{student.get('form_ordinal')}"
        )
    if int(student.get("scene_count", -1)) != EXPECTED_SCENE_COUNT:
        raise TwelveFormPdfMaterializationError(f"SCENE_COUNT_INVALID:F{ordinal:02d}")
    if int(student.get("learner_visible_activity_count", -1)) != EXPECTED_ACTIVITY_COUNT:
        raise TwelveFormPdfMaterializationError(
            f"ACTIVITY_COUNT_INVALID:F{ordinal:02d}"
        )
    if dict(student.get("skill_counts") or {}) != EXPECTED_SKILL_COUNTS:
        raise TwelveFormPdfMaterializationError(
            f"SKILL_COUNTS_INVALID:F{ordinal:02d}"
        )
    scenes = list(student.get("scenes") or [])
    activities = list(student.get("activities") or [])
    if len(scenes) != EXPECTED_SCENE_COUNT:
        raise TwelveFormPdfMaterializationError(
            f"SCENE_RECORD_COUNT_INVALID:F{ordinal:02d}:{len(scenes)}"
        )
    if len(activities) != EXPECTED_ACTIVITY_COUNT:
        raise TwelveFormPdfMaterializationError(
            f"ACTIVITY_RECORD_COUNT_INVALID:F{ordinal:02d}:{len(activities)}"
        )
    modes: list[str] = []
    for index, activity in enumerate(activities, start=1):
        mode = str(activity.get("response_mode") or "")
        if mode not in _ALLOWED_RESPONSE_MODES:
            raise TwelveFormPdfMaterializationError(
                f"RESPONSE_MODE_INVALID:F{ordinal:02d}:Q{index:02d}:{mode}"
            )
        modes.append(mode)
        if str(activity.get("skill") or "") not in EXPECTED_SKILL_COUNTS:
            raise TwelveFormPdfMaterializationError(
                f"SKILL_INVALID:F{ordinal:02d}:Q{index:02d}"
            )
    # Reuse the already-approved no-answer/private-key recursive guard.
    u18a._assert_no_answer_leak(student)


def _response_html(activity: Mapping[str, Any]) -> str:
    mode = str(activity.get("response_mode") or "")
    options = [str(value) for value in activity.get("options") or []]
    if mode == "select_one":
        if not options:
            raise TwelveFormPdfMaterializationError("SELECT_ONE_OPTIONS_REQUIRED")
        rows = []
        for index, option in enumerate(options):
            label = chr(ord("A") + index)
            rows.append(
                '<div class="choice"><span class="choice-mark"></span>'
                f'<span class="choice-label">{label}.</span>'
                f'<span>{_safe_text(option)}</span></div>'
            )
        return '<div class="choices">' + "".join(rows) + "</div>"
    if mode == "ordered_tokens":
        token_html = "".join(
            f'<span class="token">{_safe_text(token)}</span>' for token in options
        )
        return (
            f'<div class="tokens">{token_html}</div>'
            '<div class="write-line"></div><div class="write-line"></div>'
        )
    if mode == "short_text":
        return (
            '<div class="write-line"></div><div class="write-line"></div>'
            '<div class="write-line"></div>'
        )
    if mode == "practice_only":
        return (
            '<div class="speaking-box">'
            '<span class="speaking-icon">Speaking practice</span>'
            '<div class="speaking-space"></div></div>'
        )
    raise TwelveFormPdfMaterializationError(f"RESPONSE_MODE_INVALID:{mode}")


def _activity_html(activity: Mapping[str, Any], fallback_number: int) -> str:
    question_number = str(activity.get("question_number") or f"Q{fallback_number:02d}")
    skill = _humanize(activity.get("skill"))
    stimulus = str(activity.get("stimulus") or "").strip()
    prompt = str(activity.get("prompt") or "").strip()
    if not prompt:
        raise TwelveFormPdfMaterializationError(
            f"LEARNER_PROMPT_MISSING:{question_number}"
        )
    stimulus_html = (
        f'<div class="stimulus">{_safe_text(stimulus)}</div>' if stimulus else ""
    )
    return (
        '<article class="activity">'
        '<div class="activity-heading">'
        f'<span class="question-number">{_safe_text(question_number)}</span>'
        f'<span class="skill-pill">{_safe_text(skill)}</span>'
        "</div>"
        f"{stimulus_html}"
        f'<div class="prompt">{_safe_text(prompt)}</div>'
        f"{_response_html(activity)}"
        "</article>"
    )


def render_form_html(student: Mapping[str, Any]) -> str:
    """Render only whitelisted learner-safe fields from one accepted student_form."""
    ordinal = int(student.get("form_ordinal", 0))
    _validate_student_form(student, ordinal)
    scenes = list(student.get("scenes") or [])
    activities = list(student.get("activities") or [])

    scene_order: list[str] = []
    scene_titles: dict[str, str] = {}
    for scene in scenes:
        ref = str(scene.get("scene_ref_id") or "")
        if not ref or ref in scene_titles:
            raise TwelveFormPdfMaterializationError(
                f"SCENE_IDENTITY_INVALID:F{ordinal:02d}"
            )
        scene_order.append(ref)
        scene_titles[ref] = _humanize(scene.get("setting"))

    grouped: dict[str, list[Mapping[str, Any]]] = {ref: [] for ref in scene_order}
    for activity in activities:
        ref = str(activity.get("scene_ref_id") or "")
        if ref not in grouped:
            raise TwelveFormPdfMaterializationError(
                f"ACTIVITY_SCENE_NOT_IN_FORM:F{ordinal:02d}"
            )
        grouped[ref].append(activity)
    if any(len(rows) != 5 for rows in grouped.values()):
        raise TwelveFormPdfMaterializationError(
            f"SCENE_ACTIVITY_DENOMINATOR_INVALID:F{ordinal:02d}"
        )

    sections: list[str] = []
    number = 0
    for scene_number, ref in enumerate(scene_order, start=1):
        cards: list[str] = []
        for activity in grouped[ref]:
            number += 1
            cards.append(_activity_html(activity, number))
        sections.append(
            '<section class="scene-section">'
            '<div class="scene-heading">'
            f'<span class="scene-kicker">Scene {scene_number}</span>'
            f'<h2>{_safe_text(scene_titles[ref])}</h2>'
            "</div>"
            + "".join(cards)
            + "</section>"
        )

    css = """
@page{size:A4;margin:12mm 11mm 14mm}
*{box-sizing:border-box}
html,body{margin:0;padding:0;font-family:Arial,"Noto Sans",sans-serif;color:#17202a;background:#fff}
body{font-size:11.2pt;line-height:1.42}
.page-header{border-bottom:2px solid #26394d;padding:0 0 8px;margin:0 0 12px}
.page-header .eyebrow{font-size:9pt;letter-spacing:.08em;text-transform:uppercase;color:#566573;font-weight:700}
.page-header h1{font-size:22pt;margin:2px 0 2px;line-height:1.15}
.page-header p{margin:0;color:#566573;font-size:10pt}
.scene-section{break-before:page;margin:0}
.scene-section:first-of-type{break-before:auto}
.scene-heading{border-left:4px solid #34495e;padding:4px 8px;margin:0 0 10px;background:#f5f7f8}
.scene-kicker{font-size:8.7pt;text-transform:uppercase;letter-spacing:.08em;color:#5d6d7e;font-weight:700}
.scene-heading h2{font-size:15.5pt;margin:1px 0 0}
.activity{break-inside:avoid;border:1px solid #d5d8dc;border-radius:7px;padding:8px 9px;margin:0 0 8px;min-height:33mm}
.activity-heading{display:flex;align-items:center;gap:8px;margin-bottom:5px}
.question-number{font-weight:800;font-size:11pt}
.skill-pill{font-size:8.5pt;font-weight:700;border:1px solid #aeb6bf;border-radius:999px;padding:1px 7px;color:#455a64}
.stimulus{font-size:12.4pt;font-weight:700;padding:6px 8px;margin:4px 0 6px;background:#f8f9f9;border-radius:5px}
.prompt{font-size:11.2pt;margin:4px 0 7px}
.choices{display:grid;grid-template-columns:1fr 1fr;gap:5px 12px}
.choice{display:flex;align-items:flex-start;gap:5px;min-height:20px}
.choice-mark{width:13px;height:13px;border:1.5px solid #566573;border-radius:50%;display:inline-block;flex:0 0 13px;margin-top:2px}
.choice-label{font-weight:700;min-width:18px}
.tokens{display:flex;flex-wrap:wrap;gap:5px;margin:4px 0 8px}
.token{border:1px solid #aeb6bf;border-radius:4px;padding:2px 6px;background:#fbfcfc}
.write-line{height:18px;border-bottom:1px solid #99a3a4;margin:3px 0}
.speaking-box{border:1px dashed #85929e;border-radius:5px;padding:7px;margin-top:5px}
.speaking-icon{font-size:9pt;font-weight:700;color:#566573}
.speaking-space{height:23px}
.footer-note{margin-top:12px;padding-top:7px;border-top:1px solid #d5d8dc;color:#707b7c;font-size:8.5pt}
"""
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Unit 01 Form {ordinal:02d}</title><style>{css}</style></head><body>
<header class="page-header"><div class="eyebrow">A1FS · Unit 01</div>
<h1>Form {ordinal:02d}</h1>
<p>Reading · Writing · Speaking practice</p></header>
{''.join(sections)}
<div class="footer-note">Learner practice copy · answers and scoring information are not included.</div>
</body></html>"""
    lowered = document.casefold()
    for marker in _FORBIDDEN_HTML_MARKERS:
        if marker.casefold() in lowered:
            raise TwelveFormPdfMaterializationError(
                f"FORBIDDEN_LEARNER_HTML_MARKER:{marker}:F{ordinal:02d}"
            )
    return document


def _validate_r4_report(report: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    # Reuse the exact closeout acceptance instead of inventing a second Form contract.
    u18g._validate_r4(report)
    forms = list(report.get("forms") or [])
    if len(forms) != FORM_COUNT:
        raise TwelveFormPdfMaterializationError(
            f"FORM_COUNT_INVALID:{len(forms)}:{FORM_COUNT}"
        )
    ordinals: list[int] = []
    for form in forms:
        review = u18g._review_form(form)
        ordinal = int(review["form_ordinal"])
        ordinals.append(ordinal)
        student = form.get("student_form") or {}
        if not isinstance(student, Mapping):
            raise TwelveFormPdfMaterializationError(
                f"STUDENT_FORM_OBJECT_REQUIRED:F{ordinal:02d}"
            )
        _validate_student_form(student, ordinal)
    if ordinals != list(range(1, FORM_COUNT + 1)):
        raise TwelveFormPdfMaterializationError(
            f"FORM_SEQUENCE_INVALID:{ordinals}"
        )
    u18a._assert_no_answer_leak(report)
    return forms


def materialize_twelve_form_pdfs(
    *,
    r4_report_path: Path,
    output_root: Path,
    chromium_path: Path | None = None,
    browser_runner: Callable[..., Mapping[str, Any]] | None = None,
    pdf_page_counter: Callable[[Path], int] | None = None,
) -> dict[str, Any]:
    report_path = Path(r4_report_path).resolve(strict=True)
    output_root = Path(output_root).resolve()
    html_root = output_root / "html"
    pdf_root = output_root / "pdf"
    html_root.mkdir(parents=True, exist_ok=True)
    pdf_root.mkdir(parents=True, exist_ok=True)

    report = _load_json(report_path)
    forms = _validate_r4_report(report)
    chromium = (
        Path(chromium_path).resolve(strict=True)
        if chromium_path is not None
        else chromium_acceptance.discover_chromium()
    )
    run_browser = browser_runner or chromium_acceptance._run_browser
    count_pages = pdf_page_counter or chromium_acceptance._pdf_page_count

    artifacts: list[dict[str, Any]] = []
    for ordinal, form in enumerate(forms, start=1):
        student = form["student_form"]
        html_path = html_root / f"Form{ordinal:02d}.html"
        pdf_path = pdf_root / f"Form{ordinal:02d}.pdf"
        rendered_html = render_form_html(student)
        _atomic_text(html_path, rendered_html)
        render_result = dict(
            run_browser(
                chromium,
                source_html=html_path,
                output_path=pdf_path,
                mode="PDF",
            )
        )
        if not pdf_path.is_file():
            raise TwelveFormPdfMaterializationError(
                f"PDF_OUTPUT_MISSING:F{ordinal:02d}"
            )
        pdf_identity = _file_identity(pdf_path)
        if pdf_identity["bytes"] < 1024:
            raise TwelveFormPdfMaterializationError(
                f"PDF_OUTPUT_TOO_SMALL:F{ordinal:02d}:{pdf_identity['bytes']}"
            )
        page_count = int(count_pages(pdf_path))
        if page_count < 1:
            raise TwelveFormPdfMaterializationError(
                f"PDF_PAGE_COUNT_INVALID:F{ordinal:02d}:{page_count}"
            )
        artifacts.append(
            {
                "form_id": f"U01-FORM-{ordinal:02d}",
                "form_ordinal": ordinal,
                "html_relative_path": f"html/Form{ordinal:02d}.html",
                "pdf_relative_path": f"pdf/Form{ordinal:02d}.pdf",
                "page_count": page_count,
                "pdf_bytes": pdf_identity["bytes"],
                "pdf_sha256": pdf_identity["sha256"],
                "scene_count": EXPECTED_SCENE_COUNT,
                "learner_visible_activity_count": EXPECTED_ACTIVITY_COUNT,
                "skill_counts": dict(EXPECTED_SKILL_COUNTS),
                "machine_preflight": "PASS",
                "human_visual_review": "PENDING",
                "browser_render": {
                    key: value
                    for key, value in render_result.items()
                    if key not in {"source_path", "output_path"}
                },
            }
        )

    if len(artifacts) != FORM_COUNT:
        raise TwelveFormPdfMaterializationError(
            f"MATERIALIZED_PDF_COUNT_INVALID:{len(artifacts)}:{FORM_COUNT}"
        )
    hashes = [row["pdf_sha256"] for row in artifacts]
    if len(set(hashes)) != FORM_COUNT:
        raise TwelveFormPdfMaterializationError(
            f"PDF_SHA256_NOT_DISTINCT:{len(set(hashes))}:{FORM_COUNT}"
        )

    manifest = {
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS,
        "source_r4_task_id": str(report.get("task_id") or ""),
        "source_r4_validation_status": str(report.get("validation_status") or ""),
        "source_r4_report_sha256": _file_identity(report_path)["sha256"],
        "form_count": FORM_COUNT,
        "materialized_html_count": FORM_COUNT,
        "materialized_pdf_count": FORM_COUNT,
        "machine_preflight_pass_count": FORM_COUNT,
        "human_visual_review_pass_count": 0,
        "human_visual_review_pending_count": FORM_COUNT,
        "unit01_final_pdf_acceptance": "PENDING_HUMAN_VISUAL_REVIEW",
        "unit01_product_d0_closeout": False,
        "questionbank_modified": False,
        "new_question_items_authored": 0,
        "scene_authority_modified": False,
        "production_database_modified": False,
        "unit02_to_unit24_modified": False,
        "a2_unlocked": False,
        "artifacts": artifacts,
        "next_short_step": NEXT_SHORT_STEP,
    }
    _atomic_json(output_root / MANIFEST_NAME, manifest)
    return manifest


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r4-report", type=Path, default=DEFAULT_R4_REPORT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--chromium-path", type=Path)
    args = parser.parse_args(argv)
    try:
        value = materialize_twelve_form_pdfs(
            r4_report_path=args.r4_report,
            output_root=args.output_root,
            chromium_path=args.chromium_path,
        )
    except (
        TwelveFormPdfMaterializationError,
        u18g.LearnerFacingPedagogicalCloseoutError,
        u18a.Form01MaterializationError,
        chromium_acceptance.StudentEntryAcceptanceError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"STATUS={FAIL_STATUS}")
        print(f"ERROR={exc}")
        return 1

    print(f"STATUS={value['validation_status']}")
    print(f"FORMS={value['form_count']}")
    print(f"HTML_FILES={value['materialized_html_count']}")
    print(f"PDF_FILES={value['materialized_pdf_count']}")
    print(f"MACHINE_PREFLIGHT_PASS={value['machine_preflight_pass_count']}")
    print(f"HUMAN_VISUAL_REVIEW_PENDING={value['human_visual_review_pending_count']}")
    for row in value["artifacts"]:
        print(
            f"FORM{int(row['form_ordinal']):02d}_PDF="
            f"{Path(args.output_root).resolve() / row['pdf_relative_path']}"
        )
        print(f"FORM{int(row['form_ordinal']):02d}_PAGES={row['page_count']}")
        print(f"FORM{int(row['form_ordinal']):02d}_SHA256={row['pdf_sha256']}")
    print(f"OUTPUT_ROOT={Path(args.output_root).resolve()}")
    print(f"NEXT_SHORT_STEP={value['next_short_step']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
