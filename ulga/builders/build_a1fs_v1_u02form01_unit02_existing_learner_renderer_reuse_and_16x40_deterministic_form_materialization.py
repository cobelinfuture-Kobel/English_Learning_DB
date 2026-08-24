#!/usr/bin/env python3
"""Materialize Unit02 Forms01..16 from the already-approved deterministic runtime.

This module is a read-only learner-facing presentation consumer over U02QB03 /
U02FP01. It does not select, shuffle, author, replace, or promote QuestionBank
content. Each of the 640 runtime occurrences keeps the exact selected item
chosen by the existing Unit02 deterministic runtime.

The learner-safe activity shape and answer/private-key guard are reused from the
accepted Unit01 learner materialization. HTML activity rendering is reused from
the accepted Unit01 printable learner renderer, while Unit02 supplies its own
4-scene x 10-activity grouping because the Unit01 renderer's 4 x 5 denominator
is intentionally Unit01-specific.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from product.a1fs_v1_2_1 import (
    u01qb18a_form01_fresh_learner_materialization_export as u01_learner,
)
from product.a1fs_v1_2_1 import (
    u01qb18h_r1_unit01_twelve_form_learner_pdf_materialization as u01_print,
)
from ulga.builders import (
    build_a1fs_v1_u02fp01_unit02_final_package_q1_q10_export as u02fp01,
)
from ulga.builders import (
    build_a1fs_v1_u02qbc02_unit02_questionbank_gap_materialization_and_per_slot_distinct_capacity_proof
    as qbc02,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Read-only Unit02 learner-facing presentation/materialization consumer over "
    "the already-approved U02QB03/U02FP01 deterministic 16x40 runtime. It reuses "
    "the accepted Unit01 learner-safe activity projection, answer/private-key "
    "guard, and printable activity renderer; it creates no QuestionBank item, "
    "SentenceAsset, canonical scene, selector, runtime/state/scoring authority, "
    "Unit03-24 content, audio/Speaking score, or A2 authority."
)

PROGRAM_ID = "A1FS-V1"
TASK_ID = (
    "A1FS-V1-U02FORM01_"
    "Unit02ExistingLearnerRendererReuseAnd16x40DeterministicFormMaterialization"
)
SCHEMA_VERSION = "a1fs.v1.u02form01.learner_form_materialization.v1"
PASS_STATUS = (
    "PASS_A1FS_V1_U02FORM01_"
    "UNIT02_EXISTING_LEARNER_RENDERER_REUSE_AND_16X40_DETERMINISTIC_FORM_MATERIALIZATION"
)
NEXT_SHORT_STEP = (
    "A1FS-V1-U02FORM02_"
    "Unit02Form01To16ChromiumPdfMaterializationAndLearnerFacingAcceptance"
)

UNIT_ID = "GRAMMAR_REGULAR_PLURAL_NOUNS"
FORM_COUNT = 16
SCENE_COUNT = 4
TASK_FAMILY_COUNT = 10
ACTIVITIES_PER_SCENE = 10
ACTIVITIES_PER_FORM = 40
TOTAL_ACTIVITIES = 640
Q6_BOUND_OCCURRENCES = 128
EXPECTED_SKILL_COUNTS = {"READING": 16, "WRITING": 24}
ALLOWED_RESPONSE_MODES = frozenset({"select_one", "short_text"})
FORBIDDEN_HTML_MARKERS = (
    "correct_answer",
    "correct_answers",
    "answer_key",
    "expected_answer",
    "expected_response",
    "scoring_contract",
    "scoring_model",
    "private_item_json",
    "candidate_ids",
    "selected_item_id",
    "runtime_occurrence_id",
    "sentence_asset_id",
)


class Unit02FormMaterializationError(ValueError):
    """Fail-closed Unit02 learner-facing materialization defect."""


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _q10() -> dict[str, Any]:
    payload = u02fp01.build_export_payload()
    q10 = dict(payload["q10_questionbank_capacity_runtime"])
    contract = q10["runtime_form_contract"]
    expected = {
        "form_count": FORM_COUNT,
        "scene_slots_per_form": SCENE_COUNT,
        "task_family_count": TASK_FAMILY_COUNT,
        "activities_per_form": ACTIVITIES_PER_FORM,
        "runtime_occurrence_count": TOTAL_ACTIVITIES,
    }
    for key, value in expected.items():
        if int(contract.get(key, -1)) != value:
            raise Unit02FormMaterializationError(
                f"Q10_FORM_CONTRACT_DRIFT:{key}:{contract.get(key)}:{value}"
            )
    if contract.get("runtime_connected") is not True:
        raise Unit02FormMaterializationError("Q10_RUNTIME_NOT_CONNECTED")
    if contract.get("final_forms_materialized") is not True:
        raise Unit02FormMaterializationError("Q10_FINAL_FORMS_NOT_MATERIALIZED")
    if contract.get("all_slots_retain_three_legal_candidates") is not True:
        raise Unit02FormMaterializationError("Q10_THREE_CANDIDATE_CONTRACT_DRIFT")
    return q10


def _item_index(q10: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    rows = [dict(row) for row in q10["unit02_approved_items"]]
    result = {str(row["item_id"]): row for row in rows}
    if len(rows) != 994 or len(result) != 994:
        raise Unit02FormMaterializationError(
            f"QUESTIONBANK_INVENTORY_DRIFT:{len(rows)}:{len(result)}"
        )
    return result


def _response_mode(item: Mapping[str, Any]) -> str:
    options = list(item.get("options") or [])
    mode = "select_one" if options else "short_text"
    if mode not in ALLOWED_RESPONSE_MODES:
        raise Unit02FormMaterializationError(f"RESPONSE_MODE_INVALID:{mode}")
    if mode == "select_one" and len(options) < 2:
        raise Unit02FormMaterializationError(
            f"SELECT_ONE_OPTIONS_TOO_SHALLOW:{item.get('item_id')}"
        )
    return mode


def _scene_ref(form_number: int, scene_slot: int) -> str:
    return f"U02-F{form_number:02d}-S{scene_slot:02d}"


def _learner_activity(
    *,
    number: int,
    runtime_row: Mapping[str, Any],
    item: Mapping[str, Any],
) -> dict[str, Any]:
    selected_item_id = str(runtime_row["selected_item_id"])
    if selected_item_id != str(runtime_row["questionbank_item_id"]):
        raise Unit02FormMaterializationError(
            f"RUNTIME_QUESTIONBANK_BINDING_DRIFT:{runtime_row['slot_id']}"
        )
    if selected_item_id != str(item["item_id"]):
        raise Unit02FormMaterializationError(
            f"SELECTED_ITEM_LOOKUP_DRIFT:{runtime_row['slot_id']}"
        )
    if item.get("learner_visible_capable") is not True:
        raise Unit02FormMaterializationError(
            f"SELECTED_ITEM_NOT_LEARNER_VISIBLE:{selected_item_id}"
        )
    if str(runtime_row.get("target_singular") or "").casefold() == "beer":
        raise Unit02FormMaterializationError(
            f"RUNTIME_RESTRICTED_SURFACE_SELECTED:{runtime_row['slot_id']}"
        )

    response_contract = item.get("response_contract") or {}
    capture_enabled = bool(response_contract.get("capture_enabled", True))
    form_number = int(runtime_row["form_number"])
    scene_slot = int(runtime_row["scene_slot_ordinal"])
    selected = {
        "activity_id": str(runtime_row["slot_id"]),
        "skill": str(item["skill"]),
        "scene_ref_id": _scene_ref(form_number, scene_slot),
        "setting": f"Practice set {scene_slot}",
        "stimulus": str(item.get("stimulus") or ""),
        "prompt": str(item.get("prompt") or ""),
        "options": list(item.get("options") or []),
        "response_mode": _response_mode(item),
        "capture_enabled": capture_enabled,
        "practice_only": False,
    }
    blueprint = {
        "scene_ref_id": selected["scene_ref_id"],
        "skill": selected["skill"],
    }
    # Reuse the accepted Unit01 learner-safe activity projection contract.
    activity = u01_learner._student_activity(
        number=number,
        blueprint=blueprint,
        selected=selected,
    )
    return activity


def _selection_identity(runtime_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "slot_id": str(row["slot_id"]),
            "runtime_occurrence_id": str(row["runtime_occurrence_id"]),
            "selected_item_id": str(row["selected_item_id"]),
        }
        for row in runtime_rows
    ]


def _materialize_form(
    *,
    form_number: int,
    runtime_rows: Sequence[Mapping[str, Any]],
    items: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    rows = [dict(row) for row in runtime_rows if int(row["form_number"]) == form_number]
    if len(rows) != ACTIVITIES_PER_FORM:
        raise Unit02FormMaterializationError(
            f"FORM_ACTIVITY_COUNT_DRIFT:F{form_number:02d}:{len(rows)}"
        )

    activities: list[dict[str, Any]] = []
    skill_counts: Counter[str] = Counter()
    scene_counts: Counter[int] = Counter()

    for number, row in enumerate(rows, start=1):
        scene_slot = int(row["scene_slot_ordinal"])
        task_index = ((number - 1) % TASK_FAMILY_COUNT) + 1
        expected_slot = f"U02-F{form_number:02d}-S{scene_slot:02d}-T{task_index:02d}"
        if str(row["slot_id"]) != expected_slot:
            raise Unit02FormMaterializationError(
                f"Q10_SLOT_ORDER_DRIFT:{row['slot_id']}:{expected_slot}"
            )
        expected_family = qbc02.TASK_FAMILIES[task_index - 1]
        if str(row["task_family"]) != expected_family:
            raise Unit02FormMaterializationError(
                f"TASK_FAMILY_ORDER_DRIFT:{row['slot_id']}:{row['task_family']}:{expected_family}"
            )
        candidates = list(row.get("candidate_ids") or [])
        if len(candidates) != 3 or len(set(candidates)) != 3:
            raise Unit02FormMaterializationError(
                f"RUNTIME_CANDIDATE_CONTRACT_DRIFT:{row['slot_id']}"
            )
        if str(row["selected_item_id"]) != str(candidates[0]):
            raise Unit02FormMaterializationError(
                f"DETERMINISTIC_SELECTION_RULE_DRIFT:{row['slot_id']}"
            )
        item = items.get(str(row["selected_item_id"]))
        if item is None:
            raise Unit02FormMaterializationError(
                f"SELECTED_ITEM_NOT_IN_APPROVED_INVENTORY:{row['selected_item_id']}"
            )
        activity = _learner_activity(number=number, runtime_row=row, item=item)
        activities.append(activity)
        skill_counts[activity["skill"]] += 1
        scene_counts[scene_slot] += 1

    if dict(skill_counts) != EXPECTED_SKILL_COUNTS:
        raise Unit02FormMaterializationError(
            f"FORM_SKILL_COUNT_DRIFT:F{form_number:02d}:{dict(skill_counts)}"
        )
    if scene_counts != Counter({ordinal: ACTIVITIES_PER_SCENE for ordinal in range(1, SCENE_COUNT + 1)}):
        raise Unit02FormMaterializationError(
            f"FORM_SCENE_ACTIVITY_COUNT_DRIFT:F{form_number:02d}:{dict(scene_counts)}"
        )

    student_form = {
        "unit_id": UNIT_ID,
        "unit_ordinal": 2,
        "form_id": f"U02-F{form_number:02d}",
        "form_ordinal": form_number,
        "progression_stage": str(rows[0]["progression_stage"]),
        "scene_count": SCENE_COUNT,
        "learner_visible_activity_count": len(activities),
        "skill_counts": dict(skill_counts),
        "scenes": [
            {
                "scene_number": scene_slot,
                "scene_ref_id": _scene_ref(form_number, scene_slot),
                "setting": f"Practice set {scene_slot}",
            }
            for scene_slot in range(1, SCENE_COUNT + 1)
        ],
        "activities": activities,
    }
    u01_learner._assert_no_answer_leak(student_form)
    return student_form


def render_form_html(student_form: Mapping[str, Any]) -> str:
    """Render one Unit02 learner Form by reusing the accepted Unit01 activity renderer."""
    form_number = int(student_form["form_ordinal"])
    activities = list(student_form["activities"])
    scenes = list(student_form["scenes"])
    if len(activities) != ACTIVITIES_PER_FORM or len(scenes) != SCENE_COUNT:
        raise Unit02FormMaterializationError(f"HTML_FORM_DENOMINATOR_DRIFT:F{form_number:02d}")

    grouped: dict[str, list[Mapping[str, Any]]] = {
        str(scene["scene_ref_id"]): [] for scene in scenes
    }
    for activity in activities:
        ref = str(activity["scene_ref_id"])
        if ref not in grouped:
            raise Unit02FormMaterializationError(
                f"HTML_ACTIVITY_SCENE_DRIFT:F{form_number:02d}:{ref}"
            )
        grouped[ref].append(activity)
    if any(len(rows) != ACTIVITIES_PER_SCENE for rows in grouped.values()):
        raise Unit02FormMaterializationError(
            f"HTML_SCENE_ACTIVITY_DENOMINATOR_DRIFT:F{form_number:02d}"
        )

    sections: list[str] = []
    fallback_number = 0
    for scene in scenes:
        ref = str(scene["scene_ref_id"])
        cards: list[str] = []
        for activity in grouped[ref]:
            fallback_number += 1
            # Reuse the accepted Unit01 learner-facing printable activity renderer.
            cards.append(u01_print._activity_html(activity, fallback_number))
        sections.append(
            '<section class="scene-section">'
            f'<h2>Practice set {int(scene["scene_number"])}</h2>'
            + "".join(cards)
            + "</section>"
        )

    html_text = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Unit02 Form {form_number:02d}</title>
<style>
@page{{size:A4;margin:10mm}}
*{{box-sizing:border-box}}
body{{font-family:Arial,"Noto Sans",sans-serif;color:#17202a;margin:0;font-size:10.5pt;line-height:1.3}}
header{{border-bottom:2px solid #26394d;margin-bottom:8px;padding-bottom:5px}}
h1{{font-size:20pt;margin:0 0 2px}}
h2{{font-size:14pt;margin:8px 0 5px;border-left:4px solid #34495e;padding:3px 7px;background:#f5f7f8}}
.scene-section{{break-inside:auto;margin-bottom:8px}}
.activity{{break-inside:avoid;border:1px solid #d5d8dc;border-radius:6px;padding:5px 7px;margin:0 0 4px}}
.activity-heading{{display:flex;align-items:center;gap:7px;margin-bottom:3px}}
.question-number{{font-weight:800}}
.skill-pill{{font-size:8pt;font-weight:700;border:1px solid #aeb6bf;border-radius:999px;padding:1px 6px}}
.stimulus{{font-size:11pt;font-weight:700;padding:4px 6px;margin:2px 0 4px;background:#f8f9f9;border-radius:4px}}
.prompt{{margin:2px 0 4px}}
.choices{{display:grid;grid-template-columns:1fr 1fr;gap:4px 10px}}
.choice{{display:flex;gap:5px;min-height:18px}}
.choice-mark{{width:12px;height:12px;border:1.4px solid #566573;border-radius:50%;display:inline-block;margin-top:2px}}
.choice-label{{font-weight:700;min-width:17px}}
.write-line{{height:16px;border-bottom:1px solid #99a3a4;margin:2px 0}}
</style>
</head>
<body>
<header>
<div>Unit02 · Regular plural nouns (-s)</div>
<h1>Form {form_number:02d}</h1>
<div>{u01_print._safe_text(student_form["progression_stage"].replace("_", " ").title())}</div>
</header>
{"".join(sections)}
</body>
</html>
"""
    lowered = html_text.casefold()
    leaked = [marker for marker in FORBIDDEN_HTML_MARKERS if marker in lowered]
    if leaked:
        raise Unit02FormMaterializationError(
            f"ENGINEERING_OR_ANSWER_MARKER_EXPORTED_TO_HTML:F{form_number:02d}:{leaked}"
        )
    return html_text


