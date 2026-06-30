import json
import re
import sys
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

RAW_RANKING_PATH = BASE_DIR / "ulga" / "graph" / "static_candidate_ranking.json"
RAW_SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "static_candidate_ranking_summary.json"
QUALITY_AUDIT_PATH = BASE_DIR / "ulga" / "reports" / "static_candidate_ranking_quality_audit.json"
CONTRACT_PATH = BASE_DIR / "docs" / "ulga" / "ULGA_S10E_STATIC_CANDIDATE_RANKING_BALANCING_CONTRACT_DESIGN_SCAN.md"
THEME_MAPPING_PATH = BASE_DIR / "themes" / "theme_vocab_mapping.json"
CHUNK_METADATA_PATH = BASE_DIR / "ulga" / "graph" / "chunk_grammar_metadata.json"
PATTERN_PATH = BASE_DIR / "ulga" / "graph" / "sentence_patterns.json"
VOCAB_NODES_PATH = BASE_DIR / "ulga" / "graph" / "vocabulary_nodes.json"
CHUNK_NODES_PATH = BASE_DIR / "ulga" / "graph" / "chunk_nodes.json"
VOCAB_SOURCE_PATH = BASE_DIR / "vocabulary" / "json" / "vocabulary.json"

OUTPUT_PATH = BASE_DIR / "ulga" / "graph" / "static_candidate_ranking_views.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "static_candidate_ranking_views_summary.json"

SCHEMA_VERSION = "ULGA_S10F_STATIC_CANDIDATE_RANKING_VIEWS_V1"
SUMMARY_SCHEMA_VERSION = "ULGA_S10F_STATIC_CANDIDATE_RANKING_VIEWS_SUMMARY_V1"

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

VIEW_LIMITS = {
    "raw_global_view": 500,
    "balanced_global_view": 100,
    "a1_safe_view": 100,
    "reading_bridge_view": 100,
    "dialogue_bridge_view": 100,
    "pattern_first_view": 100,
    "vocabulary_first_view": 100,
    "chunk_safe_view": 100,
    "deduplicated_view": 100,
}

THEMES = ["Home", "Food", "School", "Travel", "Health", "Personal", "Daily Life"]

THEME_KEYWORDS = {
    "Home": ["home", "house", "room", "kitchen", "bedroom", "bathroom", "living room"],
    "Food": ["food", "drink", "water", "milk", "rice", "bread", "apple", "restaurant", "eat", "dining"],
    "School": ["school", "class", "teacher", "student", "book", "desk", "pen", "pencil", "lesson"],
    "Travel": ["travel", "bus", "train", "airport", "station", "ticket", "weather", "go", "trip"],
    "Health": ["health", "body", "doctor", "head", "hand", "leg", "sick", "pain", "hurt"],
    "Personal": ["name", "family", "friend", "like", "hobby", "birthday", "age"],
    "Daily Life": ["daily", "morning", "evening", "breakfast", "lunch", "dinner", "home", "school"],
}

INFERRED_TERMS = {"inferred", "unknown", "fallback", "proxy", "rule_based", "default"}
LOW_SPECIFICITY_VOCAB = {
    "and",
    "as",
    "at",
    "be",
    "for",
    "in",
    "of",
    "on",
    "or",
    "so",
    "that",
    "this",
    "to",
    "will",
    "with",
}

