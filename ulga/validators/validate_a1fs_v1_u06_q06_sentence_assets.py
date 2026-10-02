from __future__ import annotations

import re
from collections import Counter
from typing import Any, Mapping

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import build_a1fs_v1_u06_q06_sentence_assets as builder

VALIDATOR_ID = "validate_a1fs_v1_u06_q06_sentence_assets_v1"


def _validate_payload(payload: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    try:
        if payload.get("status") != builder.PASS_STATUS:
            errors.append("STATUS_INVALID")
        a = payload.get("acceptance", {})
        if a.get("authored_candidate_count") != 135:
            errors.append("CANDIDATE_COUNT_INVALID")
        if a.get("semantic_review_usable_count") != 129:
            errors.append("USABLE_COUNT_INVALID")
        if a.get("unit06_new_admitted_sentence_asset_count") != 129:
            errors.append("NEW_ASSET_COUNT_INVALID")
        if a.get("deferred_count") != 6 or a.get("rejected_count") != 0:
            errors.append("EXCLUDED_COUNT_INVALID")
        if a.get("predecessor_dedup_denominator") != 27371:
            errors.append("PREDECESSOR_DENOMINATOR_INVALID")
        if a.get("predecessor_collision_count") != 0:
            errors.append("PREDECESSOR_COLLISION_INVALID")

        reuse = list(payload.get("reuse_bindings", []))
        assets = list(payload.get("new_sentence_assets", []))
        excluded = list(payload.get("excluded_candidates", []))
        if reuse:
            errors.append("PREDECESSOR_REUSE_NOT_EXPECTED")
        if len(assets) != 129 or len(excluded) != 6:
            errors.append("MATERIALIZED_LIST_COUNTS_INVALID")
        if len({row.get("sentence_id") for row in assets}) != 129:
            errors.append("SENTENCE_ID_NOT_DISTINCT")
        if len({row.get("normalized_text") for row in assets}) != 129:
            errors.append("NORMALIZED_TEXT_NOT_DISTINCT")

        for row in assets:
            text = str(row.get("text", ""))
            if " can " not in f" {text.casefold()} ":
                errors.append("CAN_SURFACE_MISSING")
                break
            if "?" in text or re.search(r"\b(?:cannot|can't|can\s+not)\b", text, flags=re.I):
                errors.append("QUESTION_OR_NEGATIVE_LEAK")
                break
            if re.search(r"\bcan\s+to\b", text, flags=re.I):
                errors.append("CAN_TO_VERB_LEAK")
                break
            if row.get("semantic_admission_class") not in {"APPROVE", "CONTEXT_BOUND_APPROVE"}:
                errors.append("NON_ADMITTED_ASSET")
                break
            if row.get("semantic_admission_class") == "CONTEXT_BOUND_APPROVE" and row.get("requires_context_binding") is not True:
                errors.append("CONTEXT_BOUND_FLAG_MISSING")
                break
            if row.get("a2_unlocked") is not False:
                errors.append("A2_UNLOCK_LEAK")
                break

        frame_counts = dict(sorted(Counter(row.get("frame_id") for row in assets).items()))
        if frame_counts != payload.get("coverage", {}).get("frame_counts"):
            errors.append("FRAME_COVERAGE_DRIFT")
        if set(frame_counts) != {
            "U06-CF-ABILITY-INTRANSITIVE",
            "U06-CF-ABILITY-OBJECT",
            "U06-CF-ABILITY-PREDICATE-TAIL",
        }:
            errors.append("THREE_FRAME_COVERAGE_REQUIRED")

        subject_counts = dict(sorted(Counter(row.get("subject_class") for row in assets).items()))
        expected_subjects = dict(sorted(payload.get("coverage", {}).get("subject_class_counts", {}).items()))
        if subject_counts != expected_subjects:
            errors.append("SUBJECT_COVERAGE_DRIFT")
        for subject in ("I", "you", "he", "she", "it", "we", "they", "ADMITTED_PERSON_OR_ROLE_NOUN_PHRASE"):
            if subject_counts.get(subject, 0) <= 0:
                errors.append(f"SUBJECT_CLASS_MISSING:{subject}")

        coverage = payload.get("coverage", {})
        if coverage.get("q04r1_can_base_verb_surface_count") != 62:
            errors.append("CAN_BASE_DENOMINATOR_INVALID")
        if coverage.get("q06_sentence_admitted_can_base_verb_surface_count") != 56:
            errors.append("CAN_BASE_ADMITTED_INVALID")
        if coverage.get("q06_sentence_deferred_can_base_verb_surface_count") != 6:
            errors.append("CAN_BASE_DEFERRED_INVALID")
        if set(coverage.get("deferred_can_base_verbs", [])) != {"change", "do", "give", "go", "study", "tell"}:
            errors.append("DEFERRED_BASE_SET_INVALID")
        if coverage.get("q04r1_functional_chunk_surface_count") != 41:
            errors.append("FUNCTIONAL_DENOMINATOR_INVALID")
        if coverage.get("q06_sentence_admitted_functional_chunk_surface_count") != 39:
            errors.append("FUNCTIONAL_ADMITTED_INVALID")
        if coverage.get("q06_sentence_deferred_functional_chunk_surface_count") != 2:
            errors.append("FUNCTIONAL_DEFERRED_INVALID")
        if set(coverage.get("deferred_functional_chunks", [])) != {"can go to school", "can study at school"}:
            errors.append("DEFERRED_FUNCTIONAL_SET_INVALID")

        d = payload.get("predecessor_dedup_receipt", {})
        if d.get("predecessor_asset_row_count") != 27371:
            errors.append("DEDUP_DENOMINATOR_DRIFT")
        if d.get("q05_exact_and_normalized_dedup_required") is not True:
            errors.append("Q05_DEDUP_GATE_MISSING")
        if d.get("proof_mode") != "CURRENT_COURSE_PATTERN_FAMILY_DISJOINTNESS_PLUS_CANDIDATE_EXACT_NORMALIZED_IDENTITY_CHECK":
            errors.append("DEDUP_PROOF_MODE_INVALID")
        if d.get("unit06_newly_unlocked_family") != "family:ability_can":
            errors.append("ABILITY_FAMILY_LINEAGE_INVALID")
        if d.get("full_private_predecessor_sentence_body_replay_performed") is not False:
            errors.append("PRIVATE_REPLAY_CLAIM_INVALID")
        if d.get("private_u01_u03_sentence_bodies_committed") is not False:
            errors.append("PRIVATE_BODIES_EXPOSED")

        g = payload.get("generation_authority", {})
        if g.get("learner_english_authoring_mode") != "GPT-5.6_SOL_EXPLICIT_AUTHORED_AND_REVIEWED_SEED":
            errors.append("AUTHORING_MODE_INVALID")
        if g.get("python_builder_english_generation_allowed") is not False:
            errors.append("PYTHON_ENGLISH_GENERATION_FORBIDDEN")
        if g.get("reader360_generation_authority_used") is not False:
            errors.append("READER360_AUTHORITY_FORBIDDEN")
        if g.get("q07_scene_authority_used") is not False:
            errors.append("Q07_SCENE_PREMATURE")

        boundaries = payload.get("q06_boundaries", {})
        if any(boundaries.get(key) is not False for key in (
            "scene_materialized",
            "communicative_functions_materialized",
            "questionbank_materialized",
            "forms_materialized",
            "reader360_materialized",
            "can_question_target_sentence_allowed",
            "can_negative_target_sentence_allowed",
            "non_ability_can_target_sentence_allowed",
            "a2_a2plus_grammar_unlocked",
        )):
            errors.append("Q06_BOUNDARY_UNLOCK_DETECTED")

        if payload.get("next_short_step") != "A1FS-V1-U06Q07_Unit06LifeSkillMicroSceneMaterializationAndSentenceBinding":
            errors.append("NEXT_SHORT_STEP_INVALID")
    except Exception as exc:
        errors.append(f"PAYLOAD_VALIDATION_EXCEPTION:{type(exc).__name__}:{exc}")
    return errors


def validate_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    try:
        policy_artifact.verify_artifact_digest(candidate)
    except Exception as exc:
        errors.append(f"CANDIDATE_DIGEST:{exc}")
    if candidate.get("artifact_role") != "CANDIDATE_JSON":
        errors.append("CANDIDATE_ROLE_INVALID")
    if candidate.get("producer_id") != builder.TASK_ID:
        errors.append("PRODUCER_ID_INVALID")
    if candidate.get("level_scope") != ["A1"]:
        errors.append("LEVEL_SCOPE_INVALID")
    errors.extend(_validate_payload(candidate.get("payload", {})))
    core = {
        "validator_id": VALIDATOR_ID,
        "status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "candidate_artifact_sha256": candidate.get("artifact_sha256"),
    }
    if errors:
        raise ValueError(";".join(errors))
    return {
        "validator_id": VALIDATOR_ID,
        "status": "PASS",
        "receipt_sha256": builder.digest(core),
    }


def validate_approved(candidate: Mapping[str, Any], approved: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    try:
        policy_artifact.verify_artifact_digest(candidate)
        policy_artifact.verify_artifact_digest(approved)
    except Exception as exc:
        errors.append(f"ARTIFACT_DIGEST:{exc}")
    if approved.get("artifact_role") != "APPROVED_CANONICAL_JSON":
        errors.append("APPROVED_ROLE_INVALID")
    if approved.get("producer_id") != builder.TASK_ID:
        errors.append("APPROVED_PRODUCER_ID_INVALID")
    if approved.get("admission", {}).get("decision_ref") != builder.DECISION_REF:
        errors.append("DECISION_REF_INVALID")
    if approved.get("payload") != candidate.get("payload"):
        errors.append("APPROVED_PAYLOAD_DRIFT")
    errors.extend(_validate_payload(approved.get("payload", {})))
    return {
        "validator_id": VALIDATOR_ID,
        "status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
    }
