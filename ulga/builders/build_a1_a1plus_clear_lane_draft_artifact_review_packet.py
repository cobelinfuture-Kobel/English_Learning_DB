import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
DRAFTS = BASE / "ulga" / "learning_units" / "draft" / "a1_a1plus_clear_lane_learning_unit_draft_artifacts.json"
OUT = BASE / "ulga" / "reports" / "a1_a1plus_clear_lane_draft_artifact_review_packet.json"
SUMMARY = BASE / "ulga" / "reports" / "a1_a1plus_clear_lane_draft_artifact_review_packet_summary.json"
TASK_ID = "R7-M104E11_A1A1PlusClearLaneDraftArtifactReviewPacket"

REVIEW_CHECKS = [
    "schema_contract_fit",
    "learning_unit_type_fit",
    "source_cluster_traceability",
    "placeholder_fields_need_operator_completion",
    "example_quality_review",
    "promotion_block_confirmed",
]


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def count_by(items, key_fn):
    counts = {}
    for item in items:
        key = key_fn(item)
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def placeholder_fields(unit):
    fields = []
    for key, value in unit.items():
        if isinstance(value, str) and "DRAFT_" in value:
            fields.append(key)
        elif isinstance(value, list):
            for entry in value:
                if isinstance(entry, str) and "DRAFT_" in entry:
                    fields.append(key)
                    break
        elif isinstance(value, dict) and value.get("status") == "draft_placeholder":
            fields.append(key)
    return sorted(set(fields))


def review_item(artifact):
    unit = artifact.get("draft_learning_unit", {})
    source = artifact.get("source_cluster", {})
    placeholders = placeholder_fields(unit)
    return {
        "review_item_id": "review_" + artifact.get("artifact_id", "unknown"),
        "artifact_id": artifact.get("artifact_id"),
        "artifact_status": artifact.get("artifact_status"),
        "learning_unit_id": unit.get("learning_unit_id"),
        "learning_unit_type": unit.get("learning_unit_type"),
        "cefr_level": unit.get("cefr_level"),
        "schema_contract_path": artifact.get("schema_contract_path"),
        "source_cluster": source,
        "required_review_checks": REVIEW_CHECKS,
        "placeholder_fields": placeholders,
        "placeholder_field_count": len(placeholders),
        "review_decision_options": [
            "APPROVE_DRAFT_FOR_PROMOTION_PLANNING",
            "ADJUST_DRAFT_FIELDS_BEFORE_PROMOTION_PLANNING",
            "DEFER_DRAFT_FOR_SOURCE_REVIEW",
        ],
        "recommended_default_decision": "ADJUST_DRAFT_FIELDS_BEFORE_PROMOTION_PLANNING" if placeholders else "APPROVE_DRAFT_FOR_PROMOTION_PLANNING",
        "operator_review_status": "PENDING_OPERATOR_REVIEW",
        "canonical_grammar_write_allowed": False,
        "canonical_pattern_write_allowed": False,
    }


def main():
    drafts = load(DRAFTS)
    artifacts = drafts.get("draft_artifacts", [])
    if len(artifacts) != 19:
        raise ValueError(f"Expected 19 draft artifacts, got {len(artifacts)}")
    items = [review_item(artifact) for artifact in sorted(artifacts, key=lambda a: (a.get("draft_learning_unit", {}).get("learning_unit_type") or "", a.get("artifact_id") or ""))]
    groups = []
    for lut in sorted(set(item["learning_unit_type"] for item in items)):
        group_items = [item for item in items if item["learning_unit_type"] == lut]
        groups.append({
            "learning_unit_type": lut,
            "review_item_count": len(group_items),
            "placeholder_field_total": sum(item["placeholder_field_count"] for item in group_items),
            "items": group_items,
        })
    total_placeholder_fields = sum(item["placeholder_field_count"] for item in items)
    report = {
        "task_id": TASK_ID,
        "artifact_id": "a1_a1plus_clear_lane_draft_artifact_review_packet",
        "source_artifact_id": drafts.get("artifact_id"),
        "review_scope": "review packet for 19 A1/A1+ clear-lane draft learning-unit artifacts",
        "review_groups": groups,
        "review_policy": {
            "promotion_planning_allowed_after_review": True,
            "promotion_allowed_now": False,
            "canonical_grammar_write_allowed": False,
            "canonical_pattern_write_allowed": False,
            "deferred_lane_processing_allowed": False,
            "a2_a2plus_progression_allowed": False,
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
        "artifact_id": "a1_a1plus_clear_lane_draft_artifact_review_packet_summary",
        "validation_status": "PASS",
        "source_draft_artifact_count": len(artifacts),
        "review_group_count": len(groups),
        "review_item_count": len(items),
        "learning_unit_type_counts": count_by(items, lambda item: item["learning_unit_type"]),
        "review_status_counts": count_by(items, lambda item: item["operator_review_status"]),
        "recommended_default_decision_counts": count_by(items, lambda item: item["recommended_default_decision"]),
        "total_placeholder_field_count": total_placeholder_fields,
        "promotion_allowed_now": False,
        "promotion_planning_allowed_after_review": True,
        "foundation_not_final_taxonomy": True,
        "future_extension_allowed": True,
        "deferred_lane_processing_allowed": False,
        "final_closeout_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "canonical_grammar_write_allowed": False,
        "canonical_pattern_write_allowed": False,
        "next_short_step": "R7-M104E12_A1A1PlusClearLaneDraftArtifactOperatorReviewDecisionPacket",
        "stop_reason": "OPERATOR_REVIEW_REQUIRED",
    }
    write(OUT, report)
    write(SUMMARY, summary)
    print("A1/A1+ clear lane draft artifact review packet build: PASS")
    print("Review items:", len(items))
    print("Review groups:", len(groups))
    print("Learning unit types:", summary["learning_unit_type_counts"])
    print("Total placeholder fields:", total_placeholder_fields)


if __name__ == "__main__":
    main()
