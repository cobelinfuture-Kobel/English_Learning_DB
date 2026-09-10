from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any, Mapping

from product.a1fs_v1_2_1 import (
    u04fsv2_current360_contextual_form_runtime as fsv2,
)
from product.a1fs_v1_2_1 import (
    u04ms02c_ket_four_skill_task_assessment_projection as m2c,
)
from product.a1fs_v1_2_1 import (
    u04spv2_current360_speaking_cutover as spv2,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Acceptance-only integration over the already-active Unit04 FSV2 and SPV2 runtimes plus "
    "the existing formal KET prerequisite/task-shape projection. No learner content, canonical "
    "authority, Current360 episode, listening asset, or A2/A2+ scope is authored or modified."
)

PROGRAM_ID = "A1FS-V1"
UNIT_ID = "GRAMMAR_BASIC_PREPOSITIONS_PLACE"
TASK_ID = "A1FS-V1-U04RSWV2_ProductiveScoringAndCambridgeProgressionAcceptance"
STATUS = "PASS_A1FS_V1_U04RSWV2_PRODUCTIVE_SCORING_AND_CAMBRIDGE_PROGRESSION_ACCEPTANCE"
REVISION = "CURRENT360_PRODUCTIVE_SCORING_CAMBRIDGE_PROGRESSION_ACCEPTANCE_V2"
NEXT_SHORT_STEP = "A1FS-V1-U04VAV2_Current360LearnerFacingVisualPedagogicalAcceptance"

FORM_COUNT = 20
STAGE_ORDER = (
    "GUIDED",
    "REDUCED_SUPPORT",
    "INDEPENDENT",
    "TRANSFER",
    "RETENTION",
)
STAGE_FORM_RANGES = {
    "GUIDED": tuple(range(1, 5)),
    "REDUCED_SUPPORT": tuple(range(5, 9)),
    "INDEPENDENT": tuple(range(9, 13)),
    "TRANSFER": tuple(range(13, 17)),
    "RETENTION": tuple(range(17, 21)),
}
PRODUCTIVE_SCORING_MODE = "HUMAN_OR_SEMANTIC_REVIEW"
FORMAL_KET_TASK_SHAPE_AUTHORITY = "UNIT04_PROJECTED_SHAPE_NOT_OFFICIAL_KET_ITEM_FORMAT"
CAMBRIDGE_BOUNDARY_CLAIM = "PREREQUISITE_SKILL_SEED_NOT_OFFICIAL_CAMBRIDGE_EXAM_ITEM"


class Unit04RSWV2Error(ValueError):
    pass


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _build_sources() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    form_report = fsv2.build_unit04_fsv2_current360_contextual_form_runtime()
    if form_report.get("status") != fsv2.STATUS:
        raise Unit04RSWV2Error("FSV2_SOURCE_NOT_PASS")
    if form_report.get("cutover_contract", {}).get("active_form_runtime_authority") != fsv2.TASK_ID:
        raise Unit04RSWV2Error("FSV2_NOT_ACTIVE_FORM_RUNTIME")
    if form_report.get("cutover_contract", {}).get("parallel_active_form_runtime_allowed") is not False:
        raise Unit04RSWV2Error("FSV2_PARALLEL_ACTIVE_RUNTIME_ALLOWED")

    speaking_report = spv2.build_unit04_spv2_speaking_layer1_bridge_layer2_cutover()
    if speaking_report.get("status") != spv2.STATUS:
        raise Unit04RSWV2Error("SPV2_SOURCE_NOT_PASS")
    if speaking_report.get("cutover_contract", {}).get("active_speaking_runtime_authority") != spv2.TASK_ID:
        raise Unit04RSWV2Error("SPV2_NOT_ACTIVE_SPEAKING_RUNTIME")
    if speaking_report.get("cutover_contract", {}).get("parallel_active_speaking_runtime_allowed") is not False:
        raise Unit04RSWV2Error("SPV2_PARALLEL_ACTIVE_RUNTIME_ALLOWED")
    if speaking_report.get("source_authority", {}).get("active_form_runtime") != fsv2.TASK_ID:
        raise Unit04RSWV2Error("SPV2_FSV2_LINEAGE_DRIFT")

    ket_report = m2c.build_unit04_ket_four_skill_task_assessment_projection()
    if ket_report.get("status") != m2c.STATUS:
        raise Unit04RSWV2Error("M2C_FORMAL_KET_PROJECTION_NOT_PASS")
    return form_report, speaking_report, ket_report


