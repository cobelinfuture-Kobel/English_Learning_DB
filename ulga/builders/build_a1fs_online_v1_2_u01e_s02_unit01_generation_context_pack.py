#!/usr/bin/env python3
"""Build deterministic Unit 01 question-generation context packs.

S02 consumes the approved S01 five-context package and the existing learner
database read-only. It creates a learner-safe authoring pack and a local-only
learner-adaptive pack. Both packs may only request candidate JSON; neither pack
can write canonical content, expose hidden answers/responses, infer mastery, or
unlock A2.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import (
    build_a1fs_online_v1_2_u01e_s01_unit01_five_context_authority_admission as s01,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Builds deterministic prompt context from an already-approved Unit 01 "
    "artifact and read-only attempt metadata. It creates no learner content, "
    "answer, scoring rule, canonical write, learner-state mutation, mastery "
    "decision, audio, A2 unlock, external route, or parallel authority."
)

PROGRAM_ID = "A1FS-ONLINE-V1.2-U01E"
TASK_ID = (
    "A1FS-ONLINE-V1.2-U01E-S02_"
    "Unit01MultiStandardQuestionGenerationContextPack"
)
SCHEMA_VERSION = "a1fs.online.v1_2.u01e.s02.generation_context_pack.v1"
PASS_STATUS = "PASS_A1FS_ONLINE_V1_2_U01E_S02_GENERATION_CONTEXT_PACK"
NEXT_SHORT_STEP = (
    "A1FS-ONLINE-V1.2-U01E-S03_"
    "Unit01MultiTypeExerciseCandidateGenerationAndAdmission"
)
SAFE_PACK_TYPE = "UNIT01_AUTHORING_CONTEXT_SAFE"
PRIVATE_PACK_TYPE = "UNIT01_LEARNER_CONTEXT_PRIVATE"
EXPECTED_CONTEXT_COUNT = 5
EXPECTED_EXISTING_ITEM_COUNT = 11
EXPECTED_CAMBRIDGE_PATTERN_COUNT = 8
WEAK_OUTCOMES = {"AUTO_FAIL", "HUMAN_REJECT"}
PASS_OUTCOMES = {"AUTO_PASS", "HUMAN_APPROVE"}
PENDING_OUTCOMES = {"PENDING_HUMAN_REVIEW", "HUMAN_DEFER", "UNSCORED"}
FORBIDDEN_SOURCE_KEYS = {
    "accepted_texts",
    "accepted_sequence",
    "correct_answer",
    "answer",
    "response_json",
    "contract_json",
    "private_scoring_contract",
    "scoring_contract",
}
TARGET_FIELDS = (
    "target_evp_sense_ids",
    "target_egp_row_ids",
    "target_chunk_ids",
    "target_context_phrase_ids",
    "target_sentence_ids",
    "target_pattern_ids",
    "target_ket_prerequisite_node_ids",
)
OUTPUT_FIELDS = (
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
    "target_sentence_ids",
    "target_pattern_ids",
    "target_ket_node_ids",
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
)


class S02ContextPackError(ValueError):
    """Fail-closed S02 source, privacy, or prompt-context error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise S02ContextPackError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise S02ContextPackError(f"{code}_not_object")
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


def walk_keys(value: Any) -> Iterable[str]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            yield str(key)
            yield from walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_keys(child)


