import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "product/a1fs_v1_2_1/data/u06_reading360_pilot15_lexical_capacity_audit.json"


def load_report():
    return json.loads(REPORT.read_text(encoding="utf-8"))


def test_u06_pilot15_capacity_audit_scope_and_r2_acceptance():
    r = load_report()
    assert r["status"] == "AUDIT_PASS_PILOT15_R2_LEXICAL_AND_STYLE_ACCEPTED"
    assert r["scope"]["pilot_entry_count"] == 15
    assert r["scope"]["source_pilot_modified"] is True
    assert r["scope"]["reading360_full_materialized"] is False
    assert r["scope"]["writing360_modified"] is False
    assert r["scope"]["spoken360_modified"] is False
    assert r["scope"]["pattern360_modified"] is False
    assert r["scope"]["a2_a2plus_unlocked"] is False


def test_u06_pilot15_capacity_audit_r2_category_metrics():
    c = load_report()["category_results"]
    assert (c["noun_like"]["capacity"], c["noun_like"]["unique_used"]) == (202, 61)
    assert (c["object"]["capacity"], c["object"]["unique_used"]) == (25, 23)
    assert (c["place"]["capacity"], c["place"]["unique_used"]) == (29, 18)
    assert (c["person_role"]["capacity"], c["person_role"]["unique_used"]) == (17, 9)
    assert (c["adjective"]["capacity"], c["adjective"]["unique_used"]) == (25, 11)
    assert (c["action"]["capacity"], c["action"]["unique_used"]) == (60, 20)
    assert (c["number"]["capacity"], c["number"]["unique_used"]) == (3, 3)


def test_u06_pilot15_capacity_audit_r2_blockers_are_cleared():
    r = load_report()
    c = r["category_results"]
    assert c["object"]["unique_primary_object_count"] == 13
    assert c["object"]["primary_object_repeat_count"] == 0
    assert c["object"]["primary_objects_outside_direct_legal_reservoir"] == []
    assert c["object"]["max_episode_presence"] <= 2
    assert c["person_role"]["top1"]["surface"] == "friend"
    assert c["person_role"]["top1"]["occurrences"] == 6
    assert c["person_role"]["top1"]["occurrence_share"] == 0.333
    assert r["blocking_findings"] == []


def test_u06_pilot15_capacity_audit_r2_style_and_unlock():
    r = load_report()
    s = r["style_results"]
    assert s["ready_occurrence_count"] == 0
    assert s["ready_closure_count"] == 0
    assert s["unique_final_sentence_count"] == 15
    assert s["exact_final_sentence_duplicate_count"] == 0
    assert r["human_review"]["status"] == "PASS"
    assert r["human_review"]["review_round"] == "R2"
    assert r["conclusion"]["pilot15_lexical_balance_accepted"] is True
    assert r["conclusion"]["pilot15_human_review_r2_accepted"] is True
    assert r["conclusion"]["full360_expansion_allowed"] is True
