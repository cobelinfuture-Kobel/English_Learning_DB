#!/usr/bin/env python3
"""Build deterministic Unit 01 question-generation context packs.

S02 emits two inputs for later candidate generation:

* a learner-safe authoring pack containing only approved curriculum metadata;
* a private learner pack containing target-level attempt aggregates, never raw
  responses, hidden answers, scoring contracts, or mastery claims.

Neither pack contains generated questions and neither may write canonical data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import (
    build_a1fs_online_v1_2_u01e_s01_unit01_five_context_authority_admission as s01,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Builds deterministic prompt context and target-level learner aggregates from "
    "already-approved Unit 01 metadata. It creates no question content, answer, "
    "scoring rule, canonical write, learner-state write, mastery decision, audio, "
    "A2 unlock, external route, or parallel authority."
)

PROGRAM_ID = "A1FS-ONLINE-V1.2-U01E"
TASK_ID = (
    "A1FS-ONLINE-V1.2-U01E-S02_"
    "Unit01MultiStandardQuestionGenerationContextPack"
)
SCHEMA_VERSION = "a1fs.online.v1_2.u01e.s02.question_generation_context_pack.v1"
PASS_STATUS = "PASS_A1FS_ONLINE_V1_2_U01E_S02_QUESTION_GENERATION_CONTEXT_PACK"
NEXT_SHORT_STEP = (
    "A1FS-ONLINE-V1.2-U01E-S03_"
    "Unit01MultiTypeExerciseCandidateGenerationAndAdmission"
)

SAFE_PACK_ROLE = "UNIT01_AUTHORING_CONTEXT_SAFE"
PRIVATE_PACK_ROLE = "UNIT01_LEARNER_CONTEXT_PRIVATE"
TARGET_TOTAL_ACTIVITY_COUNT = 24
EXISTING_ACTIVITY_COUNT = 11
NEW_CANDIDATE_TARGET_COUNT = TARGET_TOTAL_ACTIVITY_COUNT - EXISTING_ACTIVITY_COUNT
ALLOWED_TOTAL_ACTIVITY_RANGE = (20, 26)
ALLOWED_NEW_CANDIDATE_RANGE = (
    ALLOWED_TOTAL_ACTIVITY_RANGE[0] - EXISTING_ACTIVITY_COUNT,
    ALLOWED_TOTAL_ACTIVITY_RANGE[1] - EXISTING_ACTIVITY_COUNT,
)

NEW_SKILL_DISTRIBUTION = {"READING": 6, "WRITING": 4, "SPEAKING": 3}
NEW_CONTEXT_DISTRIBUTION = {
    "U01-C2-HOME-TOY-BOX": 3,
    "U01-C3-PICNIC-FOOD": 3,
    "U01-C4-TOY-SHOP": 3,
    "U01-C5-PARK-BIRTHDAY": 4,
}
NEW_QUESTION_TYPE_DISTRIBUTION = {
    "multiple_choice": 1,
    "context_match": 2,
    "error_discrimination": 1,
    "gap_fill": 2,
    "word_order": 2,
    "guided_sentence": 3,
    "checkpoint_choice": 1,
    "checkpoint_write": 1,
}
LEARNING_ROLE_DISTRIBUTION = {
    "NEW": 5,
    "WEAK": 3,
    "REVIEW": 3,
    "TRANSFER": 2,
}
SUPPORT_LEVEL_DISTRIBUTION = {
    "GUIDED": 5,
    "REDUCED_SUPPORT": 4,
    "INDEPENDENT": 2,
    "UNSEEN_TRANSFER": 2,
}

TARGET_FIELDS = {
    "evp_sense_ids": "target_evp_sense_ids",
    "egp_row_ids": "target_egp_row_ids",
    "canonical_chunk_ids": "target_chunk_ids",
    "context_phrase_ids": "target_context_phrase_ids",
    "sentence_ids": "target_sentence_ids",
    "pattern_ids": "target_pattern_ids",
    "ket_prerequisite_node_ids": "target_ket_prerequisite_node_ids",
}
FAILED_OUTCOMES = {"AUTO_FAIL", "HUMAN_REJECT", "REJECTED"}
PASS_OUTCOMES = {"AUTO_PASS", "HUMAN_APPROVE", "APPROVED"}

REQUIRED_CANDIDATE_OUTPUT_FIELDS = [
    "candidate_item_id",
    "skill",
    "question_type",
    "stimulus",
    "prompt",
    "options",
    "correct_answer",
    "acceptable_variants",
    "explanation",
    "target_evp_sense_ids",
    "target_egp_row_ids",
    "target_chunk_ids",
    "target_context_phrase_ids",
    "target_sentence_ids",
    "target_pattern_ids",
    "target_ket_prerequisite_node_ids",
    "cambridge_stage",
    "cambridge_capability_refs",
    "assessment_pattern_ref",
    "learning_role",
    "support_level",
    "context_id",
    "source_refs",
    "answerability_evidence",
    "error_tags",
    "remediation_tags",
]


class S02ContextPackError(ValueError):
    """Fail-closed context-pack source, privacy, or identity error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def finalize(core: Mapping[str, Any]) -> dict[str, Any]:
    value = deepcopy(dict(core))
    value["pack_sha256"] = digest(value)
    return value


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


