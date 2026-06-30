import json
import re
import statistics
import sys
from collections import Counter
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ulga.validators.validate_static_candidate_ranking import validate as validate_static_candidate_ranking
from ulga.validators.validate_static_candidate_ranking_views import validate as validate_static_candidate_ranking_views


RAW_RANKING_PATH = BASE_DIR / "ulga" / "graph" / "static_candidate_ranking.json"
RAW_SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "static_candidate_ranking_summary.json"
VIEWS_PATH = BASE_DIR / "ulga" / "graph" / "static_candidate_ranking_views.json"
VIEWS_SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "static_candidate_ranking_views_summary.json"
S10D_AUDIT_PATH = BASE_DIR / "ulga" / "reports" / "static_candidate_ranking_quality_audit.json"
REPORT_PATH = BASE_DIR / "ulga" / "reports" / "static_candidate_ranking_views_quality_audit.json"
THEME_MAPPING_PATH = BASE_DIR / "themes" / "theme_vocab_mapping.json"

SCHEMA_VERSION = "ULGA_S10G_STATIC_CANDIDATE_RANKING_VIEWS_QA_AUDIT_V1"
TOP_WINDOWS = [10, 20, 50, 100]
REQUIRED_VIEWS = [
    "raw_global_view",
    "balanced_global_view",
    "a1_safe_view",
    "theme_scoped_view",
    "reading_bridge_view",
    "dialogue_bridge_view",
    "pattern_first_view",
    "vocabulary_first_view",
    "chunk_safe_view",
    "deduplicated_view",
]
THEMES = ["Home", "Food", "School", "Travel", "Health", "Personal", "Daily Life"]
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
OPAQUE_FLAGS = {
    "contains_sb_sth",
    "contains_slash_alternative",
    "contains_bracket_alternative",
    "movable_object_pattern",
    "idiomatic_or_low_transparency",
    "label_too_long",
    "missing_theme_anchor",
    "missing_pattern_bridge",
    "missing_vocabulary_anchor",
    "advanced_modal_or_perfect",
}
THEME_KEYWORDS = {
    "Home": ["home", "house", "room", "kitchen", "bedroom", "bathroom", "living room"],
    "Food": ["food", "drink", "water", "milk", "rice", "bread", "apple", "restaurant", "eat", "dining"],
    "School": ["school", "class", "teacher", "student", "book", "desk", "pen", "pencil", "lesson"],
    "Travel": ["travel", "bus", "train", "airport", "station", "ticket", "weather", "go", "trip"],
    "Health": ["health", "body", "doctor", "head", "hand", "leg", "sick", "pain", "hurt"],
    "Personal": ["name", "family", "friend", "like", "hobby", "birthday", "age"],
    "Daily Life": ["daily", "morning", "evening", "breakfast", "lunch", "dinner", "home", "school"],
}
FRAME_PATTERN_HINTS = ["{", "?", "there is", "can you", "i have", "this is", "that is", "i "]
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


def read_json(path, default=None):
    if not path.exists():
        return default
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
    text = re.sub(r"\s+", " ", text).strip(" ./_-")
    return text.replace("sb_sth", "sb/sth")


def level_value(level):
    return CEFR_ORDER.get(level, 999)


def ratio(count, total):
    return round((count / total), 4) if total else 0.0


def mean(values):
    return round(sum(values) / len(values), 4) if values else 0.0


def median(values):
    return round(float(statistics.median(values)), 4) if values else 0.0


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


def type_distribution(candidates):
    return dict(sorted(Counter(candidate["candidate_type"] for candidate in candidates).items()))


def level_distribution(candidates):
    return dict(sorted(Counter(candidate["level"] for candidate in candidates).items(), key=lambda item: level_value(item[0])))


def duplicate_count(candidates, window=None):
    seen = set()
    duplicates = 0
    items = candidates[:window] if window else candidates
    for candidate in items:
        normalized = normalize_label(candidate["label"])
        if normalized in seen:
            duplicates += 1
        seen.add(normalized)
    return duplicates


