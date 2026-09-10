from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from product.a1fs_v1_2_1 import (
    u01qb18h_r1_unit01_twelve_form_learner_pdf_materialization as u01_pdf,
)
from product.a1fs_v1_2_1 import (
    u04fsv2_current360_contextual_form_runtime as fsv2,
)
from product.a1fs_v1_2_1 import (
    u04q10r1_unit04_learner_facing_pedagogical_acceptance as learner_renderer,
)
from product.a1fs_v1_2_1 import (
    u04q10r2_unit04_learner_pdf_materialization_and_visual_acceptance as q10r2,
)
from product.a1fs_v1_2_1 import (
    u04q10r2r1_unit04_actual_pdf_pagination_repair as pagination,
)
from product.a1fs_v1_2_1 import (
    u04rswv2_productive_scoring_cambridge_progression_acceptance as rswv2,
)
from product.a1fs_v1_2_1 import (
    u04spv2_current360_speaking_cutover as spv2,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Read-only learner presentation and PDF machine-acceptance adapter over the "
    "already-active Unit04 FSV2 and SPV2 Current360 runtimes. Reuses the existing "
    "Unit04 learner HTML renderer, Unit01/Q10R2 Chromium runner and Q10R2R1 print "
    "pagination guard. Creates no QuestionBank, sentence, scene, passage, selector, "
    "scoring, listening, Cambridge, A2/A2+, or parallel renderer authority."
)

PROGRAM_ID = "A1FS-V1"
UNIT_ID = "GRAMMAR_BASIC_PREPOSITIONS_PLACE"
TASK_ID = "A1FS-V1-U04VAV2_Current360LearnerFacingVisualPedagogicalAcceptance"
STATUS = (
    "PASS_A1FS_V1_U04VAV2_CURRENT360_LEARNER_FACING_VISUAL_"
    "PEDAGOGICAL_MACHINE_ACCEPTANCE"
)
REVISION = "CURRENT360_LEARNER_PRESENTATION_PDF_MACHINE_ACCEPTANCE_V2"
SCHEMA_VERSION = "a1fs.v1.u04.vav2.current360_visual_pedagogical_acceptance.v1"
NEXT_SHORT_STEP = (
    "A1FS-V1-U04VAV2R1_Current360ActualPdfHumanVisualPedagogicalAcceptance"
)

FORM_COUNT = 20
ACTIVITIES_PER_FORM = 40
TOTAL_ACTIVITIES = 800
SPEAKING_TASK_COUNT = 240
SECTION_ORDER = ("A", "B", "C", "D", "E")
MANIFEST_NAME = "unit04_current360_form01_20_visual_acceptance.private.json"
DEFAULT_OUTPUT_ROOT = Path(
    ".local/a1fs_v1/review/unit04_current360_form01_20_visual_acceptance"
)


