import json
import sys
from collections import Counter
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

LEARNING_OPPORTUNITIES_PATH = BASE_DIR / "ulga" / "graph" / "learning_opportunities.json"
REINFORCEMENT_SIGNAL_PATH = BASE_DIR / "ulga" / "graph" / "reinforcement_signal.json"
DEPENDENCY_GRAPH_PATH = BASE_DIR / "ulga" / "graph" / "dependency_graph.json"
VOCABULARY_NODES_PATH = BASE_DIR / "ulga" / "graph" / "vocabulary_nodes.json"
GRAMMAR_NODES_PATH = BASE_DIR / "ulga" / "graph" / "grammar_nodes.json"
SENTENCE_PATTERNS_PATH = BASE_DIR / "ulga" / "graph" / "sentence_patterns.json"
THEME_NODES_PATH = BASE_DIR / "ulga" / "graph" / "theme_nodes.json"
CHUNK_NODES_PATH = BASE_DIR / "ulga" / "graph" / "chunk_nodes.json"

RESOLUTION_OUT_PATH = BASE_DIR / "ulga" / "graph" / "dependency_readiness_resolution.json"
SUMMARY_OUT_PATH = BASE_DIR / "ulga" / "reports" / "dependency_readiness_resolution_summary.json"

SOURCE = "ULGA_S8Y_DEPENDENCY_READINESS_RESOLUTION"
GENERATED_AT = "2026-06-18T00:00:00Z"
VERSION = "1.0"
CEFR_ORDER = ["PreA1", "A1", "A1+", "A2", "A2+", "B1", "B1+", "B2", "B2+", "C1", "C2"]
CEFR_RANK = {level: index for index, level in enumerate(CEFR_ORDER)}
RESOLUTION_TYPES = {
    "explicit_requires_satisfied",
    "explicit_requires_level_blocked",
    "missing_required_ref",
    "no_requires_ready",
    "insufficient_evidence_unknown",
    "authority_reference_mismatch",
}


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


def build_node_index(*node_lists):
    index = {}
    for nodes in node_lists:
        if not isinstance(nodes, list):
            continue
        for node in nodes:
            if isinstance(node, dict) and node.get("id"):
                index[node["id"]] = node
    return index


def level_rank(level):
    return CEFR_RANK.get(level)


def level_ceiling_passed(opportunity_level, required_levels):
    opportunity_rank = level_rank(opportunity_level)
    if opportunity_rank is None:
        return False
    for required_level in required_levels:
        required_rank = level_rank(required_level)
        if required_rank is None or required_rank > opportunity_rank:
            return False
    return True


def max_required_level(required_levels):
    ranked_levels = [level for level in required_levels if level in CEFR_RANK]
    if not ranked_levels:
        return None
    return max(ranked_levels, key=lambda level: CEFR_RANK[level])


def reinforcement_positive_unknown_ids(reinforcement_payload):
    signals = reinforcement_payload.get("signals", []) if isinstance(reinforcement_payload, dict) else []
    return {
        signal.get("target_id")
        for signal in signals
        if isinstance(signal, dict)
        and isinstance(signal.get("signal_score"), (int, float))
        and signal["signal_score"] > 0
        and signal.get("ineligible_reason") == "dependency_unknown"
    }


def resolution_id_for(index):
    return f"DRR_{index:06d}"


def make_evidence(opportunity, required_refs, missing_required_refs, node_index):
    required_levels = [
        node_index[ref].get("cefr_level")
        for ref in required_refs
        if ref in node_index and node_index[ref].get("cefr_level")
    ]
    opportunity_level = opportunity.get("level")
    return {
        "has_explicit_requires": bool(required_refs),
        "requires_count": len(required_refs),
        "all_required_refs_exist": not missing_required_refs,
        "required_refs": required_refs,
        "missing_required_refs": missing_required_refs,
        "opportunity_level": opportunity_level,
        "max_required_level": max_required_level(required_levels),
        "level_ceiling_passed": level_ceiling_passed(opportunity_level, required_levels) if required_refs else True,
    }


def classify_resolution(evidence):
    if evidence["requires_count"] == 0:
        return "ready", "no_requires_ready", 0.8, []
    if not evidence["all_required_refs_exist"]:
        return "blocked", "missing_required_ref", 0.95, ["required refs missing from mounted node authority"]
    if evidence["level_ceiling_passed"] is True:
        return "ready", "explicit_requires_satisfied", 0.9, []
    return "blocked", "explicit_requires_level_blocked", 0.9, ["required level exceeds opportunity level ceiling"]


