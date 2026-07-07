import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
BUILDER = BASE_DIR / "ulga" / "builders" / "build_grammar_node_egp_batch01_authority_patch_plan.py"
VALIDATOR = BASE_DIR / "ulga" / "validators" / "validate_grammar_node_egp_batch01_authority_patch_plan.py"
DATA_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_authority_patch_plan.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_authority_patch_plan_summary.json"
EXPECTED_IDS = {
    "GRAMMAR_ARTICLES_BASIC",
    "GRAMMAR_BASIC_PREPOSITIONS_PLACE",
    "GRAMMAR_BE_VERB_BASIC",
    "GRAMMAR_CAN_STATEMENT",
    "GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC",
}


def run_command(args):
    return subprocess.run(args, cwd=BASE_DIR, capture_output=True, text=True)


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_authority_patch_plan_builder_can_run():
    result = run_command([sys.executable, str(BUILDER)])
    assert result.returncode == 0, result.stdout + result.stderr
    assert DATA_PATH.exists()
    assert SUMMARY_PATH.exists()


def test_authority_patch_plan_validator_can_pass():
    result = run_command([sys.executable, str(VALIDATOR)])
    assert result.returncode == 0, result.stdout + result.stderr


def test_authority_patch_plan_contract_and_safety_flags():
    data = load_json(DATA_PATH)
    summary = load_json(SUMMARY_PATH)
    assert data["task_id"] == "R7-M87A_Batch01AuthorityPatchPlanArtifactBuilder"
    assert summary["task_id"] == "R7-M87A_Batch01AuthorityPatchPlanArtifactBuilder"
    assert data["plan_scope"] == "PATCH_PLAN_ONLY_NO_AUTHORITY_WRITE"
    scope = data["scope_constraints"]
    assert scope["no_canonical_grammar_write"] is True
    assert scope["no_egp_evidence_refs_write"] is True
    assert scope["no_raz_usage_attachment_write"] is True
    assert scope["no_coverage_increase"] is True
    assert scope["no_practicebank_generation"] is True
    assert scope["no_learner_state_write"] is True
    assert scope["no_runtime_change"] is True
    assert scope["operator_review_required"] is True
    assert summary["write_allowed"] is False
    assert summary["canonical_grammar_write_allowed"] is False
    assert summary["egp_evidence_refs_write_allowed"] is False
    assert summary["raz_usage_attachment_write_allowed"] is False
    assert summary["coverage_increase_allowed"] is False


def test_patch_plan_records_cover_batch01_targets():
    data = load_json(DATA_PATH)
    records = data["records"]
    assert {record["grammar_id"] for record in records} == EXPECTED_IDS
    for record in records:
        assert record["write_allowed"] is False
        assert record["operator_review_required"] is True
        if record["planned_action"] == "PLAN_REFINED_EGP_CANDIDATE_REQUEST":
            assert record["selected_egp_row_id"] is None
            assert record["selected_egp_evidence_role"] is None
            assert record["write_target_path"] is None
        else:
            assert record["selected_egp_row_id"]
            assert record["selected_egp_evidence_role"]
            assert record["write_target_path"] == "ulga/grammar/grammar_nodes.json"


def test_summary_counts_match_records():
    data = load_json(DATA_PATH)
    summary = load_json(SUMMARY_PATH)
    records = data["records"]
    action_counts = {}
    for record in records:
        action_counts[record["planned_action"]] = action_counts.get(record["planned_action"], 0) + 1
    assert summary["target_count"] == len(records)
    assert summary["action_counts"] == dict(sorted(action_counts.items()))
    assert summary["planned_authority_patch_count"] == action_counts.get("PLAN_AUTHORITY_EGP_EVIDENCE_PATCH", 0)
    assert summary["planned_form_only_patch_count"] == action_counts.get("PLAN_FORM_ONLY_EGP_EVIDENCE_PATCH", 0)
    assert summary["planned_refined_candidate_request_count"] == action_counts.get("PLAN_REFINED_EGP_CANDIDATE_REQUEST", 0)
    assert summary["next_short_step"] == "R7-M88A_Batch01AuthorityPatchPlanReadback"
    assert summary["stop_reason"] == "NONE"


def test_can_statement_is_form_only_plan():
    data = load_json(DATA_PATH)
    record = next(item for item in data["records"] if item["grammar_id"] == "GRAMMAR_CAN_STATEMENT")
    assert record["planned_action"] == "PLAN_FORM_ONLY_EGP_EVIDENCE_PATCH"
    assert record["selected_egp_row_id"] == "1741163708329x931125497510935300"
    assert record["selected_egp_evidence_role"] == "EGP_FORM_EVIDENCE"
    assert record["write_allowed"] is False
