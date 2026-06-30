import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

LEARNER_STATE_PATH = BASE_DIR / "ulga" / "learner_state" / "learner_state.json"
LEARNING_OPPORTUNITIES_PATH = BASE_DIR / "ulga" / "graph" / "learning_opportunities.json"
DEPENDENCY_READINESS_RESOLUTION_PATH = BASE_DIR / "ulga" / "graph" / "dependency_readiness_resolution.json"
REINFORCEMENT_CANDIDATE_EXPANSION_PATH = BASE_DIR / "ulga" / "graph" / "reinforcement_candidate_expansion.json"
REINFORCEMENT_CANDIDATE_EXPANSION_SUMMARY_PATH = (
    BASE_DIR / "ulga" / "reports" / "reinforcement_candidate_expansion_summary.json"
)
EXPOSURE_MAPPING_BRIDGE_PATH = BASE_DIR / "ulga" / "graph" / "exposure_mapping_bridge.json"

EVIDENCE_OUT_PATH = BASE_DIR / "ulga" / "graph" / "learner_exposure_evidence.json"
SUMMARY_OUT_PATH = BASE_DIR / "ulga" / "reports" / "learner_exposure_evidence_summary.json"

SOURCE = "ULGA_S9Y_LEARNER_EXPOSURE_EVIDENCE"
CONTRACT_VERSION = "ULGA-S9Z1"
GENERATED_AT = "2026-06-18T00:00:00Z"

