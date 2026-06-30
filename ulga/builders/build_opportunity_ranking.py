import json
import re
from collections import Counter, defaultdict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

LEARNING_OPPORTUNITIES_PATH = BASE_DIR / "ulga" / "graph" / "learning_opportunities.json"
THEME_SPIRAL_GRAPH_PATH = BASE_DIR / "ulga" / "graph" / "theme_spiral_graph.json"
THEME_NODES_PATH = BASE_DIR / "ulga" / "graph" / "theme_nodes.json"
VOCABULARY_NODES_PATH = BASE_DIR / "ulga" / "graph" / "vocabulary_nodes.json"

RANKED_OUT_PATH = BASE_DIR / "ulga" / "graph" / "ranked_learning_opportunities.json"
SUMMARY_OUT_PATH = BASE_DIR / "ulga" / "reports" / "opportunity_ranking_summary.json"

SOURCE = "ULGA_S10C_OPPORTUNITY_RANKING_AUTHORITY"
CONTRACT_VERSION = "ULGA-S10C"
RANKING_MODE = "static_offline"
WEIGHTS = {
    "dependency_score": 0.40,
    "frequency_score": 0.25,
    "theme_continuity_score": 0.20,
    "spiral_weight_score": 0.15,
}
DEPENDENCY_SCORE = {"ready": 1.0, "unknown": 0.5, "blocked": 0.0}
THEME_SOURCE_SCORE = {
    "pattern_theme_ref": 1.0,
    "pattern_slot_gate": 0.9,
    "theme_consensus": 0.85,
    "vocabulary_theme": 0.8,
    "chunk_theme_hint": 0.7,
    "general_fallback": 0.2,
}
CEFR_ORDER = ["A1", "A1_plus", "A2", "A2_plus", "B1", "B1_plus", "B2", "B2_plus", "C1", "C2"]
CEFR_RANK = {level: index for index, level in enumerate(CEFR_ORDER)}


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
    if value is None:
        return 0.5
    return round(max(0.0, min(1.0, float(value))), 6)


def normalize_theme_id(parent_theme):
    base = str(parent_theme or "").replace("(Bridge)", "").strip()
    base = re.sub(r"\s+", "_", base.lower())
    base = re.sub(r"[^a-z0-9_]+", "", base)
    return base


def build_vocabulary_index(vocabulary_nodes):
    return {
        node["id"]: node
        for node in vocabulary_nodes
        if isinstance(node, dict) and node.get("id")
    }


def build_theme_stage_lookup(theme_nodes):
    lookup = {}
    for node in theme_nodes or []:
        if not isinstance(node, dict):
            continue
        node_id = node.get("id")
        meta = node.get("metadata", {})
        parent_theme = meta.get("parent_theme")
        progression_stage = meta.get("progression_stage") or meta.get("level_scope") or node.get("cefr_level")
        if not node_id or not parent_theme or not progression_stage:
            continue
        lookup[node_id] = {
            "stage_id": f"theme:{normalize_theme_id(parent_theme)}:{progression_stage}",
            "theme_id": normalize_theme_id(parent_theme),
            "cefr_band": progression_stage,
        }
    return lookup


def build_spiral_index(theme_spiral_graph):
    score_by_stage = {}
    edge_count_by_stage = defaultdict(int)
    worst_gap_by_stage = defaultdict(int)

    stage_nodes = theme_spiral_graph.get("theme_stage_nodes", []) if isinstance(theme_spiral_graph, dict) else []
    for node in stage_nodes:
        if not isinstance(node, dict):
            continue
        stage_id = node.get("stage_id")
        if stage_id:
            score_by_stage[stage_id] = 0.6

    spiral_edges = theme_spiral_graph.get("spiral_edges", []) if isinstance(theme_spiral_graph, dict) else []
    for edge in spiral_edges:
        if not isinstance(edge, dict) or edge.get("review_status") != "accepted":
            continue
        stage_gap = 1
        for evidence in edge.get("evidence", []):
            if isinstance(evidence, dict) and isinstance(evidence.get("stage_gap"), int):
                stage_gap = evidence["stage_gap"]
                break
        for stage_id in [edge.get("source_stage_id"), edge.get("target_stage_id")]:
            if not stage_id:
                continue
            edge_count_by_stage[stage_id] += 1
            worst_gap_by_stage[stage_id] = max(worst_gap_by_stage[stage_id], stage_gap)
            if stage_gap <= 1:
                score_by_stage[stage_id] = max(score_by_stage.get(stage_id, 0.6), 1.0)
            else:
                score_by_stage[stage_id] = max(score_by_stage.get(stage_id, 0.6), 0.75)

    return score_by_stage, dict(edge_count_by_stage), dict(worst_gap_by_stage)


