from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from product.a1fs_v1_2_1 import (
    _u04fsv2_current360_contextual_form_runtime_base as _base,
)
from product.a1fs_v1_2_1 import (
    u04fsv2a_section_a_current360_approved_binding as section_a_current360,
)
from product.a1fs_v1_2_1._u04fsv2_current360_contextual_form_runtime_base import *  # noqa: F401,F403

Unit04FSV2Error = _base.Unit04FSV2Error
_relation_options = _base._relation_options
SECTION_A_REVISION = section_a_current360.SECTION_A_REVISION
SECTION_A_TASK_ID = section_a_current360.TASK_ID
SECTION_A_STATUS = section_a_current360.STATUS
SHORT_MESSAGE_ASSET_PATH = Path(__file__).with_name(
    "u04ketgap01_short_message_meaning_gpt56_approved20.json"
)
SHORT_MESSAGE_REVISION = "CURRENT_FSV2_D05_Q31_SHORT_MESSAGE_MEANING_CUTOVER_V1"
SHORT_MESSAGE_EXPECTED_COUNT = 20


def _section_a_episode_index() -> dict[str, dict[str, Any]]:
    current_report = _base.current360.build_unit04_neb02_natural_episode_bank_360()
    if current_report.get("status") != _base.current360.STATUS:
        raise Unit04FSV2Error("SECTION_A_CURRENT360_SOURCE_NOT_PASS")
    episodes = {
        str(row["episode_id"]): dict(row)
        for row in current_report.get("effective_episodes") or []
    }
    if len(episodes) != 360:
        raise Unit04FSV2Error(f"SECTION_A_CURRENT360_EPISODE_COUNT_DRIFT:{len(episodes)}")
    return episodes


def _section_a_lineage(candidate: Mapping[str, Any], episode: Mapping[str, Any]) -> dict[str, Any]:
    return {
        **_base._episode_lineage(episode),
        "section_a_candidate_id": str(candidate["candidate_id"]),
        "section_a_revision": SECTION_A_REVISION,
        "source_authority": section_a_current360.SOURCE_AUTHORITY,
        "gpt5_6_semantic_review": str(candidate["gpt5_6_semantic_review"]),
        "operator_approved": bool(candidate["operator_approved"]),
        "operator_approval_date": section_a_current360.OPERATOR_APPROVAL_DATE,
        "at_policy": section_a_current360.AT_POLICY,
    }


