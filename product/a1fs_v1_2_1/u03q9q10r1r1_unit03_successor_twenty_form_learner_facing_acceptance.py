#!/usr/bin/env python3
"""Learner-facing acceptance for the Unit03 Q9/Q10 20x40 successor.

Consumes the approved U03Q9Q10R1 successor without regenerating or reselecting
QuestionBank/runtime identity. It projects exactly 20 learner Forms x 40,
keeps the A6/B10/C10/D8/E6 contract, verifies the B/C/E pedagogical proofs,
and reuses the accepted Unit01 learner activity HTML renderer. PDF work stays
out of scope.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any, Mapping, Sequence

from product.a1fs_v1_2_1 import (
    u01qb18a_form01_fresh_learner_materialization_export as u01_learner,
)
from product.a1fs_v1_2_1 import (
    u01qb18h_r1_unit01_twelve_form_learner_pdf_materialization as u01_pdf,
)
from ulga.builders import (
    build_a1fs_v1_u03q9q10r1_unit03_form_pedagogical_contract_20x40_6_10_10_8_6
    as source,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Read-only learner-facing acceptance consumer over the approved U03Q9Q10R1 "
    "successor 20x40 runtime. It preserves all 800 QuestionBank/runtime selected "
    "and candidate identities, reuses the accepted Unit01 learner activity HTML "
    "renderer, and creates no Q6 SentenceAsset, QuestionBank item, selector, runtime, "
    "PDF, learner-state, scoring, Q11, Unit04, or A2 authority."
)

PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U03Q9Q10R1R1_Unit03SuccessorTwentyFormLearnerFacingAcceptance"
SCHEMA_VERSION = "a1fs.v1.u03q9q10r1r1.successor_twenty_form_learner_acceptance.v1"
PASS_STATUS = "PASS_A1FS_V1_U03Q9Q10R1R1_SUCCESSOR_TWENTY_FORM_LEARNER_FACING_ACCEPTANCE"
NEXT_SHORT_STEP = "A1FS-V1-U03FP01_Unit03Q1Q10FinalPackageSuccessorReconciliation"

FORM_COUNT = 20
ACTIVITIES_PER_FORM = 40
TOTAL_ACTIVITIES = 800
SECTION_COUNTS = {"A": 6, "B": 10, "C": 10, "D": 8, "E": 6}
SECTION_ORDER = ("A", "B", "C", "D", "E")
ALLOWED_RESPONSE_MODES = frozenset({"select_one", "short_text"})
FORBIDDEN_LEARNER_MARKERS = (
    "selected_item_id",
    "candidate_ids",
    "runtime_occurrence_id",
    "correct_answer",
    "accepted_answers",
    "response_contract",
    "semantic_signature",
    "source_sentence_asset_ids",
    "integration_proof",
    "q6_binding_status",
    "questionbank_item_id",
)


class Unit03SuccessorLearnerAcceptanceError(ValueError):
    pass


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _runtime_identity(runtime: Sequence[Mapping[str, Any]]) -> str:
    return _digest([
        {
            "runtime_occurrence_id": row["runtime_occurrence_id"],
            "slot_id": row["slot_id"],
            "selected_item_id": row["selected_item_id"],
            "candidate_ids": list(row["candidate_ids"]),
            "form_number": row["form_number"],
            "section": row["section"],
            "task_family": row["task_family"],
            "question_type": row["question_type"],
            "source_identity": row["source_identity"],
        }
        for row in runtime
    ])


def _source_contract(payload: Mapping[str, Any]) -> None:
    if payload.get("status") != source.PASS_STATUS:
        raise Unit03SuccessorLearnerAcceptanceError("SOURCE_STATUS_INVALID")
    contract = dict(payload.get("q10_successor_form_contract") or {})
    expected = {
        "materialization_identity": "U03Q10R1_SUCCESSOR_20X40_6_10_10_8_6",
        "form_count": FORM_COUNT,
        "activities_per_form": ACTIVITIES_PER_FORM,
        "runtime_occurrence_count": TOTAL_ACTIVITIES,
        "candidate_count_per_slot": 3,
        "section_counts_per_form": SECTION_COUNTS,
        "selected_item_identity_count": TOTAL_ACTIVITIES,
        "global_800_distinct_selected_item_proof": True,
    }
    for key, value in expected.items():
        if contract.get(key) != value:
            raise Unit03SuccessorLearnerAcceptanceError(
                f"SOURCE_CONTRACT_DRIFT:{key}:{contract.get(key)}:{value}"
            )
    q9 = dict(payload.get("q9_amendment") or {})
    if q9.get("task_family_count") != 10 or q9.get("family_11_created") is not False:
        raise Unit03SuccessorLearnerAcceptanceError("SOURCE_Q9_FAMILY_CONTRACT_INVALID")
    if tuple(q9.get("task_families") or ()) != source.Q9_FAMILIES:
        raise Unit03SuccessorLearnerAcceptanceError("SOURCE_Q9_FAMILY_IDENTITY_DRIFT")
    q6 = dict(payload.get("q6_preservation") or {})
    if q6.get("successor_sentence_assets_created") != 0 or q6.get("q6_regenerated") is not False:
        raise Unit03SuccessorLearnerAcceptanceError("SOURCE_Q6_PRESERVATION_INVALID")
    boundaries = dict(payload.get("claim_boundaries") or {})
    for key in (
        "q1_q4_mutated", "q5_mutated", "q6_regenerated", "q6_mutated",
        "q7_mutated", "q8_mutated", "historical_q10_runtime_mutated",
        "historical_u03scfv2_runtime_mutated", "family_11_created",
        "pdf_pagination_modified", "pdf_renderer_modified", "q11_opened",
        "unit04_opened", "a2_unlocked",
    ):
        if boundaries.get(key) is not False:
            raise Unit03SuccessorLearnerAcceptanceError(f"SOURCE_BOUNDARY_DRIFT:{key}")


def _response_mode(item: Mapping[str, Any]) -> str:
    return "select_one" if list(item.get("options") or []) else "short_text"


def _learner_activity(number: int, item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "question_number": f"Q{number:02d}",
        "skill": str(item.get("skill") or ""),
        "stimulus": str(item.get("stimulus") or ""),
        "prompt": str(item.get("prompt") or ""),
        "options": [str(value) for value in item.get("options") or []],
        "response_mode": _response_mode(item),
        "capture_enabled": True,
        "practice_only": False,
    }


def _project_forms(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    items = list(payload.get("successor_questionbank_items") or [])
    runtime = list(payload.get("runtime_bindings") or [])
    if len(items) != TOTAL_ACTIVITIES or len(runtime) != TOTAL_ACTIVITIES:
        raise Unit03SuccessorLearnerAcceptanceError("SOURCE_800_DENOMINATOR_INVALID")
    index = {str(row["item_id"]): row for row in items}
    if len(index) != TOTAL_ACTIVITIES:
        raise Unit03SuccessorLearnerAcceptanceError("SOURCE_ITEM_IDENTITY_COLLISION")

    forms: list[dict[str, Any]] = []
    for form_number in range(1, FORM_COUNT + 1):
        rows = [row for row in runtime if int(row["form_number"]) == form_number]
        if len(rows) != ACTIVITIES_PER_FORM:
            raise Unit03SuccessorLearnerAcceptanceError(
                f"FORM_RUNTIME_COUNT_INVALID:F{form_number:02d}"
            )
        activities: list[dict[str, Any]] = []
        sections: list[dict[str, Any]] = []
        position = 0
        for section in SECTION_ORDER:
            count = SECTION_COUNTS[section]
            section_rows = rows[position : position + count]
            if len(section_rows) != count or any(str(row["section"]) != section for row in section_rows):
                raise Unit03SuccessorLearnerAcceptanceError(
                    f"FORM_SECTION_RUNTIME_ALIGNMENT_INVALID:F{form_number:02d}:{section}"
                )
            for runtime_row in section_rows:
                item = index.get(str(runtime_row["selected_item_id"]))
                if item is None:
                    raise Unit03SuccessorLearnerAcceptanceError(
                        f"SELECTED_ITEM_MISSING:{runtime_row['selected_item_id']}"
                    )
                if str(item.get("section")) != section or int(item.get("form_number", -1)) != form_number:
                    raise Unit03SuccessorLearnerAcceptanceError(
                        f"SELECTED_ITEM_SCOPE_DRIFT:F{form_number:02d}:{section}"
                    )
                activities.append(_learner_activity(len(activities) + 1, item))
            sections.append({
                "section": section,
                "section_name": next(name for key, name, _ in source.SECTION_SPECS if key == section),
                "activity_count": count,
            })
            position += count
        form = {
            "unit_id": source.UNIT_ID,
            "unit_ordinal": 3,
            "form_id": f"U03Q10R1-F{form_number:02d}",
            "form_ordinal": form_number,
            "progression_stage": str(rows[0]["progression_stage"]),
            "section_count": len(SECTION_ORDER),
            "learner_visible_activity_count": len(activities),
            "sections": sections,
            "activities": activities,
        }
        u01_learner._assert_no_answer_leak(form)
        forms.append(form)
    return forms


def _validate_pedagogical_proofs(payload: Mapping[str, Any]) -> dict[str, Any]:
    items = list(payload["successor_questionbank_items"])
    per_form: dict[int, dict[str, Any]] = {}
    connected_total = 0
    for form_number in range(1, FORM_COUNT + 1):
        rows = [row for row in items if int(row["form_number"]) == form_number]
        section_counter = Counter(str(row["section"]) for row in rows)
        if section_counter != Counter(SECTION_COUNTS):
            raise Unit03SuccessorLearnerAcceptanceError(
                f"FORM_SECTION_COUNTS_INVALID:F{form_number:02d}:{dict(section_counter)}"
            )
        b_rows = [row for row in rows if row["section"] == "B"]
        b_evidence = {value for row in b_rows for value in row.get("pedagogical_evidence") or []}
        if not source.B_REQUIRED_EVIDENCE.issubset(b_evidence):
            raise Unit03SuccessorLearnerAcceptanceError(
                f"FORM_B_EVIDENCE_MISSING:F{form_number:02d}:{sorted(b_evidence)}"
            )
        c_rows = [row for row in rows if row["section"] == "C"]
        for row in c_rows:
            proof = dict(row.get("integration_proof") or {})
            if set(row.get("grammar_targets") or []) != source.C_TARGETS:
                raise Unit03SuccessorLearnerAcceptanceError(
                    f"FORM_C_TARGETS_INVALID:F{form_number:02d}:{row['item_id']}"
                )
            if proof != {
                "same_question_contains_u01_article": True,
                "same_question_contains_u02_number_plural": True,
                "same_question_contains_u03_subject_pronoun": True,
                "alternating_separate_questions_only": False,
            }:
                raise Unit03SuccessorLearnerAcceptanceError(
                    f"FORM_C_INTEGRATION_PROOF_INVALID:F{form_number:02d}:{row['item_id']}"
                )
        e_rows = [row for row in rows if row["section"] == "E"]
        if len(e_rows) != 6 or not all(row.get("connected_passage") is True for row in e_rows):
            raise Unit03SuccessorLearnerAcceptanceError(
                f"FORM_E_CONNECTED_COUNT_INVALID:F{form_number:02d}"
            )
        passage_ids = {str(row.get("passage_id") or "") for row in e_rows}
        passage_texts = {str(row.get("stimulus") or "") for row in e_rows}
        if len(passage_ids) != 1 or "" in passage_ids or len(passage_texts) != 1:
            raise Unit03SuccessorLearnerAcceptanceError(
                f"FORM_E_PASSAGE_CONNECTION_INVALID:F{form_number:02d}"
            )
        expected_sentence_count = source.PASSAGE_SENTENCE_COUNT_BY_STAGE[source._stage(form_number)]
        if {int(row.get("passage_sentence_count", -1)) for row in e_rows} != {expected_sentence_count}:
            raise Unit03SuccessorLearnerAcceptanceError(
                f"FORM_E_PASSAGE_LENGTH_INVALID:F{form_number:02d}"
            )
        if {str(row["question_type"]) for row in e_rows} != {qtype for qtype, _ in source.CONNECTED_PASSAGE_TYPES}:
            raise Unit03SuccessorLearnerAcceptanceError(
                f"FORM_E_QUESTION_TYPES_INVALID:F{form_number:02d}"
            )
        connected_total += len(e_rows)
        per_form[form_number] = {
            "section_b_evidence": sorted(b_evidence),
            "section_c_integrated_item_count": len(c_rows),
            "section_e_connected_question_count": len(e_rows),
            "section_e_passage_sentence_count": expected_sentence_count,
        }
    if connected_total != 120:
        raise Unit03SuccessorLearnerAcceptanceError(
            f"CONNECTED_PASSAGE_TOTAL_INVALID:{connected_total}:120"
        )
    return {
        "forms_validated": FORM_COUNT,
        "section_b_all_forms_proven": True,
        "section_c_all_items_same_question_integrated": True,
        "section_e_connected_passage_questions": connected_total,
        "per_form": per_form,
    }


def _validate_learner_forms(forms: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if len(forms) != FORM_COUNT:
        raise Unit03SuccessorLearnerAcceptanceError(f"FORM_COUNT_INVALID:{len(forms)}")
    stage_counts: Counter[str] = Counter()
    rendered_activity_count = 0
    for form_number, form in enumerate(forms, start=1):
        if int(form.get("form_ordinal", -1)) != form_number:
            raise Unit03SuccessorLearnerAcceptanceError(f"FORM_SEQUENCE_INVALID:{form_number}")
        if int(form.get("learner_visible_activity_count", -1)) != ACTIVITIES_PER_FORM:
            raise Unit03SuccessorLearnerAcceptanceError(f"FORM_ACTIVITY_COUNT_INVALID:F{form_number:02d}")
        sections = list(form.get("sections") or [])
        if [row.get("section") for row in sections] != list(SECTION_ORDER):
            raise Unit03SuccessorLearnerAcceptanceError(f"FORM_SECTION_ORDER_INVALID:F{form_number:02d}")
        if {str(row["section"]): int(row["activity_count"]) for row in sections} != SECTION_COUNTS:
            raise Unit03SuccessorLearnerAcceptanceError(f"FORM_SECTION_DENOMINATOR_INVALID:F{form_number:02d}")
        activities = list(form.get("activities") or [])
        for index, activity in enumerate(activities, start=1):
            if activity.get("question_number") != f"Q{index:02d}":
                raise Unit03SuccessorLearnerAcceptanceError(
                    f"QUESTION_SEQUENCE_INVALID:F{form_number:02d}:Q{index:02d}"
                )
            if not str(activity.get("prompt") or "").strip():
                raise Unit03SuccessorLearnerAcceptanceError(
                    f"PROMPT_MISSING:F{form_number:02d}:Q{index:02d}"
                )
            mode = str(activity.get("response_mode") or "")
            if mode not in ALLOWED_RESPONSE_MODES:
                raise Unit03SuccessorLearnerAcceptanceError(
                    f"RESPONSE_MODE_INVALID:F{form_number:02d}:Q{index:02d}:{mode}"
                )
            if mode == "select_one" and len(activity.get("options") or []) < 2:
                raise Unit03SuccessorLearnerAcceptanceError(
                    f"SELECT_ONE_OPTIONS_TOO_SHALLOW:F{form_number:02d}:Q{index:02d}"
                )
            u01_pdf._activity_html(activity, index)
            rendered_activity_count += 1
        u01_learner._assert_no_answer_leak(form)
        stage_counts[str(form.get("progression_stage") or "")] += len(activities)
    if stage_counts != Counter({stage: 160 for stage in source.STAGE_BY_FORMS}):
        raise Unit03SuccessorLearnerAcceptanceError(f"STAGE_COUNTS_INVALID:{dict(stage_counts)}")
    if rendered_activity_count != TOTAL_ACTIVITIES:
        raise Unit03SuccessorLearnerAcceptanceError(
            f"RENDERED_ACTIVITY_COUNT_INVALID:{rendered_activity_count}"
        )
    return {
        "form_count": FORM_COUNT,
        "activity_count": TOTAL_ACTIVITIES,
        "rendered_activity_count": rendered_activity_count,
        "stage_activity_counts": dict(stage_counts),
    }


def render_form_html(form: Mapping[str, Any]) -> str:
    ordinal = int(form.get("form_ordinal", 0))
    activities = list(form.get("activities") or [])
    if len(activities) != ACTIVITIES_PER_FORM:
        raise Unit03SuccessorLearnerAcceptanceError(f"RENDER_FORM_COUNT_INVALID:F{ordinal:02d}")
    blocks: list[str] = []
    position = 0
    sections = list(form.get("sections") or [])
    for section in sections:
        count = int(section["activity_count"])
        rows = activities[position : position + count]
        cards = "".join(
            u01_pdf._activity_html(activity, position + local_index)
            for local_index, activity in enumerate(rows, start=1)
        )
        blocks.append(
            '<section class="unit03-section">'
            f'<h2>{u01_pdf._safe_text(str(section["section_name"]).replace("_", " ").title())}</h2>'
            f"{cards}</section>"
        )
        position += count
    document = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        f'<title>Unit 03 Successor Form {ordinal:02d}</title></head><body>'
        '<header><div>A1FS · Unit 03</div>'
        f'<h1>Form {ordinal:02d}</h1>'
        f'<p>{u01_pdf._safe_text(str(form.get("progression_stage") or "").replace("_", " ").title())}</p>'
        '</header>' + "".join(blocks) +
        '<footer>Learner practice copy · answers and scoring information are not included.</footer>'
        '</body></html>'
    )
    lowered = document.casefold()
    for marker in FORBIDDEN_LEARNER_MARKERS:
        if marker.casefold() in lowered:
            raise Unit03SuccessorLearnerAcceptanceError(
                f"FORBIDDEN_LEARNER_HTML_MARKER:{marker}:F{ordinal:02d}"
            )
    if document.count('<article class="activity">') != ACTIVITIES_PER_FORM:
        raise Unit03SuccessorLearnerAcceptanceError(f"HTML_ACTIVITY_COUNT_INVALID:F{ordinal:02d}")
    return document


def build_acceptance_report(source_payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload = dict(source_payload or source.build_export_payload())
    _source_contract(payload)
    source_snapshot = _digest(payload)
    runtime_identity = _runtime_identity(payload["runtime_bindings"])
    source_package_sha = str(payload.get("package_sha256") or "")
    if not source_package_sha:
        raise Unit03SuccessorLearnerAcceptanceError("SOURCE_PACKAGE_SHA_MISSING")

    pedagogy = _validate_pedagogical_proofs(payload)
    forms = _project_forms(payload)
    acceptance = _validate_learner_forms(forms)
    rendered = [render_form_html(form) for form in forms]
    if len(rendered) != FORM_COUNT:
        raise Unit03SuccessorLearnerAcceptanceError("HTML_FORM_COUNT_INVALID")

    if _digest(payload) != source_snapshot or _runtime_identity(payload["runtime_bindings"]) != runtime_identity:
        raise Unit03SuccessorLearnerAcceptanceError("SOURCE_AUTHORITY_MUTATED")

    return {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS,
        "source_task_id": source.TASK_ID,
        "source_status": source.PASS_STATUS,
        "source_package_sha256": source_package_sha,
        "source_runtime_identity_sha256": runtime_identity,
        "learner_forms": forms,
        "acceptance": acceptance,
        "pedagogical_acceptance": pedagogy,
        "html_form_count": len(rendered),
        "html_activity_count": sum(html.count('<article class="activity">') for html in rendered),
        "renderer_reuse": (
            "product.a1fs_v1_2_1.u01qb18h_r1_unit01_twelve_form_learner_pdf_materialization._activity_html"
        ),
        "claim_boundaries": {
            "source_800_runtime_rows_mutated": False,
            "source_selected_item_identities_mutated": False,
            "source_candidate_identities_mutated": False,
            "source_questionbank_items_mutated": False,
            "q6_redone": False,
            "q9_redone": False,
            "q10_successor_rematerialized": False,
            "second_questionbank_authority_created": False,
            "second_selector_created": False,
            "second_renderer_created": False,
            "pdf_modified": False,
            "learner_state_mutated": False,
            "scoring_authority_mutated": False,
            "q11_opened": False,
            "unit04_opened": False,
            "a2_unlocked": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }


def main() -> int:
    report = build_acceptance_report()
    print(f"STATUS={PASS_STATUS}")
    print(f"FORMS={report['acceptance']['form_count']}")
    print(f"ACTIVITIES={report['acceptance']['activity_count']}")
    print(f"HTML_FORMS={report['html_form_count']}")
    print(f"CONNECTED_PASSAGE_QUESTIONS={report['pedagogical_acceptance']['section_e_connected_passage_questions']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
