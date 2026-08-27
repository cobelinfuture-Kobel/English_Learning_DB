#!/usr/bin/env python3
"""Unit03 Forms01..20 learner-facing acceptance over the locked 800 bindings.

R1 consumes the already-approved U03SCFV2 20x40 materialization.  It does not
regenerate, reselect, or rewrite any runtime binding, candidate identity,
QuestionBank item, SentenceAsset, Q6/Q9/Q10 authority, selector, learner state,
or scoring authority.  It reuses the accepted Unit01 learner activity renderer
and applies two presentation-only corrections found by learner-facing review:

* REFERENCE_CHAIN masks the already-selected subject pronoun in sentence two so
  the answer is not printed in the stimulus.
* PRONOUN_REFERENT_MATCH removes a plain-name distractor when it is semantically
  identical to the qualified correct referent for I/You/We.

The resulting Forms01..20 are then fail-closed checked across all 800 learner
activities and rendered through the existing Unit01 activity HTML renderer.
"""
from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from typing import Any, Mapping, Sequence

from product.a1fs_v1_2_1 import (
    u01qb18h_r1_unit01_twelve_form_learner_pdf_materialization as u01_pdf,
)
from ulga.builders import (
    build_a1fs_v1_u03scfv2_unit03_sentence_competence_forms_v2_800_materialization
    as u03,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Product-level learner-facing acceptance consumer over the already-approved "
    "U03SCFV2 20x40 runtime. It preserves all 800 runtime/selected/candidate "
    "identities and reuses the accepted Unit01 learner activity HTML renderer. "
    "It only removes presentation answer leakage and semantically duplicate "
    "referent choices; it creates no QuestionBank/SentenceAsset/canonical pattern, "
    "selector, runtime, learner-state, scoring, Q6/Q9/Q10, Unit04-24, or A2 authority."
)

PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U03SCFV2R1_Unit03TwentyFormLearnerFacingAcceptance"
SCHEMA_VERSION = "a1fs.v1.u03scfv2r1.twenty_form_learner_facing_acceptance.v1"
PASS_STATUS = "PASS_A1FS_V1_U03SCFV2R1_UNIT03_TWENTY_FORM_LEARNER_FACING_ACCEPTANCE"

FORM_COUNT = 20
ACTIVITIES_PER_FORM = 40
TOTAL_ACTIVITIES = 800
SECTIONS_PER_FORM = 5
ACTIVITIES_PER_SECTION = 8
REFERENCE_CHAIN_COUNT = 80
REFERENT_DEDUP_FIX_COUNT = 35

SECTION_ORDER = [section for section, _ in u03.SECTION_FAMILIES]
ALLOWED_RESPONSE_MODES = frozenset({"select_one", "ordered_tokens", "short_text", "practice_only"})
FORBIDDEN_LEARNER_MARKERS = (
    "selected_item_id",
    "candidate_ids",
    "runtime_occurrence_id",
    "questionbank_item_id",
    "source_refs",
    "correct_answer",
    "accepted_answers",
    "response_contract",
    "semantic_signature",
    "unit03_q6",
    "unit03_q9",
    "unit02_q10",
    "q10_questionbank",
)


class Unit03LearnerFacingAcceptanceError(ValueError):
    """Fail-closed Unit03 learner-facing acceptance defect."""


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _runtime_identity(runtime: Sequence[Mapping[str, Any]]) -> str:
    return _digest([
        {
            "slot_id": row["slot_id"],
            "runtime_occurrence_id": row["runtime_occurrence_id"],
            "candidate_ids": list(row["candidate_ids"]),
            "selected_item_id": row["selected_item_id"],
            "questionbank_item_id": row["questionbank_item_id"],
            "questionbank_source": row["questionbank_source"],
        }
        for row in runtime
    ])


def _referent_key(value: Any) -> str:
    text = re.sub(r"\s*\([^)]*\)\s*", " ", str(value or "").strip())
    return re.sub(r"\s+", " ", text).strip().casefold()


