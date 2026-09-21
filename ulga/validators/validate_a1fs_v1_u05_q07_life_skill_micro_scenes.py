from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import build_a1fs_v1_u05_q06_sentence_assets as q06_builder
from ulga.builders import build_a1fs_v1_u05_q07_life_skill_micro_scenes as builder

VALIDATOR_ID = "validate_a1fs_v1_u05_q07_life_skill_micro_scenes_v1"


def _q06_identity(row: Mapping[str, Any]) -> str:
    return str(row.get("sentence_id") or row.get("binding_id") or "")


def _validate_payload(payload: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    try:
        if payload.get("status") != "PASS_A1FS_V1_U05Q07_LIFE_SKILL_MICRO_SCENE_MATERIALIZATION_AND_SENTENCE_BINDING":
            errors.append("STATUS_INVALID")

        q06 = q06_builder.build_report()
        q06_rows = [*q06["reuse_bindings"], *q06["new_sentence_assets"]]
        q06_context = [row for row in q06_rows if row["requires_context_binding"] is True]
        q06_standalone = [row for row in q06_rows if row["requires_context_binding"] is False]
        if (len(q06_rows), len(q06_context), len(q06_standalone)) != (855, 478, 377):
            errors.append("Q06_SOURCE_COUNTS_DRIFT")

        scenes = list(payload.get("micro_scenes", []))
        bindings = list(payload.get("sentence_scene_bindings", []))
        if len(bindings) != 478:
            errors.append("BINDING_COUNT_INVALID")
        if not 0 < len(scenes) < 478:
            errors.append("SCENE_GROUPING_NOT_EFFECTIVE")
        if len({row.get("scene_ref_id") for row in scenes}) != len(scenes):
            errors.append("SCENE_ID_NOT_DISTINCT")
        if len({row.get("semantic_scene_key_sha256") for row in scenes}) != len(scenes):
            errors.append("SEMANTIC_SCENE_KEY_NOT_DISTINCT")
        if len({row.get("binding_id") for row in bindings}) != 478:
            errors.append("BINDING_ID_NOT_DISTINCT")

        q06_context_ids = {_q06_identity(row) for row in q06_context}
        q06_standalone_ids = {_q06_identity(row) for row in q06_standalone}
        bound_ids = {str(row.get("q06_identity")) for row in bindings}
        if bound_ids != q06_context_ids:
            errors.append("CONTEXT_REQUIRED_BINDING_SET_MISMATCH")
        if bound_ids & q06_standalone_ids:
            errors.append("STANDALONE_SENTENCE_FORCED_INTO_SCENE_BINDING")

        scene_ids = {str(row.get("scene_ref_id")) for row in scenes}
        if {str(row.get("scene_ref_id")) for row in bindings} != scene_ids:
            errors.append("SCENE_REFERENCE_SET_MISMATCH")

        governed = set(payload.get("prior_scene_authority", {}).get("governed_scene_families", []))
        if len(governed) != 17:
            errors.append("GOVERNED_SCENE_FAMILY_DENOMINATOR_INVALID")
        if not all(row.get("scene_family") in governed for row in scenes):
            errors.append("UNGOVERNED_SCENE_FAMILY_USED")
        if any(row.get("canonical_scene_scope") != "UNIT05_LOCAL_AUTHORITATIVE_INSTANCE" for row in scenes):
            errors.append("SCENE_SCOPE_INVALID")

        for scene in scenes:
            truth = scene.get("truth_evidence_spec", {})
            answer = scene.get("answerability_guard", {})
            if truth.get("target_sentence_may_be_used_as_scene_prompt") is not False:
                errors.append("TARGET_SENTENCE_PROMPT_LEAK")
                break
            if answer.get("scene_binds_truth_of_all_bound_sentences") is not True:
                errors.append("SCENE_TRUTH_BINDING_MISSING")
                break
            if answer.get("unbound_context_required_use_allowed") is not False:
                errors.append("UNBOUND_CONTEXT_USE_ALLOWED")
                break
            if answer.get("learner_visible_target_sentence_used_as_scene_prompt") is not False:
                errors.append("LEARNER_TARGET_SENTENCE_PROMPT_LEAK")
                break
            if scene.get("polarity") == "NEGATIVE":
                if truth.get("explicit_positive_alternative_required_for_negative") is not True:
                    errors.append("NEGATIVE_POSITIVE_CONTRAST_REQUIRED")
                    break
                if truth.get("negation_proof_by_absence_allowed") is not False:
                    errors.append("NEGATION_BY_ABSENCE_FORBIDDEN")
                    break
            if scene.get("subject_class") in {"he", "she", "it", "they"}:
                if scene.get("referent_binding_spec", {}).get("required") is not True:
                    errors.append("PRONOUN_ANTECEDENT_BINDING_REQUIRED")
                    break

        coverage = payload.get("coverage", {})
        if coverage.get("q06_usable_sentence_supply_count") != 855:
            errors.append("COVERAGE_USABLE_COUNT_INVALID")
        if coverage.get("q06_context_required_sentence_surface_count") != 478:
            errors.append("COVERAGE_CONTEXT_REQUIRED_COUNT_INVALID")
        if coverage.get("q06_standalone_sentence_surface_count") != 377:
            errors.append("COVERAGE_STANDALONE_COUNT_INVALID")
        if coverage.get("sentence_scene_binding_count") != 478:
            errors.append("COVERAGE_BINDING_COUNT_INVALID")
        if coverage.get("q06_unbound_context_required_sentence_count") != 0:
            errors.append("UNBOUND_CONTEXT_REQUIRED_NONZERO")
        if coverage.get("unit05_scene_instance_count") != len(scenes):
            errors.append("COVERAGE_SCENE_COUNT_DRIFT")
        if coverage.get("surface_variant_scene_reuse_count") != 478 - len(scenes):
            errors.append("SURFACE_VARIANT_SCENE_REUSE_COUNT_DRIFT")
        if sum(coverage.get("used_scene_family_counts", {}).values()) != len(scenes):
            errors.append("SCENE_FAMILY_COUNT_SUM_INVALID")
        if sum(coverage.get("binding_frame_counts", {}).values()) != 478:
            errors.append("BINDING_FRAME_COUNT_SUM_INVALID")
        if sum(coverage.get("binding_polarity_counts", {}).values()) != 478:
            errors.append("BINDING_POLARITY_COUNT_SUM_INVALID")

        if Counter(row.get("scene_family") for row in scenes) != Counter(coverage.get("used_scene_family_counts", {})):
            errors.append("SCENE_FAMILY_COVERAGE_DRIFT")
        if Counter(row.get("frame_id") for row in bindings) != Counter(coverage.get("binding_frame_counts", {})):
            errors.append("BINDING_FRAME_COVERAGE_DRIFT")
        if Counter(row.get("polarity") for row in bindings) != Counter(coverage.get("binding_polarity_counts", {})):
            errors.append("BINDING_POLARITY_COVERAGE_DRIFT")

        b = payload.get("q07_boundaries", {})
        locked_false = (
            "q06_sentence_assets_mutated",
            "unit04_scene_content_used_as_unit05_generation_authority",
            "unit04_reader360_used_as_unit05_authority",
            "global_canonical_scene_library_rewritten",
            "communicative_functions_materialized",
            "questionbank_materialized",
            "forms_materialized",
            "unit05_current360_materialized",
            "unit05_spoken360_materialized",
            "unit05_pattern360_materialized",
            "be_interrogative_mastery_activated",
            "past_be_activated",
            "existential_there_be_activated",
            "present_continuous_mastery_activated",
            "a2_a2plus_unlocked",
        )
        if any(b.get(key) is not False for key in locked_false):
            errors.append("Q07_BOUNDARY_UNLOCK_DETECTED")

        if payload.get("next_short_step") != "A1FS-V1-U05Q08_Unit05CommunicativeFunctionAuthority":
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