def _apply_approved_section_a(report: dict[str, Any]) -> dict[str, Any]:
    bindings = section_a_current360.build_section_a_binding_index()
    episodes = _section_a_episode_index()

    active_by_slot = {
        (int(row["form_number"]), str(row["section"]), int(row["section_activity_ordinal"])): row
        for row in report["active_items"]
    }
    runtime_by_slot = {
        (int(row["form_number"]), str(row["section"]), int(row["section_activity_ordinal"])): row
        for row in report["runtime_bindings"]
    }

    section_a_ids: set[str] = set()
    section_a_episode_ids: set[str] = set()
    at_count = 0

    for form_number in range(1, section_a_current360.FORM_COUNT + 1):
        for local in range(1, section_a_current360.ITEMS_PER_FORM + 1):
            candidate = dict(bindings[(form_number, local)])
            episode_id = str(candidate["source_episode_id"])
            if episode_id not in episodes:
                raise Unit04FSV2Error(
                    f"SECTION_A_CURRENT360_EPISODE_MISSING:{candidate['candidate_id']}:{episode_id}"
                )
            episode = episodes[episode_id]
            section_a_current360.validate_current360_episode(candidate, episode)

            slot = (form_number, "A", local)
            item = active_by_slot[slot]
            runtime = runtime_by_slot[slot]
            relation = str(candidate["target_relation"])
            learner_activity = section_a_current360.materialize_learner_activity(candidate)
            learner_activity["question_number"] = f"Q{local:02d}"
            scoring = _base._selected_scoring(str(candidate["answer"]))
            lineage = _section_a_lineage(candidate, episode)

            old_active_item_id = str(item["active_item_id"])
            identity = {
                "form": form_number,
                "section": "A",
                "local": local,
                "source_q10_item_id": str(item["source_q10_lineage"]["source_q10_item_id"]),
                "section_a_candidate_id": str(candidate["candidate_id"]),
                "section_a_current360_episode_id": episode_id,
                "target_relation": relation,
                "section_a_revision": SECTION_A_REVISION,
            }
            active_item_id = (
                f"U04FSV2-F{form_number:02d}-A{local:02d}-"
                f"{_base._digest(identity)[:12].upper()}"
            )

            item["active_item_id"] = active_item_id
            item["target_relation_surface"] = relation
            item["learner_activity"] = learner_activity
            item["scoring_contract"] = scoring
            item["answer_key_private"] = {
                "reference_answer": scoring["reference_answer"],
                "scoring_mode": scoring["scoring_mode"],
            }
            item["section_a_current360_lineage"] = lineage
            item["section_a_candidate_id"] = str(candidate["candidate_id"])
            item["section_a_revision"] = SECTION_A_REVISION
            item["source_q10_lineage"]["section_a_override_authority"] = SECTION_A_TASK_ID
            item["source_q10_lineage"]["source_q10_item_preserved_as_lineage_only_for_section_a"] = True

            runtime["active_item_id"] = active_item_id
            runtime["section_a_candidate_id"] = str(candidate["candidate_id"])
            runtime["section_a_current360_episode_id"] = episode_id
            runtime["section_a_revision"] = SECTION_A_REVISION
            runtime["superseded_section_a_active_item_id"] = old_active_item_id

            section_a_ids.add(str(candidate["candidate_id"]))
            section_a_episode_ids.add(episode_id)
            at_count += int(relation == "at")

    if len(section_a_ids) != section_a_current360.TOTAL_ITEMS:
        raise Unit04FSV2Error(f"SECTION_A_CANDIDATE_BINDING_COUNT_DRIFT:{len(section_a_ids)}")
    if at_count != section_a_current360.EXPECTED_AT_COUNT:
        raise Unit04FSV2Error(f"SECTION_A_AT_BINDING_COUNT_DRIFT:{at_count}")

    for form in report["forms"]:
        form_number = int(form["form_number"])
        form_rows = [
            row for row in report["active_items"]
            if int(row["form_number"]) == form_number
        ]
        if len(form_rows) != 40:
            raise Unit04FSV2Error(f"SECTION_A_FORM_TOTAL_DRIFT:F{form_number:02d}:{len(form_rows)}")
        form["active_item_ids"] = [str(row["active_item_id"]) for row in form_rows]
        section_a_rows = [row for row in form_rows if row["section"] == "A"]
        if len(section_a_rows) != 6:
            raise Unit04FSV2Error(f"SECTION_A_FORM_COUNT_DRIFT:F{form_number:02d}")
        if len({str(row["target_relation_surface"]) for row in section_a_rows}) != 6:
            raise Unit04FSV2Error(f"SECTION_A_FORM_RELATION_DUPLICATE:F{form_number:02d}")
        if len({str(row["section_a_current360_lineage"]["episode_id"]) for row in section_a_rows}) != 6:
            raise Unit04FSV2Error(f"SECTION_A_FORM_EPISODE_DUPLICATE:F{form_number:02d}")

    active_ids = [str(row["active_item_id"]) for row in report["active_items"]]
    if len(active_ids) != 800 or len(set(active_ids)) != 800:
        raise Unit04FSV2Error("SECTION_A_ACTIVE_ITEM_ID_COLLISION")

    relation_counts = Counter(str(row["target_relation_surface"]) for row in report["active_items"])
    if set(relation_counts) != _base.TARGET_RELATION_SET:
        raise Unit04FSV2Error(f"SECTION_A_TARGET_RELATION_COVERAGE_DRIFT:{sorted(relation_counts)}")
    report["coverage"]["target_relation_coverage"] = f"{len(relation_counts)}/8"
    report["coverage"]["target_relation_counts"] = {
        relation: relation_counts[relation] for relation in _base.TARGET_RELATIONS
    }
    report["coverage"]["section_a_current360_binding_count"] = len(section_a_ids)
    report["coverage"]["section_a_current360_distinct_episode_count"] = len(section_a_episode_ids)
    report["coverage"]["section_a_gpt5_6_review_pass_count"] = len(section_a_ids)
    report["coverage"]["section_a_operator_approved_count"] = len(section_a_ids)
    report["coverage"]["section_a_at_selected_response_count"] = at_count

    report["source_authority"]["section_a_current360_approved120"] = {
        "task_id": SECTION_A_TASK_ID,
        "status": SECTION_A_STATUS,
        "source_authority": section_a_current360.SOURCE_AUTHORITY,
        "gpt5_6_semantic_review": "PASS_REQUIRED",
        "operator_approved": True,
        "operator_approval_date": section_a_current360.OPERATOR_APPROVAL_DATE,
    }
    report["cutover_contract"]["section_a_runtime_role"] = (
        "CURRENT360_FACT_AUTHORITY_PLUS_GPT5_6_REVIEWED_OPERATOR_APPROVED_SELECTED_RESPONSE"
    )
    report["cutover_contract"]["section_a_parallel_runtime_allowed"] = False
    report["cutover_contract"]["section_a_at_policy"] = section_a_current360.AT_POLICY
    report["materialization_contract"]["section_a_current360_approved_activity_count"] = len(section_a_ids)
    report["materialization_contract"]["section_a_at_bounded_exception_count"] = at_count

    report["safety"]["selected_at_default_guard_retained"] = True
    report["safety"]["section_a_at_bounded_exception_count"] = at_count
    report["safety"]["section_a_at_global_unlocked"] = False
    report["safety"]["section_a_requires_current360_gpt5_6_operator_approval"] = True
    report["safety"]["q31_d05_modified_by_section_a_cutover"] = False
    report["safety"]["b_c_d_e_items_modified_by_section_a_cutover"] = False

    report["section_a_binding_readback"] = section_a_current360.compact_readback()
    report["deterministic_runtime_sha256"] = _base._digest({
        "forms": report["forms"],
        "active_items": report["active_items"],
        "runtime_bindings": report["runtime_bindings"],
    })
    return report


