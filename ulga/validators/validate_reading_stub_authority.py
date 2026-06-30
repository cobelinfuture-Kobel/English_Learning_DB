import json
import sys
from collections import Counter
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

READINGS_PATH = BASE_DIR / "ulga" / "graph" / "reading_stub_authority.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "reading_stub_summary.json"
OPPORTUNITIES_PATH = BASE_DIR / "ulga" / "graph" / "learning_opportunities.json"
THEME_NODES_PATH = BASE_DIR / "ulga" / "graph" / "theme_nodes.json"

SOURCE = "READING_STUB_AUTHORITY"
REQUIRED_FIELDS = {
    "reading_id",
    "title",
    "level",
    "theme_refs",
    "linked_opportunities",
    "focus_vocabulary",
    "focus_grammar",
    "focus_patterns",
    "estimated_word_count",
    "difficulty_profile",
    "content_status",
    "delivery_ready",
    "source",
}
REQUIRED_DIFFICULTY_FIELDS = {
    "cefr",
    "vocabulary_load",
    "grammar_load",
    "pattern_load",
    "word_count_band",
    "theme_complexity",
    "difficulty_score",
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


def theme_ids_from_nodes(theme_nodes):
    if not isinstance(theme_nodes, list):
        return set()
    return {node.get("id") for node in theme_nodes if isinstance(node, dict) and node.get("id")}


def validate_reading(record, index, opportunity_ids, theme_ids):
    missing = REQUIRED_FIELDS - set(record)
    if missing:
        return fail(f"readings[{index}] missing required fields: {sorted(missing)}")
    reading_id = record.get("reading_id")
    if not reading_id:
        return fail(f"readings[{index}] reading_id is empty")
    if not record.get("title"):
        return fail(f"{reading_id} title is empty")
    if not record.get("level"):
        return fail(f"{reading_id} level is empty")
    if record.get("content_status") != "stub":
        return fail(f"{reading_id} content_status must be stub")
    if record.get("delivery_ready") is not True:
        return fail(f"{reading_id} delivery_ready must be true")
    if record.get("source") != SOURCE:
        return fail(f"{reading_id} source must be {SOURCE}")

    linked = record.get("linked_opportunities")
    if not isinstance(linked, list) or len(linked) != 1:
        return fail(f"{reading_id} linked_opportunities must contain exactly one opportunity")
    if linked[0] not in opportunity_ids:
        return fail(f"{reading_id} links unknown opportunity: {linked[0]}")

    theme_refs = record.get("theme_refs")
    if not isinstance(theme_refs, list) or not theme_refs:
        return fail(f"{reading_id} theme_refs must be a non-empty list")
    if theme_ids:
        unknown_themes = sorted(set(theme_refs) - theme_ids)
        if unknown_themes:
            return fail(f"{reading_id} has unknown theme_refs: {unknown_themes}")

    for key in ["focus_vocabulary", "focus_grammar", "focus_patterns"]:
        if not isinstance(record.get(key), list):
            return fail(f"{reading_id} {key} must be a list")

    word_count = record.get("estimated_word_count")
    if not isinstance(word_count, int) or word_count <= 0:
        return fail(f"{reading_id} estimated_word_count must be a positive integer")

    difficulty = record.get("difficulty_profile")
    if not isinstance(difficulty, dict):
        return fail(f"{reading_id} difficulty_profile must be an object")
    missing_difficulty = REQUIRED_DIFFICULTY_FIELDS - set(difficulty)
    if missing_difficulty:
        return fail(f"{reading_id} difficulty_profile missing: {sorted(missing_difficulty)}")
    if difficulty.get("cefr") != record.get("level"):
        return fail(f"{reading_id} difficulty_profile.cefr must match level")
    for key in [
        "vocabulary_load",
        "grammar_load",
        "pattern_load",
        "theme_complexity",
        "difficulty_score",
    ]:
        value = difficulty.get(key)
        if not isinstance(value, (int, float)) or value < 0 or value > 1:
            return fail(f"{reading_id} difficulty_profile.{key} must be between 0 and 1")
    if difficulty.get("word_count_band") not in {"short", "medium", "long"}:
        return fail(f"{reading_id} difficulty_profile.word_count_band is invalid")
    return True


def validate_summary(summary, readings, opportunities):
    if not isinstance(summary, dict):
        return fail("reading_stub_summary.json must contain an object")
    if summary.get("source") != SOURCE:
        return fail(f"summary source must be {SOURCE}")
    if summary.get("status") not in {"PASS", "PASS_WITH_WARNINGS", "BLOCKED"}:
        return fail("summary status must be PASS, PASS_WITH_WARNINGS, or BLOCKED")
    if summary.get("total_readings") != len(readings):
        return fail("summary total_readings does not match readings length")

    opportunity_ids = {item.get("opportunity_id") for item in opportunities if item.get("opportunity_id")}
    linked_ids = {
        linked
        for reading in readings
        for linked in reading.get("linked_opportunities", [])
    }
    coverage_ratio = round(len(linked_ids & opportunity_ids) / len(opportunity_ids), 6) if opportunity_ids else 0.0
    if summary.get("linked_opportunities") != len(linked_ids):
        return fail("summary linked_opportunities does not match readings")
    if summary.get("coverage_ratio") != coverage_ratio:
        return fail("summary coverage_ratio does not match readings")

    by_level = Counter(reading["level"] for reading in readings)
    by_theme = Counter(theme for reading in readings for theme in reading["theme_refs"])
    status_distribution = Counter(reading["content_status"] for reading in readings)
    if summary.get("by_level") != dict(sorted(by_level.items())):
        return fail("summary by_level does not match readings")
    if summary.get("by_theme") != dict(sorted(by_theme.items())):
        return fail("summary by_theme does not match readings")
    if summary.get("content_status_distribution") != dict(sorted(status_distribution.items())):
        return fail("summary content_status_distribution does not match readings")

    planner = summary.get("planner_readiness")
    if not isinstance(planner, dict):
        return fail("summary planner_readiness must be an object")
    delivery_ready_count = sum(1 for reading in readings if reading.get("delivery_ready") is True)
    delivery_ready_ratio = round(delivery_ready_count / len(readings), 6) if readings else 0.0
    expected_planner = {
        "opportunity_count": len(opportunity_ids),
        "reading_count": len(readings),
        "coverage_ratio": coverage_ratio,
        "delivery_ready_ratio": delivery_ready_ratio,
    }
    if planner != expected_planner:
        return fail("summary planner_readiness does not match readings")
    if not isinstance(summary.get("warnings"), list):
        return fail("summary warnings must be a list")
    return True


def validate():
    print("Validating ULGA Reading Stub Authority...")
    for path in [READINGS_PATH, SUMMARY_PATH, OPPORTUNITIES_PATH]:
        if not path.exists():
            return fail(f"required file does not exist: {path}")

    readings = read_json(READINGS_PATH)
    summary = read_json(SUMMARY_PATH)
    opportunities = read_json(OPPORTUNITIES_PATH)
    theme_nodes = read_json(THEME_NODES_PATH) if THEME_NODES_PATH.exists() else []
    if readings is None or summary is None or opportunities is None or theme_nodes is None:
        return False
    if not isinstance(readings, list):
        return fail("reading_stub_authority.json must contain a list")
    if not isinstance(opportunities, list):
        return fail("learning_opportunities.json must contain a list")

    opportunity_ids = {item.get("opportunity_id") for item in opportunities if item.get("opportunity_id")}
    theme_ids = theme_ids_from_nodes(theme_nodes)
    seen_ids = set()
    linked_ids = []
    for index, record in enumerate(readings):
        if not isinstance(record, dict):
            return fail(f"readings[{index}] must be an object")
        reading_id = record.get("reading_id")
        if reading_id in seen_ids:
            return fail(f"duplicate reading_id: {reading_id}")
        seen_ids.add(reading_id)
        if not validate_reading(record, index, opportunity_ids, theme_ids):
            return False
        linked_ids.extend(record["linked_opportunities"])

    if len(readings) != len(opportunity_ids):
        return fail("reading count must equal opportunity count for S11B 1:1 mapping")
    if set(linked_ids) != opportunity_ids:
        return fail("linked opportunities must cover all opportunities exactly once")
    if len(linked_ids) != len(set(linked_ids)):
        return fail("linked opportunities must be unique in S11B")
    if not validate_summary(summary, readings, opportunities):
        return False

    print("Reading Stub Authority validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