def _validate_productive_scoring(form_report: Mapping[str, Any]) -> dict[str, Any]:
    rows = [
        row
        for row in form_report.get("active_items") or []
        if row.get("scoring_contract", {}).get("scoring_mode") == PRODUCTIVE_SCORING_MODE
    ]
    if not rows:
        raise Unit04RSWV2Error("FSV2_PRODUCTIVE_ROWS_MISSING")
    expected_count = int(form_report.get("coverage", {}).get("productive_response_count") or 0)
    if len(rows) != expected_count:
        raise Unit04RSWV2Error(
            f"FSV2_PRODUCTIVE_COUNT_DRIFT:{len(rows)}:{expected_count}"
        )

    section_counts = Counter(str(row["section"]) for row in rows)
    stage_counts = Counter(str(row["progression_stage"]) for row in rows)
    variant_counts = Counter(str(row["task_variant"]) for row in rows)
    expected_dimensions = set(fsv2.PRODUCTIVE_SCORING_DIMENSIONS)

    for row in rows:
        scoring = row["scoring_contract"]
        if scoring.get("single_answer_required") is not False:
            raise Unit04RSWV2Error(
                f"PRODUCTIVE_SINGLE_ANSWER_REQUIRED:{row['active_item_id']}"
            )
        if scoring.get("reference_response_nonexclusive") is not True:
            raise Unit04RSWV2Error(
                f"PRODUCTIVE_REFERENCE_EXCLUSIVE:{row['active_item_id']}"
            )
        if scoring.get("acceptable_paraphrase") is not True:
            raise Unit04RSWV2Error(
                f"PRODUCTIVE_PARAPHRASE_REJECTED:{row['active_item_id']}"
            )
        if set(scoring.get("dimensions") or []) != expected_dimensions:
            raise Unit04RSWV2Error(
                f"PRODUCTIVE_DIMENSION_DRIFT:{row['active_item_id']}"
            )
        if row.get("a2_grammar_introduced") is not False:
            raise Unit04RSWV2Error(
                f"PRODUCTIVE_A2_GRAMMAR_LEAK:{row['active_item_id']}"
            )
        if row.get("support_relations_assessed") is not False:
            raise Unit04RSWV2Error(
                f"PRODUCTIVE_SUPPORT_RELATION_PROMOTED:{row['active_item_id']}"
            )

    required_sections = {"B", "C", "D", "E"}
    if not required_sections.issubset(section_counts):
        raise Unit04RSWV2Error(
            "PRODUCTIVE_SECTION_COVERAGE_INCOMPLETE:"
            + ",".join(sorted(required_sections.difference(section_counts)))
        )
    if set(stage_counts) != set(STAGE_ORDER):
        raise Unit04RSWV2Error(
            f"PRODUCTIVE_STAGE_COVERAGE_DRIFT:{sorted(stage_counts)}"
        )

    return {
        "productive_response_count": len(rows),
        "productive_section_counts": dict(sorted(section_counts.items())),
        "productive_stage_counts": {
            stage: stage_counts[stage] for stage in STAGE_ORDER
        },
        "productive_task_variant_count": len(variant_counts),
        "scoring_mode": PRODUCTIVE_SCORING_MODE,
        "single_answer_required": False,
        "reference_response_nonexclusive": True,
        "acceptable_paraphrase": True,
        "dimensions": list(fsv2.PRODUCTIVE_SCORING_DIMENSIONS),
    }


