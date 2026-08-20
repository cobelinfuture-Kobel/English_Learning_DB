#!/usr/bin/env python3
"""Bind the Unit01 12-form blueprint to the existing U01QB02/M3/M6 runtime.

U01QB13 consumes the validated U01QB08 scene rotation, U01QB09 skill/task/support
allocation, and the active U01QB12 474-item runtime. It does not create a second
planner, learner database, item bank, response-capture engine, or scoring engine.

A logical form contains 20 blueprint activities: 8 Reading, 8 Writing, and four
Speaking practice cards. Execution remains inside the existing skill-specific M3
sessions. U01QB13 binds the required blueprint activities into the ordinary
U01QB02 session-plan/session-item tables; the remaining positions needed by the
legacy ten-item session container are support fillers and are not part of the
logical form or assessment denominator.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_online_v1_2_u01e_s01_unit01_five_context_authority_admission as s01
from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import build_a1fs_v1_u01qb02_unit01_approved_variant_session_runtime as qb02
from ulga.builders import build_a1fs_v1_u01qb08_unit01_twelve_form_scene_rotation as u01qb08
from ulga.builders import build_a1fs_v1_u01qb09_unit01_scene_skill_task_angle_support_allocation as u01qb09
from ulga.builders import build_a1fs_v1_u01qb10_unit01_question_bank_production_angle_coverage_reconciliation as u01qb10
from ulga.builders import build_a1fs_v1_u01qb12_unit01_reference_evidence_and_phrase_construction_partial_coverage_fullfix as u01qb12
from ulga.validators import validate_a1fs_v1_u01qb08_unit01_twelve_form_scene_rotation as u01qb08_validator
from ulga.validators import validate_a1fs_v1_u01qb09_unit01_scene_skill_task_angle_support_allocation as u01qb09_validator

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB13_Unit01TwelveFormRuntimeSelectionAndAssessmentBlueprintIntegration"
SCHEMA_VERSION = "a1fs.v1.u01qb13.unit01_twelve_form_runtime_selection_assessment_blueprint.v1"
PASS_STATUS = "PASS_A1FS_V1_U01QB13_UNIT01_TWELVE_FORM_RUNTIME_SELECTION_AND_ASSESSMENT_BLUEPRINT_INTEGRATION"
DECISION_REF = "OPERATOR_APPROVAL:2026-08-03:U01QB13"
UNIT_ID = u01qb12.UNIT_ID
FORM_COUNT = 12
SCENES_PER_FORM = 4
ACTIVITIES_PER_SCENE = 5
ACTIVITIES_PER_FORM = 20
SCORED_PER_FORM = 16
SPEAKING_PRACTICE_PER_FORM = 4
READING_PER_FORM = 8
WRITING_PER_FORM = 8
SPEAKING_PER_FORM = 4
EXPECTED_ACTIVITY_COUNT = 240
EXPECTED_SCORED_ACTIVITY_COUNT = 192
EXPECTED_SPEAKING_ACTIVITY_COUNT = 48
EXPECTED_RUNTIME_COUNT = 474
EXPECTED_EXTENSION_COUNT = 186
SUPPORT_FILLER_COUNTS = {"READING": 2, "WRITING": 2, "SPEAKING": 6}
ASSESSMENT_FORM_ORDINALS = (10, 11, 12)

PF04 = "U01-PF04-FIRST-MENTION-CONTEXT"
PF05 = "U01-PF05-KNOWN-REFERENCE-CONTEXT"
PF06 = "U01-PF06-ERROR-DISCRIMINATION"
PF07 = "U01-PF07-WORD-ORDER"
PF08 = "U01-PF08-TRANSFER-FIRST-MENTION"
PF09 = "U01-PF09-TRANSFER-KNOWN-REFERENCE"
PF10 = "U01-PF10-SPEAK-NOUN"
PF11 = "U01-PF11-SPEAK-ADJ-NOUN"
PF12 = "U01-PF12-SPEAK-VERY-ADJ-NOUN"
PF13 = u01qb10.PF13
PF14 = u01qb10.PF14
PF15 = u01qb10.PF15
PF16 = u01qb12.PF16
PF17 = u01qb12.PF17

# Exact scored bindings after U01QB12. Speaking remains practice-only; its
# sentence/connected-sentence angles are scene-projected practice prompts over
# existing speaking lexical anchors and never become scored bank claims.
EXACT_SCORED_BINDINGS: dict[tuple[str, str], tuple[str, ...]] = {
    ("READING", "ARTICLE_CONTROL"): (PF04, PF08),
    ("READING", "FIRST_MENTION_CONTEXT"): (PF04, PF08),
    ("READING", "KNOWN_REFERENCE_CONTEXT"): (PF05,),
    ("READING", "ERROR_CHECK"): (PF06,),
    ("READING", "REFERENCE_EVIDENCE"): (PF16,),
    ("READING", "TRANSFER_DECISION"): (PF08,),
    ("WRITING", "PHRASE_CONSTRUCTION"): (PF17,),
    ("WRITING", "WORD_ORDER"): (PF07,),
    ("WRITING", "CONTEXTUAL_REFERENCE_GAP"): (PF09,),
    ("WRITING", "ERROR_CHECK"): (PF13,),
    ("WRITING", "COMPLETE_SENTENCE_PRODUCTION"): (PF14,),
    ("WRITING", "CONNECTED_SENTENCE_PRODUCTION"): (PF15,),
}
SPEAKING_LEXICAL_FAMILIES = (PF10, PF11, PF12)
CONTEXT_BOUND_FAMILIES = frozenset((PF04, PF05, PF08, PF09, PF13, PF14, PF15, PF16))
FAMILY_CANONICAL_CONTEXT = {
    "SCHOOL": "U01-C1-CLASSROOM-BAG",
    "HOME": "U01-C2-HOME-TOY-BOX",
    "FOOD_SOCIAL": "U01-C3-PICNIC-FOOD",
    "SHOPPING": "U01-C4-TOY-SHOP",
    "OUTDOORS": "U01-C5-PARK-BIRTHDAY",
    "OUTDOORS_SOCIAL": "U01-C5-PARK-BIRTHDAY",
}
EXACT_CONTEXT = "EXACT_CONTEXT"
NEUTRAL_COMPATIBLE = "NEUTRAL_COMPATIBLE"
INCOMPATIBLE = "INCOMPATIBLE"
_SCENE_SEMANTIC_CACHE: tuple[object, dict[str, dict[str, Any]]] | None = None

# U01QB18H-R2R1 installs read-only learner-facing guards at this consumer
# boundary.  Keeping the hooks optional preserves the canonical U01QB13
# authority when the adapter is not installed, while making the guarded path
# explicit and testable instead of duplicating a second selector.
_SYSTEMIC_CANDIDATE_GUARD: Any = None
_SYSTEMIC_OPTION_PERMUTER: Any = None
_SYSTEMIC_FORM_OPTION_ALLOCATOR: Any = None


def install_systemic_candidate_guard(guard: Any) -> None:
    global _SYSTEMIC_CANDIDATE_GUARD
    _SYSTEMIC_CANDIDATE_GUARD = guard


def install_systemic_option_permuter(permuter: Any) -> None:
    global _SYSTEMIC_OPTION_PERMUTER
    _SYSTEMIC_OPTION_PERMUTER = permuter


def install_systemic_form_option_allocator(allocator: Any) -> None:
    """Install the optional learner-facing form-level option allocator."""
    global _SYSTEMIC_FORM_OPTION_ALLOCATOR
    _SYSTEMIC_FORM_OPTION_ALLOCATOR = allocator

SUPPLEMENT_PATH = Path(__file__).resolve().parents[1] / "contracts/a1fs_v1_u01qb07_unit01_model_authored_scene_supplement.json"
DEFAULT_CANDIDATE = Path("ulga/private/a1fs_v1_u01qb13_unit01_runtime_blueprint.candidate.private.json")
DEFAULT_APPROVED = Path("ulga/private/a1fs_v1_u01qb13_unit01_runtime_blueprint.approved.private.json")
DEFAULT_REPORT = Path("ulga/reports/a1fs_v1_u01qb13_unit01_runtime_blueprint_integration.json")
NEXT_SHORT_STEP = "A1FS-V1-U01QB14_Unit01TwelveFormPrivateProductionReplayAndLearnerFormAcceptance"

BLUEPRINT_SQL = """
CREATE TABLE IF NOT EXISTS u01qb13_metadata(
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS u01qb13_blueprint_activities(
  activity_id TEXT PRIMARY KEY,
  form_id TEXT NOT NULL,
  form_ordinal INTEGER NOT NULL CHECK(form_ordinal BETWEEN 1 AND 12),
  scene_ref_id TEXT NOT NULL,
  situation_family TEXT NOT NULL,
  setting TEXT NOT NULL,
  skill TEXT NOT NULL CHECK(skill IN ('READING','WRITING','SPEAKING')),
  task_angle TEXT NOT NULL,
  support_level TEXT NOT NULL,
  scored INTEGER NOT NULL CHECK(scored IN (0,1)),
  assessment_candidate INTEGER NOT NULL CHECK(assessment_candidate IN (0,1)),
  pattern_family_ids_json TEXT NOT NULL,
  scene_anchors_json TEXT NOT NULL,
  practice_projection_json TEXT NOT NULL,
  activity_digest TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS u01qb13_session_bindings(
  session_id TEXT NOT NULL REFERENCES u01qb02_session_plans(session_id),
  activity_id TEXT NOT NULL REFERENCES u01qb13_blueprint_activities(activity_id),
  item_id TEXT NOT NULL REFERENCES u01qb02_item_catalog(item_id),
  item_position INTEGER NOT NULL CHECK(item_position BETWEEN 1 AND 10),
  binding_quality TEXT NOT NULL,
  is_assessment_evidence INTEGER NOT NULL CHECK(is_assessment_evidence IN (0,1)),
  PRIMARY KEY(session_id,activity_id),
  UNIQUE(session_id,item_id),
  UNIQUE(session_id,item_position)
);
"""


class BlueprintIntegrationError(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def timestamp(value: str | None = None) -> str:
    return qb02.timestamp(value)


def write_json(path: Path, value: Mapping[str, Any], *, private: bool = False) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    if private:
        try:
            path.chmod(0o600)
        except OSError:
            pass


def _words(value: str) -> set[str]:
    return set(re.findall(r"[a-z]+", str(value).casefold().replace("_", " ")))


def _active_nouns() -> set[str]:
    return {str(row["lemma"]).casefold() for row in u01qb10.seed.nouns()}


def _scene_semantic_index() -> dict[str, dict[str, Any]]:
    active = _active_nouns()
    result: dict[str, dict[str, Any]] = {}
    for context in s01.CONTEXTS:
        text = " ".join(str(row) for row in context["sentences"])
        anchors = sorted(_words(text) & active)
        if not anchors:
            raise BlueprintIntegrationError(f"CANONICAL_SCENE_ANCHORS_MISSING:{context['context_id']}")
        result[str(context["context_id"])] = {
            "scene_ref_id": str(context["context_id"]),
            "objects": anchors,
            "anchors": anchors,
            "setting": str(context["setting"]),
            "source": "CANONICAL_CONTEXT",
            "event": str(context["title"]),
        }
    try:
        supplement = json.loads(SUPPLEMENT_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BlueprintIntegrationError(f"SCENE_SUPPLEMENT_UNREADABLE:{exc}") from exc
    for candidate in supplement.get("candidates", []):
        ref = str(candidate.get("candidate_id") or "")
        if not ref:
            continue
        object_words = {str(row).casefold() for row in candidate.get("objects", [])}
        setting_words = _words(str(candidate.get("medium_setting") or ""))
        anchors = sorted((object_words | setting_words) & active)
        if not anchors:
            raise BlueprintIntegrationError(f"MODEL_SCENE_ANCHORS_MISSING:{ref}")
        result[ref] = {
            "scene_ref_id": ref,
            "objects": sorted(object_words),
            "anchors": anchors,
            "setting": str(candidate.get("medium_setting") or ""),
            "source": "MODEL_AUTHORED_APPROVED_SCENE",
            "event": str(candidate.get("small_micro_scene_event") or ""),
            "action": list(candidate.get("actions") or []),
            "relations": list(candidate.get("relations") or []),
            "communicative_goal": str(candidate.get("communicative_goal") or ""),
        }
    return result


def _practice_projection(angle: str, semantics: Mapping[str, Any]) -> dict[str, Any]:
    anchors = list(semantics.get("anchors") or [])
    noun = anchors[0]
    if angle == "SCENE_DESCRIPTION":
        prompt = f"Say one short sentence about the {noun} in this scene."
    elif angle == "COMPLETE_SENTENCE_PRODUCTION":
        prompt = f"Say one complete sentence. Introduce the {noun} in this scene."
    elif angle == "CONNECTED_SENTENCE_PRODUCTION":
        prompt = f"Say two connected sentences. Introduce the {noun}, then mention the same {noun} again."
    else:
        raise BlueprintIntegrationError(f"SPEAKING_ANGLE_UNSUPPORTED:{angle}")
    return {
        "projection_mode": "SCENE_PROJECTED_PRACTICE_ONLY",
        "prompt": prompt,
        "capture_enabled": False,
        "assessment_eligible": False,
        "scoring_enabled": False,
        "lexical_anchor": noun,
    }


def build_blueprint_payload(rotation: Mapping[str, Any], allocation: Mapping[str, Any]) -> dict[str, Any]:
    u01qb08_validator.validate(rotation)
    u01qb09_validator.validate(allocation)
    if rotation.get("unit_id") != UNIT_ID or allocation.get("unit_id") != UNIT_ID:
        raise BlueprintIntegrationError("UNIT_IDENTITY_INVALID")
    if len(rotation.get("forms") or []) != FORM_COUNT or len(allocation.get("forms") or []) != FORM_COUNT:
        raise BlueprintIntegrationError("FORM_COUNT_INVALID")
    semantics_index = _scene_semantic_index()
    rotation_by_form = {str(row["form_id"]): row for row in rotation["forms"]}
    activities: list[dict[str, Any]] = []
    form_summaries: list[dict[str, Any]] = []
    scored_binding_counts: Counter[str] = Counter()
    speaking_angle_counts: Counter[str] = Counter()

    for form in allocation["forms"]:
        form_id = str(form["form_id"])
        form_ordinal = int(form["form_ordinal"])
        rotation_form = rotation_by_form.get(form_id)
        if rotation_form is None:
            raise BlueprintIntegrationError(f"ROTATION_FORM_MISSING:{form_id}")
        expected_scene_refs = [str(row["scene_ref_id"]) for row in rotation_form["scene_slots"]]
        actual_scene_refs = [str(row["scene_ref_id"]) for row in form["scene_packages"]]
        if expected_scene_refs != actual_scene_refs:
            raise BlueprintIntegrationError(f"FORM_SCENE_ORDER_DRIFT:{form_id}")
        form_activity_ids: list[str] = []
        form_scored = 0
        form_speaking = 0
        for scene in form["scene_packages"]:
            ref = str(scene["scene_ref_id"])
            semantics = semantics_index.get(ref)
            if semantics is None:
                raise BlueprintIntegrationError(f"SCENE_SEMANTICS_MISSING:{ref}")
            for source_activity in scene["activities"]:
                skill = str(source_activity["skill"])
                angle = str(source_activity["task_angle"])
                scored = bool(source_activity["scored"])
                if skill == "SPEAKING":
                    if scored:
                        raise BlueprintIntegrationError(f"SPEAKING_SCORED_DRIFT:{source_activity['activity_id']}")
                    families = list(SPEAKING_LEXICAL_FAMILIES)
                    projection = _practice_projection(angle, semantics)
                    binding_mode = "SCENE_PROJECTED_PRACTICE_OVER_EXISTING_SPEAKING_ANCHOR"
                    speaking_angle_counts[angle] += 1
                else:
                    families = list(EXACT_SCORED_BINDINGS.get((skill, angle), ()))
                    if not scored or not families:
                        raise BlueprintIntegrationError(f"SCORED_EXACT_BINDING_MISSING:{skill}:{angle}")
                    projection = {}
                    binding_mode = "EXACT_CANONICAL_QUESTIONBANK_BINDING"
                    scored_binding_counts[f"{skill}:{angle}"] += 1
                assessment = form_ordinal in ASSESSMENT_FORM_ORDINALS and scored
                row = {
                    "activity_id": str(source_activity["activity_id"]),
                    "form_id": form_id,
                    "form_ordinal": form_ordinal,
                    "week": int(form["week"]),
                    "day_in_week": int(form["day_in_week"]),
                    "scene_ref_id": ref,
                    "situation_family": str(scene["situation_family"]),
                    "setting": str(scene["setting"]),
                    "scene_event": str(semantics.get("event") or ""),
                    "scene_anchors": list(semantics["anchors"]),
                    "skill": skill,
                    "task_angle": angle,
                    "support_level": str(source_activity["support_level"]),
                    "purpose": str(source_activity["purpose"]),
                    "evidence_class": str(source_activity["evidence_class"]),
                    "prompt_perspective": str(source_activity["prompt_perspective"]),
                    "scored": scored,
                    "practice_only": not scored,
                    "assessment_candidate": assessment,
                    "allowed_pattern_family_ids": families,
                    "binding_mode": binding_mode,
                    "practice_projection": projection,
                }
                row["activity_digest"] = digest(row)
                activities.append(row)
                form_activity_ids.append(row["activity_id"])
                form_scored += int(scored)
                form_speaking += int(skill == "SPEAKING")
        if len(form_activity_ids) != ACTIVITIES_PER_FORM or form_scored != SCORED_PER_FORM or form_speaking != SPEAKING_PER_FORM:
            raise BlueprintIntegrationError(f"FORM_ACTIVITY_DENOMINATOR_INVALID:{form_id}:{len(form_activity_ids)}:{form_scored}:{form_speaking}")
        form_summaries.append(
            {
                "form_id": form_id,
                "form_ordinal": form_ordinal,
                "week": int(form["week"]),
                "day_in_week": int(form["day_in_week"]),
                "support_level": str(form["support_level"]),
                "purpose": str(form["purpose"]),
                "scene_count": len(form["scene_packages"]),
                "activity_count": len(form_activity_ids),
                "reading_activity_count": 8,
                "writing_activity_count": 8,
                "speaking_practice_count": 4,
                "scored_activity_count": 16,
                "formal_assessment_mode": form_ordinal in ASSESSMENT_FORM_ORDINALS,
                "assessment_scored_activity_count": 16 if form_ordinal in ASSESSMENT_FORM_ORDINALS else 0,
                "speaking_assessment_activity_count": 0,
                "activity_ids": form_activity_ids,
            }
        )

    if len(activities) != EXPECTED_ACTIVITY_COUNT:
        raise BlueprintIntegrationError(f"ACTIVITY_COUNT_INVALID:{len(activities)}")
    scored_count = sum(bool(row["scored"]) for row in activities)
    speaking_count = sum(row["skill"] == "SPEAKING" for row in activities)
    if scored_count != EXPECTED_SCORED_ACTIVITY_COUNT or speaking_count != EXPECTED_SPEAKING_ACTIVITY_COUNT:
        raise BlueprintIntegrationError("ACTIVITY_SKILL_DENOMINATOR_INVALID")
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "unit_id": UNIT_ID,
        "source_identity": {
            "rotation_task_id": rotation["task_id"],
            "rotation_sha256": rotation["rotation_sha256"],
            "allocation_task_id": allocation["task_id"],
            "allocation_sha256": allocation["allocation_sha256"],
            "active_question_bank_revision": u01qb12.CANONICAL_REVISION,
            "runtime_authority": qb02.TASK_ID,
        },
        "execution_contract": {
            "logical_form_count": FORM_COUNT,
            "scenes_per_form": SCENES_PER_FORM,
            "activities_per_form": ACTIVITIES_PER_FORM,
            "reading_per_form": READING_PER_FORM,
            "writing_per_form": WRITING_PER_FORM,
            "speaking_practice_per_form": SPEAKING_PER_FORM,
            "scored_per_form": SCORED_PER_FORM,
            "existing_u01qb02_session_size": qb02.SESSION_SIZE,
            "skill_session_execution_containers_per_form": 3,
            "support_filler_counts_per_skill_session": deepcopy(SUPPORT_FILLER_COUNTS),
            "support_fillers_are_form_activities": False,
            "support_fillers_are_assessment_evidence": False,
            "second_planner_created": False,
            "second_runtime_created": False,
        },
        "assessment_blueprint": {
            "assessment_form_ordinals": list(ASSESSMENT_FORM_ORDINALS),
            "assessment_form_count": len(ASSESSMENT_FORM_ORDINALS),
            "scored_reading_per_assessment_form": 8,
            "scored_writing_per_assessment_form": 8,
            "speaking_practice_per_assessment_form": 4,
            "speaking_scored": False,
            "assessment_evidence_class": "MASTERY_QUALITY_EVIDENCE",
            "assessment_requires_unseen_runtime_item_when_available": True,
            "assessment_requires_scene_anchor_binding": True,
        },
        "form_summaries": form_summaries,
        "activities": activities,
        "coverage_readback": {
            "activity_count": len(activities),
            "scored_activity_count": scored_count,
            "speaking_practice_activity_count": speaking_count,
            "scored_exact_binding_count": scored_count,
            "scored_unbound_count": 0,
            "speaking_projected_practice_count": speaking_count,
            "speaking_capture_enabled_count": 0,
            "question_bank_total": EXPECTED_RUNTIME_COUNT,
            "question_bank_expanded": False,
            "scored_task_angle_counts": dict(sorted(scored_binding_counts.items())),
            "speaking_task_angle_counts": dict(sorted(speaking_angle_counts.items())),
        },
        "boundaries": {
            "new_scene_authored": False,
            "question_bank_total_expanded": False,
            "real62_extension_modified": False,
            "second_planner_created": False,
            "second_runtime_created": False,
            "parallel_database_created": False,
            "parallel_scoring_created": False,
            "speaking_capture_enabled": False,
            "speaking_scoring_enabled": False,
            "unit02_to_unit24_modified": False,
            "a2_unlocked": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    payload["blueprint_sha256"] = digest(payload)
    return payload


def build_candidate(rotation: Mapping[str, Any], allocation: Mapping[str, Any]) -> dict[str, Any]:
    payload = build_blueprint_payload(rotation, allocation)
    return policy_artifact.build_candidate(
        payload=payload,
        producer_id=TASK_ID,
        level_scope=["A1"],
        source_bindings={
            "rotation_sha256": payload["source_identity"]["rotation_sha256"],
            "allocation_sha256": payload["source_identity"]["allocation_sha256"],
            "active_question_bank_revision": u01qb12.CANONICAL_REVISION,
            "runtime_task_id": qb02.TASK_ID,
            "operator_decision_ref": DECISION_REF,
        },
    )


def admit_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    from ulga.validators import validate_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration as validator

    receipt = validator.validate_candidate(candidate)
    return policy_artifact.admit_candidate(
        candidate,
        validation_receipts=[receipt],
        decision_ref=DECISION_REF,
        producer_id=TASK_ID,
    )


def _require_table(connection: sqlite3.Connection, table: str) -> None:
    if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is None:
        raise BlueprintIntegrationError(f"REQUIRED_TABLE_MISSING:{table}")


def install_blueprint(database: Path, approved: Mapping[str, Any]) -> dict[str, Any]:
    database = Path(database)
    if not database.is_file():
        raise BlueprintIntegrationError("LEARNER_DATABASE_MISSING")
    from ulga.validators import validate_a1fs_v1_policy_bound_content_artifact as policy_validator

    policy_validator.validate_artifact(approved, expected_role=policy_artifact.APPROVED_ROLE)
    payload = approved.get("payload")
    if not isinstance(payload, Mapping) or payload.get("task_id") != TASK_ID:
        raise BlueprintIntegrationError("APPROVED_BLUEPRINT_IDENTITY_INVALID")
    runtime = qb02.Unit01ApprovedVariantSessionRuntime(database)
    with runtime.write() as connection:
        connection.row_factory = sqlite3.Row
        for table in ("metadata", "u01qb02_item_catalog", "u01qb02_session_plans", "u01qb02_session_items", "response_contracts", "razq01e_extension_items", "u01qb12_metadata"):
            _require_table(connection, table)
        if connection.execute("SELECT COUNT(*) FROM u01qb02_item_catalog").fetchone()[0] != EXPECTED_RUNTIME_COUNT:
            raise BlueprintIntegrationError("RUNTIME_DENOMINATOR_INVALID")
        if connection.execute("SELECT COUNT(*) FROM razq01e_extension_items").fetchone()[0] != EXPECTED_EXTENSION_COUNT:
            raise BlueprintIntegrationError("REAL62_DENOMINATOR_INVALID")
        u12_meta = dict(connection.execute("SELECT key,value FROM u01qb12_metadata"))
        if u12_meta.get("validation_status") != u01qb12.PASS_STATUS:
            raise BlueprintIntegrationError("U01QB12_RUNTIME_NOT_ACTIVE")
        connection.executescript(BLUEPRINT_SQL)
        connection.execute("DELETE FROM u01qb13_blueprint_activities")
        for row in payload["activities"]:
            connection.execute(
                """INSERT INTO u01qb13_blueprint_activities
                (activity_id,form_id,form_ordinal,scene_ref_id,situation_family,setting,skill,task_angle,
                 support_level,scored,assessment_candidate,pattern_family_ids_json,scene_anchors_json,
                 practice_projection_json,activity_digest)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    row["activity_id"], row["form_id"], row["form_ordinal"], row["scene_ref_id"],
                    row["situation_family"], row["setting"], row["skill"], row["task_angle"],
                    row["support_level"], int(row["scored"]), int(row["assessment_candidate"]),
                    canonical(row["allowed_pattern_family_ids"]), canonical(row["scene_anchors"]),
                    canonical(row["practice_projection"]), row["activity_digest"],
                ),
            )
        metadata = {
            "task_id": TASK_ID,
            "schema_version": SCHEMA_VERSION,
            "validation_status": PASS_STATUS,
            "approved_blueprint_artifact_sha256": str(approved["artifact_sha256"]),
            "blueprint_sha256": str(payload["blueprint_sha256"]),
            "activity_count": str(EXPECTED_ACTIVITY_COUNT),
            "form_count": str(FORM_COUNT),
            "runtime_item_count": str(EXPECTED_RUNTIME_COUNT),
            "second_planner_created": "false",
            "second_runtime_created": "false",
            "speaking_scoring_enabled": "false",
            "next_short_step": NEXT_SHORT_STEP,
        }
        connection.executemany("INSERT OR REPLACE INTO u01qb13_metadata(key,value) VALUES(?,?)", metadata.items())
    return {
        "validation_status": PASS_STATUS,
        "installed_activity_count": EXPECTED_ACTIVITY_COUNT,
        "form_count": FORM_COUNT,
        "runtime_item_count": EXPECTED_RUNTIME_COUNT,
        "second_planner_created": False,
        "second_runtime_created": False,
        "speaking_scoring_enabled": False,
    }


