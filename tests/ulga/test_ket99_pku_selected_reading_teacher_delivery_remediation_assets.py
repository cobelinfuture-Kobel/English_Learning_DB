from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from ulga.builders import build_ket99_pku_selected_reading_teacher_delivery_remediation_assets as builder
from ulga.validators import validate_ket99_pku_selected_reading_teacher_delivery_remediation_assets as validator


def signed(value: dict) -> dict:
    result = copy.deepcopy(value)
    result["artifact_sha256"] = builder.digest(result)
    return result


def fixtures() -> tuple[dict, dict]:
    candidates, bindings = [], []
    for pku_id, lessons in builder.PLACEMENT_POLICY.items():
        for index, lesson_id in enumerate(lessons, 1):
            candidate_id = f"CAND:{pku_id}:{lesson_id}"
            candidates.append({
                "asset_candidate_id": candidate_id,
                "pku_id": pku_id,
                "lesson_id": lesson_id,
                "lesson_node_id": f"LESSON:READING:{lesson_id}",
                "skill": "READING",
                "level": "A1+",
                "source_transcript_id": "P008",
                "textbook_page": 12,
                "lesson_role": "regular",
                "evidence_anchor_ids": [f"ANCHOR:{pku_id}:{index}"],
                "source_lineage": {"m2_artifact_sha256": "a" * 64},
            })
            bindings.append({
                "asset_candidate_id": candidate_id,
                "pku_id": pku_id,
                "concept_id": builder.ASSET_DEFINITIONS[pku_id]["concept_id"],
                "knowledge_mode": "ERROR_REPAIR" if pku_id == "KET99-P008-PKU05" else "LEARNER_SKILL",
                "knowledge_type": "ERROR_PATTERN" if pku_id == "KET99-P008-PKU05" else "READING_STRATEGY",
                "teaching_roles": ["FOCUS", "PRACTICE", "REMEDIATION"],
                "lesson_id": lesson_id,
                "skill": "READING",
                "level": "A1+",
                "mapping_class": "CONTROLLED",
                "authority_ids": [],
                "teaching_need_id": f"TEACHING_NEED:{pku_id}",
                "material_profile": {"asset_count": 10, "roles": ["CHK", "CTX", "ERR", "EVD", "MOD", "PRD"], "material_digest": f"{index}" * 64, "media_evidence_required": False},
                "raw_incremental_value_score": 6 if pku_id == "KET99-P008-PKU05" else 5,
                "evaluation_reasons": ["NON_GRAMMAR_SKILL_VALUE"],
                "source_lineage": {"m2_artifact_sha256": "a" * 64},
                "within_pku_rank": index,
                "pku_binding_retention_cap": len(lessons),
                "learning_value_priority": "MEDIUM",
                "binding_decision": "RETAIN_FOR_ASSET_AUTHORING_EVALUATION",
                "teacher_delivery_activation_status": "NOT_ACTIVATED",
                "remediation_activation_status": "NOT_ACTIVATED",
                "human_content_review_required": True,
            })
    m4a = signed({
        "task_id": builder.m4a.TASK_ID,
        "schema_version": builder.m4a.SCHEMA_VERSION,
        "validation_status": builder.m4a.PASS_STATUS,
        "artifact_type": "metadata_only_teacher_delivery_remediation_asset_intake",
        "scope": "A1_A1_PLUS_ONLY",
        "source_identity": {},
        "mainline_consumer_contracts": {},
        "intake_policy": {"learning_value_evaluation_required": True},
        "lesson_asset_intake": [],
        "asset_candidates": candidates,
        "counts": {"asset_candidate_count": len(candidates)},
        "claim_boundaries": {},
        "errors": [],
        "stop_reason": "NONE",
        "next_short_step": builder.m4a.NEXT_SHORT_STEP,
    })
    m4b = signed({
        "task_id": builder.m4b.TASK_ID,
        "schema_version": builder.m4b.SCHEMA_VERSION,
        "validation_status": builder.m4b.PASS_STATUS,
        "artifact_type": "metadata_only_current_material_comparative_learning_value_evaluation",
        "scope": "A1_A1_PLUS_ONLY",
        "source_identity": {"m4a_intake_sha256": builder.digest(m4a)},
        "evaluation_policy": {"activation_allowed": False},
        "pku_evaluations": [],
        "binding_evaluations": bindings,
        "counts": {"source_pku_count": 4, "source_binding_count": len(bindings), "retained_pku_count": 4, "teacher_delivery_activated_count": 0, "remediation_activated_count": 0},
        "claim_boundaries": {"pedagogical_effectiveness_proven": False},
        "errors": [],
        "stop_reason": "NONE",
        "next_short_step": builder.m4b.NEXT_SHORT_STEP,
    })
    return m4a, m4b


def resign(value: dict) -> None:
    value.pop("artifact_sha256", None)
    value["artifact_sha256"] = builder.digest(value)


def test_builds_four_bundles_and_eleven_placements() -> None:
    m4a, m4b = fixtures()
    artifact = builder.build_artifact(m4a, m4b)
    assert artifact["counts"]["authored_asset_bundle_count"] == 4
    assert artifact["counts"]["authored_placement_count"] == 11
    assert artifact["counts"]["referenced_lesson_count"] == 3
    assert artifact["counts"]["teacher_delivery_bundle_count"] == 3
    assert artifact["counts"]["remediation_bundle_count"] == 3
    assert len(builder.assets_for_lesson(artifact, "KETR-RB-00-L01")) == 4
    assert len(builder.assets_for_lesson(artifact, "KETR-RB-01-L01")) == 3


def test_rejects_missing_selected_placement() -> None:
    m4a, m4b = fixtures()
    m4b["binding_evaluations"] = m4b["binding_evaluations"][:-1]
    resign(m4b)
    with pytest.raises(ValueError, match="selected_binding_set_mismatch"):
        builder.build_artifact(m4a, m4b)


def test_rejects_wrong_source_transcript() -> None:
    m4a, m4b = fixtures()
    m4a["asset_candidates"][0]["source_transcript_id"] = "P009"
    resign(m4a)
    m4b["source_identity"]["m4a_intake_sha256"] = builder.digest(m4a)
    resign(m4b)
    with pytest.raises(ValueError, match="selected_binding_source_boundary_invalid"):
        builder.build_artifact(m4a, m4b)


def test_rejects_non_authoring_decision() -> None:
    m4a, m4b = fixtures()
    m4b["binding_evaluations"][0]["binding_decision"] = "DEFER_SUPPORT_ONLY"
    resign(m4b)
    with pytest.raises(ValueError, match="selected_binding_not_authoring_eligible"):
        builder.build_artifact(m4a, m4b)


def test_validator_detects_tamper(tmp_path: Path) -> None:
    m4a, m4b = fixtures()
    artifact = builder.build_artifact(m4a, m4b)
    artifact_path, m4a_path, m4b_path = tmp_path / "artifact.json", tmp_path / "m4a.json", tmp_path / "m4b.json"
    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
    m4a_path.write_text(json.dumps(m4a), encoding="utf-8")
    m4b_path.write_text(json.dumps(m4b), encoding="utf-8")
    report = validator.validate_paths(artifact_path=artifact_path, m4a_path=m4a_path, m4b_path=m4b_path)
    assert report["error_count"] == 0
    artifact["asset_bundles"][0]["consumer_policy"]["learner_facing_allowed"] = True
    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
    report = validator.validate_paths(artifact_path=artifact_path, m4a_path=m4a_path, m4b_path=m4b_path)
    assert report["error_count"] > 0
