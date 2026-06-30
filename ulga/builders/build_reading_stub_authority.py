import json
from collections import Counter
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

LEARNING_OPPORTUNITIES_PATH = BASE_DIR / "ulga" / "graph" / "learning_opportunities.json"
RANKED_OPPORTUNITIES_PATH = BASE_DIR / "ulga" / "graph" / "ranked_learning_opportunities.json"
THEME_NODES_PATH = BASE_DIR / "ulga" / "graph" / "theme_nodes.json"
VOCABULARY_NODES_PATH = BASE_DIR / "ulga" / "graph" / "vocabulary_nodes.json"
SENTENCE_PATTERNS_PATH = BASE_DIR / "ulga" / "graph" / "sentence_patterns.json"
S11A_DESIGN_PATH = BASE_DIR / "docs" / "ulga" / "ULGA_S11A_READING_AUTHORITY_DESIGN_SCAN.md"

READINGS_OUT_PATH = BASE_DIR / "ulga" / "graph" / "reading_stub_authority.json"
SUMMARY_OUT_PATH = BASE_DIR / "ulga" / "reports" / "reading_stub_summary.json"

SOURCE = "READING_STUB_AUTHORITY"
CONTRACT_VERSION = "ULGA-S11B"
CEFR_ORDER = ["A1", "A2", "B1", "B2", "C1", "C2"]
WORD_COUNT_BY_LEVEL = {
    "A1": 80,
    "A2": 130,
    "B1": 220,
    "B2": 320,
    "C1": 420,
    "C2": 520,
}


def read_json_optional(path, default):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, sort_keys=False)
        f.write("\n")


def relative_path(path):
    return path.relative_to(BASE_DIR).as_posix()


def unique_sorted(values):
    return sorted({value for value in values if value})


def safe_level(level):
    return level if level in CEFR_ORDER else "UNK"


def reading_id_for(index, level):
    return f"RA_STUB_{safe_level(level)}_{index:06d}"


def title_for(opportunity):
    level = safe_level(opportunity.get("level"))
    themes = opportunity.get("theme_refs") or []
    theme_label = "General"
    if themes:
        theme_label = themes[0].split(":", 1)[-1].replace("_", " ").title()
        level_prefix = f"{level} "
        if theme_label.startswith(level_prefix):
            theme_label = theme_label[len(level_prefix):]
    return f"Stub Reading {level} {theme_label}"


def word_count_for(level):
    return WORD_COUNT_BY_LEVEL.get(level, 180)


def difficulty_profile_for(opportunity):
    level = safe_level(opportunity.get("level"))
    focus_nodes = opportunity.get("focus_nodes", {})
    vocabulary_count = len(focus_nodes.get("vocabulary", []) or [])
    grammar_count = len(focus_nodes.get("grammar", []) or [])
    pattern_count = len(focus_nodes.get("pattern", []) or [])
    theme_count = len(opportunity.get("theme_refs", []) or [])
    word_count = word_count_for(level)
    difficulty_score = min(
        1.0,
        0.10
        + 0.04 * vocabulary_count
        + 0.05 * grammar_count
        + 0.05 * pattern_count
        + 0.03 * max(theme_count - 1, 0),
    )
    if word_count <= 120:
        word_count_band = "short"
    elif word_count <= 250:
        word_count_band = "medium"
    else:
        word_count_band = "long"
    return {
        "cefr": level,
        "vocabulary_load": round(min(1.0, vocabulary_count / 10.0), 6),
        "grammar_load": round(min(1.0, grammar_count / 5.0), 6),
        "pattern_load": round(min(1.0, pattern_count / 3.0), 6),
        "word_count_band": word_count_band,
        "theme_complexity": round(min(1.0, theme_count / 5.0), 6),
        "difficulty_score": round(difficulty_score, 6),
    }


