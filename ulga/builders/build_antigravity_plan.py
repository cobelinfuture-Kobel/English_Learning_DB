import argparse
import json
import sys
from collections import Counter
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

RANKED_OPPORTUNITIES_PATH = BASE_DIR / "ulga" / "graph" / "ranked_learning_opportunities.json"
LEARNING_OPPORTUNITIES_PATH = BASE_DIR / "ulga" / "graph" / "learning_opportunities.json"
READING_STUBS_PATH = BASE_DIR / "ulga" / "graph" / "reading_stub_authority.json"
LEARNER_STATE_PATH = BASE_DIR / "ulga" / "learner_state" / "learner_state.json"
OPPORTUNITY_RANKING_SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "opportunity_ranking_summary.json"
READING_STUB_SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "reading_stub_summary.json"

PLAN_OUT_PATH = BASE_DIR / "ulga" / "graph" / "antigravity_plan.json"
SUMMARY_OUT_PATH = BASE_DIR / "ulga" / "reports" / "antigravity_plan_summary.json"

SOURCE = "ULGA_S10E_ANTIGRAVITY_PLANNER"
CONTRACT_VERSION = "ULGA-S10E"
GENERATED_AT = "2026-06-18T00:00:00Z"
SESSION_POLICY = {
    "warm_up": 1,
    "core_learning": 2,
    "reinforcement": 1,
    "assessment": 1,
}
BLOCK_ORDER = ["warm_up", "core_learning", "reinforcement", "assessment"]
SUPPORTED_MODES = {"global", "learner"}


class PlannerError(Exception):
    pass


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


def relative_path(path):
    return path.relative_to(BASE_DIR).as_posix()


def build_reading_index(readings):
    by_opportunity = {}
    for reading in readings:
        if not isinstance(reading, dict):
            continue
        if reading.get("content_status") != "stub" or reading.get("delivery_ready") is not True:
            continue
        linked = reading.get("linked_opportunities") or []
        for opportunity_id in linked:
            by_opportunity.setdefault(opportunity_id, []).append(reading)
    for records in by_opportunity.values():
        records.sort(key=lambda item: item.get("reading_id", ""))
    return by_opportunity


def learner_ids_from_state(learner_state):
    records = learner_state.get("learner_state_records", []) if isinstance(learner_state, dict) else []
    return {record.get("learner_id") for record in records if record.get("learner_id")}


def validate_learner_mode(learner_id, learner_state, warnings):
    if not learner_id:
        raise PlannerError("learner mode requires learner_id")
    learner_ids = learner_ids_from_state(learner_state)
    if learner_id not in learner_ids:
        raise PlannerError(f"learner mode has no learner_state records for {learner_id}")
    warnings.append("learner mode uses guarded learner_state only for availability gating in S10E V1")


def reason_codes_for(ranked, opportunity):
    reasons = ["high_rank"]
    dependency_status = opportunity.get("dependency", {}).get("status")
    if dependency_status == "ready":
        reasons.append("dependency_ready")
    if ranked.get("score_breakdown", {}).get("theme_continuity_score", 0) >= 0.7:
        reasons.append("theme_continuity")
    if ranked.get("score_breakdown", {}).get("reinforcement_score", 0) > 0:
        reasons.append("reinforcement_available")
    if ranked.get("score_breakdown", {}).get("frequency_score", 0) >= 0.7:
        reasons.append("high_frequency")
    if ranked.get("score_breakdown", {}).get("pattern_utility_score", 0) >= 0.7:
        reasons.append("pattern_high_utility")
    reasons.append("reading_available")
    return reasons


def rejection(reason, ranked, hard_block=True):
    return {
        "opportunity_id": ranked.get("opportunity_id"),
        "rank": ranked.get("rank"),
        "candidate_score": ranked.get("candidate_score"),
        "rejection_reasons": [reason],
        "hard_block": hard_block,
    }


def eligible_candidate(ranked_item, opportunities_by_id, reading_by_opportunity, used_opportunities, used_readings):
    opportunity_id = ranked_item.get("opportunity_id")
    opportunity = opportunities_by_id.get(opportunity_id)
    if not opportunity:
        return None, None, "metadata_join_failed"
    if opportunity_id in used_opportunities:
        return None, None, "duplicate_opportunity"
    if opportunity.get("dependency", {}).get("status") != "ready":
        return None, None, "unknown_dependency_blocked"
    readings = reading_by_opportunity.get(opportunity_id, [])
    if not readings:
        return None, None, "reading_missing"
    reading = next((item for item in readings if item.get("reading_id") not in used_readings), None)
    if not reading:
        return None, None, "duplicate_reading_blocked"
    if reading.get("level") != opportunity.get("level"):
        return None, None, "level_mismatch"
    return opportunity, reading, None