def _validate_speaking_scoring(speaking_report: Mapping[str, Any]) -> dict[str, Any]:
    bridge = list(speaking_report.get("bridge_tasks") or [])
    layer2 = list(speaking_report.get("layer2_connected_speaking") or [])
    rows = bridge + layer2
    if len(bridge) != 80 or len(layer2) != 160 or len(rows) != 240:
        raise Unit04RSWV2Error(
            f"SPV2_PRODUCTIVE_DENOMINATOR_DRIFT:{len(bridge)}:{len(layer2)}"
        )

    mode_counts = Counter(str(row["speaking_mode"]) for row in rows)
    stage_counts = Counter(str(row["progression_stage"]) for row in rows)
    expected_dimensions = set(spv2.SPEAKING_SCORING_DIMENSIONS)
    fsv2_ids = {
        str(row["source_form_runtime_lineage"]["fsv2_active_item_id"])
        for row in rows
    }

    for row in rows:
        scoring = row["scoring_contract"]
        if scoring.get("scoring_mode") != PRODUCTIVE_SCORING_MODE:
            raise Unit04RSWV2Error(
                f"SPEAKING_SCORING_MODE_DRIFT:{row['speaking_task_id']}"
            )
        if scoring.get("single_answer_required") is not False:
            raise Unit04RSWV2Error(
                f"SPEAKING_SINGLE_ANSWER_REQUIRED:{row['speaking_task_id']}"
            )
        if scoring.get("reference_response_nonexclusive") is not True:
            raise Unit04RSWV2Error(
                f"SPEAKING_REFERENCE_EXCLUSIVE:{row['speaking_task_id']}"
            )
        if scoring.get("acceptable_paraphrase") is not True:
            raise Unit04RSWV2Error(
                f"SPEAKING_PARAPHRASE_REJECTED:{row['speaking_task_id']}"
            )
        if set(scoring.get("dimensions") or []) != expected_dimensions:
            raise Unit04RSWV2Error(
                f"SPEAKING_DIMENSION_DRIFT:{row['speaking_task_id']}"
            )
        required = set(scoring.get("required_dimensions") or [])
        if not required or not required.issubset(expected_dimensions):
            raise Unit04RSWV2Error(
                f"SPEAKING_REQUIRED_DIMENSION_INVALID:{row['speaking_task_id']}"
            )
        if scoring.get("audio_pronunciation_machine_score_required") is not False:
            raise Unit04RSWV2Error(
                f"SPEAKING_MACHINE_PRONUNCIATION_SCORE_REQUIRED:{row['speaking_task_id']}"
            )

    if set(stage_counts) != set(STAGE_ORDER):
        raise Unit04RSWV2Error(
            f"SPEAKING_STAGE_COVERAGE_DRIFT:{sorted(stage_counts)}"
        )

    return {
        "bridge_task_count": len(bridge),
        "layer2_task_count": len(layer2),
        "productive_speaking_task_count": len(rows),
        "distinct_speaking_mode_count": len(mode_counts),
        "speaking_mode_counts": dict(sorted(mode_counts.items())),
        "speaking_stage_counts": {
            stage: stage_counts[stage] for stage in STAGE_ORDER
        },
        "fsv2_source_item_ref_count": len(fsv2_ids),
        "scoring_mode": PRODUCTIVE_SCORING_MODE,
        "single_answer_required": False,
        "reference_response_nonexclusive": True,
        "acceptable_paraphrase": True,
        "dimensions": list(spv2.SPEAKING_SCORING_DIMENSIONS),
        "audio_pronunciation_machine_score_required": False,
    }


