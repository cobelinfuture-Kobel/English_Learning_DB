import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
BUILDER = BASE_DIR / "ulga" / "builders" / "build_grammar_node_egp_batch01_second_refinement_plan.py"
VALIDATOR = BASE_DIR / "ulga" / "validators" / "validate_grammar_node_egp_batch01_second_refinement_plan.py"
PLAN_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_second_refinement_plan.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_second_refinement_plan_summary.json"


def run_command(args):
    return subprocess.run(args, cwd=BASE_DIR, capture_output=True, text=True)


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_builder_can_run():
    result = run_command([sys.executable, str(BUILDER)])
    assert result.returncode == 0, result.stdout + result.stderr
    assert PLAN_PATH.exists()
    assert SUMMARY_PATH.exists()


def test_validator_can_pass():
    result = run_command([sys.executable, str(VALIDATOR)])
    assert result.returncode == 0, result.stdout + result.stderr


def test_plan_contract_and_safety_flags():
    plan = load_json(PLAN_PATH)
    summary = load_json(SUMMARY_PATH)
    assert plan["task_id"] == "R7-M67_Batch01SecondRefinementPlanArtifactBuilder"
    assert summary["task_id"] == "R7-M67_Batch01SecondRefinementPlanArtifactBuilder"
    scope = plan["scope_constraints"]
    assert scope["no_runtime_implementation"] is True
    assert scope["no_practicebank_generation"] is True
    assert scope["no_learner_state_write"] is True
    assert scope["no_auto_egp_row_selection"] is True
    assert scope["no_authority_write"] is True
    assert scope["no_egp_evidence_refs_write"] is True
    assert scope["no_coverage_increase"] is True


def test_targets_match_batch01_decisions():
    plan = load_json(PLAN_PATH)
    targets = {target["grammar_id"]: target for target in plan["targets"]}
    assert targets["GRAMMAR_ARTICLES_BASIC"]["operator_decision"] == "REQUEST_REFINED_CANDIDATES"
    assert targets["GRAMMAR_BASIC_PREPOSITIONS_PLACE"]["operator_decision"] == "REQUEST_REFINED_CANDIDATES"
    assert targets["GRAMMAR_BE_VERB_BASIC"]["operator_decision"] == "REQUEST_REFINED_CANDIDATES"
    assert targets["GRAMMAR_CAN_STATEMENT"]["operator_decision"] == "DEFER"
    assert targets["GRAMMAR_CAN_STATEMENT"]["candidate_to_audit"] == "1741163708329x931125497510935300"
    assert targets["GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC"]["operator_decision"] == "REQUEST_REFINED_CANDIDATES"


def test_summary_counts_match_plan():
    plan = load_json(PLAN_PATH)
    summary = load_json(SUMMARY_PATH)
    targets = plan["targets"]
    action_counts = {}
    decision_counts = {}
    for target in targets:
        action_counts[target["refinement_action"]] = action_counts.get(target["refinement_action"], 0) + 1
        decision_counts[target["operator_decision"]] = decision_counts.get(target["operator_decision"], 0) + 1
    assert summary["target_count"] == len(targets)
    assert summary["action_counts"] == action_counts
    assert summary["decision_counts"] == decision_counts
    assert summary["operator_review_required"] is True
    assert summary["next_short_step"] == "R7-M68_Batch01SecondRefinementPlanReadback"
    assert summary["stop_reason"] == "NONE"
