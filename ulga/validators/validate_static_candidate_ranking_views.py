import json
import re
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
RAW_RANKING_PATH = BASE_DIR / "ulga" / "graph" / "static_candidate_ranking.json"
VIEWS_PATH = BASE_DIR / "ulga" / "graph" / "static_candidate_ranking_views.json"

FORBIDDEN_ADAPTIVE_KEYWORDS = {
    "learner_state",
    "mastery",
    "mastery_gap",
    "retention",
    "forgetting_curve",
    "assessment",
    "attempt_history",
    "review_queue",
    "personalized_exposure",
    "student_id",
    "learner_id",
    "james",
    "cyndi",
    "planner",
    "today_plan",
}

REQUIRED_TOP_LEVEL_FIELDS = {
    "schema_version",
    "generation_mode",
    "adaptive_enabled",
    "source",
    "principles",
    "view_policy",
    "views",
    "diagnostics",
    "warnings",
}

REQUIRED_LIST_VIEWS = {
    "raw_global_view",
    "balanced_global_view",
    "a1_safe_view",
    "reading_bridge_view",
    "dialogue_bridge_view",
    "pattern_first_view",
    "vocabulary_first_view",
    "chunk_safe_view",
    "deduplicated_view",
}

REQUIRED_THEME_NAMES = {"Home", "Food", "School", "Travel", "Health", "Personal", "Daily Life"}

REQUIRED_CANDIDATE_FIELDS = {
    "view_rank",
    "view_candidate_id",
    "raw_rank",
    "raw_candidate_id",
    "candidate_type",
    "label",
    "level",
    "theme_refs",
    "raw_static_score",
    "view_score",
    "view_policy_applied",
    "balance_adjustments",
    "dedup_group_id",
    "equivalent_raw_candidate_ids",
    "curriculum_suitability_flags",
    "source_explain",
}

CEFR_ORDER = {
    "A1": 1,
    "A1+": 2,
    "A2": 3,
    "A2+": 4,
    "B1": 5,
    "B1+": 6,
    "B2": 7,
    "B2+": 8,
    "C1": 9,
    "C2": 10,
}

VIEW_TYPE_ORDER = {
    "raw_global_view": {"pattern_candidate": 0, "vocabulary_candidate": 1, "chunk_candidate": 2},
    "balanced_global_view": {"pattern_candidate": 0, "vocabulary_candidate": 1, "chunk_candidate": 2},
    "a1_safe_view": {"pattern_candidate": 0, "vocabulary_candidate": 1, "chunk_candidate": 2},
    "reading_bridge_view": {"pattern_candidate": 0, "vocabulary_candidate": 1, "chunk_candidate": 2},
    "dialogue_bridge_view": {"pattern_candidate": 0, "chunk_candidate": 1, "vocabulary_candidate": 2},
    "pattern_first_view": {"pattern_candidate": 0, "vocabulary_candidate": 1, "chunk_candidate": 2},
    "vocabulary_first_view": {"vocabulary_candidate": 0, "pattern_candidate": 1, "chunk_candidate": 2},
    "chunk_safe_view": {"chunk_candidate": 0, "pattern_candidate": 1, "vocabulary_candidate": 2},
    "deduplicated_view": {"pattern_candidate": 0, "vocabulary_candidate": 1, "chunk_candidate": 2},
    "theme_scoped_view": {"vocabulary_candidate": 0, "pattern_candidate": 1, "chunk_candidate": 2},
}


def read_json(path):
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception as exc:
        print(f"FAIL: could not parse {path}: {exc}")
        return None


def fail(message):
    print(f"FAIL: {message}")
    return False