def write_text(path: Path, value: str, *, private: bool = False) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding="utf-8")
    os.replace(temporary, path)
    if private:
        try:
            path.chmod(0o600)
        except OSError:
            pass


def verified_s01_approved(database_path: Path) -> dict[str, Any]:
    candidate = s01.build_candidate(database_path)
    approved = s01.admit_candidate(candidate)
    if approved.get("artifact_role") != "APPROVED_CANONICAL_JSON":
        raise S02ContextPackError("s01_approved_role_invalid")
    if approved.get("admission", {}).get("status") != "APPROVED":
        raise S02ContextPackError("s01_approved_status_invalid")
    if approved.get("admission", {}).get("decision_ref") != s01.DECISION_REF:
        raise S02ContextPackError("s01_approved_decision_invalid")
    return approved


def target_inventory(payload: Mapping[str, Any]) -> dict[str, list[str]]:
    language = payload.get("language_targets", {})
    result = {
        "evp_sense_ids": sorted(
            str(row["authority_id"]) for row in language.get("vocabulary", [])
        ),
        "egp_row_ids": sorted(str(row) for row in language.get("egp_row_ids", [])),
        "canonical_chunk_ids": sorted(
            str(row["authority_id"]) for row in language.get("canonical_chunks", [])
        ),
        "context_phrase_ids": sorted(
            str(row["phrase_id"]) for row in language.get("context_phrases", [])
        ),
        "sentence_ids": sorted(
            str(row["sentence_id"]) for row in language.get("sentences", [])
        ),
        "pattern_ids": sorted(
            str(row["authority_id"]) for row in language.get("patterns", [])
        ),
        "ket_prerequisite_node_ids": sorted(
            str(row)
            for row in payload.get("ket_prerequisite_alignment", {}).get(
                "target_node_ids", []
            )
        ),
    }
    for field, rows in result.items():
        if len(rows) != len(set(rows)):
            raise S02ContextPackError(f"target_inventory_duplicate:{field}")
    return result


