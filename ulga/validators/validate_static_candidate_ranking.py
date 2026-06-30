import json
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

RANKING_PATH = BASE_DIR / "ulga" / "graph" / "static_candidate_ranking.json"

FORBIDDEN_ADAPTIVE_KEYWORDS = {
    "learner_state",
    "mastery",
    "mastery_gap",
    "retention",
    "forgetting_curve",
    "assessment",
    "attempt_history",
    "review_queue",
    "personalized_exposure",
    "student_id",
    "learner_id",
    "james",
    "cyndi",
}
REQUIRED_TOP_LEVEL_FIELDS = {
    "schema_version",
    "ranking_mode",
    "adaptive_enabled",
    "generated_at",
    "source",
    "weights",
    "candidates",
    "blocked_candidates",
}
REQUIRED_CANDIDATE_FIELDS = {
    "rank",
    "candidate_id",
    "candidate_type",
    "label",
    "level",
    "static_score",
    "score_breakdown",
    "explain",
    "blocked",
    "block_reasons",
}
WEIGHTS = {
    "dependency_readiness_score": 0.30,
    "frequency_score": 0.20,
    "theme_spiral_score": 0.20,
    "reinforcement_score": 0.20,
    "authority_confidence_score": 0.10,
}
LEVEL_ORDER = {"A1": 0, "A2": 1, "B1": 2, "B2": 3, "C1": 4, "C2": 5}
CANDIDATE_TYPE_ORDER = {
    "pattern_candidate": 0,
    "vocabulary_candidate": 1,
    "chunk_candidate": 2,
}


def read_json(path):
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception as exc:
        print(f"FAIL: could not parse {path}: {exc}")
        return None


def fail(message):
    print(f"FAIL: {message}")
    return False


def in_score_range(value):
    return isinstance(value, (int, float)) and 0.0 <= value <= 1.0


def recursive_forbidden_scan(payload):
    if isinstance(payload, dict):
        for key, value in payload.items():
            if any(token in str(key).lower() for token in FORBIDDEN_ADAPTIVE_KEYWORDS):
                return True, str(key)
            detected, source = recursive_forbidden_scan(value)
            if detected:
                return True, source
        return False, None
    if isinstance(payload, list):
        for item in payload:
            detected, source = recursive_forbidden_scan(item)
            if detected:
                return True, source
        return False, None
    if isinstance(payload, str):
        lowered = payload.lower()
        for token in FORBIDDEN_ADAPTIVE_KEYWORDS:
            if token in lowered:
                return True, payload
    return False, None


def recompute_static_score(breakdown):
    return round(sum(float(breakdown[key]) * weight for key, weight in WEIGHTS.items()) + 1e-10, 4)


def candidate_sort_key(candidate):
    return (
        -candidate["static_score"],
        LEVEL_ORDER.get(candidate["level"], 999),
        CANDIDATE_TYPE_ORDER.get(candidate["candidate_type"], 999),
        candidate["candidate_id"],
    )


def validate():
    print("Validating Static Candidate Ranking...")
    if not RANKING_PATH.exists():
        return fail(f"required file does not exist: {RANKING_PATH}")

    payload = read_json(RANKING_PATH)
    if payload is None:
        return False
    if not isinstance(payload, dict):
        return fail("static_candidate_ranking.json must be an object")
    if not REQUIRED_TOP_LEVEL_FIELDS.issubset(payload):
        return fail("top-level fields are incomplete")
    if payload.get("schema_version") != "ULGA_S10C_STATIC_CANDIDATE_RANKING_V1":
        return fail("schema_version mismatch")
    if payload.get("ranking_mode") != "static_offline":
        return fail("ranking_mode must be static_offline")
    if payload.get("adaptive_enabled") is not False:
        return fail("adaptive_enabled must be false")
    if not isinstance(payload.get("candidates"), list):
        return fail("candidates must be a list")
    if not isinstance(payload.get("blocked_candidates"), list):
        return fail("blocked_candidates must be a list")

    detected, source = recursive_forbidden_scan(payload)
    if detected:
        return fail(f"forbidden adaptive keyword found in output: {source}")

    candidates = payload["candidates"]
    blocked_candidates = payload["blocked_candidates"]
    expected_sorted = sorted(candidates, key=candidate_sort_key)
    if candidates != expected_sorted:
        return fail("candidates are not sorted by the required deterministic order")

    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            return fail(f"candidates[{index}] must be an object")
        if REQUIRED_CANDIDATE_FIELDS - set(candidate):
            return fail(f"candidates[{index}] missing required fields")
        if candidate["blocked"] is not False:
            return fail("blocked=true candidates must be excluded from active ranking")
        if candidate["block_reasons"] != []:
            return fail("blocked=false candidates must have empty block_reasons")
        if not isinstance(candidate["explain"], list) or not candidate["explain"]:
            return fail("every active candidate must have a non-empty explain list")
        if candidate["rank"] != index + 1:
            return fail("active candidate ranks must be continuous from 1")
        breakdown = candidate["score_breakdown"]
        if set(breakdown) != set(WEIGHTS):
            return fail("score_breakdown keys are incomplete")
        for key, value in breakdown.items():
            if not in_score_range(value):
                return fail(f"{candidate['candidate_id']} {key} out of range")
        if not in_score_range(candidate["static_score"]):
            return fail(f"{candidate['candidate_id']} static_score out of range")
        if recompute_static_score(breakdown) != candidate["static_score"]:
            return fail(f"{candidate['candidate_id']} static_score does not recompute correctly")

    for index, candidate in enumerate(blocked_candidates):
        if not isinstance(candidate, dict):
            return fail(f"blocked_candidates[{index}] must be an object")
        if REQUIRED_CANDIDATE_FIELDS - set(candidate):
            return fail(f"blocked_candidates[{index}] missing required fields")
        if candidate["blocked"] is not True:
            return fail("blocked_candidates entries must set blocked=true")
        if not isinstance(candidate["block_reasons"], list) or not candidate["block_reasons"]:
            return fail("blocked candidates must include block_reasons")
        if candidate["candidate_id"] in {item["candidate_id"] for item in candidates}:
            return fail("blocked candidates must be excluded from active ranking")
        breakdown = candidate["score_breakdown"]
        if set(breakdown) != set(WEIGHTS):
            return fail("blocked candidate score_breakdown keys are incomplete")
        for key, value in breakdown.items():
            if not in_score_range(value):
                return fail(f"blocked candidate {candidate['candidate_id']} {key} out of range")

    print("Static Candidate Ranking validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
