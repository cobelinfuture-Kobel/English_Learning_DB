#!/usr/bin/env python3
"""Materialize Unit01 Forms01..12 as learner-safe HTML and Chromium PDFs.

R1 consumes the already-accepted U01QB18F-R4 private replay. That replay is the
current-main learner-safe projection of the exact active 474-item runtime across
all 12 Forms. This module adds only a shared printable consumer: it validates
that replay through the existing U01QB18G closeout gates, renders the existing
``student_form`` payloads, and creates review-bound Chromium PDFs.

R1A strengthens only the presentation/acceptance boundary proven defective by
an actual Form01 PDF: engineering scene metadata is not shown to the learner,
WORD_ORDER token banks remain visible, obvious target-phrase answer
demonstrations are suppressed at print projection time, pagination no longer
forces one page per scene, Chromium is invoked with both modern and legacy
header/footer-suppression flags, and the private manifest can record
SHA-bound human visual/pedagogical review results.

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
import subprocess
import tempfile
from datetime import datetime, timezone
from copy import deepcopy
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
    "Read-only printable/review consumer over the already-accepted U01QB18F-R4 "
    "learner-safe Forms01-12 replay. It suppresses presentation-only engineering "
    "metadata, preserves existing learner response affordances, invokes the same "
    "Chromium executable with header/footer suppression compatibility flags, and "
    "records SHA-bound human review state in the existing private manifest. It "
    "creates no learner content, QuestionBank item, scene, selector, planner, "
    "runtime, database, scoring authority, Unit02-24 content, audio/Speaking score, "
    "or A2 content."
)

PROGRAM_ID = "A1FS-V1"
TASK_ID = (
    "A1FS-V1-U01QB18H-R1_"
    "Unit01Form01ToForm12LearnerPdfMaterializationFullFix"
)
R1A_TASK_ID = (
    "A1FS-V1-U01QB18H-R1A_"
    "Unit01Form01LearnerPdfPresentationAndManifestReviewFullFix"
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
MANIFEST_SCHEMA_VERSION = "a1fs.v1.u01qb18h.r1.pdf_materialization_manifest.v2"

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
_FORBIDDEN_PRESENTATION_PREFIXES = (
    "scene:",
    "scene words:",
    "relationship:",
    "action:",
    "event:",
    "task focus:",
)
_ALLOWED_RESPONSE_MODES = frozenset(
    {"select_one", "ordered_tokens", "short_text", "practice_only"}
)
_REVIEW_STATUSES = frozenset({"PENDING", "PASS", "FAIL"})
_REVIEW_FINAL_STATUSES = frozenset({"PASS", "FAIL"})
_REVIEW_DEFECT_RE = re.compile(r"^[A-Z0-9][A-Z0-9_:-]*$")


class TwelveFormPdfMaterializationError(ValueError):
    """Fail-closed printable materialization/review error."""


def _load_json(path: Path) -> dict[str, Any]:
    path = Path(path).resolve(strict=True)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TwelveFormPdfMaterializationError(
            f"JSON_UNREADABLE:{path}:{exc}"
        ) from exc
    if not isinstance(value, dict):
        raise TwelveFormPdfMaterializationError("JSON_OBJECT_REQUIRED")
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


def _humanize_inline(value: Any) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\b([A-Za-z]+(?:_[A-Za-z]+)+)\b",
                  lambda match: match.group(1).replace("_", " "), text)
    return re.sub(r"\s+", " ", text)


def _safe_text(value: Any) -> str:
    return html.escape(str(value or "").strip(), quote=True)


def _load_prior_manifest(path: Path) -> dict[str, Any] | None:
    """Read the prior private manifest for SHA-bound incremental reuse."""
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


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
    for index, activity in enumerate(activities, start=1):
        mode = str(activity.get("response_mode") or "")
        if mode not in _ALLOWED_RESPONSE_MODES:
            raise TwelveFormPdfMaterializationError(
                f"RESPONSE_MODE_INVALID:F{ordinal:02d}:Q{index:02d}:{mode}"
            )
        if str(activity.get("skill") or "") not in EXPECTED_SKILL_COUNTS:
            raise TwelveFormPdfMaterializationError(
                f"SKILL_INVALID:F{ordinal:02d}:Q{index:02d}"
            )
    u18a._assert_no_answer_leak(student)


def _is_named_segment(segment: str) -> bool:
    lowered = str(segment or "").strip().casefold()
    return any(
        lowered.startswith(prefix)
        for prefix in (
            *_FORBIDDEN_PRESENTATION_PREFIXES,
            "use:",
            "noun:",
            "word:",
            "words:",
            "example:",
            "your turn:",
            "target phrase:",
            "guide:",
            "learner:",
        )
    )


def _ordered_tokens(activity: Mapping[str, Any]) -> list[str]:
    explicit = activity.get("ordered_tokens")
    if isinstance(explicit, Sequence) and not isinstance(explicit, (str, bytes)):
        values = [_humanize_inline(value) for value in explicit if str(value).strip()]
        if len(values) >= 2:
            return values

    options = [_humanize_inline(value) for value in activity.get("options") or []]
    if len(options) >= 2:
        return options

    parts = [part.strip() for part in str(activity.get("stimulus") or "").split("|")]
    values: list[str] = []
    collecting = False
    for part in parts:
        lowered = part.casefold()
        if lowered.startswith("words:"):
            first = part.split(":", 1)[1].strip()
            if first:
                values.append(_humanize_inline(first))
            collecting = True
            continue
        if collecting:
            if _is_named_segment(part):
                break
            if part:
                values.append(_humanize_inline(part))
    if len(values) < 2:
        raise TwelveFormPdfMaterializationError(
            f"WORD_ORDER_TOKEN_BANK_UNAVAILABLE:{activity.get('question_number')}"
        )
    return values


def _target_phrase(stimulus: str) -> str:
    match = re.search(
        r"target\s+phrase\s*:\s*_{2,}\s*([^|.!?]+)",
        str(stimulus or ""),
        flags=re.I,
    )
    if not match:
        return ""
    return _humanize_inline(match.group(1)).strip()


def _contains_direct_article_phrase(text: str, target_phrase: str) -> bool:
    if not target_phrase:
        return False
    escaped = re.escape(target_phrase)
    return re.search(rf"\b(?:a|an|the)\s+{escaped}\b", text, flags=re.I) is not None


def _clean_stimulus(activity: Mapping[str, Any]) -> str:
    raw = str(activity.get("stimulus") or "").strip()
    if not raw:
        return ""

    target = _target_phrase(raw)
    response_mode = str(activity.get("response_mode") or "")
    parts = [part.strip() for part in raw.split("|") if part.strip()]
    cleaned: list[str] = []
    collecting_words = False

    for part in parts:
        lowered = part.casefold()
        if any(lowered.startswith(prefix) for prefix in _FORBIDDEN_PRESENTATION_PREFIXES):
            collecting_words = False
            continue

        if collecting_words and not _is_named_segment(part):
            continue
        collecting_words = False

        if lowered.startswith("words:"):
            collecting_words = response_mode == "ordered_tokens"
            if collecting_words:
                continue

        if lowered.startswith("use:"):
            value = _humanize_inline(part.split(":", 1)[1])
            if value.replace(" ", "").casefold() in {"a/an", "aoran"}:
                cleaned.append("Use a or an.")
            else:
                cleaned.append(f"Use {value}.")
            continue

        if lowered.startswith("noun:"):
            value = _humanize_inline(part.split(":", 1)[1])
            cleaned.append(f"Word: {value}")
            continue

        value = _humanize_inline(part)
        value = re.sub(r"\bGUIDE\s*:", "Guide:", value, flags=re.I)
        value = re.sub(r"\bLEARNER\s*:", "You:", value, flags=re.I)

        if target:
            marker = re.search(r"target\s+phrase\s*:", value, flags=re.I)
            if marker:
                before = value[: marker.start()].strip()
                after = value[marker.start() :].strip()
                if _contains_direct_article_phrase(before, target):
                    value = after
            elif _contains_direct_article_phrase(value, target):
                continue
        cleaned.append(value)

    result = " · ".join(part for part in cleaned if part).strip()
    if any(
        result.casefold().startswith(prefix)
        or f" · {prefix}" in result.casefold()
        for prefix in _FORBIDDEN_PRESENTATION_PREFIXES
    ):
        raise TwelveFormPdfMaterializationError(
            f"ENGINEERING_PRESENTATION_MARKER_SURVIVED:{activity.get('question_number')}"
        )
    if re.search(r"\b[A-Za-z]+(?:_[A-Za-z]+)+\b", result):
        raise TwelveFormPdfMaterializationError(
            f"SNAKE_CASE_LEARNER_TEXT_SURVIVED:{activity.get('question_number')}"
        )
    return result


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
                f'<span>{_safe_text(_humanize_inline(option))}</span></div>'
            )
        return '<div class="choices">' + "".join(rows) + "</div>"
    if mode == "ordered_tokens":
        tokens = _ordered_tokens(activity)
        token_html = "".join(
            f'<span class="token">{_safe_text(token)}</span>' for token in tokens
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
    stimulus = _clean_stimulus(activity)
    prompt = _humanize_inline(activity.get("prompt"))
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
    """Render learner-safe presentation fields from one accepted student_form."""
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
            '<div class="scene-lead">'
            '<div class="scene-heading">'
            f'<span class="scene-kicker">Scene {scene_number}</span>'
            f'<h2>{_safe_text(scene_titles[ref])}</h2>'
            "</div>"
            + (cards[0] if cards else "")
            + "</div>"
            + "".join(cards[1:])
            + "</section>"
        )

    css = """
