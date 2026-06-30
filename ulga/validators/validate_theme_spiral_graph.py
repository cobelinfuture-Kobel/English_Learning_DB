import json
import sys
from collections import defaultdict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

THEME_SPIRAL_GRAPH_PATH = BASE_DIR / "ulga" / "graph" / "theme_spiral_graph.json"
STAGE_GAP_REVIEW_QUEUE_PATH = BASE_DIR / "ulga" / "reports" / "theme_spiral_stage_gap_review_queue.json"
THEME_CATALOG_PATH = BASE_DIR / "themes" / "theme_catalog.json"
THEME_VOCAB_MAPPING_PATH = BASE_DIR / "themes" / "theme_vocab_mapping.json"
LEARNING_SIGNAL_POLICY_PATH = BASE_DIR / "ulga" / "schema" / "learning_signal_policy.json"

RELATION = "SPIRAL_TO"
CEFR_ORDER = ["A1", "A1_plus", "A2", "A2_plus", "B1", "B1_plus", "B2", "B2_plus", "C1"]
CEFR_RANK = {level: index for index, level in enumerate(CEFR_ORDER)}
ALLOWED_CONFIDENCE_METHODS = {
    "authoritative",
    "derived",
    "heuristic",
    "manual_review_required",
}
ALLOWED_REVIEW_STATUS = {"accepted", "needs_review", "blocked", "deprecated"}
REQUIRED_THEME_SOURCE_FILES = {
    "themes/theme_catalog.json",
    "themes/theme_vocab_mapping.json",
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


def has_cycle(edges):
    graph = defaultdict(list)
    for edge in edges:
        graph[edge["source_stage_id"]].append(edge["target_stage_id"])

    visiting = set()
    visited = set()

    def visit(node):
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for nxt in graph.get(node, []):
            if visit(nxt):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in list(graph))


def validate_stage_node(node, index):
    required = {
        "stage_id",
        "node_type",
        "theme_id",
        "theme_label",
        "cefr_band",
        "source_theme_ids",
        "source_parent_themes",
        "source_files",
        "source_authority",
        "confidence",
        "review_status",
        "notes",
    }
    missing = required - set(node)
    if missing:
        return fail(f"theme_stage_nodes[{index}] missing required fields: {sorted(missing)}")
    if node["node_type"] != "ThemeStageNode":
        return fail(f"theme_stage_nodes[{index}] has invalid node_type.")
    if node["cefr_band"] not in CEFR_RANK:
        return fail(f"theme_stage_nodes[{index}] has invalid cefr_band: {node['cefr_band']}")
    expected_stage_id = f"theme:{node['theme_id']}:{node['cefr_band']}"
    if node["stage_id"] != expected_stage_id:
        return fail(f"theme_stage_nodes[{index}] stage_id must be {expected_stage_id}.")
    if not isinstance(node["source_theme_ids"], list) or not node["source_theme_ids"]:
        return fail(f"theme_stage_nodes[{index}] source_theme_ids must be non-empty.")
    source_authority = node["source_authority"]
    if not isinstance(source_authority, dict):
        return fail(f"theme_stage_nodes[{index}] source_authority must be an object.")
    required_authority = {
        "authority_name",
        "source_files",
        "source_theme_ids",
        "derivation",
        "normalization_policy",
        "confidence_basis",
    }
    missing_authority = required_authority - set(source_authority)
    if missing_authority:
        return fail(
            f"theme_stage_nodes[{index}] source_authority missing fields: {sorted(missing_authority)}"
        )
    if source_authority["authority_name"] != "ThemeAuthority":
        return fail(f"theme_stage_nodes[{index}] source_authority.authority_name must be ThemeAuthority.")
    if source_authority["source_theme_ids"] != node["source_theme_ids"]:
        return fail(
            f"theme_stage_nodes[{index}] source_authority.source_theme_ids must match node.source_theme_ids."
        )
    if not REQUIRED_THEME_SOURCE_FILES.issubset(set(source_authority.get("source_files", []))):
        return fail(
            f"theme_stage_nodes[{index}] source_authority.source_files must include required theme source files."
        )
    if not str(source_authority.get("derivation", "")).strip():
        return fail(f"theme_stage_nodes[{index}] source_authority.derivation must be non-empty.")
    if not str(source_authority.get("normalization_policy", "")).strip():
        return fail(f"theme_stage_nodes[{index}] source_authority.normalization_policy must be non-empty.")
    if not str(source_authority.get("confidence_basis", "")).strip():
        return fail(f"theme_stage_nodes[{index}] source_authority.confidence_basis must be non-empty.")
    if not isinstance(node["notes"], list):
        return fail(f"theme_stage_nodes[{index}] notes must be a list.")
    confidence = node["confidence"]
    if not isinstance(confidence, dict):
        return fail(f"theme_stage_nodes[{index}] confidence must be an object.")
    if confidence.get("method") not in ALLOWED_CONFIDENCE_METHODS:
        return fail(f"theme_stage_nodes[{index}] confidence.method is invalid.")
    value = confidence.get("value")
    if not isinstance(value, (int, float)) or value < 0 or value > 1:
        return fail(f"theme_stage_nodes[{index}] confidence.value must be between 0 and 1.")
    if node["review_status"] not in ALLOWED_REVIEW_STATUS:
        return fail(f"theme_stage_nodes[{index}] review_status is invalid.")
    return True


