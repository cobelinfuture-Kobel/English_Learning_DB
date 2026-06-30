import json
import sys
from collections import Counter
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

EVIDENCE_PATH = BASE_DIR / "ulga" / "graph" / "learner_exposure_evidence.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "learner_exposure_evidence_summary.json"
LEARNER_STATE_PATH = BASE_DIR / "ulga" / "learner_state" / "learner_state.json"
LEARNING_OPPORTUNITIES_PATH = BASE_DIR / "ulga" / "graph" / "learning_opportunities.json"
EXPOSURE_MAPPING_BRIDGE_PATH = BASE_DIR / "ulga" / "graph" / "exposure_mapping_bridge.json"

SOURCE = "ULGA_S9Y_LEARNER_EXPOSURE_EVIDENCE"
VALID_BANDS = {"weak", "medium", "strong"}
VALID_TARGET_TYPES = {"opportunity"}
VALID_SOURCES = {"vocabulary", "grammar", "theme", "direct_focus_node", "dependency_parent"}
VALID_MAPPING_TYPES = {
    "focus_node_overlap",
    "theme_overlap",
    "direct_focus_node_bridge",
    "grammar_bridge",
    "vocabulary_bridge",
    "theme_bridge",
    "dependency_parent_bridge",
}
VALID_DEPENDENCY_STATUSES = {"ready", "blocked", "unknown"}


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


def in_score_range(value):
    return isinstance(value, (int, float)) and 0 <= value <= 1


def validate_evidence_record(record, index, learner_ids, opportunity_ids, bridge_ids):
    required = {
        "evidence_id",
        "learner_id",
        "target_type",
        "target_id",
        "opportunity_exposure_score",
        "confidence_band",
        "prior_exposure",
        "evidence_sources",
        "source_node_id",
        "source_node_type",
        "mapping_type",
        "bridge_refs",
        "dependency_status",
        "warnings",
        "source",
    }
    missing = required - set(record)
    if missing:
        return fail(f"evidence[{index}] missing required fields: {sorted(missing)}")
    evidence_id = record["evidence_id"]
    if record["learner_id"] not in learner_ids:
        return fail(f"{evidence_id} learner does not exist: {record['learner_id']}")
    if record["target_type"] not in VALID_TARGET_TYPES:
        return fail(f"{evidence_id} target_type invalid")
    if record["target_id"] not in opportunity_ids:
        return fail(f"{evidence_id} opportunity does not exist: {record['target_id']}")
    score = record["opportunity_exposure_score"]
    if not in_score_range(score):
        return fail(f"{evidence_id} opportunity_exposure_score must be between 0 and 1")
    if record["confidence_band"] not in VALID_BANDS:
        return fail(f"{evidence_id} confidence_band invalid")
    if not isinstance(record["prior_exposure"], bool):
        return fail(f"{evidence_id} prior_exposure must be boolean")
    if record["prior_exposure"] != (score > 0):
        return fail(f"{evidence_id} prior_exposure must match positive score")
    sources = record["evidence_sources"]
    if not isinstance(sources, list) or not sources:
        return fail(f"{evidence_id} evidence_sources must be a non-empty list")
    for source in sources:
        if source not in VALID_SOURCES:
            return fail(f"{evidence_id} invalid evidence source: {source}")
    if not isinstance(record["source_node_type"], str) or not record["source_node_type"]:
        return fail(f"{evidence_id} source_node_type invalid")
    if record["mapping_type"] not in VALID_MAPPING_TYPES:
        return fail(f"{evidence_id} mapping_type invalid")
    bridge_refs = record["bridge_refs"]
    if not isinstance(bridge_refs, list):
        return fail(f"{evidence_id} bridge_refs must be a list")
    for bridge_ref in bridge_refs:
        if bridge_ref not in bridge_ids:
            return fail(f"{evidence_id} bridge_ref does not exist: {bridge_ref}")
    if record["source_node_type"] == "theme" and record["mapping_type"] not in {"theme_overlap", "theme_bridge"}:
        return fail(f"{evidence_id} theme source must use theme_overlap")
    if not bridge_refs and record["source_node_type"] != "theme" and record["mapping_type"] != "focus_node_overlap":
        return fail(f"{evidence_id} non-theme source must use focus_node_overlap")
    if record["dependency_status"] not in VALID_DEPENDENCY_STATUSES:
        return fail(f"{evidence_id} dependency_status invalid")
    if not isinstance(record["warnings"], list):
        return fail(f"{evidence_id} warnings must be a list")
    if record["source"] != SOURCE:
        return fail(f"{evidence_id} source must be {SOURCE}")
    return True


