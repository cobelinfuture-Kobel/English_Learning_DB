from copy import deepcopy

from ulga.builders import build_a1_a1plus_synthetic_gap_inventory as inventory_builder


def test_inventory_reports_no_synthetic_pipeline_gaps_and_no_new_human_evidence():
    inventory = inventory_builder.build_inventory()

    assert inventory["validation_status"] == inventory_builder.PASS_STATUS
    assert inventory["scope"] == "A1_A1_PLUS_ONLY"
    assert inventory["decision_mode"] == "SYNTHETIC_GAP_INVENTORY_ONLY"
    assert inventory["unit_count"] == 24
    assert inventory["synthetic_pass_unit_count"] == 24
    assert inventory["synthetic_gap_unit_count"] == 0
    assert inventory["synthetic_gap_unit_ids"] == []
    assert inventory["direct_canonical_gate_unit_count"] == 23
    assert inventory["rowless_structural_gate_unit_count"] == 1
    assert inventory["rowless_structural_unit_ids"] == ["GRAMMAR_DEMONSTRATIVES_CONTRAST"]
    assert inventory["historical_human_pilot_sampled_unit_count"] == 3
    assert inventory["new_human_evidence_requested_unit_count"] == 0
    assert inventory["next_short_step"] == "R7-M104E16A_A1A1PlusCoverageRecheck_NoNewDesignDocs"
    assert inventory["claims"] == {
        "learner_evidence_created": False,
        "learner_mastery_claimed": False,
        "retention_confirmed": False,
        "persistent_learner_state_write": False,
        "production_runtime_event": False,
    }
    assert all(row["synthetic_pipeline_status"] == "PASS" for row in inventory["inventory_units"])
    assert all(row["failed_checks"] == [] for row in inventory["inventory_units"])
    assert all(row["new_human_evidence_requested"] is False for row in inventory["inventory_units"])


def test_inventory_classifies_failed_checks_without_creating_learner_claims(monkeypatch):
    pipeline = inventory_builder.build_report()
    tampered = deepcopy(pipeline)
    tampered["validation_status"] = "FAIL"
    tampered["units"][0]["checks"]["coverage_gate"] = False
    monkeypatch.setattr(inventory_builder, "build_report", lambda: tampered)

    inventory = inventory_builder.build_inventory()

    assert inventory["validation_status"] == inventory_builder.FAIL_STATUS
    assert inventory["synthetic_gap_unit_count"] == 1
    assert inventory["synthetic_gap_unit_ids"] == [tampered["units"][0]["grammar_unit_id"]]
    first = inventory["inventory_units"][0]
    assert first["synthetic_pipeline_status"] == "GAP"
    assert first["failed_checks"] == ["coverage_gate"]
    assert first["new_human_evidence_requested"] is False
    assert first["learner_mastery_claimed"] is False
    assert first["retention_confirmed"] is False


def test_failed_check_extraction_fails_closed_when_checks_are_missing():
    assert inventory_builder._failed_checks({}) == ["checks_missing"]
