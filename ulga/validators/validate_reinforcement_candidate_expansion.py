import json
import sys
from collections import Counter
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

EXPANSION_PATH = BASE_DIR / "ulga" / "graph" / "reinforcement_candidate_expansion.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "reinforcement_candidate_expansion_summary.json"
LEARNING_OPPORTUNITIES_PATH = BASE_DIR / "ulga" / "graph" / "learning_opportunities.json"
LEARNER_EXPOSURE_EVIDENCE_PATH = BASE_DIR / "ulga" / "graph" / "learner_exposure_evidence.json"
DEPENDENCY_READINESS_RESOLUTION_PATH = BASE_DIR / "ulga" / "graph" / "dependency_readiness_resolution.json"
LEARNER_STATE_PATH = BASE_DIR / "ulga" / "learner_state" / "learner_state.json"

SOURCE = "ULGA_S10J_REINFORCEMENT_CANDIDATE_EXPANSION"
VALID_SOURCES = {"direct_review", "dependency_parent", "theme_revisit", "exposure_evidence"}
VALID_DEPENDENCY_STATUSES = {"ready", "blocked", "unknown"}
VALID_INELIGIBLE_REASONS = {
    None,
    "dependency_blocked",
    "dependency_unknown",
    "reading_missing",
    "no_prior_exposure",
    "level_blocked",
}
TARGET_REF_KEYS = {"vocabulary", "grammar", "pattern", "theme", "chunk"}


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


def expected_ineligible_reason(candidate):
    if candidate["dependency_status"] == "blocked":
        return "dependency_blocked"
    if candidate["dependency_status"] == "unknown":
        return "dependency_unknown"
    if candidate["reading_ready"] is not True:
        return "reading_missing"
    if candidate["prior_exposure"] is not True:
        return "no_prior_exposure"
    if candidate.get("level_safe") is not True:
        return "level_blocked"
    return None


def validate_candidate(candidate, index, opportunity_ids, learner_ids, exposure_evidence_ids, dependency_status_by_opportunity):
    required = {
        "candidate_id",
        "opportunity_id",
        "candidate_source",
        "learner_id",
        "target_refs",
        "evidence_refs",
        "evidence",
        "planner_eligible",
        "ineligible_reason",
        "dependency_status",
        "reading_ready",
        "prior_exposure",
        "level_safe",
        "confidence",
        "warnings",
        "source",
    }
    missing = required - set(candidate)
    if missing:
        return fail(f"candidates[{index}] missing required fields: {sorted(missing)}")
    candidate_id = candidate["candidate_id"]
    if candidate["opportunity_id"] not in opportunity_ids:
        return fail(f"{candidate_id} opportunity does not exist: {candidate['opportunity_id']}")
    if candidate["candidate_source"] not in VALID_SOURCES:
        return fail(f"{candidate_id} invalid candidate_source")
    if candidate["candidate_source"] == "exposure_evidence":
        if candidate["learner_id"] not in learner_ids:
            return fail(f"{candidate_id} learner_id does not exist")
        evidence_refs = candidate["evidence_refs"]
        if not isinstance(evidence_refs, list) or not evidence_refs:
            return fail(f"{candidate_id} exposure_evidence candidate must include evidence_refs")
        for evidence_ref in evidence_refs:
            if evidence_ref not in exposure_evidence_ids:
                return fail(f"{candidate_id} evidence_ref does not exist: {evidence_ref}")
    elif not isinstance(candidate["evidence_refs"], list):
        return fail(f"{candidate_id} evidence_refs must be a list")
    if not isinstance(candidate["planner_eligible"], bool):
        return fail(f"{candidate_id} planner_eligible must be boolean")
    if candidate["ineligible_reason"] not in VALID_INELIGIBLE_REASONS:
        return fail(f"{candidate_id} invalid ineligible_reason")
    if candidate["dependency_status"] not in VALID_DEPENDENCY_STATUSES:
        return fail(f"{candidate_id} dependency_status invalid")
    expected_dependency_status = dependency_status_by_opportunity.get(candidate["opportunity_id"])
    if expected_dependency_status and candidate["dependency_status"] != expected_dependency_status:
        return fail(f"{candidate_id} dependency overlay was not applied")
    if not isinstance(candidate["reading_ready"], bool):
        return fail(f"{candidate_id} reading_ready must be boolean")
    if not isinstance(candidate["prior_exposure"], bool):
        return fail(f"{candidate_id} prior_exposure must be boolean")
    if not isinstance(candidate["level_safe"], bool):
        return fail(f"{candidate_id} level_safe must be boolean")
    confidence = candidate["confidence"]
    if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
        return fail(f"{candidate_id} confidence must be between 0 and 1")
    if not isinstance(candidate["warnings"], list):
        return fail(f"{candidate_id} warnings must be a list")
    if candidate["source"] != SOURCE:
        return fail(f"{candidate_id} source must be {SOURCE}")
    target_refs = candidate["target_refs"]
    if not isinstance(target_refs, dict) or set(target_refs) != TARGET_REF_KEYS:
        return fail(f"{candidate_id} target_refs keys invalid")
    if not any(target_refs[key] for key in TARGET_REF_KEYS):
        return fail(f"{candidate_id} target_refs must contain at least one ref")
    for key, refs in target_refs.items():
        if not isinstance(refs, list):
            return fail(f"{candidate_id} target_refs.{key} must be a list")
    if not isinstance(candidate["evidence"], dict):
        return fail(f"{candidate_id} evidence must be an object")
    if candidate["planner_eligible"]:
        if candidate["dependency_status"] != "ready":
            return fail(f"{candidate_id} planner_eligible candidate must be dependency ready")
        if candidate["reading_ready"] is not True:
            return fail(f"{candidate_id} planner_eligible candidate must be reading ready")
        if candidate["prior_exposure"] is not True:
            return fail(f"{candidate_id} planner_eligible candidate must have prior exposure")
        if candidate["level_safe"] is not True:
            return fail(f"{candidate_id} planner_eligible candidate must be level safe")
        if candidate["ineligible_reason"] is not None:
            return fail(f"{candidate_id} planner_eligible candidate must not have ineligible_reason")
    elif candidate["ineligible_reason"] != expected_ineligible_reason(candidate):
        return fail(f"{candidate_id} ineligible_reason inconsistent")
    return True