def validate():
    print("Validating ULGA Learner Exposure Evidence...")
    for path in [EVIDENCE_PATH, SUMMARY_PATH, LEARNER_STATE_PATH, LEARNING_OPPORTUNITIES_PATH]:
        if not path.exists():
            return fail(f"required file does not exist: {path}")

    payload = read_json(EVIDENCE_PATH)
    summary = read_json(SUMMARY_PATH)
    learner_state = read_json(LEARNER_STATE_PATH)
    opportunities = read_json(LEARNING_OPPORTUNITIES_PATH)
    bridge_payload = read_json(EXPOSURE_MAPPING_BRIDGE_PATH) if EXPOSURE_MAPPING_BRIDGE_PATH.exists() else {"bridges": []}
    if payload is None or summary is None or learner_state is None or opportunities is None:
        return False
    if not isinstance(payload, dict):
        return fail("learner_exposure_evidence.json must contain an object")
    if not isinstance(summary, dict):
        return fail("learner_exposure_evidence_summary.json must contain an object")
    if not isinstance(opportunities, list):
        return fail("learning_opportunities.json must contain a list")

    metadata = payload.get("metadata")
    evidence = payload.get("evidence")
    if not isinstance(metadata, dict):
        return fail("metadata must be an object")
    if metadata.get("source") != SOURCE:
        return fail(f"metadata source must be {SOURCE}")
    if not metadata.get("generated_at"):
        return fail("metadata generated_at is required")
    if not isinstance(evidence, list):
        return fail("evidence must be a list")

    learner_ids = {
        item.get("learner_id")
        for item in learner_state.get("learner_state_records", [])
        if isinstance(item, dict) and item.get("learner_id")
    }
    opportunity_ids = {item.get("opportunity_id") for item in opportunities if isinstance(item, dict)}
    opportunity_ids.discard(None)
    bridge_ids = {
        item.get("bridge_id")
        for item in bridge_payload.get("bridges", [])
        if isinstance(item, dict) and item.get("bridge_id")
    }

    seen_ids = set()
    seen_keys = set()
    for index, record in enumerate(evidence):
        if not isinstance(record, dict):
            return fail(f"evidence[{index}] must be an object")
        evidence_id = record.get("evidence_id")
        if not evidence_id:
            return fail(f"evidence[{index}] missing evidence_id")
        if evidence_id in seen_ids:
            return fail(f"duplicate evidence_id: {evidence_id}")
        seen_ids.add(evidence_id)
        key = (
            record.get("learner_id"),
            record.get("target_id"),
            record.get("source_node_id"),
            record.get("mapping_type"),
        )
        if key in seen_keys:
            return fail(f"duplicate evidence tuple: {key}")
        seen_keys.add(key)
        if not validate_evidence_record(record, index, learner_ids, opportunity_ids, bridge_ids):
            return False

    mapped_opportunity_ids = {item["target_id"] for item in evidence}
    band_counts = Counter(item["confidence_band"] for item in evidence)
    opportunity_count = len(opportunity_ids)
    expected_coverage_rate = round(len(mapped_opportunity_ids) / opportunity_count, 6) if opportunity_count else 0.0
    if summary.get("status") not in {"PASS", "PASS_WITH_WARNINGS", "BLOCKED"}:
        return fail("summary status invalid")
    if summary.get("evidence_count") != len(evidence):
        return fail("summary evidence_count mismatch")
    if summary.get("opportunity_mapping_count") != len(mapped_opportunity_ids):
        return fail("summary opportunity_mapping_count mismatch")
    if summary.get("weak_count") != band_counts.get("weak", 0):
        return fail("summary weak_count mismatch")
    if summary.get("medium_count") != band_counts.get("medium", 0):
        return fail("summary medium_count mismatch")
    if summary.get("strong_count") != band_counts.get("strong", 0):
        return fail("summary strong_count mismatch")
    if summary.get("coverage_rate") != expected_coverage_rate:
        return fail("summary coverage_rate mismatch")
    source_distribution = Counter(
        source
        for item in evidence
        for source in item.get("evidence_sources", [])
    )
    if summary.get("evidence_source_distribution") != dict(sorted(source_distribution.items())):
        return fail("summary evidence_source_distribution mismatch")
    bridge_ref_count = sum(len(item.get("bridge_refs", [])) for item in evidence)
    if summary.get("bridge_ref_count") != bridge_ref_count:
        return fail("summary bridge_ref_count mismatch")
    if not isinstance(summary.get("warnings"), list):
        return fail("summary warnings must be a list")

    print("Learner Exposure Evidence validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
