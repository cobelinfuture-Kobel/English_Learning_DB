from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from product.a1fs_v1_2_1 import u04r360_b01_reader_acceptance as reader360
from product.a1fs_v1_2_1 import u04ms02b_ket99_dialogue_prompt_remediation_transfer_overlay as ket99
from product.a1fs_v1_2_1 import u04ms02c_ket_four_skill_task_assessment_projection as four_skill

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Metadata-only capability coverage projection over accepted Unit04 Reader360, "
    "existing KET99 public semantic-delivery metadata, and the existing formal "
    "KET four-skill prerequisite projection. No transcript prose, private payload, "
    "new learner-facing wording, canonical authority, Reader, or A2 content is produced."
)

TASK_ID = "A1FS-V1-U04R360-KET99FourSkillSRTCapabilityCoverageProjection"
STATUS = "PASS_A1FS_V1_U04R360_KET99_FOUR_SKILL_SRT_CAPABILITY_COVERAGE_PROJECTION"
SCHEMA_VERSION = "a1fs.v1.u04.reader360.ket99_four_skill_srt_capability_coverage_projection.v1"
UNIT_ID = "GRAMMAR_BASIC_PREPOSITIONS_PLACE"
DISPOSITIONS = ("COVERED", "MISSING", "LATER_UNIT")
READERS = ("CURRENT360", "SPOKEN360", "PATTERN360")

SOURCE_REFS = {
    "reader360_acceptance": "product/a1fs_v1_2_1/u04r360_b01_reader_acceptance.py",
    "ket99_semantic_delivery_overlay": "product/a1fs_v1_2_1/u04ms02b_ket99_dialogue_prompt_remediation_transfer_overlay.py",
    "formal_ket_four_skill_projection": "product/a1fs_v1_2_1/u04ms02c_ket_four_skill_task_assessment_projection.py",
    "ket99_public_content_units": "ulga/reports/ket_comp_transcript_final_consolidation/transcript_content_units.jsonl",
    "ket99_public_semantic_artifact": "ulga/reports/ket_comp_transcript_final_consolidation/normalized_transcript_semantic_artifact.jsonl",
}