def build_resolution(index, opportunity, node_index):
    dependency = opportunity.get("dependency", {})
    required_refs = sorted(set(dependency.get("requires") or []))
    missing_required_refs = [ref for ref in required_refs if ref not in node_index]
    evidence = make_evidence(opportunity, required_refs, missing_required_refs, node_index)
    resolved_status, resolution_type, confidence, warnings = classify_resolution(evidence)
    return {
        "resolution_id": resolution_id_for(index),
        "opportunity_id": opportunity["opportunity_id"],
        "previous_dependency_status": "unknown",
        "resolved_dependency_status": resolved_status,
        "resolution_type": resolution_type,
        "evidence": evidence,
        "confidence": confidence,
        "planner_eligible_after_resolution": resolved_status == "ready",
        "warnings": warnings,
        "source": SOURCE,
    }


def build_summary(resolutions, unknown_input_count, positive_unknown_ids, missing_optional_inputs, warnings):
    resolved_status_counts = Counter(item["resolved_dependency_status"] for item in resolutions)
    resolution_type_distribution = Counter(item["resolution_type"] for item in resolutions)
    ready_ids = {
        item["opportunity_id"]
        for item in resolutions
        if item["resolved_dependency_status"] == "ready"
    }
    status = "PASS_WITH_WARNINGS" if warnings or missing_optional_inputs else "PASS"
    return {
        "status": status,
        "total_unknown_inputs": unknown_input_count,
        "resolved_ready_count": resolved_status_counts.get("ready", 0),
        "resolved_blocked_count": resolved_status_counts.get("blocked", 0),
        "still_unknown_count": resolved_status_counts.get("unknown", 0),
        "resolution_type_distribution": dict(sorted(resolution_type_distribution.items())),
        "reinforcement_positive_unknown_before": len(positive_unknown_ids),
        "reinforcement_positive_eligible_after": len(positive_unknown_ids & ready_ids),
        "missing_optional_inputs": missing_optional_inputs,
        "warnings": warnings,
    }


def build_dependency_readiness_resolution(
    output_path=RESOLUTION_OUT_PATH,
    summary_path=SUMMARY_OUT_PATH,
):
    warnings = []
    optional_inputs = [
        REINFORCEMENT_SIGNAL_PATH,
        DEPENDENCY_GRAPH_PATH,
        VOCABULARY_NODES_PATH,
        GRAMMAR_NODES_PATH,
        SENTENCE_PATTERNS_PATH,
        THEME_NODES_PATH,
        CHUNK_NODES_PATH,
    ]
    missing_optional_inputs = [relative_path(path) for path in optional_inputs if not path.exists()]

    opportunities = read_json(LEARNING_OPPORTUNITIES_PATH)
    reinforcement_payload = read_json_optional(REINFORCEMENT_SIGNAL_PATH, {})
    read_json_optional(DEPENDENCY_GRAPH_PATH, {})
    vocabulary_nodes = read_json_optional(VOCABULARY_NODES_PATH, [])
    grammar_nodes = read_json_optional(GRAMMAR_NODES_PATH, [])
    sentence_patterns = read_json_optional(SENTENCE_PATTERNS_PATH, [])
    theme_nodes = read_json_optional(THEME_NODES_PATH, [])
    chunk_nodes = read_json_optional(CHUNK_NODES_PATH, [])

    if not isinstance(opportunities, list):
        raise ValueError("learning_opportunities.json must contain a list")

    node_index = build_node_index(vocabulary_nodes, grammar_nodes, sentence_patterns, theme_nodes, chunk_nodes)
    unknown_opportunities = [
        opportunity
        for opportunity in opportunities
        if isinstance(opportunity, dict)
        and opportunity.get("opportunity_id")
        and opportunity.get("dependency", {}).get("status") == "unknown"
    ]
    unknown_opportunities.sort(key=lambda item: item["opportunity_id"])

    resolutions = [
        build_resolution(index, opportunity, node_index)
        for index, opportunity in enumerate(unknown_opportunities, start=1)
    ]
    positive_unknown_ids = reinforcement_positive_unknown_ids(reinforcement_payload)
    uncovered_positive = sorted(positive_unknown_ids - {item["opportunity_id"] for item in resolutions})
    if uncovered_positive:
        warnings.append(
            "positive dependency_unknown reinforcement signals without matching unknown opportunity: "
            + ", ".join(uncovered_positive)
        )

    payload = {
        "metadata": {
            "source": SOURCE,
            "version": VERSION,
            "generated_at": GENERATED_AT,
        },
        "resolutions": resolutions,
    }
    summary = build_summary(
        resolutions,
        len(unknown_opportunities),
        positive_unknown_ids,
        missing_optional_inputs,
        warnings,
    )
    write_json(output_path, payload)
    write_json(summary_path, summary)
    print(f"Dependency Readiness Resolution build: {summary['status']}")
    print(f"Unknown inputs: {summary['total_unknown_inputs']}")
    print(f"Resolved ready: {summary['resolved_ready_count']}")
    print(f"Resolved blocked: {summary['resolved_blocked_count']}")
    print(f"Warnings: {len(warnings)}")
    return summary


def main():
    try:
        build_dependency_readiness_resolution()
    except Exception as exc:
        print(f"Dependency Readiness Resolution build: FAIL - {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
