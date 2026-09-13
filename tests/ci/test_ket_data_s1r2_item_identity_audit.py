from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path

TASK_ID = "KET_Data_S1R2_M01_ExistingIdentityAuditFreezeAndRegionContractRepair"
SCHEMA = "ket.data.s1r2.item_identity_state.m01.v1"
CONTRACT_SHA256 = "90cff1c631671b567d300a72d802cf04161b8e50bbb50b9d285c6fcbfa7fdc46"
VALID_STATUSES = {"CONFIRMED_CANONICAL_ITEM", "DEPRECATED_NON_ITEM", "UNRESOLVED"}
ITEM_RE = re.compile(r"^KET_ITEM_(\d{6})$")


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load() -> dict:
    p = _root() / "data" / "ket" / "ket_s1r2_item_identity_state.json"
    return json.loads(p.read_text(encoding="utf-8"))


def _num(item_id: str) -> int:
    m = ITEM_RE.fullmatch(item_id)
    assert m, item_id
    return int(m.group(1))


def test_s1r2_m01_existing_identity_audit_freeze_and_region_contract_repair():
    p = _load()
    assert p["schema"] == SCHEMA
    assert p["task_id"] == TASK_ID
    assert p["contract_source"] == "KET_S1_revised.txt"
    assert p["contract_sha256"] == CONTRACT_SHA256

    scope = p["scope"]
    assert scope["milestone"] == "S1R2-M01"
    assert scope["clauses"] == ["S1-C01", "S1-C02", "S1-C03", "S1-C04", "S1-C05", "S1-C06"]
    assert scope["new_item_materialization_allowed"] is False
    assert scope["canonical_item_completeness_evaluated"] is False
    assert scope["s2_projection_allowed"] is False

    pred = p["predecessor"]
    assert pred["source_count"] == 34
    assert pred["pdf_source_count"] == 33
    assert pred["page_count"] == 1398
    assert pred["image_identity_count"] == 1572
    assert pred["legacy_question_region_count"] == 629
    assert pred["legacy_item_id_count"] == 629

    region = p["region_contract_repair"]
    assert region["legacy_region_name"] == "QUESTION"
    assert region["normalized_region_name"] == "QUESTION_CANDIDATE"
    assert region["legacy_question_region_implies_canonical_item"] is False
    assert region["canonical_item_requires_admission"] is True
    assert region["historical_segmentation_payload_rewritten"] is False
    assert region["normalization_mode"] == "NON_DESTRUCTIVE_OVERLAY"

    freeze = p["identity_freeze"]
    assert freeze["existing_item_ids_immutable"] is True
    assert freeze["existing_item_ids_must_not_be_rebound"] is True
    assert freeze["existing_item_ids_must_not_be_reused"] is True
    rng = freeze["existing_item_id_range"]
    assert (_num(rng["first"]), _num(rng["last"]), rng["count"]) == (1, 629, 629)
    assert freeze["next_available_new_item_id"] == "KET_ITEM_000630"

    audit = p["legacy_identity_audit"]
    assert set(audit["status_enum"]) == VALID_STATUSES
    assert audit["default_status"] == "UNRESOLVED"
    assert audit["explicit_overrides"] == []
    assert audit["status_counts"] == {
        "CONFIRMED_CANONICAL_ITEM": 0,
        "DEPRECATED_NON_ITEM": 0,
        "UNRESOLVED": 629,
    }
    ranges = audit["status_ranges"]
    assert len(ranges) == 1
    rr = ranges[0]
    assert (_num(rr["first"]), _num(rr["last"]), rr["count"], rr["status"]) == (1, 629, 629, "UNRESOLVED")
    assert rr["count"] == _num(rr["last"]) - _num(rr["first"]) + 1

    gates = p["gates"]
    assert gates["legacy_item_range_fully_covered_by_status"] is True
    assert gates["legacy_id_reuse_forbidden"] is True
    assert gates["question_region_normalized_to_candidate"] is True
    assert gates["canonical_item_admission_required"] is True
    assert gates["new_item_ids_created"] == 0
    assert gates["canonical_item_completeness"] == "NOT_EVALUATED_M01"
    assert gates["s2_item_projection_readiness"] is False
    assert p["next_milestone"] == "KET_Data_S1R2_M02_CanonicalExamItemAdmissionAndCompleteness"