def load_approved_s01(path: Path) -> dict[str, Any]:
    approved = read_json(path, "s01_approved")
    try:
        policy_artifact.verify_artifact_digest(approved)
    except policy_artifact.ContentPolicyBuildError as exc:
        raise S02ContextPackError(f"s01_approved_digest_invalid:{exc}") from exc
    if approved.get("artifact_role") != policy_artifact.APPROVED_ROLE:
        raise S02ContextPackError("s01_approved_role_invalid")
    if approved.get("producer_id") != s01.TASK_ID:
        raise S02ContextPackError("s01_approved_producer_invalid")
    if approved.get("admission", {}).get("status") != "APPROVED":
        raise S02ContextPackError("s01_approved_status_invalid")
    payload = approved.get("payload")
    if not isinstance(payload, Mapping):
        raise S02ContextPackError("s01_approved_payload_missing")
    if payload.get("unit_id") != s01.m01.UNIT_ID:
        raise S02ContextPackError("s01_unit_identity_invalid")
    if len(payload.get("contexts", [])) != EXPECTED_CONTEXT_COUNT:
        raise S02ContextPackError("s01_context_denominator_invalid")
    if len(payload.get("existing_asset_target_index", [])) != EXPECTED_EXISTING_ITEM_COUNT:
        raise S02ContextPackError("s01_item_index_denominator_invalid")
    leaked = sorted(FORBIDDEN_SOURCE_KEYS & set(walk_keys(approved)))
    if leaked:
        raise S02ContextPackError(f"s01_hidden_source_key_detected:{leaked[0]}")
    return approved


def semantic_signature(row: Mapping[str, Any]) -> dict[str, Any]:
    semantic = {
        "skill": str(row.get("skill") or ""),
        "question_type": str(row.get("question_type") or ""),
        "assessment_pattern_ref": str(row.get("assessment_pattern_ref") or ""),
        "context_id": str(row.get("context_id") or ""),
        "spec_id": str(row.get("spec_id") or ""),
        "target_refs": {
            field: sorted(str(value) for value in row.get(field, []) if value)
            for field in TARGET_FIELDS
        },
    }
    return {
        "semantic_signature": digest(semantic),
        "skill": semantic["skill"],
        "question_type": semantic["question_type"],
        "context_id": semantic["context_id"],
        "assessment_pattern_ref": semantic["assessment_pattern_ref"],
    }


