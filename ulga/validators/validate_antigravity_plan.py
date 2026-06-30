import json
import sys
from collections import Counter
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

PLAN_PATH = BASE_DIR / "ulga" / "graph" / "antigravity_plan.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "antigravity_plan_summary.json"
OPPORTUNITIES_PATH = BASE_DIR / "ulga" / "graph" / "learning_opportunities.json"
READINGS_PATH = BASE_DIR / "ulga" / "graph" / "reading_stub_authority.json"

SOURCE = "ULGA_S10E_ANTIGRAVITY_PLANNER"
VALID_MODES = {"global", "learner"}
BLOCK_TYPES = ["warm_up", "core_learning", "reinforcement", "assessment"]


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


def validate():
    print("Validating ULGA Antigravity Plan...")
    for path in [PLAN_PATH, SUMMARY_PATH, OPPORTUNITIES_PATH, READINGS_PATH]:
        if not path.exists():
            return fail(f"required file does not exist: {path}")

    plan = read_json(PLAN_PATH)
    summary = read_json(SUMMARY_PATH)
    opportunities = read_json(OPPORTUNITIES_PATH)
    readings = read_json(READINGS_PATH)
    if plan is None or summary is None or opportunities is None or readings is None:
        return False
    if not isinstance(plan, dict):
        return fail("antigravity_plan.json must contain an object")
    if not isinstance(summary, dict):
        return fail("antigravity_plan_summary.json must contain an object")
    if not isinstance(opportunities, list):
        return fail("learning_opportunities.json must contain a list")
    if not isinstance(readings, list):
        return fail("reading_stub_authority.json must contain a list")

    if plan.get("source") != SOURCE:
        return fail(f"plan source must be {SOURCE}")
    if plan.get("planner_mode") not in VALID_MODES:
        return fail("planner_mode must be global or learner")
    if not plan.get("plan_id"):
        return fail("plan_id is required")
    if not plan.get("generated_at"):
        return fail("generated_at is required")

    opportunity_ids = {item.get("opportunity_id") for item in opportunities if isinstance(item, dict)}
    opportunity_ids.discard(None)
    reading_ids = {item.get("reading_id") for item in readings if isinstance(item, dict)}
    reading_ids.discard(None)
    opportunity_by_id = {item.get("opportunity_id"): item for item in opportunities if isinstance(item, dict)}

    selected = plan.get("selected_opportunities")
    if not isinstance(selected, list):
        return fail("selected_opportunities must be a list")
    selected_ids = []
    selected_reading_ids = []
    for item in selected:
        if not isinstance(item, dict):
            return fail("selected_opportunities entries must be objects")
        for key in ["opportunity_id", "reading_id", "source_rank", "source_candidate_score", "reason_codes"]:
            if key not in item:
                return fail(f"selected opportunity missing {key}")
        opportunity_id = item["opportunity_id"]
        reading_id = item["reading_id"]
        if opportunity_id not in opportunity_ids:
            return fail(f"selected unknown opportunity_id: {opportunity_id}")
        if reading_id not in reading_ids:
            return fail(f"selected unknown reading_id: {reading_id}")
        if not isinstance(item["reason_codes"], list) or not item["reason_codes"]:
            return fail(f"{opportunity_id} reason_codes must be non-empty")
        if "reading_available" not in item["reason_codes"]:
            return fail(f"{opportunity_id} must include reading_available reason")
        selected_ids.append(opportunity_id)
        selected_reading_ids.append(reading_id)

    if len(selected_ids) != len(set(selected_ids)):
        return fail("selected opportunities must be unique")
    if len(selected_reading_ids) != len(set(selected_reading_ids)):
        return fail("selected reading assets must be unique")

    sessions = plan.get("sessions")
    if not isinstance(sessions, list):
        return fail("sessions must be a list")
    session_ids = [session.get("session_id") for session in sessions if isinstance(session, dict)]
    if len(session_ids) != len(set(session_ids)):
        return fail("session ids must be unique")
    for session in sessions:
        if not isinstance(session, dict):
            return fail("sessions entries must be objects")
        if session.get("planner_mode") != plan.get("planner_mode"):
            return fail("session planner_mode must match plan")
        blocks = session.get("blocks")
        if not isinstance(blocks, list):
            return fail("session blocks must be a list")
        if [block.get("block_type") for block in blocks] != BLOCK_TYPES:
            return fail("session block order is invalid")
        block_ids = []
        for block in blocks:
            ids = block.get("opportunity_ids")
            if not isinstance(ids, list):
                return fail("block opportunity_ids must be a list")
            for opportunity_id in ids:
                if opportunity_id not in selected_ids:
                    return fail(f"block references unselected opportunity: {opportunity_id}")
            block_ids.extend(ids)
        if block_ids != selected_ids:
            return fail("block opportunity order must match selected opportunities")

    explanations = plan.get("explanations")
    if not isinstance(explanations, list):
        return fail("explanations must be a list")
    explanation_ids = [item.get("opportunity_id") for item in explanations]
    if explanation_ids != selected_ids:
        return fail("explanations must match selected opportunities")
    for item in explanations:
        if not isinstance(item.get("reason_codes"), list) or not item["reason_codes"]:
            return fail("explanation reason_codes must be non-empty")

    if summary.get("source") != SOURCE:
        return fail(f"summary source must be {SOURCE}")
    if summary.get("status") not in {"PASS", "PASS_WITH_WARNINGS", "BLOCKED"}:
        return fail("summary status is invalid")
    if summary.get("session_count") != len(sessions):
        return fail("summary session_count mismatch")
    if summary.get("selected_opportunities") != len(selected):
        return fail("summary selected_opportunities mismatch")
    delivery_rate = round(len([item for item in selected if item.get("reading_id")]) / len(selected), 6) if selected else 0.0
    if summary.get("reading_delivery_rate") != delivery_rate:
        return fail("summary reading_delivery_rate mismatch")
    theme_distribution = Counter(theme for item in selected for theme in item.get("theme_refs", []))
    level_distribution = Counter(opportunity_by_id[item["opportunity_id"]].get("level") for item in selected)
    if summary.get("theme_distribution") != dict(sorted(theme_distribution.items())):
        return fail("summary theme_distribution mismatch")
    if summary.get("level_distribution") != dict(sorted(level_distribution.items())):
        return fail("summary level_distribution mismatch")
    if not isinstance(summary.get("warnings"), list):
        return fail("summary warnings must be a list")

    print("Antigravity Plan validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
