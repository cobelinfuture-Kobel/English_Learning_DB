from __future__ import annotations

import copy
import json
from pathlib import Path

from ulga.builders import build_ket99_pku_controlled_lesson_candidate_mapping as builder
from ulga.validators import validate_ket99_pku_controlled_lesson_candidate_mapping as validator


def bridge() -> dict:
    fields = ["pku_id", "operator_decision", "confirmed_disposition", "authority_ids", "teaching_need_id", "production_admission_allowed", "production_lesson_mapping_allowed"]
    rows = [
        ["KET99-P006-PKU01", "CONFIRM_EXACT_AUTHORITY_JOIN", "PILOT_ADMITTED", ["GRAMMAR_BE"], None, False, False],
        ["KET99-P008-PKU01", "CONFIRM_TEACHING_NEED_BRIDGE", "PILOT_ADMITTED", [], "TEACHING_NEED:READING.STRATEGY", False, False],
        ["KET99-P026-PKU01", "CONFIRM_TEACHING_NEED_BRIDGE", "PILOT_ADMITTED", [], "TEACHING_NEED:WRITING.ADJECTIVES", False, False],
        ["KET99-P005-PKU01", "CONFIRM_TEACHING_NEED_BRIDGE", "PILOT_ADMITTED", [], "TEACHING_NEED:LISTENING.NUMBERS", False, False],
        ["KET99-P005-PKU07", "CONFIRM_REJECT_EXAM_PROCEDURE_ONLY", "REJECTED_EXAM_PROCEDURE_ONLY", [], None, False, False],
    ]
    return {
        "task_id": builder.M2_TASK, "validation_status": builder.M2_STATUS, "stop_reason": "NONE",
        "authority_contract": {"production_lesson_mapping_allowed": False, "hard_lesson_selection_allowed": False, "a2_mapping_allowed": False},
        "operator_decision_field_order": fields, "operator_decisions": rows,
    }


def m1_rows() -> list[dict[str, str]]:
    return [
        {"pku_id": "KET99-P006-PKU01", "source_transcript_id": "P006", "cefr_decision": "ADMITTED_A1", "skill_scope": "SPEAKING|WRITING"},
        {"pku_id": "KET99-P008-PKU01", "source_transcript_id": "P008", "cefr_decision": "ADMITTED_A1_PLUS", "skill_scope": "READING"},
        {"pku_id": "KET99-P026-PKU01", "source_transcript_id": "P026", "cefr_decision": "ADMITTED_A1", "skill_scope": "WRITING"},
        {"pku_id": "KET99-P005-PKU01", "source_transcript_id": "P005", "cefr_decision": "ADMITTED_A1", "skill_scope": "LISTENING"},
        {"pku_id": "KET99-P005-PKU07", "source_transcript_id": "P005", "cefr_decision": "NOT_ADMITTED", "skill_scope": "LISTENING"},
    ]


def consumer() -> dict:
    lessons = [
        {"lesson_id": "S-A1-BE", "skill": "SPEAKING", "level": "A1", "requirement_node_ids": ["REF:SPEAKING:GRAMMAR_BE"]},
        {"lesson_id": "W-A1-BE", "skill": "WRITING", "level": "A1", "requirement_node_ids": ["REF:WRITING:GRAMMAR_BE"]},
        {"lesson_id": "R-A1P-DETAIL", "skill": "READING", "level": "A1+", "requirement_node_ids": []},
        {"lesson_id": "R-A1P-UNRELATED", "skill": "READING", "level": "A1+", "requirement_node_ids": []},
        {"lesson_id": "W-A1-ADJ", "skill": "WRITING", "level": "A1", "requirement_node_ids": []},
        {"lesson_id": "L-A1-NUM", "skill": "LISTENING", "level": "A1", "requirement_node_ids": []},
        {"lesson_id": "R-A2", "skill": "READING", "level": "A2", "requirement_node_ids": []},
    ]
    return {
        "task_id": builder.M2_CONSUMER_TASK, "schema_version": builder.M2_CONSUMER_SCHEMA,
        "validation_status": builder.M2_CONSUMER_STATUS, "lesson_catalog": lessons,
        "access_contract": {"a2_payload_query_allowed": False},
    }


