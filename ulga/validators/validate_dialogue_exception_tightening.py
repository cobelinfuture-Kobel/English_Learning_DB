import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ulga.validators.validate_learner_state_schema import validate_learner_state_collection


LEARNER_STATE_PATH = BASE_DIR / "ulga" / "learner_state" / "learner_state.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "dialogue_exception_tightening_summary.json"


class ValidationError(Exception):
    pass


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def require(condition, message):
    if not condition:
        raise ValidationError(message)


def validate_dialogue_exception_tightening(learner_state_path=LEARNER_STATE_PATH, summary_path=SUMMARY_PATH):
    require(learner_state_path.exists(), f"missing learner state output: {learner_state_path}")
    require(summary_path.exists(), f"missing dialogue exception tightening summary: {summary_path}")

    learner_state = load_json(learner_state_path)
    summary = load_json(summary_path)
    validate_learner_state_collection(learner_state)

    records = learner_state["learner_state_records"]
    dialogue_records = [record for record in records if record["node_type"] == "dialogue"]
    require(summary.get("records_evaluated") == len(records), "summary records_evaluated mismatch")
    require(summary.get("dialogue_records_evaluated") == len(dialogue_records), "summary dialogue_records_evaluated mismatch")
    require(summary.get("records_modified") == len(summary.get("before_after_examples", [])), "summary records_modified mismatch")
    require(summary.get("status") == "PASS", "summary status must be PASS")

    for example in summary.get("before_after_examples", []):
        require(example["node_type"] == "dialogue", "before_after_examples must only include dialogue records")
        require(example["strongest_role"] != "primary_target", "dialogue tightening example must be non-primary")
        require(example["exposure_count"] == 1, "dialogue tightening example must be single-event")
        require(example["guarded_mastery_score"] <= 0.49, "single-event non-primary dialogue exceeded 0.49")

    for record in dialogue_records:
        if record["exposure_count"] == 1 and record["mastery_score"] > 0.49:
            require(
                False,
                f"single-event dialogue record exceeded 0.49: {record['learner_id']} | {record['node_id']}",
            )


def main():
    try:
        validate_dialogue_exception_tightening()
    except Exception as exc:
        print(f"Dialogue exception tightening validation: FAIL - {exc}")
        return 1
    print("Dialogue exception tightening validation: PASS")
    print(f"Validated {LEARNER_STATE_PATH.relative_to(BASE_DIR)}")
    print(f"Validated {SUMMARY_PATH.relative_to(BASE_DIR)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
