from __future__ import annotations

import base64
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Mapping

from product.a1fs_v1_2_1 import u01qb18h_r1_unit01_twelve_form_learner_pdf_materialization as u01_pdf
from product.a1fs_v1_2_1 import u04formv3c_direct_authored_form01_04_validator as formv3c
from product.a1fs_v1_2_1 import u04q10r1_unit04_learner_facing_pedagogical_acceptance as learner_renderer
from product.a1fs_v1_2_1 import u04q10r2_unit04_learner_pdf_materialization_and_visual_acceptance as q10r2
from product.a1fs_v1_2_1 import u04q10r2r1_unit04_actual_pdf_pagination_repair as pagination

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Read-only presentation integration over GPT-5.6-direct-authored FormV3C static assets. "
    "It serializes already-authored structured response data into the already-merged Unit04 "
    "learner renderer primitives, binds GPT-designed static SVG picture assets, restores the "
    "approved worksheet CSS, adds context-group pagination and response-field affordances, "
    "and reuses the merged pagination/Chromium chain. It does not select Current360 sources, "
    "assign response modes/task families, write prompts/answers/distractors, shuffle options, "
    "mutate passages, or create a second renderer/runtime."
)

PROGRAM_ID = "A1FS-V1"
UNIT_ID = "GRAMMAR_BASIC_PREPOSITIONS_PLACE"
TASK_ID = "A1FS-V1-U04FORMV3C_A2_PictureAssetMaterializationAndDiversifiedRendererIntegration"
STATUS = "PASS_A1FS_V1_U04FORMV3C_A2_PICTURE_ASSET_AND_DIVERSIFIED_RENDERER_INTEGRATION"
REVISION = "FORMV3C_A2_EXISTING_RENDERER_PRESENTATION_V2_A3R1"
NEXT_SHORT_STEP = "A1FS-V1-U04FORMV3C_A3_ActualForm01To04PdfHumanVisualPedagogicalAcceptance"
A3_R1_TASK_ID = "A1FS-V1-U04FORMV3C_A3_R1_ActualPdfContextGroupingAndResponseAffordanceFullFix"
A3_R1_STATUS = "PASS_A1FS_V1_U04FORMV3C_A3_R1_CONTEXT_GROUPING_AND_RESPONSE_AFFORDANCE_FULLFIX"
A3_R1_NEXT_SHORT_STEP = "A1FS-V1-U04FORMV3C_A3_R2_ActualForm01To04PdfHumanVisualPedagogicalAcceptance"
FORM_COUNT = 4
QUESTIONS_PER_FORM = 40
TOTAL_QUESTIONS = 160
PICTURE_ASSET_COUNT = 8
CONTEXT_GROUPS_PER_FORM = 10
TOTAL_CONTEXT_GROUPS = FORM_COUNT * CONTEXT_GROUPS_PER_FORM
DEFAULT_OUTPUT_ROOT = Path(".local/a1fs_v1/review/unit04_formv3c_form01_04_visual_acceptance")
MANIFEST_NAME = "unit04_formv3c_form01_04_visual_acceptance.private.json"
PICTURE_MANIFEST_PATH = Path(
    "product/a1fs_v1_2_1/assets/u04formv3c/u04formv3c_picture_asset_manifest.json"
)

SECTION_TITLES = {
    "A": "A · Understand the place",
    "B": "B · Read and find evidence",
    "C": "C · Write from the evidence",
    "D": "D · Understand people, objects, and actions",
    "E": "E · Write and speak",
}
SECTION_COUNTS = {"A": 6, "B": 10, "C": 10, "D": 8, "E": 6}
SECTION_INDEX = {section: index for index, section in enumerate(("A", "B", "C", "D", "E"), start=1)}
CONTEXT_GROUP_LOAD = {"A": 3, "B": 5, "C": 5, "D": 4, "E": 3}

