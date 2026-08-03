#!/usr/bin/env python3
"""Allocate Unit01 scene exposures across skill, task angle, support and evidence roles.

Read-only with respect to the QuestionBank: consumes the validated U01QB08
rotation and emits a deterministic pedagogical allocation manifest. It also
reports whether the existing 12 pattern families can fully, partially, or not
yet support each requested task angle. No learner content is authored here.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_u01qb06_unit01_micro_scene_pool_inventory as scene_policy
from ulga.builders import build_a1fs_v1_u01qb08_unit01_twelve_form_scene_rotation as rotation_builder
from ulga.validators import validate_a1fs_v1_u01qb08_unit01_twelve_form_scene_rotation as rotation_validator

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Deterministic skill/task/support allocation over approved scene rotation; "
    "does not author learner content, mutate the 474-item QuestionBank, scoring, or learner state."
)
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB09_Unit01SceneSkillTaskAngleSupportAllocation"
SCHEMA_VERSION = "a1fs.v1.u01qb09.unit01_scene_skill_task_angle_support_allocation.v1"
PASS_STATUS = "PASS_A1FS_V1_U01QB09_UNIT01_SCENE_SKILL_TASK_ANGLE_SUPPORT_ALLOCATION"
UNIT_ID = "GRAMMAR_ARTICLES_BASIC"
DEFAULT_OUTPUT = Path("ulga/reports/a1fs_v1_u01qb09_unit01_scene_skill_task_angle_support_allocation.json")
NEXT_SHORT_STEP = "A1FS-V1-U01QB10_Unit01QuestionBankProductionAngleCoverageReconciliation"

ACTIVITIES_PER_SCENE = 5
SCORED_ACTIVITIES_PER_SCENE = 4
SPEAKING_PRACTICE_PER_SCENE = 1
EXPECTED_SCENE_EXPOSURES = 48
EXPECTED_ACTIVITY_SLOTS = EXPECTED_SCENE_EXPOSURES * ACTIVITIES_PER_SCENE
EXPECTED_SCORED_SLOTS = EXPECTED_SCENE_EXPOSURES * SCORED_ACTIVITIES_PER_SCENE
EXPECTED_SPEAKING_SLOTS = EXPECTED_SCENE_EXPOSURES * SPEAKING_PRACTICE_PER_SCENE

TASK_ANGLES = (
    "ARTICLE_CONTROL",
    "PHRASE_CONSTRUCTION",
    "WORD_ORDER",
    "ERROR_CHECK",
    "FIRST_MENTION_CONTEXT",
    "KNOWN_REFERENCE_CONTEXT",
    "REFERENCE_EVIDENCE",
    "CONTEXTUAL_REFERENCE_GAP",
    "COMPLETE_SENTENCE_PRODUCTION",
    "CONNECTED_SENTENCE_PRODUCTION",
    "SCENE_DESCRIPTION",
    "TRANSFER_DECISION",
)

BANK_BINDINGS: dict[tuple[str, str], dict[str, Any]] = {
    ("READING", "ARTICLE_CONTROL"): {"status": "FULL", "pattern_family_ids": ["U01-PF04-FIRST-MENTION-CONTEXT", "U01-PF08-TRANSFER-FIRST-MENTION"]},
    ("READING", "FIRST_MENTION_CONTEXT"): {"status": "FULL", "pattern_family_ids": ["U01-PF04-FIRST-MENTION-CONTEXT", "U01-PF08-TRANSFER-FIRST-MENTION"]},
    ("READING", "KNOWN_REFERENCE_CONTEXT"): {"status": "FULL", "pattern_family_ids": ["U01-PF05-KNOWN-REFERENCE-CONTEXT"]},
    ("READING", "ERROR_CHECK"): {"status": "FULL", "pattern_family_ids": ["U01-PF06-ERROR-DISCRIMINATION"]},
    ("READING", "REFERENCE_EVIDENCE"): {"status": "PARTIAL", "pattern_family_ids": ["U01-PF05-KNOWN-REFERENCE-CONTEXT"]},
    ("READING", "TRANSFER_DECISION"): {"status": "FULL", "pattern_family_ids": ["U01-PF08-TRANSFER-FIRST-MENTION"]},
    ("WRITING", "PHRASE_CONSTRUCTION"): {"status": "PARTIAL", "pattern_family_ids": ["U01-PF07-WORD-ORDER"]},
    ("WRITING", "WORD_ORDER"): {"status": "FULL", "pattern_family_ids": ["U01-PF07-WORD-ORDER"]},
    ("WRITING", "CONTEXTUAL_REFERENCE_GAP"): {"status": "FULL", "pattern_family_ids": ["U01-PF09-TRANSFER-KNOWN-REFERENCE"]},
    ("WRITING", "ERROR_CHECK"): {"status": "GAP", "pattern_family_ids": []},
    ("WRITING", "COMPLETE_SENTENCE_PRODUCTION"): {"status": "GAP", "pattern_family_ids": []},
    ("WRITING", "CONNECTED_SENTENCE_PRODUCTION"): {"status": "GAP", "pattern_family_ids": []},
    ("SPEAKING", "SCENE_DESCRIPTION"): {"status": "PARTIAL", "pattern_family_ids": ["U01-PF10-SPEAK-NOUN", "U01-PF11-SPEAK-ADJ-NOUN", "U01-PF12-SPEAK-VERY-ADJ-NOUN"]},
    ("SPEAKING", "COMPLETE_SENTENCE_PRODUCTION"): {"status": "GAP", "pattern_family_ids": []},
    ("SPEAKING", "CONNECTED_SENTENCE_PRODUCTION"): {"status": "GAP", "pattern_family_ids": []},
}

SUPPORT_PROFILES: dict[str, dict[str, Any]] = {
    "GUIDED": {
        "form_ordinals": [1, 2, 3], "purpose": "LEARNING", "prompt_perspective": "DISCOVERY",
        "evidence_class": "LEARNING_EVIDENCE",
        "candidates": {
            "READING": ["ARTICLE_CONTROL", "FIRST_MENTION_CONTEXT", "KNOWN_REFERENCE_CONTEXT", "ERROR_CHECK"],
            "WRITING": ["PHRASE_CONSTRUCTION", "WORD_ORDER", "CONTEXTUAL_REFERENCE_GAP", "ERROR_CHECK"],
            "SPEAKING": ["SCENE_DESCRIPTION", "COMPLETE_SENTENCE_PRODUCTION", "CONNECTED_SENTENCE_PRODUCTION"],
        },
    },
    "REDUCED_SUPPORT": {
        "form_ordinals": [4, 5, 6], "purpose": "PRACTICE", "prompt_perspective": "REFERENCE_USE",
        "evidence_class": "CONSOLIDATION_EVIDENCE",
        "candidates": {
            "READING": ["KNOWN_REFERENCE_CONTEXT", "ERROR_CHECK", "REFERENCE_EVIDENCE", "TRANSFER_DECISION", "ARTICLE_CONTROL", "FIRST_MENTION_CONTEXT"],
            "WRITING": ["CONTEXTUAL_REFERENCE_GAP", "WORD_ORDER", "ERROR_CHECK", "COMPLETE_SENTENCE_PRODUCTION", "PHRASE_CONSTRUCTION", "CONNECTED_SENTENCE_PRODUCTION"],
            "SPEAKING": ["SCENE_DESCRIPTION", "COMPLETE_SENTENCE_PRODUCTION", "CONNECTED_SENTENCE_PRODUCTION"],
        },
    },
    "INDEPENDENT": {
        "form_ordinals": [7, 8, 9], "purpose": "CONSOLIDATION", "prompt_perspective": "INDEPENDENT_USE",
        "evidence_class": "PERFORMANCE_EVIDENCE",
        "candidates": {
            "READING": ["REFERENCE_EVIDENCE", "TRANSFER_DECISION", "KNOWN_REFERENCE_CONTEXT", "ERROR_CHECK", "ARTICLE_CONTROL", "FIRST_MENTION_CONTEXT"],
            "WRITING": ["ERROR_CHECK", "COMPLETE_SENTENCE_PRODUCTION", "CONNECTED_SENTENCE_PRODUCTION", "CONTEXTUAL_REFERENCE_GAP", "PHRASE_CONSTRUCTION", "WORD_ORDER"],
            "SPEAKING": ["COMPLETE_SENTENCE_PRODUCTION", "CONNECTED_SENTENCE_PRODUCTION", "SCENE_DESCRIPTION"],
        },
    },
    "TRANSFER": {
        "form_ordinals": [10, 11, 12], "purpose": "ASSESSMENT_TRANSFER", "prompt_perspective": "UNSEEN_TRANSFER",
        "evidence_class": "MASTERY_QUALITY_EVIDENCE",
        "candidates": {
            "READING": ["TRANSFER_DECISION", "REFERENCE_EVIDENCE", "KNOWN_REFERENCE_CONTEXT", "ERROR_CHECK", "ARTICLE_CONTROL", "FIRST_MENTION_CONTEXT"],
            "WRITING": ["CONNECTED_SENTENCE_PRODUCTION", "COMPLETE_SENTENCE_PRODUCTION", "ERROR_CHECK", "CONTEXTUAL_REFERENCE_GAP", "PHRASE_CONSTRUCTION", "WORD_ORDER"],
            "SPEAKING": ["CONNECTED_SENTENCE_PRODUCTION", "COMPLETE_SENTENCE_PRODUCTION", "SCENE_DESCRIPTION"],
        },
    },
}


class AllocationError(ValueError):
    pass


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AllocationError(f"UNREADABLE_JSON:{path}:{exc}") from exc


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def support_for_form(form_ordinal: int) -> str:
    for support, profile in SUPPORT_PROFILES.items():
        if form_ordinal in profile["form_ordinals"]:
            return support
    raise AllocationError(f"FORM_SUPPORT_UNMAPPED:{form_ordinal}")


def choose_angles(support: str, skill: str, previous: set[str], count: int) -> list[str]:
    candidates = SUPPORT_PROFILES[support]["candidates"][skill]
    selected = [angle for angle in candidates if angle not in previous][:count]
    if len(selected) < count:
        selected.extend(angle for angle in candidates if angle not in selected)[: count - len(selected)]
    if len(selected) != count:
        raise AllocationError(f"TASK_ANGLE_CAPACITY_INSUFFICIENT:{support}:{skill}")
    return selected


def bank_binding(skill: str, angle: str) -> dict[str, Any]:
    binding = BANK_BINDINGS.get((skill, angle), {"status": "GAP", "pattern_family_ids": []})
    return deepcopy(binding)


def build_allocation(rotation: Mapping[str, Any]) -> dict[str, Any]:
    rotation_validator.validate(rotation)
    forms = rotation.get("forms")
    if not isinstance(forms, list) or len(forms) != rotation_builder.FORM_COUNT:
        raise AllocationError("VALIDATED_ROTATION_FORMS_REQUIRED")

    prior_angles: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    prior_package: dict[str, dict[str, Any]] = {}
    output_forms: list[dict[str, Any]] = []
    coverage_counts: Counter[str] = Counter()
    coverage_by_skill: dict[str, Counter[str]] = defaultdict(Counter)
    angle_counts: Counter[str] = Counter()
    support_counts: Counter[str] = Counter()
    skill_counts: Counter[str] = Counter()
    gap_angles: Counter[str] = Counter()

    for form in forms:
        form_ordinal = int(form["form_ordinal"])
        support = support_for_form(form_ordinal)
        profile = SUPPORT_PROFILES[support]
        scene_packages: list[dict[str, Any]] = []
        for scene_slot in form["scene_slots"]:
            ref = str(scene_slot["scene_ref_id"])
            previous_by_skill = prior_angles[ref]
            reading = choose_angles(support, "READING", previous_by_skill["READING"], 2)
            writing = choose_angles(support, "WRITING", previous_by_skill["WRITING"], 2)
            speaking = choose_angles(support, "SPEAKING", previous_by_skill["SPEAKING"], 1)
            assignments = [("READING", a) for a in reading] + [("WRITING", a) for a in writing] + [("SPEAKING", a) for a in speaking]
            activities: list[dict[str, Any]] = []
            for activity_index, (skill, angle) in enumerate(assignments, start=1):
                binding = bank_binding(skill, angle)
                scored = skill != "SPEAKING"
                coverage = str(binding["status"])
                coverage_counts[coverage] += 1
                coverage_by_skill[skill][coverage] += 1
                angle_counts[angle] += 1
                skill_counts[skill] += 1
                if coverage == "GAP":
                    gap_angles[angle] += 1
                activities.append({
                    "activity_id": f"{form['form_id']}-S{scene_slot['slot']:02d}-A{activity_index:02d}",
                    "activity_ordinal": activity_index,
                    "skill": skill,
                    "task_angle": angle,
                    "support_level": support,
                    "purpose": profile["purpose"],
                    "prompt_perspective": profile["prompt_perspective"],
                    "evidence_class": profile["evidence_class"],
                    "scored": scored,
                    "practice_only": skill == "SPEAKING",
                    "assessment_candidate": support == "TRANSFER" and scored,
                    "current_bank_support": coverage,
                    "pattern_family_ids": binding["pattern_family_ids"],
                })
            for skill, angles in (("READING", reading), ("WRITING", writing), ("SPEAKING", speaking)):
                previous_by_skill[skill].update(angles)

            previous = prior_package.get(ref)
            change_dimensions: list[str] = []
            if previous is not None:
                if previous["support_level"] != support:
                    change_dimensions.append("SUPPORT_LEVEL")
                if previous["prompt_perspective"] != profile["prompt_perspective"]:
                    change_dimensions.append("PROMPT_PERSPECTIVE")
                previous_pairs = {(row["skill"], row["task_angle"]) for row in previous["activities"]}
                current_pairs = {(row["skill"], row["task_angle"]) for row in activities}
                if previous_pairs != current_pairs:
                    change_dimensions.append("TASK_ANGLE")
                if previous_pairs & current_pairs:
                    raise AllocationError(f"SAME_SCENE_SKILL_TASK_ANGLE_REPLAY:{ref}")
                if len(change_dimensions) < rotation_builder.REUSED_SCENE_CHANGED_DIMENSIONS_MIN:
                    raise AllocationError(f"REUSED_SCENE_CHANGE_DIMENSIONS_BELOW_MIN:{ref}")

            package = {
                "scene_slot": int(scene_slot["slot"]),
                "scene_ref_id": ref,
                "semantic_scene_signature_v2": str(scene_slot["semantic_scene_signature_v2"]),
                "situation_family": str(scene_slot["situation_family"]),
                "setting": str(scene_slot["setting"]),
                "exposure_ordinal": int(scene_slot["exposure_ordinal"]),
                "support_level": support,
                "purpose": profile["purpose"],
                "prompt_perspective": profile["prompt_perspective"],
                "evidence_class": profile["evidence_class"],
                "reuse_change_dimensions": change_dimensions,
                "activity_count": len(activities),
                "scored_activity_count": sum(bool(row["scored"]) for row in activities),
                "speaking_practice_count": sum(row["skill"] == "SPEAKING" for row in activities),
                "activities": activities,
            }
            prior_package[ref] = deepcopy(package)
            scene_packages.append(package)
            support_counts[support] += 1

        output_forms.append({
            "form_id": form["form_id"],
            "form_ordinal": form_ordinal,
            "week": form["week"],
            "day_in_week": form["day_in_week"],
            "support_level": support,
            "purpose": profile["purpose"],
            "scene_count": len(scene_packages),
            "activity_count": sum(row["activity_count"] for row in scene_packages),
            "scored_activity_count": sum(row["scored_activity_count"] for row in scene_packages),
            "speaking_practice_count": sum(row["speaking_practice_count"] for row in scene_packages),
            "scene_packages": scene_packages,
        })

    scored_gap_count = sum(
        row["current_bank_support"] == "GAP" and row["scored"]
        for form in output_forms for scene in form["scene_packages"] for row in scene["activities"]
    )
    scored_partial_count = sum(
        row["current_bank_support"] == "PARTIAL" and row["scored"]
        for form in output_forms for scene in form["scene_packages"] for row in scene["activities"]
    )
    artifact: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "unit_id": UNIT_ID,
        "source_identity": {
            "rotation_task_id": rotation["task_id"],
            "rotation_sha256": rotation["rotation_sha256"],
            "approved_scene_artifact_sha256": rotation["source_identity"]["approved_scene_artifact_sha256"],
        },
        "allocation_policy": {
            "scene_exposure_count": EXPECTED_SCENE_EXPOSURES,
            "activities_per_scene": ACTIVITIES_PER_SCENE,
            "reading_per_scene": 2,
            "writing_per_scene": 2,
            "speaking_practice_per_scene": 1,
            "scored_activities_per_form": 16,
            "speaking_practice_per_form": 4,
            "speaking_assessment_eligible": False,
            "same_scene_same_skill_same_task_angle_repeat_allowed": False,
            "reused_scene_min_changed_dimensions": rotation_builder.REUSED_SCENE_CHANGED_DIMENSIONS_MIN,
            "support_progression": {support: profile["form_ordinals"] for support, profile in SUPPORT_PROFILES.items()},
            "task_angle_ids": list(TASK_ANGLES),
        },
        "task_angle_bank_bindings": [
            {"skill": skill, "task_angle": angle, **deepcopy(binding)}
            for (skill, angle), binding in sorted(BANK_BINDINGS.items())
        ],
        "forms": output_forms,
        "allocation_metrics": {
            "form_count": len(output_forms),
            "scene_exposure_count": sum(form["scene_count"] for form in output_forms),
            "activity_slot_count": sum(form["activity_count"] for form in output_forms),
            "scored_activity_slot_count": sum(form["scored_activity_count"] for form in output_forms),
            "speaking_practice_slot_count": sum(form["speaking_practice_count"] for form in output_forms),
            "skill_slot_counts": dict(sorted(skill_counts.items())),
            "support_scene_counts": dict(sorted(support_counts.items())),
            "task_angle_slot_counts": dict(sorted(angle_counts.items())),
            "current_bank_support_counts": dict(sorted(coverage_counts.items())),
            "current_bank_support_by_skill": {skill: dict(sorted(counts.items())) for skill, counts in sorted(coverage_by_skill.items())},
            "scored_partial_support_count": scored_partial_count,
            "scored_gap_count": scored_gap_count,
            "gap_task_angle_counts": dict(sorted(gap_angles.items())),
            "question_bank_full_alignment_ready": scored_gap_count == 0 and scored_partial_count == 0,
            "question_bank_reconciliation_required": scored_gap_count > 0 or scored_partial_count > 0,
        },
        "boundaries": {
            "scene_authority_modified": False,
            "new_scene_authored": False,
            "question_bank_modified": False,
            "question_items_materialized": False,
            "scoring_modified": False,
            "learner_state_modified": False,
            "speaking_scoring_enabled": False,
            "unit02_to_unit24_modified": False,
            "a2_unlocked": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    artifact["allocation_sha256"] = scene_policy.digest(artifact)
    return artifact


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rotation", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        artifact = build_allocation(read_json(args.rotation))
        write_json(args.output, artifact)
    except (AllocationError, rotation_validator.SceneRotationValidationError, KeyError, TypeError, ValueError, OSError) as exc:
        print("STATUS=FAIL_A1FS_V1_U01QB09_UNIT01_SCENE_SKILL_TASK_ANGLE_SUPPORT_ALLOCATION")
        print(f"ERROR={exc}")
        return 1
    metrics = artifact["allocation_metrics"]
    print(f"STATUS={PASS_STATUS}")
    print(f"FORMS={metrics['form_count']}")
    print(f"SCENE_EXPOSURES={metrics['scene_exposure_count']}")
    print(f"ACTIVITY_SLOTS={metrics['activity_slot_count']}")
    print(f"SCORED_SLOTS={metrics['scored_activity_slot_count']}")
    print(f"SPEAKING_PRACTICE_SLOTS={metrics['speaking_practice_slot_count']}")
    print(f"SCORED_PARTIAL_SUPPORT={metrics['scored_partial_support_count']}")
    print(f"SCORED_GAPS={metrics['scored_gap_count']}")
    print(f"QUESTION_BANK_FULL_ALIGNMENT_READY={metrics['question_bank_full_alignment_ready']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
