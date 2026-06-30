import json
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

PLAN_PATH = BASE_DIR / "ulga" / "graph" / "antigravity_plan.json"
REINFORCEMENT_SIGNAL_PATH = BASE_DIR / "ulga" / "graph" / "reinforcement_signal.json"
RANKED_OPPORTUNITIES_PATH = BASE_DIR / "ulga" / "graph" / "ranked_learning_opportunities.json"
LEARNING_OPPORTUNITIES_PATH = BASE_DIR / "ulga" / "graph" / "learning_opportunities.json"
READING_STUBS_PATH = BASE_DIR / "ulga" / "graph" / "reading_stub_authority.json"

PLAN_SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "antigravity_plan_summary.json"
REINFORCEMENT_SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "reinforcement_signal_summary.json"
RANKING_SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "opportunity_ranking_summary.json"
READING_STUB_SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "reading_stub_summary.json"

AUDIT_OUT_PATH = BASE_DIR / "ulga" / "reports" / "antigravity_planner_reinforcement_audit.json"

CONTRACT_VERSION = "ULGA-S10H"
REINFORCEMENT_SOURCE = "ULGA_S10G_REINFORCEMENT_SIGNAL"
REINFORCEMENT_REASON_CODES = {
    "reinforcement_available",
    "reinforcement_evidence_available",
    "dependency_reinforcement",
    "opportunity_reinforces_nodes",
    "review_due",
    "low_mastery",
    "time_decay",
    "theme_revisit",
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


def block_opportunity_ids(plan, block_type):
    ids = []
    for session in plan.get("sessions", []) if isinstance(plan, dict) else []:
        for block in session.get("blocks", []) if isinstance(session, dict) else []:
            if block.get("block_type") == block_type:
                ids.extend(block.get("opportunity_ids", []) or [])
    return ids


def selected_index(plan):
    selected = plan.get("selected_opportunities", []) if isinstance(plan, dict) else []
    return {
        item["opportunity_id"]: item
        for item in selected
        if isinstance(item, dict) and item.get("opportunity_id")
    }


def signal_index(signal_payload):
    signals = signal_payload.get("signals", []) if isinstance(signal_payload, dict) else []
    return {
        item["target_id"]: item
        for item in signals
        if isinstance(item, dict) and item.get("target_id")
    }


def planner_claims_reinforcement(selected_item):
    if not selected_item:
        return False
    if selected_item.get("planner_role_quality") == "reinforcement_evidence_available":
        return True
    reason_codes = set(selected_item.get("reason_codes", []) or [])
    return bool(reason_codes & REINFORCEMENT_REASON_CODES)


def signal_presence(signal_payload, signal_summary, opportunities):
    signals = signal_payload.get("signals", []) if isinstance(signal_payload, dict) else []
    return {
        "reinforcement_signal_exists": REINFORCEMENT_SIGNAL_PATH.exists(),
        "total_signals": signal_summary.get("total_signals", len(signals)),
        "learning_opportunity_count": len(opportunities) if isinstance(opportunities, list) else 0,
        "signal_count_matches_learning_opportunities": (
            signal_summary.get("total_signals", len(signals)) == len(opportunities)
            if isinstance(opportunities, list)
            else False
        ),
        "signals_with_score_gt_zero": signal_summary.get(
            "signals_with_score_gt_zero",
            sum(1 for signal in signals if signal.get("signal_score", 0) > 0),
        ),
        "planner_eligible_count": signal_summary.get(
            "planner_eligible_count",
            sum(1 for signal in signals if signal.get("planner_eligible") is True),
        ),
        "eligible_with_score_gt_zero": signal_summary.get(
            "eligible_with_score_gt_zero",
            sum(
                1
                for signal in signals
                if signal.get("planner_eligible") is True and signal.get("signal_score", 0) > 0
            ),
        ),
        "dependency_unknown_blocked_count": signal_summary.get(
            "dependency_unknown_blocked_count",
            sum(1 for signal in signals if signal.get("dependency", {}).get("status") in {"unknown", "blocked"}),
        ),
    }


def planner_behavior(plan, signals_by_target):
    reinforcement_ids = block_opportunity_ids(plan, "reinforcement")
    selected_by_id = selected_index(plan)
    selected_block_items = [selected_by_id.get(opportunity_id) for opportunity_id in reinforcement_ids]
    selected_existing = [item for item in selected_block_items if item]
    selected_signals = [
        signals_by_target.get(item["opportunity_id"])
        for item in selected_existing
        if signals_by_target.get(item["opportunity_id"])
    ]
    claimed_items = [item for item in selected_existing if planner_claims_reinforcement(item)]
    claimed_eligible = [
        item
        for item in claimed_items
        if signals_by_target.get(item["opportunity_id"], {}).get("planner_eligible") is True
    ]
    selected_eligible = [signal for signal in selected_signals if signal.get("planner_eligible") is True]
    selected_positive = [signal for signal in selected_signals if signal.get("signal_score", 0) > 0]
    selected_ineligible_claims = [
        {
            "opportunity_id": item["opportunity_id"],
            "planner_role_quality": item.get("planner_role_quality"),
            "reason_codes": item.get("reason_codes", []),
            "signal_planner_eligible": signals_by_target.get(item["opportunity_id"], {}).get("planner_eligible"),
            "signal_score": signals_by_target.get(item["opportunity_id"], {}).get("signal_score"),
            "ineligible_reason": signals_by_target.get(item["opportunity_id"], {}).get("ineligible_reason"),
        }
        for item in claimed_items
        if signals_by_target.get(item["opportunity_id"], {}).get("planner_eligible") is not True
    ]
    missing_signal_claims = [
        item["opportunity_id"]
        for item in claimed_items
        if item["opportunity_id"] not in signals_by_target
    ]
    return {
        "reinforcement_block_exists": bool(reinforcement_ids),
        "reinforcement_block_opportunity_ids": reinforcement_ids,
        "reinforcement_block_selected_count": len(selected_existing),
        "selected_reinforcement_count": len(claimed_items),
        "selected_eligible_reinforcement_count": len(claimed_eligible),
        "selected_block_signal_count": len(selected_signals),
        "selected_block_eligible_signal_count": len(selected_eligible),
        "selected_block_positive_signal_count": len(selected_positive),
        "structural_fallback_detected": bool(reinforcement_ids) and not claimed_items,
        "selected_ineligible_reinforcement_claims": selected_ineligible_claims,
        "missing_reinforcement_signal_claims": missing_signal_claims,
    }


def diagnose(presence, behavior):
    blockers = []
    warnings = []
    signal_failure = False
    planner_failure = False
    primary_cause = None

    if not presence["reinforcement_signal_exists"]:
        blockers.append("reinforcement_signal_missing")
        signal_failure = True
    if not presence["signal_count_matches_learning_opportunities"]:
        blockers.append("signal_count_learning_opportunity_mismatch")
        signal_failure = True
    if not behavior["reinforcement_block_exists"]:
        blockers.append("reinforcement_block_missing")
        planner_failure = True
    if behavior["missing_reinforcement_signal_claims"]:
        blockers.append("planner_claimed_reinforcement_without_signal")
        planner_failure = True
    if behavior["selected_ineligible_reinforcement_claims"]:
        blockers.append("planner_claimed_ineligible_reinforcement")
        planner_failure = True

    if presence["eligible_with_score_gt_zero"] == 0:
        if presence["dependency_unknown_blocked_count"] >= presence["signals_with_score_gt_zero"] > 0:
            primary_cause = "UPSTREAM_DEPENDENCY_READINESS_GAP"
            warnings.append("no planner-eligible reinforcement signals; positive signals are dependency unknown or blocked")
        else:
            primary_cause = "NO_ELIGIBLE_REINFORCEMENT_SIGNAL"
            warnings.append("no planner-eligible reinforcement signals were available")
        if behavior["structural_fallback_detected"]:
            warnings.append("planner used structural reinforcement block fallback without claiming reinforcement evidence")
    elif behavior["selected_eligible_reinforcement_count"] > 0:
        primary_cause = None
    else:
        primary_cause = "PLANNER_REINFORCEMENT_NOT_CONSUMED"
        warnings.append("eligible reinforcement signals exist but planner did not select one")

    if signal_failure:
        primary_cause = primary_cause or "SIGNAL_FAILURE"
    if planner_failure:
        primary_cause = primary_cause or "PLANNER_FAILURE"

    return {
        "diagnosis": {
            "primary_cause": primary_cause,
            "planner_failure": planner_failure,
            "signal_failure": signal_failure,
        },
        "blockers": blockers,
        "warnings": warnings,
    }


def status_for(presence, behavior, blockers):
    if blockers:
        return "BLOCKER"
    if presence["eligible_with_score_gt_zero"] > 0 and behavior["selected_eligible_reinforcement_count"] > 0:
        return "PASS"
    return "PASS_WITH_WARNINGS"


def run_audit(report_path=AUDIT_OUT_PATH):
    plan = read_json_optional(PLAN_PATH, {})
    signal_payload = read_json_optional(REINFORCEMENT_SIGNAL_PATH, {})
    signal_summary = read_json_optional(REINFORCEMENT_SUMMARY_PATH, {})
    opportunities = read_json_optional(LEARNING_OPPORTUNITIES_PATH, [])
    read_json_optional(RANKED_OPPORTUNITIES_PATH, [])
    read_json_optional(READING_STUBS_PATH, [])
    read_json_optional(PLAN_SUMMARY_PATH, {})
    read_json_optional(RANKING_SUMMARY_PATH, {})
    read_json_optional(READING_STUB_SUMMARY_PATH, {})

    signals_by_target = signal_index(signal_payload)
    presence = signal_presence(signal_payload, signal_summary, opportunities)
    behavior = planner_behavior(plan, signals_by_target)
    diagnosis_result = diagnose(presence, behavior)
    status = status_for(presence, behavior, diagnosis_result["blockers"])

    report = {
        "contract_version": CONTRACT_VERSION,
        "status": status,
        "signal_presence": presence,
        "planner_behavior": behavior,
        "diagnosis": diagnosis_result["diagnosis"],
        "blockers": diagnosis_result["blockers"],
        "warnings": diagnosis_result["warnings"],
        "inputs_read": [
            "ulga/graph/antigravity_plan.json",
            "ulga/graph/reinforcement_signal.json",
            "ulga/graph/ranked_learning_opportunities.json",
            "ulga/graph/learning_opportunities.json",
            "ulga/graph/reading_stub_authority.json",
            "ulga/reports/antigravity_plan_summary.json",
            "ulga/reports/reinforcement_signal_summary.json",
            "ulga/reports/opportunity_ranking_summary.json",
            "ulga/reports/reading_stub_summary.json",
        ],
        "source": "ULGA_S10H_PLANNER_REAUDIT_WITH_REINFORCEMENT_SIGNAL",
    }
    write_json(report_path, report)
    return report


def main():
    try:
        report = run_audit()
    except Exception as exc:
        print(f"Antigravity Planner Reinforcement audit: FAIL - {exc}")
        return 1
    print(f"Antigravity Planner Reinforcement audit: {report['status']}")
    print(f"Signals: {report['signal_presence']['total_signals']}")
    print(f"Eligible positive signals: {report['signal_presence']['eligible_with_score_gt_zero']}")
    print(f"Selected eligible reinforcement: {report['planner_behavior']['selected_eligible_reinforcement_count']}")
    print(f"Primary cause: {report['diagnosis']['primary_cause']}")
    print(f"Blockers: {len(report['blockers'])}")
    return 0 if report["status"] != "BLOCKER" else 1


if __name__ == "__main__":
    sys.exit(main())
