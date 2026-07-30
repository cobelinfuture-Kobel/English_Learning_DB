#!/usr/bin/env python3
"""Admit reviewed Unit01 RAZ candidates into reusable content assets.

The builder consumes the existing RAZQ01C selection report plus explicit human
review decisions. It does not publish raw RAZ text. It creates stable Unit01
MICRO_SCENE / SHORT_PASSAGE / SHORT_DIALOGUE assets, projects every admitted
asset into the existing Unit01 Reading, Writing, and Speaking question-bank
families, and emits a reference-only handoff for Unit02.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"
A1FS_CONTENT_POLICY_EXEMPTION = ""
PROGRAM_ID = "A1FS-V1"
TASK_ID = (
    "A1FS-V1-RAZQ01D_"
    "Unit01MicroScenePassageDialogueAdmissionThreeSkillProjectionAndUnit02ReusableHandoff"
)
SCHEMA_VERSION = "a1fs.v1.razq01d.unit01_content_handoff.v1"
PASS_STATUS = "PASS_A1FS_V1_RAZQ01D_UNIT01_CONTENT_HANDOFF"
UNIT_ID = "GRAMMAR_ARTICLES_BASIC"
TARGET_BANK_ID = "A1FS_V1_UNIT01_APPROVED_VARIANT_POOL"
TARGET_BANK_VERSION = "2.0.0"
NEXT_SHORT_STEP = "A1FS-V1-RAZQ01D-OPS_RealPrivateCandidateAndReviewDecisionMaterialization"

CONTENT_KINDS = frozenset({"MICRO_SCENE", "SHORT_PASSAGE", "SHORT_DIALOGUE"})
SKILLS = ("READING", "WRITING", "SPEAKING")
READING_FAMILIES = (
    "U01-PF04-FIRST-MENTION-CONTEXT",
    "U01-PF05-KNOWN-REFERENCE-CONTEXT",
    "U01-PF08-TRANSFER-FIRST-MENTION",
)
WRITING_FAMILIES = (
    "U01-PF01-AAN-NOUN-GAP",
    "U01-PF02-AAN-ADJ-NOUN-GAP",
    "U01-PF03-VERY-ADJ-NOUN-GAP",
    "U01-PF09-TRANSFER-KNOWN-REFERENCE",
)
SPEAKING_FAMILIES = (
    "U01-PF10-SPEAK-NOUN",
    "U01-PF11-SPEAK-ADJ-NOUN",
    "U01-PF12-SPEAK-VERY-ADJ-NOUN",
)
FAMILIES_BY_SKILL = {
    "READING": READING_FAMILIES,
    "WRITING": WRITING_FAMILIES,
    "SPEAKING": SPEAKING_FAMILIES,
}

INSPECTION_FINDINGS = (
    {
        "finding_id": "U01-SCENE-BREADTH-001",
        "status": "CONFIRMED_GAP",
        "finding": "FIVE_FIXED_CONTEXT_LABELS_ARE_INSUFFICIENT_FOR_UNIT01_SCENE_BREADTH",
    },
    {
        "finding_id": "U01-RAZ-QB-LINK-002",
        "status": "CONFIRMED_GAP",
        "finding": "RAZQ01C_CANDIDATES_ARE_NOT_CONSUMED_BY_THE_EXISTING_288_ITEM_U01QB_POOL",
    },
    {
        "finding_id": "U01-U01E-THREE-SKILL-003",
        "status": "CONFIRMED_EXISTING_CAPABILITY",
        "finding": "THE_EXISTING_U01E_SHORT_TEXTS_HAVE_READING_WRITING_AND_SPEAKING_PROJECTIONS",
    },
    {
        "finding_id": "U01-DIALOGUE-004",
        "status": "CONFIRMED_MISCLASSIFICATION_RISK",
        "finding": "A_THIRD_PERSON_NARRATIVE_WITHOUT_SPEAKER_TURNS_IS_NOT_A_SHORT_DIALOGUE",
    },
    {
        "finding_id": "U01-SHARED-CONTENT-005",
        "status": "REQUIRED_CONTRACT",
        "finding": "ONE_STABLE_CONTENT_ASSET_MUST_BE_SHARED_ACROSS_READING_WRITING_AND_SPEAKING",
    },
)


class ContentHandoffBuildError(ValueError):
    """Fail-closed Unit01 content admission error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    if not isinstance(value, str):
        value = canonical(value)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContentHandoffBuildError(f"UNREADABLE_JSON:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise ContentHandoffBuildError(f"OBJECT_REQUIRED:{path}")
    return value


def atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def _require_string(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ContentHandoffBuildError(f"NONEMPTY_STRING_REQUIRED:{label}")
    return text


def _selection_candidates(report: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    task_id = str(report.get("task_id") or "")
    status = str(report.get("status") or "")
    if "RAZQ01C" not in task_id:
        raise ContentHandoffBuildError("RAZQ01C_SELECTION_REPORT_REQUIRED")
    if not status.startswith("PASS_"):
        raise ContentHandoffBuildError("RAZQ01C_PASS_STATUS_REQUIRED")
    scope = report.get("scope") or {}
    if scope.get("allowed_units") not in ([UNIT_ID], None):
        raise ContentHandoffBuildError("UNIT01_ONLY_SELECTION_SCOPE_REQUIRED")
    rows = report.get("selected_candidates")
    if not isinstance(rows, list):
        raise ContentHandoffBuildError("SELECTED_CANDIDATE_LIST_REQUIRED")
    result: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise ContentHandoffBuildError("SELECTION_CANDIDATE_OBJECT_REQUIRED")
        source_record_id = _require_string(row.get("source_record_id"), "source_record_id")
        if source_record_id in result:
            raise ContentHandoffBuildError(f"DUPLICATE_SOURCE_RECORD_ID:{source_record_id}")
        result[source_record_id] = row
    return result


def _review_decisions(value: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    rows = value.get("decisions")
    if not isinstance(rows, list) or not rows:
        raise ContentHandoffBuildError("NONEMPTY_REVIEW_DECISIONS_REQUIRED")
    return rows


def _adapted_content(decision: Mapping[str, Any], content_kind: str) -> dict[str, Any]:
    if content_kind == "SHORT_DIALOGUE":
        turns = decision.get("turns")
        if not isinstance(turns, list) or len(turns) < 2:
            raise ContentHandoffBuildError("SHORT_DIALOGUE_REQUIRES_AT_LEAST_TWO_TURNS")
        normalized: list[dict[str, Any]] = []
        for index, turn in enumerate(turns, 1):
            if not isinstance(turn, Mapping):
                raise ContentHandoffBuildError("DIALOGUE_TURN_OBJECT_REQUIRED")
            normalized.append(
                {
                    "turn_index": index,
                    "speaker_id": _require_string(turn.get("speaker_id"), "speaker_id"),
                    "text": _require_string(turn.get("text"), "dialogue_turn_text"),
                }
            )
        speakers = sorted({row["speaker_id"] for row in normalized})
        if len(speakers) < 2:
            raise ContentHandoffBuildError("SHORT_DIALOGUE_REQUIRES_TWO_DISTINCT_SPEAKERS")
        return {"turns": normalized, "speaker_ids": speakers}
    adapted_text = _require_string(decision.get("adapted_text"), "adapted_text")
    return {"adapted_text": adapted_text}


def _projection(
    *, content_asset_id: str, skill: str, task_role: str, target_family_ids: Sequence[str]
) -> dict[str, Any]:
    return {
        "projection_id": f"{content_asset_id}-{skill[:1]}01",
        "content_asset_id": content_asset_id,
        "skill": skill,
        "task_role": task_role,
        "target_bank_id": TARGET_BANK_ID,
        "target_bank_version": TARGET_BANK_VERSION,
        "target_family_ids": list(target_family_ids),
        "projection_mode": "REFERENCE_EXISTING_FAMILIES_NO_SECOND_BANK",
        "runtime_materialization_status": "READY_FOR_EXISTING_U01QB_PROJECTION",
    }


def _asset(candidate: Mapping[str, Any], decision: Mapping[str, Any]) -> dict[str, Any]:
    if decision.get("review_status") != "APPROVED":
        raise ContentHandoffBuildError("ONLY_APPROVED_REVIEW_DECISIONS_CAN_BE_ADMITTED")
    content_kind = _require_string(decision.get("content_kind"), "content_kind")
    if content_kind not in CONTENT_KINDS:
        raise ContentHandoffBuildError(f"UNSUPPORTED_CONTENT_KIND:{content_kind}")
    content_asset_id = _require_string(decision.get("content_asset_id"), "content_asset_id")
    if not content_asset_id.startswith("U01-"):
        raise ContentHandoffBuildError("UNIT01_CONTENT_ASSET_ID_REQUIRED")
    if str(candidate.get("selection_class")) == "REJECT":
        raise ContentHandoffBuildError("REJECTED_RAZQ01C_CANDIDATE_CANNOT_BE_ADMITTED")

    content = _adapted_content(decision, content_kind)
    source_text = str(candidate.get("text_excerpt") or "")
    if not source_text:
        raise ContentHandoffBuildError("SOURCE_TEXT_REQUIRED_FOR_PRIVATE_HASH_BINDING")

    target_alignment = {
        "grammar_target_ids": list(
            decision.get("grammar_target_ids") or ["ARTICLE_FIRST_AND_KNOWN_REFERENCE"]
        ),
        "egp_row_ids": list(decision.get("egp_row_ids") or []),
        "vocabulary_asset_ids": list(decision.get("vocabulary_asset_ids") or []),
        "vocabulary_lemmas": sorted(
            set(decision.get("vocabulary_lemmas") or candidate.get("active_noun_hits") or [])
        ),
        "adjective_lemmas": sorted(
            set(decision.get("adjective_lemmas") or candidate.get("active_adjective_hits") or [])
        ),
        "chunk_asset_ids": list(decision.get("chunk_asset_ids") or []),
        "sentence_frame_ids": sorted(
            set(
                decision.get("sentence_frame_ids")
                or candidate.get("matched_sentence_frame_ids")
                or []
            )
        ),
        "pattern_ids": list(
            decision.get("pattern_ids")
            or ["U01-NP-ARTICLE-NOUN", "U01-NP-ARTICLE-ADJECTIVE-NOUN"]
        ),
        "theme_id": decision.get("theme_id"),
        "situation_family_id": decision.get("situation_family_id"),
        "micro_situation_id": decision.get("micro_situation_id"),
        "communicative_function_ids": list(
            decision.get("communicative_function_ids") or []
        ),
    }
    scene_profile = {
        "setting": _require_string(decision.get("setting"), "setting"),
        "participants": list(decision.get("participants") or []),
        "objects": list(decision.get("objects") or []),
        "actions": list(decision.get("actions") or []),
        "information_structure": list(
            decision.get("information_structure")
            or ["FIRST_MENTION", "KNOWN_REFERENCE"]
        ),
        "template_only": False,
    }
    scene_profile["distinct_scene_signature"] = digest(scene_profile)

    if content_kind == "SHORT_DIALOGUE":
        turns = content["turns"]
        dialogue_profile = {
            "is_real_dialogue": True,
            "speaker_count": len(content["speaker_ids"]),
            "turn_count": len(turns),
            "speaker_ids": content["speaker_ids"],
            "adjacency_pair_types": list(decision.get("adjacency_pair_types") or []),
            "role_play_supported": True,
        }
    else:
        dialogue_profile = {
            "is_real_dialogue": False,
            "speaker_count": 0,
            "turn_count": 0,
            "speaker_ids": [],
            "adjacency_pair_types": [],
            "role_play_supported": False,
        }

    projections = {
        "reading": [
            _projection(
                content_asset_id=content_asset_id,
                skill="READING",
                task_role="SHORT_TEXT_COMPREHENSION_AND_ARTICLE_REFERENCE",
                target_family_ids=READING_FAMILIES,
            )
        ],
        "writing": [
            _projection(
                content_asset_id=content_asset_id,
                skill="WRITING",
                task_role="GUIDED_SENTENCE_AND_CONTEXTUAL_TRANSFER",
                target_family_ids=WRITING_FAMILIES,
            )
        ],
        "speaking": [
            _projection(
                content_asset_id=content_asset_id,
                skill="SPEAKING",
                task_role=(
                    "ROLE_PLAY" if content_kind == "SHORT_DIALOGUE" else "ORAL_RETELLING"
                ),
                target_family_ids=SPEAKING_FAMILIES,
            )
        ],
        "listening": [],
        "listening_status": "DEFERRED_NO_AUDIO_IN_RAZQ01D",
        "shared_scene_across_skills": True,
        "three_skill_projection_complete": True,
    }

    source_record_id = _require_string(candidate.get("source_record_id"), "source_record_id")
    asset = {
        "content_asset_id": content_asset_id,
        "content_kind": content_kind,
        "unit_id": UNIT_ID,
        "introduced_unit_id": UNIT_ID,
        "introduced_unit_sequence": 1,
        "content": content,
        "source_lineage": {
            "source_authority": "RAZ_READING_AUTHORITY_PRIVATE",
            "source_record_id": source_record_id,
            "semantic_identity": candidate.get("semantic_identity"),
            "source_level": candidate.get("source_level"),
            "source_type": candidate.get("source_type"),
            "original_excerpt_sha256": digest(source_text),
            "original_excerpt_private": True,
            "original_excerpt_published": False,
            "adaptation_mode": _require_string(
                decision.get("adaptation_mode") or "PROJECT_AUTHORED_REWRITE",
                "adaptation_mode",
            ),
            "adaptation_reason_codes": list(decision.get("adaptation_reason_codes") or []),
            "derived_from_task_id": str(
                decision.get("derived_from_task_id") or "A1FS-V1-RAZQ01C"
            ),
        },
        "target_alignment": target_alignment,
        "scene_profile": scene_profile,
        "dialogue_profile": dialogue_profile,
        "skill_projections": projections,
        "admission": {
            "selection_class": candidate.get("selection_class"),
            "review_status": "APPROVED",
            "decision_ref": _require_string(decision.get("decision_ref"), "decision_ref"),
            "reviewed_dimensions": list(
                decision.get("reviewed_dimensions")
                or [
                    "GRAMMAR_SAFETY",
                    "VOCABULARY_SAFETY",
                    "SEMANTIC_NATURALNESS",
                    "A1_ANSWERABILITY",
                    "SCENE_DISTINCTNESS",
                    "THREE_SKILL_AFFORDANCE",
                ]
            ),
            "rejection_reason_codes": [],
            "canonical_admission": True,
        },
        "later_unit_reuse": {
            "reusable_in_later_units": True,
            "copy_on_reuse": False,
            "reuse_identity_mode": "REFERENCE_STABLE_CONTENT_ASSET_ID",
            "eligible_future_unit_roles": [
                "PREREQUISITE",
                "CARRY_OVER",
                "RECOMBINATION",
                "TRANSFER",
                "SCHEDULED_REVIEW",
                "REMEDIATION",
                "ASSESSMENT_SUPPORT",
            ],
            "reuse_gates": [
                "PREREQUISITE_UNLOCKED",
                "LEVEL_SCOPE_ALLOWED",
                "NEW_GRAMMAR_COMPATIBILITY_PASS",
                "NO_UNINTRODUCED_GRAMMAR",
                "SEMANTIC_COMPATIBILITY_PASS",
                "SCENE_DEDUPLICATION_PASS",
                "REUSE_REASON_RECORDED",
            ],
        },
    }
    asset["content_asset_sha256"] = digest(
        {key: value for key, value in asset.items() if key != "content_asset_sha256"}
    )
    return asset


def build_handoff(
    selection_report: Mapping[str, Any], review_decisions: Mapping[str, Any]
) -> dict[str, Any]:
    candidates = _selection_candidates(selection_report)
    assets: list[dict[str, Any]] = []
    seen_asset_ids: set[str] = set()
    used_sources: set[str] = set()
    for decision in _review_decisions(review_decisions):
        if not isinstance(decision, Mapping):
            raise ContentHandoffBuildError("REVIEW_DECISION_OBJECT_REQUIRED")
        source_record_id = _require_string(decision.get("source_record_id"), "source_record_id")
        candidate = candidates.get(source_record_id)
        if candidate is None:
            raise ContentHandoffBuildError(f"UNKNOWN_SOURCE_RECORD_ID:{source_record_id}")
        asset = _asset(candidate, decision)
        asset_id = asset["content_asset_id"]
        if asset_id in seen_asset_ids:
            raise ContentHandoffBuildError(f"DUPLICATE_CONTENT_ASSET_ID:{asset_id}")
        if source_record_id in used_sources:
            raise ContentHandoffBuildError(
                f"SOURCE_RECORD_ADMITTED_MORE_THAN_ONCE:{source_record_id}"
            )
        seen_asset_ids.add(asset_id)
        used_sources.add(source_record_id)
        assets.append(asset)

    kind_counts = Counter(asset["content_kind"] for asset in assets)
    projection_counts = {
        skill: sum(len(asset["skill_projections"][skill.lower()]) for asset in assets)
        for skill in SKILLS
    }
    unique_scene_count = len(
        {asset["scene_profile"]["distinct_scene_signature"] for asset in assets}
    )
    report = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "scope": {
            "allowed_units": [UNIT_ID],
            "unit02_to_unit24_modified": False,
            "unit02_handoff_reference_only": True,
            "a2_status": "LOCKED",
            "raw_raz_text_published": False,
            "second_question_bank_created": False,
            "listening_population": "DEFERRED",
        },
        "inputs": {
            "selection_task_id": selection_report.get("task_id"),
            "selection_status": selection_report.get("status"),
            "selection_report_sha256": digest(selection_report),
            "review_decision_set_id": review_decisions.get("decision_set_id"),
            "review_decisions_sha256": digest(review_decisions),
        },
        "inspection_findings": list(INSPECTION_FINDINGS),
        "content_assets": sorted(assets, key=lambda row: row["content_asset_id"]),
        "question_bank_integration": {
            "target_bank_id": TARGET_BANK_ID,
            "target_bank_version": TARGET_BANK_VERSION,
            "integration_mode": "EXTEND_EXISTING_AUTHORITY_BY_STABLE_CONTENT_REFERENCE",
            "second_bank_created": False,
            "existing_family_ids_by_skill": {
                "READING": list(READING_FAMILIES),
                "WRITING": list(WRITING_FAMILIES),
                "SPEAKING": list(SPEAKING_FAMILIES),
            },
            "content_asset_ids": sorted(seen_asset_ids),
        },
        "coverage_readback": {
            "admitted_content_asset_count": len(assets),
            "distinct_micro_scene_count": kind_counts["MICRO_SCENE"],
            "distinct_short_passage_count": kind_counts["SHORT_PASSAGE"],
            "distinct_dialogue_count": kind_counts["SHORT_DIALOGUE"],
            "distinct_scene_signature_count": unique_scene_count,
            "raz_grounded_content_count": len(assets),
            "project_authored_rewrite_count": sum(
                asset["source_lineage"]["adaptation_mode"] == "PROJECT_AUTHORED_REWRITE"
                for asset in assets
            ),
            "source_record_coverage_count": len(used_sources),
            "reading_projection_count": projection_counts["READING"],
            "writing_projection_count": projection_counts["WRITING"],
            "speaking_projection_count": projection_counts["SPEAKING"],
            "three_skill_shared_content_count": sum(
                asset["skill_projections"]["three_skill_projection_complete"]
                for asset in assets
            ),
            "template_only_task_count": 0,
            "template_only_task_ratio": 0.0,
            "unit02_reusable_asset_count": len(assets),
        },
        "unit02_reusable_handoff": {
            "target_unit_sequence": 2,
            "handoff_mode": "REFERENCE_ONLY_NO_CONTENT_COPY",
            "source_unit_id": UNIT_ID,
            "stable_content_asset_ids": sorted(seen_asset_ids),
            "required_binding_fields": [
                "target_unit_id",
                "source_content_asset_id",
                "target_unit_role",
                "new_grammar_target_ids",
                "reuse_reason",
                "compatibility_gate_status",
            ],
            "unit02_content_modified": False,
        },
        "listening_readback": {
            "status": "DEFERRED_NO_AUDIO_IN_RAZQ01D",
            "listening_projection_count": 0,
            "listening_claimed_complete": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    report["artifact_sha256"] = digest(
        {key: value for key, value in report.items() if key != "artifact_sha256"}
    )
    return report


def run(*, selection_path: Path, decisions_path: Path, output_path: Path) -> dict[str, Any]:
    report = build_handoff(load_json(selection_path), load_json(decisions_path))
    atomic_json(output_path, report)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection-report", type=Path, required=True)
    parser.add_argument("--review-decisions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = run(
            selection_path=args.selection_report.resolve(),
            decisions_path=args.review_decisions.resolve(),
            output_path=args.output.resolve(),
        )
    except (ContentHandoffBuildError, OSError, ValueError, KeyError, TypeError) as exc:
        print("STATUS=FAIL_A1FS_V1_RAZQ01D_UNIT01_CONTENT_HANDOFF")
        print(f"ERROR={exc}")
        return 1
    print(f"STATUS={report['status']}")
    print(f"CONTENT_ASSETS={report['coverage_readback']['admitted_content_asset_count']}")
    print(f"THREE_SKILL_SHARED={report['coverage_readback']['three_skill_shared_content_count']}")
    print(f"NEXT_SHORT_STEP={report['next_short_step']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