def opaque_ratio(candidates, window):
    items = candidates[:window]
    opaque = sum(
        1
        for candidate in items
        if candidate["candidate_type"] == "chunk_candidate"
        and any(flag in OPAQUE_FLAGS for flag in candidate.get("curriculum_suitability_flags", []))
    )
    return opaque, ratio(opaque, len(items))


def score_diagnostics(candidates):
    view_scores = [candidate["view_score"] for candidate in candidates]
    raw_scores = [candidate["raw_static_score"] for candidate in candidates]
    deltas = [abs(candidate["view_score"] - candidate["raw_static_score"]) for candidate in candidates]
    gt = sum(1 for candidate in candidates if candidate["view_score"] > candidate["raw_static_score"])
    lt = sum(1 for candidate in candidates if candidate["view_score"] < candidate["raw_static_score"])
    return {
        "min_view_score": min(view_scores) if view_scores else 0.0,
        "max_view_score": max(view_scores) if view_scores else 0.0,
        "mean_view_score": mean(view_scores),
        "median_view_score": median(view_scores),
        "mean_raw_static_score": mean(raw_scores),
        "mean_abs_view_raw_delta": mean(deltas),
        "max_abs_view_raw_delta": round(max(deltas), 4) if deltas else 0.0,
        "count_view_score_gt_raw_score": gt,
        "count_view_score_lt_raw_score": lt,
        "gt_ratio": ratio(gt, len(candidates)),
        "lt_ratio": ratio(lt, len(candidates)),
    }


def frame_like_count(candidates, window):
    items = candidates[:window]
    count = 0
    for candidate in items:
        label = candidate["label"].lower()
        if candidate["candidate_type"] == "pattern_candidate" or any(hint in label for hint in FRAME_PATTERN_HINTS):
            count += 1
    return count


def load_theme_lookup():
    payload = read_json(THEME_MAPPING_PATH, {"themes": []}) or {"themes": []}
    lookup = {}
    for item in payload.get("themes", []):
        theme_id = item.get("theme_id")
        if theme_id:
            lookup[f"theme:{theme_id}"] = item
    return lookup


def theme_relevant(candidate, theme_name, theme_lookup):
    keywords = THEME_KEYWORDS[theme_name]
    haystacks = [normalize_label(candidate["label"])]
    haystacks.extend(str(entry).lower() for entry in candidate.get("source_explain", []))
    haystacks.extend(str(entry).lower() for entry in candidate.get("curriculum_suitability_flags", []))
    for theme_ref in candidate.get("theme_refs", []):
        haystacks.append(str(theme_ref).lower())
        theme_info = theme_lookup.get(theme_ref, {})
        haystacks.append(str(theme_info.get("theme_id") or "").lower())
        haystacks.append(str(theme_info.get("parent_theme") or "").lower())
        haystacks.extend(str(topic).lower() for topic in theme_info.get("primary_topics", []))
        haystacks.extend(str(topic).lower() for topic in theme_info.get("secondary_topics", []))
    return any(keyword in haystack for keyword in keywords for haystack in haystacks)


def traceability_diagnostics(views_payload, raw_ids):
    counts = {
        "missing_raw_rank_count": 0,
        "missing_raw_candidate_id_count": 0,
        "missing_raw_static_score_count": 0,
        "unmatched_raw_candidate_id_count": 0,
    }
    for view_name, view_value in views_payload["views"].items():
        iterable = view_value.values() if view_name == "theme_scoped_view" else [view_value]
        for candidates in iterable:
            for candidate in candidates:
                if candidate.get("raw_rank") is None:
                    counts["missing_raw_rank_count"] += 1
                if not candidate.get("raw_candidate_id"):
                    counts["missing_raw_candidate_id_count"] += 1
                if candidate.get("raw_static_score") is None:
                    counts["missing_raw_static_score_count"] += 1
                elif candidate["raw_candidate_id"] not in raw_ids:
                    counts["unmatched_raw_candidate_id_count"] += 1
    counts["traceability_pass"] = sum(counts.values()) == 0
    return counts