def _dedupe_referent_options(options: Sequence[Any], correct: str) -> list[str]:
    result: list[str] = []
    seen_semantic: set[str] = set()
    ordered = [str(correct)] + [str(value) for value in options if str(value) != str(correct)]
    for value in ordered:
        key = _referent_key(value)
        if key and key not in seen_semantic:
            seen_semantic.add(key)
            result.append(value)
    if correct not in result or len(result) < 3:
        raise Unit03LearnerFacingAcceptanceError(
            f"REFERENT_OPTIONS_NOT_ANSWERABLE:{correct}:{result}"
        )
    return result


def _mask_reference_chain(stimulus: str, pronoun: str) -> str:
    marker = f"{pronoun} "
    head, separator, tail = str(stimulus).rpartition(marker)
    if not separator:
        raise Unit03LearnerFacingAcceptanceError(
            f"REFERENCE_CHAIN_TARGET_PRONOUN_NOT_FOUND:{pronoun}:{stimulus}"
        )
    masked = f"{head}___ {tail}"
    if masked == stimulus or "___ " not in masked:
        raise Unit03LearnerFacingAcceptanceError("REFERENCE_CHAIN_MASK_FAILED")
    return masked


def _source_contract(payload: Mapping[str, Any]) -> None:
    if str(payload.get("status") or "") != u03.PASS_STATUS:
        raise Unit03LearnerFacingAcceptanceError(
            f"SOURCE_STATUS_INVALID:{payload.get('status')}"
        )
    contract = payload.get("runtime_form_contract") or {}
    expected = {
        "form_count": FORM_COUNT,
        "activities_per_form": ACTIVITIES_PER_FORM,
        "runtime_occurrence_count": TOTAL_ACTIVITIES,
        "inherited_runtime_binding_count": 400,
        "unit03_delta_runtime_binding_count": 400,
        "sections_per_form": SECTIONS_PER_FORM,
        "activities_per_section": ACTIVITIES_PER_SECTION,
        "candidate_count_per_slot": 3,
    }
    for key, value in expected.items():
        if int(contract.get(key, -1)) != value:
            raise Unit03LearnerFacingAcceptanceError(
                f"SOURCE_CONTRACT_DRIFT:{key}:{contract.get(key)}:{value}"
            )
    if contract.get("global_800_distinct_selected_item_proof") is not True:
        raise Unit03LearnerFacingAcceptanceError("SOURCE_GLOBAL_800_DISTINCTNESS_NOT_PROVEN")
    boundaries = payload.get("claim_boundaries") or {}
    if any(boundaries.get(key) is not False for key in (
        "unit02_forms01_16_mutated",
        "unit01_unit02_questionbank_items_mutated",
        "second_questionbank_authority_created",
        "second_selector_created",
        "second_renderer_created",
        "parallel_sentence_asset_schema_created",
        "canonical_sentence_pattern_authority_mutated",
        "learner_state_mutated",
        "a2_unlocked",
    )):
        raise Unit03LearnerFacingAcceptanceError("SOURCE_CLAIM_BOUNDARY_DRIFT")


