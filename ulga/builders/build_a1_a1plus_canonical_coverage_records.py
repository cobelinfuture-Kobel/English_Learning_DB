import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]

DRAFTS_PATH = BASE / "ulga" / "learning_units" / "draft" / "a1_a1plus_clear_lane_learning_unit_draft_artifacts.json"
OUT_PATH = BASE / "ulga" / "graph" / "a1_a1plus_canonical_coverage_records.json"
SUMMARY_PATH = BASE / "ulga" / "reports" / "a1_a1plus_canonical_coverage_records_summary.json"

TASK_ID = "R7-M104E17_A1A1PlusPatchedDraftCanonicalCoverageRecords_NoNewDesignDocs"

EGP_A1_TOTAL_ROWS = 109
BASELINE_CANONICAL_COVERED_ROWS = 17
EXPECTED_DRAFT_ARTIFACT_COUNT = 19
EXPECTED_PATCHED_FIELD_COUNT = 48
EXPECTED_PROMOTED_ROW_COUNT = 40


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def pct(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6)


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        yield value
        for child in value:
            yield from walk(child)
    else:
        yield value


def has_forbidden_placeholder(value) -> bool:
    for node in walk(value):
        if isinstance(node, dict) and node.get("status") == "draft_placeholder":
            return True
        if isinstance(node, str):
            if "DRAFT_EXAMPLE_REQUIRES_OPERATOR_REVIEW" in node:
                return True
            if "DRAFT_COMPONENT_NODE_REQUIRES_OPERATOR_REVIEW" in node:
                return True
            if "DRAFT_SLOT_SEQUENCE_REQUIRES_OPERATOR_REVIEW" in node:
                return True
            if "draft_placeholder" in node:
                return True
    return False


def collect_evidence(value) -> dict:
    evidence_objects = []
    primary_refs = []

    for node in walk(value):
        if isinstance(node, dict):
            evidence = node.get("evidence")
            if isinstance(evidence, dict):
                evidence_objects.append(evidence)
                primary_refs.extend(evidence.get("primary", []))

    return {
        "evidence_policy": "BALANCED_SOURCE_GROUNDED",
        "evidence_object_count": len(evidence_objects),
        "primary_refs": sorted(set(primary_refs)),
        "support_refs": ["EVP_SUPPORT", "RAZ_SUPPORT"],
        "context_refs": ["CAMBRIDGE_EXAM_CONTEXT_ONLY"],
    }


def validate_source_artifact(artifact: dict) -> None:
    artifact_id = artifact.get("artifact_id")
    unit = artifact.get("draft_learning_unit", {})
    patch = artifact.get("field_completion_patch", {})

    if artifact.get("artifact_status") != "DRAFT_NOT_CANONICAL":
        raise ValueError(f"{artifact_id}: artifact_status must remain DRAFT_NOT_CANONICAL")

    if unit.get("status") != "draft":
        raise ValueError(f"{artifact_id}: draft unit status must remain draft")

    if patch.get("patch_status") != "PATCHED_DRAFT_FIELDS_NOT_CANONICAL":
        raise ValueError(f"{artifact_id}: field patch status is missing or invalid")

    if patch.get("coverage_credit_now") != 0:
        raise ValueError(f"{artifact_id}: draft coverage_credit_now must be 0 before canonical coverage record creation")

    if patch.get("canonical_grammar_write_allowed") is not False:
        raise ValueError(f"{artifact_id}: canonical grammar write must remain false at draft patch layer")

    if patch.get("canonical_pattern_write_allowed") is not False:
        raise ValueError(f"{artifact_id}: canonical pattern write must remain false at draft patch layer")

    if has_forbidden_placeholder(unit):
        raise ValueError(f"{artifact_id}: forbidden placeholder remains")

    evidence = collect_evidence(unit)
    if evidence["evidence_policy"] != "BALANCED_SOURCE_GROUNDED":
        raise ValueError(f"{artifact_id}: evidence policy mismatch")

    if not evidence["primary_refs"]:
        raise ValueError(f"{artifact_id}: primary evidence refs missing")