def _item_context_id(item: Mapping[str, Any]) -> str:
    return str(
        item.get("context_id")
        or (item.get("lexical_slots") or {}).get("context_id")
        or ""
    )


def _approved_context_neutral_evidence(item: Mapping[str, Any]) -> bool:
    source_refs = item.get("source_refs") or []
    return bool(
        str(item.get("skill") or "").upper() == "READING"
        and str(item.get("pattern_family_id") or "") == PF04
        and not _item_context_id(item)
       and str(item.get("content_kind") or "") in {"MICRO_SCENE", "SHORT_DIALOGUE"}
       and str(item.get("content_lineage_mode") or "")
           in {
               "SEMANTIC_ANCHOR_A1_IMITATION",
               "PROJECT_AUTHORED_CONTRACT_COMPLETION",
               "SEMANTIC_EQUIVALENT",
           }
        and str(item.get("content_asset_id") or "")
        and any(
            isinstance(source, Mapping)
            and str(source.get("source_type") or "")
            == "RAZQ01D_APPROVED_CONTENT_ASSET"
            for source in source_refs
        )
    )


def _cached_scene_semantic_index() -> dict[str, dict[str, Any]]:
    global _SCENE_SEMANTIC_CACHE
    resolver = _scene_semantic_index
    if _SCENE_SEMANTIC_CACHE is None or _SCENE_SEMANTIC_CACHE[0] is not resolver:
        _SCENE_SEMANTIC_CACHE = (resolver, resolver())
    return _SCENE_SEMANTIC_CACHE[1]


