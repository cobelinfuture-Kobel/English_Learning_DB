import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

LEARNER_STATE_PATH = BASE_DIR / "ulga" / "learner_state" / "learner_state.json"
LEARNING_OPPORTUNITIES_PATH = BASE_DIR / "ulga" / "graph" / "learning_opportunities.json"
DEPENDENCY_READINESS_RESOLUTION_PATH = BASE_DIR / "ulga" / "graph" / "dependency_readiness_resolution.json"
READING_STUBS_PATH = BASE_DIR / "ulga" / "graph" / "reading_stub_authority.json"
VOCABULARY_NODES_PATH = BASE_DIR / "ulga" / "graph" / "vocabulary_nodes.json"
SENTENCE_PATTERNS_PATH = BASE_DIR / "ulga" / "graph" / "sentence_patterns.json"
THEME_NODES_PATH = BASE_DIR / "ulga" / "graph" / "theme_nodes.json"
DEPENDENCY_GRAPH_PATH = BASE_DIR / "ulga" / "graph" / "dependency_graph.json"

BRIDGE_OUT_PATH = BASE_DIR / "ulga" / "graph" / "exposure_mapping_bridge.json"
SUMMARY_OUT_PATH = BASE_DIR / "ulga" / "reports" / "exposure_mapping_bridge_summary.json"

SOURCE = "ULGA_S9Z1_EXPOSURE_MAPPING_BRIDGE"
CONTRACT_VERSION = "ULGA-S9Z1"
GENERATED_AT = "2026-06-18T00:00:00Z"