def build_materialization() -> dict[str, Any]:
    q10 = _q10()
    runtime_rows = [dict(row) for row in q10["runtime_occurrences"]]
    if len(runtime_rows) != TOTAL_ACTIVITIES:
        raise Unit02FormMaterializationError(
            f"RUNTIME_OCCURRENCE_COUNT_DRIFT:{len(runtime_rows)}"
        )
    if len({str(row["runtime_occurrence_id"]) for row in runtime_rows}) != TOTAL_ACTIVITIES:
        raise Unit02FormMaterializationError("RUNTIME_OCCURRENCE_ID_NOT_DISTINCT")

    items = _item_index(q10)
    student_forms = [
        _materialize_form(
            form_number=form_number,
            runtime_rows=runtime_rows,
            items=items,
        )
        for form_number in range(1, FORM_COUNT + 1)
    ]
    visible_activities = sum(
        int(form["learner_visible_activity_count"]) for form in student_forms
    )
    if visible_activities != TOTAL_ACTIVITIES:
        raise Unit02FormMaterializationError(
            f"MATERIALIZED_ACTIVITY_COUNT_DRIFT:{visible_activities}"
        )

    bound_rows = [
        row
        for row in runtime_rows
        if (row.get("sentence_asset_binding") or {}).get("status")
        == "BOUND_CANONICAL_Q6_SENTENCE_ASSET"
    ]
    if len(bound_rows) != Q6_BOUND_OCCURRENCES:
        raise Unit02FormMaterializationError(
            f"Q6_BOUND_OCCURRENCE_COUNT_DRIFT:{len(bound_rows)}"
        )
    # Q6 binding_text is answer-bearing lineage and must never be copied into
    # learner-safe student_form payloads.
    learner_blob = _canonical(student_forms)
    for row in bound_rows:
        binding = row["sentence_asset_binding"]
        if str(binding.get("sentence_asset_id") or "") in learner_blob:
            raise Unit02FormMaterializationError(
                f"Q6_SENTENCE_ASSET_ID_LEAK:{row['slot_id']}"
            )

    selection_identity = _selection_identity(runtime_rows)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "unit_id": UNIT_ID,
        "source_authority": {
            "u02fp01_task_id": u02fp01.TASK_ID,
            "u02qb03_task_id": q10["source_task_ids"][-1],
            "q10_package_sha256": _digest(q10),
            "unit01_learner_projection_reuse": (
                "product.a1fs_v1_2_1."
                "u01qb18a_form01_fresh_learner_materialization_export._student_activity/"
                "_assert_no_answer_leak"
            ),
            "unit01_printable_activity_renderer_reuse": (
                "product.a1fs_v1_2_1."
                "u01qb18h_r1_unit01_twelve_form_learner_pdf_materialization._activity_html"
            ),
        },
        "form_contract": {
            "form_count": FORM_COUNT,
            "scene_slots_per_form": SCENE_COUNT,
            "task_family_count": TASK_FAMILY_COUNT,
            "activities_per_scene": ACTIVITIES_PER_SCENE,
            "activities_per_form": ACTIVITIES_PER_FORM,
            "materialized_activity_count": visible_activities,
            "q10_selection_recomputed": False,
            "q10_candidate_order_mutated": False,
            "q10_selected_item_identity_mutated": False,
            "within_form_same_task_family_selected_item_reuse": False,
        },
        "student_forms": student_forms,
        "runtime_proof": {
            "source_runtime_occurrence_count": len(runtime_rows),
            "source_selection_identity_sha256": _digest(selection_identity),
            "q6_bound_occurrence_count": len(bound_rows),
            "q6_binding_used_as_hidden_lineage_only": True,
            "q6_binding_text_exported_to_learner": False,
            "restricted_surface_selected": False,
            "candidate_ids_exported_to_learner": False,
            "selected_item_ids_exported_to_learner": False,
            "questionbank_modified": False,
            "new_question_items_authored": 0,
            "parallel_selector_created": False,
            "parallel_runtime_created": False,
        },
        "claim_boundaries": {
            "learner_facing_materialization_created": True,
            "canonical_content_created": False,
            "questionbank_items_created": False,
            "sentence_assets_created": False,
            "canonical_scene_authority_created": False,
            "runtime_authority_created": False,
            "learner_state_mutated": False,
            "scoring_authority_created": False,
            "a2_unlocked": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    for form in student_forms:
        u01_learner._assert_no_answer_leak(form)
        render_form_html(form)
    return payload


def write_materialization(output_dir: Path) -> dict[str, Any]:
    payload = build_materialization()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    files: list[dict[str, Any]] = []
    for form in payload["student_forms"]:
        ordinal = int(form["form_ordinal"])
        stem = f"Unit02_Form{ordinal:02d}"
        json_path = output_dir / f"{stem}.student.json"
        html_path = output_dir / f"{stem}.html"
        json_bytes = (_canonical(form) + "\n").encode("utf-8")
        html_bytes = render_form_html(form).encode("utf-8")
        json_path.write_bytes(json_bytes)
        html_path.write_bytes(html_bytes)
        files.extend(
            [
                {
                    "name": json_path.name,
                    "bytes": len(json_bytes),
                    "sha256": hashlib.sha256(json_bytes).hexdigest(),
                },
                {
                    "name": html_path.name,
                    "bytes": len(html_bytes),
                    "sha256": hashlib.sha256(html_bytes).hexdigest(),
                },
            ]
        )
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "unit_id": UNIT_ID,
        "form_contract": payload["form_contract"],
        "runtime_proof": payload["runtime_proof"],
        "claim_boundaries": payload["claim_boundaries"],
        "files": files,
        "next_short_step": NEXT_SHORT_STEP,
    }
    manifest_path = output_dir / "Unit02_Form01_16_Materialization_Manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    manifest = write_materialization(args.output_dir)
    contract = manifest["form_contract"]
    print(f"STATUS={PASS_STATUS}")
    print(f"FORMS={contract['form_count']}")
    print(f"SCENE_SLOTS_PER_FORM={contract['scene_slots_per_form']}")
    print(f"TASK_FAMILIES={contract['task_family_count']}")
    print(f"ACTIVITIES_PER_FORM={contract['activities_per_form']}")
    print(f"MATERIALIZED_ACTIVITIES={contract['materialized_activity_count']}")
    print(f"Q6_BOUND_OCCURRENCES={manifest['runtime_proof']['q6_bound_occurrence_count']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