CHOICE_MODES = {"SELECT_ONE", "GIST_BEST_TITLE"}
MATCHING_MODES = {"MATCHING", "MULTIPLE_MATCHING", "REFERENCE_MATCHING"}
FIELD_MODES = {"NOTE_COMPLETION", "TABLE_COMPLETION"}
SPEAKING_MODES = {"SPEAK_SHORT_RESPONSE", "SHORT_RETELL"}
PICTURE_MODES = {"PICTURE_POSITION", "PICTURE_LABEL", "PICTURE_DIFFERENCE"}
EXPECTED_SEMANTIC_RESPONSE_MODES = frozenset(
    {
        "ASK_A_QUESTION",
        "DIALOGUE_RESPONSE",
        "FACT_CORRECTION",
        "GIST_BEST_TITLE",
        "MATCHING",
        "MULTIPLE_MATCHING",
        "NOTE_COMPLETION",
        "ONE_TO_THREE_WORDS",
        "ONE_WORD_GAP",
        "ORDER_SEQUENCE",
        "PICTURE_DIFFERENCE",
        "PICTURE_LABEL",
        "PICTURE_POSITION",
        "RECONSTRUCTION",
        "REFERENCE_MATCHING",
        "SELECT_ONE",
        "SENTENCE_COMPLETION",
        "SHORT_ANSWER",
        "SHORT_RETELL",
        "SPEAK_SHORT_RESPONSE",
        "TABLE_COMPLETION",
        "WRITE_SENTENCE",
    }
)

WORKSHEET_STYLE_ID = "u04-formv3c-approved-worksheet-css"
WORKSHEET_CSS = """
@page{size:A4;margin:10mm 10mm 12mm}
*{box-sizing:border-box}
html,body{margin:0;padding:0;font-family:Arial,"Noto Sans",sans-serif;color:#17202a;background:#fff}
body{font-size:10.5pt;line-height:1.3}
body>h1{font-size:20pt;margin:0 0 2px;line-height:1.12;border-bottom:2px solid #26394d;padding-bottom:5px}
body>p{margin:0 0 7px;color:#566573;font-size:9.5pt}
.unit04-section{margin:0 0 8px;break-inside:auto}
.unit04-section>h2{font-size:14pt;margin:4px 0 5px;border-left:4px solid #34495e;padding:3px 7px;background:#f5f7f8;break-after:avoid;page-break-after:avoid}
.u04-context-group{break-inside:avoid;page-break-inside:avoid;margin:0 0 4px}
.u04-context-group article.activity:last-child{margin-bottom:0}
.activity{break-inside:avoid;border:1px solid #d5d8dc;border-radius:6px;padding:5px 7px;margin:0 0 4px}
.activity-heading{display:flex;align-items:center;gap:7px;margin-bottom:3px}
.question-number{font-weight:800;font-size:10.5pt}
.skill-pill{font-size:8pt;font-weight:700;border:1px solid #aeb6bf;border-radius:999px;padding:1px 6px;color:#455a64}
.stimulus{font-size:11.1pt;font-weight:700;padding:4px 6px;margin:2px 0 4px;background:#f8f9f9;border-radius:4px}
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
.matching-answer-grid,.order-answer-grid{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin:4px 0 1px}
.answer-slot,.order-slot{display:inline-flex;align-items:center;gap:3px;font-weight:700}
.answer-blank{display:inline-block;min-width:28px;height:15px;border-bottom:1px solid #7f8c8d}
.order-slot .answer-blank{min-width:34px}
.order-arrow{color:#7f8c8d;font-weight:700}
.field-answer-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;margin:4px 0 1px}
.field-answer-row{display:flex;align-items:flex-end;gap:4px;min-width:0}
.field-answer-label{font-weight:700;white-space:nowrap}
.field-answer-blank{display:block;flex:1;min-width:42px;height:15px;border-bottom:1px solid #7f8c8d}
""".strip()

PICTURE_STYLE_ID = "u04-formv3c-picture-assets"


class Unit04FormV3CIntegrationError(ValueError):
    pass


def _root(repo_root: Path | str | None = None) -> Path:
    return Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]


def _file_identity(path: Path) -> dict[str, Any]:
    raw = Path(path).read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def _load_picture_manifest(root: Path) -> dict[str, Any]:
    path = root / PICTURE_MANIFEST_PATH
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Unit04FormV3CIntegrationError(f"PICTURE_MANIFEST_UNREADABLE:{path}:{exc}") from exc
    if payload.get("schema_version") != "a1fs.v1.u04.formv3c.picture_assets.v1":
        raise Unit04FormV3CIntegrationError("PICTURE_MANIFEST_SCHEMA_DRIFT")
    if payload.get("task_id") != TASK_ID:
        raise Unit04FormV3CIntegrationError("PICTURE_MANIFEST_TASK_DRIFT")
    provenance = payload.get("authoring_provenance") or {}
    if provenance.get("visual_asset_design") != "GPT-5.6_SOL_DIRECT_DESIGN":
        raise Unit04FormV3CIntegrationError("PICTURE_ASSET_AUTHORING_PROVENANCE_DRIFT")
    if provenance.get("python_visual_authoring_used") is not False:
        raise Unit04FormV3CIntegrationError("PYTHON_VISUAL_AUTHORING_FORBIDDEN")
    rows = list(payload.get("assets") or [])
    if len(rows) != PICTURE_ASSET_COUNT:
        raise Unit04FormV3CIntegrationError(f"PICTURE_ASSET_COUNT_DRIFT:{len(rows)}")
    if len({str(row.get("asset_id") or "") for row in rows}) != PICTURE_ASSET_COUNT:
        raise Unit04FormV3CIntegrationError("PICTURE_ASSET_ID_DUPLICATE")
    return payload