def generic_view_quality(candidates):
    windows = {}
    for window in TOP_WINDOWS:
        scoped = candidates[:window]
        opaque_count, opaque_window_ratio = opaque_ratio(candidates, window)
        windows[f"top_{window}"] = {
            "candidate_count": len(scoped),
            "type_distribution": type_distribution(scoped),
            "level_distribution": level_distribution(scoped),
            "duplicate_normalized_label_count": duplicate_count(scoped),
            "opaque_chunk_ratio": opaque_window_ratio,
            "mean_view_score": mean([candidate["view_score"] for candidate in scoped]),
            "mean_raw_static_score": mean([candidate["raw_static_score"] for candidate in scoped]),
            "opaque_chunk_count": opaque_count,
        }
    return windows


def readiness_for(view_name, warnings):
    warning_text = " ".join(warnings)
    if not warnings:
        return "READY"
    if view_name in {"reading_bridge_view", "dialogue_bridge_view"}:
        return "NEEDS_TUNING"
    if "traceability" in warning_text:
        return "NOT_READY"
    return "READY_WITH_WARNINGS"


def audit_deduplication(views_payload, raw_ids, warnings, critical_findings):
    result = {}
    targets = ["balanced_global_view", "a1_safe_view", "theme_scoped_view", "reading_bridge_view", "dialogue_bridge_view", "deduplicated_view"]
    for target in targets:
        if target == "theme_scoped_view":
            theme_result = {}
            for theme_name, candidates in views_payload["views"][target].items():
                equivalent_ids = [raw_id for candidate in candidates for raw_id in candidate.get("equivalent_raw_candidate_ids", [])]
                canonical_without_equivalents = sum(
                    1
                    for candidate in candidates
                    if candidate.get("dedup_group_id") and not candidate.get("equivalent_raw_candidate_ids")
                )
                theme_result[theme_name] = {
                    "duplicate_normalized_labels_top_20": duplicate_count(candidates, 20),
                    "duplicate_normalized_labels_top_100": duplicate_count(candidates, 100),
                    "dedup_group_count": sum(1 for candidate in candidates if candidate.get("dedup_group_id")),
                    "equivalent_raw_candidate_id_count": len(equivalent_ids),
                    "canonical_without_equivalents_count": canonical_without_equivalents,
                }
            result[target] = theme_result
            continue

        candidates = views_payload["views"][target]
        equivalent_ids = [raw_id for candidate in candidates for raw_id in candidate.get("equivalent_raw_candidate_ids", [])]
        unmatched_equivalent_ids = [raw_id for raw_id in equivalent_ids if raw_id not in raw_ids]
        canonical_without_equivalents = sum(
            1
            for candidate in candidates
            if candidate.get("dedup_group_id") and not candidate.get("equivalent_raw_candidate_ids")
        )
        entry = {
            "duplicate_normalized_labels_top_20": duplicate_count(candidates, 20),
            "duplicate_normalized_labels_top_100": duplicate_count(candidates, 100),
            "dedup_group_count": sum(1 for candidate in candidates if candidate.get("dedup_group_id")),
            "equivalent_raw_candidate_id_count": len(equivalent_ids),
            "canonical_without_equivalents_count": canonical_without_equivalents,
        }
        result[target] = entry

        if target in {"balanced_global_view", "a1_safe_view", "deduplicated_view"} and entry["duplicate_normalized_labels_top_20"] > 0:
            critical_findings.append(f"{target} top_20 has duplicate normalized labels")
        if canonical_without_equivalents > max(5, len(candidates) * 0.4):
            warnings.append(f"{target} has many canonical entries without equivalent_raw_candidate_ids")
        if unmatched_equivalent_ids:
            warnings.append(f"{target} has equivalent_raw_candidate_ids not found in raw ranking")
    return result