def _context_classification(
    item: Mapping[str, Any],
    situation_family: str,
    *,
    scene_ref_id: str | None = None,
) -> str:
    """Classify a context-bound item without treating missing context as universal."""
    family = str(item.get("pattern_family_id") or "")
    expected = FAMILY_CANONICAL_CONTEXT.get(situation_family)
    if family not in CONTEXT_BOUND_FAMILIES or expected is None:
        return EXACT_CONTEXT
    context_id = _item_context_id(item)
    if context_id:
        return EXACT_CONTEXT if context_id == expected else INCOMPATIBLE
    if not _approved_context_neutral_evidence(item):
        return INCOMPATIBLE
    semantics = _cached_scene_semantic_index().get(str(scene_ref_id or ""))
    if not isinstance(semantics, Mapping):
        return INCOMPATIBLE
    noun = str((item.get("lexical_slots") or {}).get("noun") or "").casefold()
    anchors = {
        str(value).casefold()
        for value in (semantics.get("anchors") or semantics.get("objects") or [])
        if str(value).strip()
    }
    if not noun or noun not in anchors:
        return INCOMPATIBLE
    return NEUTRAL_COMPATIBLE


def _context_matches(
    item: Mapping[str, Any],
    situation_family: str,
    *,
    scene_ref_id: str | None = None,
) -> bool:
    return _context_classification(
        item,
        situation_family,
        scene_ref_id=scene_ref_id,
    ) != INCOMPATIBLE


