import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
VALIDATOR = BASE_DIR / "ulga" / "validators" / "validate_grammar_node_egp_batch01_egp_raz_coordination_operator_decisions.py"
DATA_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_egp_raz_coordination_operator_decisions.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_egp_raz_coordination_operator_decisions_summary.json"
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


def test_coordination_operator_decision_validator_can_pass():
    result = run_command([sys.executable, str(VALIDATOR)])
    assert result.returncode == 0, result.stdout + result.stderr


def test_coordination_operator_decision_contract_and_safety_flags():
    data = load_json(DATA_PATH)
    summary = load_json(SUMMARY_PATH)
    assert data["task_id"] == "R7-M85A_Batch01EGPRAZCoordinationOperatorDecisionArtifact"
    assert summary["task_id"] == "R7-M85A_Batch01EGPRAZCoordinationOperatorDecisionArtifact"
    assert data["operator_decision_status"] == "APPROVED_R7_M84A_COORDINATION_PACKET"
    assert data["decision_scope"] == "EGP_RAZ_COORDINATION_DECISION_ONLY"
    for key in [
        "authority_write_allowed",
        "egp_evidence_refs_write_allowed",
        "raz_usage_attachment_write_allowed",
        "coverage_increase_allowed",
        "practicebank_generation_allowed",
        "learner_state_write_allowed",
        "runtime_change_allowed",
    ]:
        assert data[key] is False
        assert summary[key] is False


def test_records_cover_batch01_targets():
    data = load_json(DATA_PATH)
    records = data["records"]
    assert {record["grammar_id"] for record in records} == EXPECTED_IDS
    for record in records:
        assert record["operator_decision"] == "APPROVE_COORDINATION_RECOMMENDATION"
        assert record["approved_raz_usage_example_count"] > 0


def test_summary_counts_match_records():
    data = load_json(DATA_PATH)
    summary = load_json(SUMMARY_PATH)
    records = data["records"]
    assert summary["target_count"] == len(records)
    assert summary["egp_accept_as_authority_count"] == sum(1 for record in records if record["egp_decision"] == "ACCEPT_EGP_ROW_AS_AUTHORITY_EVIDENCE")
    assert summary["egp_accept_as_form_only_count"] == sum(1 for record in records if record["egp_decision"] == "ACCEPT_EGP_ROW_AS_FORM_EVIDENCE_ONLY")
    assert summary["egp_unresolved_request_refined_count"] == sum(1 for record in records if record["egp_decision"] == "KEEP_EGP_UNRESOLVED_REQUEST_REFINED_CANDIDATES")
    assert summary["approved_raz_usage_example_count"] == sum(record["approved_raz_usage_example_count"] for record in records)
    assert summary["next_short_step"] == "R7-M86A_Batch01AuthorityPatchPlanPolicyScan"
    assert summary["stop_reason"] == "NONE"


def test_can_statement_decision_is_form_only_with_raz_semantic_usage():
    data = load_json(DATA_PATH)
    record = next(item for item in data["records"] if item["grammar_id"] == "GRAMMAR_CAN_STATEMENT")
    assert record["egp_decision"] == "ACCEPT_EGP_ROW_AS_FORM_EVIDENCE_ONLY"
    assert record["egp_row_id"] == "1741163708329x931125497510935300"
    assert record["egp_evidence_role"] == "EGP_FORM_EVIDENCE"
    assert record["raz_decision"] == "KEEP_APPROVED_RAZ_SEMANTIC_USAGE_EVIDENCE"
    assert record["approved_raz_usage_example_count"] == 7