def audit_theme_views(theme_views, theme_lookup, warnings):
    result = {}
    for theme_name, candidates in theme_views.items():
        top20 = candidates[:20]
        relevant_count = sum(1 for candidate in top20 if theme_relevant(candidate, theme_name, theme_lookup))
        opaque_count, opaque_window_ratio = opaque_ratio(candidates, 20)
        entry = {
            "candidate_count": len(candidates),
            "top_20_type_distribution": type_distribution(top20),
            "top_20_level_distribution": level_distribution(top20),
            "top_20_theme_relevance_ratio": ratio(relevant_count, len(top20)),
            "top_20_opaque_chunk_ratio": opaque_window_ratio,
            "top_20_duplicate_normalized_label_count": duplicate_count(candidates, 20),
            "top_20_labels": [candidate["label"] for candidate in top20],
        }
        if entry["top_20_theme_relevance_ratio"] < 0.60:
            warnings.append(f"{theme_name} theme relevance ratio < 0.60")
        if top20 and not any(candidate["candidate_type"] == "pattern_candidate" for candidate in top20) and any(candidate["candidate_type"] == "pattern_candidate" for candidate in candidates):
            warnings.append(f"{theme_name} top_20 has no pattern candidates")
        if top20 and not any(candidate["candidate_type"] == "vocabulary_candidate" for candidate in top20) and any(candidate["candidate_type"] == "vocabulary_candidate" for candidate in candidates):
            warnings.append(f"{theme_name} top_20 has no vocabulary candidates")
        if entry["top_20_opaque_chunk_ratio"] > 0.40:
            warnings.append(f"{theme_name} top_20 opaque chunk ratio > 0.40")
        if entry["top_20_duplicate_normalized_label_count"] > 0:
            warnings.append(f"{theme_name} top_20 has duplicate normalized labels")
        result[theme_name] = entry
    return result


