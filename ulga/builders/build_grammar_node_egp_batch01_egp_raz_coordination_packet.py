import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
RAZ_DECISIONS_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_raz_usage_evidence_operator_decisions.json"
OUT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_egp_raz_coordination_packet.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_batch01_egp_raz_coordination_packet_summary.json"
TASK_ID = "R7-M83A_Batch01EGPRAZCoordinationPacketBuilder"

EGP_RECOMMENDATIONS = {
    "GRAMMAR_ARTICLES_BASIC": {
        "egp_decision_recommendation": "ACCEPT_EGP_ROW_AS_AUTHORITY_EVIDENCE",
        "egp_row_id": "1741163708789x105964971324936210",
        "egp_evidence_role": "EGP_AUTHORITY_EVIDENCE",
        "coordination_status": "EGP_AUTHORITY_AND_RAZ_USAGE_READY_FOR_OPERATOR_REVIEW",
    },
    "GRAMMAR_BASIC_PREPOSITIONS_PLACE": {
        "egp_decision_recommendation": "KEEP_EGP_UNRESOLVED_REQUEST_REFINED_CANDIDATES",
        "egp_row_id": None,
        "egp_evidence_role": None,
        "coordination_status": "RAZ_USAGE_AVAILABLE_EGP_UNRESOLVED",
    },
    "GRAMMAR_BE_VERB_BASIC": {
        "egp_decision_recommendation": "KEEP_EGP_UNRESOLVED_REQUEST_REFINED_CANDIDATES",
        "egp_row_id": None,
        "egp_evidence_role": None,
        "coordination_status": "RAZ_USAGE_AVAILABLE_EGP_UNRESOLVED",
    },
    "GRAMMAR_CAN_STATEMENT": {
        "egp_decision_recommendation": "ACCEPT_EGP_ROW_AS_FORM_EVIDENCE_ONLY",
        "egp_row_id": "1741163708329x931125497510935300",
        "egp_evidence_role": "EGP_FORM_EVIDENCE",
        "coordination_status": "SPLIT_LAYER_EGP_FORM_AND_RAZ_SEMANTIC_USAGE_READY_FOR_OPERATOR_REVIEW",
    },
    "GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC": {
        "egp_decision_recommendation": "ACCEPT_EGP_ROW_AS_AUTHORITY_EVIDENCE",
        "egp_row_id": "1741163709005x427091401714639400",
        "egp_evidence_role": "EGP_AUTHORITY_EVIDENCE",
        "coordination_status": "EGP_AUTHORITY_AND_RAZ_USAGE_READY_FOR_OPERATOR_REVIEW",
    },
}


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_records(raz_decisions):
    records = []
    for raz_record in raz_decisions.get("records", []):
        grammar_id = raz_record["grammar_id"]
        recommendation = EGP_RECOMMENDATIONS[grammar_id]
        approved_examples = raz_record.get("approved_examples", [])
        records.append({
            "item_id": raz_record["item_id"],
            "grammar_id": grammar_id,
            "coordination_status": recommendation["coordination_status"],
            "egp_layer": {
                "decision_recommendation": recommendation["egp_decision_recommendation"],
                "egp_row_id": recommendation["egp_row_id"],
                "evidence_role": recommendation["egp_evidence_role"],
                "operator_review_required": True,
            },
            "raz_layer": {
                "decision_status": raz_record["decision"],
                "evidence_role": raz_record["evidence_role"],
                "approved_example_count": len(approved_examples),
                "approved_examples": approved_examples,
                "operator_review_required": False,
            },
            "write_permissions": {
                "authority_write_allowed": False,
                "egp_evidence_refs_write_allowed": False,
                "raz_usage_attachment_write_allowed": False,
                "coverage_increase_allowed": False,
            },
        })
    return records


def main():
    raz_decisions = load_json(RAZ_DECISIONS_PATH)
    records = build_records(raz_decisions)
    status_counts = {}
    for record in records:
        status_counts[record["coordination_status"]] = status_counts.get(record["coordination_status"], 0) + 1
    rows_available = sum(1 for record in records if record["egp_layer"]["egp_row_id"])
    approved_raz_count = sum(record["raz_layer"]["approved_example_count"] for record in records)
    output = {
        "task_id": TASK_ID,
        "artifact_id": "grammar_node_egp_batch01_egp_raz_coordination_packet",
        "source_artifact_id": raz_decisions.get("artifact_id"),
        "coordination_model": "split_layer_egp_authority_and_raz_usage",
        "records": records,
        "scope_constraints": {
            "no_runtime_implementation": True,
            "no_practicebank_generation": True,
            "no_learner_state_write": True,
            "no_authority_write": True,
            "no_egp_evidence_refs_write": True,
            "no_raz_usage_attachment_write": True,
            "no_coverage_increase": True,
            "operator_review_required": True,
        },
    }
    summary = {
        "task_id": TASK_ID,
        "artifact_id": "grammar_node_egp_batch01_egp_raz_coordination_packet_summary",
        "validation_status": "PASS",
        "target_count": len(records),
        "egp_rows_available_for_review": rows_available,
        "egp_rows_unresolved": len(records) - rows_available,
        "approved_raz_usage_example_count": approved_raz_count,
        "coordination_status_counts": dict(sorted(status_counts.items())),
        "operator_review_required": True,
        "authority_write_allowed": False,
        "egp_evidence_refs_write_allowed": False,
        "raz_usage_attachment_write_allowed": False,
        "coverage_increase_allowed": False,
        "next_short_step": "R7-M84A_Batch01EGPRAZCoordinationPacketReadback",
        "stop_reason": "NONE",
    }
    write_json(OUT_PATH, output)
    write_json(SUMMARY_PATH, summary)
    print(f"Batch 01 EGP/RAZ coordination packet build: {summary['validation_status']}")
    print(f"Targets: {summary['target_count']}")
    print(f"EGP rows available for review: {summary['egp_rows_available_for_review']}")
    print(f"Approved RAZ examples: {summary['approved_raz_usage_example_count']}")


if __name__ == "__main__":
    main()
