from __future__ import annotations

import json
from collections import Counter
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


def build_unit04_fsv2_current360_contextual_form_runtime() -> dict[str, Any]:
    return _apply_approved_section_a(_base.build_unit04_fsv2_current360_contextual_form_runtime())


def compact_readback(report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        **_base.compact_readback(report),
        "section_a_binding_readback": report["section_a_binding_readback"],
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
    }


def main() -> int:
    print(json.dumps(compact_readback(build_unit04_fsv2_current360_contextual_form_runtime()), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