def _validate_cambridge_progression(
    form_report: Mapping[str, Any], speaking_report: Mapping[str, Any]
) -> dict[str, Any]:
    forms = list(form_report.get("forms") or [])
    if len(forms) != FORM_COUNT:
        raise Unit04RSWV2Error(f"FORM_COUNT_DRIFT:{len(forms)}")

    stage_form_counts: Counter[str] = Counter()
    for form in forms:
        form_number = int(form["form_number"])
        stage = str(form["progression_stage"])
        expected_stage = next(
            (
                candidate
                for candidate, numbers in STAGE_FORM_RANGES.items()
                if form_number in numbers
            ),
            None,
        )
        if expected_stage is None or stage != expected_stage:
            raise Unit04RSWV2Error(
                f"FORM_STAGE_DRIFT:F{form_number:02d}:{stage}:{expected_stage}"
            )
        contract = fsv2.STAGE_CONTRACT[stage]
        if form.get("support_level") != contract["support_level"]:
            raise Unit04RSWV2Error(f"FORM_SUPPORT_LEVEL_DRIFT:F{form_number:02d}")
        if form.get("context_exposure") != contract["context_exposure"]:
            raise Unit04RSWV2Error(f"FORM_CONTEXT_EXPOSURE_DRIFT:F{form_number:02d}")
        stage_form_counts[stage] += 1

    active_items = list(form_report.get("active_items") or [])
    if len(active_items) != 800:
        raise Unit04RSWV2Error(f"FSV2_ACTIVE_ITEM_COUNT_DRIFT:{len(active_items)}")
    section_claims: dict[str, dict[str, str]] = {}
    for section, expected in fsv2.CAMBRIDGE_ALIGNMENT.items():
        rows = [row for row in active_items if row.get("section") == section]
        if not rows:
            raise Unit04RSWV2Error(f"CAMBRIDGE_SECTION_MISSING:{section}")
        for row in rows:
            alignment = row.get("cambridge_prerequisite_alignment") or {}
            if alignment.get("yle") != expected["yle"]:
                raise Unit04RSWV2Error(
                    f"CAMBRIDGE_YLE_ALIGNMENT_DRIFT:{row['active_item_id']}"
                )
            if alignment.get("ket_prerequisite") != expected["ket_prerequisite"]:
                raise Unit04RSWV2Error(
                    f"CAMBRIDGE_KET_ALIGNMENT_DRIFT:{row['active_item_id']}"
                )
            if alignment.get("claim") != CAMBRIDGE_BOUNDARY_CLAIM:
                raise Unit04RSWV2Error(
                    f"CAMBRIDGE_BOUNDARY_CLAIM_DRIFT:{row['active_item_id']}"
                )
            if alignment.get("grammar_ceiling") != "A1":
                raise Unit04RSWV2Error(
                    f"CAMBRIDGE_GRAMMAR_CEILING_DRIFT:{row['active_item_id']}"
                )
            if alignment.get("a2_grammar_introduced") is not False:
                raise Unit04RSWV2Error(
                    f"CAMBRIDGE_A2_GRAMMAR_LEAK:{row['active_item_id']}"
                )
        section_claims[section] = dict(expected)

    speaking_rows = list(speaking_report.get("bridge_tasks") or []) + list(
        speaking_report.get("layer2_connected_speaking") or []
    )
    for row in speaking_rows:
        form_number = int(row["form_number"])
        expected_stage = next(
            stage for stage, numbers in STAGE_FORM_RANGES.items() if form_number in numbers
        )
        if row.get("progression_stage") != expected_stage:
            raise Unit04RSWV2Error(
                f"SPV2_FORM_STAGE_DRIFT:{row['speaking_task_id']}"
            )
        if form_number <= 12 and not str(row.get("context_exposure") or "").startswith("SEEN"):
            raise Unit04RSWV2Error(
                f"SPV2_EXPECTED_SEEN_CONTEXT:{row['speaking_task_id']}"
            )
        if form_number >= 13 and not str(row.get("context_exposure") or "").startswith("UNSEEN"):
            raise Unit04RSWV2Error(
                f"SPV2_EXPECTED_UNSEEN_CONTEXT:{row['speaking_task_id']}"
            )

    return {
        "form_count": len(forms),
        "stage_order": list(STAGE_ORDER),
        "stage_form_counts": {stage: stage_form_counts[stage] for stage in STAGE_ORDER},
        "stage_contract": {
            stage: {
                "forms": list(STAGE_FORM_RANGES[stage]),
                "support_level": fsv2.STAGE_CONTRACT[stage]["support_level"],
                "context_exposure": fsv2.STAGE_CONTRACT[stage]["context_exposure"],
            }
            for stage in STAGE_ORDER
        },
        "cambridge_section_alignment": section_claims,
        "cambridge_claim": CAMBRIDGE_BOUNDARY_CLAIM,
        "official_cambridge_item_format_claimed": False,
        "grammar_ceiling": "A1",
        "a2_grammar_introduced_count": 0,
        "seen_to_unseen_boundary_form": 13,
    }