def _candidate_rank(
    *,
    row: Mapping[str, Any],
    anchors: set[str],
    situation_family: str,
    learner_id: str,
    session_id: str,
    activity_id: str,
    exposed: set[str],
    recent: set[str],
    assessment: bool,
    scene_ref_id: str | None = None,
    task_angle: str | None = None,
) -> tuple[Any, ...] | None:
    item = json.loads(str(row["private_item_json"]))
    guard_applies = bool(task_angle) or str(row.get("skill") or "").upper() == "WRITING"
    if _SYSTEMIC_CANDIDATE_GUARD is not None and guard_applies:
        if not _SYSTEMIC_CANDIDATE_GUARD(
            item,
            task_angle=str(task_angle or ""),
            scene_ref_id=str(scene_ref_id or ""),
            situation_family=str(situation_family or ""),
        ):
            return None
    noun = str((item.get("lexical_slots") or {}).get("noun") or "").casefold()
    anchor_match = noun in anchors
    context_classification = _context_classification(
        item,
        situation_family,
        scene_ref_id=scene_ref_id,
    )
    skill = str(row["skill"])
    if skill != "SPEAKING" and not anchor_match:
        context_fallback = (
            skill == "WRITING"
            and str(item.get("pattern_family_id") or "") in CONTEXT_BOUND_FAMILIES
            and bool(_item_context_id(item))
            and context_classification in {EXACT_CONTEXT, NEUTRAL_COMPATIBLE}
        )
        if not context_fallback:
            return None
    if context_classification == INCOMPATIBLE:
        return None
    if skill == "SPEAKING" and not anchor_match:
        return None
    item_id = str(row["item_id"])
    context_priority = int(context_classification == NEUTRAL_COMPATIBLE)
    anchor_priority = int(not anchor_match)
    return (
        anchor_priority,
        context_priority,
        assessment and item_id in exposed,
        item_id in recent,
        item_id in exposed,
        hashlib.sha256(f"{learner_id}|{session_id}|{activity_id}|{item_id}".encode("utf-8")).hexdigest(),
        item_id,
    )