FORMAL_ROWS: tuple[dict[str, Any], ...] = (
    {
        "capability_id": "KET4_READING_CONNECTED_CONTEXT_LOCATION_COMPREHENSION",
        "skill": "READING",
        "source_component": "SHORT_READING_LOCATION_EXTRACTION",
        "requirement": "UNDERSTAND_SHORT_CONNECTED_CONTEXT_AND_LOCATION_MEANING",
        "unit04_expected_now": True,
        "carriers": {"CURRENT360": "DIRECT", "SPOKEN360": "SUPPORT", "PATTERN360": "SUPPORT"},
        "evidence": ["CURRENT360_360_CONNECTED_PASSAGES"],
    },
    {
        "capability_id": "KET4_READING_DETAIL_LOCATION_EXTRACTION",
        "skill": "READING",
        "source_component": "SHORT_READING_LOCATION_EXTRACTION",
        "requirement": "EXTRACT_SPECIFIC_LOCATION_RELATION_FROM_SHORT_CONTEXT",
        "unit04_expected_now": True,
        "carriers": {"CURRENT360": "DIRECT", "SPOKEN360": "SUPPORT", "PATTERN360": "SUPPORT"},
        "evidence": ["CURRENT360_360_RELATION_BEARING_EPISODES"],
    },
    {
        "capability_id": "KET4_LISTENING_DIALOGUE_LANGUAGE_PRECURSOR",
        "skill": "LISTENING",
        "source_component": "LISTENING_LOCATION_EXTRACTION",
        "requirement": "UNDERSTAND_DIALOGUE_LANGUAGE_AND_LOCATION_QA_BEFORE_AUDIO_DECODING",
        "unit04_expected_now": True,
        "carriers": {"CURRENT360": "SUPPORT", "SPOKEN360": "DIRECT", "PATTERN360": "SUPPORT"},
        "evidence": ["SPOKEN360_360_DIALOGUES", "SPOKEN360_MIN_5_TURNS_PER_EPISODE"],
    },
    {
        "capability_id": "KET4_LISTENING_AUDIO_LOCATION_EXTRACTION",
        "skill": "LISTENING",
        "source_component": "LISTENING_LOCATION_EXTRACTION",
        "requirement": "DECODE_AUDIO_AND_IDENTIFY_LOCATION_RELATION",
        "unit04_expected_now": False,
        "carriers": {"CURRENT360": "NONE", "SPOKEN360": "SUPPORT", "PATTERN360": "NONE"},
        "evidence": ["FORMAL_RESOURCE_MODE_NO_AUDIO_BODY", "SPOKEN360_TEXT_ONLY"],
    },
    {
        "capability_id": "KET4_SPEAKING_LOCATION_QA",
        "skill": "SPEAKING",
        "source_component": "SPEAKING_LOCATION_QA_AND_TRANSFER",
        "requirement": "ASK_AND_ANSWER_LOCATION_QUESTIONS_IN_SHORT_INTERACTION",
        "unit04_expected_now": True,
        "carriers": {"CURRENT360": "SUPPORT", "SPOKEN360": "DIRECT", "PATTERN360": "DIRECT"},
        "evidence": ["SPOKEN360_360_DIALOGUES", "PATTERN_C_WHERE_QA_360", "PATTERN_D_CONFIRMATION_QA_360"],
    },
    {
        "capability_id": "KET4_SPEAKING_ALTERNATE_SCENE_TRANSFER",
        "skill": "SPEAKING",
        "source_component": "SPEAKING_LOCATION_QA_AND_TRANSFER",
        "requirement": "PRODUCE_LOCATION_LANGUAGE_IN_AN_ALTERNATE_UNSEEN_SCENE",
        "unit04_expected_now": False,
        "carriers": {"CURRENT360": "SUPPORT", "SPOKEN360": "SUPPORT", "PATTERN360": "SUPPORT"},
        "evidence": ["THIRTY_SIX_SCENES_AVAILABLE", "NO_READER_TRANSFER_PROMPT_OR_RESPONSE_CAPTURE"],
    },
    {
        "capability_id": "KET4_WRITING_CONTROLLED_LOCATION_DESCRIPTION",
        "skill": "WRITING",
        "source_component": "SHORT_WRITING_LOCATION_DESCRIPTION",
        "requirement": "FORM_COMPLETE_LOCATION_SENTENCES_FROM_EXISTING_SCENE_FACTS",
        "unit04_expected_now": True,
        "carriers": {"CURRENT360": "SUPPORT", "SPOKEN360": "SUPPORT", "PATTERN360": "DIRECT"},
        "evidence": ["PATTERN_A_DESCRIPTION_360", "PATTERN_B_POSSESSIVE_360", "PATTERN_F_ACTION_LOCATION_360"],
    },
    {
        "capability_id": "KET4_WRITING_INDEPENDENT_SHORT_RESPONSE",
        "skill": "WRITING",
        "source_component": "SHORT_WRITING_LOCATION_DESCRIPTION",
        "requirement": "WRITE_AN_INDEPENDENT_SHORT_RESPONSE_WITHOUT_MODEL_COPYING",
        "unit04_expected_now": False,
        "carriers": {"CURRENT360": "SUPPORT", "SPOKEN360": "SUPPORT", "PATTERN360": "SUPPORT"},
        "evidence": ["READER360_NOT_A_QUESTION_WORKSHEET", "NO_WRITTEN_RESPONSE_CAPTURE_IN_THREE_READERS"],
    },
)

