import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

LEARNING_OPPORTUNITIES_PATH = BASE_DIR / "ulga" / "graph" / "learning_opportunities.json"
RANKED_OPPORTUNITIES_PATH = BASE_DIR / "ulga" / "graph" / "ranked_learning_opportunities.json"
ANTIGRAVITY_PLAN_PATH = BASE_DIR / "ulga" / "graph" / "antigravity_plan.json"
READING_STUBS_PATH = BASE_DIR / "ulga" / "graph" / "reading_stub_authority.json"
LEARNER_STATE_PATH = BASE_DIR / "ulga" / "learner_state" / "learner_state.json"
DEPENDENCY_GRAPH_PATH = BASE_DIR / "ulga" / "graph" / "dependency_graph.json"
THEME_SPIRAL_GRAPH_PATH = BASE_DIR / "ulga" / "graph" / "theme_spiral_graph.json"
LEARNING_SIGNAL_POLICY_PATH = BASE_DIR / "ulga" / "schema" / "learning_signal_policy.json"

SIGNAL_OUT_PATH = BASE_DIR / "ulga" / "graph" / "reinforcement_signal.json"
SUMMARY_OUT_PATH = BASE_DIR / "ulga" / "reports" / "reinforcement_signal_summary.json"

SOURCE = "ULGA_S10G_REINFORCEMENT_SIGNAL"
CONTRACT_VERSION = "ULGA-S10G"
GENERATED_AT = "2026-06-18T00:00:00Z"
PLAN_TIME = datetime(2026, 6, 18, tzinfo=timezone.utc)
VALID_DEPENDENCY_STATUSES = {"ready", "unknown", "blocked"}
WEIGHTS = {
    "review_due_score": 0.30,
    "mastery_gap_score": 0.25,
    "time_decay_score": 0.20,
    "dependency_importance_score": 0.15,
    "theme_continuity_score": 0.10,
}


def read_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_json_optional(path, default):
    if not path.exists():
        return default
    return read_json(path)


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, sort_keys=False)
        f.write("\n")


def clamp(value):
    return round(max(0.0, min(1.0, float(value))), 6)