def audit_views(views_payload, raw_payload, warnings, critical_findings):
    raw_ids = {candidate["candidate_id"] for candidate in raw_payload["candidates"]}
    enough_non_chunk_a1 = sum(1 for candidate in raw_payload["candidates"] if candidate["level"] == "A1" and candidate["candidate_type"] != "chunk_candidate") >= 20
    safe_a1_chunks_deeper = any(
        candidate["candidate_type"] == "chunk_candidate"
        and candidate["level"] == "A1"
        and not any(flag in OPAQUE_FLAGS for flag in candidate.get("curriculum_suitability_flags", []))
        for candidate in views_payload["views"]["chunk_safe_view"][20:]
    )

    view_quality = {}
    score_diagnostics_map = {}
    opacity_diagnostics = {}
    readiness = {}

    for view_name in REQUIRED_VIEWS:
        if view_name == "theme_scoped_view":
            continue
        candidates = views_payload["views"][view_name]
        top20 = candidates[:20]
        entry = generic_view_quality(candidates)
        entry["candidate_count"] = len(candidates)
        entry["warnings"] = []
        view_quality[view_name] = entry
        score_diagnostics_map[view_name] = score_diagnostics(candidates)
        opacity_top20_count, opacity_top20_ratio = opaque_ratio(candidates, 20)
        opacity_top100_count, opacity_top100_ratio = opaque_ratio(candidates, 100)
        opacity_diagnostics[view_name] = {
            "opaque_chunk_count_top_20": opacity_top20_count,
            "opaque_chunk_ratio_top_20": opacity_top20_ratio,
            "opaque_chunk_count_top_100": opacity_top100_count,
            "opaque_chunk_ratio_top_100": opacity_top100_ratio,
        }

        diag = score_diagnostics_map[view_name]
        if diag["mean_abs_view_raw_delta"] > 0.15:
            entry["warnings"].append("mean_abs_view_raw_delta > 0.15")
        if diag["max_abs_view_raw_delta"] > 0.35:
            entry["warnings"].append("max_abs_view_raw_delta > 0.35")
        if diag["gt_ratio"] > 0.80:
            entry["warnings"].append("more than 80% of view_score values exceed raw_static_score")
        if diag["lt_ratio"] > 0.80:
            entry["warnings"].append("more than 80% of view_score values are below raw_static_score")

        if view_name == "balanced_global_view":
            types = type_distribution(top20)
            top100_types = type_distribution(candidates[:100])
            if types.get("chunk_candidate", 0) == 0:
                entry["warnings"].append("chunk_candidate == 0 in top_20")
            if ratio(top100_types.get("chunk_candidate", 0), len(candidates[:100])) < 0.05:
                entry["warnings"].append("chunk_candidate ratio < 0.05 in top_100")
            if ratio(types.get("pattern_candidate", 0) + types.get("vocabulary_candidate", 0), len(top20)) > 0.95:
                entry["warnings"].append("pattern_candidate + vocabulary_candidate ratio > 0.95 in top_20")
        elif view_name == "a1_safe_view":
            if any(level_value(candidate["level"]) > level_value("A1") for candidate in candidates):
                critical_findings.append("a1_safe_view includes levels above A1")
            if safe_a1_chunks_deeper and type_distribution(top20).get("chunk_candidate", 0) == 0:
                entry["warnings"].append("chunk_candidate == 0 in top_20 while safe A1 chunks exist deeper in A1 pool")
            if frame_like_count(top20, len(top20)) < 5:
                entry["warnings"].append("top_20 is too lexical and lacks usable sentence patterns")
            if any("advanced_modal_or_perfect" in candidate.get("curriculum_suitability_flags", []) for candidate in top20):
                entry["warnings"].append("top_20 contains advanced modal/perfect signals")
            if any("contains_sb_sth" in candidate.get("curriculum_suitability_flags", []) for candidate in top20):
                entry["warnings"].append("top_20 contains sb/sth labels")
            if any("contains_slash_alternative" in candidate.get("curriculum_suitability_flags", []) for candidate in top20):
                entry["warnings"].append("top_20 contains slash alternatives")
            if enough_non_chunk_a1 and ratio(type_distribution(top20).get("chunk_candidate", 0), len(top20)) > 0.25:
                entry["warnings"].append("chunk ratio > 0.25 in top_20")
            if opacity_diagnostics[view_name]["opaque_chunk_ratio_top_20"] > 0.15:
                entry["warnings"].append("opaque_chunk_ratio_top_20 > 0.15")
        elif view_name == "reading_bridge_view":
            types = type_distribution(top20)
            theme_ref_empty_ratio = ratio(sum(1 for candidate in top20 if not candidate.get("theme_refs")), len(top20))
            if ratio(types.get("vocabulary_candidate", 0), len(top20)) > 0.80:
                entry["warnings"].append("vocabulary_candidate ratio > 0.80 in top_20")
            if types.get("pattern_candidate", 0) < 4:
                entry["warnings"].append("pattern_candidate count < 4 in top_20")
            if ratio(types.get("chunk_candidate", 0), len(top20)) > 0.25:
                entry["warnings"].append("chunk_candidate ratio > 0.25 in top_20")
            if theme_ref_empty_ratio > 0.70:
                entry["warnings"].append("theme_refs are mostly empty in top_20")
            if frame_like_count(top20, len(top20)) < 4:
                entry["warnings"].append("top_20 lacks sentence-frame-like patterns")
            if opacity_diagnostics[view_name]["opaque_chunk_ratio_top_20"] > 0.25:
                entry["warnings"].append("opaque_chunk_ratio_top_20 > 0.25")
        elif view_name == "dialogue_bridge_view":
            types = type_distribution(top20)
            sb_sth_count = sum(1 for candidate in top20 if "contains_sb_sth" in candidate.get("curriculum_suitability_flags", []))
            slash_count = sum(1 for candidate in top20 if "contains_slash_alternative" in candidate.get("curriculum_suitability_flags", []))
            question_like = sum(1 for candidate in top20 if "?" in candidate["label"] or candidate["candidate_type"] == "pattern_candidate")
            if ratio(types.get("chunk_candidate", 0), len(top20)) > 0.70:
                entry["warnings"].append("chunk_candidate ratio > 0.70 in top_20")
            if types.get("pattern_candidate", 0) < 4:
                entry["warnings"].append("pattern_candidate count < 4 in top_20")
            if opacity_diagnostics[view_name]["opaque_chunk_ratio_top_20"] > 0.40:
                entry["warnings"].append("opaque_chunk_ratio_top_20 > 0.40")
            if sb_sth_count + slash_count > 6:
                entry["warnings"].append("top_20 contains many sb/sth or slash alternatives")
            if question_like < 4:
                entry["warnings"].append("top_20 lacks question/answer or sentence-frame support")
        elif view_name == "pattern_first_view":
            if type_distribution(top20).get("pattern_candidate", 0) < type_distribution(top20).get("vocabulary_candidate", 0):
                entry["warnings"].append("pattern_first_view is not pattern dominant in top_20")
        elif view_name == "vocabulary_first_view":
            if type_distribution(top20).get("vocabulary_candidate", 0) < 15:
                entry["warnings"].append("vocabulary_first_view is not strongly vocabulary dominant in top_20")
        elif view_name == "chunk_safe_view":
            if type_distribution(top20).get("chunk_candidate", 0) == 0:
                entry["warnings"].append("chunk_safe_view lacks chunk presence in top_20")
            if opacity_diagnostics[view_name]["opaque_chunk_ratio_top_20"] > 0.25:
                entry["warnings"].append("opaque_chunk_ratio_top_20 > 0.25")
        elif view_name == "deduplicated_view":
            if duplicate_count(candidates, 20) > 0:
                critical_findings.append("deduplicated_view top_20 has duplicate normalized labels")

        warnings.extend(entry["warnings"])
        readiness[view_name] = readiness_for(view_name, entry["warnings"])

    return view_quality, score_diagnostics_map, opacity_diagnostics, readiness


