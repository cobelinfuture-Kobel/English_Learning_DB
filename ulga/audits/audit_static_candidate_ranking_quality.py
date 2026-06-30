import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ulga.validators.validate_static_candidate_ranking import validate as validate_static_candidate_ranking


RANKING_PATH = BASE_DIR / "ulga" / "graph" / "static_candidate_ranking.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "static_candidate_ranking_summary.json"
REPORT_PATH = BASE_DIR / "ulga" / "reports" / "static_candidate_ranking_quality_audit.json"
THEME_MAPPING_PATH = BASE_DIR / "themes" / "theme_vocab_mapping.json"
CHUNK_METADATA_PATH = BASE_DIR / "ulga" / "graph" / "chunk_grammar_metadata.json"

SCHEMA_VERSION = "ULGA_S10D_STATIC_CANDIDATE_RANKING_QA_AUDIT_V1"
TOP_WINDOWS = [10, 20, 50, 100, 500]
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
COMPONENT_KEYS = [
    "dependency_readiness_score",
    "frequency_score",
    "theme_spiral_score",
    "reinforcement_score",
    "authority_confidence_score",
]
GENERIC_EXPLAIN_TERMS = {"default", "unknown", "fallback", "inferred", "no_signal"}
INFERRED_SIGNAL_TERMS = {"inferred", "unknown", "fallback", "proxy", "rule_based", "default"}
LEVEL_ORDER = {"A1": 0, "A2": 1, "B1": 2, "B2": 3, "C1": 4, "C2": 5}
THEME_KEYWORDS = {
    "Home": ["home", "homes", "neighborhood", "daily_life", "daily life"],
    "Food": ["food", "dining", "drink"],
    "School": ["school", "education", "classroom", "academic"],
    "Travel": ["travel", "airport", "transport", "consumption"],
    "Health": ["health", "medical", "body"],
    "Personal": ["personal", "social", "greetings", "interests", "abilities"],
    "Daily Life": ["daily_life", "daily life", "routines", "local_environment"],
}


def read_json(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False, sort_keys=False)
        handle.write("\n")


