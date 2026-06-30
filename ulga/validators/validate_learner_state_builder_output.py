import json
import sys
from collections import Counter
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ulga.validators.validate_learner_state_schema import validate_learner_state_collection


LEARNER_STATE_PATH = BASE_DIR / "ulga" / "learner_state" / "learner_state.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "learner_state_builder_summary.json"


class ValidationError(Exception):
    pass


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def require(condition, message):
    if not condition:
        raise ValidationError(message)


def validate_builder_output(learner_state_path=LEARNER_STATE_PATH, summary_path=SUMMARY_PATH):
    require(learner_state_path.exists(), f"missing learner state output: {learner_state_path}")
    require(summary_path.exists(), f"missing learner state builder summary: {summary_path}")

    learner_state_payload = load_json(learner_state_path)
    summary_payload = load_json(summary_path)
    validate_learner_state_collection(learner_state_payload)

    records = learner_state_payload["learner_state_records"]
    learner_ids = {record["learner_id"] for record in records}
    node_type_counts = Counter(record["node_type"] for record in records)
    mastery_band_counts = Counter(record["mastery_band"] for record in records)

    require(summary_payload.get("total_learner_state_records") == len(records), "summary total_learner_state_records mismatch")
    require(summary_payload.get("learner_count") == len(learner_ids), "summary learner_count mismatch")
    require(summary_payload.get("node_type_counts") == dict(sorted(node_type_counts.items())), "summary node_type_counts mismatch")
    require(summary_payload.get("mastery_band_counts") == dict(sorted(mastery_band_counts.items())), "summary mastery_band_counts mismatch")

    seen_pairs = set()
    seen_idempotency_keys = set()
    for record in records:
        pair = (record["learner_id"], record["node_id"])
        require(pair not in seen_pairs, f"duplicate learner_id + node_id detected: {pair[0]} | {pair[1]}")
        seen_pairs.add(pair)

        idem_key = record["processing_idempotency_key"]
        require(idem_key not in seen_idempotency_keys, f"duplicate processing_idempotency_key detected: {idem_key}")
        seen_idempotency_keys.add(idem_key)


def main():
    try:
        validate_builder_output()
    except Exception as exc:
        print(f"Learner state builder output validation: FAIL - {exc}")
        return 1
    print("Learner state builder output validation: PASS")
    print(f"Validated {LEARNER_STATE_PATH.relative_to(BASE_DIR)}")
    print(f"Validated {SUMMARY_PATH.relative_to(BASE_DIR)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
