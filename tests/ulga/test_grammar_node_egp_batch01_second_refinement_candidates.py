import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
BUILDER = BASE_DIR / "ulga" / "builders" / "build_grammar_node_egp_batch01_second_refinement_candidates.py"
VALIDATOR = BASE_DIR / "ulga" / "validators" / "validate_grammar_node_egp_batch01_second_refinement_candidates.py"
DATA_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_second_refinement_candidates.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_second_refinement_candidates_summary.json"


def run_command(args):
    return subprocess.run(args, cwd=BASE_DIR, capture_output=True, text=True)


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_builder_can_run():
    result = run_command([sys.executable, str(BUILDER)])
    assert result.returncode == 0, result.stdout + result.stderr
    assert DATA_PATH.exists()
    assert SUMMARY_PATH.exists()


def test_validator_can_pass():
    result = run_command([sys.executable, str(VALIDATOR)])
    assert result.returncode == 0, result.stdout + result.stderr


def test_contract_and_safety_flags():
    data = load_json(DATA_PATH)
    summary = load_json(SUMMARY_PATH)
    assert data["task_id"] == "R7-M69_Batch01SecondRefinementCandidateAuditBuilderImplementation"
    assert summary["task_id"] == "R7-M69_Batch01SecondRefinementCandidateAuditBuilderImplementation"
    scope = data["scope_constraints"]
    assert scope["no_runtime_implementation"] is True
    assert scope["no_practicebank_generation"] is True
    assert scope["no_learner_state_write"] is True
    assert scope["no_auto_egp_row_selection"] is True
    assert scope["no_authority_write"] is True
    assert scope["no_egp_evidence_refs_write"] is True
    assert scope["no_coverage_increase"] is True


def test_records_include_expected_actions():
    data = load_json(DATA_PATH)
    records = {record["grammar_id"]: record for record in data["records"]}
    assert records["GRAMMAR_ARTICLES_BASIC"]["refinement_action"] == "SECOND_PASS_REFINE"
    assert records["GRAMMAR_BASIC_PREPOSITIONS_PLACE"]["refinement_action"] == "SECOND_PASS_REFINE"
    assert records["GRAMMAR_BE_VERB_BASIC"]["refinement_action"] == "SECOND_PASS_REFINE"
    assert records["GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC"]["refinement_action"] == "SECOND_PASS_REFINE"
    assert records["GRAMMAR_CAN_STATEMENT"]["refinement_action"] == "SOURCE_ROW_AUDIT"
    assert records["GRAMMAR_CAN_STATEMENT"]["source_row_audit"]["candidate_to_audit"] == "1741163708329x931125497510935300"


def test_summary_counts_match_records():
    data = load_json(DATA_PATH)
    summary = load_json(SUMMARY_PATH)
    records = data["records"]
    action_counts = {}
    total_candidates = 0
    audit_count = 0
    missing_targets = 0
    for record in records:
        action = record["refinement_action"]
        action_counts[action] = action_counts.get(action, 0) + 1
        if action == "SECOND_PASS_REFINE":
            candidates = record.get("second_refinement_candidates", [])
            total_candidates += len(candidates)
            if not candidates:
                missing_targets += 1
        if action == "SOURCE_ROW_AUDIT":
            audit_count += 1
    assert summary["record_count"] == len(records)
    assert summary["action_counts"] == action_counts
    assert summary["total_second_refinement_candidate_count"] == total_candidates
    assert summary["source_row_audit_count"] == audit_count
    assert summary["second_refine_targets_without_candidates"] == missing_targets
    assert summary["operator_review_required"] is True
    assert summary["next_short_step"] == "R7-M70_Batch01SecondRefinementCandidateAuditReadback"
    assert summary["stop_reason"] == "NONE"