def validate_edge_shape(edge, index):
    required = {
        "edge_id",
        "source_stage_id",
        "target_stage_id",
        "relation",
        "theme_id",
        "source_cefr",
        "target_cefr",
        "confidence",
        "review_status",
        "gate_eligible",
        "evidence",
        "notes",
    }
    missing = required - set(edge)
    if missing:
        return fail(f"spiral_edges[{index}] missing required fields: {sorted(missing)}")
    if not str(edge["edge_id"]).startswith("theme_spiral_edge:"):
        return fail(f"spiral_edges[{index}] has invalid edge_id prefix.")
    if edge["source_stage_id"] == edge["target_stage_id"]:
        return fail(f"spiral_edges[{index}] is a self edge.")
    if edge["relation"] != RELATION:
        return fail(f"spiral_edges[{index}] invalid relation: {edge['relation']}")
    if edge["source_cefr"] not in CEFR_RANK or edge["target_cefr"] not in CEFR_RANK:
        return fail(f"spiral_edges[{index}] has invalid CEFR field.")
    if CEFR_RANK[edge["target_cefr"]] <= CEFR_RANK[edge["source_cefr"]]:
        return fail(f"spiral_edges[{index}] is backward or non-progressing.")
    if edge["gate_eligible"] is not False:
        return fail(f"spiral_edges[{index}] gate_eligible must be false.")
    if edge["review_status"] not in ALLOWED_REVIEW_STATUS:
        return fail(f"spiral_edges[{index}] review_status is invalid.")
    if not isinstance(edge["evidence"], list) or not edge["evidence"]:
        return fail(f"spiral_edges[{index}] evidence must be a non-empty list.")
    if not isinstance(edge["notes"], list):
        return fail(f"spiral_edges[{index}] notes must be a list.")
    confidence = edge["confidence"]
    if not isinstance(confidence, dict):
        return fail(f"spiral_edges[{index}] confidence must be an object.")
    value = confidence.get("value")
    if not isinstance(value, (int, float)) or value < 0 or value > 1:
        return fail(f"spiral_edges[{index}] confidence.value must be between 0 and 1.")
    if confidence.get("method") not in ALLOWED_CONFIDENCE_METHODS:
        return fail(f"spiral_edges[{index}] confidence.method is invalid.")
    return True