def _load_short_message_asset() -> dict[str, Any]:
    if not SHORT_MESSAGE_ASSET_PATH.is_file():
        raise Unit04FSV2Error(f"SHORT_MESSAGE_ASSET_MISSING:{SHORT_MESSAGE_ASSET_PATH}")
    payload = json.loads(SHORT_MESSAGE_ASSET_PATH.read_text(encoding="utf-8"))
    if payload.get("schema") != "a1fs.v1.u04.ket_gap.short_message_meaning.approved20.v1":
        raise Unit04FSV2Error("SHORT_MESSAGE_SCHEMA_DRIFT")
    if payload.get("status") != "HUMAN_PDF_APPROVED_PENDING_RUNTIME_BINDING":
        raise Unit04FSV2Error("SHORT_MESSAGE_APPROVAL_STATUS_DRIFT")

    operator = payload.get("operator_acceptance") or {}
    if operator.get("operator_status") != "APPROVED":
        raise Unit04FSV2Error("SHORT_MESSAGE_OPERATOR_APPROVAL_MISSING")
    if operator.get("runtime_binding_approved") is not True:
        raise Unit04FSV2Error("SHORT_MESSAGE_RUNTIME_BINDING_NOT_APPROVED")

    provenance = payload.get("generation_provenance") or {}
    if provenance.get("generation_model") != "GPT-5.6":
        raise Unit04FSV2Error("SHORT_MESSAGE_GENERATION_MODEL_DRIFT")
    if provenance.get("source_task_copied") is not False:
        raise Unit04FSV2Error("SHORT_MESSAGE_SOURCE_TASK_COPY_FORBIDDEN")
    if provenance.get("source_wording_copied") is not False:
        raise Unit04FSV2Error("SHORT_MESSAGE_SOURCE_WORDING_COPY_FORBIDDEN")
    if provenance.get("live_model_call_in_ci") is not False:
        raise Unit04FSV2Error("SHORT_MESSAGE_LIVE_MODEL_CI_FORBIDDEN")

    policy = payload.get("runtime_binding_policy") or {}
    expected_policy = {
        "form_count": 20,
        "slot_per_form": "D05",
        "learner_question_number": "Q31",
        "replace_task_variant": "READING_SIMPLE_GIST_SEED",
        "new_task_variant": "SHORT_MESSAGE_MEANING",
        "forms_remain_20_x_40": True,
        "parallel_runtime_allowed": False,
        "stage_exposure_must_be_preserved": True,
        "shared_d_e_context_must_be_preserved": True,
        "existing_location_extraction_tasks_unchanged": True,
    }
    for key, expected in expected_policy.items():
        if policy.get(key) != expected:
            raise Unit04FSV2Error(f"SHORT_MESSAGE_BINDING_POLICY_DRIFT:{key}:{policy.get(key)!r}")

    items = list(payload.get("items") or [])
    if len(items) != SHORT_MESSAGE_EXPECTED_COUNT:
        raise Unit04FSV2Error(f"SHORT_MESSAGE_ITEM_COUNT_DRIFT:{len(items)}")
    if [int(row["form_number"]) for row in items] != list(range(1, 21)):
        raise Unit04FSV2Error("SHORT_MESSAGE_FORM_SEQUENCE_DRIFT")
    return payload