def recommendations_for(warnings):
    recommendations = []
    joined = " ".join(warnings)
    if "chunk_candidate == 0 in top_20" in joined or "pattern_candidate + vocabulary_candidate ratio > 0.95 in top_20" in joined:
        recommendations.append("Design a chunk reinsertion policy so balanced and A1-safe views can expose a small number of safe concrete chunks without returning to chunk dominance.")
    if "vocabulary_candidate ratio > 0.80 in top_20" in joined or "pattern_candidate count < 4 in top_20" in joined:
        recommendations.append("Design a reading-bridge view contract that enforces sentence-frame support alongside lexical coverage.")
    if "chunk_candidate ratio > 0.70 in top_20" in joined or "opaque_chunk_ratio_top_20 > 0.40" in joined:
        recommendations.append("Design a dialogue-bridge tuning contract that preserves conversational chunks while raising pattern support and lowering opaque chunk load.")
    if "theme relevance ratio < 0.60" in joined:
        recommendations.append("Tighten theme-scoped view relevance rules before bridge consumers use theme windows as topic truth.")
    if not recommendations:
        recommendations.append("Use the current S10F views as a static baseline, but add bridge-specific tuning contracts before content-facing downstream modules consume them directly.")
    return recommendations


def status_for(required_views_present, traceability_pass, adaptive_leakage_detected, critical_findings, warnings, view_count):
    if adaptive_leakage_detected or not required_views_present or not traceability_pass or critical_findings or view_count == 0:
        return "FAIL"
    if warnings:
        return "PASS_WITH_WARNINGS"
    return "PASS"