def validate():
    print("Validating ULGA Theme Spiral Graph...")
    if not THEME_SPIRAL_GRAPH_PATH.exists():
        return fail(f"required file does not exist: {THEME_SPIRAL_GRAPH_PATH}")

    graph = read_json(THEME_SPIRAL_GRAPH_PATH)
    theme_catalog = read_json(THEME_CATALOG_PATH)
    theme_mapping = read_json(THEME_VOCAB_MAPPING_PATH)
    policy = read_json(LEARNING_SIGNAL_POLICY_PATH)
    if graph is None or theme_catalog is None or theme_mapping is None or policy is None:
        return False

    if not isinstance(graph, dict):
        return fail("theme_spiral_graph.json must be an object.")
    if "graph_metadata" not in graph or "theme_stage_nodes" not in graph or "spiral_edges" not in graph:
        return fail("theme spiral graph must contain graph_metadata, theme_stage_nodes, and spiral_edges.")
    if graph["graph_metadata"].get("contract_version") != "ULGA-S8H":
        return fail("theme spiral graph contract_version must be ULGA-S8H.")
    compliance = graph["graph_metadata"].get("learning_signal_compliance", {})
    if compliance.get("learning_signal_graph_generated") is not False:
        return fail("theme spiral graph must not generate a learning signal graph.")
    if compliance.get("dependency_graph_modified") is not False:
        return fail("theme spiral graph must not modify dependency graph.")

    stage_nodes = graph["theme_stage_nodes"]
    edges = graph["spiral_edges"]
    if not isinstance(stage_nodes, list) or not stage_nodes:
        return fail("theme_stage_nodes must be a non-empty list.")
    if not isinstance(edges, list) or not edges:
        return fail("spiral_edges must be a non-empty list.")

    source_theme_ids = {
        theme.get("theme_id")
        for payload in [theme_catalog, theme_mapping]
        for theme in payload.get("themes", [])
        if theme.get("theme_id")
    }

    stage_by_id = {}
    for index, node in enumerate(stage_nodes):
        if not validate_stage_node(node, index):
            return False
        if node["stage_id"] in stage_by_id:
            return fail(f"duplicate stage_id: {node['stage_id']}")
        missing_source_themes = set(node["source_theme_ids"]) - source_theme_ids
        if missing_source_themes:
            return fail(f"stage references missing source theme ids: {sorted(missing_source_themes)}")
        stage_by_id[node["stage_id"]] = node

    spiral_rule = next(
        (
            rule
            for rule in policy.get("signal_mapping_rules", [])
            if rule.get("source_relation") == RELATION
        ),
        None,
    )
    if spiral_rule is None:
        return fail("learning_signal_policy.json has no SPIRAL_TO mapping rule.")
    if spiral_rule.get("gate_allowed") is not False:
        return fail("learning signal policy must keep SPIRAL_TO gate_allowed=false.")

    seen_ids = set()
    seen_tuples = set()
    for index, edge in enumerate(edges):
        if not validate_edge_shape(edge, index):
            return False
        if edge["edge_id"] in seen_ids:
            return fail(f"duplicate edge_id: {edge['edge_id']}")
        seen_ids.add(edge["edge_id"])
        edge_tuple = (edge["source_stage_id"], edge["target_stage_id"], edge["relation"])
        if edge_tuple in seen_tuples:
            return fail(f"duplicate spiral tuple: {edge_tuple}")
        seen_tuples.add(edge_tuple)

        source_node = stage_by_id.get(edge["source_stage_id"])
        target_node = stage_by_id.get(edge["target_stage_id"])
        if source_node is None:
            return fail(f"missing source stage node: {edge['source_stage_id']}")
        if target_node is None:
            return fail(f"missing target stage node: {edge['target_stage_id']}")
        if source_node["theme_id"] != target_node["theme_id"]:
            return fail(f"cross-theme spiral edge detected: {edge['edge_id']}")
        if edge["theme_id"] != source_node["theme_id"]:
            return fail(f"edge theme_id does not match source stage theme_id: {edge['edge_id']}")
        if edge["source_cefr"] != source_node["cefr_band"] or edge["target_cefr"] != target_node["cefr_band"]:
            return fail(f"edge CEFR fields do not match stage nodes: {edge['edge_id']}")

    if has_cycle(edges):
        return fail("cycle detected in Theme Spiral graph.")

    stage_gap_edges = [
        edge
        for edge in edges
        if CEFR_RANK[edge["target_cefr"]] - CEFR_RANK[edge["source_cefr"]] > 1
    ]
    if stage_gap_edges:
        if not STAGE_GAP_REVIEW_QUEUE_PATH.exists():
            return fail("stage-gap review queue is required when stage-gap edges exist.")
        review_queue = read_json(STAGE_GAP_REVIEW_QUEUE_PATH)
        if review_queue is None:
            return False
        if not isinstance(review_queue, list):
            return fail("stage-gap review queue must be a list.")
        queue_by_edge_id = {entry.get("edge_id"): entry for entry in review_queue}
        for edge in stage_gap_edges:
            entry = queue_by_edge_id.get(edge["edge_id"])
            if entry is None:
                return fail(f"stage-gap edge missing from review queue: {edge['edge_id']}")
            if entry.get("gate_eligible") is not False:
                return fail(f"stage-gap review queue entry must be non-gating: {edge['edge_id']}")
            if entry.get("review_status") != "needs_review":
                return fail(f"stage-gap review queue entry must be needs_review: {edge['edge_id']}")

    print("ULGA Theme Spiral Graph validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