def make_selected_item(ranked_item, opportunity, reading):
    return {
        "opportunity_id": ranked_item["opportunity_id"],
        "reading_id": reading["reading_id"],
        "source_rank": ranked_item["rank"],
        "source_candidate_score": ranked_item["candidate_score"],
        "level": opportunity.get("level"),
        "theme_refs": opportunity.get("theme_refs", []),
        "reason_codes": reason_codes_for(ranked_item, opportunity),
    }


def select_candidates(ranked, opportunities_by_id, reading_by_opportunity, target_count):
    selected = []
    rejected = []
    used_opportunities = set()
    used_readings = set()
    rejection_seen = set()

    def append_rejection_once(reason_code, ranked_item):
        key = (ranked_item.get("opportunity_id"), reason_code)
        if key not in rejection_seen:
            rejected.append(rejection(reason_code, ranked_item))
            rejection_seen.add(key)

    def take_first(predicate):
        for ranked_item in ranked:
            if not predicate(ranked_item):
                continue
            opportunity, reading, reason = eligible_candidate(
                ranked_item,
                opportunities_by_id,
                reading_by_opportunity,
                used_opportunities,
                used_readings,
            )
            if reason:
                append_rejection_once(reason, ranked_item)
                continue
            selected_item = make_selected_item(ranked_item, opportunity, reading)
            selected.append(selected_item)
            used_opportunities.add(selected_item["opportunity_id"])
            used_readings.add(selected_item["reading_id"])
            return selected_item
        return None

    # Warm-up + core use strongest ranked eligible candidates.
    for _ in range(SESSION_POLICY["warm_up"] + SESSION_POLICY["core_learning"]):
        if not take_first(lambda _ranked: True):
            break

    reinforcement_selected = take_first(
        lambda ranked_item: ranked_item.get("score_breakdown", {}).get("reinforcement_score", 0) > 0
    )

    # Assessment slot uses the strongest remaining eligible candidate in V1.
    take_first(lambda _ranked: True)

    while len(selected) < target_count:
        if not take_first(lambda _ranked: True):
            break

    for item in selected:
        item["planner_role_quality"] = (
            "reinforcement_evidence_available"
            if item is reinforcement_selected
            else "ranked_eligible"
        )

    return selected, rejected


def build_session(selected):
    blocks = []
    cursor = 0
    for block_type in BLOCK_ORDER:
        size = SESSION_POLICY[block_type]
        block_selected = selected[cursor:cursor + size]
        cursor += size
        blocks.append(
            {
                "block_type": block_type,
                "opportunity_ids": [item["opportunity_id"] for item in block_selected],
            }
        )
        for item in block_selected:
            item["assigned_block"] = block_type
    return {
        "session_id": "SESSION_GLOBAL_000001",
        "planner_mode": "global",
        "learner_id": None,
        "blocks": blocks,
    }


def build_summary(plan, selected, rejected, warnings):
    theme_distribution = Counter(theme for item in selected for theme in item.get("theme_refs", []))
    level_distribution = Counter(item.get("level") for item in selected)
    delivered = sum(1 for item in selected if item.get("reading_id"))
    reading_delivery_rate = round(delivered / len(selected), 6) if selected else 0.0
    dependency_block_count = sum(
        1 for item in rejected for reason in item.get("rejection_reasons", []) if reason == "unknown_dependency_blocked"
    )
    status = "PASS" if selected and reading_delivery_rate == 1.0 and not warnings else "PASS_WITH_WARNINGS"
    if not selected:
        status = "BLOCKED"
    return {
        "status": status,
        "contract_version": CONTRACT_VERSION,
        "source": SOURCE,
        "session_count": len(plan.get("sessions", [])),
        "selected_opportunities": len(selected),
        "reading_delivery_rate": reading_delivery_rate,
        "theme_distribution": dict(sorted(theme_distribution.items())),
        "level_distribution": dict(sorted(level_distribution.items())),
        "dependency_block_count": dependency_block_count,
        "rejected_candidate_count": len(rejected),
        "warnings": warnings,
    }


def blocked_payload(mode, learner_id, reason):
    plan = {
        "plan_id": "PLAN_S10E_000001",
        "contract_version": CONTRACT_VERSION,
        "planner_mode": mode,
        "learner_id": learner_id,
        "generated_at": GENERATED_AT,
        "generated_from": {
            "ranked_opportunities": relative_path(RANKED_OPPORTUNITIES_PATH),
            "learning_opportunities": relative_path(LEARNING_OPPORTUNITIES_PATH),
            "reading_stub_authority": relative_path(READING_STUBS_PATH),
            "learner_state": relative_path(LEARNER_STATE_PATH),
        },
        "sessions": [],
        "selected_opportunities": [],
        "rejected_candidates": [],
        "explanations": [{"reason_codes": [reason]}],
        "source": SOURCE,
    }
    summary = {
        "status": "BLOCKED",
        "contract_version": CONTRACT_VERSION,
        "source": SOURCE,
        "session_count": 0,
        "selected_opportunities": 0,
        "reading_delivery_rate": 0.0,
        "theme_distribution": {},
        "level_distribution": {},
        "dependency_block_count": 0,
        "rejected_candidate_count": 0,
        "warnings": [reason],
    }
    return plan, summary