def dependency_score(opportunity):
    status = opportunity.get("dependency", {}).get("status")
    return DEPENDENCY_SCORE.get(status, 0.5)


def theme_continuity_score(opportunity):
    source = opportunity.get("theme_confidence", {}).get("source")
    return THEME_SOURCE_SCORE.get(source, 0.2)


def spiral_weight_score(opportunity, theme_stage_lookup, spiral_score_by_stage):
    theme_refs = opportunity.get("theme_refs", []) or []
    if theme_refs == ["General"]:
        return 0.2

    scores = []
    for theme_ref in theme_refs:
        stage = theme_stage_lookup.get(theme_ref)
        if not stage:
            continue
        scores.append(spiral_score_by_stage.get(stage["stage_id"], 0.6))
    if not scores:
        return 0.5
    return clamp(sum(scores) / len(scores))


def frequency_score(opportunity, vocabulary_index):
    scores = []
    for vocab_id in opportunity.get("focus_nodes", {}).get("vocabulary", []) or []:
        node = vocabulary_index.get(vocab_id)
        if not node:
            continue
        meta = node.get("metadata", {})
        raw_score = meta.get("frequency_score")
        if isinstance(raw_score, (int, float)):
            scores.append(clamp(raw_score / 100.0))
            continue
        rank = meta.get("frequency_rank")
        if isinstance(rank, int) and rank > 0:
            scores.append(clamp(1.0 - min(rank, 20000) / 20000.0))
    if not scores:
        return 0.5
    return clamp(sum(scores) / len(scores))


def pattern_utility_score(opportunity):
    raw = opportunity.get("ranking_features", {}).get("pattern_utility_score")
    if not isinstance(raw, (int, float)):
        return 0.5
    return clamp(raw / 3.0)


def score_breakdown_for(opportunity, vocabulary_index, theme_stage_lookup, spiral_score_by_stage):
    theme_score = theme_continuity_score(opportunity)
    return {
        "dependency_score": dependency_score(opportunity),
        "mastery_gap_score": 0.0,
        "reinforcement_score": 0.0,
        "theme_continuity_score": theme_score,
        "frequency_score": frequency_score(opportunity, vocabulary_index),
        "pattern_utility_score": pattern_utility_score(opportunity),
        "spiral_weight_score": spiral_weight_score(opportunity, theme_stage_lookup, spiral_score_by_stage),
    }


def candidate_score(breakdown):
    return round(sum(WEIGHTS[key] * breakdown[key] for key in WEIGHTS), 6)


def explanation_for(opportunity, breakdown, theme_stage_lookup, spiral_edge_count_by_stage, spiral_worst_gap_by_stage):
    explanation = []
    if opportunity.get("dependency", {}).get("status") == "ready":
        explanation.append("dependency_ready")
    elif opportunity.get("dependency", {}).get("status") == "blocked":
        explanation.append("dependency_blocked")
    else:
        explanation.append("dependency_unknown")

    if breakdown["theme_continuity_score"] >= 0.8:
        explanation.append("theme_specific")
    elif breakdown["theme_continuity_score"] <= 0.2:
        explanation.append("theme_general_fallback")

    if breakdown["frequency_score"] >= 0.7:
        explanation.append("high_frequency")
    elif breakdown["frequency_score"] <= 0.35:
        explanation.append("low_frequency")

    theme_refs = opportunity.get("theme_refs", []) or []
    stage_ids = [
        theme_stage_lookup[theme_ref]["stage_id"]
        for theme_ref in theme_refs
        if theme_ref in theme_stage_lookup
    ]
    if any(spiral_edge_count_by_stage.get(stage_id, 0) > 0 for stage_id in stage_ids):
        explanation.append("spiral_supported")
    if any(spiral_worst_gap_by_stage.get(stage_id, 0) > 1 for stage_id in stage_ids):
        explanation.append("spiral_stage_gap_capped")

    if breakdown["pattern_utility_score"] >= 0.7:
        explanation.append("pattern_utility_high")
    explanation.append("static_offline_ranked")
    return explanation


def bucket_score(score):
    if score >= 0.8:
        return "0.80-1.00"
    if score >= 0.6:
        return "0.60-0.79"
    if score >= 0.4:
        return "0.40-0.59"
    if score >= 0.2:
        return "0.20-0.39"
    return "0.00-0.19"


