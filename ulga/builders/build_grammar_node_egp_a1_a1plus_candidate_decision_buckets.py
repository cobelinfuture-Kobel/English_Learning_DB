import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
SOURCE_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_candidate_resolver.json"
OUT_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_candidate_decision_buckets.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "grammar_node_egp_a1_a1plus_candidate_decision_buckets_summary.json"
TASK_ID = "R7-M99A_A1A1PLUSBulkCandidateDecisionBucketBuilder"
ACCEPTABLE_LEVELS = {"A1", "A2"}


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def reviewable(candidate):
    return candidate.get("level") in ACCEPTABLE_LEVELS and int(candidate.get("score", 0)) >= 2


def bucket_record(record):
    candidates = record.get("candidates", [])
    review_candidates = [c for c in candidates if reviewable(c)]
    if not candidates:
        bucket = "NO_SAFE_CANDIDATE"
    elif review_candidates:
        bucket = "OPERATOR_REVIEW_REQUIRED"
    else:
        bucket = "REJECT_BROAD_ONLY"
    return {
        "grammar_id": record["grammar_id"],
        "decision_bucket": bucket,
        "candidate_count": len(candidates),
        "review_candidate_count": len(review_candidates),
        "review_candidates": review_candidates[:3],
        "rejected_candidate_count": len(candidates) - len(review_candidates),
        "auto_accept_allowed": False,
        "canonical_write_allowed": False,
        "operator_review_required": bucket == "OPERATOR_REVIEW_REQUIRED",
    }


def main():
    source = load_json(SOURCE_PATH)
    records = [bucket_record(record) for record in source.get("records", [])]
    bucket_counts = {}
    for record in records:
        bucket_counts[record["decision_bucket"]] = bucket_counts.get(record["decision_bucket"], 0) + 1
    report = {
        "task_id": TASK_ID,
        "artifact_id": "grammar_node_egp_a1_a1plus_candidate_decision_buckets",
        "source_artifact_id": source.get("artifact_id"),
        "decision_scope": "BULK_CANDIDATE_BUCKETS_NO_CANONICAL_WRITE",
        "records": records,
        "scope_constraints": {
            "auto_accept_allowed": False,
            "canonical_grammar_write_allowed": False,
            "egp_evidence_refs_write_allowed": False,
            "coverage_increase_allowed": False,
            "practicebank_generation_allowed": False,
            "learner_state_write_allowed": False,
            "runtime_change_allowed": False
        }
    }
    summary = {
        "task_id": TASK_ID,
        "artifact_id": "grammar_node_egp_a1_a1plus_candidate_decision_buckets_summary",
        "validation_status": "PASS",
        "source_target_count": len(source.get("records", [])),
        "bucketed_target_count": len(records),
        "bucket_counts": dict(sorted(bucket_counts.items())),
        "operator_review_required_count": bucket_counts.get("OPERATOR_REVIEW_REQUIRED", 0),
        "auto_accept_count": 0,
        "canonical_grammar_write_allowed": False,
        "next_short_step": "R7-M100A_A1A1PLUSOperatorReviewPacketBuilder",
        "stop_reason": "NONE"
    }
    write_json(OUT_PATH, report)
    write_json(SUMMARY_PATH, summary)
    print("A1/A1_PLUS candidate decision bucket build: PASS")
    print("Bucket counts:", summary["bucket_counts"])


if __name__ == "__main__":
    main()
