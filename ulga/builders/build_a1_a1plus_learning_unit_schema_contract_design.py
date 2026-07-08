import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
IMPLEMENTATION_PLAN = BASE / "ulga" / "reports" / "a1_a1plus_clear_learning_unit_schema_implementation_plan.json"
OUT = BASE / "ulga" / "reports" / "a1_a1plus_learning_unit_schema_contract_design.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_a1plus_learning_unit_schema_contract_design_summary.json"
TASK_ID = "R7-M104E8_A1A1PlusLearningUnitSchemaContractDesign"

COMMON_REQUIRED_FIELDS = [
    "learning_unit_id",
    "learning_unit_type",
    "schema_version",
    "cefr_level",
    "egp_cluster_refs",
    "source_refs",
    "status",
]

COMMON_PROPERTIES = {
    "learning_unit_id": {"type": "string"},
    "learning_unit_type": {"type": "string"},
    "schema_version": {"type": "string"},
    "cefr_level": {"type": "string", "enum": ["A1", "A1_PLUS"]},
    "egp_cluster_refs": {"type": "array", "items": {"type": "string"}},
    "source_refs": {"type": "array", "items": {"type": "string"}},
    "status": {"type": "string", "enum": ["draft", "reviewed", "promoted", "deprecated"]},
}

FAMILY_SPECIFIC_PROPERTIES = {
    "phrase_pattern_schema": {
        "phrase_head_type": {"type": "string"},
        "slot_model": {"type": "object"},
        "constraints": {"type": "array", "items": {"type": "object"}},
        "positive_examples": {"type": "array", "items": {"type": "string"}},
        "negative_examples": {"type": "array", "items": {"type": "string"}},
    },
    "sentence_pattern_schema": {
        "sentence_role_model": {"type": "object"},
        "slot_sequence": {"type": "array", "items": {"type": "string"}},
        "transformations": {"type": "array", "items": {"type": "object"}},
        "positive_examples": {"type": "array", "items": {"type": "string"}},
        "negative_examples": {"type": "array", "items": {"type": "string"}},
    },
    "construction_schema": {
        "construction_type": {"type": "string"},
        "head_pattern": {"type": "object"},
        "complement_model": {"type": "object"},
        "constraints": {"type": "array", "items": {"type": "object"}},
        "positive_examples": {"type": "array", "items": {"type": "string"}},
        "negative_examples": {"type": "array", "items": {"type": "string"}},
    },
    "usage_constraint_schema": {
        "constraint_type": {"type": "string"},
        "applies_to": {"type": "array", "items": {"type": "string"}},
        "allowed_values": {"type": "array", "items": {"type": "string"}},
        "blocked_values": {"type": "array", "items": {"type": "string"}},
        "examples": {"type": "array", "items": {"type": "string"}},
    },
    "composite_learning_unit_schema": {
        "component_node_refs": {"type": "array", "items": {"type": "string"}},
        "composition_rule": {"type": "object"},
        "role_mapping": {"type": "object"},
        "positive_examples": {"type": "array", "items": {"type": "string"}},
        "negative_examples": {"type": "array", "items": {"type": "string"}},
    },
}

