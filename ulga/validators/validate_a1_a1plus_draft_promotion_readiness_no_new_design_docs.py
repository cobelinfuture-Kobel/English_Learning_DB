import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
DRAFTS_PATH = BASE / "ulga" / "learning_units" / "draft" / "a1_a1plus_clear_lane_learning_unit_draft_artifacts.json"
COVERAGE_SUMMARY_PATH = BASE / "ulga" / "reports" / "a1_a1plus_coverage_recheck_no_new_design_docs_summary.json"
TASK_ID = "R7-M104E16D_A1A1PlusDraftPromotionReadinessValidator_NoNewDesignDocs"
EXPECTED_ARTIFACT_COUNT = 19
EXPECTED_PATCHED_FIELD_COUNT = 48
EXPECTED_DRAFT_MISSING_ROWS = 40
EXPECTED_THEORETICAL_COVERAGE_PERCENT = 52.2936


def fail(message):
    print("FAIL: " + message)
    return False


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def walk(value):
    if isinstance(value, dict):
        for child in value.values():
            yield from walk(child)
        yield value
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)
        yield value
    else:
        yield value


def has_placeholder(value):
    for node in walk(value):
        if isinstance(node, dict) and node.get("status") == "draft_placeholder":
            return True
        if isinstance(node, str) and (
            "DRAFT_EXAMPLE_REQUIRES_OPERATOR_REVIEW" in node
            or "DRAFT_COMPONENT_NODE_REQUIRES_OPERATOR_REVIEW" in node
            or "DRAFT_SLOT_SEQUENCE_REQUIRES_OPERATOR_REVIEW" in node
            or "draft_placeholder" in node
        ):
            return True
    return False


def evidence_ok(value):
    found = False
    for node in walk(value):
        if isinstance(node, dict) and "evidence" in node:
            evidence = node.get("evidence", {})
            if evidence.get("policy") != "BALANCED_SOURCE_GROUNDED":
                return False
            if not evidence.get("primary"):
                return False
            found = True
    return found


def validate_artifact(artifact):
    unit = artifact.get("draft_learning_unit", {})
    cluster = artifact.get("source_cluster", {})
    cluster_id = cluster.get("cluster_id")
    patch = artifact.get("field_completion_patch", {})
    if artifact.get("artifact_status") != "DRAFT_NOT_CANONICAL":
        return fail("artifact must remain DRAFT_NOT_CANONICAL")
    if unit.get("status") != "draft":
        return fail("unit must remain draft")
    if has_placeholder(unit):
        return fail(f"placeholder remains: {artifact.get('artifact_id')}")
    if patch.get("patch_status") != "PATCHED_DRAFT_FIELDS_NOT_CANONICAL":
        return fail("artifact patch status mismatch")
    if patch.get("coverage_credit_now") != 0:
        return fail("coverage_credit_now must remain 0 before canonical promotion")
    if patch.get("canonical_grammar_write_allowed") is not False or patch.get("canonical_pattern_write_allowed") is not False:
        return fail("canonical write must remain blocked")
    if cluster_id not in unit.get("egp_cluster_refs", []):
        return fail("cluster_id missing from egp_cluster_refs")
    if not unit.get("source_refs"):
        return fail("source_refs missing")
    if not evidence_ok(unit):
        return fail(f"source evidence missing or invalid: {artifact.get('artifact_id')}")
    return True


def validate():
    print("Validating A1/A1+ draft promotion readiness no-new-design-docs...")
    drafts = load(DRAFTS_PATH)
    coverage = load(COVERAGE_SUMMARY_PATH)
    artifacts = drafts.get("draft_artifacts", [])
    if len(artifacts) != EXPECTED_ARTIFACT_COUNT:
        return fail("draft artifact count mismatch")
    for artifact in artifacts:
        ok = validate_artifact(artifact)
        if ok is not True:
            return False
    metadata = drafts.get("field_completion_patch_metadata", {})
    if metadata.get("patched_field_count") != EXPECTED_PATCHED_FIELD_COUNT:
        return fail("patched_field_count mismatch")
    for key in ["new_design_docs_created", "new_planning_docs_created", "canonical_grammar_write_allowed", "canonical_pattern_write_allowed", "a2_a2plus_progression_allowed"]:
        if metadata.get(key) is not False:
            return fail(f"metadata {key} must be false")
    if coverage.get("validation_status") != "PASS":
        return fail("coverage recheck summary must be PASS")
    if coverage.get("canonical_covered_rows") != 17 or coverage.get("canonical_missing_rows") != 92:
        return fail("canonical coverage baseline mismatch")
    if coverage.get("draft_only_missing_row_count") != EXPECTED_DRAFT_MISSING_ROWS:
        return fail("draft_only_missing_row_count mismatch")
    if coverage.get("patched_field_count") != EXPECTED_PATCHED_FIELD_COUNT:
        return fail("coverage patched_field_count mismatch")
    if coverage.get("draft_only_coverage_credit_now") != 0:
        return fail("draft coverage credit must remain 0")
    if coverage.get("theoretical_coverage_percent_after_clear_lane_promotion") != EXPECTED_THEORETICAL_COVERAGE_PERCENT:
        return fail("theoretical coverage percent mismatch")
    for key in ["new_design_docs_created", "canonical_grammar_write_allowed", "canonical_pattern_write_allowed", "a2_a2plus_progression_allowed"]:
        if coverage.get(key) is not False:
            return fail(f"coverage {key} must be false")
    print("A1/A1+ draft promotion readiness validation: PASS")
    print("Draft artifacts ready for promotion review:", EXPECTED_ARTIFACT_COUNT)
    print("Patched fields:", EXPECTED_PATCHED_FIELD_COUNT)
    print("Canonical coverage remains: 17 / 109 (15.5963%)")
    print("Theoretical after promotion:", f"{EXPECTED_THEORETICAL_COVERAGE_PERCENT}%")
    print("Canonical write allowed now: False")
    return True


if __name__ == "__main__":
    try:
        ok = validate()
    except Exception as exc:
        ok = fail(str(exc))
    if not ok:
        sys.exit(1)