def static_generation_context(payload: Mapping[str, Any]) -> dict[str, Any]:
    language = payload["language_targets"]
    cambridge = payload["cambridge_alignment"]
    patterns = cambridge.get("task_compatibility", {})
    if not isinstance(patterns, Mapping) or len(patterns) != EXPECTED_CAMBRIDGE_PATTERN_COUNT:
        raise S02ContextPackError("cambridge_assessment_pattern_denominator_invalid")
    item_index = payload["existing_asset_target_index"]
    signatures = [semantic_signature(row) for row in item_index]
    if len({row["semantic_signature"] for row in signatures}) != len(signatures):
        raise S02ContextPackError("existing_semantic_signature_collision")
    productive = [
        {"authority_id": row["authority_id"], "label": row["label"]}
        for row in language["vocabulary"]
        if row["learning_role"] == "NEW_PRODUCTIVE"
    ]
    receptive = [
        {"authority_id": row["authority_id"], "label": row["label"]}
        for row in language["vocabulary"]
        if row["learning_role"] == "NEW_RECEPTIVE"
    ]
    return {
        "unit": {
            "unit_id": payload["unit_id"],
            "level_scope": list(payload["level_scope"]),
            "selection_model": payload["selection_model"],
            "cambridge_stage": cambridge["cambridge_stage"],
            "cambridge_policy_decision": cambridge["policy_decision"],
            "a2_handoff_blocked": True,
        },
        "approved_contexts": [
            {
                "context_id": row["context_id"],
                "role": row["role"],
                "setting": row["setting"],
                "title": row["title"],
                "sentences": list(row["sentences"]),
                "source_role": row["source_role"],
            }
            for row in payload["contexts"]
        ],
        "curriculum_targets": {
            "new_productive_vocabulary": productive,
            "new_receptive_vocabulary": receptive,
            "canonical_chunks": [
                {"authority_id": row["authority_id"], "label": row["label"]}
                for row in language["canonical_chunks"]
            ],
            "context_phrases": [
                {
                    "phrase_id": row["phrase_id"],
                    "label": row["label"],
                    "canonical_chunk_coverage_allowed": False,
                }
                for row in language["context_phrases"]
            ],
            "sentences": [
                {
                    "sentence_id": row["sentence_id"],
                    "context_id": row["context_id"],
                    "text": row["text"],
                    "learning_role": row["learning_role"],
                }
                for row in language["sentences"]
            ],
            "patterns": [
                {"authority_id": row["authority_id"], "label": row["label"]}
                for row in language["patterns"]
            ],
            "egp_row_ids": sorted(str(row) for row in language["egp_row_ids"]),
            "ket_prerequisite_node_ids": [],
            "ket_binding_status": payload["ket_prerequisite_alignment"]["activity_level_bridge_status"],
        },
        "assessment_policy": {
            "allowed_pattern_refs": sorted(str(key) for key in patterns),
            "pattern_compatibility": dict(sorted((str(key), str(value)) for key, value in patterns.items())),
            "blocked_pattern_refs": ["FLYERS_A2_LANGUAGE_TARGET", "A2_KEY_FORMAL_TASK"],
            "minimum_distinct_question_types": 8,
            "target_activity_range": [20, 26],
            "no_filler_policy": True,
        },
        "existing_item_dedup": {
            "existing_item_count": len(signatures),
            "semantic_signatures": signatures,
            "reject_existing_semantic_signature": True,
        },
        "generation_budget_contract": {
            "support_level_percent": {
                "GUIDED": 40,
                "REDUCED_SUPPORT": 30,
                "INDEPENDENT": 20,
                "UNSEEN_TRANSFER": 10,
            },
            "learning_role_percent_default": {
                "NEW": 50,
                "WEAK_CARRYOVER": 0,
                "REVIEW": 30,
                "TRANSFER": 20,
            },
            "learning_role_percent_with_weak_items": {
                "NEW": 40,
                "WEAK_CARRYOVER": 30,
                "REVIEW": 20,
                "TRANSFER": 10,
            },
        },
        "candidate_output_contract": {
            "artifact_role": "CANDIDATE_JSON",
            "format": "JSON_ONLY",
            "required_fields": list(OUTPUT_FIELDS),
            "direct_canonical_write_allowed": False,
            "admission_required_before_runtime": True,
        },
        "hard_rules": [
            "USE_ONLY_APPROVED_A1_A1PLUS_TARGETS_AND_SUPPORT",
            "DO_NOT_INTRODUCE_UNLISTED_PRODUCTIVE_TARGETS",
            "DO_NOT_PROMOTE_OBSERVED_ONLY_MATERIAL",
            "DO_NOT_CLAIM_MASTERY",
            "DO_NOT_INVENT_AUTHORITY_IDS_OR_SOURCE_CLAIMS",
            "DO_NOT_REPEAT_EXISTING_SEMANTIC_SIGNATURES",
            "AUTO_SCORED_ITEMS_REQUIRE_ONE_DETERMINISTIC_ANSWER",
            "SPEAKING_REMAINS_PRACTICE_ONLY",
            "LISTENING_AUDIO_REMAINS_DISABLED",
            "A2_AND_FLYERS_LANGUAGE_TARGETS_REMAIN_BLOCKED",
        ],
    }


def table_names(connection: sqlite3.Connection) -> set[str]:
    return {
        str(row[0])
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }


def target_sets(rows: Sequence[Mapping[str, Any]]) -> dict[str, set[str]]:
    return {
        field: {
            str(value)
            for row in rows
            for value in row.get(field, [])
            if value
        }
        for field in TARGET_FIELDS
    }


def sorted_target_sets(value: Mapping[str, set[str]]) -> dict[str, list[str]]:
    return {field: sorted(value.get(field, set())) for field in TARGET_FIELDS}


def subtract_target_sets(
    left: Mapping[str, set[str]], right: Mapping[str, set[str]]
) -> dict[str, list[str]]:
    return {field: sorted(left.get(field, set()) - right.get(field, set())) for field in TARGET_FIELDS}