VALID_NODE_TYPES = {"vocabulary", "grammar", "theme"}
MAPPING_WEIGHTS = {
    "vocabulary": 1.0,
    "grammar": 1.0,
    "theme": 0.67,
}
BRIDGE_SOURCE_BY_TYPE = {
    "direct_focus_node_bridge": "direct_focus_node",
    "grammar_bridge": "grammar",
    "vocabulary_bridge": "vocabulary",
    "theme_bridge": "theme",
    "dependency_parent_bridge": "dependency_parent",
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


def clamp(value):
    return round(max(0.0, min(1.0, float(value))), 6)


def evidence_id_for(index):
    return f"LEE_{index:06d}"


def confidence_band(record):
    attempt_count = record.get("attempt_count", record.get("exposure_count", 0))
    if not isinstance(attempt_count, (int, float)):
        attempt_count = 0
    if attempt_count >= 3 and record.get("mastery_band") != "seen":
        return "strong"
    if attempt_count >= 2:
        return "medium"
    return "weak"


def base_exposure_score(record):
    if not record.get("last_seen_at"):
        return 0.0
    band = confidence_band(record)
    return {
        "weak": 0.5,
        "medium": 0.75,
        "strong": 1.0,
    }[band]


def opportunity_indexes(opportunities):
    by_focus = defaultdict(list)
    by_theme = defaultdict(list)
    opportunity_ids = set()
    for opportunity in opportunities if isinstance(opportunities, list) else []:
        if not isinstance(opportunity, dict) or not opportunity.get("opportunity_id"):
            continue
        opportunity_ids.add(opportunity["opportunity_id"])
        for refs in (opportunity.get("focus_nodes") or {}).values():
            for ref in refs or []:
                by_focus[ref].append(opportunity)
        for theme_id in opportunity.get("theme_refs") or []:
            by_theme[theme_id].append(opportunity)
    for values in by_focus.values():
        values.sort(key=lambda item: item["opportunity_id"])
    for values in by_theme.values():
        values.sort(key=lambda item: item["opportunity_id"])
    return by_focus, by_theme, opportunity_ids


def dependency_overlay(resolution_payload):
    index = {}
    for resolution in resolution_payload.get("resolutions", []) if isinstance(resolution_payload, dict) else []:
        if not isinstance(resolution, dict):
            continue
        opportunity_id = resolution.get("opportunity_id")
        status = resolution.get("resolved_dependency_status")
        if opportunity_id and status:
            index[opportunity_id] = status
    return index


def mapping_type_for(node_type):
    if node_type == "theme":
        return "theme_overlap"
    return "focus_node_overlap"


def opportunities_for_record(record, by_focus, by_theme):
    node_id = record.get("node_id")
    node_type = record.get("node_type")
    if not node_id or node_type not in VALID_NODE_TYPES:
        return []
    if node_type == "theme":
        return by_theme.get(node_id, [])
    return by_focus.get(node_id, [])


def make_evidence(record, opportunity, dependency_status_by_opportunity, index):
    node_type = record["node_type"]
    score = clamp(base_exposure_score(record) * MAPPING_WEIGHTS[node_type])
    source_name = "theme" if node_type == "theme" else node_type
    warnings = []
    if score == 0:
        warnings.append("missing_last_seen_at")
    dependency_status = dependency_status_by_opportunity.get(
        opportunity["opportunity_id"],
        opportunity.get("dependency", {}).get("status", "unknown"),
    )
    return {
        "evidence_id": evidence_id_for(index),
        "learner_id": record.get("learner_id"),
        "target_type": "opportunity",
        "target_id": opportunity["opportunity_id"],
        "opportunity_exposure_score": score,
        "confidence_band": confidence_band(record),
        "prior_exposure": score > 0,
        "evidence_sources": [source_name],
        "source_node_id": record.get("node_id"),
        "source_node_type": node_type,
        "mapping_type": mapping_type_for(node_type),
        "bridge_refs": [],
        "dependency_status": dependency_status,
        "warnings": warnings,
        "source": SOURCE,
    }


def confidence_band_from_score(score):
    if score >= 0.7:
        return "strong"
    if score >= 0.5:
        return "medium"
    return "weak"


def make_bridge_evidence(bridge, index):
    confidence = bridge.get("confidence", 0.0)
    if not isinstance(confidence, (int, float)):
        confidence = 0.0
    score = clamp(confidence)
    source_name = BRIDGE_SOURCE_BY_TYPE.get(bridge.get("bridge_type"), "direct_focus_node")
    return {
        "evidence_id": evidence_id_for(index),
        "learner_id": bridge.get("learner_id"),
        "target_type": "opportunity",
        "target_id": bridge.get("opportunity_id"),
        "opportunity_exposure_score": score,
        "confidence_band": confidence_band_from_score(score),
        "prior_exposure": bridge.get("prior_exposure") is True and score > 0,
        "evidence_sources": [source_name],
        "source_node_id": bridge.get("source_ref"),
        "source_node_type": bridge.get("source_node_type"),
        "mapping_type": bridge.get("bridge_type"),
        "bridge_refs": [bridge.get("bridge_id")],
        "dependency_status": bridge.get("dependency_status", "unknown"),
        "reading_ready": bridge.get("reading_ready"),
        "planner_safe": bridge.get("planner_safe"),
        "warnings": list(bridge.get("warnings") or []),
        "source": SOURCE,
    }


def dedupe_evidence(evidence):
    best_by_key = {}
    for item in evidence:
        key = (item["learner_id"], item["target_id"], item["source_node_id"], item["mapping_type"])
        previous = best_by_key.get(key)
        if previous is None or item["opportunity_exposure_score"] > previous["opportunity_exposure_score"]:
            best_by_key[key] = item
    output = sorted(
        best_by_key.values(),
        key=lambda item: (
            item["learner_id"] or "",
            item["target_id"],
            item["source_node_id"] or "",
            item["mapping_type"],
        ),
    )
    for index, item in enumerate(output, start=1):
        item["evidence_id"] = evidence_id_for(index)
    return output


def build_summary(evidence, opportunities, warnings):
    band_counts = Counter(item["confidence_band"] for item in evidence)
    source_counts = Counter(
        source
        for item in evidence
        for source in item.get("evidence_sources", [])
    )
    mapped_opportunity_ids = {item["target_id"] for item in evidence}
    opportunity_count = len(
        [item for item in opportunities if isinstance(item, dict) and item.get("opportunity_id")]
    )
    coverage_rate = round(len(mapped_opportunity_ids) / opportunity_count, 6) if opportunity_count else 0.0
    status = "PASS_WITH_WARNINGS" if warnings else "PASS"
    if not evidence:
        status = "PASS_WITH_WARNINGS"
        if "no exposure evidence generated" not in warnings:
            warnings.append("no exposure evidence generated")
    return {
        "status": status,
        "evidence_count": len(evidence),
        "opportunity_mapping_count": len(mapped_opportunity_ids),
        "weak_count": band_counts.get("weak", 0),
        "medium_count": band_counts.get("medium", 0),
        "strong_count": band_counts.get("strong", 0),
        "coverage_rate": coverage_rate,
        "evidence_source_distribution": dict(sorted(source_counts.items())),
        "bridge_ref_count": sum(len(item.get("bridge_refs", [])) for item in evidence),
        "warnings": warnings,
    }


def build_learner_exposure_evidence(output_path=EVIDENCE_OUT_PATH, summary_path=SUMMARY_OUT_PATH):
    warnings = []
    learner_state = read_json_optional(LEARNER_STATE_PATH, {})
    opportunities = read_json_optional(LEARNING_OPPORTUNITIES_PATH, [])
    resolution_payload = read_json_optional(DEPENDENCY_READINESS_RESOLUTION_PATH, {})
    read_json_optional(REINFORCEMENT_CANDIDATE_EXPANSION_PATH, {})
    read_json_optional(REINFORCEMENT_CANDIDATE_EXPANSION_SUMMARY_PATH, {})
    bridge_payload = read_json_optional(EXPOSURE_MAPPING_BRIDGE_PATH, {})

    if not isinstance(opportunities, list):
        warnings.append("learning_opportunities.json was not a list; emitted zero evidence")
        opportunities = []

    records = learner_state.get("learner_state_records", []) if isinstance(learner_state, dict) else []
    if not records:
        warnings.append("learner_state has no records; emitted zero evidence")

    by_focus, by_theme, _ = opportunity_indexes(opportunities)
    dependency_status_by_opportunity = dependency_overlay(resolution_payload)

    evidence = []
    bridges = bridge_payload.get("bridges", []) if isinstance(bridge_payload, dict) else []
    if bridges:
        for bridge in bridges:
            if not isinstance(bridge, dict) or bridge.get("prior_exposure") is not True:
                continue
            evidence.append(make_bridge_evidence(bridge, len(evidence) + 1))
    else:
        for record in records:
            if not isinstance(record, dict) or record.get("node_type") not in VALID_NODE_TYPES:
                continue
            if not record.get("last_seen_at") and not record.get("exposure_count") and not record.get("attempt_count"):
                continue
            for opportunity in opportunities_for_record(record, by_focus, by_theme):
                evidence.append(
                    make_evidence(
                        record,
                        opportunity,
                        dependency_status_by_opportunity,
                        len(evidence) + 1,
                    )
                )

    evidence = dedupe_evidence(evidence)
    payload = {
        "metadata": {
            "source": SOURCE,
            "contract_version": CONTRACT_VERSION,
            "version": "1.0",
            "generated_at": GENERATED_AT,
        },
        "evidence": evidence,
    }
    summary = build_summary(evidence, opportunities, warnings)
    write_json(output_path, payload)
    write_json(summary_path, summary)
    print(f"Learner Exposure Evidence build: {summary['status']}")
    print(f"Evidence: {summary['evidence_count']}")
    print(f"Opportunity mappings: {summary['opportunity_mapping_count']}")
    print(f"Coverage rate: {summary['coverage_rate']}")
    print(f"Warnings: {len(summary['warnings'])}")
    return summary


def main():
    try:
        build_learner_exposure_evidence()
    except Exception as exc:
        print(f"Learner Exposure Evidence build: FAIL - {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