KET99_ROWS: tuple[dict[str, Any], ...] = (
    {
        "capability_id": "KET99_GUIDED_DIALOGUE_LOCATION_QA",
        "skill": "SPEAKING",
        "source_component": "GUIDED_DIALOGUE",
        "requirement": "LOCATION_QA",
        "unit04_expected_now": True,
        "carriers": {"CURRENT360": "SUPPORT", "SPOKEN360": "DIRECT", "PATTERN360": "DIRECT"},
        "evidence": ["SPOKEN360_360_DIALOGUES", "PATTERN_C_D_QA_720_FAMILY_CHECKS"],
    },
    {
        "capability_id": "KET99_FOLLOW_UP_SCENE_DESCRIPTION_DETAIL_EXPANSION",
        "skill": "READING_WRITING_SPEAKING",
        "source_component": "FOLLOW_UP_PROMPT",
        "requirement": "SCENE_DESCRIPTION_AND_DETAIL_EXPANSION",
        "unit04_expected_now": True,
        "carriers": {"CURRENT360": "DIRECT", "SPOKEN360": "SUPPORT", "PATTERN360": "DIRECT"},
        "evidence": ["CURRENT360_CONNECTED_CONTEXT_360", "PATTERN_A_B_F_1080_FAMILY_CHECKS"],
    },
    {
        "capability_id": "KET99_RELATION_CONTRAST_DISCRIMINATION",
        "skill": "SPEAKING_WRITING",
        "source_component": "ERROR_REPAIR",
        "requirement": "RELATION_CONTRAST_AND_DISCRIMINATION",
        "unit04_expected_now": True,
        "carriers": {"CURRENT360": "SUPPORT", "SPOKEN360": "SUPPORT", "PATTERN360": "DIRECT"},
        "evidence": ["PATTERN_G_CONTRAST_OR_COMPARISON_360", "PATTERN_D_CONFIRMATION_360"],
    },
    {
        "capability_id": "KET99_ERROR_CORRECTION_RETRY_LOOP",
        "skill": "SPEAKING_WRITING",
        "source_component": "ERROR_REPAIR",
        "requirement": "DETECT_ERROR_CORRECT_AND_RETRY_OWN_RESPONSE",
        "unit04_expected_now": False,
        "carriers": {"CURRENT360": "NONE", "SPOKEN360": "SUPPORT", "PATTERN360": "SUPPORT"},
        "evidence": ["NO_READER_DIAGNOSIS_OR_RETRY_LOOP"],
    },
    {
        "capability_id": "KET99_ALTERNATE_SCENE_TRANSFER_PROMPT",
        "skill": "SPEAKING_WRITING",
        "source_component": "TRANSFER_PROMPT",
        "requirement": "TRANSFER_LOCATION_LANGUAGE_TO_ALTERNATE_SCENE",
        "unit04_expected_now": False,
        "carriers": {"CURRENT360": "SUPPORT", "SPOKEN360": "SUPPORT", "PATTERN360": "SUPPORT"},
        "evidence": ["THIRTY_SIX_SCENES_AVAILABLE", "NO_READER_TRANSFER_TASK"],
    },
)


class CoverageProjectionError(ValueError):
    pass