def safe_asset_index(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source in payload.get("existing_asset_target_index", []):
        row = {
            "asset_key": source["asset_key"],
            "lesson_id": source["lesson_id"],
            "skill": source["skill"],
            "spec_id": source["spec_id"],
            "question_type": source["question_type"],
            "assessment_pattern_ref": source["assessment_pattern_ref"],
            "context_id": source["context_id"],
            "cambridge_stage": source["cambridge_stage"],
            "binding_status": source["binding_status"],
            "ket_binding_status": source["ket_binding_status"],
        }
        for target_field in TARGET_FIELDS.values():
            row[target_field] = sorted(str(value) for value in source.get(target_field, []))
        signature_payload = {
            "skill": row["skill"],
            "spec_id": row["spec_id"],
            "question_type": row["question_type"],
            "context_id": row["context_id"],
            **{field: row[field] for field in TARGET_FIELDS.values()},
        }
        row["semantic_signature"] = digest(signature_payload)
        rows.append(row)
    rows.sort(key=lambda row: (row["lesson_id"], row["asset_key"]))
    if len(rows) != EXISTING_ACTIVITY_COUNT:
        raise S02ContextPackError(f"existing_asset_index_count_invalid:{len(rows)}")
    return rows


def generation_policy(payload: Mapping[str, Any]) -> dict[str, Any]:
    allowed = sorted(payload.get("cambridge_alignment", {}).get("task_compatibility", {}))
    if set(allowed) != set(NEW_QUESTION_TYPE_DISTRIBUTION):
        raise S02ContextPackError("question_type_distribution_outside_cambridge_policy")
    if sum(NEW_SKILL_DISTRIBUTION.values()) != NEW_CANDIDATE_TARGET_COUNT:
        raise S02ContextPackError("skill_distribution_count_invalid")
    if sum(NEW_CONTEXT_DISTRIBUTION.values()) != NEW_CANDIDATE_TARGET_COUNT:
        raise S02ContextPackError("context_distribution_count_invalid")
    if sum(NEW_QUESTION_TYPE_DISTRIBUTION.values()) != NEW_CANDIDATE_TARGET_COUNT:
        raise S02ContextPackError("question_type_distribution_count_invalid")
    if sum(LEARNING_ROLE_DISTRIBUTION.values()) != NEW_CANDIDATE_TARGET_COUNT:
        raise S02ContextPackError("learning_role_distribution_count_invalid")
    if sum(SUPPORT_LEVEL_DISTRIBUTION.values()) != NEW_CANDIDATE_TARGET_COUNT:
        raise S02ContextPackError("support_distribution_count_invalid")
    return {
        "generation_mode": "OFFLINE_CANDIDATE_ONLY",
        "existing_activity_count": EXISTING_ACTIVITY_COUNT,
        "target_total_activity_count": TARGET_TOTAL_ACTIVITY_COUNT,
        "requested_new_candidate_count": NEW_CANDIDATE_TARGET_COUNT,
        "allowed_new_candidate_range": list(ALLOWED_NEW_CANDIDATE_RANGE),
        "skill_distribution": deepcopy(NEW_SKILL_DISTRIBUTION),
        "context_distribution": deepcopy(NEW_CONTEXT_DISTRIBUTION),
        "question_type_distribution": deepcopy(NEW_QUESTION_TYPE_DISTRIBUTION),
        "learning_role_distribution": deepcopy(LEARNING_ROLE_DISTRIBUTION),
        "support_level_distribution": deepcopy(SUPPORT_LEVEL_DISTRIBUTION),
        "allowed_question_types": allowed,
        "blocked_question_types": [
            "LISTENING_WITHOUT_PLAYABLE_AUDIO",
            "SPEAKING_CAPTURE_OR_SCORING",
            "A2_OR_FLYERS_LANGUAGE_TARGET",
            "UNVALIDATED_RUNTIME_RANDOM_ITEM",
        ],
        "no_filler_policy": True,
        "approved_bank_required_before_learner_delivery": True,
        "randomization_policy": {
            "approved_item_selection_allowed": True,
            "approved_item_order_shuffle_allowed": True,
            "approved_option_order_shuffle_allowed": True,
            "free_runtime_generation_allowed": False,
            "unvalidated_variant_delivery_allowed": False,
        },
    }


def output_contract() -> dict[str, Any]:
    return {
        "output_format": "JSON_OBJECT_WITH_CANDIDATE_ITEMS_ARRAY",
        "required_item_fields": list(REQUIRED_CANDIDATE_OUTPUT_FIELDS),
        "candidate_only": True,
        "canonical_write_allowed": False,
        "learner_delivery_allowed": False,
        "stable_candidate_ids_required": True,
        "single_objectively_scoreable_answer_required_for_auto_scored_items": True,
        "human_review_contract_required_for_productive_open_response": True,
        "source_lineage_required": True,
        "semantic_signature_required": True,
    }


def hard_rules() -> list[str]:
    return [
        "Use only supplied A1 authority targets and supplied support language.",
        "Do not invent EVP, EGP, Chunk, Pattern, KET, Cambridge, source, or item IDs.",
        "Do not promote Unit context phrases into canonical Chunk coverage.",
        "Do not claim KET coverage while activity-level KET refs remain unresolved.",
        "Do not introduce A2 or Flyers language targets.",
        "Do not copy or claim raw RAZ or KET source text.",
        "Do not repeat an existing semantic signature.",
        "Do not expose hidden answers from existing assets.",
        "Do not infer stable or mastered learner state from one response.",
        "Return candidate JSON only; validation and admission are mandatory later steps.",
    ]


def build_safe_pack(approved: Mapping[str, Any]) -> dict[str, Any]:
    payload = approved.get("payload")
    if not isinstance(payload, Mapping):
        raise S02ContextPackError("s01_approved_payload_missing")
    assets = safe_asset_index(payload)
    contexts = [
        {
            "context_id": row["context_id"],
            "role": row["role"],
            "setting": row["setting"],
            "title": row["title"],
            "sentences": list(row["sentences"]),
            "source_role": row["source_role"],
        }
        for row in payload.get("contexts", [])
    ]
    core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "pack_role": SAFE_PACK_ROLE,
        "private": False,
        "unit_identity": {
            "unit_id": payload["unit_id"],
            "level_scope": list(payload["level_scope"]),
            "cambridge_stage": payload["cambridge_alignment"]["cambridge_stage"],
            "cambridge_policy_decision": payload["cambridge_alignment"]["policy_decision"],
        },
        "source_identity": {
            "s01_task_id": s01.TASK_ID,
            "s01_approved_sha256": approved["artifact_sha256"],
            "s01_decision_ref": approved["admission"]["decision_ref"],
        },
        "approved_contexts": contexts,
        "approved_language_targets": deepcopy(payload["language_targets"]),
        "unselected_material_vocabulary": deepcopy(
            payload["unselected_material_vocabulary"]
        ),
        "target_inventory": target_inventory(payload),
        "existing_asset_target_index": assets,
        "existing_semantic_signatures": sorted(
            row["semantic_signature"] for row in assets
        ),
        "authority_gaps": {
            "ket_activity_bridge_status": payload["ket_prerequisite_alignment"][
                "activity_level_bridge_status"
            ],
            "cambridge_granular_capability_status": payload[
                "cambridge_alignment"
            ]["granular_capability_status"],
            "flyers_or_a2_blocked": True,
        },
        "generation_policy": generation_policy(payload),
        "output_contract": output_contract(),
        "hard_rules": hard_rules(),
        "claim_boundaries": {
            "learner_private_data_included": False,
            "hidden_answers_included": False,
            "raw_responses_included": False,
            "generated_questions_included": False,
            "canonical_write_allowed": False,
            "runtime_generation_allowed": False,
            "unit02_modified": False,
            "audio_enabled": False,
            "speaking_capture_enabled": False,
            "a2_unlocked": False,
        },
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    return finalize(core)


def table_names(connection: sqlite3.Connection) -> set[str]:
    return {
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }


def aggregate_targets(
    rows: Sequence[Mapping[str, Any]], field_name: str
) -> dict[str, list[str]]:
    result: defaultdict[str, set[str]] = defaultdict(set)
    for row in rows:
        asset = row["asset"]
        for authority_name, target_field in TARGET_FIELDS.items():
            for target_id in asset.get(target_field, []):
                result[authority_name].add(str(target_id))
    return {
        authority: sorted(values)
        for authority, values in sorted(result.items())
    }


def learner_attempt_rows(
    *, database_path: Path, learner_id: str, safe_pack: Mapping[str, Any]
) -> list[dict[str, Any]]:
    if not learner_id.strip():
        raise S02ContextPackError("learner_id_required")
    by_asset = {
        str(row["asset_key"]): row
        for row in safe_pack.get("existing_asset_target_index", [])
    }
    lesson_ids = sorted({str(row["lesson_id"]) for row in by_asset.values()})
    placeholders = ",".join("?" for _ in lesson_ids)
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        required = {"response_attempts", "scoring_results"}
        missing = required - table_names(connection)
        if missing:
            raise S02ContextPackError(
                f"learner_database_tables_missing:{sorted(missing)[0]}"
            )
        attempts = connection.execute(
            "SELECT a.asset_key,a.lesson_id,a.submitted_at,s.outcome "
            "FROM response_attempts a "
            "LEFT JOIN scoring_results s ON s.attempt_id=a.attempt_id "
            f"WHERE a.learner_id=? AND a.lesson_id IN ({placeholders}) "
            "ORDER BY a.submitted_at,a.attempt_id",
            (learner_id, *lesson_ids),
        ).fetchall()
    rows: list[dict[str, Any]] = []
    for attempt in attempts:
        asset_key = str(attempt["asset_key"])
        asset = by_asset.get(asset_key)
        if not isinstance(asset, Mapping):
            raise S02ContextPackError(
                f"attempt_asset_not_in_safe_index:{asset_key}"
            )
        rows.append(
            {
                "asset": asset,
                "submitted_at": str(attempt["submitted_at"]),
                "outcome": str(attempt["outcome"] or "UNSCORED"),
            }
        )
    return rows


def build_private_pack(
    *,
    safe_pack: Mapping[str, Any],
    database_path: Path,
    learner_id: str,
) -> dict[str, Any]:
    attempts = learner_attempt_rows(
        database_path=database_path,
        learner_id=learner_id,
        safe_pack=safe_pack,
    )
    failed = [row for row in attempts if row["outcome"] in FAILED_OUTCOMES]
    passed = [row for row in attempts if row["outcome"] in PASS_OUTCOMES]
    outcomes = Counter(row["outcome"] for row in attempts)
    practised = aggregate_targets(attempts, "practised")
    weak = aggregate_targets(failed, "weak")
    passed_targets = aggregate_targets(passed, "passed")
    recent_contexts = list(
        dict.fromkeys(
            str(row["asset"]["context_id"])
            for row in reversed(attempts)
        )
    )
    weak_question_types = sorted(
        {
            str(row["asset"]["question_type"])
            for row in failed
        }
    )
    core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "pack_role": PRIVATE_PACK_ROLE,
        "private": True,
        "learner_id": learner_id,
        "source_identity": {
            "safe_pack_sha256": safe_pack["pack_sha256"],
            "learner_database_sha256": file_digest(database_path),
        },
        "safe_authoring_context": deepcopy(dict(safe_pack)),
        "learner_attempt_summary": {
            "attempt_count": len(attempts),
            "distinct_attempted_asset_count": len(
                {str(row["asset"]["asset_key"]) for row in attempts}
            ),
            "outcome_counts": dict(sorted(outcomes.items())),
            "recent_context_ids": recent_contexts,
            "weak_question_types": weak_question_types,
        },
        "learner_target_state": {
            "practised_target_ids": practised,
            "weak_target_ids": weak,
            "passed_target_ids": passed_targets,
            "stable_target_ids": {},
            "mastered_target_ids": {},
            "transfer_proven_target_ids": {},
            "stable_status": "NOT_AVAILABLE_FROM_CURRENT_EVIDENCE",
            "mastery_status": "NOT_AVAILABLE_FROM_CURRENT_EVIDENCE",
            "transfer_status": "NOT_AVAILABLE_FROM_CURRENT_EVIDENCE",
        },
        "adaptive_generation_priority": {
            "carry_over_weak_target_ids": weak,
            "avoid_recent_context_ids": recent_contexts[:2],
            "learning_role_distribution": deepcopy(
                LEARNING_ROLE_DISTRIBUTION
            ),
            "support_level_distribution": deepcopy(
                SUPPORT_LEVEL_DISTRIBUTION
            ),
            "do_not_infer_mastery": True,
        },
        "claim_boundaries": {
            "raw_responses_included": False,
            "hidden_answers_included": False,
            "attempt_ids_included": False,
            "learner_state_written": False,
            "mastery_inferred": False,
            "generated_questions_included": False,
            "canonical_write_allowed": False,
            "runtime_generation_allowed": False,
            "unit02_modified": False,
            "audio_enabled": False,
            "speaking_capture_enabled": False,
            "a2_unlocked": False,
        },
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    return finalize(core)


def render_prompt(pack: Mapping[str, Any]) -> str:
    role = str(pack.get("pack_role") or "")
    if role not in {SAFE_PACK_ROLE, PRIVATE_PACK_ROLE}:
        raise S02ContextPackError("prompt_pack_role_invalid")
    body = json.dumps(dict(pack), ensure_ascii=False, sort_keys=True, indent=2)
    return (
        "SYSTEM ROLE\n"
        "You generate offline candidate learning activities for A1FS Unit 01.\n"
        "You must obey the supplied authority targets, context allocation, Cambridge "
        "task-pattern policy, privacy boundaries, output contract, and hard rules.\n"
        "You do not have canonical write permission and your output is not learner-facing.\n\n"
        f"CONTEXT_PACK_ROLE={role}\n"
        f"CONTEXT_PACK_SHA256={pack['pack_sha256']}\n\n"
        "BEGIN_CONTEXT_PACK_JSON\n"
        f"{body}\n"
        "END_CONTEXT_PACK_JSON\n\n"
        "Return exactly one JSON object with a candidate_items array. "
        "Do not return Markdown, prose outside JSON, or any canonical-write claim.\n"
    )


def materialize(
    *,
    database_path: Path,
    learner_id: str,
    safe_json_path: Path,
    safe_prompt_path: Path,
    private_json_path: Path,
    private_prompt_path: Path,
    report_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    approved = verified_s01_approved(database_path)
    safe_pack = build_safe_pack(approved)
    private_pack = build_private_pack(
        safe_pack=safe_pack,
        database_path=database_path,
        learner_id=learner_id,
    )
    from ulga.validators import (
        validate_a1fs_online_v1_2_u01e_s02_question_generation_context_pack as validator,
    )

    report = validator.validate_packs(
        safe_pack=safe_pack,
        private_pack=private_pack,
        approved=approved,
        database_path=database_path,
        safe_prompt=render_prompt(safe_pack),
        private_prompt=render_prompt(private_pack),
    )
    if report["error_count"]:
        raise S02ContextPackError(
            "validation_failed:" + "|".join(report["errors"])
        )
    write_json(safe_json_path, safe_pack)
    write_text(safe_prompt_path, render_prompt(safe_pack))
    write_json(private_json_path, private_pack, private=True)
    write_text(private_prompt_path, render_prompt(private_pack), private=True)
    write_json(report_path, report)
    return safe_pack, private_pack, report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--learner-id", required=True)
    parser.add_argument("--safe-json", type=Path, required=True)
    parser.add_argument("--safe-prompt", type=Path, required=True)
    parser.add_argument("--private-json", type=Path, required=True)
    parser.add_argument("--private-prompt", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        _, _, report = materialize(
            database_path=args.database,
            learner_id=args.learner_id,
            safe_json_path=args.safe_json,
            safe_prompt_path=args.safe_prompt,
            private_json_path=args.private_json,
            private_prompt_path=args.private_prompt,
            report_path=args.report,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (
        S02ContextPackError,
        s01.S01AdmissionError,
        sqlite3.Error,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
