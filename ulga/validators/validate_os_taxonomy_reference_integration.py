import json
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
REPORTS = BASE_DIR / "ulga" / "reports"
SCHEMAS = BASE_DIR / "ulga" / "schemas"

REQUIRED_JSON_ARTIFACTS = {
    "s0": REPORTS / "os_taxonomy_source_license_scope_policy.json",
    "s1": REPORTS / "os_taxonomy_schema_mapping_foundation.json",
    "s2": REPORTS / "os_taxonomy_reference_node_edge_layer_policy.json",
    "s3": REPORTS / "os_taxonomy_english_domain_mapping.json",
    "s4": REPORTS / "os_taxonomy_dependency_signal_mapping.json",
    "s5": REPORTS / "grammar_skill_tree_os_taxonomy_reference_candidates.json",
    "s6": REPORTS / "reading_v1_os_taxonomy_skill_depth_mapping.json",
    "s7": REPORTS / "phonics_word_reading_reference_mapping.json",
    "s8": REPORTS / "mastery_evidence_reference_schema.json",
    "s9": REPORTS / "os_taxonomy_planner_reference_signal_policy.json",
    "s10": REPORTS / "os_taxonomy_four_skill_readiness.json",
    "s11": REPORTS / "parent_explanation_reference_policy.json",
    "node_schema": SCHEMAS / "external_reference_node.schema.json",
    "edge_schema": SCHEMAS / "external_reference_edge.schema.json",
}


class ValidationError(Exception):
    pass


def load_json(path: Path):
    if not path.exists():
        raise ValidationError(f"missing artifact: {path.relative_to(BASE_DIR).as_posix()}")
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        raise ValidationError(f"invalid JSON {path.relative_to(BASE_DIR).as_posix()}: {exc}") from exc


def require(condition, message):
    if not condition:
        raise ValidationError(message)


def expect_false(obj, key_path):
    cur = obj
    for key in key_path:
        cur = cur.get(key, {}) if isinstance(cur, dict) else None
    require(cur is False, ".".join(key_path) + " must be false")


def expect_true(obj, key_path):
    cur = obj
    for key in key_path:
        cur = cur.get(key, {}) if isinstance(cur, dict) else None
    require(cur is True, ".".join(key_path) + " must be true")