def _short_message_activity(item: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    options = [str(value) for value in item.get("options") or []]
    correct_index = int(item["correct_option_index"])
    if len(options) != 3 or len(set(options)) != 3:
        raise Unit04FSV2Error(f"SHORT_MESSAGE_OPTION_CONTRACT_DRIFT:F{int(item['form_number']):02d}")
    if correct_index not in {0, 1, 2}:
        raise Unit04FSV2Error(f"SHORT_MESSAGE_CORRECT_INDEX_DRIFT:F{int(item['form_number']):02d}")
    answer = options[correct_index]
    activity = {
        "question_number": "Q31",
        "skill": "READING",
        "stimulus": f"Message: {str(item['message']).strip()}",
        "prompt": str(item["question"]).strip(),
        "options": options,
        "response_mode": "select_one",
        "capture_enabled": True,
        "practice_only": False,
    }
    if not activity["stimulus"] or not activity["prompt"]:
        raise Unit04FSV2Error(f"SHORT_MESSAGE_VISIBLE_TEXT_EMPTY:F{int(item['form_number']):02d}")
    return activity, _base._selected_scoring(answer)


def _apply_short_message_meaning(report: dict[str, Any]) -> dict[str, Any]:
    payload = _load_short_message_asset()
    items = {int(row["form_number"]): dict(row) for row in payload["items"]}
    episodes = _section_a_episode_index()

    active_by_slot = {
        (int(row["form_number"]), str(row["section"]), int(row["section_activity_ordinal"])): row
        for row in report["active_items"]
    }
    runtime_by_slot = {
        (int(row["form_number"]), str(row["section"]), int(row["section_activity_ordinal"])): row
        for row in report["runtime_bindings"]
    }

    bound_forms: set[int] = set()
    runtime_episode_ids: set[str] = set()
    authoring_episode_ids: set[str] = set()

    for form_number in range(1, 21):
        approved = items[form_number]
        d05 = active_by_slot[(form_number, "D", 5)]
        e05 = active_by_slot[(form_number, "E", 5)]
        runtime = runtime_by_slot[(form_number, "D", 5)]

        if d05["task_variant"] != "READING_SIMPLE_GIST_SEED":
            raise Unit04FSV2Error(
                f"SHORT_MESSAGE_D05_PREDECESSOR_VARIANT_DRIFT:F{form_number:02d}:{d05['task_variant']}"
            )
        if d05["learner_activity"]["question_number"] != "Q31":
            raise Unit04FSV2Error(f"SHORT_MESSAGE_D05_QUESTION_NUMBER_DRIFT:F{form_number:02d}")
        if str(d05["progression_stage"]) != str(approved["progression_stage"]):
            raise Unit04FSV2Error(f"SHORT_MESSAGE_STAGE_DRIFT:F{form_number:02d}")

        d_lineage = dict(d05.get("current360_episode_lineage") or {})
        e_lineage = dict(e05.get("current360_episode_lineage") or {})
        if not d_lineage or not e_lineage:
            raise Unit04FSV2Error(f"SHORT_MESSAGE_D_E_CURRENT360_LINEAGE_MISSING:F{form_number:02d}")
        if d_lineage["episode_id"] != e_lineage["episode_id"]:
            raise Unit04FSV2Error(f"SHORT_MESSAGE_D_E_EPISODE_SHARING_DRIFT:F{form_number:02d}")
        if d_lineage["micro_scene_id"] != e_lineage["micro_scene_id"]:
            raise Unit04FSV2Error(f"SHORT_MESSAGE_D_E_MICRO_SCENE_SHARING_DRIFT:F{form_number:02d}")

        source_episode_id = str(approved["authoring_source_episode_id"])
        if source_episode_id not in episodes:
            raise Unit04FSV2Error(
                f"SHORT_MESSAGE_AUTHORING_EPISODE_MISSING:F{form_number:02d}:{source_episode_id}"
            )
        source_episode = episodes[source_episode_id]
        if str(source_episode["micro_scene_id"]) != str(approved["micro_scene_id"]):
            raise Unit04FSV2Error(f"SHORT_MESSAGE_AUTHORING_MICRO_SCENE_DRIFT:F{form_number:02d}")

        learner_activity, scoring = _short_message_activity(approved)
        old_active_item_id = str(d05["active_item_id"])
        identity = {
            "form": form_number,
            "section": "D",
            "local": 5,
            "source_q10_item_id": str(d05["source_q10_lineage"]["source_q10_item_id"]),
            "approved_authoring_episode_id": source_episode_id,
            "runtime_current360_episode_id": str(d_lineage["episode_id"]),
            "task_variant": "SHORT_MESSAGE_MEANING",
            "revision": SHORT_MESSAGE_REVISION,
        }
        active_item_id = (
            f"U04FSV2-F{form_number:02d}-D05-"
            f"{_base._digest(identity)[:12].upper()}"
        )

        d05["active_item_id"] = active_item_id
        d05["task_variant"] = "SHORT_MESSAGE_MEANING"
        d05["learner_activity"] = learner_activity
        d05["scoring_contract"] = scoring
        d05["answer_key_private"] = {
            "reference_answer": scoring["reference_answer"],
            "scoring_mode": scoring["scoring_mode"],
        }
        d05["direct_target_relation_scoring"] = False
        d05["short_message_meaning_lineage"] = {
            "task_id": str(payload["task_id"]),
            "schema": str(payload["schema"]),
            "admission_status": str(payload["status"]),
            "revision": SHORT_MESSAGE_REVISION,
            "ket_s3_profile": str(payload["source_authorities"]["ket_s3_profile"]),
            "ket_task_family": str(payload["source_authorities"]["ket_task_family"]),
            "assessment_capability": str(payload["source_authorities"]["assessment_capability"]),
            "generation_model": str(payload["generation_provenance"]["generation_model"]),
            "generation_method": str(payload["generation_provenance"]["generation_method"]),
            "operator_status": str(payload["operator_acceptance"]["operator_status"]),
            "runtime_binding_approved": bool(
                payload["operator_acceptance"]["runtime_binding_approved"]
            ),
            "authoring_current360_episode_lineage": _base._episode_lineage(source_episode),
            "runtime_current360_episode_lineage_preserved": d_lineage,
            "shared_e05_current360_episode_id": str(e_lineage["episode_id"]),
            "runtime_context_binding_mode": (
                "PRESERVE_EXISTING_D05_E05_CURRENT360_CONTEXT_WHILE_BINDING_APPROVED_MESSAGE"
            ),
            "language_ceiling": dict(payload["language_ceiling"]),
        }

        runtime["active_item_id"] = active_item_id
        runtime["short_message_meaning_cutover"] = True
        runtime["short_message_task_id"] = str(payload["task_id"])
        runtime["short_message_revision"] = SHORT_MESSAGE_REVISION
        runtime["short_message_authoring_episode_id"] = source_episode_id
        runtime["short_message_runtime_current360_episode_id"] = str(d_lineage["episode_id"])
        runtime["superseded_d05_active_item_id"] = old_active_item_id

        bound_forms.add(form_number)
        runtime_episode_ids.add(str(d_lineage["episode_id"]))
        authoring_episode_ids.add(source_episode_id)

    if bound_forms != set(range(1, 21)):
        raise Unit04FSV2Error(f"SHORT_MESSAGE_FORM_BINDING_DRIFT:{sorted(bound_forms)}")

    for form in report["forms"]:
        form_number = int(form["form_number"])
        form_rows = [
            row for row in report["active_items"]
            if int(row["form_number"]) == form_number
        ]
        if len(form_rows) != 40:
            raise Unit04FSV2Error(f"SHORT_MESSAGE_FORM_TOTAL_DRIFT:F{form_number:02d}:{len(form_rows)}")
        form["active_item_ids"] = [str(row["active_item_id"]) for row in form_rows]

    active_ids = [str(row["active_item_id"]) for row in report["active_items"]]
    if len(active_ids) != 800 or len(set(active_ids)) != 800:
        raise Unit04FSV2Error("SHORT_MESSAGE_ACTIVE_ITEM_ID_COLLISION")

    short_rows = [
        row for row in report["active_items"]
        if row["section"] == "D" and int(row["section_activity_ordinal"]) == 5
    ]
    if len(short_rows) != 20:
        raise Unit04FSV2Error(f"SHORT_MESSAGE_BOUND_COUNT_DRIFT:{len(short_rows)}")
    if any(row["task_variant"] != "SHORT_MESSAGE_MEANING" for row in short_rows):
        raise Unit04FSV2Error("SHORT_MESSAGE_D05_VARIANT_CUTOVER_INCOMPLETE")
    old_gist_count = sum(
        int(row["task_variant"] == "READING_SIMPLE_GIST_SEED")
        for row in report["active_items"]
    )
    if old_gist_count:
        raise Unit04FSV2Error(f"SHORT_MESSAGE_LEGACY_GIST_REMAINS:{old_gist_count}")

    for form_number in range(1, 21):
        d05 = active_by_slot[(form_number, "D", 5)]
        e05 = active_by_slot[(form_number, "E", 5)]
        if (
            d05["current360_episode_lineage"]["episode_id"]
            != e05["current360_episode_lineage"]["episode_id"]
        ):
            raise Unit04FSV2Error(f"SHORT_MESSAGE_POST_CUTOVER_D_E_SHARING_DRIFT:F{form_number:02d}")

    task_variant_counts = Counter(str(row["task_variant"]) for row in report["active_items"])
    report["coverage"]["task_variant_count"] = len(task_variant_counts)
    report["coverage"]["task_variant_counts"] = dict(sorted(task_variant_counts.items()))
    report["coverage"]["short_message_meaning_activity_count"] = len(short_rows)
    report["coverage"]["reading_simple_gist_seed_activity_count"] = old_gist_count
    report["coverage"]["short_message_runtime_current360_distinct_episode_count"] = len(
        runtime_episode_ids
    )
    report["coverage"]["short_message_authoring_current360_distinct_episode_count"] = len(
        authoring_episode_ids
    )

    report["source_authority"]["short_message_meaning_approved20"] = {
        "task_id": str(payload["task_id"]),
        "schema": str(payload["schema"]),
        "admission_status": str(payload["status"]),
        "generation_model": str(payload["generation_provenance"]["generation_model"]),
        "operator_status": str(payload["operator_acceptance"]["operator_status"]),
        "runtime_binding_approved": bool(payload["operator_acceptance"]["runtime_binding_approved"]),
        "current360_role": (
            "APPROVED_MESSAGE_AUTHORING_PROVENANCE_PLUS_PRESERVED_ACTIVE_D05_E05_CONTEXT"
        ),
    }
    report["cutover_contract"]["d05_q31_active_task_variant"] = "SHORT_MESSAGE_MEANING"
    report["cutover_contract"]["d05_q31_superseded_task_variant"] = "READING_SIMPLE_GIST_SEED"
    report["cutover_contract"]["d05_q31_parallel_runtime_allowed"] = False
    report["cutover_contract"]["d05_e05_current360_shared_context_preserved"] = True
    report["materialization_contract"]["short_message_meaning_activity_count"] = len(short_rows)
    report["materialization_contract"]["short_message_meaning_slot_per_form"] = "D05"
    report["materialization_contract"]["short_message_meaning_learner_question_number"] = "Q31"

    report["safety"]["q31_d05_modified_by_short_message_cutover"] = True
    report["safety"]["e05_q39_modified_by_short_message_cutover"] = False
    report["safety"]["d05_e05_current360_shared_context_preserved"] = True
    report["safety"]["section_a_current360_approved120_preserved"] = (
        report["coverage"].get("section_a_current360_binding_count") == 120
    )
    report["safety"]["short_message_parallel_runtime_created"] = False
    report["safety"]["a2_a2plus_unlocked_by_short_message_cutover"] = False

    report["short_message_binding_readback"] = {
        "task_id": str(payload["task_id"]),
        "revision": SHORT_MESSAGE_REVISION,
        "bound_activity_count": len(short_rows),
        "form_count": len(bound_forms),
        "slot_per_form": "D05",
        "learner_question_number": "Q31",
        "new_task_variant": "SHORT_MESSAGE_MEANING",
        "superseded_task_variant": "READING_SIMPLE_GIST_SEED",
        "operator_status": str(payload["operator_acceptance"]["operator_status"]),
        "runtime_binding_approved": bool(payload["operator_acceptance"]["runtime_binding_approved"]),
        "d_e_shared_current360_context_preserved": True,
        "section_a_120_preserved": report["safety"]["section_a_current360_approved120_preserved"],
    }

    report["deterministic_runtime_sha256"] = _base._digest({
        "forms": report["forms"],
        "active_items": report["active_items"],
        "runtime_bindings": report["runtime_bindings"],
    })
    return report


def build_unit04_fsv2_current360_contextual_form_runtime() -> dict[str, Any]:
    report = _apply_approved_section_a(_base.build_unit04_fsv2_current360_contextual_form_runtime())
    return _apply_short_message_meaning(report)


def compact_readback(report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        **_base.compact_readback(report),
        "section_a_binding_readback": report["section_a_binding_readback"],
        "short_message_binding_readback": report["short_message_binding_readback"],
        "section_a_safety": {
            key: report["safety"][key]
            for key in (
                "selected_at_default_guard_retained",
                "section_a_at_bounded_exception_count",
                "section_a_at_global_unlocked",
                "section_a_requires_current360_gpt5_6_operator_approval",
                "q31_d05_modified_by_section_a_cutover",
                "b_c_d_e_items_modified_by_section_a_cutover",
            )
        },
        "short_message_safety": {
            key: report["safety"][key]
            for key in (
                "q31_d05_modified_by_short_message_cutover",
                "e05_q39_modified_by_short_message_cutover",
                "d05_e05_current360_shared_context_preserved",
                "section_a_current360_approved120_preserved",
                "short_message_parallel_runtime_created",
                "a2_a2plus_unlocked_by_short_message_cutover",
            )
        },
    }


def main() -> int:
    print(json.dumps(compact_readback(build_unit04_fsv2_current360_contextual_form_runtime()), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