def _selection_reason(*, item_id: str, exposed: set[str], recent: set[str], assessment: bool, skill: str) -> str:
    if assessment:
        return "TRANSFER"
    if item_id in exposed and item_id not in recent:
        return "SCHEDULED_REVIEW"
    if skill == "SPEAKING":
        return "GUIDED_EXTENSION"
    return "NEW_OR_UNSEEN"


def assemble_form_component(
    database: Path,
    *,
    learner_id: str,
    session_id: str,
    form_ordinal: int,
    selected_at: str | None = None,
) -> dict[str, Any]:
    if form_ordinal < 1 or form_ordinal > FORM_COUNT:
        raise BlueprintIntegrationError("FORM_ORDINAL_INVALID")
    selected_at = timestamp(selected_at)
    runtime = qb02.Unit01ApprovedVariantSessionRuntime(Path(database))
    with runtime.write() as connection:
        connection.row_factory = sqlite3.Row
        for table in ("u01qb13_metadata", "u01qb13_blueprint_activities", "u01qb13_session_bindings"):
            _require_table(connection, table)
        metadata = dict(connection.execute("SELECT key,value FROM u01qb13_metadata"))
        if metadata.get("validation_status") != PASS_STATUS:
            raise BlueprintIntegrationError("U01QB13_BLUEPRINT_NOT_INSTALLED")
        session = runtime._active_session(connection, learner_id=learner_id, session_id=session_id)
        skill = str(session["skill"])
        existing = connection.execute("SELECT 1 FROM u01qb13_session_bindings WHERE session_id=? LIMIT 1", (session_id,)).fetchone()
        if existing:
            return form_component_payload(connection, session_id=session_id)
        if connection.execute("SELECT 1 FROM u01qb02_session_plans WHERE session_id=?", (session_id,)).fetchone():
            raise BlueprintIntegrationError("SESSION_ALREADY_PLANNED_WITHOUT_U01QB13_BINDING")
        activities = [
            dict(row)
            for row in connection.execute(
                """SELECT * FROM u01qb13_blueprint_activities
                   WHERE form_ordinal=? AND skill=? ORDER BY activity_id""",
                (form_ordinal, skill),
            )
        ]
        expected_count = {"READING": READING_PER_FORM, "WRITING": WRITING_PER_FORM, "SPEAKING": SPEAKING_PER_FORM}[skill]
        if len(activities) != expected_count:
            raise BlueprintIntegrationError(f"FORM_COMPONENT_ACTIVITY_COUNT_INVALID:{skill}:{len(activities)}")
        catalog = [
            dict(row)
            for row in connection.execute("SELECT * FROM u01qb02_item_catalog WHERE lesson_id=? ORDER BY item_id", (session["lesson_id"],))
        ]
        exposed = {str(row[0]) for row in connection.execute("SELECT DISTINCT item_id FROM u01qb02_item_exposures WHERE learner_id=?", (learner_id,))}
        recent = {str(row[0]) for row in connection.execute("SELECT item_id FROM u01qb02_item_exposures WHERE learner_id=? ORDER BY exposure_seq DESC LIMIT ?", (learner_id, qb02.RECENT_EXPOSURE_WINDOW))}
        selected: list[tuple[dict[str, Any], str, str | None, str | None]] = []
        selected_ids: set[str] = set()
        selected_visible_signatures_by_scene: dict[str, set[str]] = defaultdict(set)
        for activity in activities:
            allowed = set(json.loads(str(activity["pattern_family_ids_json"])))
            anchors = {str(row).casefold() for row in json.loads(str(activity["scene_anchors_json"]))}
            candidates = []
            for row in catalog:
                if str(row["item_id"]) in selected_ids or str(row["pattern_family_id"]) not in allowed:
                    continue
                rank = _candidate_rank(
                    row=row,
                    anchors=anchors,
                    situation_family=str(activity["situation_family"]),
                    learner_id=learner_id,
                    session_id=session_id,
                    activity_id=str(activity["activity_id"]),
                    exposed=exposed,
                    recent=recent,
                    assessment=bool(activity["assessment_candidate"]),
                    scene_ref_id=str(activity["scene_ref_id"]),
                    task_angle=str(activity["task_angle"]),
                )
                if rank is not None:
                    if _SYSTEMIC_CANDIDATE_GUARD is not None:
                        visible_signature = _SYSTEMIC_CANDIDATE_GUARD.visible_signature(item=json.loads(str(row["private_item_json"])))
                        if visible_signature in selected_visible_signatures_by_scene[str(activity["scene_ref_id"])]:
                            continue
                    else:
                        visible_signature = ""
                    candidates.append((rank, row))
            if not candidates:
                raise BlueprintIntegrationError(f"SCENE_TASK_RUNTIME_BINDING_GAP:{activity['activity_id']}")
            candidates.sort(key=lambda pair: pair[0])
            row = candidates[0][1]
            item_id = str(row["item_id"])
            item = json.loads(str(row["private_item_json"]))
            quality = "LEXICAL_ANCHOR"
            if _context_classification(
                item,
                str(activity["situation_family"]),
                scene_ref_id=str(activity["scene_ref_id"]),
            ) != INCOMPATIBLE:
                quality = "LEXICAL_ANCHOR_AND_CONTEXT_FAMILY"
            reason = _selection_reason(
                item_id=item_id,
                exposed=exposed,
                recent=recent,
                assessment=bool(activity["assessment_candidate"]),
                skill=skill,
            )
            selected.append((row, reason, str(activity["activity_id"]), quality))
            selected_ids.add(item_id)
            if _SYSTEMIC_CANDIDATE_GUARD is not None:
                selected_visible_signatures_by_scene[str(activity["scene_ref_id"])].add(
                    _SYSTEMIC_CANDIDATE_GUARD.visible_signature(item=json.loads(str(row["private_item_json"])))
                )

        filler_needed = qb02.SESSION_SIZE - len(selected)
        if filler_needed != SUPPORT_FILLER_COUNTS[skill]:
            raise BlueprintIntegrationError(f"SUPPORT_FILLER_COUNT_INVALID:{skill}:{filler_needed}")
        filler = [row for row in catalog if str(row["item_id"]) not in selected_ids and str(row["item_id"]) not in recent]
        filler = runtime._stable_order(learner_id, session_id, "FALLBACK", filler)
        if len(filler) < filler_needed:
            filler = runtime._stable_order(
                learner_id,
                session_id,
                "FALLBACK",
                [row for row in catalog if str(row["item_id"]) not in selected_ids],
            )
        for row in filler[:filler_needed]:
            selected.append((row, "FALLBACK", None, None))
            selected_ids.add(str(row["item_id"]))
        if len(selected) != qb02.SESSION_SIZE:
            raise BlueprintIntegrationError(f"SESSION_CONTAINER_COUNT_INVALID:{len(selected)}")

        plan_core = {
            "session_id": session_id,
            "learner_id": learner_id,
            "lesson_id": session["lesson_id"],
            "skill": skill,
            "selected_at": selected_at,
            "recent_exposure_window": qb02.RECENT_EXPOSURE_WINDOW,
            "items": [
                {"position": index, "item_id": row["item_id"], "reason": reason}
                for index, (row, reason, _activity_id, _quality) in enumerate(selected, 1)
            ],
            "source_bank_sha256": dict(connection.execute("SELECT key,value FROM u01qb02_metadata"))["source_bank_artifact_sha256"],
        }
        plan_digest = qb02.digest(plan_core)
        connection.execute(
            "INSERT INTO u01qb02_session_plans VALUES(?,?,?,?,?,?,?,?,?)",
            (
                session_id, learner_id, session["lesson_id"], skill, qb02.SESSION_SIZE,
                selected_at, qb02.RECENT_EXPOSURE_WINDOW, plan_core["source_bank_sha256"], plan_digest,
            ),
        )
        connection.executemany(
            "INSERT INTO u01qb02_session_items(session_id,item_position,item_id,selection_reason) VALUES(?,?,?,?)",
            [(session_id, index, row["item_id"], reason) for index, (row, reason, _activity, _quality) in enumerate(selected, 1)],
        )
        for index, (row, _reason, activity_id, quality) in enumerate(selected, 1):
            if activity_id is None:
                continue
            activity = next(item for item in activities if str(item["activity_id"]) == activity_id)
            connection.execute(
                """INSERT INTO u01qb13_session_bindings
                (session_id,activity_id,item_id,item_position,binding_quality,is_assessment_evidence)
                VALUES(?,?,?,?,?,?)""",
                (session_id, activity_id, row["item_id"], index, quality, int(activity["assessment_candidate"])),
            )
        return form_component_payload(connection, session_id=session_id)