FAMILY_TYPE = {
    "phrase_pattern_schema": "PHRASE_PATTERN_NODE",
    "sentence_pattern_schema": "SENTENCE_PATTERN_NODE",
    "construction_schema": "CONSTRUCTION_NODE",
    "usage_constraint_schema": "USAGE_CONSTRAINT",
    "composite_learning_unit_schema": "MULTI_NODE_COMPOSITE",
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    plan = load(IMPLEMENTATION_PLAN)
    implementation_units = plan.get("implementation_units", [])
    contract_designs = []
    family_counts = {}
    contract_field_counts = {}
    source_item_total = 0
    for unit in sorted(implementation_units, key=lambda u: u.get("schema_family") or ""):
        family = unit.get("schema_family")
        specific = FAMILY_SPECIFIC_PROPERTIES.get(family, {})
        properties = dict(COMMON_PROPERTIES)
        properties.update(specific)
        required = list(COMMON_REQUIRED_FIELDS)
        for field in specific:
            if field not in required:
                required.append(field)
        source_count = unit.get("source_item_count", 0)
        source_item_total += source_count
        family_counts[family] = source_count
        contract_field_counts[family] = len(required)
        contract_designs.append({
            "schema_family": family,
            "learning_unit_type": FAMILY_TYPE.get(family, unit.get("learning_unit_type")),
            "source_item_count": source_count,
            "planned_schema_path": unit.get("planned_schema_path"),
            "contract_status": "DESIGN_ONLY_NOT_IMPLEMENTED",
            "draft_schema_contract": {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "title": family,
                "type": "object",
                "required": required,
                "additionalProperties": False,
                "properties": properties,
            },
            "validator_contract": {
                "must_validate_required_fields": True,
                "must_reject_unknown_fields": True,
                "must_validate_cefr_a1_a1plus_only": True,
                "must_require_egp_cluster_refs": True,
                "must_require_source_refs": True,
                "must_keep_canonical_write_blocked": True,
            },
            "builder_contract": {
                "input_source": "clear active lane schema planning packet",
                "output_policy": "static report artifacts only before canonical promotion",
                "source_cluster_ids": [cluster.get("cluster_id") for cluster in unit.get("source_clusters", [])],
            },
            "extension_note": unit.get("extension_note"),
        })
    report = {
        "task_id": TASK_ID,
        "artifact_id": "a1_a1plus_learning_unit_schema_contract_design",
        "source_artifact_id": plan.get("artifact_id"),
        "contract_scope": "design only for A1/A1+ clear-lane learning unit schema contracts",
        "foundation_policy": {
            "foundation_not_final_taxonomy": True,
            "future_extension_allowed": True,
            "extension_targets": plan.get("future_extension_allowed", []),
        },
        "contract_designs": contract_designs,
        "implementation_not_started": True,
        "not_allowed_scope": [
            "creating schema contract files under ulga/schemas/learning_units",
            "canonical grammar node writes",
            "canonical pattern graph writes",
            "deferred lane processing",
            "A2/A2+ progression",
        ],
        "next_implementation_scope_candidate": {
            "recommended_next_task": "R7-M104E9_A1A1PlusLearningUnitSchemaContractFilesImplementation",
            "requires_operator_approval": True,
            "reason": "Next step creates schema contract files, moving from design packet to implementation artifacts.",
        },
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "canonical_grammar_write_allowed": False,
        "canonical_pattern_write_allowed": False,
        "local_validation_required": True,
        "ci_gate_required": False,
    }
    summary = {
        "task_id": TASK_ID,
        "artifact_id": "a1_a1plus_learning_unit_schema_contract_design_summary",
        "validation_status": "PASS",
        "source_implementation_unit_count": len(implementation_units),
        "contract_design_count": len(contract_designs),
        "source_schema_planning_item_count": source_item_total,
        "schema_family_counts": dict(sorted(family_counts.items())),
        "contract_field_counts": dict(sorted(contract_field_counts.items())),
        "foundation_not_final_taxonomy": True,
        "future_extension_allowed": True,
        "implementation_not_started": True,
        "deferred_lane_processing_allowed": False,
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "canonical_grammar_write_allowed": False,
        "canonical_pattern_write_allowed": False,
        "next_short_step": "R7-M104E9_A1A1PlusLearningUnitSchemaContractFilesImplementation",
        "stop_reason": "OPERATOR_APPROVAL_REQUIRED",
    }
    write(OUT, report)
    write(SUMMARY, summary)
    print("A1/A1+ learning unit schema contract design build: PASS")
    print("Contract designs:", len(contract_designs))
    print("Source schema planning items:", source_item_total)
    print("Schema families:", summary["schema_family_counts"])
    print("Implementation not started:", summary["implementation_not_started"])


if __name__ == "__main__":
    main()