def build_stub_for_opportunity(opportunity, index):
    focus_nodes = opportunity.get("focus_nodes", {})
    level = opportunity.get("level") or "unknown"
    return {
        "reading_id": reading_id_for(index, level),
        "title": title_for(opportunity),
        "level": level,
        "theme_refs": unique_sorted(opportunity.get("theme_refs", []) or []),
        "linked_opportunities": [opportunity["opportunity_id"]],
        "focus_vocabulary": unique_sorted(focus_nodes.get("vocabulary", []) or []),
        "focus_grammar": unique_sorted(focus_nodes.get("grammar", []) or []),
        "focus_patterns": unique_sorted(focus_nodes.get("pattern", []) or []),
        "estimated_word_count": word_count_for(level),
        "difficulty_profile": difficulty_profile_for(opportunity),
        "content_status": "stub",
        "delivery_ready": True,
        "source": SOURCE,
    }


def build_summary(readings, opportunities, warnings, missing_inputs):
    linked_ids = [linked for reading in readings for linked in reading["linked_opportunities"]]
    opportunity_ids = {item.get("opportunity_id") for item in opportunities if item.get("opportunity_id")}
    linked_unique = set(linked_ids)
    coverage_ratio = round(len(linked_unique & opportunity_ids) / len(opportunity_ids), 6) if opportunity_ids else 0.0
    delivery_ready_count = sum(1 for reading in readings if reading.get("delivery_ready") is True)
    delivery_ready_ratio = round(delivery_ready_count / len(readings), 6) if readings else 0.0
    by_level = Counter(reading["level"] for reading in readings)
    by_theme = Counter(theme for reading in readings for theme in reading["theme_refs"])
    content_status_distribution = Counter(reading["content_status"] for reading in readings)
    status = "PASS_WITH_WARNINGS" if warnings or missing_inputs else "PASS"
    if not opportunities:
        status = "BLOCKED"
    return {
        "status": status,
        "contract_version": CONTRACT_VERSION,
        "source": SOURCE,
        "total_readings": len(readings),
        "linked_opportunities": len(linked_unique),
        "coverage_ratio": coverage_ratio,
        "by_level": dict(sorted(by_level.items())),
        "by_theme": dict(sorted(by_theme.items())),
        "content_status_distribution": dict(sorted(content_status_distribution.items())),
        "planner_readiness": {
            "opportunity_count": len(opportunity_ids),
            "reading_count": len(readings),
            "coverage_ratio": coverage_ratio,
            "delivery_ready_ratio": delivery_ready_ratio,
        },
        "missing_inputs": missing_inputs,
        "warnings": warnings,
    }


def build_reading_stub_authority():
    warnings = []
    expected_inputs = [
        LEARNING_OPPORTUNITIES_PATH,
        RANKED_OPPORTUNITIES_PATH,
        THEME_NODES_PATH,
        VOCABULARY_NODES_PATH,
        SENTENCE_PATTERNS_PATH,
        S11A_DESIGN_PATH,
    ]
    missing_inputs = [relative_path(path) for path in expected_inputs if not path.exists()]

    opportunities = read_json_optional(LEARNING_OPPORTUNITIES_PATH, [])
    read_json_optional(RANKED_OPPORTUNITIES_PATH, [])
    read_json_optional(THEME_NODES_PATH, [])
    read_json_optional(VOCABULARY_NODES_PATH, [])
    read_json_optional(SENTENCE_PATTERNS_PATH, [])

    if not isinstance(opportunities, list):
        warnings.append("learning_opportunities.json was not a list; emitted zero readings")
        opportunities = []

    valid_opportunities = []
    for opportunity in opportunities:
        if not isinstance(opportunity, dict) or not opportunity.get("opportunity_id"):
            warnings.append("skipped malformed opportunity without opportunity_id")
            continue
        valid_opportunities.append(opportunity)

    valid_opportunities.sort(key=lambda item: (item.get("level") or "", item.get("opportunity_id") or ""))
    readings = [
        build_stub_for_opportunity(opportunity, index)
        for index, opportunity in enumerate(valid_opportunities, start=1)
    ]

    summary = build_summary(readings, valid_opportunities, warnings, missing_inputs)
    write_json(READINGS_OUT_PATH, readings)
    write_json(SUMMARY_OUT_PATH, summary)
    print(f"Reading Stub Authority build: {summary['status']}")
    print(f"Readings: {len(readings)}")
    print(f"Coverage ratio: {summary['coverage_ratio']}")
    print(f"Warnings: {len(warnings)}")
    return summary


if __name__ == "__main__":
    build_reading_stub_authority()