def _project_forms(payload: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    source_forms = list(payload.get("student_forms") or [])
    runtime = list(payload.get("runtime_bindings") or [])
    new_items = list((payload.get("questionbank_delta") or {}).get("unit03_new_items") or [])
    if len(source_forms) != FORM_COUNT or len(runtime) != TOTAL_ACTIVITIES:
        raise Unit03LearnerFacingAcceptanceError("SOURCE_FORM_OR_RUNTIME_DENOMINATOR_INVALID")
    item_index = {str(row["item_id"]): row for row in new_items}
    if len(item_index) != 400:
        raise Unit03LearnerFacingAcceptanceError("SOURCE_UNIT03_ITEM_INDEX_INVALID")

    forms = deepcopy(source_forms)
    chain_fixes = 0
    referent_fixes = 0
    for form_number, form in enumerate(forms, start=1):
        rows = [row for row in runtime if int(row["form_number"]) == form_number]
        activities = list(form.get("activities") or [])
        if len(rows) != ACTIVITIES_PER_FORM or len(activities) != ACTIVITIES_PER_FORM:
            raise Unit03LearnerFacingAcceptanceError(
                f"FORM_RUNTIME_ALIGNMENT_INVALID:F{form_number:02d}"
            )
        for runtime_row, activity in zip(rows, activities):
            if runtime_row.get("questionbank_source") != "UNIT03_DELTA":
                continue
            item = item_index.get(str(runtime_row["selected_item_id"]))
            if item is None:
                raise Unit03LearnerFacingAcceptanceError(
                    f"UNIT03_SELECTED_ITEM_MISSING:{runtime_row['selected_item_id']}"
                )
            family = str(item["task_family"])
            correct = str(item["correct_answer"])
            pronoun = str((item.get("lexical_slots") or {}).get("subject_pronoun") or "")
            if family == "PRONOUN_REFERENT_MATCH":
                before = [str(value) for value in activity.get("options") or []]
                after = _dedupe_referent_options(before, correct)
                if after != before:
                    activity["options"] = after
                    referent_fixes += 1
            elif family == "TWO_SENTENCE_REFERENCE_CHAIN":
                activity["stimulus"] = _mask_reference_chain(str(activity.get("stimulus") or ""), pronoun)
                support = str(runtime_row.get("learner_support_note") or "").strip()
                prompt = "Choose the subject pronoun that completes the second sentence and keeps the same reference."
                activity["prompt"] = f"{prompt} {support}".strip()
                chain_fixes += 1
        u03.u01_learner._assert_no_answer_leak(form)
    return forms, {
        "reference_chain_answer_leak_fixes": chain_fixes,
        "referent_semantic_duplicate_fixes": referent_fixes,
    }


def _validate_projected_forms(
    forms: Sequence[Mapping[str, Any]],
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    runtime = list(payload["runtime_bindings"])
    new_items = {
        str(row["item_id"]): row
        for row in payload["questionbank_delta"]["unit03_new_items"]
    }
    if len(forms) != FORM_COUNT:
        raise Unit03LearnerFacingAcceptanceError(f"FORM_COUNT_INVALID:{len(forms)}")

    stage_counts: dict[str, int] = {}
    rendered_activity_count = 0
    for form_number, form in enumerate(forms, start=1):
        if int(form.get("form_ordinal", -1)) != form_number:
            raise Unit03LearnerFacingAcceptanceError(f"FORM_SEQUENCE_INVALID:{form_number}")
        if int(form.get("section_count", -1)) != SECTIONS_PER_FORM:
            raise Unit03LearnerFacingAcceptanceError(f"SECTION_COUNT_INVALID:F{form_number:02d}")
        if int(form.get("learner_visible_activity_count", -1)) != ACTIVITIES_PER_FORM:
            raise Unit03LearnerFacingAcceptanceError(f"ACTIVITY_COUNT_INVALID:F{form_number:02d}")
        sections = list(form.get("sections") or [])
        if [str(row.get("section") or "") for row in sections] != SECTION_ORDER:
            raise Unit03LearnerFacingAcceptanceError(f"SECTION_ORDER_INVALID:F{form_number:02d}")
        if any(int(row.get("activity_count", -1)) != ACTIVITIES_PER_SECTION for row in sections):
            raise Unit03LearnerFacingAcceptanceError(f"SECTION_DENOMINATOR_INVALID:F{form_number:02d}")

        activities = list(form.get("activities") or [])
        rows = [row for row in runtime if int(row["form_number"]) == form_number]
        if len(activities) != ACTIVITIES_PER_FORM or len(rows) != ACTIVITIES_PER_FORM:
            raise Unit03LearnerFacingAcceptanceError(f"FORM_ALIGNMENT_INVALID:F{form_number:02d}")
        stage = str(form.get("progression_stage") or "")
        stage_counts[stage] = stage_counts.get(stage, 0) + len(activities)

        for activity_number, (activity, runtime_row) in enumerate(zip(activities, rows), start=1):
            if str(activity.get("question_number") or "") != f"Q{activity_number:02d}":
                raise Unit03LearnerFacingAcceptanceError(
                    f"QUESTION_SEQUENCE_INVALID:F{form_number:02d}:Q{activity_number:02d}"
                )
            prompt = str(activity.get("prompt") or "").strip()
            if not prompt:
                raise Unit03LearnerFacingAcceptanceError(
                    f"PROMPT_MISSING:F{form_number:02d}:Q{activity_number:02d}"
                )
            support = str(runtime_row.get("learner_support_note") or "").strip()
            if support and support not in prompt:
                raise Unit03LearnerFacingAcceptanceError(
                    f"STAGE_SUPPORT_NOT_VISIBLE:F{form_number:02d}:Q{activity_number:02d}"
                )
            mode = str(activity.get("response_mode") or "")
            if mode not in ALLOWED_RESPONSE_MODES:
                raise Unit03LearnerFacingAcceptanceError(
                    f"RESPONSE_MODE_INVALID:F{form_number:02d}:Q{activity_number:02d}:{mode}"
                )
            if mode == "select_one" and len(activity.get("options") or []) < 2:
                raise Unit03LearnerFacingAcceptanceError(
                    f"SELECT_ONE_OPTIONS_TOO_SHALLOW:F{form_number:02d}:Q{activity_number:02d}"
                )

            if runtime_row.get("questionbank_source") == "UNIT03_DELTA":
                item = new_items[str(runtime_row["selected_item_id"])]
                family = str(item["task_family"])
                correct = str(item["correct_answer"])
                if correct not in [str(value) for value in activity.get("options") or []]:
                    raise Unit03LearnerFacingAcceptanceError(
                        f"CORRECT_OPTION_NOT_REPRESENTABLE:F{form_number:02d}:Q{activity_number:02d}"
                    )
                if family == "PRONOUN_REFERENT_MATCH":
                    keys = [_referent_key(value) for value in activity.get("options") or []]
                    if len(keys) != len(set(keys)):
                        raise Unit03LearnerFacingAcceptanceError(
                            f"SEMANTICALLY_DUPLICATE_REFERENT_OPTIONS:F{form_number:02d}:Q{activity_number:02d}"
                        )
                if family == "TWO_SENTENCE_REFERENCE_CHAIN":
                    stimulus = str(activity.get("stimulus") or "")
                    if "___ " not in stimulus:
                        raise Unit03LearnerFacingAcceptanceError(
                            f"REFERENCE_CHAIN_ANSWER_NOT_MASKED:F{form_number:02d}:Q{activity_number:02d}"
                        )
            u01_pdf._activity_html(activity, activity_number)
            rendered_activity_count += 1
        u03.u01_learner._assert_no_answer_leak(form)

    expected_stage_counts = {stage: 160 for stage in u03.STAGE_BY_FORMS}
    if stage_counts != expected_stage_counts:
        raise Unit03LearnerFacingAcceptanceError(
            f"STAGE_ACTIVITY_COUNTS_INVALID:{stage_counts}:{expected_stage_counts}"
        )
    if rendered_activity_count != TOTAL_ACTIVITIES:
        raise Unit03LearnerFacingAcceptanceError(
            f"RENDERED_ACTIVITY_COUNT_INVALID:{rendered_activity_count}:{TOTAL_ACTIVITIES}"
        )
    return {
        "form_count": FORM_COUNT,
        "activity_count": TOTAL_ACTIVITIES,
        "rendered_activity_count": rendered_activity_count,
        "stage_activity_counts": stage_counts,
    }


def render_form_html(form: Mapping[str, Any]) -> str:
    """Render one accepted Unit03 form using the existing Unit01 activity renderer."""
    ordinal = int(form.get("form_ordinal", 0))
    activities = list(form.get("activities") or [])
    if len(activities) != ACTIVITIES_PER_FORM:
        raise Unit03LearnerFacingAcceptanceError(f"RENDER_FORM_ACTIVITY_COUNT_INVALID:F{ordinal:02d}")
    sections: list[str] = []
    for section_index, section_name in enumerate(SECTION_ORDER, start=1):
        start = (section_index - 1) * ACTIVITIES_PER_SECTION
        rows = activities[start : start + ACTIVITIES_PER_SECTION]
        cards = "".join(
            u01_pdf._activity_html(activity, start + local_index)
            for local_index, activity in enumerate(rows, start=1)
        )
        sections.append(
            '<section class="unit03-section">'
            f'<h2>{u01_pdf._safe_text(section_name.replace("_", " ").title())}</h2>'
            f"{cards}</section>"
        )
    document = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        f'<title>Unit 03 Form {ordinal:02d}</title></head><body>'
        '<header><div>A1FS · Unit 03</div>'
        f'<h1>Form {ordinal:02d}</h1>'
        f'<p>{u01_pdf._safe_text(str(form.get("progression_stage") or "").replace("_", " ").title())}</p>'
        '</header>' + "".join(sections) +
        '<footer>Learner practice copy · answers and scoring information are not included.</footer>'
        '</body></html>'
    )
    lowered = document.casefold()
    for marker in FORBIDDEN_LEARNER_MARKERS:
        if marker.casefold() in lowered:
            raise Unit03LearnerFacingAcceptanceError(
                f"FORBIDDEN_LEARNER_HTML_MARKER:{marker}:F{ordinal:02d}"
            )
    return document


def build_acceptance_report(source_payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload = dict(source_payload or u03.build_export_payload())
    _source_contract(payload)
    runtime = list(payload["runtime_bindings"])
    source_runtime_identity = _runtime_identity(runtime)
    source_package_sha = str(payload.get("package_sha256") or "")
    source_snapshot = _digest(payload)

    forms, fixes = _project_forms(payload)
    acceptance = _validate_projected_forms(forms, payload)
    rendered_forms = [render_form_html(form) for form in forms]
    if len(rendered_forms) != FORM_COUNT or any(html.count('<article class="activity">') != ACTIVITIES_PER_FORM for html in rendered_forms):
        raise Unit03LearnerFacingAcceptanceError("FORM_HTML_ACTIVITY_DENOMINATOR_INVALID")

    if _digest(payload) != source_snapshot or _runtime_identity(payload["runtime_bindings"]) != source_runtime_identity:
        raise Unit03LearnerFacingAcceptanceError("SOURCE_MATERIALIZATION_MUTATED")

    if fixes != {
        "reference_chain_answer_leak_fixes": REFERENCE_CHAIN_COUNT,
        "referent_semantic_duplicate_fixes": REFERENT_DEDUP_FIX_COUNT,
    }:
        raise Unit03LearnerFacingAcceptanceError(f"LEARNER_FIX_DENOMINATOR_DRIFT:{fixes}")

    return {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS,
        "source_task_id": str(payload["task_id"]),
        "source_status": str(payload["status"]),
        "source_package_sha256": source_package_sha,
        "source_runtime_identity_sha256": source_runtime_identity,
        "learner_forms": forms,
        "acceptance": acceptance,
        "presentation_fixes": fixes,
        "html_form_count": len(rendered_forms),
        "html_activity_count": sum(html.count('<article class="activity">') for html in rendered_forms),
        "renderer_reuse": "product.a1fs_v1_2_1.u01qb18h_r1_unit01_twelve_form_learner_pdf_materialization._activity_html",
        "claim_boundaries": {
            "source_800_runtime_rows_mutated": False,
            "source_selected_item_identities_mutated": False,
            "source_candidate_identities_mutated": False,
            "source_questionbank_items_mutated": False,
            "source_sentence_assets_mutated": False,
            "q6_redone": False,
            "q9_redone": False,
            "q10_redone": False,
            "second_questionbank_authority_created": False,
            "second_selector_created": False,
            "second_renderer_created": False,
            "parallel_sentence_asset_schema_created": False,
            "learner_state_mutated": False,
            "scoring_authority_mutated": False,
            "a2_unlocked": False,
        },
    }


def main() -> int:
    report = build_acceptance_report()
    print(f"STATUS={PASS_STATUS}")
    print(f"FORMS={report['acceptance']['form_count']}")
    print(f"ACTIVITIES={report['acceptance']['activity_count']}")
    print(f"HTML_FORMS={report['html_form_count']}")
    print(f"REFERENCE_CHAIN_FIXES={report['presentation_fixes']['reference_chain_answer_leak_fixes']}")
    print(f"REFERENT_DEDUP_FIXES={report['presentation_fixes']['referent_semantic_duplicate_fixes']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