def _validate_formal_ket_boundary(ket_report: Mapping[str, Any]) -> dict[str, Any]:
    summary = ket_report.get("projection_summary") or {}
    if summary.get("task_projection_count") != 144:
        raise Unit04RSWV2Error("FORMAL_KET_TASK_PROJECTION_COUNT_DRIFT")
    expected_distribution = {skill: 36 for skill in m2c.SKILLS}
    if summary.get("skill_distribution") != expected_distribution:
        raise Unit04RSWV2Error(
            f"FORMAL_KET_SKILL_DISTRIBUTION_DRIFT:{summary.get('skill_distribution')}"
        )

    formal = ket_report.get("formal_ket_reference") or {}
    if formal.get("authority_role") != m2c.FORMAL_KET_AUTHORITY_ROLE:
        raise Unit04RSWV2Error("FORMAL_KET_AUTHORITY_ROLE_DRIFT")
    if formal.get("learner_facing_authority") is not False:
        raise Unit04RSWV2Error("FORMAL_KET_PROMOTED_TO_LEARNER_AUTHORITY")
    if formal.get("canonical_promotion_allowed") is not False:
        raise Unit04RSWV2Error("FORMAL_KET_CANONICAL_PROMOTION_ALLOWED")

    tasks = list(ket_report.get("task_projections") or [])
    if len(tasks) != 144:
        raise Unit04RSWV2Error("FORMAL_KET_TASK_ROWS_DRIFT")
    for row in tasks:
        if row.get("task_shape_authority") != FORMAL_KET_TASK_SHAPE_AUTHORITY:
            raise Unit04RSWV2Error(
                f"FORMAL_KET_TASK_SHAPE_AUTHORITY_DRIFT:{row.get('task_projection_id')}"
            )
        boundary = row.get("authority_boundary") or {}
        if boundary.get("formal_ket_is_learner_facing_authority") is not False:
            raise Unit04RSWV2Error("FORMAL_KET_TASK_PROMOTED_TO_LEARNER_AUTHORITY")
        if boundary.get("formal_ket_canonical_promotion_allowed") is not False:
            raise Unit04RSWV2Error("FORMAL_KET_TASK_CANONICAL_PROMOTION_ALLOWED")
        if boundary.get("formal_ket_source_text_copied") is not False:
            raise Unit04RSWV2Error("FORMAL_KET_SOURCE_TEXT_COPIED")
        if boundary.get("a2_unlocked") is not False:
            raise Unit04RSWV2Error("FORMAL_KET_TASK_A2_UNLOCKED")

    return {
        "formal_ket_source_id": formal["source_id"],
        "formal_ket_authority_role": formal["authority_role"],
        "formal_ket_task_projection_count": len(tasks),
        "skill_distribution": expected_distribution,
        "formal_prerequisite_signals": sorted(
            {
                signal
                for row in tasks
                for signal in row.get("formal_prerequisite_signals") or []
            }
        ),
        "task_shape_authority": FORMAL_KET_TASK_SHAPE_AUTHORITY,
        "learner_facing_authority": False,
        "canonical_promotion_allowed": False,
        "formal_ket_source_text_copied": False,
        "a2_unlocked": False,
    }


