import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
SCHEMA_PLAN = BASE / "ulga" / "reports" / "a1_a1plus_clear_learning_unit_schema_planning_packet.json"
OUT = BASE / "ulga" / "reports" / "a1_a1plus_clear_learning_unit_schema_implementation_plan.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_a1plus_clear_learning_unit_schema_implementation_plan_summary.json"
TASK_ID = "R7-M104E7_A1A1PlusClearLearningUnitSchemaImplementationPlan"

SCHEMA_TARGETS = {
    "phrase_pattern_schema": {
        "planned_schema_path": "ulga/schemas/learning_units/phrase_pattern_unit_schema.json",
        "planned_builder_family": "phrase_pattern_learning_unit_builder",
        "planned_validator_family": "phrase_pattern_learning_unit_validator",
        "graph_output_policy": "planned_static_report_only_before_canonical_promotion",
        "extension_note": "foundation only; can later split into noun/preposition/adjective/determiner phrase subfamilies",
    },
    "sentence_pattern_schema": {
        "planned_schema_path": "ulga/schemas/learning_units/sentence_pattern_unit_schema.json",
        "planned_builder_family": "sentence_pattern_learning_unit_builder",
        "planned_validator_family": "sentence_pattern_learning_unit_validator",
        "graph_output_policy": "planned_static_report_only_before_canonical_promotion",
        "extension_note": "foundation only; can later extend to clause, question, transformation, and discourse sentence roles",
    },
    "construction_schema": {
        "planned_schema_path": "ulga/schemas/learning_units/construction_unit_schema.json",
        "planned_builder_family": "construction_learning_unit_builder",
        "planned_validator_family": "construction_learning_unit_validator",
        "graph_output_policy": "planned_static_report_only_before_canonical_promotion",
        "extension_note": "foundation only; can later split into verb-complement, clause-complement, and lexicalized construction subfamilies",
    },
    "usage_constraint_schema": {
        "planned_schema_path": "ulga/schemas/learning_units/usage_constraint_unit_schema.json",
        "planned_builder_family": "usage_constraint_learning_unit_builder",
        "planned_validator_family": "usage_constraint_learning_unit_validator",
        "graph_output_policy": "planned_static_report_only_before_canonical_promotion",
        "extension_note": "foundation only; can later cover countability, reference, quantity, distribution, and register constraints",
    },
    "composite_learning_unit_schema": {
        "planned_schema_path": "ulga/schemas/learning_units/composite_learning_unit_schema.json",
        "planned_builder_family": "composite_learning_unit_builder",
        "planned_validator_family": "composite_learning_unit_validator",
        "graph_output_policy": "planned_static_report_only_before_canonical_promotion",
        "extension_note": "foundation only; can later support cross-skill bundles and paragraph/writing-unit composition",
    },
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    schema_plan = load(SCHEMA_PLAN)
    schema_groups = schema_plan.get("schema_groups", [])
    implementation_units = []
    family_counts = {}
    item_total = 0
    for group in sorted(schema_groups, key=lambda g: g.get("schema_family") or ""):
        family = group.get("schema_family")
        target = SCHEMA_TARGETS.get(family)
        if target is None:
            target = default_schema_target(family)
        items = group.get("items", [])
        family_counts[family] = len(items)
        item_total += len(items)
        implementation_units.append({
            "schema_family": family,
            "learning_unit_type": group.get("learning_unit_type"),
            "source_item_count": len(items),
            "planned_schema_path": target["planned_schema_path"],
            "planned_builder_family": target["planned_builder_family"],
            "planned_validator_family": target["planned_validator_family"],
            "graph_output_policy": target["graph_output_policy"],
            "extension_note": target["extension_note"],
            "minimum_contract_fields": group.get("required_fields", []),
            "source_clusters": [
                {
                    "cluster_id": item.get("cluster_id"),
                    "cluster_key": item.get("cluster_key"),
                    "missing_row_count": item.get("missing_row_count"),
                    "recommended_decision_path": item.get("recommended_decision_path"),
                }
                for item in sorted(items, key=lambda x: (-(x.get("missing_row_count") or 0), x.get("cluster_key") or ""))
            ],
        })
    report = {
        "task_id": TASK_ID,
        "artifact_id": "a1_a1plus_clear_learning_unit_schema_implementation_plan",
        "source_artifact_id": schema_plan.get("artifact_id"),
        "operator_approval_basis": "E7 approved: five schema families are an A1/A1+ clear-lane foundation, not final linguistic taxonomy",
        "planning_scope": "implementation planning only for 19 clear active lane items",
        "language_learning_progression_note": "Foundation supports later extension from words/forms to phrases, clauses, sentences, paragraphs, and essays.",
        "implementation_units": implementation_units,
        "implementation_sequence": [
            "create schema contract files under ulga/schemas/learning_units",
            "create validators for schema contract structure",
            "create planning/report builders that emit static reports only",
            "validate clear-lane source item coverage",
            "keep deferred lane out of scope",
            "require a later explicit gate before canonical graph writes",
        ],
        "not_allowed_scope": [
            "canonical grammar node writes",
            "canonical pattern graph writes",
            "deferred lane processing",
            "A2/A2+ progression",
            "treating the five schema families as final complete linguistic taxonomy",
        ],
        "future_extension_allowed": [
            "clause pattern schema",
            "discourse connector schema",
            "paragraph structure schema",
            "essay structure schema",
            "writing genre schema",
            "error tag schema",
            "cross-skill task schema",
        ],
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "canonical_grammar_write_allowed": False,
        "canonical_pattern_write_allowed": False,
        "local_validation_required": True,
        "ci_gate_required": False,
    }
    summary = {
        "task_id": TASK_ID,
        "artifact_id": "a1_a1plus_clear_learning_unit_schema_implementation_plan_summary",
        "validation_status": "PASS",
        "source_schema_group_count": len(schema_groups),
        "implementation_unit_count": len(implementation_units),
        "source_schema_planning_item_count": item_total,
        "schema_family_counts": dict(sorted(family_counts.items())),
        "foundation_not_final_taxonomy": True,
        "future_extension_allowed": True,
        "deferred_lane_processing_allowed": False,
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "canonical_grammar_write_allowed": False,
        "canonical_pattern_write_allowed": False,
        "next_short_step": "R7-M104E8_A1A1PlusLearningUnitSchemaContractDesign",
        "stop_reason": "NONE",
    }
    write(OUT, report)
    write(SUMMARY, summary)
    print("A1/A1+ clear learning unit schema implementation plan build: PASS")
    print("Implementation units:", len(implementation_units))
    print("Source schema planning items:", item_total)
    print("Schema families:", summary["schema_family_counts"])
    print("Foundation not final taxonomy:", summary["foundation_not_final_taxonomy"])


def default_schema_target(family):
    safe_family = (family or "unknown_schema").replace("/", "_")
    return {
        "planned_schema_path": f"ulga/schemas/learning_units/{safe_family}.json",
        "planned_builder_family": f"{safe_family}_builder",
        "planned_validator_family": f"{safe_family}_validator",
        "graph_output_policy": "planned_static_report_only_before_canonical_promotion",
        "extension_note": "foundation only; requires later review before specialization",
    }


if __name__ == "__main__":
    main()