def _picture_assets(root: Path) -> dict[str, dict[str, Any]]:
    manifest = _load_picture_manifest(root)
    result: dict[str, dict[str, Any]] = {}
    for row in manifest["assets"]:
        asset_id = str(row["asset_id"])
        path = root / str(row["relative_path"])
        if not path.is_file():
            raise Unit04FormV3CIntegrationError(f"PICTURE_ASSET_MISSING:{asset_id}:{path}")
        raw = path.read_bytes()
        if not raw.lstrip().startswith(b"<svg"):
            raise Unit04FormV3CIntegrationError(f"PICTURE_ASSET_NOT_SVG:{asset_id}")
        result[asset_id] = {
            **dict(row),
            "path": path,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
        }
    return result


def _learner_skill(task: Mapping[str, Any]) -> str:
    mode = str(task.get("response_mode") or "")
    if mode in SPEAKING_MODES:
        return "SPEAKING"
    skill = str(task.get("skill") or "")
    if "WRITING" in skill:
        return "WRITING"
    if skill == "GRAMMAR":
        return "GRAMMAR"
    return "READING"


def _primitive_response(task: Mapping[str, Any]) -> tuple[str, list[str] | None]:
    mode = str(task.get("response_mode") or "")
    if mode in CHOICE_MODES or (
        mode == "DIALOGUE_RESPONSE" and task.get("dialogue_mode") == "select_one"
    ):
        return "select_one", list(task.get("options") or [])
    if mode == "ORDER_SEQUENCE":
        values = [str(value) for value in task.get("sequence_items") or []]
        return "ordered_tokens", [f"{index}. {value}" for index, value in enumerate(values, start=1)]
    if mode in MATCHING_MODES:
        left = [str(value) for value in task.get("left_items") or []]
        right = [str(value) for value in task.get("right_options") or []]
        tokens = [f"{index}. {value}" for index, value in enumerate(left, start=1)]
        tokens.extend(f"{chr(ord('A') + index)}. {value}" for index, value in enumerate(right))
        return "ordered_tokens", tokens
    if mode in FIELD_MODES:
        fields = list(task.get("response_fields") or [])
        tokens = [f"{str(row.get('label') or '').strip()}: __________" for row in fields]
        return "ordered_tokens", tokens
    if mode in SPEAKING_MODES:
        return "practice_only", None
    return "short_text", None


