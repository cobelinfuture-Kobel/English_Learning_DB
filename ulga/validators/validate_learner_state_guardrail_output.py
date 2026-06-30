import json
import sys
from collections import Counter
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ulga.validators.validate_learner_state_schema import validate_learner_state_collection


LEARNER_STATE_PATH = BASE_DIR / "ulga" / "learner_state" / "learner_state.json"
GUARDRAIL_SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "learner_state_guardrail_summary.json"


class ValidationError(Exception):
    pass


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def require(condition, message):
    if not condition:
        raise ValidationError(message)


def validate_guardrail_output(learner_state_path=LEARNER_STATE_PATH, guardrail_summary_path=GUARDRAIL_SUMMARY_PATH):
    require(learner_state_path.exists(), f"missing learner state output: {learner_state_path}")
    require(guardrail_summary_path.exists(), f"missing learner state guardrail summary: {guardrail_summary_path}")

    learner_state_payload = load_json(learner_state_path)
    guardrail_summary = load_json(guardrail_summary_path)
    validate_learner_state_collection(learner_state_payload)

    records = learner_state_payload["learner_state_records"]
    require(guardrail_summary.get("records_evaluated") == len(records), "guardrail summary records_evaluated mismatch")
    examples = guardrail_summary.get("before_after_examples")
    require(isinstance(examples, list), "guardrail summary before_after_examples must be a list")

    seen_pairs = {(record["learner_id"], record["node_id"]) for record in records}
    reason_counts = Counter()
    changed_count = 0
    for example in examples:
        pair = (example["learner_id"], example["node_id"])
        require(pair in seen_pairs, f"guardrail example references missing learner-node pair: {pair[0]} | {pair[1]}")
        require(example["guarded_mastery_score"] <= example["base_mastery_score"], "guarded_mastery_score must not exceed base_mastery_score")
        require(example["guarded_mastery_score"] <= example["guardrail_ceiling"], "guarded_mastery_score exceeds guardrail_ceiling")
        require(example["guarded_mastery_score"] != example["base_mastery_score"], "guardrail example must represent a changed record")
        require(example["before_band"] != example["after_band"] or example["guarded_mastery_score"] != example["base_mastery_score"], "invalid before/after guardrail example")
        changed_count += 1
        for reason in example.get("guardrail_reasons", []):
            reason_counts[reason] += 1

    require(
        guardrail_summary.get("records_modified_by_guardrails") == changed_count,
        "guardrail summary records_modified_by_guardrails mismatch",
    )
    require(
        guardrail_summary.get("guardrail_reason_counts") == dict(sorted(reason_counts.items())),
        "guardrail summary guardrail_reason_counts mismatch",
    )
    require(guardrail_summary.get("status") == "PASS", "guardrail summary status must be PASS")


def main():
    try:
        validate_guardrail_output()
    except Exception as exc:
        print(f"Learner state guardrail output validation: FAIL - {exc}")
        return 1
    print("Learner state guardrail output validation: PASS")
    print(f"Validated {LEARNER_STATE_PATH.relative_to(BASE_DIR)}")
    print(f"Validated {GUARDRAIL_SUMMARY_PATH.relative_to(BASE_DIR)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
