import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
LANE_PACKET = BASE / "ulga" / "reports" / "a1_a1plus_clear_learning_unit_lane_packet.json"
SCHEMA_DIR = BASE / "ulga" / "schemas" / "learning_units"
OUT = BASE / "ulga" / "learning_units" / "draft" / "a1_a1plus_clear_lane_learning_unit_draft_artifacts.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_a1plus_clear_lane_learning_unit_draft_artifacts_summary.json"
TASK_ID = "R7-M104E10_A1A1PlusClearLaneLearningUnitDraftArtifactsImplementation"
SCHEMA_VERSION = "0.1.0-foundation"
DEFAULT_CEFR_LEVEL = "A1"

TYPE_TO_SCHEMA = {
    "PHRASE_PATTERN_NODE": "phrase_pattern_unit_schema.json",
    "SENTENCE_PATTERN_NODE": "sentence_pattern_unit_schema.json",
    "CONSTRUCTION_NODE": "construction_unit_schema.json",
    "USAGE_CONSTRAINT": "usage_constraint_unit_schema.json",
    "MULTI_NODE_COMPOSITE": "composite_learning_unit_schema.json",
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def slug(value):
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "unknown"


def make_learning_unit_id(item):
    return "a1_a1plus_lu_" + slug(item.get("cluster_id") or item.get("cluster_key") or "unknown")


def draft_source_ref(item):
    return f"a1_a1plus_clear_learning_unit_lane_packet:{item.get('cluster_id')}"


def draft_example(item):
    return "DRAFT_EXAMPLE_REQUIRES_OPERATOR_REVIEW: " + (item.get("cluster_key") or item.get("cluster_id") or "unknown")


def base_unit(item):
    return {
        "learning_unit_id": make_learning_unit_id(item),
        "learning_unit_type": item.get("learning_unit_type"),
        "schema_version": SCHEMA_VERSION,
        "cefr_level": DEFAULT_CEFR_LEVEL,
        "egp_cluster_refs": [item.get("cluster_id")],
        "source_refs": [draft_source_ref(item)],
        "status": "draft",
    }


def phrase_head_type(item):
    key = (item.get("cluster_key") or "").lower()
    if "preposition" in key or "prepositional" in key:
        return "prepositional_phrase"
    if "adjective" in key:
        return "adjective_noun_phrase"
    if "determiner" in key or "article" in key or "noun" in key:
        return "noun_phrase"
    return "phrase_pattern"


def construction_type(item):
    key = (item.get("cluster_key") or "").lower()
    if "clause" in key:
        return "clause_construction"
    if "verb" in key:
        return "verb_complement_construction"
    if "pronoun" in key:
        return "lexicalized_pronoun_construction"
    return "construction"


def constraint_type(item):
    key = (item.get("cluster_key") or "").lower()
    if "noun" in key and "type" in key:
        return "noun_type_constraint"
    return "usage_constraint"


def build_draft_unit(item):
    unit = base_unit(item)
    lut = item.get("learning_unit_type")
    if lut == "PHRASE_PATTERN_NODE":
        unit.update({
            "phrase_head_type": phrase_head_type(item),
            "slot_model": {
                "status": "draft_placeholder",
                "source_cluster_key": item.get("cluster_key"),
                "requires_operator_review_before_promotion": True,
            },
            "constraints": [],
            "positive_examples": [draft_example(item)],
            "negative_examples": [],
        })
    elif lut == "SENTENCE_PATTERN_NODE":
        unit.update({
            "sentence_role_model": {
                "status": "draft_placeholder",
                "source_cluster_key": item.get("cluster_key"),
                "requires_operator_review_before_promotion": True,
            },
            "slot_sequence": ["DRAFT_SLOT_SEQUENCE_REQUIRES_OPERATOR_REVIEW"],
            "transformations": [],
            "positive_examples": [draft_example(item)],
            "negative_examples": [],
        })
    elif lut == "CONSTRUCTION_NODE":
        unit.update({
            "construction_type": construction_type(item),
            "head_pattern": {
                "status": "draft_placeholder",
                "source_cluster_key": item.get("cluster_key"),
                "requires_operator_review_before_promotion": True,
            },
            "complement_model": {
                "status": "draft_placeholder",
                "source_cluster_key": item.get("cluster_key"),
                "requires_operator_review_before_promotion": True,
            },
            "constraints": [],
            "positive_examples": [draft_example(item)],
            "negative_examples": [],
        })
    elif lut == "USAGE_CONSTRAINT":
        unit.update({
            "constraint_type": constraint_type(item),
            "applies_to": [item.get("cluster_id")],
            "allowed_values": [],
            "blocked_values": [],
            "examples": [draft_example(item)],
        })
    elif lut == "MULTI_NODE_COMPOSITE":
        unit.update({
            "component_node_refs": ["DRAFT_COMPONENT_NODE_REQUIRES_OPERATOR_REVIEW"],
            "composition_rule": {
                "status": "draft_placeholder",
                "source_cluster_key": item.get("cluster_key"),
                "requires_operator_review_before_promotion": True,
            },
            "role_mapping": {
                "status": "draft_placeholder",
                "source_cluster_key": item.get("cluster_key"),
                "requires_operator_review_before_promotion": True,
            },
            "positive_examples": [draft_example(item)],
            "negative_examples": [],
        })
    else:
        raise ValueError(f"Unsupported learning_unit_type: {lut}")
    return unit


def build_artifact(item):
    schema_file = TYPE_TO_SCHEMA[item.get("learning_unit_type")]
    return {
        "artifact_id": "draft_" + make_learning_unit_id(item),
        "artifact_status": "DRAFT_NOT_CANONICAL",
        "source_cluster": {
            "cluster_id": item.get("cluster_id"),
            "cluster_key": item.get("cluster_key"),
            "row_count": item.get("row_count"),
            "missing_row_count": item.get("missing_row_count"),
            "recommended_decision_path": item.get("recommended_decision_path"),
            "classification_rationale": item.get("classification_rationale", []),
        },
        "schema_contract_path": "ulga/schemas/learning_units/" + schema_file,
        "draft_learning_unit": build_draft_unit(item),
        "promotion_policy": {
            "requires_operator_review_before_promotion": True,
            "canonical_grammar_write_allowed": False,
            "canonical_pattern_write_allowed": False,
        },
    }


def count_by(items, key_fn):
    counts = {}
    for item in items:
        key = key_fn(item)
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def main():
    lane = load(LANE_PACKET)
    clear_items = lane.get("clear_active_lane_items", [])
    if len(clear_items) != 19:
        raise ValueError(f"Expected 19 clear active lane items, got {len(clear_items)}")
    artifacts = [build_artifact(item) for item in sorted(clear_items, key=lambda x: (x.get("learning_unit_type") or "", x.get("cluster_id") or ""))]
    collection = {
        "task_id": TASK_ID,
        "artifact_id": "a1_a1plus_clear_lane_learning_unit_draft_artifacts",
        "source_artifact_id": lane.get("artifact_id"),
        "artifact_status": "DRAFT_NOT_CANONICAL",
        "cefr_assignment_policy": "draft_default_a1_until_row_level_a1_plus_split_is_reviewed",
        "schema_version": SCHEMA_VERSION,
        "draft_artifacts": artifacts,
        "deferred_lane_processing_allowed": False,
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "canonical_grammar_write_allowed": False,
        "canonical_pattern_write_allowed": False,
        "local_validation_required": True,
        "ci_gate_required": False,
    }
    summary = {
        "task_id": TASK_ID,
        "artifact_id": "a1_a1plus_clear_lane_learning_unit_draft_artifacts_summary",
        "validation_status": "PASS",
        "draft_artifact_count": len(artifacts),
        "schema_contract_file_count": len(set(a["schema_contract_path"] for a in artifacts)),
        "learning_unit_type_counts": count_by(artifacts, lambda a: a["draft_learning_unit"]["learning_unit_type"]),
        "artifact_status_counts": count_by(artifacts, lambda a: a["artifact_status"]),
        "cefr_level_counts": count_by(artifacts, lambda a: a["draft_learning_unit"]["cefr_level"]),
        "foundation_not_final_taxonomy": True,
        "future_extension_allowed": True,
        "deferred_lane_processing_allowed": False,
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "canonical_grammar_write_allowed": False,
        "canonical_pattern_write_allowed": False,
        "next_short_step": "R7-M104E11_A1A1PlusClearLaneDraftArtifactReviewPacket",
        "stop_reason": "OPERATOR_REVIEW_REQUIRED",
    }
    write(OUT, collection)
    write(SUMMARY, summary)
    print("A1/A1+ clear lane learning unit draft artifacts build: PASS")
    print("Draft artifacts:", len(artifacts))
    print("Learning unit types:", summary["learning_unit_type_counts"])
    print("Artifact output:", OUT.relative_to(BASE))


if __name__ == "__main__":
    main()