def inspect_learner_state(
    *,
    database_path: Path,
    learner_id: str,
    item_index: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    learner_id = str(learner_id or "").strip()
    if not learner_id:
        raise S02ContextPackError("learner_id_required")
    allowed_assets = {str(row["asset_key"]) for row in item_index}
    if len(allowed_assets) != EXPECTED_EXISTING_ITEM_COUNT:
        raise S02ContextPackError("item_index_asset_identity_invalid")
    placeholders = ",".join("?" for _ in allowed_assets)
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        required = {"response_attempts", "scoring_results"}
        missing = required - table_names(connection)
        if missing:
            raise S02ContextPackError(f"learner_database_tables_missing:{sorted(missing)[0]}")
        rows = connection.execute(
            "SELECT a.attempt_id,a.asset_key,a.attempt_sequence,a.submitted_at,"
            "COALESCE(s.outcome,'UNSCORED') AS outcome "
            "FROM response_attempts a LEFT JOIN scoring_results s ON s.attempt_id=a.attempt_id "
            f"WHERE a.learner_id=? AND a.asset_key IN ({placeholders}) "
            "ORDER BY a.submitted_at,a.attempt_id",
            (learner_id, *sorted(allowed_assets)),
        ).fetchall()

    latest_by_asset: dict[str, dict[str, Any]] = {}
    recent_attempts: list[dict[str, Any]] = []
    outcome_counts: Counter[str] = Counter()
    for row in rows:
        outcome = str(row["outcome"])
        item = {
            "attempt_id": str(row["attempt_id"]),
            "asset_key": str(row["asset_key"]),
            "attempt_sequence": int(row["attempt_sequence"]),
            "submitted_at": str(row["submitted_at"]),
            "outcome": outcome,
        }
        recent_attempts.append(item)
        latest_by_asset[item["asset_key"]] = item
        outcome_counts[outcome] += 1

    index_by_asset = {str(row["asset_key"]): row for row in item_index}
    attempted_rows = [index_by_asset[key] for key in latest_by_asset]
    weak_assets = sorted(
        key for key, row in latest_by_asset.items() if row["outcome"] in WEAK_OUTCOMES
    )
    passed_assets = sorted(
        key for key, row in latest_by_asset.items() if row["outcome"] in PASS_OUTCOMES
    )
    pending_assets = sorted(
        key for key, row in latest_by_asset.items() if row["outcome"] in PENDING_OUTCOMES
    )
    weak_rows = [index_by_asset[key] for key in weak_assets]
    passed_rows = [index_by_asset[key] for key in passed_assets]
    all_targets = target_sets(item_index)
    practised_targets = target_sets(attempted_rows)
    weak_targets = target_sets(weak_rows)
    review_targets = target_sets(passed_rows)
    budget = (
        {"NEW": 40, "WEAK_CARRYOVER": 30, "REVIEW": 20, "TRANSFER": 10}
        if weak_assets
        else {"NEW": 50, "WEAK_CARRYOVER": 0, "REVIEW": 30, "TRANSFER": 20}
    )
    error_tags = sorted(
        {
            f"{latest_by_asset[key]['outcome']}:{index_by_asset[key]['question_type']}"
            for key in weak_assets
        }
    )
    state_core = {
        "learner_id": learner_id,
        "attempt_count": len(recent_attempts),
        "distinct_attempted_asset_count": len(latest_by_asset),
        "outcome_counts": dict(sorted(outcome_counts.items())),
        "latest_evidence_by_asset": [
            latest_by_asset[key] for key in sorted(latest_by_asset)
        ],
        "weak_asset_keys": weak_assets,
        "passed_asset_keys": passed_assets,
        "pending_asset_keys": pending_assets,
        "target_state": {
            "unseen": subtract_target_sets(all_targets, practised_targets),
            "practised": sorted_target_sets(practised_targets),
            "weak": sorted_target_sets(weak_targets),
            "review": sorted_target_sets(review_targets),
        },
        "recent_error_tags": error_tags,
        "generation_learning_role_percent": budget,
        "mastery_state": "NOT_INFERRED_FROM_ATTEMPT_OUTCOMES",
    }
    return {**state_core, "learner_state_sha256": digest(state_core)}


def render_prompt(pack_type: str, context: Mapping[str, Any]) -> str:
    role = (
        "You generate governed Unit 01 candidate activities for the shared A1FS curriculum."
        if pack_type == SAFE_PACK_TYPE
        else "You generate learner-adaptive Unit 01 candidate activities using the supplied private learner evidence."
    )
    return (
        "SYSTEM ROLE\n"
        f"{role}\n\n"
        "NON-NEGOTIABLE OUTPUT\n"
        "Return structured JSON candidate items only. Do not write canonical data. "
        "Every item must remain a candidate until independent validation and admission.\n\n"
        "UNIT 01 GENERATION CONTEXT\n"
        + json.dumps(context, ensure_ascii=False, sort_keys=True, indent=2)
        + "\n"
    )


def finalized_pack(core: Mapping[str, Any]) -> dict[str, Any]:
    prompt = render_prompt(str(core["pack_type"]), core["generation_context"])
    value = {
        **dict(core),
        "prompt_text": prompt,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
    }
    return {**value, "pack_sha256": digest(value)}


def build_packs(
    *,
    approved_s01_path: Path,
    database_path: Path,
    learner_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    approved = load_approved_s01(approved_s01_path)
    payload = approved["payload"]
    static_context = static_generation_context(payload)
    source_identity = {
        "s01_task_id": s01.TASK_ID,
        "s01_approved_artifact_sha256": approved["artifact_sha256"],
        "s01_approved_file_sha256": file_digest(approved_s01_path),
    }
    boundaries = {
        "candidate_generation_only": True,
        "canonical_write_allowed": False,
        "learner_database_written": False,
        "hidden_answer_exposed": False,
        "learner_response_exposed": False,
        "mastery_inferred": False,
        "unit02_modified": False,
        "audio_enabled": False,
        "speaking_capture_enabled": False,
        "a2_unlocked": False,
    }
    stale = {
        "requires_exact_s01_approved_artifact_sha256": True,
        "rebuild_when_s01_artifact_changes": True,
    }
    safe_core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "pack_type": SAFE_PACK_TYPE,
        "source_identity": source_identity,
        "generation_context": static_context,
        "stale_state_contract": stale,
        "claim_boundaries": boundaries,
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    safe = finalized_pack(safe_core)

    learner = inspect_learner_state(
        database_path=database_path,
        learner_id=learner_id,
        item_index=payload["existing_asset_target_index"],
    )
    private_context = {
        **static_context,
        "learner_state": learner,
        "generation_budget_contract": {
            **static_context["generation_budget_contract"],
            "active_learning_role_percent": learner["generation_learning_role_percent"],
        },
    }
    private_source = {
        **source_identity,
        "learner_database_sha256": file_digest(database_path),
        "learner_state_sha256": learner["learner_state_sha256"],
    }
    private_stale = {
        **stale,
        "requires_exact_learner_database_sha256": True,
        "rebuild_when_learner_evidence_changes": True,
    }
    private_core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "pack_type": PRIVATE_PACK_TYPE,
        "source_identity": private_source,
        "generation_context": private_context,
        "stale_state_contract": private_stale,
        "claim_boundaries": boundaries,
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    private = finalized_pack(private_core)
    return safe, private


def materialize(
    *,
    approved_s01_path: Path,
    database_path: Path,
    learner_id: str,
    safe_path: Path,
    private_path: Path,
    report_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    safe, private = build_packs(
        approved_s01_path=approved_s01_path,
        database_path=database_path,
        learner_id=learner_id,
    )
    from ulga.validators import (
        validate_a1fs_online_v1_2_u01e_s02_unit01_generation_context_pack as validator,
    )

    report = validator.validate_packs(safe, private)
    if report["error_count"]:
        raise S02ContextPackError("validation_failed:" + "|".join(report["errors"]))
    write_json(safe_path, safe)
    write_json(private_path, private, private=True)
    write_json(report_path, report)
    return safe, private, report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved-s01", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--learner-id", required=True)
    parser.add_argument("--safe", type=Path, required=True)
    parser.add_argument("--private", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        _, _, report = materialize(
            approved_s01_path=args.approved_s01,
            database_path=args.database,
            learner_id=args.learner_id,
            safe_path=args.safe,
            private_path=args.private,
            report_path=args.report,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (
        S02ContextPackError,
        policy_artifact.ContentPolicyBuildError,
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