def normalize_label(label):
    text = str(label or "").lower().replace("_", " ")
    text = re.sub(r":safe_chunk_\d+", "", text)
    text = re.sub(r"\bsafe chunk \d+\b", "", text)
    text = re.sub(r"\bsth/sb\b", "sb/sth", text)
    text = re.sub(r"\bsb/sth\b|\bsth/sb\b", "sb_sth", text)
    text = re.sub(r"[(){}\[\],;:!?]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" ./_-")
    return text.replace("sb_sth", "sb/sth")


def recursive_forbidden_scan(payload):
    if isinstance(payload, dict):
        for key, value in payload.items():
            if any(token in str(key).lower() for token in FORBIDDEN_ADAPTIVE_KEYWORDS):
                return True, str(key)
            found, source = recursive_forbidden_scan(value)
            if found:
                return True, source
        return False, None
    if isinstance(payload, list):
        for item in payload:
            found, source = recursive_forbidden_scan(item)
            if found:
                return True, source
        return False, None
    if isinstance(payload, str):
        lowered = payload.lower()
        for token in FORBIDDEN_ADAPTIVE_KEYWORDS:
            if token in lowered:
                return True, payload
    return False, None


def level_value(level):
    return CEFR_ORDER.get(level, 999)


def sort_key(view_name, candidate):
    return (
        -candidate["view_score"],
        -candidate["raw_static_score"],
        level_value(candidate["level"]),
        VIEW_TYPE_ORDER.get(view_name, {}).get(candidate["candidate_type"], 999),
        normalize_label(candidate["label"]),
        candidate["raw_candidate_id"],
    )


def in_range(value):
    return isinstance(value, (int, float)) and 0.0 <= value <= 1.0


def validate_candidate_list(view_name, candidates, raw_ids):
    if not isinstance(candidates, list):
        return fail(f"{view_name} must be a list")
    for index, candidate in enumerate(candidates):
        if REQUIRED_CANDIDATE_FIELDS - set(candidate):
            return fail(f"{view_name}[{index}] missing required fields")
        if candidate["view_rank"] != index + 1:
            return fail(f"{view_name} view_rank must be sequential")
        if candidate["raw_candidate_id"] not in raw_ids:
            return fail(f"{view_name} candidate does not trace to raw ranking: {candidate['raw_candidate_id']}")
        if candidate["raw_rank"] < 1:
            return fail(f"{view_name} raw_rank must be positive")
        if not in_range(candidate["raw_static_score"]):
            return fail(f"{view_name} raw_static_score out of range")
        if not in_range(candidate["view_score"]):
            return fail(f"{view_name} view_score out of range")
        if not isinstance(candidate["source_explain"], list):
            return fail(f"{view_name} source_explain must be a list")
        if not isinstance(candidate["view_policy_applied"], list):
            return fail(f"{view_name} view_policy_applied must be a list")
        if not isinstance(candidate["balance_adjustments"], list):
            return fail(f"{view_name} balance_adjustments must be a list")
        if not isinstance(candidate["curriculum_suitability_flags"], list):
            return fail(f"{view_name} curriculum_suitability_flags must be a list")
        if not isinstance(candidate["equivalent_raw_candidate_ids"], list):
            return fail(f"{view_name} equivalent_raw_candidate_ids must be a list")
    expected_sorted = sorted(candidates, key=lambda item: sort_key(view_name, item))
    if view_name != "deduplicated_view" and candidates != expected_sorted:
        return fail(f"{view_name} is not sorted by required deterministic order")
    return True


def duplicate_count_top20(candidates):
    seen = set()
    duplicates = 0
    for candidate in candidates[:20]:
        normalized = normalize_label(candidate["label"])
        if normalized in seen:
            duplicates += 1
        seen.add(normalized)
    return duplicates


def validate():
    print("Validating Static Candidate Ranking Views...")
    if not VIEWS_PATH.exists():
        return fail(f"required file does not exist: {VIEWS_PATH}")
    if not RAW_RANKING_PATH.exists():
        return fail(f"required raw ranking does not exist: {RAW_RANKING_PATH}")

    payload = read_json(VIEWS_PATH)
    raw_payload = read_json(RAW_RANKING_PATH)
    if payload is None or raw_payload is None:
        return False
    if not REQUIRED_TOP_LEVEL_FIELDS.issubset(payload):
        return fail("top-level fields are incomplete")
    if payload.get("schema_version") != "ULGA_S10F_STATIC_CANDIDATE_RANKING_VIEWS_V1":
        return fail("schema_version mismatch")
    if payload.get("generation_mode") != "static_offline_view_construction":
        return fail("generation_mode must be static_offline_view_construction")
    if payload.get("adaptive_enabled") is not False:
        return fail("adaptive_enabled must be false")

    detected, source = recursive_forbidden_scan(payload)
    if detected:
        return fail(f"forbidden adaptive keyword found in output: {source}")

    views = payload.get("views")
    if not isinstance(views, dict):
        return fail("views must be an object")
    if REQUIRED_LIST_VIEWS - set(views):
        return fail("required list views are missing")
    if "theme_scoped_view" not in views or not isinstance(views["theme_scoped_view"], dict):
        return fail("theme_scoped_view must be an object")
    if REQUIRED_THEME_NAMES - set(views["theme_scoped_view"]):
        return fail("theme_scoped_view missing required themes")

    raw_candidates = raw_payload.get("candidates", [])
    raw_ids = {candidate["candidate_id"] for candidate in raw_candidates}
    raw_scores = {candidate["candidate_id"]: candidate["static_score"] for candidate in raw_candidates}
    enough_non_chunk_a1 = sum(1 for candidate in raw_candidates if candidate["level"] == "A1" and candidate["candidate_type"] != "chunk_candidate") >= 20
    enough_mixed = all(sum(1 for candidate in raw_candidates if candidate["candidate_type"] == candidate_type) >= 20 for candidate_type in ["pattern_candidate", "vocabulary_candidate", "chunk_candidate"])

    for view_name in REQUIRED_LIST_VIEWS:
        if not validate_candidate_list(view_name, views[view_name], raw_ids):
            return False
        for candidate in views[view_name]:
            if raw_scores.get(candidate["raw_candidate_id"]) != candidate["raw_static_score"]:
                return fail(f"{view_name} overwrote raw_static_score for {candidate['raw_candidate_id']}")

    for theme_name, candidates in views["theme_scoped_view"].items():
        if not validate_candidate_list("theme_scoped_view", candidates, raw_ids):
            return False

    for view_name in ["balanced_global_view", "a1_safe_view", "deduplicated_view"]:
        if duplicate_count_top20(views[view_name]) > 0:
            return fail(f"{view_name} top-20 contains duplicate normalized labels")

    for candidate in views["a1_safe_view"]:
        if level_value(candidate["level"]) > level_value("A1"):
            return fail("a1_safe_view contains level above A1")

    top20_a1 = views["a1_safe_view"][:20]
    if enough_non_chunk_a1 and top20_a1:
        chunk_ratio = sum(1 for candidate in top20_a1 if candidate["candidate_type"] == "chunk_candidate") / len(top20_a1)
        if chunk_ratio > 0.25:
            return fail("a1_safe_view top-20 chunk ratio exceeds 0.25 when enough non-chunk candidates are available")

    top20_balanced = views["balanced_global_view"][:20]
    if enough_mixed and len({candidate["candidate_type"] for candidate in top20_balanced}) == 1:
        return fail("balanced_global_view top-20 is single-type dominated")
    if enough_mixed:
        if sum(1 for candidate in top20_balanced if candidate["candidate_type"] == "pattern_candidate") < 4:
            return fail("balanced_global_view top-20 does not include at least 4 pattern candidates when available")
        if sum(1 for candidate in top20_balanced if candidate["candidate_type"] == "vocabulary_candidate") < 6:
            return fail("balanced_global_view top-20 does not include at least 6 vocabulary candidates when available")
        if sum(1 for candidate in top20_balanced if candidate["candidate_type"] == "chunk_candidate") > 7:
            return fail("balanced_global_view top-20 exceeds 7 chunk candidates when enough alternatives are available")

    if enough_non_chunk_a1 and top20_a1:
        if sum(1 for candidate in top20_a1 if candidate["candidate_type"] == "pattern_candidate") < 5:
            return fail("a1_safe_view top-20 does not include at least 5 pattern candidates when available")
        if sum(1 for candidate in top20_a1 if candidate["candidate_type"] == "vocabulary_candidate") < 5:
            return fail("a1_safe_view top-20 does not include at least 5 vocabulary candidates when available")

    print("Static Candidate Ranking Views validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
