from __future__ import annotations

import copy
import json
from pathlib import Path

from ulga.validators import validate_ket99_pku_operator_confirmation_and_teaching_need_bridge as validator

ROOT = Path(__file__).resolve().parents[2]
PILOT = ROOT / "ulga/reports/ket99_pku_pilot/ket99_pedagogical_knowledge_units.pilot.json"
BRIDGE = ROOT / "ulga/reports/ket99_pku_pilot/ket99_pku_operator_confirmation_teaching_need_bridge.v1.json"


def load() -> tuple[dict, dict]:
    return json.loads(PILOT.read_text()), json.loads(BRIDGE.read_text())


def row(bundle: dict, field_key: str, row_key: str, identity_key: str, identity: str) -> list:
    fields = bundle[field_key]
    index = fields.index(identity_key)
    return next(item for item in bundle[row_key] if item[index] == identity)


def set_field(bundle: dict, field_key: str, target: list, name: str, value: object) -> None:
    target[bundle[field_key].index(name)] = value


def test_committed_bridge_passes() -> None:
    pilot, bridge = load()
    report = validator.validate_bridge(bridge, pilot, pilot_blob_sha=validator._git_blob_sha(PILOT))
    assert report["validation_status"] == validator.PASS_STATUS, report
    assert (report["source_pku_count"], report["operator_decision_count"]) == (35, 35)
    assert (report["teaching_need_identity_count"], report["exact_authority_join_count"]) == (22, 10)
    assert report["exam_only_reject_count"] == 3
    assert report["production_lesson_mapping_count"] == 0
    assert report["a2_unlocked"] is False


def test_rejects_unbound_teaching_need_identity() -> None:
    pilot, bridge = load(); tampered = copy.deepcopy(bridge)
    target = row(tampered, "teaching_need_field_order", "teaching_need_registry", "source_pku_id", "KET99-P005-PKU01")
    set_field(tampered, "teaching_need_field_order", target, "teaching_need_id", "TEACHING_NEED:UNBOUND")
    report = validator.validate_bridge(tampered, pilot)
    assert report["validation_status"].startswith("FAIL_")
    assert "teaching_need_identity_invalid:KET99-P005-PKU01" in report["errors"]


def test_rejects_production_mapping_claim() -> None:
    pilot, bridge = load(); tampered = copy.deepcopy(bridge)
    tampered["authority_contract"]["production_lesson_mapping_allowed"] = True
    tampered["counts"]["production_lesson_mapping_count"] = 1
    report = validator.validate_bridge(tampered, pilot)
    assert "authority_boundary_true:production_lesson_mapping_allowed" in report["errors"]
    assert "committed_count_invalid:production_lesson_mapping_count" in report["errors"]


def test_rejects_exam_procedure_admission() -> None:
    pilot, bridge = load(); tampered = copy.deepcopy(bridge)
    target = row(tampered, "operator_decision_field_order", "operator_decisions", "pku_id", "KET99-P005-PKU07")
    set_field(tampered, "operator_decision_field_order", target, "operator_decision", "CONFIRM_TEACHING_NEED_BRIDGE")
    set_field(tampered, "operator_decision_field_order", target, "confirmed_disposition", "PILOT_ADMITTED")
    report = validator.validate_bridge(tampered, pilot)
    assert "exam_decision_invalid:KET99-P005-PKU07" in report["errors"]
    assert "exam_disposition_invalid:KET99-P005-PKU07" in report["errors"]


def test_rejects_a2_unlock_and_hard_graph_mutation() -> None:
    pilot, bridge = load(); tampered = copy.deepcopy(bridge)
    tampered["scope"]["a2_status"] = "UNLOCKED"
    tampered["authority_contract"]["hard_graph_mutation_allowed"] = True
    report = validator.validate_bridge(tampered, pilot)
    assert "a2_not_locked" in report["errors"]
    assert "authority_boundary_true:hard_graph_mutation_allowed" in report["errors"]
