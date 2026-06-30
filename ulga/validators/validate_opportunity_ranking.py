import json
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

LEARNING_OPPORTUNITIES_PATH = BASE_DIR / "ulga" / "graph" / "learning_opportunities.json"
RANKED_PATH = BASE_DIR / "ulga" / "graph" / "ranked_learning_opportunities.json"
SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "opportunity_ranking_summary.json"

SOURCE = "ULGA_S10C_OPPORTUNITY_RANKING_AUTHORITY"
REQUIRED_BREAKDOWN_KEYS = {
    "dependency_score",
    "mastery_gap_score",
    "reinforcement_score",
    "theme_continuity_score",
    "frequency_score",
    "pattern_utility_score",
    "spiral_weight_score",
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


def in_score_range(value):
    return isinstance(value, (int, float)) and 0 <= value <= 1


def validate():
    print("Validating ULGA Opportunity Ranking...")
    for path in [LEARNING_OPPORTUNITIES_PATH, RANKED_PATH, SUMMARY_PATH]:
        if not path.exists():
            return fail(f"required file does not exist: {path}")

    opportunities = read_json(LEARNING_OPPORTUNITIES_PATH)
    ranked = read_json(RANKED_PATH)
    summary = read_json(SUMMARY_PATH)
    if opportunities is None or ranked is None or summary is None:
        return False
    if not isinstance(opportunities, list):
        return fail("learning_opportunities.json must be a list")
    if not isinstance(ranked, list):
        return fail("ranked_learning_opportunities.json must be a list")
    if not isinstance(summary, dict):
        return fail("opportunity_ranking_summary.json must be an object")

    opportunity_ids = {item.get("opportunity_id") for item in opportunities if isinstance(item, dict)}
    opportunity_ids.discard(None)
    ranks = []
    seen_ids = set()
    previous_score = None
    previous_id = None
    for index, item in enumerate(ranked):
        if not isinstance(item, dict):
            return fail(f"ranked[{index}] must be an object")
        for key in ["rank", "opportunity_id", "candidate_score", "score_breakdown", "explanation", "source"]:
            if key not in item:
                return fail(f"ranked[{index}] missing {key}")
        if item.get("ranking_mode") != "static_offline":
            return fail(f"ranked[{index}] ranking_mode must be static_offline")
        rank = item["rank"]
        if not isinstance(rank, int):
            return fail(f"ranked[{index}] rank must be an integer")
        ranks.append(rank)
        opportunity_id = item["opportunity_id"]
        if opportunity_id not in opportunity_ids:
            return fail(f"ranked[{index}] unknown opportunity_id: {opportunity_id}")
        if opportunity_id in seen_ids:
            return fail(f"duplicate ranked opportunity_id: {opportunity_id}")
        seen_ids.add(opportunity_id)
        if item["source"] != SOURCE:
            return fail(f"{opportunity_id} source must be {SOURCE}")
        if not in_score_range(item["candidate_score"]):
            return fail(f"{opportunity_id} candidate_score out of range")
        breakdown = item["score_breakdown"]
        if not isinstance(breakdown, dict):
            return fail(f"{opportunity_id} score_breakdown must be an object")
        if set(breakdown) != REQUIRED_BREAKDOWN_KEYS:
            return fail(f"{opportunity_id} score_breakdown keys are incomplete")
        for key, value in breakdown.items():
            if not in_score_range(value):
                return fail(f"{opportunity_id} {key} out of range")
        if not isinstance(item["explanation"], list) or not item["explanation"]:
            return fail(f"{opportunity_id} explanation must be a non-empty list")
        if not all(isinstance(value, str) and value for value in item["explanation"]):
            return fail(f"{opportunity_id} explanation entries must be non-empty strings")
        if previous_score is not None:
            if item["candidate_score"] > previous_score:
                return fail("ranking is not sorted by descending candidate_score")
            if item["candidate_score"] == previous_score and opportunity_id < previous_id:
                return fail("ranking deterministic tie-break by opportunity_id is violated")
        previous_score = item["candidate_score"]
        previous_id = opportunity_id

    expected_ranks = list(range(1, len(ranked) + 1))
    if ranks != expected_ranks:
        return fail("ranks must be unique and continuous from 1")
    if len(ranked) != len(opportunity_ids):
        return fail("ranked count must match learning opportunity count")
    if summary.get("source") != SOURCE:
        return fail(f"summary source must be {SOURCE}")
    if summary.get("ranking_mode") != "static_offline":
        return fail("summary ranking_mode must be static_offline")
    if summary.get("adaptive_inputs_used") != []:
        return fail("summary adaptive_inputs_used must be an empty list")
    if summary.get("status") not in {"PASS", "PASS_WITH_WARNINGS"}:
        return fail("summary status must be PASS or PASS_WITH_WARNINGS")
    if summary.get("total_ranked") != len(ranked):
        return fail("summary total_ranked does not match ranked length")
    for key in [
        "top_10_levels",
        "top_10_themes",
        "score_distribution",
        "dependency_distribution",
        "theme_source_distribution",
    ]:
        if not isinstance(summary.get(key), dict):
            return fail(f"summary {key} must be an object")
    if not isinstance(summary.get("warnings"), list):
        return fail("summary warnings must be a list")

    print("Opportunity Ranking validation: PASS")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
