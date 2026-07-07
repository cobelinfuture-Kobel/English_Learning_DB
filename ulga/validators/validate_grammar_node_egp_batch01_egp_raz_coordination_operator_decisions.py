import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_egp_raz_coordination_operator_decisions.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_egp_raz_coordination_operator_decisions_summary.json"
EXPECTED_TASK = "R7-M85A_Batch01EGPRAZCoordinationOperatorDecisionArtifact"
EXPECTED_IDS = {
    "GRAMMAR_ARTICLES_BASIC",
    "GRAMMAR_BASIC_PREPOSITIONS_PLACE",
    "GRAMMAR_BE_VERB_BASIC",
    "GRAMMAR_CAN_STATEMENT",
    "GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC",
}


def load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"FAIL: {path}: {exc}")
        return None


def fail(message):
    print("FAIL: " + message)
    return False


def validate():
    print("Validating Batch 01 EGP/RAZ coordination operator decisions...")
    if not DATA_PATH.exists() or not SUMMARY_PATH.exists():
        return fail("required output missing")
    data = load(DATA_PATH)
    summary = load(SUMMARY_PATH)
    if not isinstance(data, dict) or not isinstance(summary, dict):
        return fail("top-level outputs must be objects")
    if data.get("task_id") != EXPECTED_TASK or summary.get("task_id") != EXPECTED_TASK:
        return fail("task_id mismatch")
    if data.get("operator_decision_status") != "APPROVED_R7_M84A_COORDINATION_PACKET":
        return fail("operator_decision_status mismatch")
    if data.get("decision_scope") != "EGP_RAZ_COORDINATION_DECISION_ONLY":
        return fail("decision_scope mismatch")
    for key in [
        "authority_write_allowed",
        "egp_evidence_refs_write_allowed",
        "raz_usage_attachment_write_allowed",
        "coverage_increase_allowed",
        "practicebank_generation_allowed",
        "learner_state_write_allowed",
        "runtime_change_allowed",
    ]:
        if data.get(key) is not False or summary.get(key) is not False:
            return fail(f"safety flag must be false: {key}")
    records = data.get("records", [])
    if {record.get("grammar_id") for record in records} != EXPECTED_IDS:
        return fail("unexpected grammar ids")
    authority_count = 0
    form_count = 0
    unresolved_count = 0
    raz_count = 0
    for record in records:
        if record.get("operator_decision") != "APPROVE_COORDINATION_RECOMMENDATION":
            return fail("operator decision mismatch")
        egp_decision = record.get("egp_decision")
        if egp_decision == "ACCEPT_EGP_ROW_AS_AUTHORITY_EVIDENCE":
            authority_count += 1
            if not record.get("egp_row_id") or record.get("egp_evidence_role") != "EGP_AUTHORITY_EVIDENCE":
                return fail("authority decision missing row or role")
        elif egp_decision == "ACCEPT_EGP_ROW_AS_FORM_EVIDENCE_ONLY":
            form_count += 1
            if not record.get("egp_row_id") or record.get("egp_evidence_role") != "EGP_FORM_EVIDENCE":
                return fail("form-only decision missing row or role")
        elif egp_decision == "KEEP_EGP_UNRESOLVED_REQUEST_REFINED_CANDIDATES":
            unresolved_count += 1
            if record.get("egp_row_id") is not None or record.get("egp_evidence_role") is not None:
                return fail("unresolved decision must not include row or role")
        else:
            return fail("unexpected EGP decision")
        count = record.get("approved_raz_usage_example_count")
        if not isinstance(count, int) or count <= 0:
            return fail("approved RAZ count must be positive")
        raz_count += count
    if summary.get("target_count") != len(records):
        return fail("target_count mismatch")
    if summary.get("egp_accept_as_authority_count") != authority_count:
        return fail("authority count mismatch")
    if summary.get("egp_accept_as_form_only_count") != form_count:
        return fail("form count mismatch")
    if summary.get("egp_unresolved_request_refined_count") != unresolved_count:
        return fail("unresolved count mismatch")
    if summary.get("approved_raz_usage_example_count") != raz_count:
        return fail("approved RAZ count mismatch")
    if summary.get("next_short_step") != "R7-M86A_Batch01AuthorityPatchPlanPolicyScan":
        return fail("next_short_step mismatch")
    if summary.get("stop_reason") != "NONE":
        return fail("stop_reason must be NONE")
    print("Batch 01 EGP/RAZ coordination operator decision validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