def normalize_label(label):
    text = str(label or "").lower()
    text = text.replace("_", " ")
    text = re.sub(r":safe_chunk_\d+", "", text)
    text = re.sub(r"\bsafe chunk \d+\b", "", text)
    text = re.sub(r"[(){}\[\].,;:!?]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def ratio(count, total):
    return round((count / total), 4) if total else 0.0


def distribution(items, key):
    return dict(sorted(Counter(item.get(key) for item in items).items()))


def mean(values):
    return round(sum(values) / len(values), 4) if values else 0.0


def median(values):
    return round(float(statistics.median(values)), 4) if values else 0.0


def contains_adaptive_keyword(payload):
    if isinstance(payload, dict):
        for key, value in payload.items():
            if any(token in str(key).lower() for token in FORBIDDEN_ADAPTIVE_KEYWORDS):
                return True, str(key)
            found, source = contains_adaptive_keyword(value)
            if found:
                return True, source
        return False, None
    if isinstance(payload, list):
        for item in payload:
            found, source = contains_adaptive_keyword(item)
            if found:
                return True, source
        return False, None
    if isinstance(payload, str):
        lowered = payload.lower()
        for token in FORBIDDEN_ADAPTIVE_KEYWORDS:
            if token in lowered:
                return True, payload
    return False, None


def build_theme_lookup(theme_payload):
    lookup = {}
    for item in theme_payload.get("themes", []) if isinstance(theme_payload, dict) else []:
        if not isinstance(item, dict):
            continue
        theme_id = item.get("theme_id")
        if theme_id:
            lookup[f"theme:{theme_id}"] = {
                "theme_id": theme_id,
                "parent_theme": str(item.get("parent_theme") or ""),
                "level": str(item.get("level") or ""),
            }
    return lookup


def build_chunk_metadata_lookup(chunk_metadata):
    lookup = {}
    for item in chunk_metadata if isinstance(chunk_metadata, list) else []:
        if isinstance(item, dict) and item.get("chunk_id"):
            lookup[item["chunk_id"]] = item
    return lookup


def looks_opaque_or_advanced(label):
    normalized = normalize_label(label)
    advanced_patterns = [
        r"\bsb\b",
        r"\bsth\b",
        r"/",
        r"\bwould\b",
        r"\bmodal\b",
        r"\bperfect\b",
        r"\bconditional\b",
        r"\betc\b",
    ]
    return any(re.search(pattern, normalized) for pattern in advanced_patterns)


def candidate_type_window(candidates):
    total = len(candidates)
    counts = Counter(candidate["candidate_type"] for candidate in candidates)
    return {
        "counts": dict(sorted(counts.items())),
        "ratios": {key: ratio(value, total) for key, value in sorted(counts.items())},
    }


def level_window(candidates):
    total = len(candidates)
    counts = Counter(candidate["level"] for candidate in candidates)
    return {
        "counts": dict(sorted(counts.items(), key=lambda item: LEVEL_ORDER.get(item[0], 999))),
        "ratios": {key: ratio(value, total) for key, value in sorted(counts.items(), key=lambda item: LEVEL_ORDER.get(item[0], 999))},
    }


def audit_top_n_windows(candidates, warnings, critical_findings):
    result = {}
    for top_n in TOP_WINDOWS:
        window = candidates[:top_n]
        type_data = candidate_type_window(window)
        level_data = level_window(window)
        labels = [candidate["label"] for candidate in window]
        result[f"top_{top_n}"] = {
            "candidate_count": len(window),
            "candidate_type_distribution": type_data["counts"],
            "candidate_type_ratios": type_data["ratios"],
            "level_distribution": level_data["counts"],
            "level_ratios": level_data["ratios"],
            "labels": labels,
        }

    top_20_ratios = result["top_20"]["candidate_type_ratios"]
    top_50_ratios = result["top_50"]["candidate_type_ratios"]
    top_100_ratios = result["top_100"]["candidate_type_ratios"]

    if top_20_ratios.get("chunk_candidate", 0.0) > 0.70:
        warnings.append("chunk_candidate ratio > 0.70 in top_20")
    if top_50_ratios.get("chunk_candidate", 0.0) > 0.60:
        warnings.append("chunk_candidate ratio > 0.60 in top_50")
    if top_100_ratios.get("pattern_candidate", 0.0) < 0.10:
        warnings.append("pattern_candidate ratio < 0.10 in top_100")
    if top_100_ratios.get("vocabulary_candidate", 0.0) < 0.20:
        warnings.append("vocabulary_candidate ratio < 0.20 in top_100")
    if len(result["top_20"]["candidate_type_distribution"]) == 1:
        critical_findings.append("top_20 contains only one candidate_type")

    return result


def audit_level_distribution(candidates, warnings):
    top_20 = candidates[:20]
    top_100 = candidates[:100]
    a1_only = [candidate for candidate in candidates if candidate.get("level") == "A1"]
    a1_a2 = [candidate for candidate in candidates if candidate.get("level") in {"A1", "A2"}]

    result = {
        "all_active": level_window(candidates),
        "top_20": level_window(top_20),
        "top_100": level_window(top_100),
        "A1_only": level_window(a1_only),
        "A1_A2": level_window(a1_a2),
    }

    advanced_top_100 = sum(result["top_100"]["counts"].get(level, 0) for level in ["B2", "C1", "C2"])
    if ratio(advanced_top_100, len(top_100)) > 0.5:
        warnings.append("B2/C1/C2 dominate top_100")
    if result["top_100"]["ratios"].get("A1", 0.0) < 0.10:
        warnings.append("A1 candidates are under 10% of top_100")

    return result


def audit_a1_quality(candidates, chunk_metadata_lookup, warnings):
    a1_candidates = [candidate for candidate in candidates if candidate.get("level") == "A1"]
    a1_top_20 = a1_candidates[:20]
    a1_top_50 = a1_candidates[:50]
    opaque_chunk_count = sum(
        1
        for candidate in a1_top_20
        if candidate["candidate_type"] == "chunk_candidate" and looks_opaque_or_advanced(candidate["label"])
    )
    component_averages = {
        key: mean([candidate["score_breakdown"][key] for candidate in a1_candidates])
        for key in COMPONENT_KEYS
    }
    result = {
        "a1_candidate_count": len(a1_candidates),
        "a1_top_20": [
            {
                "rank": candidate["rank"],
                "candidate_id": candidate["candidate_id"],
                "candidate_type": candidate["candidate_type"],
                "label": candidate["label"],
                "static_score": candidate["static_score"],
            }
            for candidate in a1_top_20
        ],
        "a1_type_distribution": distribution(a1_candidates, "candidate_type"),
        "a1_level_distribution": distribution(a1_candidates, "level"),
        "a1_theme_distribution": dict(
            sorted(
                Counter(
                    theme
                    for candidate in a1_candidates
                    for theme in candidate.get("theme_refs", [])
                ).items()
            )
        ),
        "a1_score_component_averages": component_averages,
        "opaque_chunk_ratio_in_a1_top_20": ratio(opaque_chunk_count, len(a1_top_20)),
        "warnings": [],
    }

    if a1_top_20 and all(candidate["candidate_type"] == "chunk_candidate" for candidate in a1_top_20):
        result["warnings"].append("A1 top_20 is entirely chunk_candidate")
    if ratio(opaque_chunk_count, len(a1_top_20)) > 0.5:
        result["warnings"].append("A1 top_20 contains mostly opaque idiomatic chunks")
    if not any(candidate["candidate_type"] == "pattern_candidate" for candidate in a1_top_50):
        result["warnings"].append("A1 pattern candidates are absent from A1 top_50")
    if not any(candidate["candidate_type"] == "vocabulary_candidate" for candidate in a1_top_50):
        result["warnings"].append("A1 vocabulary candidates are absent from A1 top_50")

    warnings.extend(result["warnings"])
    return result


def theme_match(theme_ref, theme_info, keywords):
    haystacks = [
        str(theme_ref or "").lower(),
        str((theme_info or {}).get("theme_id") or "").lower(),
        str((theme_info or {}).get("parent_theme") or "").lower(),
    ]
    return any(keyword in haystack for haystack in haystacks for keyword in keywords)


def audit_theme_quality(candidates, theme_lookup, warnings):
    result = {}
    for theme_name, keywords in THEME_KEYWORDS.items():
        filtered = []
        for candidate in candidates:
            theme_refs = candidate.get("theme_refs", [])
            if any(theme_match(theme_ref, theme_lookup.get(theme_ref), keywords) for theme_ref in theme_refs):
                filtered.append(candidate)
        top_20 = filtered[:20]
        entry = {
            "candidate_count": len(filtered),
            "top_20_type_distribution": distribution(top_20, "candidate_type"),
            "top_20_level_distribution": distribution(top_20, "level"),
            "top_20_labels": [candidate["label"] for candidate in top_20],
            "warnings": [],
        }
        if top_20 and not any(candidate["candidate_type"] == "pattern_candidate" for candidate in top_20):
            entry["warnings"].append(f"{theme_name} view has no pattern candidates")
        if top_20 and not any(candidate["candidate_type"] == "vocabulary_candidate" for candidate in top_20):
            entry["warnings"].append(f"{theme_name} view has no vocabulary candidates")
        if top_20:
            unrelated = [
                candidate["label"]
                for candidate in top_20
                if candidate["candidate_type"] == "chunk_candidate" and looks_opaque_or_advanced(candidate["label"])
            ]
            if ratio(len(unrelated), len(top_20)) > 0.5:
                entry["warnings"].append(f"{theme_name} view top_20 is dominated by unrelated labels")
        warnings.extend(entry["warnings"])
        result[theme_name] = entry
    return result


def audit_score_components(candidates, warnings):
    result = {}
    active_count = len(candidates)
    top_100 = candidates[:100]
    for component in COMPONENT_KEYS:
        values = [candidate["score_breakdown"][component] for candidate in candidates]
        top_100_values = [candidate["score_breakdown"][component] for candidate in top_100]
        identical_ratio = ratio(max(Counter(values).values(), default=0), active_count)
        component_result = {
            "min": round(min(values), 4) if values else 0.0,
            "max": round(max(values), 4) if values else 0.0,
            "mean": mean(values),
            "median": median(values),
            "count_at_1_0": sum(1 for value in values if value == 1.0),
            "count_at_0_0": sum(1 for value in values if value == 0.0),
            "top_100_mean": mean(top_100_values),
            "identical_value_ratio": identical_ratio,
        }
        result[component] = component_result
        if ratio(sum(1 for value in top_100_values if value == 1.0), len(top_100_values)) > 0.80:
            warnings.append(f"{component} is 1.0 for more than 80% of top_100")
        if identical_ratio > 0.80:
            warnings.append(f"{component} is identical for more than 80% of active candidates")
    return result


def audit_inferred_scores(candidates, warnings):
    total_explain_entries = 0
    inferred_entries = 0
    top_100_entries = 0
    top_100_inferred_entries = 0
    for index, candidate in enumerate(candidates):
        explain_entries = candidate.get("explain", [])
        for entry in explain_entries:
            total_explain_entries += 1
            if any(term in str(entry).lower() for term in INFERRED_SIGNAL_TERMS):
                inferred_entries += 1
            if index < 100:
                top_100_entries += 1
                if any(term in str(entry).lower() for term in INFERRED_SIGNAL_TERMS):
                    top_100_inferred_entries += 1

    result = {
        "inferred_signal_count": inferred_entries,
        "inferred_signal_ratio": ratio(inferred_entries, total_explain_entries),
        "top_100_inferred_signal_ratio": ratio(top_100_inferred_entries, top_100_entries),
    }
    if result["top_100_inferred_signal_ratio"] > 0.50:
        warnings.append("top_100_inferred_signal_ratio > 0.50")
    return result


def audit_blocked_candidates(blocked_candidates, warnings):
    block_reason_distribution = Counter(
        reason
        for candidate in blocked_candidates
        for reason in candidate.get("block_reasons", [])
    )
    result = {
        "blocked_candidate_count": len(blocked_candidates),
        "block_reason_distribution": dict(sorted(block_reason_distribution.items())),
        "blocked_candidate_type_distribution": distribution(blocked_candidates, "candidate_type"),
        "blocked_level_distribution": dict(sorted(Counter(candidate.get("level") for candidate in blocked_candidates).items(), key=lambda item: LEVEL_ORDER.get(item[0], 999))),
    }

    if block_reason_distribution:
        dominant_reason, dominant_count = block_reason_distribution.most_common(1)[0]
        if ratio(dominant_count, len(blocked_candidates)) > 0.70:
            warnings.append(f"one block reason accounts for more than 70% of all blocks: {dominant_reason}")
        if "schema_invalid" == dominant_reason:
            warnings.append("manual review blocks dominate")
        if dominant_reason == "not_generator_allowed":
            warnings.append("generator-disallowed blocks dominate")
        if dominant_reason == "forbidden_adaptive_feature_detected":
            warnings.append("forbidden-token blocks appear unexpectedly high")
    return result


def audit_explain_quality(candidates, warnings):
    explain_missing_count = 0
    explain_empty_count = 0
    explain_lengths = []
    top_100_distribution = Counter()
    generic_top_100 = 0

    for index, candidate in enumerate(candidates):
        if "explain" not in candidate:
            explain_missing_count += 1
            continue
        explain = candidate.get("explain")
        if not explain:
            explain_empty_count += 1
            continue
        explain_lengths.append(len(explain))
        if index < 100:
            for entry in explain:
                top_100_distribution[entry] += 1
                if any(term in str(entry).lower() for term in GENERIC_EXPLAIN_TERMS):
                    generic_top_100 += 1

    result = {
        "explain_missing_count": explain_missing_count,
        "explain_empty_count": explain_empty_count,
        "average_explain_length": mean(explain_lengths),
        "top_100_explain_distribution": dict(top_100_distribution.most_common(20)),
        "top_100_generic_explain_ratio": ratio(generic_top_100, sum(top_100_distribution.values())),
    }
    if explain_empty_count > 0 or explain_missing_count > 0:
        warnings.append("any active candidate has empty explain")
    if result["top_100_generic_explain_ratio"] > 0.30:
        warnings.append("top_100 explanations are too generic")
    return result


def audit_duplicate_risk(candidates, warnings):
    top_20 = candidates[:20]
    top_100 = candidates[:100]
    top_20_normalized = [normalize_label(candidate["label"]) for candidate in top_20]
    top_100_normalized = [normalize_label(candidate["label"]) for candidate in top_100]
    top_20_duplicates = [label for label, count in Counter(top_20_normalized).items() if count > 1]
    duplicate_occurrences = sum(count - 1 for count in Counter(top_100_normalized).values() if count > 1)
    result = {
        "top_20_duplicate_normalized_labels": sorted(top_20_duplicates),
        "top_20_duplicate_count": len(top_20_duplicates),
        "top_100_duplicate_normalized_label_ratio": ratio(duplicate_occurrences, len(top_100_normalized)),
    }
    if top_20_duplicates:
        warnings.append("top_20 contains duplicate normalized labels")
    if result["top_100_duplicate_normalized_label_ratio"] > 0.15:
        warnings.append("top_100 duplicate normalized label ratio > 0.15")
    return result


def status_for(critical_findings, warnings, adaptive_leakage_detected, active_candidate_count):
    if adaptive_leakage_detected or active_candidate_count == 0:
        return "FAIL"
    if critical_findings or warnings:
        return "PASS_WITH_WARNINGS"
    return "PASS"


def build_recommendations(warnings):
    recommendations = []
    if any("chunk_candidate ratio" in warning or "one candidate_type" in warning for warning in warnings):
        recommendations.append("Design a candidate-type balancing contract for downstream ranking views before any consumer uses top-N as curriculum truth.")
    if any("A1" in warning for warning in warnings):
        recommendations.append("Design an A1-safe window policy that prefers explicit vocabulary and pattern coverage before opaque chunk-heavy windows.")
    if any("duplicate" in warning for warning in warnings):
        recommendations.append("Add duplicate-label suppression and normalized-label de-dup rules to a future query/balancing contract.")
    if any("inferred" in warning for warning in warnings):
        recommendations.append("Separate direct authority signals from inferred fallback signals in future balancing/query contracts.")
    if not recommendations:
        recommendations.append("Keep S10C as baseline and document current ranking behavior before any downstream balancing contract.")
    return recommendations


def run_audit():
    validator_passed = validate_static_candidate_ranking()
    if not validator_passed:
        raise RuntimeError("S10C ranking validator failed")
    ranking = read_json(RANKING_PATH)
    summary = read_json(SUMMARY_PATH)
    theme_payload = read_json(THEME_MAPPING_PATH) if THEME_MAPPING_PATH.exists() else {"themes": []}
    chunk_metadata = read_json(CHUNK_METADATA_PATH) if CHUNK_METADATA_PATH.exists() else []

    candidates = ranking.get("candidates", [])
    blocked_candidates = ranking.get("blocked_candidates", [])
    warnings = []
    critical_findings = []
    theme_lookup = build_theme_lookup(theme_payload)
    chunk_metadata_lookup = build_chunk_metadata_lookup(chunk_metadata)

    top_n_quality = audit_top_n_windows(candidates, warnings, critical_findings)
    level_distribution = audit_level_distribution(candidates, warnings)
    a1_quality = audit_a1_quality(candidates, chunk_metadata_lookup, warnings)
    theme_quality = audit_theme_quality(candidates, theme_lookup, warnings)
    score_component_diagnostics = audit_score_components(candidates, warnings)
    inferred_score_diagnostics = audit_inferred_scores(candidates, warnings)
    blocked_candidate_diagnostics = audit_blocked_candidates(blocked_candidates, warnings)
    explain_quality = audit_explain_quality(candidates, warnings)
    duplicate_risk = audit_duplicate_risk(candidates, warnings)

    adaptive_leakage_detected, leakage_source = contains_adaptive_keyword(ranking)
    if adaptive_leakage_detected:
        critical_findings.append(f"adaptive leakage found in source ranking: {leakage_source}")

    report = {
        "schema_version": SCHEMA_VERSION,
        "audit_mode": "read_only_quality_audit",
        "source_ranking_file": "ulga/graph/static_candidate_ranking.json",
        "source_summary_file": "ulga/reports/static_candidate_ranking_summary.json",
        "status": "PASS_WITH_WARNINGS",
        "adaptive_leakage_detected": adaptive_leakage_detected,
        "overall": {
            "candidate_count": summary.get("candidate_count", len(candidates) + len(blocked_candidates)),
            "active_candidate_count": summary.get("active_candidate_count", len(candidates)),
            "blocked_candidate_count": summary.get("blocked_candidate_count", len(blocked_candidates)),
        },
        "top_n_quality": top_n_quality,
        "level_distribution": level_distribution,
        "a1_quality": a1_quality,
        "theme_quality": theme_quality,
        "score_component_diagnostics": score_component_diagnostics,
        "inferred_score_diagnostics": inferred_score_diagnostics,
        "blocked_candidate_diagnostics": blocked_candidate_diagnostics,
        "explain_quality": explain_quality,
        "duplicate_risk": duplicate_risk,
        "critical_findings": critical_findings,
        "warnings": warnings,
        "recommendations": build_recommendations(warnings),
        "next_recommended_task": "ULGA-S10E_StaticCandidateRanking_BalancingContract_DesignScan",
    }

    report["status"] = status_for(
        critical_findings=report["critical_findings"],
        warnings=report["warnings"],
        adaptive_leakage_detected=report["adaptive_leakage_detected"],
        active_candidate_count=report["overall"]["active_candidate_count"],
    )

    audit_leakage_detected, leakage_source = contains_adaptive_keyword(report)
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
        print(f"Static Candidate Ranking quality audit: FAIL - {exc}")
        return 1
    print(f"Static Candidate Ranking quality audit: {report['status']}")
    print(f"Active candidates: {report['overall']['active_candidate_count']}")
    print(f"Critical findings: {len(report['critical_findings'])}")
    print(f"Warnings: {len(report['warnings'])}")
    return 0 if report["status"] != "FAIL" else 1


if __name__ == "__main__":
    sys.exit(main())