def validate_all(artifacts):
    s0 = artifacts["s0"]
    require(s0.get("use_policy", {}).get("use_policy") == "reference_only", "S0 use_policy must be reference_only")
    for key in [
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
    ]:
        expect_false(s0, ["use_policy", key])

    s1 = artifacts["s1"]
    expect_false(s1, ["restricted_text_policy", "learner_facing_allowed"])
    expect_false(s1, ["external_standard_policy", "standard_text_import_allowed"])
    expect_false(s1, ["promotion_policy", "canonical_promotion_allowed"])

    s2 = artifacts["s2"]
    for key in ["canonical_promotion_allowed", "learner_facing_allowed", "content_extraction_allowed", "verbatim_text_copy_allowed"]:
        expect_false(s2, ["reference_layer_policy", key])
    expect_false(s2, ["promotion_policy", "canonical_graph_write_allowed"])
    expect_false(s2, ["promotion_policy", "verified_dependency_write_allowed"])

    s3 = artifacts["s3"]
    require("summary" in s3.get("source_basis", {}).get("restricted_fields_not_used", []), "S3 must exclude cluster summaries")
    require(s3.get("non_english_policy", {}).get("status") == "out_of_scope_for_current_project_stage", "S3 must block non-English scope")
    expect_false(s3, ["promotion_policy", "reference_node_creation_allowed_in_s3"])
    expect_false(s3, ["promotion_policy", "reference_edge_creation_allowed_in_s3"])

    s4 = artifacts["s4"]
    strengths = {entry.get("source_strength"): entry.get("mapped_reference_edge_type") for entry in s4.get("source_strength_mapping", [])}
    require(strengths.get("hard") == "external_requires_candidate", "S4 hard mapping mismatch")
    require(strengths.get("soft") == "external_supports_candidate", "S4 soft mapping mismatch")
    expect_false(s4, ["restricted_text_policy", "dependency_reason_copied"])
    expect_false(s4, ["promotion_policy", "verified_edge_creation_allowed_in_s4"])
    expect_false(s4, ["promotion_policy", "dependency_graph_write_allowed"])

    s5 = artifacts["s5"]
    expect_false(s5, ["egp_supremacy_rule", "egp_row_modification_allowed"])
    expect_false(s5, ["egp_supremacy_rule", "grammar_node_creation_from_os_taxonomy_allowed"])
    expect_false(s5, ["egp_supremacy_rule", "grammar_edge_creation_from_os_taxonomy_allowed"])
    expect_false(s5, ["promotion_policy", "grammar_node_write_allowed_in_s5"])
    expect_false(s5, ["promotion_policy", "grammar_edge_write_allowed_in_s5"])

    s6 = artifacts["s6"]
    expect_false(s6, ["source_authority_policy", "raz_authority_modified"])
    expect_false(s6, ["source_authority_policy", "cambridge_authority_modified"])
    expect_false(s6, ["source_authority_policy", "cefr_authority_modified"])
    expect_false(s6, ["source_authority_policy", "reading_v1_runtime_write_allowed"])
    expect_false(s6, ["promotion_policy", "practice_bank_write_allowed_in_s6"])
    expect_false(s6, ["promotion_policy", "canonical_skill_node_write_allowed_in_s6"])

    s7 = artifacts["s7"]
    for key in [
        "evp_replacement_allowed",
        "ngsl_replacement_allowed",
        "cambridge_replacement_allowed",
        "raz_replacement_allowed",
        "formal_phonics_curriculum_authority_allowed",
    ]:
        expect_false(s7, ["authority_boundary_policy", key])
    expect_false(s7, ["reading_v1_connection_policy", "reading_v1_runtime_write_allowed"])
    expect_false(s7, ["reading_v1_connection_policy", "practice_bank_write_allowed"])
    expect_false(s7, ["reading_v1_connection_policy", "can_block_reading_v1_generation"])

    s8 = artifacts["s8"]
    expect_false(s8, ["restricted_text_policy", "external_evidence_copied"])
    expect_false(s8, ["restricted_text_policy", "external_assessment_prompt_copied"])
    expect_false(s8, ["restricted_text_policy", "external_cluster_summary_copied"])
    expect_false(s8, ["promotion_policy", "learner_state_write_allowed_in_s8"])
    expect_false(s8, ["promotion_policy", "mastery_runtime_write_allowed_in_s8"])
    expect_false(s8, ["promotion_policy", "question_bank_write_allowed_in_s8"])

    s9 = artifacts["s9"]
    expect_false(s9, ["scoring_policy", "runtime_weight_allowed"])
    expect_false(s9, ["scoring_policy", "can_singlehandedly_select_next_node"])
    expect_false(s9, ["scoring_policy", "can_singlehandedly_block_next_node"])
    expect_true(s9, ["primary_signal_supremacy_policy", "planner_must_work_without_os_taxonomy"])

    s10 = artifacts["s10"]
    statuses = {entry.get("skill_system"): entry.get("integration_status") for entry in s10.get("four_skill_readiness", [])}
    for skill in ["Reading", "Writing", "Listening", "Speaking"]:
        require(skill in statuses, f"S10 missing four-skill status: {skill}")
    for key in ["canonical_authority_allowed", "runtime_integration_allowed_in_s10", "learner_facing_output_allowed_in_s10", "restricted_text_copy_allowed"]:
        expect_false(s10, ["global_four_skill_policy", key])

    s11 = artifacts["s11"]
    expect_false(s11, ["copy_policy", "cluster_summary_copy_allowed"])
    expect_false(s11, ["copy_policy", "topic_description_copy_allowed"])
    expect_false(s11, ["runtime_policy", "dashboard_runtime_write_allowed_in_s11"])
    expect_false(s11, ["runtime_policy", "learner_state_write_allowed_in_s11"])
    expect_false(s11, ["runtime_policy", "final_parent_copy_generation_allowed_in_s11"])


def main():
    artifacts = {key: load_json(path) for key, path in REQUIRED_JSON_ARTIFACTS.items()}
    validate_all(artifacts)
    print("OS Taxonomy full reference integration validation: PASS")


if __name__ == "__main__":
    try:
        main()
    except ValidationError as exc:
        print(f"FAIL: {exc}")
        sys.exit(1)
