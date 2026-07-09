import json
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

S0_POLICY_PATH = BASE_DIR / "ulga" / "reports" / "os_taxonomy_source_license_scope_policy.json"
S1_MAPPING_PATH = BASE_DIR / "ulga" / "reports" / "os_taxonomy_schema_mapping_foundation.json"
S2_POLICY_PATH = BASE_DIR / "ulga" / "reports" / "os_taxonomy_reference_node_edge_layer_policy.json"
NODE_SCHEMA_PATH = BASE_DIR / "ulga" / "schemas" / "external_reference_node.schema.json"
EDGE_SCHEMA_PATH = BASE_DIR / "ulga" / "schemas" / "external_reference_edge.schema.json"


REQUIRED_ARTIFACTS = [
    S0_POLICY_PATH,
    S1_MAPPING_PATH,
    S2_POLICY_PATH,
    NODE_SCHEMA_PATH,
    EDGE_SCHEMA_PATH,
]


FORBIDDEN_CANONICAL_PATHS = [
    BASE_DIR / "ulga" / "graph" / "canonical_graph.json",
    BASE_DIR / "ulga" / "graph" / "dependency_graph.json",
    BASE_DIR / "ulga" / "graph" / "grammar_nodes.json",
    BASE_DIR / "ulga" / "graph" / "grammar_edges.json",
    BASE_DIR / "ulga" / "graph" / "os_taxonomy_reference_nodes_candidate.json",
    BASE_DIR / "ulga" / "graph" / "os_taxonomy_reference_edges_candidate.json",
]


def fail(message):
    print(f"FAIL: {message}")
    return False


def read_json(path):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        raise ValueError(f"could not load {path}: {exc}") from exc


def require_file(path):
    if not path.exists():
        return fail(f"required artifact missing: {path.relative_to(BASE_DIR).as_posix()}")
    return True


def validate_s0(policy):
    if policy.get("task_id") != "AUX-OSTX-S0_SourceLicenseAndScopeFoundation":
        return fail("S0 task_id mismatch")
    use_policy = policy.get("use_policy", {})
    required_false = [
        "direct_use_allowed",
        "authority_import_allowed",
        "content_extraction_allowed",
        "learner_facing_allowed",
        "canonical_promotion_allowed",
        "cambridge_authority",
        "egp_replacement",
        "evp_replacement",
        "ngsl_replacement",
        "raz_replacement",
    ]
    for key in required_false:
        if use_policy.get(key) is not False:
            return fail(f"S0 use_policy.{key} must be false")
    if use_policy.get("use_policy") != "reference_only":
        return fail("S0 use_policy must be reference_only")
    restricted_fields = policy.get("license_policy", {}).get("restricted_text_fields", [])
    for field in [
        "topic.name",
        "topic.description",
        "topic.evidence",
        "topic.assessmentPrompt",
        "dependency.reason",
        "cluster.summary",
    ]:
        if field not in restricted_fields:
            return fail(f"S0 restricted field missing: {field}")
    return True


def validate_s1(mapping):
    if mapping.get("task_id") != "AUX-OSTX-S1_SchemaMappingFoundation":
        return fail("S1 task_id mismatch")
    if mapping.get("promotion_policy", {}).get("canonical_promotion_allowed") is not False:
        return fail("S1 canonical promotion must be blocked")
    if mapping.get("restricted_text_policy", {}).get("learner_facing_allowed") is not False:
        return fail("S1 learner-facing restricted text must be blocked")
    if mapping.get("external_standard_policy", {}).get("standard_text_import_allowed") is not False:
        return fail("S1 curriculum standard text import must be blocked")
    for section in ["topic_field_mapping", "dependency_field_mapping", "cluster_field_mapping"]:
        if not mapping.get(section):
            return fail(f"S1 mapping section missing: {section}")
    restricted_entries = []
    for section in ["topic_field_mapping", "dependency_field_mapping", "cluster_field_mapping"]:
        restricted_entries.extend(
            entry for entry in mapping.get(section, []) if entry.get("field_classification") == "restricted_text_field"
        )
    if not restricted_entries:
        return fail("S1 has no restricted text field classifications")
    return True


def validate_s2(policy, node_schema, edge_schema):
    if policy.get("task_id") != "AUX-OSTX-S2_ReferenceNodeEdgeLayer":
        return fail("S2 task_id mismatch")
    layer = policy.get("reference_layer_policy", {})
    for key in [
        "canonical_promotion_allowed",
        "learner_facing_allowed",
        "content_extraction_allowed",
        "verbatim_text_copy_allowed",
    ]:
        if layer.get(key) is not False:
            return fail(f"S2 reference_layer_policy.{key} must be false")
    if layer.get("authority_status") != "reference_only":
        return fail("S2 authority_status must be reference_only")
    if policy.get("promotion_policy", {}).get("canonical_graph_write_allowed") is not False:
        return fail("S2 canonical graph write must be blocked")
    if policy.get("promotion_policy", {}).get("verified_dependency_write_allowed") is not False:
        return fail("S2 verified dependency write must be blocked")
    if node_schema.get("properties", {}).get("authority_status", {}).get("const") != "reference_only":
        return fail("node schema authority_status const must be reference_only")
    if edge_schema.get("properties", {}).get("authority_status", {}).get("const") != "reference_only":
        return fail("edge schema authority_status const must be reference_only")
    for schema_name, schema in [("node", node_schema), ("edge", edge_schema)]:
        for key in ["canonical_promotion_allowed", "learner_facing_allowed"]:
            if schema.get("properties", {}).get(key, {}).get("const") is not False:
                return fail(f"{schema_name} schema {key} const must be false")
    return True


def validate_no_forbidden_outputs():
    for path in FORBIDDEN_CANONICAL_PATHS:
        if path.name.startswith("os_taxonomy_reference_") and path.exists():
            return fail(f"S12A forbids populated candidate artifact at this stage: {path.relative_to(BASE_DIR).as_posix()}")
    return True


def validate():
    print("Validating OS Taxonomy reference foundation...")
    for path in REQUIRED_ARTIFACTS:
        if not require_file(path):
            return False

    try:
        s0_policy = read_json(S0_POLICY_PATH)
        s1_mapping = read_json(S1_MAPPING_PATH)
        s2_policy = read_json(S2_POLICY_PATH)
        node_schema = read_json(NODE_SCHEMA_PATH)
        edge_schema = read_json(EDGE_SCHEMA_PATH)
    except ValueError as exc:
        return fail(str(exc))

    checks = [
        validate_s0(s0_policy),
        validate_s1(s1_mapping),
        validate_s2(s2_policy, node_schema, edge_schema),
        validate_no_forbidden_outputs(),
    ]
    if not all(checks):
        return False

    print("OS Taxonomy reference foundation validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