def _project_form(payload: Mapping[str, Any], picture_assets: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    form = dict(payload.get("form") or {})
    contexts = {str(row["slot"]): dict(row) for row in form.get("contexts") or []}
    tasks = list(form.get("tasks") or [])
    if len(tasks) != QUESTIONS_PER_FORM:
        raise Unit04FormV3CIntegrationError(f"TASK_COUNT_DRIFT:{len(tasks)}")

    activities: list[dict[str, Any]] = []
    seen_section_context: set[tuple[str, str]] = set()
    section_ordinals = Counter()
    semantic_modes: Counter[str] = Counter()
    picture_bindings: list[dict[str, Any]] = []

    for task in tasks:
        section = str(task["section"])
        slot = str(task["context_role"])
        key = (section, slot)
        passage = str(contexts[slot]["passage"]) if key not in seen_section_context else ""
        seen_section_context.add(key)

        semantic_mode = str(task["response_mode"])
        semantic_modes[semantic_mode] += 1
        primitive_mode, primitive_values = _primitive_response(task)
        section_ordinals[section] += 1

        activity = {
            "question_number": f"Q{int(task['question_number']):02d}",
            "skill": _learner_skill(task),
            "stimulus": passage,
            "prompt": str(task["prompt"]),
            "response_mode": primitive_mode,
            "semantic_response_mode": semantic_mode,
            "section": section,
            "section_ordinal": int(section_ordinals[section]),
            "context_role": slot,
            "response_field_count": int(task.get("response_field_count") or 1),
            "response_labels": [
                str(row.get("label") or "").strip()
                for row in task.get("response_fields") or []
            ],
        }
        if primitive_mode == "select_one":
            activity["options"] = list(primitive_values or [])
        elif primitive_mode == "ordered_tokens":
            activity["ordered_tokens"] = list(primitive_values or [])

        if bool(task.get("picture_required")):
            spec = dict(task.get("visual_spec") or {})
            asset_id = str(spec.get("asset_id") or "")
            asset = picture_assets.get(asset_id)
            if asset is None:
                raise Unit04FormV3CIntegrationError(
                    f"PICTURE_ASSET_BINDING_MISSING:{task.get('question_id')}:{asset_id}"
                )
            if int(asset["form_number"]) != int(form["form_number"]):
                raise Unit04FormV3CIntegrationError(f"PICTURE_ASSET_FORM_DRIFT:{asset_id}")
            if int(asset["question_number"]) != int(task["question_number"]):
                raise Unit04FormV3CIntegrationError(f"PICTURE_ASSET_QUESTION_DRIFT:{asset_id}")
            if str(asset["response_mode"]) != semantic_mode:
                raise Unit04FormV3CIntegrationError(f"PICTURE_ASSET_MODE_DRIFT:{asset_id}")
            picture_bindings.append(
                {
                    "asset_id": asset_id,
                    "section": section,
                    "section_ordinal": int(section_ordinals[section]),
                    "height_mm": int(asset["height_mm"]),
                    "path": Path(asset["path"]),
                    "sha256": str(asset["sha256"]),
                }
            )
        activities.append(activity)

    if len(semantic_modes) != 21 or not set(semantic_modes).issubset(EXPECTED_SEMANTIC_RESPONSE_MODES):
        raise Unit04FormV3CIntegrationError(
            f"FORM_RESPONSE_MODE_COVERAGE_DRIFT:F{form.get('form_number')}:{sorted(semantic_modes)}"
        )
    if len(picture_bindings) != 2:
        raise Unit04FormV3CIntegrationError(
            f"FORM_PICTURE_BINDING_COUNT_DRIFT:F{form.get('form_number')}:{len(picture_bindings)}"
        )

    return {
        "form_id": str(form["form_id"]),
        "form_ordinal": int(form["form_number"]),
        "progression_stage": str(form["stage"]),
        "sections": [
            {"section": section, "section_name": SECTION_TITLES[section], "activity_count": SECTION_COUNTS[section]}
            for section in ("A", "B", "C", "D", "E")
        ],
        "activities": activities,
        "semantic_response_mode_counts": dict(sorted(semantic_modes.items())),
        "picture_bindings": picture_bindings,
    }


def load_projected_formv3c_forms(repo_root: Path | str | None = None) -> list[dict[str, Any]]:
    root = _root(repo_root)
    validation = formv3c.validate_form01_04(root)
    if validation.get("status") != formv3c.STATUS:
        raise Unit04FormV3CIntegrationError("FORMV3C_SOURCE_NOT_PASS")
    picture_assets = _picture_assets(root)
    forms = [
        _project_form(formv3c._load_asset(root, ordinal), picture_assets)
        for ordinal in formv3c.EXPECTED_FORMS
    ]
    if [row["form_ordinal"] for row in forms] != [1, 2, 3, 4]:
        raise Unit04FormV3CIntegrationError("FORM_SEQUENCE_DRIFT")
    if sum(len(row["picture_bindings"]) for row in forms) != PICTURE_ASSET_COUNT:
        raise Unit04FormV3CIntegrationError("PICTURE_BINDING_TOTAL_DRIFT")
    return forms


def inject_approved_worksheet_css(rendered_html: str) -> str:
    html = str(rendered_html)
    if WORKSHEET_STYLE_ID in html:
        raise Unit04FormV3CIntegrationError("WORKSHEET_STYLE_ALREADY_PRESENT")
    marker = "</head>"
    if html.count(marker) != 1:
        raise Unit04FormV3CIntegrationError(f"HTML_HEAD_BOUNDARY_INVALID:{html.count(marker)}")
    style = f'<style id="{WORKSHEET_STYLE_ID}">{WORKSHEET_CSS}</style>'
    return html.replace(marker, style + marker, 1)


def _context_group_ranges(form: Mapping[str, Any]) -> list[tuple[int, int]]:
    activities = list(form.get("activities") or [])
    if len(activities) != QUESTIONS_PER_FORM:
        raise Unit04FormV3CIntegrationError("CONTEXT_GROUP_ACTIVITY_COUNT_DRIFT")
    groups: list[tuple[int, int]] = []
    start = 0
    last_key: tuple[str, str] | None = None
    for index, activity in enumerate(activities):
        key = (str(activity.get("section") or ""), str(activity.get("context_role") or ""))
        if last_key is None:
            last_key = key
            start = index
        elif key != last_key:
            groups.append((start, index - 1))
            start = index
            last_key = key
    groups.append((start, len(activities) - 1))
    if len(groups) != CONTEXT_GROUPS_PER_FORM:
        raise Unit04FormV3CIntegrationError(
            f"CONTEXT_GROUP_COUNT_DRIFT:F{form.get('form_ordinal')}:{len(groups)}"
        )
    return groups


def _structured_response_article(article: str, activity: Mapping[str, Any]) -> str:
    mode = str(activity.get("semantic_response_mode") or "")
    old_two_lines = '<div class="write-line"></div><div class="write-line"></div>'
    if mode in MATCHING_MODES:
        count = int(activity.get("response_field_count") or 0)
        if count < 1 or old_two_lines not in article:
            raise Unit04FormV3CIntegrationError(
                f"MATCHING_RESPONSE_AFFORDANCE_SOURCE_INVALID:{activity.get('question_number')}"
            )
        slots = "".join(
            f'<span class="answer-slot">{index}.<span class="answer-blank"></span></span>'
            for index in range(1, count + 1)
        )
        return article.replace(
            old_two_lines,
            f'<div class="matching-answer-grid">{slots}</div>',
            1,
        )
    if mode == "ORDER_SEQUENCE":
        count = int(activity.get("response_field_count") or 0)
        if count < 1 or old_two_lines not in article:
            raise Unit04FormV3CIntegrationError(
                f"ORDER_RESPONSE_AFFORDANCE_SOURCE_INVALID:{activity.get('question_number')}"
            )
        parts: list[str] = []
        for index in range(count):
            if index:
                parts.append('<span class="order-arrow">→</span>')
            parts.append('<span class="order-slot"><span class="answer-blank"></span></span>')
        return article.replace(
            old_two_lines,
            '<div class="order-answer-grid">' + "".join(parts) + "</div>",
            1,
        )
    if mode in FIELD_MODES:
        labels = [str(value) for value in activity.get("response_labels") or []]
        count = int(activity.get("response_field_count") or 0)
        if len(labels) != count or count < 1:
            raise Unit04FormV3CIntegrationError(
                f"FIELD_RESPONSE_LABEL_COUNT_INVALID:{activity.get('question_number')}"
            )
        rows = "".join(
            '<div class="field-answer-row">'
            f'<span class="field-answer-label">{u01_pdf._safe_text(label)}</span>'
            '<span class="field-answer-blank"></span></div>'
            for label in labels
        )
        pattern = re.compile(
            r'<div class="tokens">.*?</div>'
            r'<div class="write-line"></div><div class="write-line"></div>',
            flags=re.S,
        )
        repaired, replacement_count = pattern.subn(
            '<div class="field-answer-grid">' + rows + "</div>",
            article,
            count=1,
        )
        if replacement_count != 1:
            raise Unit04FormV3CIntegrationError(
                f"FIELD_RESPONSE_AFFORDANCE_SOURCE_INVALID:{activity.get('question_number')}"
            )
        return repaired
    return article


def inject_context_grouping_and_response_affordances(
    rendered_html: str,
    form: Mapping[str, Any],
) -> str:
    html = str(rendered_html)
    activities = list(form.get("activities") or [])
    if len(activities) != QUESTIONS_PER_FORM:
        raise Unit04FormV3CIntegrationError(
            f"A3R1_ACTIVITY_COUNT_DRIFT:{len(activities)}"
        )

    article_pattern = re.compile(r'<article class="activity">.*?</article>', flags=re.S)
    matches = list(article_pattern.finditer(html))
    if len(matches) != QUESTIONS_PER_FORM:
        raise Unit04FormV3CIntegrationError(
            f"A3R1_RENDERED_ACTIVITY_COUNT_DRIFT:{len(matches)}"
        )
    repaired_articles = [
        _structured_response_article(match.group(0), activity)
        for match, activity in zip(matches, activities)
    ]
    rendered_iter = iter(repaired_articles)

    section_pattern = re.compile(
        r'(<section class="unit04-section"><h2>.*?</h2>)(.*?)(</section>)',
        flags=re.S,
    )
    section_matches = list(section_pattern.finditer(html))
    if len(section_matches) != len(SECTION_COUNTS):
        raise Unit04FormV3CIntegrationError(
            f"A3R1_SECTION_COUNT_DRIFT:{len(section_matches)}"
        )

    pieces: list[str] = []
    cursor = 0
    activity_cursor = 0
    context_group_count = 0
    for section_match in section_matches:
        pieces.append(html[cursor:section_match.start()])
        pieces.append(section_match.group(1))
        body = section_match.group(2)
        section_articles = list(article_pattern.finditer(body))
        if not section_articles:
            raise Unit04FormV3CIntegrationError("A3R1_SECTION_ACTIVITY_MISSING")
        section_activity_count = len(section_articles)
        section_activities = activities[
            activity_cursor:activity_cursor + section_activity_count
        ]
        body_groups: list[str] = []
        section_body_cursor = 0
        group_open = False
        last_key: tuple[str, str] | None = None
        for local_index, section_article in enumerate(section_articles):
            body_groups.append(body[section_body_cursor:section_article.start()])
            activity = section_activities[local_index]
            key = (
                str(activity.get("section") or ""),
                str(activity.get("context_role") or ""),
            )
            if last_key is None or key != last_key:
                if group_open:
                    body_groups.append("</div>")
                body_groups.append('<div class="u04-context-group">')
                context_group_count += 1
                group_open = True
                last_key = key
            body_groups.append(next(rendered_iter))
            section_body_cursor = section_article.end()
        body_groups.append(body[section_body_cursor:])
        if group_open:
            body_groups.append("</div>")
        pieces.extend(body_groups)
        pieces.append(section_match.group(3))
        cursor = section_match.end()
        activity_cursor += section_activity_count
    pieces.append(html[cursor:])
    repaired = "".join(pieces)

    if activity_cursor != QUESTIONS_PER_FORM:
        raise Unit04FormV3CIntegrationError(
            f"A3R1_ACTIVITY_CURSOR_DRIFT:{activity_cursor}"
        )
    if context_group_count != CONTEXT_GROUPS_PER_FORM:
        raise Unit04FormV3CIntegrationError(
            f"CONTEXT_GROUP_WRAPPER_COUNT_DRIFT:{context_group_count}"
        )

    expected_matching = sum(
        str(activity.get("semantic_response_mode") or "") in MATCHING_MODES
        for activity in activities
    )
    expected_order = sum(
        str(activity.get("semantic_response_mode") or "") == "ORDER_SEQUENCE"
        for activity in activities
    )
    expected_fields = sum(
        str(activity.get("semantic_response_mode") or "") in FIELD_MODES
        for activity in activities
    )
    if repaired.count('class="matching-answer-grid"') != expected_matching:
        raise Unit04FormV3CIntegrationError("MATCHING_AFFORDANCE_COUNT_DRIFT")
    if repaired.count('class="order-answer-grid"') != expected_order:
        raise Unit04FormV3CIntegrationError("ORDER_AFFORDANCE_COUNT_DRIFT")
    if repaired.count('class="field-answer-grid"') != expected_fields:
        raise Unit04FormV3CIntegrationError("FIELD_AFFORDANCE_COUNT_DRIFT")
    if repaired.count('<article class="activity">') != QUESTIONS_PER_FORM:
        raise Unit04FormV3CIntegrationError("A3R1_ACTIVITY_MARKUP_MUTATED")
    return repaired


def _picture_css(form: Mapping[str, Any]) -> str:
    rules: list[str] = []
    for binding in form.get("picture_bindings") or []:
        raw = Path(binding["path"]).read_bytes()
        encoded = base64.b64encode(raw).decode("ascii")
        section = str(binding["section"])
        section_index = SECTION_INDEX[section]
        ordinal = int(binding["section_ordinal"])
        group_load = CONTEXT_GROUP_LOAD[section]
        context_group = (ordinal - 1) // group_load + 1
        local_ordinal = (ordinal - 1) % group_load + 1
        height = int(binding["height_mm"])
        selector = (
            f".unit04-section:nth-of-type({section_index}) "
            f".u04-context-group:nth-of-type({context_group}) "
            f"article.activity:nth-of-type({local_ordinal})::before"
        )
        rules.append(
            selector
            + "{content:\"\";display:block;width:100%;height:"
            + f"{height}mm;background-image:url(\"data:image/svg+xml;base64,{encoded}\");"
            + "background-repeat:no-repeat;background-position:center;background-size:contain;"
            + "margin:2mm 0 2.5mm;break-inside:avoid;page-break-inside:avoid;}"
        )
    return "\n".join(rules)


def inject_picture_assets(rendered_html: str, form: Mapping[str, Any]) -> str:
    html = str(rendered_html)
    if PICTURE_STYLE_ID in html:
        raise Unit04FormV3CIntegrationError("PICTURE_STYLE_ALREADY_PRESENT")
    css = _picture_css(form)
    if css.count("data:image/svg+xml;base64,") != 2:
        raise Unit04FormV3CIntegrationError(
            f"PICTURE_DATA_URI_COUNT_DRIFT:F{form.get('form_ordinal')}:{css.count('data:image/svg+xml;base64,')}"
        )
    marker = "</head>"
    style = f'<style id="{PICTURE_STYLE_ID}">{css}</style>'
    return html.replace(marker, style + marker, 1)


def render_formv3c_with_existing_renderer(form: Mapping[str, Any]) -> str:
    # The only learner HTML renderer invoked is the merged Unit04 Q10R1 renderer.
    html = learner_renderer.render_form_html(form)
    html = inject_context_grouping_and_response_affordances(html, form)
    html = inject_approved_worksheet_css(html)
    html = inject_picture_assets(html, form)
    html = pagination.inject_pdf_pagination_guards(html)
    if html.count('<article class="activity">') != QUESTIONS_PER_FORM:
        raise Unit04FormV3CIntegrationError("RENDERED_ACTIVITY_COUNT_DRIFT")
    if html.count('<div class="stimulus">') != CONTEXT_GROUPS_PER_FORM:
        raise Unit04FormV3CIntegrationError("PASSAGE_DISPLAY_COUNT_DRIFT")
    return html


def build_machine_integration_report(repo_root: Path | str | None = None) -> dict[str, Any]:
    root = _root(repo_root)
    forms = load_projected_formv3c_forms(root)
    rendered = [render_formv3c_with_existing_renderer(form) for form in forms]
    semantic_counts = Counter()
    primitive_counts = Counter()
    matching_affordance_count = 0
    order_affordance_count = 0
    field_affordance_count = 0
    for form in forms:
        for activity in form["activities"]:
            mode = str(activity["semantic_response_mode"])
            semantic_counts[mode] += 1
            primitive_counts[str(activity["response_mode"])] += 1
            matching_affordance_count += mode in MATCHING_MODES
            order_affordance_count += mode == "ORDER_SEQUENCE"
            field_affordance_count += mode in FIELD_MODES
    if set(semantic_counts) != EXPECTED_SEMANTIC_RESPONSE_MODES:
        raise Unit04FormV3CIntegrationError(
            f"GLOBAL_RESPONSE_MODE_COVERAGE_DRIFT:{sorted(semantic_counts)}"
        )
    return {
        "task_id": TASK_ID,
        "status": STATUS,
        "revision": REVISION,
        "a3_r1_task_id": A3_R1_TASK_ID,
        "a3_r1_status": A3_R1_STATUS,
        "form_count": len(forms),
        "question_count": sum(len(form["activities"]) for form in forms),
        "semantic_response_mode_coverage_count": len(semantic_counts),
        "semantic_response_mode_coverage": sorted(semantic_counts),
        "presentation_primitive_counts": dict(sorted(primitive_counts.items())),
        "picture_asset_count": PICTURE_ASSET_COUNT,
        "picture_binding_count": sum(len(form["picture_bindings"]) for form in forms),
        "picture_css_form_count": sum(PICTURE_STYLE_ID in html for html in rendered),
        "picture_data_uri_count": sum(html.count("data:image/svg+xml;base64,") for html in rendered),
        "html_activity_count": sum(html.count('<article class="activity">') for html in rendered),
        "context_group_count": sum(html.count('class="u04-context-group"') for html in rendered),
        "context_group_passage_count": sum(html.count('<div class="stimulus">') for html in rendered),
        "matching_affordance_count": matching_affordance_count,
        "order_affordance_count": order_affordance_count,
        "field_affordance_count": field_affordance_count,
        "worksheet_css_form_count": sum(WORKSHEET_STYLE_ID in html for html in rendered),
        "pagination_guard_form_count": sum(pagination.PDF_PAGINATION_STYLE_ID in html for html in rendered),
        "renderer_task_id": learner_renderer.TASK_ID,
        "renderer_reused": True,
        "second_renderer_created": False,
        "python_blueprint_generation_used": False,
        "python_response_mode_assignment_used": False,
        "python_task_family_assignment_used": False,
        "python_learner_content_authoring_used": False,
        "python_answer_option_authoring_used": False,
        "python_visual_authoring_used": False,
        "current360_passage_mutated": False,
        "listening_modified": False,
        "a2_a2plus_unlocked": False,
        "human_visual_review": "PENDING_ACTUAL_PDF_EVIDENCE",
        "human_pedagogical_review": "PENDING_ACTUAL_PDF_EVIDENCE",
        "next_short_step": A3_R1_NEXT_SHORT_STEP,
    }


def materialize_form01_04_pdfs(
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    chromium_path: Path | None = None,
    browser_runner: Callable[..., Mapping[str, Any]] | None = None,
    pdf_page_counter: Callable[[Path], int] | None = None,
    repo_root: Path | str | None = None,
) -> dict[str, Any]:
    forms = load_projected_formv3c_forms(repo_root)
    output_root = Path(output_root).resolve()
    html_root = output_root / "html"
    pdf_root = output_root / "pdf"
    html_root.mkdir(parents=True, exist_ok=True)
    pdf_root.mkdir(parents=True, exist_ok=True)

    chromium = (
        Path(chromium_path).resolve(strict=True)
        if chromium_path is not None
        else q10r2.chromium_acceptance.discover_chromium()
    )
    run_browser = browser_runner or q10r2.UNIT01_HEADERLESS_BROWSER_RUNNER
    count_pages = pdf_page_counter or q10r2.UNIT01_PDF_PAGE_COUNTER

    artifacts: list[dict[str, Any]] = []
    for form in forms:
        ordinal = int(form["form_ordinal"])
        html_path = html_root / f"Form{ordinal:02d}.html"
        pdf_path = pdf_root / f"Form{ordinal:02d}.pdf"
        rendered = render_formv3c_with_existing_renderer(form)
        u01_pdf._atomic_text(html_path, rendered)
        result = dict(run_browser(chromium, source_html=html_path, output_path=pdf_path, mode="PDF"))
        if not pdf_path.is_file():
            raise Unit04FormV3CIntegrationError(f"PDF_OUTPUT_MISSING:F{ordinal:02d}")
        identity = _file_identity(pdf_path)
        if identity["bytes"] < 1024:
            raise Unit04FormV3CIntegrationError(f"PDF_OUTPUT_TOO_SMALL:F{ordinal:02d}:{identity['bytes']}")
        page_count = int(count_pages(pdf_path))
        if page_count < 1:
            raise Unit04FormV3CIntegrationError(f"PDF_PAGE_COUNT_INVALID:F{ordinal:02d}:{page_count}")
        artifacts.append(
            {
                "form_id": form["form_id"],
                "form_ordinal": ordinal,
                "html_relative_path": f"html/Form{ordinal:02d}.html",
                "pdf_relative_path": f"pdf/Form{ordinal:02d}.pdf",
                "pdf_bytes": identity["bytes"],
                "pdf_sha256": identity["sha256"],
                "page_count": page_count,
                "browser_render": {k: v for k, v in result.items() if k not in {"source_path", "output_path"}},
                "picture_asset_count": len(form["picture_bindings"]),
                "context_group_count": len(_context_group_ranges(form)),
                "human_visual_review": "PENDING",
                "human_pedagogical_review": "PENDING",
            }
        )

    if len(artifacts) != FORM_COUNT:
        raise Unit04FormV3CIntegrationError(f"PDF_COUNT_DRIFT:{len(artifacts)}")
    if len({row["pdf_sha256"] for row in artifacts}) != FORM_COUNT:
        raise Unit04FormV3CIntegrationError("PDF_SHA256_NOT_DISTINCT")

    manifest = {
        "schema_version": "a1fs.v1.u04.formv3c.a3r1.actual_pdf_manifest.v1",
        "task_id": TASK_ID,
        "machine_status": STATUS,
        "a3_r1_task_id": A3_R1_TASK_ID,
        "a3_r1_status": A3_R1_STATUS,
        "form_count": FORM_COUNT,
        "question_count": TOTAL_QUESTIONS,
        "semantic_response_mode_coverage_count": len(EXPECTED_SEMANTIC_RESPONSE_MODES),
        "materialized_picture_asset_count": PICTURE_ASSET_COUNT,
        "materialized_pdf_count": FORM_COUNT,
        "context_group_count": TOTAL_CONTEXT_GROUPS,
        "renderer_reused": learner_renderer.TASK_ID,
        "pagination_reused": pagination.TASK_ID,
        "chromium_chain_reused": q10r2.TASK_ID,
        "python_learner_content_authoring_used": False,
        "python_visual_authoring_used": False,
        "artifacts": artifacts,
        "human_visual_review_pending_count": FORM_COUNT,
        "human_pedagogical_review_pending_count": FORM_COUNT,
        "human_acceptance": "PENDING_ACTUAL_PDF_REVIEW",
        "next_short_step": A3_R1_NEXT_SHORT_STEP,
    }
    u01_pdf._atomic_json(output_root / MANIFEST_NAME, manifest)
    return manifest


def main() -> int:
    print(json.dumps(build_machine_integration_report(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