def build_coverage_record(artifact: dict) -> dict:
    cluster = artifact["source_cluster"]
    unit = artifact["draft_learning_unit"]
    patch = artifact["field_completion_patch"]

    cluster_id = cluster["cluster_id"]
    covered_rows = int(cluster.get("missing_row_count", 0))

    return {
        "coverage_record_id": f"a1_a1plus_canonical_coverage:{cluster_id}",
        "coverage_record_status": "CANONICAL_COVERAGE_ACCEPTED",
        "coverage_source": "PATCHED_DRAFT_ARTIFACT",
        "coverage_granularity": "cluster_missing_row_count",
        "row_id_materialization_status": "ROW_IDS_NOT_MATERIALIZED_CLUSTER_COUNT_ACCEPTED",
        "source_draft_artifact_id": artifact["artifact_id"],
        "learning_unit_id": unit["learning_unit_id"],
        "learning_unit_type": unit["learning_unit_type"],
        "cluster_id": cluster_id,
        "cluster_key": cluster["cluster_key"],
        "source_refs": unit.get("source_refs", []),
        "egp_cluster_refs": unit.get("egp_cluster_refs", []),
        "cluster_total_row_count": int(cluster.get("row_count", 0)),
        "canonical_covered_row_count": covered_rows,
        "patched_field_count": int(patch.get("patched_field_count", 0)),
        "evidence_trace": collect_evidence(unit),
        "operator_review_required_for_row_id_materialization": True,
    }


def main() -> None:
    draft_data = load_json(DRAFTS_PATH)
    artifacts = draft_data.get("draft_artifacts", [])

    if len(artifacts) != EXPECTED_DRAFT_ARTIFACT_COUNT:
        raise ValueError(f"Expected {EXPECTED_DRAFT_ARTIFACT_COUNT} draft artifacts, got {len(artifacts)}")

    records = []
    for artifact in artifacts:
        validate_source_artifact(artifact)
        records.append(build_coverage_record(artifact))

    promoted_rows = sum(record["canonical_covered_row_count"] for record in records)
    patched_fields = sum(record["patched_field_count"] for record in records)

    if promoted_rows != EXPECTED_PROMOTED_ROW_COUNT:
        raise ValueError(f"Expected {EXPECTED_PROMOTED_ROW_COUNT} promoted rows, got {promoted_rows}")

    if patched_fields != EXPECTED_PATCHED_FIELD_COUNT:
        raise ValueError(f"Expected {EXPECTED_PATCHED_FIELD_COUNT} patched fields, got {patched_fields}")

    canonical_covered_rows = BASELINE_CANONICAL_COVERED_ROWS + promoted_rows
    canonical_missing_rows = EGP_A1_TOTAL_ROWS - canonical_covered_rows
    coverage_ratio = pct(canonical_covered_rows, EGP_A1_TOTAL_ROWS)

    output = {
        "task_id": TASK_ID,
        "artifact_id": "a1_a1plus_canonical_coverage_records",
        "validation_status": "PASS",
        "coverage_policy": "PATCHED_DRAFT_ARTIFACTS_TO_CANONICAL_COVERAGE_RECORDS",
        "egp_a1_total_rows": EGP_A1_TOTAL_ROWS,
        "baseline_canonical_covered_rows": BASELINE_CANONICAL_COVERED_ROWS,
        "promoted_covered_rows_from_patched_drafts": promoted_rows,
        "canonical_covered_rows": canonical_covered_rows,
        "canonical_missing_rows": canonical_missing_rows,
        "canonical_coverage_ratio": coverage_ratio,
        "canonical_coverage_percent": round(coverage_ratio * 100, 4),
        "coverage_record_count": len(records),
        "patched_field_count": patched_fields,
        "coverage_records": records,
        "new_design_docs_created": False,
        "new_planning_docs_created": False,
        "new_review_docs_created": False,
        "new_sync_docs_created": False,
        "a2_a2plus_progression_allowed": False,
        "row_id_materialization_status": "ROW_IDS_NOT_MATERIALIZED_CLUSTER_COUNT_ACCEPTED",
        "next_short_step": "R7-M104E18_A1A1PlusRemainingMissingRowsDirectPatch_NoNewDesignDocs",
        "stop_reason": "NONE",
    }

    summary = dict(output)
    summary.pop("coverage_records")

    write_json(OUT_PATH, output)
    write_json(SUMMARY_PATH, summary)

    print("A1/A1+ canonical coverage records build: PASS")
    print(f"Canonical coverage: {canonical_covered_rows} / {EGP_A1_TOTAL_ROWS} ({summary['canonical_coverage_percent']}%)")
    print(f"Promoted rows from patched drafts: {promoted_rows}")
    print(f"Canonical missing rows: {canonical_missing_rows}")
    print(f"Coverage records: {len(records)}")
    print(f"Patched fields: {patched_fields}")


if __name__ == "__main__":
    main()