def _validate_cross_runtime_lineage(
    form_report: Mapping[str, Any], speaking_report: Mapping[str, Any]
) -> dict[str, Any]:
    active_ids = {str(row["active_item_id"]) for row in form_report.get("active_items") or []}
    speaking_rows = list(speaking_report.get("bridge_tasks") or []) + list(
        speaking_report.get("layer2_connected_speaking") or []
    )
    refs = [
        str(row["source_form_runtime_lineage"]["fsv2_active_item_id"])
        for row in speaking_rows
    ]
    missing = sorted(set(refs).difference(active_ids))
    if missing:
        raise Unit04RSWV2Error(
            f"SPV2_FSV2_SOURCE_REF_MISSING:{len(missing)}:{missing[0]}"
        )
    if speaking_report.get("coverage", {}).get("seen_unseen_overlap_count") != 0:
        raise Unit04RSWV2Error("SPV2_SEEN_UNSEEN_OVERLAP")
    if form_report.get("coverage", {}).get("selected_seen_unseen_overlap_count") != 0:
        raise Unit04RSWV2Error("FSV2_SEEN_UNSEEN_OVERLAP")
    return {
        "fsv2_active_item_count": len(active_ids),
        "speaking_source_ref_occurrence_count": len(refs),
        "distinct_speaking_source_ref_count": len(set(refs)),
        "missing_speaking_source_ref_count": 0,
        "fsv2_seen_unseen_overlap_count": 0,
        "spv2_seen_unseen_overlap_count": 0,
    }


