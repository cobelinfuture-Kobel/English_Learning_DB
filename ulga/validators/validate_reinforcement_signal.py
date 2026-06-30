import json
import sys
from collections import Counter
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

SIGNAL_PATH = BASE_DIR / "ulga" / "graph" / "reinforcement_signal.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "reinforcement_signal_summary.json"
LEARNING_OPPORTUNITIES_PATH = BASE_DIR / "ulga" / "graph" / "learning_opportunities.json"

SOURCE = "ULGA_S10G_REINFORCEMENT_SIGNAL"
VALID_BANDS = {"none", "low", "medium", "high"}
VALID_DEPENDENCY_STATUSES = {"ready", "unknown", "blocked"}
VALID_INELIGIBLE_REASONS = {None, "dependency_unknown", "dependency_blocked", "no_positive_signal"}
REQUIRED_BREAKDOWN_KEYS = {
    "review_due_score",
    "mastery_gap_score",
    "time_decay_score",
    "dependency_importance_score",
    "theme_continuity_score",
}


def read_json(path):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"FAIL: could not load {path}: {exc}")
        return None


def fail(message):
    print(f"FAIL: {message}")
    return False


def in_score_range(value):
    return isinstance(value, (int, float)) and 0 <= value <= 1


def expected_band(score):
    if score == 0:
        return "none"
    if score < 0.35:
        return "low"
    if score < 0.65:
        return "medium"
    return "high"


