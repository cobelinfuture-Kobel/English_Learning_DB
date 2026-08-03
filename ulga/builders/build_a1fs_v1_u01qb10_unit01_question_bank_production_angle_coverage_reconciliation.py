#!/usr/bin/env python3
"""Reconcile Unit01 QuestionBank production-angle coverage without increasing bank size.

U01QB10 consumes the admitted U01QB01 288-item base bank and deterministically
replaces 48 overrepresented recognition/context items with 48 Writing production
items. The canonical base count stays 288 and the accepted Real62 extension stays
186, so projected Unit01 runtime capacity remains 474. This milestone does not
activate the revised bank in runtime; activation is a later migration milestone.
"""
from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import build_a1fs_v1_u01qb01_unit01_pattern_family_approved_variant_pool as seed

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB10_Unit01QuestionBankProductionAngleCoverageReconciliation"
SCHEMA_VERSION = "a1fs.v1.u01qb10.unit01_question_bank_production_angle_coverage_reconciliation.v1"
PASS_STATUS = "PASS_A1FS_V1_U01QB10_UNIT01_QUESTION_BANK_PRODUCTION_ANGLE_COVERAGE_RECONCILIATION"
DECISION_REF = "OPERATOR_APPROVAL:2026-08-03:U01QB10"
UNIT_ID = seed.UNIT_ID
BANK_ID = seed.BANK_ID
BANK_VERSION = seed.BANK_VERSION
CANONICAL_REVISION = "U01QB10-R1"
APPROVED_CONTRACT_SHA256 = seed.APPROVED_CONTRACT_SHA256
EXPECTED_APPROVED_COUNT = 288
EXPECTED_EXTENSION_COUNT = 186
EXPECTED_PROJECTED_RUNTIME_COUNT = 474
EXPECTED_RETAINED_COUNT = 240
EXPECTED_REPLACEMENT_COUNT = 48
EXPECTED_SCORED_GAP_BEFORE = 48
EXPECTED_SCORED_GAP_AFTER = 0
EXPECTED_SCORED_PARTIAL_REMAINING = 36
EXPECTED_SKILL_COUNTS = {"READING": 130, "SPEAKING": 25, "WRITING": 133}

PF13 = "U01-PF13-WRITING-ERROR-CORRECTION"
PF14 = "U01-PF14-WRITING-COMPLETE-SENTENCE"
PF15 = "U01-PF15-WRITING-CONNECTED-SENTENCES"

REPLACEMENT_PLAN: dict[str, tuple[int, str]] = {
    "U01-PF04-FIRST-MENTION-CONTEXT": (12, PF13),
    "U01-PF05-KNOWN-REFERENCE-CONTEXT": (12, PF14),
    "U01-PF08-TRANSFER-FIRST-MENTION": (12, PF14),
    "U01-PF09-TRANSFER-KNOWN-REFERENCE": (12, PF15),
}
PRODUCTION_FAMILY_CONTRACTS: tuple[dict[str, Any], ...] = (
    {
        "family_id": PF13,
        "skill": "WRITING",
        "question_type": "error_correction",
        "task_angle": "ERROR_CHECK",
        "approved_count": 12,
        "scoring_mode": "NORMALIZED_TEXT",
    },
    {
        "family_id": PF14,
        "skill": "WRITING",
        "question_type": "complete_sentence_production",
        "task_angle": "COMPLETE_SENTENCE_PRODUCTION",
        "approved_count": 24,
        "scoring_mode": "FEATURE_RUBRIC",
    },
    {
        "family_id": PF15,
        "skill": "WRITING",
        "question_type": "connected_sentence_production",
        "task_angle": "CONNECTED_SENTENCE_PRODUCTION",
        "approved_count": 12,
        "scoring_mode": "FEATURE_RUBRIC",
    },
)

DEFAULT_CANDIDATE = Path("ulga/private/a1fs_v1_u01qb10_unit01_question_bank_reconciled.candidate.private.json")
DEFAULT_APPROVED = Path("ulga/private/a1fs_v1_u01qb10_unit01_question_bank_reconciled.approved.private.json")
DEFAULT_REPORT = Path("ulga/reports/a1fs_v1_u01qb10_unit01_question_bank_production_angle_reconciliation.json")
NEXT_SHORT_STEP = "A1FS-V1-U01QB11_Unit01ReconciledQuestionBankRuntimeMigrationAnd474Replay"


class ReconciliationBuildError(ValueError):
    pass


