import json
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

OPPORTUNITIES_PATH = BASE_DIR / "ulga" / "graph" / "learning_opportunities.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "learning_opportunity_summary.json"
SENTENCE_PATTERNS_PATH = BASE_DIR / "ulga" / "graph" / "sentence_patterns.json"

SOURCE = "ULGA_S10B_LEARNING_OPPORTUNITY_AUTHORITY"
ALLOWED_DEPENDENCY_STATUS = {"ready", "blocked", "unknown"}
REQUIRED_RANKING_FEATURES = {
    "dependency_score",
    "mastery_gap_score",
    "reinforcement_score",
    "theme_continuity_score",
    "frequency_score",
    "pattern_utility_score",
}
REQUIRED_POLICY_FLAGS = {
    "generator_ready",
    "requires_learner_state",
    "has_theme",
    "has_pattern",
    "has_vocabulary",
    "has_grammar",
}
REQUIRED_FOCUS_KEYS = {"vocabulary", "grammar", "pattern", "chunk"}
ALLOWED_THEME_SOURCES = {
    "pattern_theme_ref",
    "pattern_slot_gate",
    "vocabulary_theme",
    "chunk_theme_hint",
    "theme_consensus",
    "general_fallback",
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


def warn(warnings, message):
    warnings.append(message)


def validate_opportunity(record, index, source_pattern_ids, warnings):
    required = {
        "opportunity_id",
        "source_pattern_id",
        "candidate_type",
        "level",
        "focus_nodes",
        "theme_refs",
        "theme_confidence",
        "reinforces",
        "dependency",
        "ranking_features",
        "policy_flags",
        "source",
    }
    missing = required - set(record)
    if missing:
        return fail(f"opportunities[{index}] missing required fields: {sorted(missing)}")
    if record["candidate_type"] != "learning_opportunity":
        return fail(f"{record['opportunity_id']} candidate_type must be learning_opportunity")
    if record["source"] != SOURCE:
        return fail(f"{record['opportunity_id']} source must be {SOURCE}")
    if not record["source_pattern_id"]:
        return fail(f"{record['opportunity_id']} source_pattern_id is empty")
    if source_pattern_ids and record["source_pattern_id"] not in source_pattern_ids:
        return fail(f"{record['opportunity_id']} unknown source_pattern_id: {record['source_pattern_id']}")
    if not record["level"]:
        return fail(f"{record['opportunity_id']} level is empty")

    focus_nodes = record["focus_nodes"]
    if not isinstance(focus_nodes, dict):
        return fail(f"{record['opportunity_id']} focus_nodes must be an object")
    missing_focus = REQUIRED_FOCUS_KEYS - set(focus_nodes)
    if missing_focus:
        return fail(f"{record['opportunity_id']} focus_nodes missing keys: {sorted(missing_focus)}")
    for key in REQUIRED_FOCUS_KEYS:
        if not isinstance(focus_nodes.get(key), list):
            return fail(f"{record['opportunity_id']} focus_nodes.{key} must be a list")
    if not focus_nodes["pattern"] and not focus_nodes["vocabulary"]:
        return fail(f"{record['opportunity_id']} must have at least pattern or vocabulary focus")

    theme_refs = record["theme_refs"]
    if not isinstance(theme_refs, list) or not theme_refs:
        return fail(f"{record['opportunity_id']} theme_refs must be a non-empty list")
    if "General" in theme_refs:
        warn(warnings, f"{record['opportunity_id']} uses General theme fallback")

    theme_confidence = record["theme_confidence"]
    if not isinstance(theme_confidence, dict):
        return fail(f"{record['opportunity_id']} theme_confidence must be an object")
    if set(theme_confidence) != {"source", "confidence"}:
        return fail(f"{record['opportunity_id']} theme_confidence must contain source and confidence")
    if theme_confidence["source"] not in ALLOWED_THEME_SOURCES:
        return fail(f"{record['opportunity_id']} invalid theme source: {theme_confidence['source']}")
    confidence = theme_confidence["confidence"]
    if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
        return fail(f"{record['opportunity_id']} theme confidence must be between 0 and 1")
    if theme_confidence["source"] == "general_fallback" and theme_refs != ["General"]:
        return fail(f"{record['opportunity_id']} general_fallback source must emit only General")
    if theme_confidence["source"] != "general_fallback" and theme_refs == ["General"]:
        return fail(f"{record['opportunity_id']} specific theme source must not emit only General")

    dependency = record["dependency"]
    if not isinstance(dependency, dict):
        return fail(f"{record['opportunity_id']} dependency must be an object")
    for key in ["status", "missing_requires", "requires"]:
        if key not in dependency:
            return fail(f"{record['opportunity_id']} dependency missing {key}")
    if dependency["status"] not in ALLOWED_DEPENDENCY_STATUS:
        return fail(f"{record['opportunity_id']} invalid dependency.status: {dependency['status']}")
    if not isinstance(dependency["missing_requires"], list) or not isinstance(dependency["requires"], list):
        return fail(f"{record['opportunity_id']} dependency requires fields must be lists")

    ranking_features = record["ranking_features"]
    if not isinstance(ranking_features, dict):
        return fail(f"{record['opportunity_id']} ranking_features must be an object")
    missing_features = REQUIRED_RANKING_FEATURES - set(ranking_features)
    if missing_features:
        return fail(f"{record['opportunity_id']} ranking_features missing: {sorted(missing_features)}")

    policy_flags = record["policy_flags"]
    if not isinstance(policy_flags, dict):
        return fail(f"{record['opportunity_id']} policy_flags must be an object")
    missing_flags = REQUIRED_POLICY_FLAGS - set(policy_flags)
    if missing_flags:
        return fail(f"{record['opportunity_id']} policy_flags missing: {sorted(missing_flags)}")
    for key in REQUIRED_POLICY_FLAGS:
        if not isinstance(policy_flags[key], bool):
            return fail(f"{record['opportunity_id']} policy_flags.{key} must be boolean")
    if policy_flags["has_theme"] is False:
        warn(warnings, f"{record['opportunity_id']} has_theme is false")
    if policy_flags["has_vocabulary"] is False:
        warn(warnings, f"{record['opportunity_id']} has_vocabulary is false")
    return True


def validate():
    print("Validating ULGA Learning Opportunities...")
    if not OPPORTUNITIES_PATH.exists():
        return fail(f"required file does not exist: {OPPORTUNITIES_PATH}")
    if not SUMMARY_PATH.exists():
        return fail(f"required file does not exist: {SUMMARY_PATH}")

    opportunities = read_json(OPPORTUNITIES_PATH)
    summary = read_json(SUMMARY_PATH)
    patterns = read_json(SENTENCE_PATTERNS_PATH) if SENTENCE_PATTERNS_PATH.exists() else []
    if opportunities is None or summary is None or patterns is None:
        return False
    if not isinstance(opportunities, list):
        return fail("learning_opportunities.json must contain a list")
    if not isinstance(summary, dict):
        return fail("learning_opportunity_summary.json must contain an object")
    if not isinstance(patterns, list):
        patterns = []

    source_pattern_ids = {
        pattern.get("authority_source", {}).get("source_record_id")
        or pattern.get("metadata", {}).get("source_record_id")
        or pattern.get("metadata", {}).get("pattern_id")
        or pattern.get("id")
        for pattern in patterns
    }
    source_pattern_ids.discard(None)

    seen_ids = set()
    warnings = []
    for index, record in enumerate(opportunities):
        if not isinstance(record, dict):
            return fail(f"opportunities[{index}] must be an object")
        opportunity_id = record.get("opportunity_id")
        if not opportunity_id:
            return fail(f"opportunities[{index}] missing opportunity_id")
        if opportunity_id in seen_ids:
            return fail(f"duplicate opportunity_id: {opportunity_id}")
        seen_ids.add(opportunity_id)
        if not validate_opportunity(record, index, source_pattern_ids, warnings):
            return False

    if summary.get("total_opportunities") != len(opportunities):
        return fail("summary total_opportunities does not match opportunities length")
    if summary.get("source") != SOURCE:
        return fail(f"summary source must be {SOURCE}")
    if summary.get("status") not in {"PASS", "PASS_WITH_WARNINGS"}:
        return fail("summary status must be PASS or PASS_WITH_WARNINGS")
    if not isinstance(summary.get("missing_optional_inputs"), list):
        return fail("summary missing_optional_inputs must be a list")
    if not isinstance(summary.get("warnings"), list):
        return fail("summary warnings must be a list")
    theme_source_distribution = summary.get("theme_source_distribution")
    if not isinstance(theme_source_distribution, dict):
        return fail("summary theme_source_distribution must be an object")
    actual_distribution = {}
    for record in opportunities:
        source = record["theme_confidence"]["source"]
        actual_distribution[source] = actual_distribution.get(source, 0) + 1
    if theme_source_distribution != dict(sorted(actual_distribution.items())):
        return fail("summary theme_source_distribution does not match opportunities")

    theme_specificity = summary.get("theme_specificity")
    if not isinstance(theme_specificity, dict):
        return fail("summary theme_specificity must be an object")
    general_count = sum(1 for record in opportunities if record["theme_refs"] == ["General"])
    specific_count = len(opportunities) - general_count
    specific_ratio = round(specific_count / len(opportunities), 6) if opportunities else 0.0
    if theme_specificity.get("general_count") != general_count:
        return fail("summary theme_specificity.general_count does not match opportunities")
    if theme_specificity.get("specific_count") != specific_count:
        return fail("summary theme_specificity.specific_count does not match opportunities")
    if theme_specificity.get("specific_ratio") != specific_ratio:
        return fail("summary theme_specificity.specific_ratio does not match opportunities")

    print(f"Learning Opportunity validation: PASS ({len(warnings)} warnings)")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