def form_component_payload(connection: sqlite3.Connection, *, session_id: str) -> dict[str, Any]:
    plan = connection.execute("SELECT * FROM u01qb02_session_plans WHERE session_id=?", (session_id,)).fetchone()
    if plan is None:
        raise BlueprintIntegrationError("SESSION_PLAN_NOT_FOUND")
    bindings = connection.execute(
        """SELECT b.*,a.form_id,a.form_ordinal,a.scene_ref_id,a.situation_family,a.setting,
                  a.skill,a.task_angle,a.support_level,a.scored,a.assessment_candidate,
                  a.scene_anchors_json,a.practice_projection_json,c.private_item_json,c.capture_enabled,
                  s.selection_reason
           FROM u01qb13_session_bindings b
           JOIN u01qb13_blueprint_activities a USING(activity_id)
           JOIN u01qb02_item_catalog c USING(item_id)
           JOIN u01qb02_session_items s ON s.session_id=b.session_id AND s.item_id=b.item_id
           WHERE b.session_id=? ORDER BY b.item_position""",
        (session_id,),
    ).fetchall()
    if not bindings:
        raise BlueprintIntegrationError("SESSION_BLUEPRINT_BINDINGS_NOT_FOUND")
    form_ids = {str(row["form_id"]) for row in bindings}
    if len(form_ids) != 1:
        raise BlueprintIntegrationError("SESSION_MULTIPLE_FORM_BINDING")
    display_options_by_activity: dict[str, list[str]] = {}
    if _SYSTEMIC_FORM_OPTION_ALLOCATOR is not None and str(plan["skill"]) == "READING":
        allocator_rows = []
        for row in bindings:
            private_item = json.loads(str(row["private_item_json"]))
            allocator_rows.append(
                {
                    "activity_id": str(row["activity_id"]),
                    "form_id": str(row["form_id"]),
                    "options": list(private_item.get("options") or []),
                    "canonical_answer": private_item.get("correct_answer"),
                    "response_mode": "select_one" if private_item.get("options") else "",
                }
            )
        allocated = _SYSTEMIC_FORM_OPTION_ALLOCATOR(
            form_id=str(bindings[0]["form_id"]),
            activities=allocator_rows,
        )
        if not isinstance(allocated, Mapping):
            raise BlueprintIntegrationError("FORM_OPTION_ALLOCATOR_RESULT_INVALID")
        display_options_by_activity = {
            str(activity_id): list(options)
            for activity_id, options in allocated.items()
        }
    items = []
    for row in bindings:
        private_item = json.loads(str(row["private_item_json"]))
        projection = json.loads(str(row["practice_projection_json"]))
        speaking = str(row["skill"]) == "SPEAKING"
        items.append(
            {
                "activity_id": str(row["activity_id"]),
                "item_position": int(row["item_position"]),
                "item_id": str(row["item_id"]),
                "scene_ref_id": str(row["scene_ref_id"]),
                "situation_family": str(row["situation_family"]),
                "setting": str(row["setting"]),
                "scene_anchors": json.loads(str(row["scene_anchors_json"])),
                "skill": str(row["skill"]),
                "task_angle": str(row["task_angle"]),
                "support_level": str(row["support_level"]),
                "scored": bool(row["scored"]),
                "assessment_candidate": bool(row["assessment_candidate"]),
                "selection_reason": str(row["selection_reason"]),
                "binding_quality": str(row["binding_quality"]),
                "prompt": projection.get("prompt") if speaking else str(private_item["prompt"]),
                "stimulus": "" if speaking else str(private_item["stimulus"]),
                "options": (
                    []
                    if speaking
                    else (
                        display_options_by_activity.get(str(row["activity_id"]))
                        if str(row["activity_id"]) in display_options_by_activity
                        else list(private_item.get("options") or [])
                        if _SYSTEMIC_OPTION_PERMUTER is None
                        else _SYSTEMIC_OPTION_PERMUTER(
                            list(private_item.get("options") or []),
                            canonical_answer=private_item.get("correct_answer"),
                            form_id=str(row["form_id"]),
                            question_identity=str(row["activity_id"]),
                        )
                    )
                ),
                "capture_enabled": False if speaking else bool(row["capture_enabled"]),
                "practice_only": speaking,
            }
        )
    return {
        "validation_status": PASS_STATUS,
        "session_id": session_id,
        "form_id": next(iter(form_ids)),
        "form_ordinal": int(bindings[0]["form_ordinal"]),
        "skill": str(plan["skill"]),
        "blueprint_activity_count": len(items),
        "support_filler_count": qb02.SESSION_SIZE - len(items),
        "runtime_session_item_count": qb02.SESSION_SIZE,
        "items": items,
        "support_fillers_are_form_activities": False,
        "second_runtime_created": False,
        "speaking_scoring_enabled": False,
    }


