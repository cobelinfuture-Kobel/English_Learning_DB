import json
import sys
from collections import Counter
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

RESOLUTION_PATH = BASE_DIR / "ulga" / "graph" / "dependency_readiness_resolution.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "dependency_readiness_resolution_summary.json"
LEARNING_OPPORTUNITIES_PATH = BASE_DIR / "ulga" / "graph" / "learning_opportunities.json"

SOURCE = "ULGA_S8Y_DEPENDENCY_READINESS_RESOLUTION"
VALID_STATUSES = {"ready", "blocked", "unknown"}
VALID_RESOLUTION_TYPES = {
    "explicit_requires_satisfied",
    "explicit_requires_level_blocked",
    "missing_required_ref",
    "no_requires_ready",
    "insufficient_evidence_unknown",
    "authority_reference_mismatch",
}
REQUIRED_EVIDENCE_FIELDS = {
    "has_explicit_requires",
    "requires_count",
    "all_required_refs_exist",
    "required_refs",
    "missing_required_refs",
    "opportunity_level",
    "max_required_level",
    "level_ceiling_passed",
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


def validate_resolution(record, index, opportunity_ids, unknown_opportunity_ids):
    required_fields = {
        "resolution_id",
        "opportunity_id",
        "previous_dependency_status",
        "resolved_dependency_status",
        "resolution_type",
        "evidence",
        "confidence",
        "planner_eligible_after_resolution",
        "warnings",
        "source",
    }
    missing = required_fields - set(record)
    if missing:
        return fail(f"resolutions[{index}] missing required fields: {sorted(missing)}")

    resolution_id = record["resolution_id"]
    opportunity_id = record["opportunity_id"]
    if opportunity_id not in opportunity_ids:
        return fail(f"{resolution_id} opportunity_id does not exist: {opportunity_id}")
    if opportunity_id not in unknown_opportunity_ids:
        return fail(f"{resolution_id} target opportunity was not dependency unknown: {opportunity_id}")
    if record["previous_dependency_status"] != "unknown":
        return fail(f"{resolution_id} previous_dependency_status must be unknown")
    if record["resolved_dependency_status"] not in VALID_STATUSES:
        return fail(f"{resolution_id} invalid resolved_dependency_status")
    if record["resolution_type"] not in VALID_RESOLUTION_TYPES:
        return fail(f"{resolution_id} invalid resolution_type")
    if record["source"] != SOURCE:
        return fail(f"{resolution_id} source must be {SOURCE}")
    confidence = record["confidence"]
    if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
        return fail(f"{resolution_id} confidence must be between 0 and 1")
    if not isinstance(record["planner_eligible_after_resolution"], bool):
        return fail(f"{resolution_id} planner_eligible_after_resolution must be boolean")
    if record["planner_eligible_after_resolution"] != (record["resolved_dependency_status"] == "ready"):
        return fail(f"{resolution_id} planner eligibility inconsistent with resolved status")
    if not isinstance(record["warnings"], list):
        return fail(f"{resolution_id} warnings must be a list")

    evidence = record["evidence"]
    if not isinstance(evidence, dict):
        return fail(f"{resolution_id} evidence must be an object")
    if REQUIRED_EVIDENCE_FIELDS - set(evidence):
        return fail(f"{resolution_id} evidence missing fields: {sorted(REQUIRED_EVIDENCE_FIELDS - set(evidence))}")
    if not isinstance(evidence["has_explicit_requires"], bool):
        return fail(f"{resolution_id} evidence.has_explicit_requires must be boolean")
    if not isinstance(evidence["requires_count"], int) or evidence["requires_count"] < 0:
        return fail(f"{resolution_id} evidence.requires_count must be a non-negative integer")
    if not isinstance(evidence["all_required_refs_exist"], bool):
        return fail(f"{resolution_id} evidence.all_required_refs_exist must be boolean")
    if not isinstance(evidence["required_refs"], list):
        return fail(f"{resolution_id} evidence.required_refs must be a list")
    if not isinstance(evidence["missing_required_refs"], list):
        return fail(f"{resolution_id} evidence.missing_required_refs must be a list")
    if evidence["requires_count"] != len(evidence["required_refs"]):
        return fail(f"{resolution_id} evidence requires_count mismatch")
    if evidence["has_explicit_requires"] != bool(evidence["required_refs"]):
        return fail(f"{resolution_id} evidence has_explicit_requires mismatch")
    if evidence["all_required_refs_exist"] != (not evidence["missing_required_refs"]):
        return fail(f"{resolution_id} evidence all_required_refs_exist mismatch")

    if record["resolution_type"] == "missing_required_ref" and record["resolved_dependency_status"] == "ready":
        return fail(f"{resolution_id} missing_required_ref cannot be marked ready")
    if evidence["missing_required_refs"] and record["resolved_dependency_status"] == "ready":
        return fail(f"{resolution_id} missing required refs cannot be marked ready")
    if record["resolution_type"] == "explicit_requires_level_blocked":
        if record["resolved_dependency_status"] != "blocked":
            return fail(f"{resolution_id} level-blocked resolution must be blocked")
        if record["planner_eligible_after_resolution"] is True:
            return fail(f"{resolution_id} level-blocked resolution cannot be planner eligible")
    if record["resolved_dependency_status"] == "ready" and evidence["missing_required_refs"]:
        return fail(f"{resolution_id} ready resolution contains missing refs")
    return True


def validate():
    print("Validating ULGA Dependency Readiness Resolution...")
    for path in [RESOLUTION_PATH, SUMMARY_PATH, LEARNING_OPPORTUNITIES_PATH]:
        if not path.exists():
            return fail(f"required file does not exist: {path}")

    payload = read_json(RESOLUTION_PATH)
    summary = read_json(SUMMARY_PATH)
    opportunities = read_json(LEARNING_OPPORTUNITIES_PATH)
    if payload is None or summary is None or opportunities is None:
        return False
    if not isinstance(payload, dict):
        return fail("dependency_readiness_resolution.json must contain an object")
    if not isinstance(summary, dict):
        return fail("dependency_readiness_resolution_summary.json must contain an object")
    if not isinstance(opportunities, list):
        return fail("learning_opportunities.json must contain a list")

    metadata = payload.get("metadata")
    resolutions = payload.get("resolutions")
    if not isinstance(metadata, dict):
        return fail("metadata must be an object")
    if metadata.get("source") != SOURCE:
        return fail(f"metadata source must be {SOURCE}")
    if not metadata.get("generated_at"):
        return fail("metadata generated_at is required")
    if not isinstance(resolutions, list):
        return fail("resolutions must be a list")

    opportunity_ids = {item.get("opportunity_id") for item in opportunities if isinstance(item, dict)}
    opportunity_ids.discard(None)
    unknown_opportunity_ids = {
        item.get("opportunity_id")
        for item in opportunities
        if isinstance(item, dict) and item.get("dependency", {}).get("status") == "unknown"
    }
    unknown_opportunity_ids.discard(None)

    seen_resolution_ids = set()
    seen_opportunity_ids = set()
    for index, record in enumerate(resolutions):
        if not isinstance(record, dict):
            return fail(f"resolutions[{index}] must be an object")
        resolution_id = record.get("resolution_id")
        if not resolution_id:
            return fail(f"resolutions[{index}] missing resolution_id")
        if resolution_id in seen_resolution_ids:
            return fail(f"duplicate resolution_id: {resolution_id}")
        seen_resolution_ids.add(resolution_id)
        opportunity_id = record.get("opportunity_id")
        if opportunity_id in seen_opportunity_ids:
            return fail(f"duplicate opportunity resolution: {opportunity_id}")
        seen_opportunity_ids.add(opportunity_id)
        if not validate_resolution(record, index, opportunity_ids, unknown_opportunity_ids):
            return False

    status_counts = Counter(record["resolved_dependency_status"] for record in resolutions)
    type_counts = Counter(record["resolution_type"] for record in resolutions)
    if summary.get("status") not in {"PASS", "PASS_WITH_WARNINGS"}:
        return fail("summary status must be PASS or PASS_WITH_WARNINGS")
    if summary.get("total_unknown_inputs") != len(unknown_opportunity_ids):
        return fail("summary total_unknown_inputs mismatch")
    if summary.get("resolved_ready_count") != status_counts.get("ready", 0):
        return fail("summary resolved_ready_count mismatch")
    if summary.get("resolved_blocked_count") != status_counts.get("blocked", 0):
        return fail("summary resolved_blocked_count mismatch")
    if summary.get("still_unknown_count") != status_counts.get("unknown", 0):
        return fail("summary still_unknown_count mismatch")
    if summary.get("resolution_type_distribution") != dict(sorted(type_counts.items())):
        return fail("summary resolution_type_distribution mismatch")
    for key in [
        "reinforcement_positive_unknown_before",
        "reinforcement_positive_eligible_after",
    ]:
        if not isinstance(summary.get(key), int) or summary[key] < 0:
            return fail(f"summary {key} must be a non-negative integer")
    if summary["reinforcement_positive_eligible_after"] > summary["reinforcement_positive_unknown_before"]:
        return fail("summary reinforcement eligible after cannot exceed before count")
    if not isinstance(summary.get("missing_optional_inputs"), list):
        return fail("summary missing_optional_inputs must be a list")
    if not isinstance(summary.get("warnings"), list):
        return fail("summary warnings must be a list")

    print("Dependency Readiness Resolution validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