def _materialize() -> dict[str, Any]:
    form_report, speaking_report, ket_report = _build_sources()
    productive = _validate_productive_scoring(form_report)
    speaking = _validate_speaking_scoring(speaking_report)
    cambridge = _validate_cambridge_progression(form_report, speaking_report)
    formal_ket = _validate_formal_ket_boundary(ket_report)
    lineage = _validate_cross_runtime_lineage(form_report, speaking_report)

    if form_report.get("coverage", {}).get("a2_grammar_introduced_count") != 0:
        raise Unit04RSWV2Error("FSV2_A2_GRAMMAR_INTRODUCED")
    if speaking_report.get("coverage", {}).get("a2_grammar_introduced_count") != 0:
        raise Unit04RSWV2Error("SPV2_A2_GRAMMAR_INTRODUCED")
    if form_report.get("coverage", {}).get("assessed_support_relation_count") != 0:
        raise Unit04RSWV2Error("FSV2_SUPPORT_RELATION_ASSESSED")
    if speaking_report.get("coverage", {}).get("support_relation_assessed_count") != 0:
        raise Unit04RSWV2Error("SPV2_SUPPORT_RELATION_ASSESSED")

    requirements = {
        "01_fsv2_productive_scoring_semantic_and_paraphrase_aware": {
            "status": "PASS",
            "evidence": productive,
        },
        "02_spv2_productive_scoring_semantic_and_mode_specific": {
            "status": "PASS",
            "evidence": speaking,
        },
        "03_cambridge_a1_task_maturity_progression": {
            "status": "PASS",
            "evidence": cambridge,
        },
        "04_formal_ket_prerequisite_boundary_preserved": {
            "status": "PASS",
            "evidence": formal_ket,
        },
        "05_fsv2_spv2_form_bound_lineage": {
            "status": "PASS",
            "evidence": lineage,
        },
        "06_seen_to_unseen_transfer_and_retention_progression": {
            "status": "PASS",
            "evidence": {
                "forms_01_12": "SEEN_CONTEXT_PROGRESSIVE_SUPPORT_FADE",
                "forms_13_16": "UNSEEN_TRANSFER",
                "forms_17_20": "UNSEEN_RETENTION",
                "seen_unseen_overlap_count": 0,
            },
        },
        "07_a1_grammar_ceiling_preserved": {
            "status": "PASS",
            "evidence": {
                "grammar_ceiling": "A1",
                "fsv2_a2_grammar_introduced_count": 0,
                "spv2_a2_grammar_introduced_count": 0,
                "a2_a2plus_unlocked": False,
            },
        },
        "08_support_language_remains_non_assessed": {
            "status": "PASS",
            "evidence": {
                "fsv2_assessed_support_relation_count": 0,
                "spv2_assessed_support_relation_count": 0,
            },
        },
        "09_active_runtime_acceptance_is_deterministic_and_non_parallel": {
            "status": "PASS",
            "evidence": {
                "active_form_runtime": fsv2.TASK_ID,
                "active_speaking_runtime": spv2.TASK_ID,
                "parallel_active_form_runtime_allowed": False,
                "parallel_active_speaking_runtime_allowed": False,
            },
        },
        "10_learner_facing_visual_pedagogical_acceptance": {
            "status": "PENDING_NEXT_SHORT_STEP",
            "evidence": {
                "runtime_acceptance_complete": True,
                "actual_visual_review_claimed": False,
                "next_short_step": NEXT_SHORT_STEP,
            },
        },
    }

    result = {
        "schema_version": "a1fs.v1.u04.rswv2.productive_scoring_cambridge_progression_acceptance.v1",
        "program_id": PROGRAM_ID,
        "unit_id": UNIT_ID,
        "unit_number": 4,
        "task_id": TASK_ID,
        "status": STATUS,
        "revision": REVISION,
        "source_runtime": {
            "active_form_runtime": fsv2.TASK_ID,
            "active_speaking_runtime": spv2.TASK_ID,
            "formal_ket_projection": m2c.TASK_ID,
        },
        "acceptance": {
            "fsv2_productive_scoring": productive,
            "spv2_productive_scoring": speaking,
            "cambridge_progression": cambridge,
            "formal_ket_boundary": formal_ket,
            "cross_runtime_lineage": lineage,
        },
        "approved_requirements_10_of_10": requirements,
        "safety": {
            "acceptance_only_no_new_learner_content": True,
            "q01_q10_authority_modified": False,
            "fsv2_runtime_modified": False,
            "spv2_runtime_modified": False,
            "current360_episode_content_modified": False,
            "formal_ket_promoted_to_learner_authority": False,
            "official_cambridge_item_format_claimed": False,
            "support_relations_promoted_to_assessed_target": False,
            "a2_a2plus_unlocked": False,
            "listening_modified": False,
            "other_units_modified": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    result["deterministic_acceptance_sha256"] = _digest(
        {
            "source_runtime": result["source_runtime"],
            "acceptance": result["acceptance"],
            "approved_requirements_10_of_10": result["approved_requirements_10_of_10"],
            "safety": result["safety"],
            "next_short_step": result["next_short_step"],
        }
    )
    return result


def build_unit04_rswv2_productive_scoring_cambridge_progression_acceptance() -> dict[str, Any]:
    return _materialize()


def compact_readback(report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": report["status"],
        "revision": report["revision"],
        "source_runtime": report["source_runtime"],
        "acceptance": report["acceptance"],
        "approved_requirements_10_of_10": report["approved_requirements_10_of_10"],
        "safety": report["safety"],
        "next_short_step": report["next_short_step"],
        "deterministic_acceptance_sha256": report["deterministic_acceptance_sha256"],
    }


def main() -> int:
    report = build_unit04_rswv2_productive_scoring_cambridge_progression_acceptance()
    print(json.dumps(compact_readback(report), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