def materialize(
    *,
    rotation: Mapping[str, Any],
    allocation: Mapping[str, Any],
    candidate_path: Path,
    approved_path: Path,
    report_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    candidate = build_candidate(rotation, allocation)
    approved = admit_candidate(candidate)
    from ulga.validators import validate_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration as validator

    report = validator.validate_approved(candidate, approved)
    if report["error_count"]:
        raise BlueprintIntegrationError("APPROVED_BLUEPRINT_VALIDATION_FAILED:" + "|".join(report["errors"]))
    write_json(candidate_path, candidate, private=True)
    write_json(approved_path, approved, private=True)
    write_json(report_path, report)
    return candidate, approved, report


def read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rotation", type=Path, required=True)
    parser.add_argument("--allocation", type=Path, required=True)
    parser.add_argument("--database", type=Path)
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--approved", type=Path, default=DEFAULT_APPROVED)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    try:
        _, approved, report = materialize(
            rotation=read_json(args.rotation),
            allocation=read_json(args.allocation),
            candidate_path=args.candidate.resolve(),
            approved_path=args.approved.resolve(),
            report_path=args.report.resolve(),
        )
        installed = install_blueprint(args.database.resolve(), approved) if args.database else None
    except (BlueprintIntegrationError, OSError, KeyError, TypeError, ValueError, policy_artifact.ContentPolicyBuildError) as exc:
        print("STATUS=FAIL_A1FS_V1_U01QB13_UNIT01_TWELVE_FORM_RUNTIME_SELECTION_AND_ASSESSMENT_BLUEPRINT_INTEGRATION")
        print(f"ERROR={exc}")
        return 1
    payload = approved["payload"]
    print(f"STATUS={PASS_STATUS}")
    print(f"FORMS={len(payload['form_summaries'])}")
    print(f"ACTIVITIES={payload['coverage_readback']['activity_count']}")
    print(f"SCORED_ACTIVITIES={payload['coverage_readback']['scored_activity_count']}")
    print(f"SPEAKING_PRACTICE={payload['coverage_readback']['speaking_practice_activity_count']}")
    print(f"RUNTIME_INSTALLED={installed is not None}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
