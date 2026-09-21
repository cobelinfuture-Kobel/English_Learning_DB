from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import build_a1fs_v1_u05_q06_sentence_assets as builder

VALIDATOR_ID = "validate_a1fs_v1_u05_q06_sentence_assets_v1"


def _validate_payload(payload: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    try:
        if payload.get("status") != "PASS_A1FS_V1_U05Q06_SENTENCE_ASSET_PRODUCTION_AND_SEMANTIC_ADMISSION":
            errors.append("STATUS_INVALID")
        a = payload.get("acceptance", {})
        if a.get("surface_candidate_count") != 884:
            errors.append("CANDIDATE_COUNT_INVALID")
        if a.get("semantic_review_usable_count") != 855:
            errors.append("USABLE_COUNT_INVALID")
        if a.get("validated_predecessor_reuse_binding_count") != 94:
            errors.append("REUSE_COUNT_INVALID")
        if a.get("unit05_new_admitted_sentence_asset_count") != 761:
            errors.append("NEW_ASSET_COUNT_INVALID")
        if a.get("deferred_count") != 12 or a.get("rejected_count") != 17:
            errors.append("EXCLUDED_COUNT_INVALID")
        if a.get("full_predecessor_dedup_row_count") != 26610:
            errors.append("PREDECESSOR_ROW_COUNT_INVALID")
        if a.get("full_predecessor_collision_count") != 100:
            errors.append("PREDECESSOR_COLLISION_COUNT_INVALID")

        reuse = list(payload.get("reuse_bindings", []))
        new_assets = list(payload.get("new_sentence_assets", []))
        excluded = list(payload.get("excluded_candidates", []))
        usable = [*reuse, *new_assets]
        if (len(reuse), len(new_assets), len(excluded), len(usable)) != (94, 761, 29, 855):
            errors.append("MATERIALIZED_LIST_COUNTS_INVALID")
        if len({row.get("normalized_text") for row in usable}) != 855:
            errors.append("USABLE_NORMALIZED_TEXT_NOT_DISTINCT")
        if len({row.get("sentence_id") for row in new_assets}) != 761:
            errors.append("NEW_SENTENCE_ID_NOT_DISTINCT")

        frame_counts = Counter(row.get("frame_id") for row in usable)
        if dict(sorted(frame_counts.items())) != payload.get("coverage", {}).get("frame_counts"):
            errors.append("FRAME_COVERAGE_DRIFT")
        subject_counts = Counter(row.get("subject_class") for row in usable)
        if dict(sorted(subject_counts.items())) != dict(sorted(payload.get("coverage", {}).get("subject_class_counts", {}).items())):
            errors.append("SUBJECT_COVERAGE_DRIFT")
        admission_counts = Counter(row.get("semantic_admission_class") for row in usable)
        if dict(sorted(admission_counts.items())) != dict(sorted(payload.get("coverage", {}).get("semantic_admission_class_counts", {}).items())):
            errors.append("SEMANTIC_ADMISSION_COVERAGE_DRIFT")

        g = payload.get("generation_authority", {})
        if g.get("unit_local_only") is not True:
            errors.append("UNIT_LOCAL_AUTHORITY_REQUIRED")
        if g.get("reader360_generation_authority_used") is not False:
            errors.append("READER360_AUTHORITY_FORBIDDEN")
        if g.get("unit04_current360_used_as_generation_authority") is not False:
            errors.append("U04_CURRENT360_AUTHORITY_FORBIDDEN")
        if g.get("unit04_spoken360_used_as_generation_authority") is not False:
            errors.append("U04_SPOKEN360_AUTHORITY_FORBIDDEN")
        if g.get("unit04_pattern360_used_as_generation_authority") is not False:
            errors.append("U04_PATTERN360_AUTHORITY_FORBIDDEN")
        if g.get("unit05_reader360_materialized") is not False:
            errors.append("U05_READER360_PREMATURE")

        d = payload.get("predecessor_dedup_receipt", {})
        if d.get("full_replay_performed") is not True:
            errors.append("FULL_PREDECESSOR_REPLAY_REQUIRED")
        if d.get("source_rows") != {"U01": 3805, "U02": 3726, "U03": 18983, "U04": 96}:
            errors.append("PREDECESSOR_SOURCE_ROWS_INVALID")
        u03 = d.get("private_source_evidence", {}).get("U03", {})
        if u03.get("dedup_only_not_semantic_authority") is not True:
            errors.append("U03_DEDUP_ONLY_BOUNDARY_REQUIRED")
        if u03.get("private_sentence_bodies_committed") is not False or u03.get("private_sentence_fingerprints_committed") is not False:
            errors.append("U03_PRIVATE_EVIDENCE_COMMITTED")

        boundaries = payload.get("q06_boundaries", {})
        locked_false = (
            "unit04_reader360_used_as_unit05_authority",
            "unit05_reader360_materialized",
            "scene_materialized",
            "communicative_functions_materialized",
            "questionbank_materialized",
            "forms_materialized",
            "be_interrogative_target_sentence_allowed",
            "past_be_target_sentence_allowed",
            "existential_there_be_target_sentence_allowed",
            "present_continuous_target_sentence_allowed",
            "a2_a2plus_unlocked",
        )
        if any(boundaries.get(key) is not False for key in locked_false):
            errors.append("Q06_BOUNDARY_UNLOCK_DETECTED")

        if payload.get("next_short_step") != "A1FS-V1-U05Q07_Unit05LifeSkillMicroSceneMaterializationAndSentenceBinding":
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
