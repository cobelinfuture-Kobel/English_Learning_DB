import json
import sys
from collections import Counter
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

BRIDGE_PATH = BASE_DIR / "ulga" / "graph" / "exposure_mapping_bridge.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "exposure_mapping_bridge_summary.json"
LEARNER_STATE_PATH = BASE_DIR / "ulga" / "learner_state" / "learner_state.json"
LEARNING_OPPORTUNITIES_PATH = BASE_DIR / "ulga" / "graph" / "learning_opportunities.json"

SOURCE = "ULGA_S9Z1_EXPOSURE_MAPPING_BRIDGE"
VALID_BRIDGE_TYPES = {
    "direct_focus_node_bridge",
    "grammar_bridge",
    "vocabulary_bridge",
    "theme_bridge",
    "dependency_parent_bridge",
}
VALID_DEPENDENCY_STATUSES = {"ready", "blocked", "unknown"}


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


def validate_bridge(bridge, index, learner_ids, source_refs, opportunity_ids):
    required = {
        "bridge_id",
        "learner_id",
        "source_ref",
        "source_node_type",
        "matched_ref",
        "opportunity_id",
        "bridge_type",
        "confidence",
        "prior_exposure",
        "planner_safe",
        "dependency_status",
        "reading_ready",
        "warnings",
        "source",
    }
    missing = required - set(bridge)
    if missing:
        return fail(f"bridges[{index}] missing required fields: {sorted(missing)}")
    bridge_id = bridge["bridge_id"]
    if bridge["learner_id"] not in learner_ids:
        return fail(f"{bridge_id} learner_id does not exist")
    if bridge["source_ref"] not in source_refs:
        return fail(f"{bridge_id} source_ref does not exist")
    if bridge["opportunity_id"] not in opportunity_ids:
        return fail(f"{bridge_id} opportunity does not exist")
    if bridge["bridge_type"] not in VALID_BRIDGE_TYPES:
        return fail(f"{bridge_id} bridge_type invalid")
    if not in_score_range(bridge["confidence"]):
        return fail(f"{bridge_id} confidence out of range")
    if not isinstance(bridge["prior_exposure"], bool) or bridge["prior_exposure"] is not True:
        return fail(f"{bridge_id} prior_exposure must be true")
    if not isinstance(bridge["planner_safe"], bool):
        return fail(f"{bridge_id} planner_safe must be boolean")
    if bridge["dependency_status"] not in VALID_DEPENDENCY_STATUSES:
        return fail(f"{bridge_id} dependency_status invalid")
    if not isinstance(bridge["reading_ready"], bool):
        return fail(f"{bridge_id} reading_ready must be boolean")
    if bridge["bridge_type"] == "theme_bridge" and bridge["planner_safe"] is True:
        return fail(f"{bridge_id} theme_bridge must not be planner_safe")
    if bridge["dependency_status"] != "ready" and bridge["planner_safe"] is True:
        return fail(f"{bridge_id} dependency blocked/unknown bridge must not be planner_safe")
    if bridge["reading_ready"] is not True and bridge["planner_safe"] is True:
        return fail(f"{bridge_id} reading-missing bridge must not be planner_safe")
    if not isinstance(bridge["warnings"], list):
        return fail(f"{bridge_id} warnings must be a list")
    if bridge["source"] != SOURCE:
        return fail(f"{bridge_id} source must be {SOURCE}")
    return True


def validate():
    print("Validating ULGA Exposure Mapping Bridge...")
    for path in [BRIDGE_PATH, SUMMARY_PATH, LEARNER_STATE_PATH, LEARNING_OPPORTUNITIES_PATH]:
        if not path.exists():
            return fail(f"required file does not exist: {path}")
    payload = read_json(BRIDGE_PATH)
    summary = read_json(SUMMARY_PATH)
    learner_state = read_json(LEARNER_STATE_PATH)
    opportunities = read_json(LEARNING_OPPORTUNITIES_PATH)
    if payload is None or summary is None or learner_state is None or opportunities is None:
        return False
    if not isinstance(payload, dict):
        return fail("exposure_mapping_bridge.json must contain an object")
    if not isinstance(summary, dict):
        return fail("exposure_mapping_bridge_summary.json must contain an object")
    if not isinstance(opportunities, list):
        return fail("learning_opportunities.json must contain a list")
    metadata = payload.get("metadata")
    bridges = payload.get("bridges")
    if not isinstance(metadata, dict):
        return fail("metadata must be an object")
    if metadata.get("source") != SOURCE:
        return fail(f"metadata source must be {SOURCE}")
    if not isinstance(bridges, list):
        return fail("bridges must be a list")

    records = [item for item in learner_state.get("learner_state_records", []) if isinstance(item, dict)]
    learner_ids = {item.get("learner_id") for item in records if item.get("learner_id")}
    source_refs = {item.get("node_id") for item in records if item.get("node_id")}
    opportunity_ids = {item.get("opportunity_id") for item in opportunities if isinstance(item, dict)}
    opportunity_ids.discard(None)

    seen_ids = set()
    seen_keys = set()
    for index, bridge in enumerate(bridges):
        if not isinstance(bridge, dict):
            return fail(f"bridges[{index}] must be an object")
        bridge_id = bridge.get("bridge_id")
        if not bridge_id:
            return fail(f"bridges[{index}] missing bridge_id")
        if bridge_id in seen_ids:
            return fail(f"duplicate bridge_id: {bridge_id}")
        seen_ids.add(bridge_id)
        key = (
            bridge.get("learner_id"),
            bridge.get("source_ref"),
            bridge.get("opportunity_id"),
            bridge.get("bridge_type"),
        )
        if key in seen_keys:
            return fail(f"duplicate bridge tuple: {key}")
        seen_keys.add(key)
        if not validate_bridge(bridge, index, learner_ids, source_refs, opportunity_ids):
            return False

    bridge_distribution = Counter(bridge["bridge_type"] for bridge in bridges)
    if summary.get("status") not in {"PASS", "PASS_WITH_WARNINGS", "BLOCKED"}:
        return fail("summary status invalid")
    if summary.get("bridge_count") != len(bridges):
        return fail("summary bridge_count mismatch")
    if summary.get("bridge_distribution") != dict(sorted(bridge_distribution.items())):
        return fail("summary bridge_distribution mismatch")
    if summary.get("planner_safe_count") != sum(1 for bridge in bridges if bridge["planner_safe"]):
        return fail("summary planner_safe_count mismatch")
    if not isinstance(summary.get("warnings"), list):
        return fail("summary warnings must be a list")

    print("Exposure Mapping Bridge validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
