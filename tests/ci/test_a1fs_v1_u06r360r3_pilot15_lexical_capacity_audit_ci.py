import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "product/a1fs_v1_2_1/data/u06_reading360_pilot15_lexical_capacity_audit.json"


def load_report():
    return json.loads(REPORT.read_text(encoding="utf-8"))


def test_u06_pilot15_capacity_audit_scope_is_read_only():
    r = load_report()
    assert r["status"] == "AUDIT_FAIL_PILOT15_LEXICAL_REBALANCE_REQUIRED"
    assert r["scope"]["pilot_entry_count"] == 15
    assert r["scope"]["source_pilot_modified"] is False
    assert r["scope"]["reading360_full_materialized"] is False
    assert r["scope"]["writing360_modified"] is False
    assert r["scope"]["spoken360_modified"] is False
    assert r["scope"]["pattern360_modified"] is False
    assert r["scope"]["a2_a2plus_unlocked"] is False


def test_u06_pilot15_capacity_audit_exact_category_metrics():
    c = load_report()["category_results"]
    assert (c["noun_like"]["capacity"], c["noun_like"]["unique_used"]) == (202, 51)
    assert (c["object"]["capacity"], c["object"]["unique_used"]) == (25, 20)
    assert (c["place"]["capacity"], c["place"]["unique_used"]) == (29, 17)
    assert (c["person_role"]["capacity"], c["person_role"]["unique_used"]) == (17, 5)
    assert (c["adjective"]["capacity"], c["adjective"]["unique_used"]) == (25, 6)
    assert (c["action"]["capacity"], c["action"]["unique_used"]) == (60, 18)
    assert (c["number"]["capacity"], c["number"]["unique_used"]) == (3, 3)


def test_u06_pilot15_capacity_audit_identifies_actual_blockers():
    r = load_report()
    c = r["category_results"]
    assert c["object"]["unique_primary_object_count"] == 14
    assert c["object"]["primary_object_repeat_count"] == 0
    assert c["object"]["primary_objects_outside_direct_legal_reservoir"] == ["bike", "toy drone"]
    assert c["person_role"]["top1"]["surface"] == "friend"
    assert c["person_role"]["top1"]["occurrences"] == 11
    assert c["person_role"]["top1"]["occurrence_share"] == 0.647
    assert c["person_role"]["top3_occurrence_share"] == 0.882
    assert set(r["blocking_findings"]) == {
        "PERSON_ROLE_FRIEND_DOMINANCE",
        "PRIMARY_OBJECT_OUTSIDE_DIRECT_LEGAL_RESERVOIR",
    }


def test_u06_pilot15_capacity_audit_preserves_passes_and_blocks_full360():
    r = load_report()
    c = r["category_results"]
    assert c["object"]["utilization_ratio"] == 0.8
    assert c["action"]["finding"] == "PASS_NOT_CONCENTRATED_FOR_15_ENTRY_PILOT"
    assert c["number"]["finding"] == "PASS_CONTROLLED"
    assert r["conclusion"]["pilot15_lexical_balance_accepted"] is False
    assert r["conclusion"]["full360_expansion_allowed"] is False
