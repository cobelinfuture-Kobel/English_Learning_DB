import csv
import json
from copy import deepcopy
from functools import lru_cache

from ulga.builders import (
    build_a1fs_v1_u02fp02_unit02_current_q09_q10_final_package_export as builder,
)


@lru_cache(maxsize=1)
def _payload():
    return builder.build_export_payload()


def test_u02fp02_exports_current_q09_q10_authority_counts_and_proofs():
    payload = _payload()
    q9 = payload["q9_task_angle_question_type"]
    q10 = payload["q10_questionbank_capacity_runtime"]

    assert payload["status"] == builder.PASS_STATUS
    assert q9["post_materialization_summary"]["task_family_count"] == 10
    assert q9["post_materialization_summary"]["global_640_distinct_runtime_question_proof"] is True

    assert q10["inventory_summary"]["unit02_approved_item_count"] == 1730
    assert q10["inventory_summary"]["cumulative_catalog_item_count"] == 2204
    assert q10["runtime_form_contract"]["form_count"] == 16
    assert q10["runtime_form_contract"]["activities_per_form"] == 40
    assert q10["runtime_form_contract"]["runtime_occurrence_count"] == 640
    assert q10["global_distinctness_proof"]["distinct_selected_item_ids"] == 640
    assert q10["global_distinctness_proof"]["distinct_visible_signatures"] == 640
    assert q10["global_distinctness_proof"]["distinct_effective_signatures"] == 640
    assert q10["global_distinctness_proof"]["distinct_semantic_signatures"] == 640
    assert q10["global_distinctness_proof"]["exact_duplicate_groups"] == 0
    assert q10["global_distinctness_proof"]["semantic_duplicate_groups"] == 0
    assert q10["global_distinctness_proof"]["prior_activity_direct_answer_leaks"] == 0
    assert q10["global_distinctness_proof"]["global_640_distinct_runtime_question_proof"] is True
    assert q10["sentence_asset_integration"]["bound_runtime_occurrence_count"] == 128
    assert q10["progression_support_contract"]["transfer_stage_runtime_occurrences"] == 160
    assert q10["progression_support_contract"]["transfer_demand_proven"] is True
    assert q10["progression_support_contract"]["independent_transfer_topology_distinct"] is True

    boundaries = payload["claim_boundaries"]
    assert boundaries["q01_q08_reexported"] is False
    assert boundaries["q01_q08_mutated"] is False
    assert boundaries["q09_q10_read_only_export"] is True
    assert boundaries["questionbank_or_runtime_authority_created"] is False
    assert boundaries["a2_unlocked"] is False


def test_u02fp02_writes_exact_replacement_file_set(tmp_path, monkeypatch):
    baseline = _payload()
    monkeypatch.setattr(builder, "build_export_payload", lambda: deepcopy(baseline))
    paths = builder.write_exports(tmp_path)
    expected = {
        "Q09_Task_Angle_Question_Type.json",
        "Q09_Task_Families.csv",
        "Q10_QuestionBank_Runtime_Summary.json",
        "Q10_QuestionBank_Runtime_Summary.csv",
        "Q10_QuestionBank_Inventory.json",
        "Q10_QuestionBank_Inventory.csv",
        "Q10_Runtime_Form_Plan.json",
        "Q10_Runtime_Form_Plan.csv",
        "Unit02_Q09_Q10_Current_Manifest.json",
    }
    assert set(paths) == expected

    q9 = json.loads((tmp_path / "Q09_Task_Angle_Question_Type.json").read_text(encoding="utf-8"))
    inventory = json.loads((tmp_path / "Q10_QuestionBank_Inventory.json").read_text(encoding="utf-8"))
    runtime = json.loads((tmp_path / "Q10_Runtime_Form_Plan.json").read_text(encoding="utf-8"))
    summary = json.loads((tmp_path / "Q10_QuestionBank_Runtime_Summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((tmp_path / "Unit02_Q09_Q10_Current_Manifest.json").read_text(encoding="utf-8"))

    assert q9["post_materialization_summary"]["task_family_count"] == 10
    assert inventory["item_count"] == 1730
    assert inventory["distinct_item_id_count"] == 1730
    assert len(inventory["items"]) == 1730
    assert runtime["runtime_occurrence_count"] == 640
    assert len(runtime["runtime_occurrences"]) == 640
    assert runtime["global_640_distinct_runtime_question_proof"] is True
    assert summary["inventory_summary"]["unit02_approved_item_count"] == 1730
    assert summary["source_authority"]["r4r2_human_acceptance"]["status"] == "PASS"
    assert manifest["replacement_scope"] == "REPLACE_OLD_UNIT02_Q09_Q10_FILES_ONLY"
    assert manifest["q01_q08_preserved_from_existing_final_package"] is True
    assert manifest["source_authority"]["r4r2_human_acceptance"]["evidence_zip_sha256"] == builder.R4R2_EVIDENCE_ZIP_SHA256

    with (tmp_path / "Q09_Task_Families.csv").open(encoding="utf-8-sig", newline="") as handle:
        assert len(list(csv.DictReader(handle))) == 10
    with (tmp_path / "Q10_QuestionBank_Inventory.csv").open(encoding="utf-8-sig", newline="") as handle:
        assert len(list(csv.DictReader(handle))) == 1730
    with (tmp_path / "Q10_Runtime_Form_Plan.csv").open(encoding="utf-8-sig", newline="") as handle:
        assert len(list(csv.DictReader(handle))) == 640


def test_u02fp02_stale_pr539_counts_are_not_current_package_truth():
    q10 = _payload()["q10_questionbank_capacity_runtime"]
    assert q10["inventory_summary"]["unit02_approved_item_count"] != 994
    assert q10["inventory_summary"]["cumulative_catalog_item_count"] != 1468
    assert q10["inventory_summary"]["unit02_approved_item_count"] == 1730
    assert q10["inventory_summary"]["cumulative_catalog_item_count"] == 2204