def validate():
    print("Validating ULGA Reinforcement Candidate Expansion...")
    for path in [
        EXPANSION_PATH,
        SUMMARY_PATH,
        LEARNING_OPPORTUNITIES_PATH,
        LEARNER_EXPOSURE_EVIDENCE_PATH,
        DEPENDENCY_READINESS_RESOLUTION_PATH,
        LEARNER_STATE_PATH,
    ]:
        if not path.exists():
            return fail(f"required file does not exist: {path}")

    payload = read_json(EXPANSION_PATH)
    summary = read_json(SUMMARY_PATH)
    opportunities = read_json(LEARNING_OPPORTUNITIES_PATH)
    exposure_payload = read_json(LEARNER_EXPOSURE_EVIDENCE_PATH)
    resolution_payload = read_json(DEPENDENCY_READINESS_RESOLUTION_PATH)
    learner_state = read_json(LEARNER_STATE_PATH)
    if (
        payload is None
        or summary is None
        or opportunities is None
        or exposure_payload is None
        or resolution_payload is None
        or learner_state is None
    ):
        return False
    if not isinstance(payload, dict):
        return fail("reinforcement_candidate_expansion.json must contain an object")
    if not isinstance(summary, dict):
        return fail("reinforcement_candidate_expansion_summary.json must contain an object")
    if not isinstance(opportunities, list):
        return fail("learning_opportunities.json must contain a list")

    metadata = payload.get("metadata")
    candidates = payload.get("candidates")
    if not isinstance(metadata, dict):
        return fail("metadata must be an object")
    if metadata.get("source") != SOURCE:
        return fail(f"metadata source must be {SOURCE}")
    if not metadata.get("generated_at"):
        return fail("metadata generated_at is required")
    if not isinstance(candidates, list):
        return fail("candidates must be a list")

    opportunity_ids = {item.get("opportunity_id") for item in opportunities if isinstance(item, dict)}
    opportunity_ids.discard(None)
    learner_ids = {
        item.get("learner_id")
        for item in learner_state.get("learner_state_records", [])
        if isinstance(item, dict) and item.get("learner_id")
    }
    exposure_evidence_ids = {
        item.get("evidence_id")
        for item in exposure_payload.get("evidence", [])
        if isinstance(item, dict) and item.get("evidence_id")
    }
    dependency_status_by_opportunity = {
        item.get("opportunity_id"): item.get("resolved_dependency_status")
        for item in resolution_payload.get("resolutions", [])
        if isinstance(item, dict)
        and item.get("opportunity_id")
        and item.get("resolved_dependency_status") in VALID_DEPENDENCY_STATUSES
    }
    seen_candidate_ids = set()
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            return fail(f"candidates[{index}] must be an object")
        candidate_id = candidate.get("candidate_id")
        if not candidate_id:
            return fail(f"candidates[{index}] missing candidate_id")
        if candidate_id in seen_candidate_ids:
            return fail(f"duplicate candidate_id: {candidate_id}")
        seen_candidate_ids.add(candidate_id)
        if not validate_candidate(
            candidate,
            index,
            opportunity_ids,
            learner_ids,
            exposure_evidence_ids,
            dependency_status_by_opportunity,
        ):
            return False

    source_distribution = Counter(candidate["candidate_source"] for candidate in candidates)
    ineligible_reason_distribution = Counter(
        candidate["ineligible_reason"] for candidate in candidates if candidate["ineligible_reason"]
    )
    if summary.get("status") not in {"PASS", "PASS_WITH_WARNINGS", "BLOCKED"}:
        return fail("summary status invalid")
    if summary.get("candidate_count") != len(candidates):
        return fail("summary candidate_count mismatch")
    if summary.get("planner_eligible_count") != sum(1 for item in candidates if item["planner_eligible"]):
        return fail("summary planner_eligible_count mismatch")
    if summary.get("source_distribution") != dict(sorted(source_distribution.items())):
        return fail("summary source_distribution mismatch")
    if summary.get("ineligible_reason_distribution") != dict(sorted(ineligible_reason_distribution.items())):
        return fail("summary ineligible_reason_distribution mismatch")
    exposure_evidence_used_count = sum(
        len(item.get("evidence_refs", []))
        for item in candidates
        if item["candidate_source"] == "exposure_evidence"
    )
    if summary.get("exposure_evidence_used_count") != exposure_evidence_used_count:
        return fail("summary exposure_evidence_used_count mismatch")
    if summary.get("dependency_ready_count") != sum(1 for item in candidates if item["dependency_status"] == "ready"):
        return fail("summary dependency_ready_count mismatch")
    if summary.get("reading_ready_count") != sum(1 for item in candidates if item["reading_ready"]):
        return fail("summary reading_ready_count mismatch")
    if not isinstance(summary.get("warnings"), list):
        return fail("summary warnings must be a list")

    print("Reinforcement Candidate Expansion validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