def build_antigravity_plan(planner_mode="global", learner_id=None, output_path=PLAN_OUT_PATH, summary_path=SUMMARY_OUT_PATH):
    if planner_mode not in SUPPORTED_MODES:
        plan, summary = blocked_payload(planner_mode, learner_id, "unsupported_planner_mode")
        write_json(output_path, plan)
        write_json(summary_path, summary)
        return summary

    warnings = []
    ranked = read_json_optional(RANKED_OPPORTUNITIES_PATH, [])
    opportunities = read_json_optional(LEARNING_OPPORTUNITIES_PATH, [])
    readings = read_json_optional(READING_STUBS_PATH, [])
    learner_state = read_json_optional(LEARNER_STATE_PATH, {})
    read_json_optional(OPPORTUNITY_RANKING_SUMMARY_PATH, {})
    read_json_optional(READING_STUB_SUMMARY_PATH, {})

    if planner_mode == "learner":
        try:
            validate_learner_mode(learner_id, learner_state, warnings)
        except PlannerError as exc:
            plan, summary = blocked_payload(planner_mode, learner_id, str(exc))
            write_json(output_path, plan)
            write_json(summary_path, summary)
            print(f"Antigravity Planner build: {summary['status']}")
            print(f"Warnings: {len(summary['warnings'])}")
            return summary

    if not isinstance(ranked, list):
        warnings.append("ranked_learning_opportunities.json was not a list")
        ranked = []
    if not isinstance(opportunities, list):
        warnings.append("learning_opportunities.json was not a list")
        opportunities = []
    if not isinstance(readings, list):
        warnings.append("reading_stub_authority.json was not a list")
        readings = []

    opportunities_by_id = {
        item["opportunity_id"]: item
        for item in opportunities
        if isinstance(item, dict) and item.get("opportunity_id")
    }
    reading_by_opportunity = build_reading_index(readings)
    target_count = sum(SESSION_POLICY.values())
    selected, rejected = select_candidates(ranked, opportunities_by_id, reading_by_opportunity, target_count)
    if len(selected) < target_count:
        warnings.append(f"selected only {len(selected)} of {target_count} required opportunities")
    if selected and not any(item.get("planner_role_quality") == "reinforcement_evidence_available" for item in selected):
        warnings.append("no eligible opportunity with reinforcement_score > 0; reinforcement block is structural only")

    session = build_session(selected)
    session["planner_mode"] = planner_mode
    session["learner_id"] = learner_id if planner_mode == "learner" else None
    plan = {
        "plan_id": "PLAN_S10E_000001",
        "contract_version": CONTRACT_VERSION,
        "planner_mode": planner_mode,
        "learner_id": learner_id if planner_mode == "learner" else None,
        "generated_at": GENERATED_AT,
        "generated_from": {
            "ranked_opportunities": relative_path(RANKED_OPPORTUNITIES_PATH),
            "learning_opportunities": relative_path(LEARNING_OPPORTUNITIES_PATH),
            "reading_stub_authority": relative_path(READING_STUBS_PATH),
            "learner_state": relative_path(LEARNER_STATE_PATH) if planner_mode == "learner" else None,
        },
        "sessions": [session] if selected else [],
        "selected_opportunities": selected,
        "rejected_candidates": rejected,
        "explanations": [
            {
                "opportunity_id": item["opportunity_id"],
                "reason_codes": item["reason_codes"],
            }
            for item in selected
        ],
        "source": SOURCE,
    }
    summary = build_summary(plan, selected, rejected, warnings)
    write_json(output_path, plan)
    write_json(summary_path, summary)
    print(f"Antigravity Planner build: {summary['status']}")
    print(f"Sessions: {summary['session_count']}")
    print(f"Selected opportunities: {summary['selected_opportunities']}")
    print(f"Reading delivery rate: {summary['reading_delivery_rate']}")
    print(f"Warnings: {len(warnings)}")
    return summary


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Build ULGA S10E Antigravity Planner output.")
    parser.add_argument("--planner-mode", default="global", choices=sorted(SUPPORTED_MODES))
    parser.add_argument("--learner-id", default=None)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        build_antigravity_plan(planner_mode=args.planner_mode, learner_id=args.learner_id)
    except Exception as exc:
        print(f"Antigravity Planner build: FAIL - {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