def _root(repo_root: Path | str | None) -> Path:
    return Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _validate_sources(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    readers = reader360.build_acceptance_report(root)
    if readers.get("status") != reader360.STATUS:
        raise CoverageProjectionError("reader360_acceptance_not_pass")
    if readers.get("materialized_episode_count") != 360:
        raise CoverageProjectionError("reader360_episode_count_drift")
    if readers.get("spoken_entry_count") != 360 or readers.get("pattern_entry_count") != 360:
        raise CoverageProjectionError("reader360_reader_count_drift")
    if readers.get("spoken_relation_alignment_count") != 360:
        raise CoverageProjectionError("spoken_relation_alignment_drift")
    if readers.get("pattern_family_semantic_count") != 2520:
        raise CoverageProjectionError("pattern_family_semantic_count_drift")

    k99 = ket99.build_unit04_ket99_dialogue_prompt_remediation_transfer_overlay(root)
    if k99.get("status") != ket99.STATUS:
        raise CoverageProjectionError("ket99_overlay_not_pass")
    ksum = k99.get("overlay_summary")
    if not isinstance(ksum, Mapping):
        raise CoverageProjectionError("ket99_overlay_summary_missing")
    if ksum.get("interaction_stage_count") != 144:
        raise CoverageProjectionError("ket99_interaction_stage_count_drift")
    if ksum.get("semantic_compatible_stage_count") != 144 or ksum.get("semantic_incompatible_stage_count") != 0:
        raise CoverageProjectionError("ket99_semantic_gate_drift")

    k4 = four_skill.build_unit04_ket_four_skill_task_assessment_projection(root)
    if k4.get("status") != four_skill.STATUS:
        raise CoverageProjectionError("four_skill_projection_not_pass")
    fsum = k4.get("projection_summary")
    if not isinstance(fsum, Mapping):
        raise CoverageProjectionError("four_skill_projection_summary_missing")
    if fsum.get("task_projection_count") != 144:
        raise CoverageProjectionError("four_skill_task_count_drift")
    if fsum.get("skill_distribution") != {skill: 36 for skill in four_skill.SKILLS}:
        raise CoverageProjectionError("four_skill_distribution_drift")

    listening_mode = four_skill.TASK_SHAPES["LISTENING"]["resource_mode"]
    if "NO_AUDIO_BODY" not in listening_mode:
        raise CoverageProjectionError("formal_listening_no_audio_boundary_missing")
    if ket99.UNIT04_TARGET_OPERATION != {
        "GUIDED_DIALOGUE": "LOCATION_QA",
        "FOLLOW_UP_PROMPT": "SCENE_DESCRIPTION_AND_DETAIL_EXPANSION",
        "ERROR_REPAIR": "RELATION_CONTRAST_AND_REPAIR",
        "TRANSFER_PROMPT": "ALTERNATE_SCENE_TRANSFER",
    }:
        raise CoverageProjectionError("ket99_unit04_target_operation_drift")
    return readers, k99, k4


def _materialize_row(source_family: str, spec: Mapping[str, Any]) -> dict[str, Any]:
    carriers = {reader: str(spec["carriers"].get(reader, "NONE")) for reader in READERS}
    invalid = [value for value in carriers.values() if value not in {"DIRECT", "SUPPORT", "NONE"}]
    if invalid:
        raise CoverageProjectionError("invalid_reader_carrier")
    direct = sorted(reader for reader, role in carriers.items() if role == "DIRECT")
    expected_now = bool(spec["unit04_expected_now"])
    disposition = "COVERED" if expected_now and direct else "MISSING" if expected_now else "LATER_UNIT"
    return {
        "capability_id": str(spec["capability_id"]),
        "source_family": source_family,
        "skill": str(spec["skill"]),
        "source_component": str(spec["source_component"]),
        "requirement": str(spec["requirement"]),
        "unit04_expected_now": expected_now,
        "reader_carriers": carriers,
        "direct_reader_carriers": direct,
        "evidence": list(spec["evidence"]),
        "disposition": disposition,
    }


def build_coverage_projection(repo_root: Path | str | None = None) -> dict[str, Any]:
    root = _root(repo_root)
    readers, k99, k4 = _validate_sources(root)

    rows = [
        *(_materialize_row("FORMAL_KET_FOUR_SKILL", spec) for spec in FORMAL_ROWS),
        *(_materialize_row("KET99_SRT_SEMANTIC_DELIVERY", spec) for spec in KET99_ROWS),
    ]
    if len({row["capability_id"] for row in rows}) != len(rows):
        raise CoverageProjectionError("coverage_capability_identity_duplicate")

    dispositions = Counter(row["disposition"] for row in rows)
    source_counts = Counter(row["source_family"] for row in rows)
    skill_counts = Counter(row["skill"] for row in rows)
    direct_carrier_counts = Counter(
        reader
        for row in rows
        for reader in row["direct_reader_carriers"]
    )
    expected_now_rows = [row for row in rows if row["unit04_expected_now"]]
    true_missing = [row for row in expected_now_rows if row["disposition"] == "MISSING"]

    result = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "status": STATUS,
        "unit_number": 4,
        "unit_id": UNIT_ID,
        "scope": {
            "coverage_projection_only": True,
            "classification_set": list(DISPOSITIONS),
            "new_reader_created": False,
            "reader360_content_modified": False,
            "questionbank_modified": False,
            "forms_modified": False,
            "runtime_modified": False,
            "audio_materialized": False,
            "unit05_plus_opened": False,
            "a2_a2plus_unlocked": False,
        },
        "source_refs": dict(SOURCE_REFS),
        "source_readback": {
            "reader360": {
                "status": readers["status"],
                "current360_episode_count": readers["source_current360_episode_count"],
                "spoken360_entry_count": readers["spoken_entry_count"],
                "pattern360_entry_count": readers["pattern_entry_count"],
                "spoken_relation_alignment_count": readers["spoken_relation_alignment_count"],
                "pattern_family_semantic_count": readers["pattern_family_semantic_count"],
            },
            "ket99": {
                "status": k99["status"],
                "interaction_stage_count": k99["overlay_summary"]["interaction_stage_count"],
                "semantic_compatible_stage_count": k99["overlay_summary"]["semantic_compatible_stage_count"],
                "semantic_incompatible_stage_count": k99["overlay_summary"]["semantic_incompatible_stage_count"],
                "target_operations": dict(ket99.UNIT04_TARGET_OPERATION),
                "private_transcript_body_read": False,
                "source_text_copied": False,
            },
            "formal_ket_four_skill": {
                "status": k4["status"],
                "task_projection_count": k4["projection_summary"]["task_projection_count"],
                "skill_distribution": dict(k4["projection_summary"]["skill_distribution"]),
                "listening_resource_mode": four_skill.TASK_SHAPES["LISTENING"]["resource_mode"],
                "official_item_wording_copied": False,
            },
        },
        "coverage_summary": {
            "capability_row_count": len(rows),
            "unit04_expected_now_count": len(expected_now_rows),
            "covered_count": dispositions["COVERED"],
            "missing_count": dispositions["MISSING"],
            "later_unit_count": dispositions["LATER_UNIT"],
            "true_unit04_missing_count": len(true_missing),
            "source_family_distribution": dict(sorted(source_counts.items())),
            "skill_distribution": dict(sorted(skill_counts.items())),
            "direct_reader_carrier_counts": {reader: direct_carrier_counts[reader] for reader in READERS},
            "unit04_reader360_sufficient_for_current_constraint_layer": len(true_missing) == 0,
        },
        "coverage_rows": rows,
        "claim_boundaries": {
            "covered_means_reader360_has_direct_carrier_for_unit04_expected_capability": True,
            "later_unit_means_not_required_of_unit04_reader360_now": True,
            "missing_requires_unit04_expected_now_and_no_direct_reader_carrier": True,
            "full_ket_four_skill_completion_claimed": False,
            "listening_audio_completion_claimed": False,
            "independent_writing_completion_claimed": False,
            "exam_simulation_completion_claimed": False,
        },
        "next_short_step": (
            "U04_READER360_COVERAGE_CLOSEOUT_NO_NEW_READER"
            if len(true_missing) == 0
            else "U04_READER360_TRUE_MISSING_CAPABILITY_REPAIR"
        ),
    }
    result["projection_sha256"] = _digest(result)
    return result


def compact_readback(projection: Mapping[str, Any]) -> dict[str, Any]:
    summary = projection["coverage_summary"]
    return {
        "status": projection["status"],
        "capability_row_count": summary["capability_row_count"],
        "covered_count": summary["covered_count"],
        "missing_count": summary["missing_count"],
        "later_unit_count": summary["later_unit_count"],
        "true_unit04_missing_count": summary["true_unit04_missing_count"],
        "unit04_reader360_sufficient_for_current_constraint_layer": summary[
            "unit04_reader360_sufficient_for_current_constraint_layer"
        ],
        "next_short_step": projection["next_short_step"],
        "projection_sha256": projection["projection_sha256"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    projection = build_coverage_projection(args.repo_root)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(projection, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print("U04R360_KET_COVERAGE_READBACK=" + json.dumps(compact_readback(projection), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