def build_summary(ranked, opportunity_by_id, warnings):
    top_10 = ranked[:10]
    top_10_levels = Counter(opportunity_by_id[item["opportunity_id"]].get("level") for item in top_10)
    top_10_themes = Counter(
        theme
        for item in top_10
        for theme in opportunity_by_id[item["opportunity_id"]].get("theme_refs", [])
    )
    score_distribution = Counter(bucket_score(item["candidate_score"]) for item in ranked)
    dependency_distribution = Counter(
        opportunity_by_id[item["opportunity_id"]].get("dependency", {}).get("status", "unknown")
        for item in ranked
    )
    theme_source_distribution = Counter(
        opportunity_by_id[item["opportunity_id"]].get("theme_confidence", {}).get("source", "unknown")
        for item in ranked
    )
    return {
        "status": "PASS_WITH_WARNINGS" if warnings else "PASS",
        "contract_version": CONTRACT_VERSION,
        "source": SOURCE,
        "ranking_mode": RANKING_MODE,
        "adaptive_inputs_used": [],
        "total_ranked": len(ranked),
        "top_10_levels": dict(sorted(top_10_levels.items())),
        "top_10_themes": dict(sorted(top_10_themes.items())),
        "score_distribution": dict(sorted(score_distribution.items())),
        "dependency_distribution": dict(sorted(dependency_distribution.items())),
        "theme_source_distribution": dict(sorted(theme_source_distribution.items())),
        "warnings": warnings,
    }


def build_opportunity_ranking():
    warnings = []
    opportunities = read_json_optional(LEARNING_OPPORTUNITIES_PATH, [])
    vocabulary_nodes = read_json_optional(VOCABULARY_NODES_PATH, [])
    theme_nodes = read_json_optional(THEME_NODES_PATH, [])
    theme_spiral_graph = read_json_optional(THEME_SPIRAL_GRAPH_PATH, {})

    if not isinstance(opportunities, list):
        warnings.append("learning_opportunities.json was not a list; emitted zero rankings")
        opportunities = []
    if not isinstance(vocabulary_nodes, list):
        warnings.append("vocabulary_nodes.json was not a list; frequency_score uses defaults")
        vocabulary_nodes = []
    if not isinstance(theme_nodes, list):
        warnings.append("theme_nodes.json was not a list; spiral weight uses defaults")
        theme_nodes = []
    if not isinstance(theme_spiral_graph, dict):
        warnings.append("theme_spiral_graph.json was not an object; spiral weight uses defaults")
        theme_spiral_graph = {}

    vocabulary_index = build_vocabulary_index(vocabulary_nodes)
    theme_stage_lookup = build_theme_stage_lookup(theme_nodes)
    spiral_score_by_stage, spiral_edge_count_by_stage, spiral_worst_gap_by_stage = build_spiral_index(
        theme_spiral_graph
    )

    ranked = []
    for opportunity in opportunities:
        opportunity_id = opportunity.get("opportunity_id")
        if not opportunity_id:
            warnings.append("skipped opportunity without opportunity_id")
            continue
        breakdown = score_breakdown_for(
            opportunity,
            vocabulary_index,
            theme_stage_lookup,
            spiral_score_by_stage,
        )
        ranked.append(
            {
                "rank": 0,
                "opportunity_id": opportunity_id,
                "candidate_score": candidate_score(breakdown),
                "score_breakdown": breakdown,
                "explanation": explanation_for(
                    opportunity,
                    breakdown,
                    theme_stage_lookup,
                    spiral_edge_count_by_stage,
                    spiral_worst_gap_by_stage,
                ),
                "ranking_mode": RANKING_MODE,
                "source": SOURCE,
            }
        )

    ranked.sort(key=lambda item: (-item["candidate_score"], item["opportunity_id"]))
    for index, item in enumerate(ranked, start=1):
        item["rank"] = index

    opportunity_by_id = {item["opportunity_id"]: item for item in opportunities if item.get("opportunity_id")}
    summary = build_summary(ranked, opportunity_by_id, warnings)
    write_json(RANKED_OUT_PATH, ranked)
    write_json(SUMMARY_OUT_PATH, summary)
    print(f"Opportunity Ranking build: {summary['status']}")
    print(f"Ranked opportunities: {len(ranked)}")
    print(f"Warnings: {len(warnings)}")
    return summary


if __name__ == "__main__":
    build_opportunity_ranking()