def run_audit():
    if not validate_static_candidate_ranking():
        raise RuntimeError("S10C ranking validator failed")
    if not validate_static_candidate_ranking_views():
        raise RuntimeError("S10F views validator failed")

    views_payload = read_json(VIEWS_PATH, {})
    views_summary = read_json(VIEWS_SUMMARY_PATH, {})
    raw_payload = read_json(RAW_RANKING_PATH, {})
    raw_summary = read_json(RAW_SUMMARY_PATH, {})
    s10d_audit = read_json(S10D_AUDIT_PATH, {})
    theme_lookup = load_theme_lookup()

    warnings = []
    critical_findings = []

    required_views_present = all(
        (
            view_name in views_payload.get("views", {})
            if view_name != "theme_scoped_view"
            else isinstance(views_payload.get("views", {}).get(view_name), dict)
            and all(theme in views_payload["views"][view_name] for theme in THEMES)
        )
        for view_name in REQUIRED_VIEWS
    )
    if not required_views_present:
        critical_findings.append("required views missing")

    raw_ids = {candidate["candidate_id"] for candidate in raw_payload.get("candidates", [])}
    traceability = traceability_diagnostics(views_payload, raw_ids)
    if not traceability["traceability_pass"]:
        critical_findings.append("raw traceability broken")

    adaptive_leakage_detected, leakage_source = recursive_forbidden_scan(views_payload)
    if adaptive_leakage_detected:
        critical_findings.append(f"adaptive leakage found in source views: {leakage_source}")

    view_quality, score_diag, opacity_diag, readiness = audit_views(views_payload, raw_payload, warnings, critical_findings)
    theme_relevance = audit_theme_views(views_payload["views"]["theme_scoped_view"], theme_lookup, warnings)
    dedup_diag = audit_deduplication(views_payload, raw_ids, warnings, critical_findings)

    view_count = sum(
        len(value) if isinstance(value, list) else sum(len(items) for items in value.values())
        for value in views_payload.get("views", {}).values()
    )

    overall = {
        "required_views_present": required_views_present,
        "raw_traceability_pass": traceability["traceability_pass"],
        "view_count": view_count,
        "s10f_summary_status": views_summary.get("status"),
        "s10c_summary_status": raw_summary.get("status"),
        "s10d_quality_status": s10d_audit.get("status"),
    }

    report = {
        "schema_version": SCHEMA_VERSION,
        "audit_mode": "read_only_view_quality_audit",
        "source_views_file": "ulga/graph/static_candidate_ranking_views.json",
        "source_summary_file": "ulga/reports/static_candidate_ranking_views_summary.json",
        "status": "PASS_WITH_WARNINGS",
        "adaptive_leakage_detected": adaptive_leakage_detected,
        "overall": overall,
        "traceability_diagnostics": traceability,
        "view_quality": {
            "balanced_global_view": view_quality["balanced_global_view"],
            "a1_safe_view": view_quality["a1_safe_view"],
            "reading_bridge_view": view_quality["reading_bridge_view"],
            "dialogue_bridge_view": view_quality["dialogue_bridge_view"],
            "theme_scoped_view": theme_relevance,
            "pattern_first_view": view_quality["pattern_first_view"],
            "vocabulary_first_view": view_quality["vocabulary_first_view"],
            "chunk_safe_view": view_quality["chunk_safe_view"],
            "deduplicated_view": view_quality["deduplicated_view"],
        },
        "score_diagnostics": score_diag,
        "deduplication_diagnostics": dedup_diag,
        "opacity_diagnostics": opacity_diag,
        "theme_relevance_diagnostics": theme_relevance,
        "downstream_readiness": readiness | {"theme_scoped_view": readiness_for("theme_scoped_view", [warning for warning in warnings if "theme " in warning.lower() or "top_20 has no pattern candidates" in warning.lower()])},
        "critical_findings": critical_findings,
        "warnings": warnings,
        "recommendations": recommendations_for(warnings),
        "next_recommended_task": "ULGA-S10H_StaticRankingBridgeReadiness_DesignScan",
    }

    report["status"] = status_for(
        required_views_present=report["overall"]["required_views_present"],
        traceability_pass=report["overall"]["raw_traceability_pass"],
        adaptive_leakage_detected=report["adaptive_leakage_detected"],
        critical_findings=report["critical_findings"],
        warnings=report["warnings"],
        view_count=report["overall"]["view_count"],
    )

    audit_leakage_detected, leakage_source = recursive_forbidden_scan(report)
    if audit_leakage_detected:
        report["adaptive_leakage_detected"] = True
        report["critical_findings"].append(f"adaptive leakage found in audit output: {leakage_source}")
        report["status"] = "FAIL"

    write_json(REPORT_PATH, report)
    return report


def main():
    try:
        report = run_audit()
    except Exception as exc:
        print(f"Static Candidate Ranking Views quality audit: FAIL - {exc}")
        return 1
    print(f"Static Candidate Ranking Views quality audit: {report['status']}")
    print(f"Required views present: {report['overall']['required_views_present']}")
    print(f"Raw traceability pass: {report['overall']['raw_traceability_pass']}")
    print(f"Critical findings: {len(report['critical_findings'])}")
    print(f"Warnings: {len(report['warnings'])}")
    return 0 if report["status"] != "FAIL" else 1


if __name__ == "__main__":
    sys.exit(main())
