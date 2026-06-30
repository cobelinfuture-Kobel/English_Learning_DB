import json
import math
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
LEVEL_PROFILE_DIR = BASE_DIR / "level_profiles"
SOURCE_REPORT_PATH = BASE_DIR / "output" / "reports" / "source_import_report.json"

PROFILE_LEVELS = [
    "A1",
    "A1_plus",
    "A2",
    "A2_plus",
    "B1",
    "B1_plus",
    "B2",
    "B2_plus",
    "C1",
]

REQUIRED_KEYS = {
    "level",
    "cefr_base",
    "theme_level",
    "active",
    "sentence_length_min",
    "sentence_length_max",
    "allowed_grammar_ids",
    "candidate_grammar_ids",
    "blocked_grammar_ids",
    "allowed_super_categories",
    "allowed_sub_categories",
    "blocked_super_categories",
    "blocked_sub_categories",
    "allowed_connectors",
    "blocked_connectors",
    "allowed_tenses",
    "blocked_tenses",
    "validation_rules",
    "generation_rules",
    "media_rules",
}


def load_json(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_profile(level):
    return load_json(LEVEL_PROFILE_DIR / f"{level}.json")


def warning_ids():
    report = load_json(SOURCE_REPORT_PATH)
    return {row["id"] for row in report["warning_rows"]}


def test_all_9_profile_files_exist():
    for level in PROFILE_LEVELS:
        assert (LEVEL_PROFILE_DIR / f"{level}.json").exists(), f"Missing {level}.json"


def test_no_c2_active_profile_exists():
    assert not (LEVEL_PROFILE_DIR / "C2.json").exists(), "C2 active profile must not exist"


def test_every_profile_has_required_keys():
    for level in PROFILE_LEVELS:
        profile = load_profile(level)
        missing = REQUIRED_KEYS - set(profile)
        assert not missing, f"{level} is missing keys: {missing}"
        assert profile["active"] is True


def test_warning_ids_are_blocked_in_every_profile():
    warnings = warning_ids()
    for level in PROFILE_LEVELS:
        profile = load_profile(level)
        blocked = set(profile["blocked_grammar_ids"])
        assert warnings <= blocked, f"{level} does not block all warning IDs"


def test_warning_ids_absent_from_allowed_and_candidate_pools():
    warnings = warning_ids()
    for level in PROFILE_LEVELS:
        profile = load_profile(level)
        allowed = set(profile["allowed_grammar_ids"])
        candidates = set(profile["candidate_grammar_ids"])
        assert warnings.isdisjoint(allowed), f"{level} allowed pool contains warning IDs"
        assert warnings.isdisjoint(candidates), f"{level} candidate pool contains warning IDs"


def test_plus_level_next_cefr_candidates_do_not_exceed_15_percent():
    for level in ["A1_plus", "A2_plus", "B1_plus", "B2_plus"]:
        profile = load_profile(level)
        allowed_count = len(profile["allowed_grammar_ids"])
        candidate_count = len(profile["candidate_grammar_ids"])
        assert candidate_count <= math.floor(allowed_count * 0.15), (
            f"{level} candidate count exceeds 15% of allowed count"
        )


def test_c1_contains_no_c2_candidate_grammar():
    profile = load_profile("C1")
    assert profile["candidate_grammar_ids"] == []
    assert profile.get("candidate_selection_status") == "not_applicable"