class Unit04VAV2Error(ValueError):
    pass


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _source_reports(
    *,
    form_report: Mapping[str, Any] | None = None,
    speaking_report: Mapping[str, Any] | None = None,
    rsw_report: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    forms = dict(
        form_report or fsv2.build_unit04_fsv2_current360_contextual_form_runtime()
    )
    speaking = dict(
        speaking_report or spv2.build_unit04_spv2_speaking_layer1_bridge_layer2_cutover()
    )
    scoring = dict(
        rsw_report
        or rswv2.build_unit04_rswv2_productive_scoring_cambridge_progression_acceptance()
    )

    if forms.get("status") != fsv2.STATUS:
        raise Unit04VAV2Error("FSV2_SOURCE_NOT_PASS")
    if (
        forms.get("cutover_contract", {}).get("active_form_runtime_authority")
        != fsv2.TASK_ID
    ):
        raise Unit04VAV2Error("FSV2_NOT_ACTIVE_FORM_RUNTIME")
    if (
        forms.get("cutover_contract", {}).get("parallel_active_form_runtime_allowed")
        is not False
    ):
        raise Unit04VAV2Error("FSV2_PARALLEL_FORM_RUNTIME_ALLOWED")

    if speaking.get("status") != spv2.STATUS:
        raise Unit04VAV2Error("SPV2_SOURCE_NOT_PASS")
    if (
        speaking.get("cutover_contract", {}).get("active_speaking_runtime_authority")
        != spv2.TASK_ID
    ):
        raise Unit04VAV2Error("SPV2_NOT_ACTIVE_SPEAKING_RUNTIME")
    if (
        speaking.get("cutover_contract", {}).get(
            "parallel_active_speaking_runtime_allowed"
        )
        is not False
    ):
        raise Unit04VAV2Error("SPV2_PARALLEL_SPEAKING_RUNTIME_ALLOWED")
    if speaking.get("source_authority", {}).get("active_form_runtime") != fsv2.TASK_ID:
        raise Unit04VAV2Error("SPV2_FSV2_LINEAGE_DRIFT")

    if scoring.get("status") != rswv2.STATUS:
        raise Unit04VAV2Error("RSWV2_SOURCE_NOT_PASS")
    if scoring.get("next_short_step") != TASK_ID:
        raise Unit04VAV2Error(
            f"RSWV2_NEXT_STEP_DRIFT:{scoring.get('next_short_step')}:{TASK_ID}"
        )
    requirement_10 = (
        scoring.get("approved_requirements_10_of_10", {})
        .get("10_learner_facing_visual_pedagogical_acceptance", {})
    )
    if requirement_10.get("status") != "PENDING_NEXT_SHORT_STEP":
        raise Unit04VAV2Error(
            f"RSWV2_VISUAL_GATE_STATE_DRIFT:{requirement_10.get('status')}"
        )

    return forms, speaking, scoring


def _project_learner_forms(form_report: Mapping[str, Any]) -> list[dict[str, Any]]:
    source_forms = list(form_report.get("forms") or [])
    source_items = list(form_report.get("active_items") or [])
    if len(source_forms) != FORM_COUNT or len(source_items) != TOTAL_ACTIVITIES:
        raise Unit04VAV2Error(
            f"FSV2_DENOMINATOR_DRIFT:{len(source_forms)}:{len(source_items)}"
        )

    item_index = {str(row["active_item_id"]): row for row in source_items}
    if len(item_index) != TOTAL_ACTIVITIES:
        raise Unit04VAV2Error("FSV2_ACTIVE_ITEM_ID_COLLISION")

    forms: list[dict[str, Any]] = []
    for expected_number, source_form in enumerate(source_forms, start=1):
        form_number = int(source_form.get("form_number", -1))
        if form_number != expected_number:
            raise Unit04VAV2Error(
                f"FSV2_FORM_SEQUENCE_DRIFT:{form_number}:{expected_number}"
            )
        stage = str(source_form.get("progression_stage") or "")
        if stage not in fsv2.STAGE_CONTRACT:
            raise Unit04VAV2Error(f"FSV2_FORM_STAGE_UNKNOWN:F{form_number:02d}:{stage}")

        active_ids = [str(value) for value in source_form.get("active_item_ids") or []]
        if len(active_ids) != ACTIVITIES_PER_FORM:
            raise Unit04VAV2Error(
                f"FSV2_FORM_ACTIVITY_DENOMINATOR_DRIFT:F{form_number:02d}:{len(active_ids)}"
            )
        activities: list[dict[str, Any]] = []
        for question_number, active_id in enumerate(active_ids, start=1):
            item = item_index.get(active_id)
            if item is None:
                raise Unit04VAV2Error(f"FSV2_ACTIVE_ITEM_UNRESOLVED:{active_id}")
            if int(item["form_number"]) != form_number:
                raise Unit04VAV2Error(f"FSV2_ITEM_FORM_DRIFT:{active_id}")
            activity = dict(item.get("learner_activity") or {})
            activity["options"] = [str(value) for value in activity.get("options") or []]
            if activity.get("question_number") != f"Q{question_number:02d}":
                raise Unit04VAV2Error(
                    f"LEARNER_QUESTION_SEQUENCE_DRIFT:{active_id}:"
                    f"{activity.get('question_number')}:Q{question_number:02d}"
                )
            if not str(activity.get("stimulus") or "").strip():
                raise Unit04VAV2Error(f"LEARNER_STIMULUS_MISSING:{active_id}")
            if not str(activity.get("prompt") or "").strip():
                raise Unit04VAV2Error(f"LEARNER_PROMPT_MISSING:{active_id}")
            response_mode = str(activity.get("response_mode") or "")
            if response_mode not in {"select_one", "short_text"}:
                raise Unit04VAV2Error(
                    f"LEARNER_RESPONSE_MODE_INVALID:{active_id}:{response_mode}"
                )
            if activity["options"] and response_mode != "select_one":
                raise Unit04VAV2Error(f"LEARNER_OPTIONS_MODE_DRIFT:{active_id}")
            if not activity["options"] and response_mode != "short_text":
                raise Unit04VAV2Error(f"LEARNER_CONSTRUCTED_MODE_DRIFT:{active_id}")
            forbidden = fsv2.FORBIDDEN_LEARNER_KEYS.intersection(activity)
            if forbidden:
                raise Unit04VAV2Error(
                    f"LEARNER_PRIVATE_KEY_VISIBLE:{active_id}:{sorted(forbidden)}"
                )
            activities.append(activity)

        sections = []
        source_sections = list(source_form.get("sections") or [])
        if [str(row.get("section") or "") for row in source_sections] != list(
            SECTION_ORDER
        ):
            raise Unit04VAV2Error(f"FSV2_SECTION_ORDER_DRIFT:F{form_number:02d}")
        for section in source_sections:
            section_id = str(section["section"])
            expected_count = fsv2.SECTION_COUNTS[section_id]
            if int(section.get("activity_count", -1)) != expected_count:
                raise Unit04VAV2Error(
                    f"FSV2_SECTION_COUNT_DRIFT:F{form_number:02d}:{section_id}"
                )
            sections.append(
                {
                    "section": section_id,
                    "section_name": str(section["section_title"]),
                    "activity_count": expected_count,
                }
            )

        form = {
            "unit_id": UNIT_ID,
            "unit_ordinal": 4,
            "form_id": f"U04VAV2-F{form_number:02d}",
            "form_ordinal": form_number,
            "progression_stage": stage,
            "section_count": len(sections),
            "learner_visible_activity_count": len(activities),
            "sections": sections,
            "activities": activities,
        }
        html = learner_renderer.render_form_html(form)
        if html.count('<article class="activity">') != ACTIVITIES_PER_FORM:
            raise Unit04VAV2Error(
                f"LEARNER_HTML_ACTIVITY_COUNT_DRIFT:F{form_number:02d}"
            )
        forms.append(form)
    return forms


def _validate_form_presentation(
    form_report: Mapping[str, Any], learner_forms: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    if len(learner_forms) != FORM_COUNT:
        raise Unit04VAV2Error(f"LEARNER_FORM_COUNT_DRIFT:{len(learner_forms)}")
    flattened = [
        activity
        for form in learner_forms
        for activity in form.get("activities") or []
    ]
    if len(flattened) != TOTAL_ACTIVITIES:
        raise Unit04VAV2Error(
            f"LEARNER_ACTIVITY_COUNT_DRIFT:{len(flattened)}:{TOTAL_ACTIVITIES}"
        )
    source_flattened = [
        dict(item.get("learner_activity") or {})
        for item in form_report.get("active_items") or []
    ]
    if _digest(flattened) != _digest(source_flattened):
        raise Unit04VAV2Error("FSV2_LEARNER_ACTIVITY_PRESENTATION_MUTATED")

    stage_counts = Counter(
        str(form["progression_stage"]) for form in learner_forms
    )
    expected_stage_counts = {stage: 4 for stage in fsv2.STAGE_CONTRACT}
    if dict(stage_counts) != expected_stage_counts:
        raise Unit04VAV2Error(
            f"LEARNER_FORM_STAGE_DISTRIBUTION_DRIFT:{dict(stage_counts)}"
        )

    rendered = [learner_renderer.render_form_html(form) for form in learner_forms]
    pagination_rendered = [
        pagination.inject_pdf_pagination_guards(html) for html in rendered
    ]
    if any(
        html.count(pagination.PDF_PAGINATION_STYLE_ID) != 1
        for html in pagination_rendered
    ):
        raise Unit04VAV2Error("PAGINATION_GUARD_INJECTION_DRIFT")
    if len({_digest(html) for html in rendered}) != FORM_COUNT:
        raise Unit04VAV2Error("LEARNER_HTML_FORM_IDENTITY_COLLISION")

    response_counts = Counter(
        str(activity["response_mode"]) for activity in flattened
    )
    skill_counts = Counter(str(activity["skill"]) for activity in flattened)
    return {
        "form_count": FORM_COUNT,
        "activity_count": TOTAL_ACTIVITIES,
        "activities_per_form": ACTIVITIES_PER_FORM,
        "rendered_html_form_count": len(rendered),
        "pagination_guarded_html_form_count": len(pagination_rendered),
        "stage_form_counts": dict(stage_counts),
        "response_mode_counts": dict(sorted(response_counts.items())),
        "skill_counts": dict(sorted(skill_counts.items())),
        "learner_activity_identity_sha256": _digest(flattened),
        "renderer_authority": (
            "product.a1fs_v1_2_1."
            "u04q10r1_unit04_learner_facing_pedagogical_acceptance.render_form_html"
        ),
        "activity_card_renderer_authority": (
            "product.a1fs_v1_2_1."
            "u01qb18h_r1_unit01_twelve_form_learner_pdf_materialization._activity_html"
        ),
        "pagination_guard_authority": pagination.TASK_ID,
        "second_renderer_created": False,
    }


def _validate_speaking_surface(speaking_report: Mapping[str, Any]) -> dict[str, Any]:
    bridge = list(speaking_report.get("bridge_tasks") or [])
    layer2 = list(speaking_report.get("layer2_connected_speaking") or [])
    rows = bridge + layer2
    if (len(bridge), len(layer2), len(rows)) != (80, 160, SPEAKING_TASK_COUNT):
        raise Unit04VAV2Error(
            f"SPV2_DENOMINATOR_DRIFT:{len(bridge)}:{len(layer2)}:{len(rows)}"
        )
    active_ids = {
        str(row["speaking_task_id"]) for row in rows
    }
    if len(active_ids) != SPEAKING_TASK_COUNT:
        raise Unit04VAV2Error("SPV2_SPEAKING_TASK_ID_COLLISION")

    mode_counts: Counter[str] = Counter()
    stage_counts: Counter[str] = Counter()
    source_item_ids: set[str] = set()
    for row in rows:
        task_id = str(row["speaking_task_id"])
        prompt = str(row.get("learner_prompt") or "").strip()
        stimulus = dict(row.get("learner_stimulus") or {})
        passage = str(stimulus.get("passage") or "").strip()
        support = str(stimulus.get("support") or "").strip()
        if not prompt:
            raise Unit04VAV2Error(f"SPV2_LEARNER_PROMPT_MISSING:{task_id}")
        if not passage:
            raise Unit04VAV2Error(f"SPV2_LEARNER_PASSAGE_MISSING:{task_id}")
        if not support:
            raise Unit04VAV2Error(f"SPV2_LEARNER_SUPPORT_MISSING:{task_id}")
        scoring = dict(row.get("scoring_contract") or {})
        if scoring.get("scoring_mode") != "HUMAN_OR_SEMANTIC_REVIEW":
            raise Unit04VAV2Error(f"SPV2_SCORING_MODE_DRIFT:{task_id}")
        if scoring.get("single_answer_required") is not False:
            raise Unit04VAV2Error(f"SPV2_SINGLE_ANSWER_REQUIRED:{task_id}")
        if scoring.get("reference_response_nonexclusive") is not True:
            raise Unit04VAV2Error(f"SPV2_REFERENCE_RESPONSE_EXCLUSIVE:{task_id}")
        if scoring.get("acceptable_paraphrase") is not True:
            raise Unit04VAV2Error(f"SPV2_PARAPHRASE_REJECTED:{task_id}")
        if scoring.get("audio_pronunciation_machine_score_required") is not False:
            raise Unit04VAV2Error(f"SPV2_MACHINE_PRONUNCIATION_REQUIRED:{task_id}")
        if row.get("a2_grammar_introduced") is not False:
            raise Unit04VAV2Error(f"SPV2_A2_GRAMMAR_LEAK:{task_id}")
        if row.get("support_relations_assessed") is not False:
            raise Unit04VAV2Error(f"SPV2_SUPPORT_RELATION_PROMOTED:{task_id}")
        lineage = dict(row.get("source_form_runtime_lineage") or {})
        source_item_id = str(lineage.get("fsv2_active_item_id") or "")
        if not source_item_id:
            raise Unit04VAV2Error(f"SPV2_FSV2_LINEAGE_MISSING:{task_id}")
        source_item_ids.add(source_item_id)
        mode_counts[str(row["speaking_mode"])] += 1
        stage_counts[str(row["progression_stage"])] += 1

    expected_stage_counts = {stage: 48 for stage in fsv2.STAGE_CONTRACT}
    if dict(stage_counts) != expected_stage_counts:
        raise Unit04VAV2Error(
            f"SPV2_STAGE_DISTRIBUTION_DRIFT:{dict(stage_counts)}"
        )
    return {
        "bridge_task_count": len(bridge),
        "layer2_task_count": len(layer2),
        "learner_speaking_prompt_count": len(rows),
        "distinct_speaking_mode_count": len(mode_counts),
        "speaking_mode_counts": dict(sorted(mode_counts.items())),
        "stage_task_counts": dict(stage_counts),
        "distinct_fsv2_source_item_count": len(source_item_ids),
        "all_prompts_nonempty": True,
        "all_current360_passages_nonempty": True,
        "semantic_scoring_preserved": True,
        "acceptable_paraphrase_preserved": True,
        "machine_pronunciation_score_required": False,
        "speaking_pdf_renderer_created": False,
        "human_speaking_prompt_review_claimed": False,
    }


def build_unit04_vav2_current360_visual_machine_acceptance(
    *,
    form_report: Mapping[str, Any] | None = None,
    speaking_report: Mapping[str, Any] | None = None,
    rsw_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    forms, speaking, scoring = _source_reports(
        form_report=form_report,
        speaking_report=speaking_report,
        rsw_report=rsw_report,
    )
    source_form_hash = str(forms.get("deterministic_runtime_sha256") or "")
    source_speaking_hash = str(speaking.get("deterministic_speaking_sha256") or "")
    if not source_form_hash:
        raise Unit04VAV2Error("FSV2_DETERMINISTIC_IDENTITY_MISSING")
    if not source_speaking_hash:
        source_speaking_hash = _digest(
            {
                "bridge_tasks": speaking.get("bridge_tasks") or [],
                "layer2_connected_speaking": speaking.get(
                    "layer2_connected_speaking"
                )
                or [],
            }
        )

    learner_forms = _project_learner_forms(forms)
    form_acceptance = _validate_form_presentation(forms, learner_forms)
    speaking_acceptance = _validate_speaking_surface(speaking)

    if forms.get("coverage", {}).get("selected_seen_unseen_overlap_count") != 0:
        raise Unit04VAV2Error("FSV2_SEEN_UNSEEN_OVERLAP")
    if forms.get("coverage", {}).get("assessed_support_relation_count") != 0:
        raise Unit04VAV2Error("FSV2_SUPPORT_RELATION_ASSESSED")
    if forms.get("coverage", {}).get("a2_grammar_introduced_count") != 0:
        raise Unit04VAV2Error("FSV2_A2_GRAMMAR_INTRODUCED")
    if speaking.get("coverage", {}).get("seen_unseen_overlap_count") != 0:
        raise Unit04VAV2Error("SPV2_SEEN_UNSEEN_OVERLAP")

    requirement_10_progress = {
        "machine_learner_form_presentation": "PASS",
        "machine_pdf_materialization_contract": "PASS",
        "machine_spv2_learner_prompt_surface": "PASS",
        "actual_pdf_human_visual_review": "PENDING",
        "actual_human_pedagogical_review": "PENDING",
        "human_speaking_prompt_review": "PENDING",
        "full_requirement_10_closed": False,
    }
    result = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "unit_id": UNIT_ID,
        "unit_number": 4,
        "task_id": TASK_ID,
        "status": STATUS,
        "revision": REVISION,
        "source_authority": {
            "active_form_runtime": fsv2.TASK_ID,
            "active_speaking_runtime": spv2.TASK_ID,
            "productive_scoring_progression_acceptance": rswv2.TASK_ID,
            "learner_html_renderer_reused": learner_renderer.TASK_ID,
            "chromium_pdf_runner_reused": q10r2.TASK_ID,
            "pdf_pagination_guard_reused": pagination.TASK_ID,
        },
        "source_identity": {
            "fsv2_deterministic_runtime_sha256": source_form_hash,
            "spv2_deterministic_speaking_sha256": source_speaking_hash,
        },
        "machine_acceptance": {
            "learner_forms": form_acceptance,
            "speaking_surface": speaking_acceptance,
            "seen_unseen_overlap_count": 0,
            "support_relation_assessed_count": 0,
            "a2_grammar_introduced_count": 0,
        },
        "learner_forms": learner_forms,
        "requirement_10_progress": requirement_10_progress,
        "human_review": {
            "actual_pdf_visual_review_claimed": False,
            "actual_pedagogical_review_claimed": False,
            "speaking_prompt_human_review_claimed": False,
            "status": "PENDING_EXACT_RENDERED_EVIDENCE",
        },
        "safety": {
            "acceptance_only_no_new_learner_content": True,
            "fsv2_runtime_modified": False,
            "spv2_runtime_modified": False,
            "current360_episode_content_modified": False,
            "q01_q10_authority_modified": False,
            "questionbank_modified": False,
            "sentence_assets_modified": False,
            "scene_authority_modified": False,
            "second_form_renderer_created": False,
            "second_speaking_renderer_created": False,
            "scoring_authority_modified": False,
            "listening_modified": False,
            "support_relations_promoted_to_assessed_target": False,
            "a2_a2plus_unlocked": False,
            "other_units_modified": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    result["deterministic_acceptance_sha256"] = _digest(
        {
            "source_authority": result["source_authority"],
            "source_identity": result["source_identity"],
            "machine_acceptance": result["machine_acceptance"],
            "requirement_10_progress": result["requirement_10_progress"],
            "human_review": result["human_review"],
            "safety": result["safety"],
            "next_short_step": result["next_short_step"],
        }
    )
    return result


def materialize_current360_twenty_form_pdfs(
    *,
    output_root: Path,
    chromium_path: Path | None = None,
    browser_runner: Callable[..., Mapping[str, Any]] | None = None,
    pdf_page_counter: Callable[[Path], int] | None = None,
    acceptance_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    report = dict(
        acceptance_report or build_unit04_vav2_current360_visual_machine_acceptance()
    )
    if report.get("status") != STATUS:
        raise Unit04VAV2Error(f"VAV2_ACCEPTANCE_STATUS_INVALID:{report.get('status')}")
    if report.get("task_id") != TASK_ID:
        raise Unit04VAV2Error(f"VAV2_ACCEPTANCE_TASK_INVALID:{report.get('task_id')}")

    learner_forms = list(report.get("learner_forms") or [])
    if len(learner_forms) != FORM_COUNT:
        raise Unit04VAV2Error(
            f"VAV2_ACCEPTANCE_FORM_COUNT_DRIFT:{len(learner_forms)}"
        )

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
    for ordinal, form in enumerate(learner_forms, start=1):
        html_path = html_root / f"Form{ordinal:02d}.html"
        pdf_path = pdf_root / f"Form{ordinal:02d}.pdf"
        source_html = learner_renderer.render_form_html(form)
        printable_html = pagination.inject_pdf_pagination_guards(source_html)
        u01_pdf._atomic_text(html_path, printable_html)
        html_identity = q10r2._file_identity(html_path)

        render_result = dict(
            run_browser(
                chromium,
                source_html=html_path,
                output_path=pdf_path,
                mode="PDF",
            )
        )
        if not pdf_path.is_file():
            raise Unit04VAV2Error(f"PDF_OUTPUT_MISSING:F{ordinal:02d}")
        pdf_identity = q10r2._file_identity(pdf_path)
        if pdf_identity["bytes"] < 1024:
            raise Unit04VAV2Error(
                f"PDF_OUTPUT_TOO_SMALL:F{ordinal:02d}:{pdf_identity['bytes']}"
            )
        page_count = int(count_pages(pdf_path))
        if page_count < 1:
            raise Unit04VAV2Error(
                f"PDF_PAGE_COUNT_INVALID:F{ordinal:02d}:{page_count}"
            )
        artifacts.append(
            {
                "form_id": str(form["form_id"]),
                "form_ordinal": ordinal,
                "progression_stage": str(form["progression_stage"]),
                "html_relative_path": f"html/Form{ordinal:02d}.html",
                "pdf_relative_path": f"pdf/Form{ordinal:02d}.pdf",
                "html_bytes": html_identity["bytes"],
                "html_sha256": html_identity["sha256"],
                "pdf_bytes": pdf_identity["bytes"],
                "pdf_sha256": pdf_identity["sha256"],
                "page_count": page_count,
                "learner_visible_activity_count": ACTIVITIES_PER_FORM,
                "machine_preflight": "PASS",
                "learner_facing_machine_acceptance": "PASS",
                "human_visual_review": "PENDING",
                "human_pedagogical_review": "PENDING",
                "browser_render": {
                    key: value
                    for key, value in render_result.items()
                    if key not in {"source_path", "output_path"}
                },
            }
        )

    if len(artifacts) != FORM_COUNT:
        raise Unit04VAV2Error(
            f"MATERIALIZED_PDF_COUNT_DRIFT:{len(artifacts)}:{FORM_COUNT}"
        )
    if len({row["pdf_sha256"] for row in artifacts}) != FORM_COUNT:
        raise Unit04VAV2Error("PDF_SHA256_NOT_DISTINCT")

    manifest = {
        "schema_version": (
            "a1fs.v1.u04.vav2.current360_pdf_materialization_manifest.v1"
        ),
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "validation_status": STATUS,
        "source_acceptance_sha256": report["deterministic_acceptance_sha256"],
        "source_identity": report["source_identity"],
        "form_count": FORM_COUNT,
        "materialized_html_count": FORM_COUNT,
        "materialized_pdf_count": FORM_COUNT,
        "materialized_activity_count": TOTAL_ACTIVITIES,
        "speaking_prompt_machine_acceptance_count": SPEAKING_TASK_COUNT,
        "machine_preflight_pass_count": FORM_COUNT,
        "learner_facing_machine_acceptance_pass_count": FORM_COUNT,
        "human_visual_review_pending_count": FORM_COUNT,
        "human_pedagogical_review_pending_count": FORM_COUNT,
        "human_speaking_prompt_review_pending_count": SPEAKING_TASK_COUNT,
        "unit04_current360_pdf_machine_acceptance": (
            "PASS_MACHINE_LEARNER_FACING_ACCEPTANCE"
        ),
        "unit04_current360_human_acceptance": (
            "PENDING_HUMAN_VISUAL_PEDAGOGICAL_REVIEW"
        ),
        "existing_learner_html_renderer_reused": True,
        "existing_chromium_pdf_runner_reused": True,
        "existing_pagination_guard_reused": True,
        "second_renderer_created": False,
        "current360_episode_content_modified": False,
        "fsv2_runtime_modified": False,
        "spv2_runtime_modified": False,
        "scoring_authority_modified": False,
        "listening_modified": False,
        "a2_a2plus_unlocked": False,
        "artifacts": artifacts,
        "next_short_step": NEXT_SHORT_STEP,
    }
    u01_pdf._atomic_json(output_root / MANIFEST_NAME, manifest)
    return manifest


def compact_readback(report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": report["status"],
        "revision": report["revision"],
        "source_authority": report["source_authority"],
        "source_identity": report["source_identity"],
        "machine_acceptance": report["machine_acceptance"],
        "requirement_10_progress": report["requirement_10_progress"],
        "human_review": report["human_review"],
        "safety": report["safety"],
        "next_short_step": report["next_short_step"],
        "deterministic_acceptance_sha256": report[
            "deterministic_acceptance_sha256"
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    del argv
    report = build_unit04_vav2_current360_visual_machine_acceptance()
    print(json.dumps(compact_readback(report), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