@page{size:A4;margin:10mm 10mm 12mm}
*{box-sizing:border-box}
html,body{margin:0;padding:0;font-family:Arial,"Noto Sans",sans-serif;color:#17202a;background:#fff}
body{font-size:10.5pt;line-height:1.3}
.page-header{border-bottom:2px solid #26394d;padding:0 0 5px;margin:0 0 7px}
.page-header .eyebrow{font-size:8.5pt;letter-spacing:.08em;text-transform:uppercase;color:#566573;font-weight:700}
.page-header h1{font-size:20pt;margin:2px 0;line-height:1.12}
.page-header p{margin:0;color:#566573;font-size:9.5pt}
.scene-section{margin:0 0 7px;break-before:auto;break-inside:auto}
.scene-lead{break-inside:avoid;page-break-inside:avoid}
.scene-heading{break-inside:avoid;break-after:avoid;page-break-inside:avoid;border-left:4px solid #34495e;padding:3px 7px;margin:0 0 5px;background:#f5f7f8}
.scene-kicker{font-size:8.2pt;text-transform:uppercase;letter-spacing:.08em;color:#5d6d7e;font-weight:700}
.scene-heading h2{font-size:14pt;margin:1px 0 0}
.activity{break-inside:avoid;border:1px solid #d5d8dc;border-radius:6px;padding:5px 7px;margin:0 0 4px}
.activity-heading{display:flex;align-items:center;gap:7px;margin-bottom:3px}
.question-number{font-weight:800;font-size:10.5pt}
.skill-pill{font-size:8pt;font-weight:700;border:1px solid #aeb6bf;border-radius:999px;padding:1px 6px;color:#455a64}
.stimulus{font-size:11.3pt;font-weight:700;padding:4px 6px;margin:2px 0 4px;background:#f8f9f9;border-radius:4px}
.prompt{font-size:10.5pt;margin:2px 0 4px}
.choices{display:grid;grid-template-columns:1fr 1fr;gap:4px 10px}
.choice{display:flex;align-items:flex-start;gap:5px;min-height:18px}
.choice-mark{width:12px;height:12px;border:1.4px solid #566573;border-radius:50%;display:inline-block;flex:0 0 12px;margin-top:2px}
.choice-label{font-weight:700;min-width:17px}
.tokens{display:flex;flex-wrap:wrap;gap:5px;margin:2px 0 4px}
.token{border:1px solid #aeb6bf;border-radius:4px;padding:2px 6px;background:#fbfcfc}
.write-line{height:16px;border-bottom:1px solid #99a3a4;margin:2px 0}
.speaking-box{border:1px dashed #85929e;border-radius:5px;padding:5px;margin-top:3px}
.speaking-icon{font-size:8.5pt;font-weight:700;color:#566573}
.speaking-space{height:12px}
.footer-note{break-before:avoid;page-break-before:avoid;margin-top:5px;padding-top:5px;border-top:1px solid #d5d8dc;color:#707b7c;font-size:8pt}
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
    for marker in _FORBIDDEN_PRESENTATION_PREFIXES:
        if marker in lowered:
            raise TwelveFormPdfMaterializationError(
                f"ENGINEERING_PRESENTATION_MARKER_RENDERED:{marker}:F{ordinal:02d}"
            )
    return document


def _validate_r4_report(report: Mapping[str, Any]) -> list[Mapping[str, Any]]:
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


def _run_pdf_browser_headerless(
    chromium: Path,
    *,
    source_html: Path,
    output_path: Path,
    mode: str,
) -> dict[str, Any]:
    """Use the existing Chromium executable with modern + legacy PDF header guards."""
    if mode != "PDF":
        raise chromium_acceptance.StudentEntryAcceptanceError(
            f"browser_mode_invalid:{mode}"
        )
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="a1fs-u01-form-pdf-") as profile:
        command = [
            str(chromium),
            "--headless=new",
            "--no-sandbox",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--allow-file-access-from-files",
            "--run-all-compositor-stages-before-draw",
            f"--user-data-dir={profile}",
            "--no-pdf-header-footer",
            "--print-to-pdf-no-header",
            f"--print-to-pdf={output_path}",
            Path(source_html).resolve().as_uri(),
        ]
        result = subprocess.run(
            command,
            text=True,
            capture_output=True,
            check=False,
            timeout=180,
        )
    if result.returncode != 0 or not output_path.is_file():
        raise chromium_acceptance.StudentEntryAcceptanceError(
            f"chromium_render_failed:PDF:{result.returncode}:"
            f"{result.stderr[-1000:]}"
        )
    identity = chromium_acceptance.file_identity(output_path)
    if identity["bytes"] < 1024:
        raise chromium_acceptance.StudentEntryAcceptanceError(
            "chromium_output_too_small:PDF"
        )
    return {
        "mode": "PDF",
        "source_name": Path(source_html).name,
        "output_name": output_path.name,
        **identity,
        "pdf_header_footer_suppression": "MODERN_AND_LEGACY_FLAGS",
    }


def _review_counts(artifacts: Sequence[Mapping[str, Any]], field: str) -> dict[str, int]:
    counts = {"PASS": 0, "FAIL": 0, "PENDING": 0}
    for row in artifacts:
        status = str(row.get(field) or "PENDING").upper()
        if status not in _REVIEW_STATUSES:
            raise TwelveFormPdfMaterializationError(
                f"HUMAN_REVIEW_STATUS_INVALID:{field}:{status}"
            )
        counts[status] += 1
    return counts


def _reconcile_human_review_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    artifacts = list(manifest.get("artifacts") or [])
    if len(artifacts) != FORM_COUNT:
        raise TwelveFormPdfMaterializationError(
            f"MANIFEST_ARTIFACT_COUNT_INVALID:{len(artifacts)}:{FORM_COUNT}"
        )
    visual = _review_counts(artifacts, "human_visual_review")
    pedagogical = _review_counts(artifacts, "human_pedagogical_review")
    manifest.update(
        {
            "human_visual_review_pass_count": visual["PASS"],
            "human_visual_review_fail_count": visual["FAIL"],
            "human_visual_review_pending_count": visual["PENDING"],
            "human_pedagogical_review_pass_count": pedagogical["PASS"],
            "human_pedagogical_review_fail_count": pedagogical["FAIL"],
            "human_pedagogical_review_pending_count": pedagogical["PENDING"],
        }
    )
    if visual["FAIL"] or pedagogical["FAIL"]:
        form_status = "FAIL_HUMAN_REVIEW"
        final_status = "BLOCKED_FORM_PDF_HUMAN_REVIEW_FAILURE"
    elif visual["PASS"] == FORM_COUNT and pedagogical["PASS"] == FORM_COUNT:
        form_status = "PASS_HUMAN_VISUAL_PEDAGOGICAL_REVIEW"
        final_status = "PENDING_PRELEARNING_FINAL_RECONCILIATION"
    else:
        form_status = "PENDING_HUMAN_VISUAL_PEDAGOGICAL_REVIEW"
        final_status = "PENDING_HUMAN_VISUAL_PEDAGOGICAL_REVIEW"
    manifest["unit01_form01_12_pdf_acceptance"] = form_status
    manifest["unit01_final_pdf_acceptance"] = final_status
    manifest["unit01_product_d0_closeout"] = False
    return manifest


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
    run_browser = browser_runner or _run_pdf_browser_headerless
    count_pages = pdf_page_counter or chromium_acceptance._pdf_page_count

    prior_manifest = _load_prior_manifest(output_root / MANIFEST_NAME)
    prior_by_ordinal = {
        int(row.get("form_ordinal", -1)): row
        for row in (prior_manifest or {}).get("artifacts", [])
        if isinstance(row, Mapping)
    }
    artifacts: list[dict[str, Any]] = []
    for ordinal, form in enumerate(forms, start=1):
        student = form["student_form"]
        html_path = html_root / f"Form{ordinal:02d}.html"
        pdf_path = pdf_root / f"Form{ordinal:02d}.pdf"
        rendered_html = render_form_html(student)
        _atomic_text(html_path, rendered_html)
        rendered_html_sha256 = hashlib.sha256(rendered_html.encode("utf-8")).hexdigest()
        prior = prior_by_ordinal.get(ordinal) or {}
        prior_pdf_sha = str(prior.get("pdf_sha256") or "").lower()
        can_reuse = (
            str(prior.get("rendered_html_sha256") or "").lower() == rendered_html_sha256
            and pdf_path.is_file()
            and bool(prior_pdf_sha)
            and _file_identity(pdf_path)["sha256"].lower() == prior_pdf_sha
        )
        if can_reuse:
            render_result = dict(prior.get("browser_render") or {})
            render_result.update(
                {
                    "mode": "PDF",
                    "source_name": html_path.name,
                    "output_name": pdf_path.name,
                    "sha256": prior_pdf_sha,
                    "bytes": _file_identity(pdf_path)["bytes"],
                }
            )
            render_action = "REUSED"
        else:
            render_result = dict(
                run_browser(
                    chromium,
                    source_html=html_path,
                    output_path=pdf_path,
                    mode="PDF",
                )
            )
            render_action = "RERENDERED"
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
        artifact = {
                "form_id": f"U01-FORM-{ordinal:02d}",
                "form_ordinal": ordinal,
                "html_relative_path": f"html/Form{ordinal:02d}.html",
                "pdf_relative_path": f"pdf/Form{ordinal:02d}.pdf",
                "page_count": page_count,
                "pdf_bytes": pdf_identity["bytes"],
                "pdf_sha256": pdf_identity["sha256"],
                "rendered_html_sha256": rendered_html_sha256,
                "render_action": render_action,
                "scene_count": EXPECTED_SCENE_COUNT,
                "learner_visible_activity_count": EXPECTED_ACTIVITY_COUNT,
                "skill_counts": dict(EXPECTED_SKILL_COUNTS),
                "machine_preflight": "PASS",
                "human_visual_review": "PENDING",
                "human_pedagogical_review": "PENDING",
                "human_review_defect_codes": [],
                "human_review_evidence_pdf_sha256": None,
                "human_reviewed_at": None,
                "browser_render": {
                    key: value
                    for key, value in render_result.items()
                    if key not in {"source_path", "output_path"}
                },
            }
        if can_reuse:
            for key in (
                "human_visual_review",
                "human_pedagogical_review",
                "human_review_defect_codes",
                "human_review_evidence_pdf_sha256",
                "human_reviewed_at",
            ):
                if key in prior:
                    artifact[key] = deepcopy(prior[key])
        artifacts.append(artifact)

    if len(artifacts) != FORM_COUNT:
        raise TwelveFormPdfMaterializationError(
            f"MATERIALIZED_PDF_COUNT_INVALID:{len(artifacts)}:{FORM_COUNT}"
        )
    hashes = [row["pdf_sha256"] for row in artifacts]
    if len(set(hashes)) != FORM_COUNT:
        raise TwelveFormPdfMaterializationError(
            f"PDF_SHA256_NOT_DISTINCT:{len(set(hashes))}:{FORM_COUNT}"
        )

    manifest: dict[str, Any] = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "latest_fullfix_task_id": R1A_TASK_ID,
        "validation_status": PASS_STATUS,
        "source_r4_task_id": str(report.get("task_id") or ""),
        "source_r4_validation_status": str(report.get("validation_status") or ""),
        "source_r4_report_sha256": _file_identity(report_path)["sha256"],
        "form_count": FORM_COUNT,
        "materialized_html_count": FORM_COUNT,
        "materialized_pdf_count": FORM_COUNT,
        "machine_preflight_pass_count": FORM_COUNT,
        "questionbank_modified": False,
        "new_question_items_authored": 0,
        "scene_authority_modified": False,
        "production_database_modified": False,
        "unit02_to_unit24_modified": False,
        "a2_unlocked": False,
        "artifacts": artifacts,
        "next_short_step": NEXT_SHORT_STEP,
    }
    _reconcile_human_review_manifest(manifest)
    _atomic_json(output_root / MANIFEST_NAME, manifest)
    return manifest


def record_human_review(
    *,
    manifest_path: Path,
    form_ordinal: int,
    expected_pdf_sha256: str,
    visual_review: str,
    pedagogical_review: str,
    defect_codes: Sequence[str] = (),
    reviewed_at: str | None = None,
) -> dict[str, Any]:
    """Record one SHA-bound human review in the existing private manifest."""
    manifest_path = Path(manifest_path).resolve(strict=True)
    manifest = _load_json(manifest_path)
    if str(manifest.get("task_id") or "") != TASK_ID:
        raise TwelveFormPdfMaterializationError("MANIFEST_TASK_ID_INVALID")
    if int(form_ordinal) < 1 or int(form_ordinal) > FORM_COUNT:
        raise TwelveFormPdfMaterializationError(
            f"REVIEW_FORM_ORDINAL_INVALID:{form_ordinal}"
        )

    visual = str(visual_review).upper()
    pedagogical = str(pedagogical_review).upper()
    if visual not in _REVIEW_FINAL_STATUSES:
        raise TwelveFormPdfMaterializationError(
            f"VISUAL_REVIEW_FINAL_STATUS_REQUIRED:{visual}"
        )
    if pedagogical not in _REVIEW_FINAL_STATUSES:
        raise TwelveFormPdfMaterializationError(
            f"PEDAGOGICAL_REVIEW_FINAL_STATUS_REQUIRED:{pedagogical}"
        )

    normalized_defects = sorted({str(code).strip().upper() for code in defect_codes if str(code).strip()})
    if any(not _REVIEW_DEFECT_RE.fullmatch(code) for code in normalized_defects):
        raise TwelveFormPdfMaterializationError("HUMAN_REVIEW_DEFECT_CODE_INVALID")
    if (visual == "FAIL" or pedagogical == "FAIL") and not normalized_defects:
        raise TwelveFormPdfMaterializationError("FAILED_HUMAN_REVIEW_REQUIRES_DEFECT_CODE")
    if visual == "PASS" and pedagogical == "PASS" and normalized_defects:
        raise TwelveFormPdfMaterializationError(
            "PASS_HUMAN_REVIEW_CANNOT_KEEP_BLOCKING_DEFECT_CODES"
        )

    artifacts = list(manifest.get("artifacts") or [])
    target = next(
        (
            row
            for row in artifacts
            if int(row.get("form_ordinal", -1)) == int(form_ordinal)
        ),
        None,
    )
    if not isinstance(target, dict):
        raise TwelveFormPdfMaterializationError(
            f"MANIFEST_FORM_ARTIFACT_MISSING:F{int(form_ordinal):02d}"
        )
    actual_sha = str(target.get("pdf_sha256") or "")
    expected_sha = str(expected_pdf_sha256 or "").strip().lower()
    if not expected_sha or actual_sha.lower() != expected_sha:
        raise TwelveFormPdfMaterializationError(
            f"STALE_HUMAN_REVIEW_PDF_SHA256:"
            f"F{int(form_ordinal):02d}:{expected_sha}:{actual_sha.lower()}"
        )

    if reviewed_at is None:
        reviewed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    target["human_visual_review"] = visual
    target["human_pedagogical_review"] = pedagogical
    target["human_review_defect_codes"] = normalized_defects
    target["human_review_evidence_pdf_sha256"] = actual_sha
    target["human_reviewed_at"] = str(reviewed_at)
    manifest["artifacts"] = artifacts
    manifest["latest_human_review_form_id"] = target["form_id"]
    _reconcile_human_review_manifest(manifest)
    _atomic_json(manifest_path, manifest)
    return manifest


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r4-report", type=Path, default=DEFAULT_R4_REPORT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--chromium-path", type=Path)
    parser.add_argument("--record-review-form", type=int)
    parser.add_argument("--expected-pdf-sha256")
    parser.add_argument("--visual-review", choices=("PASS", "FAIL"))
    parser.add_argument("--pedagogical-review", choices=("PASS", "FAIL"))
    parser.add_argument("--defect-code", action="append", default=[])
    parser.add_argument("--reviewed-at")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.record_review_form is not None:
            if not args.expected_pdf_sha256 or not args.visual_review or not args.pedagogical_review:
                raise TwelveFormPdfMaterializationError(
                    "REVIEW_MODE_REQUIRES_SHA_VISUAL_AND_PEDAGOGICAL_STATUS"
                )
            manifest_path = Path(args.output_root).resolve() / MANIFEST_NAME
            value = record_human_review(
                manifest_path=manifest_path,
                form_ordinal=int(args.record_review_form),
                expected_pdf_sha256=str(args.expected_pdf_sha256),
                visual_review=str(args.visual_review),
                pedagogical_review=str(args.pedagogical_review),
                defect_codes=list(args.defect_code or []),
                reviewed_at=args.reviewed_at,
            )
            print("STATUS=PASS_A1FS_V1_U01QB18H_R1A_HUMAN_REVIEW_RECORDED")
            print(f"FORM={int(args.record_review_form):02d}")
            print(f"UNIT01_FORM_PDF_ACCEPTANCE={value['unit01_form01_12_pdf_acceptance']}")
            print(f"UNIT01_FINAL_PDF_ACCEPTANCE={value['unit01_final_pdf_acceptance']}")
            print(f"MANIFEST={manifest_path}")
            return 0

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
    print(
        f"HUMAN_PEDAGOGICAL_REVIEW_PENDING="
        f"{value['human_pedagogical_review_pending_count']}"
    )
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
