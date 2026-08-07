#!/usr/bin/env python3
"""Close the two remaining Unit01 partial QuestionBank angles without count growth.

U01QB10 removed every scored GAP while deliberately leaving two PARTIAL angles:
READING_REFERENCE_EVIDENCE and WRITING_PHRASE_CONSTRUCTION. This milestone
reconciles a bounded subset of the already-approved 288-item base into explicit
families for those two capabilities. The base remains 288 and the accepted
Real62 extension remains 186, so projected runtime capacity remains 474.

This is a content-candidate milestone only. Runtime migration/capacity replay is
U01QB17B; no learner state, completed attempt, scoring authority, Unit02-24,
Speaking scoring, audio, or A2 state is modified here.
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
from ulga.builders import (
    build_a1fs_v1_u01qb10_unit01_question_bank_production_angle_coverage_reconciliation as u10,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB17A_Unit01RemainingPartialAngleFullAlignmentCandidateReconciliation"
SCHEMA_VERSION = "a1fs.v1.u01qb17a.unit01_remaining_partial_angle_full_alignment.v1"
PASS_STATUS = "PASS_A1FS_V1_U01QB17A_UNIT01_REMAINING_PARTIAL_ANGLE_FULL_ALIGNMENT_CANDIDATE_RECONCILIATION"
DECISION_REF = "OPERATOR_APPROVAL:2026-08-07:U01QB17"
UNIT_ID = u10.UNIT_ID
BANK_ID = u10.BANK_ID
BANK_VERSION = u10.BANK_VERSION
CANONICAL_REVISION = "U01QB17A-R1"
EXPECTED_BASE_COUNT = 288
EXPECTED_EXTENSION_COUNT = 186
EXPECTED_PROJECTED_RUNTIME_COUNT = 474
EXPECTED_PARTIAL_SLOTS_BEFORE = 36
EXPECTED_PARTIAL_ANGLES_BEFORE = (
    "READING_REFERENCE_EVIDENCE",
    "WRITING_PHRASE_CONSTRUCTION",
)
REPLACEMENTS_PER_FAMILY = 12
EXPECTED_REPLACEMENT_COUNT = REPLACEMENTS_PER_FAMILY * 2

SOURCE_REFERENCE_FAMILY = "U01-PF05-KNOWN-REFERENCE-CONTEXT"
SOURCE_PHRASE_FAMILY = "U01-PF07-WORD-ORDER"
PF16 = "U01-PF16-READING-REFERENCE-EVIDENCE"
PF17 = "U01-PF17-WRITING-PHRASE-CONSTRUCTION"

DEFAULT_CANDIDATE = Path("ulga/private/a1fs_v1_u01qb17a_unit01_full_alignment.candidate.private.json")
DEFAULT_APPROVED = Path("ulga/private/a1fs_v1_u01qb17a_unit01_full_alignment.approved.private.json")
DEFAULT_REPORT = Path("ulga/reports/a1fs_v1_u01qb17a_unit01_full_alignment_validation.json")
NEXT_SHORT_STEP = "A1FS-V1-U01QB17B_Unit01FullAlignmentRuntimeCapacityAndSafeUnboundFormMigration"


class FullAlignmentBuildError(ValueError):
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


def source_bank() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    candidate = u10.build_candidate()
    approved = u10.admit_candidate(candidate)
    payload = approved.get("payload") or {}
    items = payload.get("reconciled_items")
    if not isinstance(items, list) or len(items) != EXPECTED_BASE_COUNT:
        raise FullAlignmentBuildError("U01QB10_SOURCE_BASE_INVALID")
    coverage = payload.get("production_angle_coverage") or {}
    if coverage.get("scored_partial_support_remaining") != EXPECTED_PARTIAL_SLOTS_BEFORE:
        raise FullAlignmentBuildError("U01QB10_PARTIAL_DENOMINATOR_DRIFT")
    if tuple(coverage.get("remaining_partial_angles") or ()) != EXPECTED_PARTIAL_ANGLES_BEFORE:
        raise FullAlignmentBuildError("U01QB10_PARTIAL_ANGLE_IDENTITY_DRIFT")
    return approved, [deepcopy(dict(row)) for row in items]


def _response_contract(*, mode: str, model_answer: str) -> dict[str, Any]:
    return {
        "scoring_mode": mode,
        "response_type": "string",
        "accepted_texts": [model_answer],
        "accepted_sequence": [],
        "capture_enabled": True,
        "human_review_fallback": False,
        "rubric": {},
    }


def _context(source: Mapping[str, Any]) -> tuple[str, str, str]:
    slots = dict(source.get("lexical_slots") or {})
    noun = str(slots.get("noun") or "")
    context_id = str(source.get("context_id") or slots.get("context_id") or "")
    if not noun or context_id not in u10.seed.CONTEXT_LOCATION:
        raise FullAlignmentBuildError(f"SOURCE_CONTEXT_INVALID:{source.get('item_id')}")
    return noun, context_id, u10.seed.CONTEXT_LOCATION[context_id]


def _base_reconciled_item(source: Mapping[str, Any], *, family_id: str, ordinal: int) -> dict[str, Any]:
    item = deepcopy(dict(source))
    item["item_id"] = f"U01QB17A-{family_id}-{ordinal:02d}-{u10.seed.slug(str(source['item_id']))}"
    item["pattern_family_id"] = family_id
    item["learner_visible_capable"] = True
    item["learner_delivery_status"] = "NOT_RUNTIME_CONNECTED"
    item["assessment_eligible"] = True
    item["reassessment_eligible"] = True
    item["audio_required"] = False
    item["speaking_capture_enabled"] = False
    item["runtime_generation_used"] = False
    item["human_review_required"] = False
    item["admission_proposal"] = {
        "status": "AUTO_APPROVED",
        "reason_codes": ["U01QB17A_REMAINING_PARTIAL_ANGLE_RECONCILIATION"],
    }
    refs = list(item.get("source_refs") or [])
    refs.append(
        {
            "source_type": "U01QB10_APPROVED_ITEM_RECONCILIATION",
            "source_item_id": str(source["item_id"]),
            "source_pattern_family_id": str(source["pattern_family_id"]),
            "reconciliation_task_id": TASK_ID,
        }
    )
    item["source_refs"] = refs
    item["reconciliation_source_item_id"] = str(source["item_id"])
    return item


def _reference_evidence_item(source: Mapping[str, Any], ordinal: int) -> dict[str, Any]:
    noun, context_id, location = _context(source)
    article = u10.seed.article(noun)
    model = f"The {noun}"
    item = _base_reconciled_item(source, family_id=PF16, ordinal=ordinal)
    item.update(
        {
            "skill": "READING",
            "question_type": "reference_evidence",
            "task_angle": "REFERENCE_EVIDENCE",
            "prompt": "Choose the words in sentence 2 that show it is the same item.",
            "stimulus": f"There is {article} {noun} {location}. The {noun} is easy to see.",
            "options": [model, f"{article} {noun}", location],
            "correct_answer": model,
            "accepted_answers": [model],
            "scoring_mode": "EXACT_TEXT",
            "support_level": "REDUCED_SUPPORT" if ordinal <= 6 else "INDEPENDENT",
            "response_contract": _response_contract(mode="EXACT_TEXT", model_answer=model),
        }
    )
    item["lexical_slots"] = {**dict(item.get("lexical_slots") or {}), "noun": noun, "context_id": context_id}
    return item


def _phrase_model(source: Mapping[str, Any]) -> str:
    answer = source.get("correct_answer")
    if isinstance(answer, (list, tuple)):
        model = " ".join(str(token) for token in answer).strip()
    else:
        model = str(answer or "").strip()
    if not model:
        raise FullAlignmentBuildError(f"PHRASE_MODEL_MISSING:{source.get('item_id')}")
    return model


def _phrase_construction_item(source: Mapping[str, Any], ordinal: int) -> dict[str, Any]:
    model = _phrase_model(source)
    slots = dict(source.get("lexical_slots") or {})
    cue_words = [str(value) for key, value in sorted(slots.items()) if key in {"adjective", "noun"} and value]
    if not cue_words:
        cue_words = [token for token in model.split() if token.casefold() not in {"a", "an", "the"}]
    item = _base_reconciled_item(source, family_id=PF17, ordinal=ordinal)
    item.update(
        {
            "skill": "WRITING",
            "question_type": "phrase_construction",
            "task_angle": "PHRASE_CONSTRUCTION",
            "prompt": "Write the complete noun phrase with the correct article.",
            "stimulus": "words: " + " / ".join(cue_words),
            "options": [],
            "correct_answer": model,
            "accepted_answers": [model],
            "scoring_mode": "NORMALIZED_TEXT",
            "support_level": "GUIDED" if ordinal <= 6 else "REDUCED_SUPPORT",
            "response_contract": _response_contract(mode="NORMALIZED_TEXT", model_answer=model),
        }
    )
    return item


def _sources(items: Sequence[Mapping[str, Any]], family_id: str) -> list[dict[str, Any]]:
    rows = sorted(
        (deepcopy(dict(row)) for row in items if row.get("pattern_family_id") == family_id),
        key=lambda row: str(row["item_id"]),
    )
    if len(rows) < REPLACEMENTS_PER_FAMILY:
        raise FullAlignmentBuildError(f"SOURCE_FAMILY_CAPACITY_INVALID:{family_id}:{len(rows)}")
    return rows[:REPLACEMENTS_PER_FAMILY]


def _counts(items: Sequence[Mapping[str, Any]], key: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row[key]) for row in items).items()))


def reconciled_payload() -> dict[str, Any]:
    approved_source, source_items = source_bank()
    reference_sources = _sources(source_items, SOURCE_REFERENCE_FAMILY)
    phrase_sources = _sources(source_items, SOURCE_PHRASE_FAMILY)
    removed_ids = {str(row["item_id"]) for row in [*reference_sources, *phrase_sources]}
    retained = [deepcopy(dict(row)) for row in source_items if str(row["item_id"]) not in removed_ids]
    added = [
        *[_reference_evidence_item(row, index) for index, row in enumerate(reference_sources, 1)],
        *[_phrase_construction_item(row, index) for index, row in enumerate(phrase_sources, 1)],
    ]
    items = sorted([*retained, *added], key=lambda row: str(row["item_id"]))
    if len(removed_ids) != EXPECTED_REPLACEMENT_COUNT or len(added) != EXPECTED_REPLACEMENT_COUNT:
        raise FullAlignmentBuildError("REPLACEMENT_COUNT_INVALID")
    if len(items) != EXPECTED_BASE_COUNT:
        raise FullAlignmentBuildError(f"BASE_COUNT_DRIFT:{len(items)}")
    if len({str(row["item_id"]) for row in items}) != len(items):
        raise FullAlignmentBuildError("DUPLICATE_ITEM_ID")

    for item in added:
        item["semantic_signature"] = u10.seed.digest(
            {
                "family": item["pattern_family_id"],
                "prompt": item["prompt"],
                "stimulus": item["stimulus"],
                "options": item["options"],
                "answer": item["correct_answer"],
                "task_angle": item["task_angle"],
                "support_level": item["support_level"],
            }
        )
    if len({str(row["semantic_signature"]) for row in items}) != len(items):
        raise FullAlignmentBuildError("DUPLICATE_SEMANTIC_SIGNATURE")

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
            "second_question_bank_created": False,
        },
        "source_identity": {
            "source_task_id": u10.TASK_ID,
            "source_canonical_revision": u10.CANONICAL_REVISION,
            "source_approved_artifact_sha256": approved_source["artifact_sha256"],
            "source_base_count": len(source_items),
        },
        "count_preservation": {
            "source_base_count": len(source_items),
            "retained_base_count": len(retained),
            "removed_base_count": len(removed_ids),
            "full_alignment_items_added": len(added),
            "reconciled_base_count": len(items),
            "unchanged_real62_extension_count": EXPECTED_EXTENSION_COUNT,
            "projected_runtime_total_count": EXPECTED_PROJECTED_RUNTIME_COUNT,
            "runtime_activation_completed": False,
        },
        "replacement_plan": [
            {
                "source_pattern_family_id": SOURCE_REFERENCE_FAMILY,
                "replacement_pattern_family_id": PF16,
                "replacement_count": len(reference_sources),
                "source_item_ids": [str(row["item_id"]) for row in reference_sources],
            },
            {
                "source_pattern_family_id": SOURCE_PHRASE_FAMILY,
                "replacement_pattern_family_id": PF17,
                "replacement_count": len(phrase_sources),
                "source_item_ids": [str(row["item_id"]) for row in phrase_sources],
            },
        ],
        "full_alignment_family_contracts": [
            {
                "family_id": PF16,
                "skill": "READING",
                "question_type": "reference_evidence",
                "task_angle": "REFERENCE_EVIDENCE",
                "approved_count": REPLACEMENTS_PER_FAMILY,
                "support_progression": ["REDUCED_SUPPORT", "INDEPENDENT"],
                "scoring_mode": "EXACT_TEXT",
            },
            {
                "family_id": PF17,
                "skill": "WRITING",
                "question_type": "phrase_construction",
                "task_angle": "PHRASE_CONSTRUCTION",
                "approved_count": REPLACEMENTS_PER_FAMILY,
                "support_progression": ["GUIDED", "REDUCED_SUPPORT"],
                "scoring_mode": "NORMALIZED_TEXT",
            },
        ],
        "reconciled_items": items,
        "distribution_counts": {
            "family": _counts(items, "pattern_family_id"),
            "skill": _counts(items, "skill"),
        },
        "partial_angle_alignment": {
            "scored_partial_support_slots_before": EXPECTED_PARTIAL_SLOTS_BEFORE,
            "remaining_partial_angles_before": list(EXPECTED_PARTIAL_ANGLES_BEFORE),
            "explicit_full_support_families_added": [PF16, PF17],
            "remaining_partial_angles_after_candidate_reconciliation": [],
            "content_contract_full_alignment_candidate_ready": True,
            "runtime_capacity_replay_pending": True,
            "runtime_full_alignment_claimed": False,
        },
        "boundaries": {
            "question_bank_total_expanded": False,
            "second_question_bank_created": False,
            "runtime_migrated": False,
            "real62_extension_modified": False,
            "learner_state_modified": False,
            "completed_attempts_modified": False,
            "speaking_scoring_enabled": False,
            "audio_enabled": False,
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
            "source_task_id": u10.TASK_ID,
            "source_canonical_revision": u10.CANONICAL_REVISION,
            "bank_id": BANK_ID,
            "bank_version": BANK_VERSION,
            "count_preserving": True,
            "operator_decision_ref": DECISION_REF,
        },
    )


def admit_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    from ulga.validators import validate_a1fs_v1_u01qb17a_unit01_remaining_partial_angle_full_alignment_candidate_reconciliation as validator

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
    from ulga.validators import validate_a1fs_v1_u01qb17a_unit01_remaining_partial_angle_full_alignment_candidate_reconciliation as validator

    report = validator.validate_approved(candidate, approved)
    if report["error_count"]:
        raise FullAlignmentBuildError("APPROVED_VALIDATION_FAILED:" + "|".join(report["errors"]))
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
    except (FullAlignmentBuildError, policy_artifact.ContentPolicyBuildError, OSError, KeyError, TypeError, ValueError) as exc:
        print("STATUS=FAIL_A1FS_V1_U01QB17A_UNIT01_REMAINING_PARTIAL_ANGLE_FULL_ALIGNMENT_CANDIDATE_RECONCILIATION")
        print(f"ERROR={exc}")
        return 1
    payload = approved["payload"]
    print(f"STATUS={PASS_STATUS}")
    print(f"BASE_COUNT={payload['count_preservation']['reconciled_base_count']}")
    print(f"PROJECTED_RUNTIME_TOTAL={payload['count_preservation']['projected_runtime_total_count']}")
    print(f"REMAINING_PARTIAL_ANGLES={len(payload['partial_angle_alignment']['remaining_partial_angles_after_candidate_reconciliation'])}")
    print(f"RUNTIME_MIGRATED={payload['boundaries']['runtime_migrated']}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