VALID_BRIDGE_TYPES = {
    "direct_focus_node_bridge",
    "grammar_bridge",
    "vocabulary_bridge",
    "theme_bridge",
    "dependency_parent_bridge",
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


def bridge_id_for(index):
    return f"EMB_{index:06d}"


def opportunity_indexes(opportunities):
    by_id = {}
    by_focus = defaultdict(list)
    by_theme = defaultdict(list)
    by_requires = defaultdict(list)
    for opportunity in opportunities if isinstance(opportunities, list) else []:
        if not isinstance(opportunity, dict) or not opportunity.get("opportunity_id"):
            continue
        by_id[opportunity["opportunity_id"]] = opportunity
        for refs in (opportunity.get("focus_nodes") or {}).values():
            for ref in refs or []:
                by_focus[ref].append(opportunity)
        for theme_id in opportunity.get("theme_refs") or []:
            by_theme[theme_id].append(opportunity)
        for required_ref in (opportunity.get("dependency") or {}).get("requires") or []:
            by_requires[required_ref].append(opportunity)
    for index in [by_focus, by_theme, by_requires]:
        for values in index.values():
            values.sort(key=lambda item: item["opportunity_id"])
    return by_id, by_focus, by_theme, by_requires


def dependency_overlay(resolution_payload):
    index = {}
    level_safe = {}
    for resolution in resolution_payload.get("resolutions", []) if isinstance(resolution_payload, dict) else []:
        if not isinstance(resolution, dict):
            continue
        opportunity_id = resolution.get("opportunity_id")
        if not opportunity_id:
            continue
        status = resolution.get("resolved_dependency_status")
        if status:
            index[opportunity_id] = status
        level_safe[opportunity_id] = resolution.get("evidence", {}).get("level_ceiling_passed") is not False
    return index, level_safe


def reading_ready_index(readings):
    ready = set()
    for reading in readings if isinstance(readings, list) else []:
        if not isinstance(reading, dict) or reading.get("delivery_ready") is not True:
            continue
        ready.update(reading.get("linked_opportunities") or [])
    return ready


def normalized_focus_refs(record):
    node_id = record.get("node_id")
    node_type = record.get("node_type")
    if not node_id:
        return []
    refs = [node_id]
    if node_type == "sentence_pattern" and node_id.startswith("sentence_pattern:"):
        refs.append("pattern:" + node_id.split(":", 1)[1])
    return refs


def confidence_for_bridge(bridge_type):
    return {
        "direct_focus_node_bridge": 1.0,
        "grammar_bridge": 0.9,
        "vocabulary_bridge": 0.8,
        "theme_bridge": 0.4,
        "dependency_parent_bridge": 0.85,
    }[bridge_type]


def dependency_status_for(opportunity, dependency_status_by_opportunity):
    return dependency_status_by_opportunity.get(
        opportunity["opportunity_id"],
        (opportunity.get("dependency") or {}).get("status", "unknown"),
    )


def planner_safe_for(bridge_type, opportunity, dependency_status_by_opportunity, level_safe_by_opportunity, reading_ready):
    if bridge_type == "theme_bridge":
        return False
    if dependency_status_for(opportunity, dependency_status_by_opportunity) != "ready":
        return False
    if level_safe_by_opportunity.get(opportunity["opportunity_id"], True) is not True:
        return False
    return opportunity["opportunity_id"] in reading_ready


def make_bridge(record, opportunity, bridge_type, matched_ref, dependency_status_by_opportunity, level_safe_by_opportunity, reading_ready):
    warnings = []
    dependency_status = dependency_status_for(opportunity, dependency_status_by_opportunity)
    level_safe = level_safe_by_opportunity.get(opportunity["opportunity_id"], True)
    reading_ready_flag = opportunity["opportunity_id"] in reading_ready
    planner_safe = planner_safe_for(
        bridge_type,
        opportunity,
        dependency_status_by_opportunity,
        level_safe_by_opportunity,
        reading_ready,
    )
    if bridge_type == "theme_bridge":
        warnings.append("theme_bridge_diagnostic_only")
    if dependency_status != "ready":
        warnings.append(f"dependency_status_{dependency_status}")
    if not level_safe:
        warnings.append("level_blocked")
    if not reading_ready_flag:
        warnings.append("reading_missing")
    return {
        "bridge_id": "",
        "learner_id": record.get("learner_id"),
        "source_ref": record.get("node_id"),
        "source_node_type": record.get("node_type"),
        "matched_ref": matched_ref,
        "opportunity_id": opportunity["opportunity_id"],
        "bridge_type": bridge_type,
        "confidence": confidence_for_bridge(bridge_type),
        "prior_exposure": True,
        "planner_safe": planner_safe,
        "dependency_status": dependency_status,
        "reading_ready": reading_ready_flag,
        "warnings": sorted(set(warnings)),
        "source": SOURCE,
    }


def build_bridges(records, opportunities, resolution_payload, readings):
    _, by_focus, by_theme, by_requires = opportunity_indexes(opportunities)
    dependency_status_by_opportunity, level_safe_by_opportunity = dependency_overlay(resolution_payload)
    reading_ready = reading_ready_index(readings)
    bridges = []
    seen = set()
    for record in records:
        if not isinstance(record, dict) or not record.get("node_id"):
            continue
        if not (record.get("last_seen_at") or record.get("exposure_count") or record.get("attempt_count")):
            continue
        node_type = record.get("node_type")
        bridge_sources = []
        if node_type == "theme":
            for opportunity in by_theme.get(record["node_id"], []):
                bridge_sources.append(("theme_bridge", record["node_id"], opportunity))
        else:
            for ref in normalized_focus_refs(record):
                for opportunity in by_focus.get(ref, []):
                    bridge_type = "direct_focus_node_bridge"
                    if node_type == "grammar":
                        bridge_type = "grammar_bridge"
                    elif node_type == "vocabulary":
                        bridge_type = "vocabulary_bridge"
                    bridge_sources.append((bridge_type, ref, opportunity))
            if node_type == "grammar":
                for opportunity in by_requires.get(record["node_id"], []):
                    bridge_sources.append(("dependency_parent_bridge", record["node_id"], opportunity))
        for bridge_type, matched_ref, opportunity in bridge_sources:
            key = (record.get("learner_id"), record.get("node_id"), opportunity["opportunity_id"], bridge_type)
            if key in seen:
                continue
            seen.add(key)
            bridges.append(
                make_bridge(
                    record,
                    opportunity,
                    bridge_type,
                    matched_ref,
                    dependency_status_by_opportunity,
                    level_safe_by_opportunity,
                    reading_ready,
                )
            )
    bridges.sort(
        key=lambda item: (
            item["learner_id"] or "",
            item["opportunity_id"],
            item["bridge_type"],
            item["source_ref"] or "",
        )
    )
    for index, bridge in enumerate(bridges, start=1):
        bridge["bridge_id"] = bridge_id_for(index)
    return bridges


def build_summary(bridges, warnings):
    bridge_distribution = Counter(bridge["bridge_type"] for bridge in bridges)
    status = "PASS_WITH_WARNINGS" if warnings or not bridges else "PASS"
    if not bridges and "no exposure mapping bridges generated" not in warnings:
        warnings.append("no exposure mapping bridges generated")
        status = "PASS_WITH_WARNINGS"
    return {
        "status": status,
        "bridge_count": len(bridges),
        "bridge_distribution": dict(sorted(bridge_distribution.items())),
        "planner_safe_count": sum(1 for bridge in bridges if bridge["planner_safe"]),
        "warnings": warnings,
    }


def build_exposure_mapping_bridge(output_path=BRIDGE_OUT_PATH, summary_path=SUMMARY_OUT_PATH):
    warnings = []
    learner_state = read_json_optional(LEARNER_STATE_PATH, {})
    opportunities = read_json_optional(LEARNING_OPPORTUNITIES_PATH, [])
    resolution_payload = read_json_optional(DEPENDENCY_READINESS_RESOLUTION_PATH, {})
    readings = read_json_optional(READING_STUBS_PATH, [])
    read_json_optional(VOCABULARY_NODES_PATH, [])
    read_json_optional(SENTENCE_PATTERNS_PATH, [])
    read_json_optional(THEME_NODES_PATH, [])
    read_json_optional(DEPENDENCY_GRAPH_PATH, {})

    if not isinstance(opportunities, list):
        warnings.append("learning_opportunities.json was not a list; emitted zero bridges")
        opportunities = []
    records = learner_state.get("learner_state_records", []) if isinstance(learner_state, dict) else []
    if not records:
        warnings.append("learner_state has no records; emitted zero bridges")

    bridges = build_bridges(records, opportunities, resolution_payload, readings)
    payload = {
        "metadata": {
            "source": SOURCE,
            "contract_version": CONTRACT_VERSION,
            "version": "1.0",
            "generated_at": GENERATED_AT,
        },
        "bridges": bridges,
    }
    summary = build_summary(bridges, warnings)
    write_json(output_path, payload)
    write_json(summary_path, summary)
    print(f"Exposure Mapping Bridge build: {summary['status']}")
    print(f"Bridges: {summary['bridge_count']}")
    print(f"Planner safe: {summary['planner_safe_count']}")
    print(f"Warnings: {len(summary['warnings'])}")
    return summary


def main():
    try:
        build_exposure_mapping_bridge()
    except Exception as exc:
        print(f"Exposure Mapping Bridge build: FAIL - {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