def r3g(c: dict) -> dict:
    rows = [
        {"lesson_id": "R-A1P-DETAIL", "instructional_references": [{"transcript_id": "P008", "mapping_basis": ["CONTROLLED_HUMAN_EVIDENCE_RESOLUTION"]}]},
        {"lesson_id": "R-A1P-UNRELATED", "instructional_references": [{"transcript_id": "P009", "mapping_basis": ["EXACT_NORMALIZED_SEMANTIC_ATOM"]}]},
        {"lesson_id": "W-A1-ADJ", "instructional_references": [{"transcript_id": "P026", "mapping_basis": ["CONTROLLED_TOPIC_DOMAIN_AND_SKILL"]}]},
        {"lesson_id": "L-A1-NUM", "instructional_references": [{"transcript_id": "P005", "mapping_basis": ["TOKEN_ONLY_MATCH"]}]},
        {"lesson_id": "R-A2", "instructional_references": [{"transcript_id": "P008", "mapping_basis": ["CONTROLLED_HUMAN_EVIDENCE_RESOLUTION"]}]},
    ]
    return {
        "task_id": builder.R3G_TASK, "schema_version": builder.R3G_SCHEMA,
        "validation_status": builder.R3G_STATUS, "stop_reason": "NONE",
        "source_identity": {"m2_consumer_sha256": builder.digest(c)},
        "precision_summary": {"token_only_mapping_allowed": False},
        "lesson_instructional_references": rows,
    }


def built() -> tuple[dict, dict, dict, dict]:
    b, c = bridge(), consumer(); r = r3g(c)
    return builder.build_artifact(b, m1_rows(), c, r), b, c, r


def mappings(artifact: dict) -> dict[str, dict]:
    return {row["pku_id"]: row for row in artifact["candidate_mappings"]}


def test_controlled_candidate_mapping_passes_without_broadcast_or_a2() -> None:
    artifact, _, _, _ = built(); rows = mappings(artifact)
    assert rows["KET99-P006-PKU01"]["candidate_lesson_ids"] == ["S-A1-BE", "W-A1-BE"]
    assert rows["KET99-P008-PKU01"]["candidate_lesson_ids"] == ["R-A1P-DETAIL"]
    assert rows["KET99-P026-PKU01"]["candidate_lesson_ids"] == ["W-A1-ADJ"]
    assert rows["KET99-P005-PKU01"]["candidate_lesson_ids"] == []
    assert rows["KET99-P005-PKU07"]["candidate_status"] == "NOT_ELIGIBLE"
    assert "R-A2" not in rows["KET99-P008-PKU01"]["candidate_lesson_ids"]
    assert artifact["counts"]["candidate_mapped_pku_count"] == 3
    assert artifact["counts"]["unresolved_pku_count"] == 1
    assert artifact["counts"]["production_lesson_mapping_count"] == 0


def test_skill_level_only_lesson_is_not_broadcast_candidate() -> None:
    artifact, _, _, _ = built(); rows = mappings(artifact)
    assert "R-A1P-UNRELATED" not in rows["KET99-P008-PKU01"]["candidate_lesson_ids"]
    assert artifact["mapping_policy"]["skill_level_only_mapping_allowed"] is False


def test_token_only_reference_does_not_create_candidate() -> None:
    artifact, _, _, _ = built(); row = mappings(artifact)["KET99-P005-PKU01"]
    assert row["candidate_status"] == "NO_CONTROLLED_CANDIDATE_REQUIRES_EVIDENCE"
    assert row["candidate_count"] == 0


def test_build_is_deterministic() -> None:
    first, b, c, r = built()
    assert first == builder.build_artifact(b, m1_rows(), c, r)


def test_validator_rejects_candidate_tamper(tmp_path: Path) -> None:
    artifact, b, c, r = built(); tampered = copy.deepcopy(artifact)
    mappings(tampered)["KET99-P008-PKU01"]["candidate_lesson_ids"].append("R-A1P-UNRELATED")
    artifact_path = tmp_path / "artifact.json"; bridge_path = tmp_path / "bridge.json"
    consumer_path = tmp_path / "consumer.json"; r3g_path = tmp_path / "r3g.json"; csv_path = tmp_path / "m1.csv"
    for path, value in ((artifact_path, tampered), (bridge_path, b), (consumer_path, c), (r3g_path, r)):
        path.write_text(json.dumps(value))
    with csv_path.open("w", newline="") as handle:
        import csv
        writer = csv.DictWriter(handle, fieldnames=["pku_id", "source_transcript_id", "cefr_decision", "skill_scope"])
        writer.writeheader(); writer.writerows(m1_rows())
    report = validator.validate_paths(artifact_path=artifact_path, m1_csv=csv_path, bridge=bridge_path, consumer=consumer_path, r3g=r3g_path)
    assert report["validation_status"] == validator.FAIL_STATUS
    assert "artifact_deterministic_rebuild_mismatch" in report["errors"]


def test_source_binding_tamper_fails_closed() -> None:
    b, c = bridge(), consumer(); r = r3g(c); r["source_identity"]["m2_consumer_sha256"] = "0" * 64
    try:
        builder.build_artifact(b, m1_rows(), c, r)
    except ValueError as exc:
        assert str(exc) == "r3g_m2_binding_invalid"
    else:
        raise AssertionError("tampered R3G binding was accepted")