VIEW_TYPE_PREFERENCE = {
    "raw_global_view": {},
    "balanced_global_view": {"pattern_candidate": 0.12, "vocabulary_candidate": 0.02, "chunk_candidate": -0.05},
    "a1_safe_view": {"pattern_candidate": 0.12, "vocabulary_candidate": 0.02, "chunk_candidate": -0.05},
    "reading_bridge_view": {"pattern_candidate": 0.1, "vocabulary_candidate": 0.02, "chunk_candidate": -0.04},
    "dialogue_bridge_view": {"pattern_candidate": 0.08, "chunk_candidate": 0.02, "vocabulary_candidate": 0.0},
    "pattern_first_view": {"pattern_candidate": 0.12, "vocabulary_candidate": 0.01, "chunk_candidate": -0.04},
    "vocabulary_first_view": {"vocabulary_candidate": 0.05, "pattern_candidate": 0.01, "chunk_candidate": -0.04},
    "chunk_safe_view": {"chunk_candidate": 0.0, "pattern_candidate": 0.02, "vocabulary_candidate": 0.02},
    "deduplicated_view": {},
    "theme_scoped_view": {"vocabulary_candidate": 0.03, "pattern_candidate": 0.02, "chunk_candidate": -0.02},
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

BALANCED_TARGET_COUNTS = {"pattern_candidate": 35, "vocabulary_candidate": 40, "chunk_candidate": 25}
A1_TARGET_COUNTS = {"pattern_candidate": 35, "vocabulary_candidate": 45, "chunk_candidate": 20}


def read_json(path, default=None):
    if not path.exists():
        return deepcopy(default)
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def normalize_label(label):
    text = str(label or "").lower().replace("_", " ")
    text = re.sub(r":safe_chunk_\d+", "", text)
    text = re.sub(r"\bsafe chunk \d+\b", "", text)
    text = re.sub(r"\bsth/sb\b", "sb/sth", text)
    text = re.sub(r"\bsb/sth\b|\bsth/sb\b", "sb_sth", text)
    text = re.sub(r"[(){}\[\],;:!?]+", " ", text)
    text = re.sub(r"\s+/\s+", " / ", text)
    text = re.sub(r"\s+", " ", text).strip(" ./_-")
    return text.replace("sb_sth", "sb/sth")


def level_value(level):
    return CEFR_ORDER.get(level, 999)


def clamp(value, lower=0.0, upper=1.0):
    return max(lower, min(upper, value))


def round4(value):
    return round(value + 1e-10, 4)


def load_theme_lookup():
    payload = read_json(THEME_MAPPING_PATH, {"themes": []})
    lookup = {}
    for item in payload.get("themes", []):
        theme_id = item.get("theme_id")
        if theme_id:
            lookup[f"theme:{theme_id}"] = item
    return lookup


def load_chunk_metadata_lookup():
    payload = read_json(CHUNK_METADATA_PATH, [])
    return {item.get("chunk_id"): item for item in payload if isinstance(item, dict) and item.get("chunk_id")}


def load_pattern_lookup():
    payload = read_json(PATTERN_PATH, [])
    items = payload.get("patterns", []) if isinstance(payload, dict) else payload
    return {item.get("id"): item for item in items if isinstance(item, dict) and item.get("id")}


def load_vocab_lookup():
    payload = read_json(VOCAB_NODES_PATH, [])
    return {item.get("id"): item for item in payload if isinstance(item, dict) and item.get("id")}


def load_chunk_lookup():
    payload = read_json(CHUNK_NODES_PATH, [])
    return {item.get("id"): item for item in payload if isinstance(item, dict) and item.get("id")}


def collect_theme_hints(candidate, theme_lookup, chunk_lookup):
    hints = []
    for theme_ref in candidate.get("theme_refs", []):
        theme_info = theme_lookup.get(theme_ref, {})
        hints.extend(str(value).lower() for value in [
            theme_ref,
            theme_info.get("theme_id"),
            theme_info.get("parent_theme"),
            " ".join(theme_info.get("primary_topics", [])),
            " ".join(theme_info.get("secondary_topics", [])),
        ] if value)
    chunk_info = chunk_lookup.get(candidate["raw_candidate_id"], {})
    metadata = chunk_info.get("metadata", {})
    hints.extend(str(value).lower() for value in metadata.get("theme_hint", []))
    topic = metadata.get("topic")
    if topic:
        hints.append(str(topic).lower())
    hints.extend(str(item).lower() for item in candidate.get("source_explain", []))
    hints.append(candidate.get("normalized_label", ""))
    return hints


def opacity_flags(candidate, chunk_metadata_lookup, pattern_lookup, vocab_lookup, chunk_lookup):
    label = candidate["label"]
    normalized = candidate["normalized_label"]
    lower = label.lower()
    flags = []
    if "sb" in lower or "sth" in lower:
        flags.append("contains_sb_sth")
    if "/" in label:
        flags.append("contains_slash_alternative")
    if "(" in label or ")" in label:
        flags.append("contains_bracket_alternative")
    if candidate["candidate_type"] == "chunk_candidate" and " or " in normalized and (" sb " in f" {normalized} " or " sth " in f" {normalized} " or "sb/sth" in normalized):
        flags.append("movable_object_pattern")
    if any(term in lower for term in ["would have", "had known", "conditional", "perfect"]):
        flags.append("advanced_modal_or_perfect")
    if len(normalized.split()) > 6:
        flags.append("label_too_long")
    if candidate["candidate_type"] == "vocabulary_candidate" and normalized in LOW_SPECIFICITY_VOCAB:
        flags.append("low_specificity_vocabulary")
    theme_missing = not candidate.get("theme_refs")
    if candidate["candidate_type"] == "chunk_candidate":
        chunk_meta = chunk_metadata_lookup.get(candidate["raw_candidate_id"], {})
        chunk_node = chunk_lookup.get(candidate["raw_candidate_id"], {})
        if theme_missing and not chunk_node.get("metadata", {}).get("theme_hint"):
            flags.append("missing_theme_anchor")
        if not chunk_meta.get("pattern_seed") and not any("pattern" in entry.lower() for entry in candidate["source_explain"]):
            flags.append("missing_pattern_bridge")
        if not any(token.isalpha() and token not in {"sb", "sth", "or", "to", "do", "be"} for token in normalized.split()):
            flags.append("missing_vocabulary_anchor")
        if (
            "contains_sb_sth" in flags
            or "contains_slash_alternative" in flags
            or "contains_bracket_alternative" in flags
            or "missing_theme_anchor" in flags
        ):
            flags.append("idiomatic_or_low_transparency")
    return sorted(set(flags))


def inferred_flags(source_explain):
    flags = []
    explain_text = " ".join(str(item).lower() for item in source_explain)
    if "inferred" in explain_text:
        flags.append("inferred_signal_present")
    if "fallback" in explain_text or "default" in explain_text:
        flags.append("fallback_signal_present")
    if "proxy" in explain_text:
        flags.append("proxy_signal_present")
    return flags


def theme_matches(candidate, theme_name, theme_lookup, chunk_lookup):
    keywords = THEME_KEYWORDS[theme_name]
    haystacks = collect_theme_hints(candidate, theme_lookup, chunk_lookup)
    return any(keyword in haystack for haystack in haystacks for keyword in keywords)


def type_preference_order(view_name, candidate_type):
    return VIEW_TYPE_ORDER.get(view_name, {}).get(candidate_type, 999)


def sort_key(view_name, candidate):
    return (
        -candidate["view_score"],
        -candidate["raw_static_score"],
        level_value(candidate["level"]),
        type_preference_order(view_name, candidate["candidate_type"]),
        candidate["normalized_label"],
        candidate["raw_candidate_id"],
    )


def base_view_candidate(raw_candidate, metadata):
    entry = {
        "view_candidate_id": raw_candidate["candidate_id"],
        "raw_rank": raw_candidate["rank"],
        "raw_candidate_id": raw_candidate["candidate_id"],
        "candidate_type": raw_candidate["candidate_type"],
        "label": raw_candidate["label"],
        "level": raw_candidate["level"],
        "theme_refs": list(raw_candidate.get("theme_refs", [])),
        "raw_static_score": raw_candidate["static_score"],
        "view_score": raw_candidate["static_score"],
        "view_policy_applied": [],
        "balance_adjustments": [],
        "dedup_group_id": None,
        "equivalent_raw_candidate_ids": [],
        "curriculum_suitability_flags": [],
        "source_explain": list(raw_candidate.get("explain", [])),
        "normalized_label": normalize_label(raw_candidate["label"]),
    }
    entry["curriculum_suitability_flags"].extend(inferred_flags(entry["source_explain"]))
    entry["curriculum_suitability_flags"].extend(
        opacity_flags(
            entry,
            metadata["chunk_metadata_lookup"],
            metadata["pattern_lookup"],
            metadata["vocab_lookup"],
            metadata["chunk_lookup"],
        )
    )
    entry["curriculum_suitability_flags"] = sorted(set(entry["curriculum_suitability_flags"]))
    return entry


def add_adjustment(candidate, name, value):
    value = round4(value)
    if value == 0:
        return
    candidate["balance_adjustments"].append({"adjustment": name, "value": value})


def apply_view_score(candidate, view_name, *, theme_name=None):
    score = candidate["raw_static_score"]
    type_adj = VIEW_TYPE_PREFERENCE.get(view_name, {}).get(candidate["candidate_type"], 0.0)
    add_adjustment(candidate, "type_balance_adjustment", type_adj)
    score += type_adj

    level_adj = 0.0
    if view_name == "a1_safe_view":
        if candidate["level"] == "A1":
            level_adj = 0.05
        elif level_value(candidate["level"]) > level_value("A1"):
            level_adj = -0.1
    elif view_name in {"reading_bridge_view", "pattern_first_view", "vocabulary_first_view", "chunk_safe_view"}:
        if candidate["level"] == "A1":
            level_adj = 0.03
        elif level_value(candidate["level"]) <= level_value("B1"):
            level_adj = 0.01
        else:
            level_adj = -0.05
    add_adjustment(candidate, "level_policy_adjustment", level_adj)
    score += level_adj

    theme_adj = 0.0
    if theme_name and theme_name in candidate.get("matched_themes", []):
        theme_adj = 0.05
    elif view_name in {"reading_bridge_view", "dialogue_bridge_view", "chunk_safe_view"} and candidate.get("theme_refs"):
        theme_adj = 0.01
    if view_name in {"balanced_global_view", "a1_safe_view", "reading_bridge_view", "theme_scoped_view"} and "low_specificity_vocabulary" in candidate["curriculum_suitability_flags"]:
        theme_adj -= 0.05
    add_adjustment(candidate, "theme_policy_adjustment", theme_adj)
    score += theme_adj

    opacity_penalty = 0.0
    opacity_flags_found = set(candidate["curriculum_suitability_flags"])
    if "advanced_modal_or_perfect" in opacity_flags_found:
        opacity_penalty -= 0.08
    if "contains_sb_sth" in opacity_flags_found:
        opacity_penalty -= 0.03
    if "contains_slash_alternative" in opacity_flags_found or "contains_bracket_alternative" in opacity_flags_found:
        opacity_penalty -= 0.02
    if "idiomatic_or_low_transparency" in opacity_flags_found:
        opacity_penalty -= 0.04
    if "low_specificity_vocabulary" in opacity_flags_found:
        opacity_penalty -= 0.03
    if view_name == "dialogue_bridge_view":
        opacity_penalty *= 0.5
    if view_name == "raw_global_view":
        opacity_penalty = 0.0
    add_adjustment(candidate, "opacity_penalty", opacity_penalty)
    score += opacity_penalty

    inferred_penalty = 0.0
    if any(flag in opacity_flags_found for flag in ["inferred_signal_present", "fallback_signal_present", "proxy_signal_present"]):
        inferred_penalty = -0.02
        if view_name in {"a1_safe_view", "reading_bridge_view"}:
            inferred_penalty = -0.04
    add_adjustment(candidate, "inferred_signal_penalty", inferred_penalty)
    score += inferred_penalty

    duplicate_penalty = -0.2 if candidate.get("duplicate_penalty") else 0.0
    add_adjustment(candidate, "duplicate_penalty", duplicate_penalty)
    score += duplicate_penalty

    candidate["view_score"] = round4(clamp(score))


def finalize_view(view_name, candidates):
    ordered = sorted(candidates, key=lambda item: sort_key(view_name, item))
    for index, candidate in enumerate(ordered, start=1):
        candidate["view_rank"] = index
        candidate.pop("normalized_label", None)
        candidate.pop("matched_themes", None)
        candidate.pop("duplicate_penalty", None)
    return ordered


def deduplicate_candidates(candidates, *, preserve_equivalents=True):
    groups = {}
    for candidate in candidates:
        groups.setdefault(candidate["normalized_label"], []).append(candidate)
    deduped = []
    for normalized, group in groups.items():
        canonical = sorted(
            group,
            key=lambda item: (
                -item["raw_static_score"],
                len(item["label"]),
                level_value(item["level"]),
                item["raw_candidate_id"],
            ),
        )[0]
        candidate = deepcopy(canonical)
        candidate["dedup_group_id"] = f"dedup:{normalized}"
        if preserve_equivalents:
            candidate["equivalent_raw_candidate_ids"] = [item["raw_candidate_id"] for item in sorted(group, key=lambda entry: entry["raw_rank"])]
            if len(group) > 1:
                candidate["view_policy_applied"].append("canonical_collapse")
        deduped.append(candidate)
    return deduped


def select_with_targets(candidates, limit, target_counts, top20_rules=None):
    by_type = {
        "pattern_candidate": [candidate for candidate in candidates if candidate["candidate_type"] == "pattern_candidate"],
        "vocabulary_candidate": [candidate for candidate in candidates if candidate["candidate_type"] == "vocabulary_candidate"],
        "chunk_candidate": [candidate for candidate in candidates if candidate["candidate_type"] == "chunk_candidate"],
    }
    used_ids = set()
    used_labels = set()
    selected = []

    def try_take(candidate, enforce_unique=True):
        if candidate["raw_candidate_id"] in used_ids:
            return False
        if enforce_unique and candidate["normalized_label"] in used_labels:
            return False
        used_ids.add(candidate["raw_candidate_id"])
        used_labels.add(candidate["normalized_label"])
        selected.append(candidate)
        return True

    if top20_rules:
        for candidate_type, minimum in top20_rules.get("minimums", {}).items():
            count = 0
            for candidate in by_type[candidate_type]:
                if len(selected) >= min(20, limit):
                    break
                if try_take(candidate):
                    count += 1
                if count >= minimum:
                    break

        for candidate in by_type["chunk_candidate"]:
            if len(selected) >= min(20, limit):
                break
            current_chunks = sum(1 for item in selected if item["candidate_type"] == "chunk_candidate")
            max_chunks = top20_rules.get("chunk_max", 999)
            if current_chunks >= max_chunks:
                break
            try_take(candidate)

        merged = sorted(candidates, key=lambda item: (-item["view_score"], item["raw_rank"]))
        for candidate in merged:
            if len(selected) >= min(20, limit):
                break
            current_chunks = sum(1 for item in selected if item["candidate_type"] == "chunk_candidate")
            max_chunks = top20_rules.get("chunk_max", 999)
            if candidate["candidate_type"] == "chunk_candidate" and current_chunks >= max_chunks:
                continue
            try_take(candidate)

    target_sequence = []
    for candidate_type, desired in target_counts.items():
        target_sequence.extend([candidate_type] * desired)
    for candidate_type in ["pattern_candidate", "vocabulary_candidate", "chunk_candidate"]:
        target_sequence.extend([candidate_type] * limit)

    type_indexes = {key: 0 for key in by_type}
    for candidate_type in target_sequence:
        if len(selected) >= limit:
            break
        bucket = by_type[candidate_type]
        while type_indexes[candidate_type] < len(bucket):
            candidate = bucket[type_indexes[candidate_type]]
            type_indexes[candidate_type] += 1
            if try_take(candidate):
                break

    merged = sorted(candidates, key=lambda item: (-item["view_score"], item["raw_rank"]))
    for candidate in merged:
        if len(selected) >= limit:
            break
        try_take(candidate)

    return selected[:limit]


def build_theme_views(candidates, metadata, warnings):
    theme_views = {}
    for theme_name in THEMES:
        theme_candidates = [deepcopy(candidate) for candidate in candidates if theme_name in candidate.get("matched_themes", [])]
        for candidate in theme_candidates:
            candidate["view_policy_applied"].append("theme_scoped_filter")
            candidate["dedup_group_id"] = f"dedup:{candidate['normalized_label']}"
            apply_view_score(candidate, "theme_scoped_view", theme_name=theme_name)
        theme_candidates = deduplicate_candidates(theme_candidates)
        theme_candidates = sorted(theme_candidates, key=lambda item: sort_key("theme_scoped_view", item))

        protected = []
        seen_labels = set()
        for required_type in ["pattern_candidate", "vocabulary_candidate"]:
            for candidate in theme_candidates:
                if candidate["candidate_type"] != required_type:
                    continue
                if candidate["normalized_label"] in seen_labels:
                    continue
                seen_labels.add(candidate["normalized_label"])
                protected.append(candidate)
                break

        remaining = [candidate for candidate in theme_candidates if candidate["raw_candidate_id"] not in {item["raw_candidate_id"] for item in protected}]
        final = finalize_view("theme_scoped_view", (protected + remaining)[:50])
        theme_views[theme_name] = final
        if len(final) < 50:
            warnings.append(f"theme_view_sparse:{theme_name.lower().replace(' ', '_')}")
    return theme_views


def build_payload():
    raw_ranking = read_json(RAW_RANKING_PATH, {})
    raw_summary = read_json(RAW_SUMMARY_PATH, {})
    quality_audit = read_json(QUALITY_AUDIT_PATH, {})
    active_candidates = raw_ranking.get("candidates", [])
    if not active_candidates:
        raise RuntimeError("raw ranking has no active candidates")

    metadata = {
        "theme_lookup": load_theme_lookup(),
        "chunk_metadata_lookup": load_chunk_metadata_lookup(),
        "pattern_lookup": load_pattern_lookup(),
        "vocab_lookup": load_vocab_lookup(),
        "chunk_lookup": load_chunk_lookup(),
    }

    prepared = []
    for raw_candidate in active_candidates:
        candidate = base_view_candidate(raw_candidate, metadata)
        candidate["matched_themes"] = sorted(
            [theme_name for theme_name in THEMES if theme_matches(candidate, theme_name, metadata["theme_lookup"], metadata["chunk_lookup"])]
        )
        prepared.append(candidate)

    warnings = []

    raw_global_candidates = [deepcopy(candidate) for candidate in prepared[: VIEW_LIMITS["raw_global_view"]]]
    for candidate in raw_global_candidates:
        candidate["view_policy_applied"].append("raw_global_passthrough")
        apply_view_score(candidate, "raw_global_view")
    raw_global_view = finalize_view("raw_global_view", raw_global_candidates)

    balanced_pool = deduplicate_candidates([deepcopy(candidate) for candidate in prepared])
    for candidate in balanced_pool:
        candidate["view_policy_applied"].append("balanced_global_mix")
        apply_view_score(candidate, "balanced_global_view")
    balanced_selected = select_with_targets(
        sorted(balanced_pool, key=lambda item: sort_key("balanced_global_view", item)),
        VIEW_LIMITS["balanced_global_view"],
        BALANCED_TARGET_COUNTS,
        top20_rules={"minimums": {"pattern_candidate": 4, "vocabulary_candidate": 6}, "chunk_max": 7},
    )
    balanced_global_view = finalize_view("balanced_global_view", balanced_selected)

    a1_pool = [
        deepcopy(candidate)
        for candidate in prepared
        if level_value(candidate["level"]) <= level_value("A1")
    ]
    for candidate in a1_pool:
        candidate["view_policy_applied"].append("a1_level_ceiling")
        candidate["duplicate_penalty"] = False
        apply_view_score(candidate, "a1_safe_view")
    a1_pool = deduplicate_candidates(a1_pool)
    a1_pool = [candidate for candidate in a1_pool if "advanced_modal_or_perfect" not in candidate["curriculum_suitability_flags"]]
    a1_pool = sorted(a1_pool, key=lambda item: sort_key("a1_safe_view", item))
    a1_selected = select_with_targets(
        a1_pool,
        VIEW_LIMITS["a1_safe_view"],
        A1_TARGET_COUNTS,
        top20_rules={"minimums": {"pattern_candidate": 5, "vocabulary_candidate": 5}, "chunk_max": 5},
    )
    a1_safe_view = finalize_view("a1_safe_view", a1_selected)

    reading_pool = deduplicate_candidates([deepcopy(candidate) for candidate in prepared])
    for candidate in reading_pool:
        candidate["view_policy_applied"].append("reading_bridge_balance")
        apply_view_score(candidate, "reading_bridge_view")
    reading_pool = [candidate for candidate in reading_pool if "advanced_modal_or_perfect" not in candidate["curriculum_suitability_flags"]]
    reading_bridge_view = finalize_view(
        "reading_bridge_view",
        select_with_targets(
            sorted(reading_pool, key=lambda item: sort_key("reading_bridge_view", item)),
            VIEW_LIMITS["reading_bridge_view"],
            {"pattern_candidate": 45, "vocabulary_candidate": 40, "chunk_candidate": 15},
        ),
    )

    dialogue_pool = deduplicate_candidates([deepcopy(candidate) for candidate in prepared])
    for candidate in dialogue_pool:
        candidate["view_policy_applied"].append("dialogue_bridge_balance")
        apply_view_score(candidate, "dialogue_bridge_view")
    dialogue_bridge_view = finalize_view(
        "dialogue_bridge_view",
        select_with_targets(
            sorted(dialogue_pool, key=lambda item: sort_key("dialogue_bridge_view", item)),
            VIEW_LIMITS["dialogue_bridge_view"],
            {"pattern_candidate": 35, "chunk_candidate": 35, "vocabulary_candidate": 30},
        ),
    )

    pattern_pool = deduplicate_candidates([deepcopy(candidate) for candidate in prepared])
    for candidate in pattern_pool:
        candidate["view_policy_applied"].append("pattern_first_priority")
        apply_view_score(candidate, "pattern_first_view")
    pattern_first_view = finalize_view("pattern_first_view", sorted(pattern_pool, key=lambda item: sort_key("pattern_first_view", item))[:100])

    vocabulary_pool = deduplicate_candidates([deepcopy(candidate) for candidate in prepared])
    for candidate in vocabulary_pool:
        candidate["view_policy_applied"].append("vocabulary_first_priority")
        apply_view_score(candidate, "vocabulary_first_view")
    vocabulary_first_view = finalize_view("vocabulary_first_view", sorted(vocabulary_pool, key=lambda item: sort_key("vocabulary_first_view", item))[:100])

    chunk_safe_pool = deduplicate_candidates([deepcopy(candidate) for candidate in prepared])
    for candidate in chunk_safe_pool:
        candidate["view_policy_applied"].append("chunk_safe_balance")
        apply_view_score(candidate, "chunk_safe_view")
    chunk_safe_pool = [
        candidate
        for candidate in chunk_safe_pool
        if candidate["candidate_type"] != "chunk_candidate"
        or "advanced_modal_or_perfect" not in candidate["curriculum_suitability_flags"]
    ]
    chunk_safe_view = finalize_view(
        "chunk_safe_view",
        select_with_targets(
            sorted(chunk_safe_pool, key=lambda item: sort_key("chunk_safe_view", item)),
            VIEW_LIMITS["chunk_safe_view"],
            {"chunk_candidate": 25, "pattern_candidate": 35, "vocabulary_candidate": 40},
        ),
    )

    dedup_pool = deduplicate_candidates([deepcopy(candidate) for candidate in prepared[:500]])
    for candidate in dedup_pool:
        candidate["view_policy_applied"].append("deduplicated_canonical_collapse")
        apply_view_score(candidate, "deduplicated_view")
    deduplicated_view = finalize_view("deduplicated_view", sorted(dedup_pool, key=lambda item: item["raw_rank"])[:100])

    theme_scoped_view = build_theme_views(prepared, metadata, warnings)

    views = {
        "raw_global_view": raw_global_view,
        "balanced_global_view": balanced_global_view,
        "a1_safe_view": a1_safe_view,
        "theme_scoped_view": theme_scoped_view,
        "reading_bridge_view": reading_bridge_view,
        "dialogue_bridge_view": dialogue_bridge_view,
        "pattern_first_view": pattern_first_view,
        "vocabulary_first_view": vocabulary_first_view,
        "chunk_safe_view": chunk_safe_view,
        "deduplicated_view": deduplicated_view,
    }

    diagnostics = {
        "source_candidate_count": len(active_candidates),
        "source_blocked_candidate_count": len(raw_ranking.get("blocked_candidates", [])),
        "raw_summary_status": raw_summary.get("status"),
        "quality_audit_status": quality_audit.get("status"),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    view_policy = {
        "limits": {"theme_scoped_view_per_theme": 50, **VIEW_LIMITS},
        "balanced_global_mix": BALANCED_TARGET_COUNTS,
        "a1_safe_mix": A1_TARGET_COUNTS,
    }

    payload = {
        "schema_version": SCHEMA_VERSION,
        "generation_mode": "static_offline_view_construction",
        "adaptive_enabled": False,
        "generated_at": diagnostics["generated_at"],
        "source": {
            "raw_ranking": "ulga/graph/static_candidate_ranking.json",
            "quality_audit": "ulga/reports/static_candidate_ranking_quality_audit.json",
            "contract": "docs/ulga/ULGA_S10E_STATIC_CANDIDATE_RANKING_BALANCING_CONTRACT_DESIGN_SCAN.md",
        },
        "principles": {
            "raw_static_ranking_is_not_curriculum_ranking": True,
            "raw_ranking_untouched": True,
            "raw_static_score_preserved": True,
            "view_score_is_downstream_only": True,
            "adaptive_enabled": False,
        },
        "view_policy": view_policy,
        "views": views,
        "diagnostics": diagnostics,
        "warnings": sorted(set(warnings)),
    }
    return payload


def top20_stats(candidates):
    top20 = candidates[:20]
    type_counts = dict(sorted(Counter(candidate["candidate_type"] for candidate in top20).items()))
    level_counts = dict(sorted(Counter(candidate["level"] for candidate in top20).items(), key=lambda item: level_value(item[0])))
    duplicates = 0
    seen = set()
    opaque_chunks = 0
    for candidate in top20:
        normalized = normalize_label(candidate["label"])
        if normalized in seen:
            duplicates += 1
        seen.add(normalized)
        if candidate["candidate_type"] == "chunk_candidate" and any(
            flag in candidate.get("curriculum_suitability_flags", [])
            for flag in ["contains_sb_sth", "contains_slash_alternative", "idiomatic_or_low_transparency", "advanced_modal_or_perfect"]
        ):
            opaque_chunks += 1
    return {
        "candidate_count": len(candidates),
        "top_20_type_distribution": type_counts,
        "top_20_level_distribution": level_counts,
        "duplicate_normalized_labels_top_20": duplicates,
        "opaque_chunk_ratio_top_20": round4(opaque_chunks / len(top20)) if top20 else 0.0,
        "warnings": [],
    }


def strip_summary_candidate(candidate):
    return {
        "candidate_type": candidate["candidate_type"],
        "label": candidate["label"],
        "level": candidate["level"],
        "view_score": candidate["view_score"],
        "raw_rank": candidate["raw_rank"],
    }


def build_summary(payload, validator_passed=True):
    views = payload["views"]
    warnings = list(payload.get("warnings", []))
    summary_views = {}

    for view_name in [
        "balanced_global_view",
        "a1_safe_view",
        "reading_bridge_view",
        "dialogue_bridge_view",
        "pattern_first_view",
        "vocabulary_first_view",
        "chunk_safe_view",
        "deduplicated_view",
    ]:
        summary_views[view_name] = top20_stats(views[view_name])

    summary_views["theme_scoped_view"] = {}
    for theme_name, candidates in views["theme_scoped_view"].items():
        entry = top20_stats(candidates)
        summary_views["theme_scoped_view"][theme_name] = entry
        if len(candidates) < 20:
            entry["warnings"].append("theme_view_under_20")
            warnings.append(f"theme_view_under_20:{theme_name.lower().replace(' ', '_')}")

    if summary_views["balanced_global_view"]["duplicate_normalized_labels_top_20"] > 0:
        warnings.append("balanced_global_view_top20_has_duplicates")
    if summary_views["a1_safe_view"]["duplicate_normalized_labels_top_20"] > 0:
        warnings.append("a1_safe_view_top20_has_duplicates")
    if summary_views["deduplicated_view"]["duplicate_normalized_labels_top_20"] > 0:
        warnings.append("deduplicated_view_top20_has_duplicates")
    if len(summary_views["balanced_global_view"]["top_20_type_distribution"]) == 1:
        warnings.append("balanced_global_view_top20_single_type")

    status = "PASS"
    if not validator_passed or payload.get("adaptive_enabled") is not False or payload["diagnostics"]["source_candidate_count"] == 0:
        status = "FAIL"
    elif warnings:
        status = "PASS_WITH_WARNINGS"

    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": status,
        "adaptive_leakage_detected": False,
        "source_candidate_count": payload["diagnostics"]["source_candidate_count"],
        "views": summary_views,
        "global_warnings": sorted(set(warnings)),
        "critical_findings": [],
        "next_recommended_task": "ULGA-S10G_StaticCandidateRankingViews_QA_Audit",
    }


def main():
    try:
        payload = build_payload()
        write_json(OUTPUT_PATH, payload)
        summary = build_summary(payload, validator_passed=True)
        write_json(SUMMARY_PATH, summary)
    except Exception as exc:
        print(f"Static Candidate Ranking Views build: FAIL - {exc}")
        return 1
    print("Static Candidate Ranking Views build: PASS")
    print(f"balanced_global_view: {len(payload['views']['balanced_global_view'])}")
    print(f"a1_safe_view: {len(payload['views']['a1_safe_view'])}")
    print(f"theme_scoped_view themes: {len(payload['views']['theme_scoped_view'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