def validate():
    print("Validating ULGA Reinforcement Signal...")
    for path in [SIGNAL_PATH, SUMMARY_PATH, LEARNING_OPPORTUNITIES_PATH]:
        if not path.exists():
            return fail(f"required file does not exist: {path}")

    payload = read_json(SIGNAL_PATH)
    summary = read_json(SUMMARY_PATH)
    opportunities = read_json(LEARNING_OPPORTUNITIES_PATH)
    if payload is None or summary is None or opportunities is None:
        return False
    if not isinstance(payload, dict):
        return fail("reinforcement_signal.json must contain an object")
    if not isinstance(summary, dict):
        return fail("reinforcement_signal_summary.json must contain an object")
    if not isinstance(opportunities, list):
        return fail("learning_opportunities.json must contain a list")

    metadata = payload.get("metadata")
    signals = payload.get("signals")
    if not isinstance(metadata, dict):
        return fail("metadata must be an object")
    if metadata.get("source") != SOURCE:
        return fail(f"metadata source must be {SOURCE}")
    if not metadata.get("generated_at"):
        return fail("metadata generated_at is required")
    if not isinstance(signals, list):
        return fail("signals must be a list")

    opportunity_ids = {item.get("opportunity_id") for item in opportunities if isinstance(item, dict)}
    opportunity_ids.discard(None)
    seen_signal_ids = set()
    seen_targets = set()
    for index, signal in enumerate(signals):
        if not isinstance(signal, dict):
            return fail(f"signals[{index}] must be an object")
        for key in [
            "signal_id",
            "target_type",
            "target_id",
            "signal_score",
            "signal_band",
            "planner_eligible",
            "ineligible_reason",
            "signal_sources",
            "reason_codes",
            "dependency",
            "source",
        ]:
            if key not in signal:
                return fail(f"signals[{index}] missing {key}")
        signal_id = signal["signal_id"]
        if signal_id in seen_signal_ids:
            return fail(f"duplicate signal_id: {signal_id}")
        seen_signal_ids.add(signal_id)
        if signal["target_type"] != "learning_opportunity":
            return fail(f"{signal_id} target_type must be learning_opportunity")
        target_id = signal["target_id"]
        if target_id not in opportunity_ids:
            return fail(f"{signal_id} target_id does not exist in learning_opportunities: {target_id}")
        if target_id in seen_targets:
            return fail(f"duplicate target signal for {target_id}")
        seen_targets.add(target_id)
        score = signal["signal_score"]
        if not in_score_range(score):
            return fail(f"{signal_id} signal_score out of range")
        if signal["signal_band"] not in VALID_BANDS or signal["signal_band"] != expected_band(score):
            return fail(f"{signal_id} signal_band is inconsistent")
        if not isinstance(signal["planner_eligible"], bool):
            return fail(f"{signal_id} planner_eligible must be a bool")
        if signal["ineligible_reason"] not in VALID_INELIGIBLE_REASONS:
            return fail(f"{signal_id} invalid ineligible_reason")
        if signal["planner_eligible"] and signal["ineligible_reason"] is not None:
            return fail(f"{signal_id} planner_eligible signal must not have ineligible_reason")
        if not signal["planner_eligible"] and signal["ineligible_reason"] is None:
            return fail(f"{signal_id} ineligible signal must have ineligible_reason")
        dependency = signal["dependency"]
        if not isinstance(dependency, dict) or dependency.get("status") not in VALID_DEPENDENCY_STATUSES:
            return fail(f"{signal_id} dependency.status invalid")
        if dependency["status"] == "unknown" and signal["ineligible_reason"] != "dependency_unknown":
            return fail(f"{signal_id} unknown dependency must be dependency_unknown")
        if dependency["status"] == "blocked" and signal["ineligible_reason"] != "dependency_blocked":
            return fail(f"{signal_id} blocked dependency must be dependency_blocked")
        if signal["planner_eligible"] and (dependency["status"] != "ready" or score <= 0):
            return fail(f"{signal_id} planner eligibility violates dependency gate")
        if not isinstance(signal["signal_sources"], list):
            return fail(f"{signal_id} signal_sources must be a list")
        if not isinstance(signal["reason_codes"], list):
            return fail(f"{signal_id} reason_codes must be a list")
        if score > 0 and not signal["reason_codes"]:
            return fail(f"{signal_id} positive score must have reason_codes")
        if signal["source"] != SOURCE:
            return fail(f"{signal_id} source must be {SOURCE}")
        breakdown = signal.get("score_breakdown")
        if not isinstance(breakdown, dict) or set(breakdown) != REQUIRED_BREAKDOWN_KEYS:
            return fail(f"{signal_id} score_breakdown keys are incomplete")
        for key, value in breakdown.items():
            if not in_score_range(value):
                return fail(f"{signal_id} {key} out of range")

    if len(signals) != len(opportunity_ids):
        return fail("signal count must match learning opportunity count")
    if summary.get("status") not in {"PASS", "PASS_WITH_WARNINGS"}:
        return fail("summary status must be PASS or PASS_WITH_WARNINGS")
    if summary.get("total_signals") != len(signals):
        return fail("summary total_signals mismatch")
    planner_eligible_count = sum(1 for signal in signals if signal["planner_eligible"])
    if summary.get("planner_eligible_count") != planner_eligible_count:
        return fail("summary planner_eligible_count mismatch")
    if summary.get("ineligible_count") != len(signals) - planner_eligible_count:
        return fail("summary ineligible_count mismatch")
    if summary.get("signals_with_score_gt_zero") != sum(1 for signal in signals if signal["signal_score"] > 0):
        return fail("summary signals_with_score_gt_zero mismatch")
    if summary.get("eligible_with_score_gt_zero") != sum(
        1 for signal in signals if signal["planner_eligible"] and signal["signal_score"] > 0
    ):
        return fail("summary eligible_with_score_gt_zero mismatch")
    dependency_unknown_blocked_count = sum(
        1 for signal in signals if signal["dependency"]["status"] in {"unknown", "blocked"}
    )
    if summary.get("dependency_unknown_blocked_count") != dependency_unknown_blocked_count:
        return fail("summary dependency_unknown_blocked_count mismatch")
    if summary.get("signal_band_distribution") != dict(sorted(Counter(signal["signal_band"] for signal in signals).items())):
        return fail("summary signal_band_distribution mismatch")
    if summary.get("ineligible_reason_distribution") != dict(
        sorted(Counter(signal["ineligible_reason"] for signal in signals if signal["ineligible_reason"]).items())
    ):
        return fail("summary ineligible_reason_distribution mismatch")
    if not isinstance(summary.get("warnings"), list):
        return fail("summary warnings must be a list")

    print("Reinforcement Signal validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