def parse_time(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def all_focus_node_ids(opportunity):
    focus_nodes = opportunity.get("focus_nodes", {})
    ids = []
    for key in ["vocabulary", "grammar", "pattern", "chunk"]:
        ids.extend(focus_nodes.get(key, []) or [])
    return ids


def reinforced_node_refs(opportunity):
    reinforces = opportunity.get("reinforces", {})
    refs = []
    for key in ["vocabulary", "grammar", "pattern", "chunk"]:
        refs.extend(reinforces.get(key, []) or [])
    return sorted(set(refs))


def build_ranked_index(ranked):
    return {
        item["opportunity_id"]: item
        for item in ranked
        if isinstance(item, dict) and item.get("opportunity_id")
    }


def build_state_index(learner_state, warnings):
    records = learner_state.get("learner_state_records", []) if isinstance(learner_state, dict) else []
    if not records:
        warnings.append("learner_state has no records; learner-specific reinforcement sources are unavailable")
    by_node = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        node_id = record.get("node_id")
        if not node_id:
            continue
        by_node.setdefault(node_id, []).append(record)
    return by_node


def records_for_opportunity(opportunity, state_index):
    records = []
    for node_id in all_focus_node_ids(opportunity) + reinforced_node_refs(opportunity):
        records.extend(state_index.get(node_id, []))
    return records


def review_due_score(records):
    scores = []
    for record in records:
        due_at = parse_time(record.get("review_due_at"))
        if due_at is None:
            continue
        days_until_due = (due_at - PLAN_TIME).total_seconds() / 86400
        if days_until_due <= 0:
            scores.append(1.0)
        elif days_until_due <= 3:
            scores.append(0.7)
        else:
            scores.append(0.3)
    return max(scores) if scores else 0.0


def mastery_gap_score(records):
    scores = []
    for record in records:
        mastery = record.get("mastery_score")
        if isinstance(mastery, (int, float)):
            scores.append(clamp(1.0 - mastery))
            continue
        band = record.get("mastery_band")
        scores.append(
            {
                "seen": 0.9,
                "practicing": 0.8,
                "functional": 0.35,
                "mastered": 0.1,
                "automatic": 0.0,
            }.get(band, 0.0)
        )
    return max(scores) if scores else 0.0


def time_decay_score(records):
    scores = []
    for record in records:
        last_seen_at = parse_time(record.get("last_seen_at"))
        if last_seen_at is None:
            continue
        days_since_seen = (PLAN_TIME - last_seen_at).total_seconds() / 86400
        if record.get("last_success_at"):
            scores.append(0.0)
        elif days_since_seen >= 30:
            scores.append(1.0)
        elif days_since_seen >= 14:
            scores.append(0.7)
        elif days_since_seen >= 7:
            scores.append(0.4)
        elif days_since_seen >= 1:
            scores.append(0.2)
        else:
            scores.append(0.0)
    return max(scores) if scores else 0.0


def dependency_importance_score(opportunity, ranked_item):
    if reinforced_node_refs(opportunity):
        return 0.6
    ranked_reinforcement = ranked_item.get("score_breakdown", {}).get("reinforcement_score", 0) if ranked_item else 0
    if isinstance(ranked_reinforcement, (int, float)) and ranked_reinforcement > 0:
        return 0.4
    return 0.0


def theme_continuity_score(opportunity, concrete_signal_exists):
    if not concrete_signal_exists:
        return 0.0
    source = opportunity.get("theme_confidence", {}).get("source")
    if source in {"pattern_theme_ref", "pattern_slot_gate"}:
        return 1.0
    if source in {"vocabulary_theme", "chunk_theme_hint", "theme_consensus"}:
        return 0.6
    return 0.0


def signal_band(score):
    if score == 0:
        return "none"
    if score < 0.35:
        return "low"
    if score < 0.65:
        return "medium"
    return "high"


def dependency_gate(status, score):
    if status == "ready" and score > 0:
        return True, None
    if status == "unknown":
        return False, "dependency_unknown"
    if status == "blocked":
        return False, "dependency_blocked"
    return False, "no_positive_signal"


def reason_codes_from_breakdown(breakdown, refs):
    reason_codes = []
    if breakdown["review_due_score"] > 0:
        reason_codes.append("review_due")
    if breakdown["mastery_gap_score"] > 0:
        reason_codes.append("low_mastery")
    if breakdown["time_decay_score"] > 0:
        reason_codes.append("time_decay")
    if breakdown["dependency_importance_score"] > 0:
        reason_codes.append("dependency_reinforcement")
    if breakdown["theme_continuity_score"] > 0:
        reason_codes.append("theme_revisit")
    if refs:
        reason_codes.append("opportunity_reinforces_nodes")
    return reason_codes


def signal_sources_from_breakdown(breakdown, refs):
    sources = []
    if breakdown["review_due_score"] > 0:
        sources.append("review_due")
    if breakdown["mastery_gap_score"] > 0:
        sources.append("mastery_gap")
    if breakdown["time_decay_score"] > 0:
        sources.append("time_decay")
    if breakdown["dependency_importance_score"] > 0:
        sources.append("dependency_importance")
    if breakdown["theme_continuity_score"] > 0:
        sources.append("theme_continuity")
    if refs:
        sources.append("opportunity_reinforces")
    return sources


def score_for(opportunity, ranked_item, state_index):
    records = records_for_opportunity(opportunity, state_index)
    refs = reinforced_node_refs(opportunity)
    base_breakdown = {
        "review_due_score": review_due_score(records),
        "mastery_gap_score": mastery_gap_score(records),
        "time_decay_score": time_decay_score(records),
        "dependency_importance_score": dependency_importance_score(opportunity, ranked_item),
        "theme_continuity_score": 0.0,
    }
    concrete_signal_exists = any(
        base_breakdown[key] > 0
        for key in ["review_due_score", "mastery_gap_score", "time_decay_score", "dependency_importance_score"]
    )
    base_breakdown["theme_continuity_score"] = theme_continuity_score(opportunity, concrete_signal_exists)
    score = round(sum(WEIGHTS[key] * base_breakdown[key] for key in WEIGHTS), 6)
    return score, base_breakdown, refs


def build_signal(index, opportunity, ranked_item, state_index):
    opportunity_id = opportunity["opportunity_id"]
    dependency_status = opportunity.get("dependency", {}).get("status", "unknown")
    if dependency_status not in VALID_DEPENDENCY_STATUSES:
        dependency_status = "unknown"
    score, breakdown, refs = score_for(opportunity, ranked_item, state_index)
    planner_eligible, ineligible_reason = dependency_gate(dependency_status, score)
    reason_codes = reason_codes_from_breakdown(breakdown, refs)
    return {
        "signal_id": f"RS_{index:06d}",
        "target_type": "learning_opportunity",
        "target_id": opportunity_id,
        "signal_score": score,
        "signal_band": signal_band(score),
        "planner_eligible": planner_eligible,
        "ineligible_reason": ineligible_reason,
        "signal_sources": signal_sources_from_breakdown(breakdown, refs),
        "reason_codes": reason_codes,
        "reinforced_node_refs": refs,
        "score_breakdown": breakdown,
        "dependency": {
            "status": dependency_status,
        },
        "source": SOURCE,
    }


def build_summary(signals, warnings):
    band_distribution = Counter(signal["signal_band"] for signal in signals)
    ineligible_distribution = Counter(
        signal["ineligible_reason"] for signal in signals if signal["ineligible_reason"]
    )
    dependency_unknown_blocked_count = sum(
        1 for signal in signals if signal["dependency"]["status"] in {"unknown", "blocked"}
    )
    return {
        "status": "PASS_WITH_WARNINGS" if warnings else "PASS",
        "total_signals": len(signals),
        "planner_eligible_count": sum(1 for signal in signals if signal["planner_eligible"]),
        "ineligible_count": sum(1 for signal in signals if not signal["planner_eligible"]),
        "signals_with_score_gt_zero": sum(1 for signal in signals if signal["signal_score"] > 0),
        "eligible_with_score_gt_zero": sum(
            1 for signal in signals if signal["planner_eligible"] and signal["signal_score"] > 0
        ),
        "dependency_unknown_blocked_count": dependency_unknown_blocked_count,
        "signal_band_distribution": dict(sorted(band_distribution.items())),
        "ineligible_reason_distribution": dict(sorted(ineligible_distribution.items())),
        "warnings": warnings,
    }


def build_reinforcement_signal(output_path=SIGNAL_OUT_PATH, summary_path=SUMMARY_OUT_PATH):
    warnings = []
    opportunities = read_json_optional(LEARNING_OPPORTUNITIES_PATH, [])
    ranked = read_json_optional(RANKED_OPPORTUNITIES_PATH, [])
    learner_state = read_json_optional(LEARNER_STATE_PATH, {})
    read_json_optional(ANTIGRAVITY_PLAN_PATH, {})
    read_json_optional(READING_STUBS_PATH, [])
    read_json_optional(DEPENDENCY_GRAPH_PATH, {})
    read_json_optional(THEME_SPIRAL_GRAPH_PATH, {})
    read_json_optional(LEARNING_SIGNAL_POLICY_PATH, {})

    if not isinstance(opportunities, list):
        warnings.append("learning_opportunities.json was not a list; emitted zero signals")
        opportunities = []
    if not isinstance(ranked, list):
        warnings.append("ranked_learning_opportunities.json was not a list; ranking reinforcement source unavailable")
        ranked = []

    ranked_index = build_ranked_index(ranked)
    state_index = build_state_index(learner_state, warnings)
    signals = []
    for index, opportunity in enumerate(
        sorted(
            [item for item in opportunities if isinstance(item, dict) and item.get("opportunity_id")],
            key=lambda item: item["opportunity_id"],
        ),
        start=1,
    ):
        signals.append(build_signal(index, opportunity, ranked_index.get(opportunity["opportunity_id"], {}), state_index))

    if not any(signal["planner_eligible"] for signal in signals):
        warnings.append("no planner-eligible positive reinforcement signals were generated")

    payload = {
        "metadata": {
            "source": SOURCE,
            "generated_at": GENERATED_AT,
            "version": "1.0",
            "contract_version": CONTRACT_VERSION,
        },
        "signals": signals,
    }
    summary = build_summary(signals, warnings)
    write_json(output_path, payload)
    write_json(summary_path, summary)
    print(f"Reinforcement Signal build: {summary['status']}")
    print(f"Signals: {summary['total_signals']}")
    print(f"Planner eligible: {summary['planner_eligible_count']}")
    print(f"Warnings: {len(warnings)}")
    return summary


def main():
    try:
        build_reinforcement_signal()
    except Exception as exc:
        print(f"Reinforcement Signal build: FAIL - {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