def write_json(path: Path, value: Mapping[str, Any], *, private: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    if private:
        try:
            path.chmod(0o600)
        except OSError:
            pass


def seed_bank() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    candidate = seed.build_candidate()
    approved = seed.admit_candidate(candidate)
    from ulga.validators import validate_a1fs_v1_u01qb01_unit01_pattern_family_approved_variant_pool as seed_validator

    report = seed_validator.validate_approved(candidate, approved)
    if report.get("error_count"):
        raise ReconciliationBuildError("U01QB01_SEED_INVALID:" + "|".join(report["errors"]))
    items = approved.get("payload", {}).get("approved_items")
    if not isinstance(items, list) or len(items) != EXPECTED_APPROVED_COUNT:
        raise ReconciliationBuildError("U01QB01_APPROVED_COUNT_INVALID")
    return approved, [deepcopy(dict(row)) for row in items]


def _response_contract(*, mode: str, model_answer: str, rubric: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return {
        "scoring_mode": mode,
        "response_type": "string",
        "accepted_texts": [model_answer],
        "accepted_sequence": [],
        "capture_enabled": True,
        "human_review_fallback": mode == "FEATURE_RUBRIC",
        "rubric": dict(rubric or {}),
    }


def _production_item(source: Mapping[str, Any], family_id: str) -> dict[str, Any]:
    slots = dict(source.get("lexical_slots") or {})
    noun = str(slots.get("noun") or "")
    context_id = str(source.get("context_id") or slots.get("context_id") or "")
    source_family = str(source.get("pattern_family_id") or "")
    if not noun or context_id not in seed.CONTEXT_LOCATION or source_family not in REPLACEMENT_PLAN:
        raise ReconciliationBuildError(f"PRODUCTION_SOURCE_INVALID:{source.get('item_id')}")
    location = seed.CONTEXT_LOCATION[context_id]
    art = seed.article(noun)

    item = deepcopy(dict(source))
    item["item_id"] = (
        f"U01QB10-{family_id}-{seed.slug(source_family)}-"
        f"{seed.slug(context_id)}-{seed.slug(noun)}"
    )
    item["pattern_family_id"] = family_id
    item["skill"] = "WRITING"
    item["learner_visible_capable"] = True
    item["learner_delivery_status"] = "NOT_RUNTIME_CONNECTED"
    item["assessment_eligible"] = True
    item["reassessment_eligible"] = True
    item["audio_required"] = False
    item["speaking_capture_enabled"] = False
    item["runtime_generation_used"] = False
    item["admission_proposal"] = {
        "status": "AUTO_APPROVED",
        "reason_codes": ["U01QB10_COUNT_PRESERVING_PRODUCTION_RECONCILIATION"],
    }
    source_refs = list(item.get("source_refs") or [])
    source_refs.append(
        {
            "source_type": "U01QB01_APPROVED_ITEM_RECONCILIATION",
            "source_item_id": str(source["item_id"]),
            "source_pattern_family_id": source_family,
            "reconciliation_task_id": TASK_ID,
        }
    )
    item["source_refs"] = source_refs
    item["reconciliation_source_item_id"] = str(source["item_id"])

    if family_id == PF13:
        wrong = seed.wrong_article(art)
        model = f"{art} {noun}"
        item.update(
            {
                "question_type": "error_correction",
                "task_angle": "ERROR_CHECK",
                "prompt": "Correct the article in the noun phrase.",
                "stimulus": f"{wrong} {noun}",
                "options": [],
                "correct_answer": model,
                "accepted_answers": [model],
                "scoring_mode": "NORMALIZED_TEXT",
                "support_level": "INDEPENDENT",
                "human_review_required": False,
                "response_contract": _response_contract(mode="NORMALIZED_TEXT", model_answer=model),
            }
        )
    elif family_id == PF14:
        model = f"There is {art} {noun} {location}."
        rubric = {
            "practice_only": False,
            "concept_features": [
                "first_mention_article",
                "target_noun_present",
                "sentence_complete",
            ],
            "surface_features": ["capitalization", "punctuation", "spelling"],
            "minor_surface_error_does_not_zero_concept": True,
        }
        if source_family == "U01-PF05-KNOWN-REFERENCE-CONTEXT":
            prompt = "Write one complete sentence. Use the starter There is to introduce the item in this place."
            stimulus = f"starter: There is | item: {noun} | place: {location}"
            support_level = "REDUCED_SUPPORT"
        elif source_family == "U01-PF08-TRANSFER-FIRST-MENTION":
            prompt = "Write one complete sentence. Introduce the item in this place."
            stimulus = f"item: {noun} | place: {location}"
            support_level = "INDEPENDENT"
        else:
            raise ReconciliationBuildError(f"PF14_SOURCE_FAMILY_INVALID:{source_family}")
        item.update(
            {
                "question_type": "complete_sentence_production",
                "task_angle": "COMPLETE_SENTENCE_PRODUCTION",
                "prompt": prompt,
                "stimulus": stimulus,
                "options": [],
                "correct_answer": model,
                "accepted_answers": [model],
                "scoring_mode": "FEATURE_RUBRIC",
                "support_level": support_level,
                "human_review_required": True,
                "response_contract": _response_contract(mode="FEATURE_RUBRIC", model_answer=model, rubric=rubric),
            }
        )
    elif family_id == PF15:
        model = f"There is {art} {noun} {location}. The {noun} is easy to see."
        rubric = {
            "practice_only": False,
            "concept_features": [
                "first_mention_article",
                "known_reference_article",
                "same_referent_preserved",
                "sentence_1_complete",
                "sentence_2_complete",
            ],
            "surface_features": ["capitalization", "punctuation", "spelling"],
            "minor_surface_error_does_not_zero_concept": True,
        }
        item.update(
            {
                "question_type": "connected_sentence_production",
                "task_angle": "CONNECTED_SENTENCE_PRODUCTION",
                "prompt": "Write two connected sentences. Introduce the item, then mention the same item again.",
                "stimulus": f"item: {noun} | place: {location}",
                "options": [],
                "correct_answer": model,
                "accepted_answers": [model],
                "scoring_mode": "FEATURE_RUBRIC",
                "support_level": "TRANSFER",
                "human_review_required": True,
                "response_contract": _response_contract(mode="FEATURE_RUBRIC", model_answer=model, rubric=rubric),
            }
        )
    else:
        raise ReconciliationBuildError(f"UNKNOWN_PRODUCTION_FAMILY:{family_id}")

    item["semantic_signature"] = seed.digest(
        {
            "family": item["pattern_family_id"],
            "structure": item["candidate_structure"],
            "context": item["context_id"],
            "slots": item["lexical_slots"],
            "prompt": item["prompt"],
            "stimulus": item["stimulus"],
            "options": item["options"],
            "answer": item["correct_answer"],
            "task_angle": item["task_angle"],
        }
    )
    return item


def _replacement_sources(items: Sequence[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for family_id, (count, _replacement_family) in REPLACEMENT_PLAN.items():
        rows = sorted(
            (deepcopy(dict(row)) for row in items if row.get("pattern_family_id") == family_id),
            key=lambda row: str(row["item_id"]),
        )
        if len(rows) < count:
            raise ReconciliationBuildError(f"REPLACEMENT_SOURCE_CAPACITY_INVALID:{family_id}:{len(rows)}")
        result[family_id] = rows[:count]
    return result


def _family_counts(items: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return dict(sorted(Counter(str(row["pattern_family_id"]) for row in items).items()))


def _skill_counts(items: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return dict(sorted(Counter(str(row["skill"]) for row in items).items()))


def reconciled_payload() -> dict[str, Any]:
    approved_seed, seed_items = seed_bank()
    replacements = _replacement_sources(seed_items)
    removed_ids = {
        str(row["item_id"])
        for rows in replacements.values()
        for row in rows
    }
    retained = [deepcopy(dict(row)) for row in seed_items if str(row["item_id"]) not in removed_ids]
    added: list[dict[str, Any]] = []
    for source_family, rows in replacements.items():
        replacement_family = REPLACEMENT_PLAN[source_family][1]
        added.extend(_production_item(row, replacement_family) for row in rows)
    items = sorted([*retained, *added], key=lambda row: str(row["item_id"]))
    if len(retained) != EXPECTED_RETAINED_COUNT or len(added) != EXPECTED_REPLACEMENT_COUNT:
        raise ReconciliationBuildError("COUNT_PRESERVATION_COMPONENT_INVALID")
    if len(items) != EXPECTED_APPROVED_COUNT:
        raise ReconciliationBuildError(f"RECONCILED_COUNT_INVALID:{len(items)}")
    if len({row["item_id"] for row in items}) != len(items):
        raise ReconciliationBuildError("DUPLICATE_ITEM_ID")
    if len({row["semantic_signature"] for row in items}) != len(items):
        raise ReconciliationBuildError("DUPLICATE_SEMANTIC_SIGNATURE")

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "unit_id": UNIT_ID,
        "bank_identity": {
            "bank_id": BANK_ID,
            "bank_version": BANK_VERSION,
            "canonical_revision": CANONICAL_REVISION,
            "supersedes_runtime_activation": False,
            "second_question_bank_created": False,
        },
        "source_identity": {
            "seed_task_id": seed.TASK_ID,
            "seed_bank_artifact_sha256": approved_seed["artifact_sha256"],
            "seed_approved_item_count": len(seed_items),
            "approved_contract_sha256": APPROVED_CONTRACT_SHA256,
        },
        "count_preservation": {
            "seed_base_count": len(seed_items),
            "retained_base_count": len(retained),
            "removed_base_count": len(removed_ids),
            "production_items_added": len(added),
            "reconciled_base_count": len(items),
            "unchanged_real62_extension_count": EXPECTED_EXTENSION_COUNT,
            "projected_runtime_total_count": EXPECTED_PROJECTED_RUNTIME_COUNT,
            "runtime_activation_completed": False,
        },
        "replacement_plan": [
            {
                "source_pattern_family_id": source_family,
                "removed_count": len(replacements[source_family]),
                "replacement_pattern_family_id": replacement_family,
                "replacement_source_item_ids": [str(row["item_id"]) for row in replacements[source_family]],
            }
            for source_family, (_count, replacement_family) in REPLACEMENT_PLAN.items()
        ],
        "production_family_contracts": [deepcopy(row) for row in PRODUCTION_FAMILY_CONTRACTS],
        "reconciled_items": items,
        "distribution_counts": {
            "family": _family_counts(items),
            "skill": _skill_counts(items),
        },
        "production_angle_coverage": {
            "scored_gap_count_before": EXPECTED_SCORED_GAP_BEFORE,
            "scored_gap_count_after": EXPECTED_SCORED_GAP_AFTER,
            "scored_partial_support_remaining": EXPECTED_SCORED_PARTIAL_REMAINING,
            "writing_error_correction_slots_added": 12,
            "writing_complete_sentence_slots_added": 24,
            "writing_connected_sentence_slots_added": 12,
            "production_angle_alignment_ready": True,
            "question_bank_full_alignment_ready": False,
            "remaining_partial_angles": ["READING_REFERENCE_EVIDENCE", "WRITING_PHRASE_CONSTRUCTION"],
        },
        "scoring_contract": {
            "error_correction": "NORMALIZED_TEXT",
            "complete_sentence_production": "FEATURE_RUBRIC",
            "connected_sentence_production": "FEATURE_RUBRIC",
            "feature_rubric_routes_to_human_review": True,
            "minor_surface_error_does_not_zero_concept": True,
            "speaking_scoring_enabled": False,
        },
        "boundaries": {
            "new_scene_authored": False,
            "question_bank_total_expanded": False,
            "second_question_bank_created": False,
            "runtime_migrated": False,
            "real62_extension_modified": False,
            "learner_state_modified": False,
            "speaking_scoring_enabled": False,
            "unit02_to_unit24_modified": False,
            "a2_unlocked": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    payload["reconciliation_sha256"] = policy_artifact.digest(payload)
    return payload


def build_candidate() -> dict[str, Any]:
    payload = reconciled_payload()
    return policy_artifact.build_candidate(
        payload=payload,
        producer_id=TASK_ID,
        level_scope=["A1"],
        source_bindings={
            "seed_task_id": seed.TASK_ID,
            "seed_bank_id": BANK_ID,
            "seed_bank_version": BANK_VERSION,
            "canonical_revision": CANONICAL_REVISION,
            "count_preserving": True,
            "operator_decision_ref": DECISION_REF,
        },
    )


def admit_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    from ulga.validators import validate_a1fs_v1_u01qb10_unit01_question_bank_production_angle_coverage_reconciliation as validator

    receipt = validator.validate_candidate(candidate)
    return policy_artifact.admit_candidate(
        candidate,
        validation_receipts=[receipt],
        decision_ref=DECISION_REF,
        producer_id=TASK_ID,
    )


def materialize(*, candidate_path: Path, approved_path: Path, report_path: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    candidate = build_candidate()
    approved = admit_candidate(candidate)
    from ulga.validators import validate_a1fs_v1_u01qb10_unit01_question_bank_production_angle_coverage_reconciliation as validator

    report = validator.validate_approved(candidate, approved)
    if report["error_count"]:
        raise ReconciliationBuildError("APPROVED_VALIDATION_FAILED:" + "|".join(report["errors"]))
    write_json(candidate_path, candidate, private=True)
    write_json(approved_path, approved, private=True)
    write_json(report_path, report)
    return candidate, approved, report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--approved", type=Path, default=DEFAULT_APPROVED)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    try:
        _, approved, report = materialize(
            candidate_path=args.candidate.resolve(),
            approved_path=args.approved.resolve(),
            report_path=args.report.resolve(),
        )
    except (ReconciliationBuildError, policy_artifact.ContentPolicyBuildError, OSError, KeyError, TypeError, ValueError) as exc:
        print("STATUS=FAIL_A1FS_V1_U01QB10_UNIT01_QUESTION_BANK_PRODUCTION_ANGLE_COVERAGE_RECONCILIATION")
        print(f"ERROR={exc}")
        return 1
    payload = approved["payload"]
    print(f"STATUS={PASS_STATUS}")
    print(f"BASE_COUNT={payload['count_preservation']['reconciled_base_count']}")
    print(f"PROJECTED_RUNTIME_TOTAL={payload['count_preservation']['projected_runtime_total_count']}")
    print(f"SCORED_GAPS_AFTER={payload['production_angle_coverage']['scored_gap_count_after']}")
    print(f"RUNTIME_MIGRATED={payload['boundaries']['runtime_migrated']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
