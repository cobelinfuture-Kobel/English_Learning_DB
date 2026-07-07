import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_egp_raz_coordination_packet.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_egp_raz_coordination_packet_summary.json"
EXPECTED_TASK = "R7-M83A_Batch01EGPRAZCoordinationPacketBuilder"
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
    print("Validating Batch 01 EGP/RAZ coordination packet...")
    if not DATA_PATH.exists() or not SUMMARY_PATH.exists():
        return fail("required output missing")
    data = load(DATA_PATH)
    summary = load(SUMMARY_PATH)
    if not isinstance(data, dict) or not isinstance(summary, dict):
        return fail("top-level outputs must be objects")
    if data.get("task_id") != EXPECTED_TASK or summary.get("task_id") != EXPECTED_TASK:
        return fail("task_id mismatch")
    records = data.get("records", [])
    if {record.get("grammar_id") for record in records} != EXPECTED_IDS:
        return fail("unexpected grammar ids")
    rows_available = 0
    raz_examples = 0
    status_counts = {}
    for record in records:
        egp_layer = record.get("egp_layer", {})
        raz_layer = record.get("raz_layer", {})
        permissions = record.get("write_permissions", {})
        if egp_layer.get("operator_review_required") is not True:
            return fail("EGP layer must require operator review")
        if raz_layer.get("operator_review_required") is not False:
            return fail("RAZ layer is already operator approved")
        if egp_layer.get("egp_row_id"):
            rows_available += 1
        count = raz_layer.get("approved_example_count")
        if not isinstance(count, int) or count <= 0:
            return fail("RAZ approved example count must be positive")
        raz_examples += count
        for key in [
            "authority_write_allowed",
            "egp_evidence_refs_write_allowed",
            "raz_usage_attachment_write_allowed",
            "coverage_increase_allowed",
        ]:
            if permissions.get(key) is not False:
                return fail(f"write permission must be false: {key}")
        status = record.get("coordination_status")
        status_counts[status] = status_counts.get(status, 0) + 1
    scope = data.get("scope_constraints", {})
    for key in [
        "no_runtime_implementation",
        "no_practicebank_generation",
        "no_learner_state_write",
        "no_authority_write",
        "no_egp_evidence_refs_write",
        "no_raz_usage_attachment_write",
        "no_coverage_increase",
        "operator_review_required",
    ]:
        if scope.get(key) is not True:
            return fail(f"scope flag must be true: {key}")
    if summary.get("target_count") != len(records):
        return fail("target_count mismatch")
    if summary.get("egp_rows_available_for_review") != rows_available:
        return fail("egp_rows_available_for_review mismatch")
    if summary.get("egp_rows_unresolved") != len(records) - rows_available:
        return fail("egp_rows_unresolved mismatch")
    if summary.get("approved_raz_usage_example_count") != raz_examples:
        return fail("approved_raz_usage_example_count mismatch")
    if summary.get("coordination_status_counts") != dict(sorted(status_counts.items())):
        return fail("coordination_status_counts mismatch")
    for key in [
        "authority_write_allowed",
        "egp_evidence_refs_write_allowed",
        "raz_usage_attachment_write_allowed",
        "coverage_increase_allowed",
    ]:
        if summary.get(key) is not False:
            return fail(f"summary flag must be false: {key}")
    if summary.get("operator_review_required") is not True:
        return fail("operator_review_required must be true")
    if summary.get("next_short_step") != "R7-M84A_Batch01EGPRAZCoordinationPacketReadback":
        return fail("next_short_step mismatch")
    if summary.get("stop_reason") != "NONE":
        return fail("stop_reason must be NONE")
    print("Batch 01 EGP/RAZ coordination packet validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
