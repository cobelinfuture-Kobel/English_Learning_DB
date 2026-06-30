import json
import math
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
GRAMMAR_PATH = BASE_DIR / "grammar_profile" / "json" / "grammar_profile.json"
SOURCE_REPORT_PATH = BASE_DIR / "output" / "reports" / "source_import_report.json"
LEVEL_PROFILE_DIR = BASE_DIR / "level_profiles"
LEVEL_REPORT_PATH = BASE_DIR / "output" / "reports" / "level_profile_report.json"


PROFILE_ORDER = [
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

PROFILE_CONFIG = {
    "A1": {"cefr_base": "A1", "theme_level": "A1", "next_cefr": None, "sentence": (4, 8)},
    "A1_plus": {"cefr_base": "A1", "theme_level": "A1_plus", "next_cefr": "A2", "sentence": (5, 12)},
    "A2": {"cefr_base": "A2", "theme_level": "A2", "next_cefr": None, "sentence": (6, 14)},
    "A2_plus": {"cefr_base": "A2", "theme_level": "A2_plus", "next_cefr": "B1", "sentence": (7, 16)},
    "B1": {"cefr_base": "B1", "theme_level": "B1", "next_cefr": None, "sentence": (8, 18)},
    "B1_plus": {"cefr_base": "B1", "theme_level": "B1_plus", "next_cefr": "B2", "sentence": (9, 22)},
    "B2": {"cefr_base": "B2", "theme_level": "B2", "next_cefr": None, "sentence": (10, 26)},
    "B2_plus": {"cefr_base": "B2", "theme_level": "B2_plus", "next_cefr": "C1", "sentence": (12, 30)},
    "C1": {"cefr_base": "C1", "theme_level": "C1", "next_cefr": None, "sentence": (14, 34)},
}

LEVEL_CONNECTORS = {
    "A1": {
        "allowed": ["and", "but", "or"],
        "blocked": ["although", "however", "nevertheless", "despite"],
    },
    "A1_plus": {
        "allowed": ["and", "but", "or", "because", "so"],
        "blocked": ["although", "however", "nevertheless", "despite"],
    },
    "A2": {
        "allowed": ["and", "but", "or", "because", "so", "when"],
        "blocked": ["nevertheless", "despite", "whereas"],
    },
    "A2_plus": {
        "allowed": ["and", "but", "or", "because", "so", "when", "if", "while"],
        "blocked": ["nevertheless", "whereas"],
    },
    "B1": {
        "allowed": ["and", "but", "or", "because", "so", "when", "if", "while", "although"],
        "blocked": ["nevertheless", "notwithstanding"],
    },
    "B1_plus": {
        "allowed": ["and", "but", "or", "because", "so", "when", "if", "while", "although", "however"],
        "blocked": ["notwithstanding"],
    },
    "B2": {
        "allowed": ["and", "but", "or", "because", "so", "when", "if", "while", "although", "however", "despite"],
        "blocked": ["notwithstanding"],
    },
    "B2_plus": {
        "allowed": [
            "and",
            "but",
            "or",
            "because",
            "so",
            "when",
            "if",
            "while",
            "although",
            "however",
            "despite",
            "nevertheless",
        ],
        "blocked": [],
    },
    "C1": {
        "allowed": [
            "and",
            "but",
            "or",
            "because",
            "so",
            "when",
            "if",
            "while",
            "although",
            "however",
            "despite",
            "nevertheless",
            "whereas",
        ],
        "blocked": [],
    },
}

LEVEL_TENSES = {
    "A1": {
        "allowed": ["present_simple", "present_continuous"],
        "blocked": ["past_perfect", "future_perfect", "present_perfect_continuous"],
    },
    "A1_plus": {
        "allowed": ["present_simple", "present_continuous", "past_simple"],
        "blocked": ["past_perfect", "future_perfect", "present_perfect_continuous"],
    },
    "A2": {
        "allowed": ["present_simple", "present_continuous", "past_simple", "future_going_to"],
        "blocked": ["past_perfect", "future_perfect", "present_perfect_continuous"],
    },
    "A2_plus": {
        "allowed": ["present_simple", "present_continuous", "past_simple", "past_continuous", "present_perfect"],
        "blocked": ["past_perfect", "future_perfect"],
    },
    "B1": {
        "allowed": ["present_simple", "present_continuous", "past_simple", "past_continuous", "present_perfect"],
        "blocked": ["future_perfect"],
    },
    "B1_plus": {
        "allowed": [
            "present_simple",
            "present_continuous",
            "past_simple",
            "past_continuous",
            "present_perfect",
            "present_perfect_continuous",
            "past_perfect",
        ],
        "blocked": ["future_perfect"],
    },
    "B2": {
        "allowed": [
            "present_simple",
            "present_continuous",
            "past_simple",
            "past_continuous",
            "present_perfect",
            "present_perfect_continuous",
            "past_perfect",
        ],
        "blocked": [],
    },
    "B2_plus": {
        "allowed": [
            "present_simple",
            "present_continuous",
            "past_simple",
            "past_continuous",
            "present_perfect",
            "present_perfect_continuous",
            "past_perfect",
            "future_perfect",
        ],
        "blocked": [],
    },
    "C1": {
        "allowed": [
            "present_simple",
            "present_continuous",
            "past_simple",
            "past_continuous",
            "present_perfect",
            "present_perfect_continuous",
            "past_perfect",
            "future_perfect",
        ],
        "blocked": [],
    },
}


def load_json(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def sorted_records(records):
    return sorted(records, key=lambda record: (record.get("source_row", 0), record["id"]))


def collect_ids(records):
    return [record["id"] for record in sorted_records(records)]


def unique_sorted(values):
    return sorted({value for value in values if value})


def build_profile(level, records_by_level, warning_ids, all_super_categories, all_sub_categories):
    config = PROFILE_CONFIG[level]
    cefr_base = config["cefr_base"]
    sentence_min, sentence_max = config["sentence"]

    base_records = [
        record
        for record in records_by_level.get(cefr_base, [])
        if record["id"] not in warning_ids
    ]
    allowed_ids = collect_ids(base_records)

    candidate_records = []
    candidate_status = "not_applicable"
    next_cefr = config["next_cefr"]
    if next_cefr:
        candidate_limit = math.floor(len(allowed_ids) * 0.15)
        next_records = [
            record
            for record in sorted_records(records_by_level.get(next_cefr, []))
            if record["id"] not in warning_ids
        ]
        candidate_records = next_records[:candidate_limit]
        candidate_status = "draft_first_pass"

    candidate_ids = collect_ids(candidate_records)
    profile_super_categories = unique_sorted(
        [record.get("super_category", "") for record in base_records + candidate_records]
    )
    profile_sub_categories = unique_sorted(
        [record.get("sub_category", "") for record in base_records + candidate_records]
    )

    return {
        "level": level,
        "cefr_base": cefr_base,
        "theme_level": config["theme_level"],
        "active": True,
        "sentence_length_min": sentence_min,
        "sentence_length_max": sentence_max,
        "allowed_grammar_ids": allowed_ids,
        "candidate_grammar_ids": candidate_ids,
        "candidate_selection_status": candidate_status,
        "blocked_grammar_ids": sorted(warning_ids),
        "allowed_super_categories": profile_super_categories,
        "allowed_sub_categories": profile_sub_categories,
        "blocked_super_categories": sorted(all_super_categories - set(profile_super_categories)),
        "blocked_sub_categories": sorted(all_sub_categories - set(profile_sub_categories)),
        "allowed_connectors": LEVEL_CONNECTORS[level]["allowed"],
        "blocked_connectors": LEVEL_CONNECTORS[level]["blocked"],
        "allowed_tenses": LEVEL_TENSES[level]["allowed"],
        "blocked_tenses": LEVEL_TENSES[level]["blocked"],
        "validation_rules": {
            "required_grammar_fields": ["id", "level", "category", "can_do_statement", "example"],
            "blocked_grammar_ids_must_be_excluded": True,
            "max_candidate_ratio": 0.15,
            "max_sentence_length": sentence_max,
            "no_c2_active_profile": True,
        },
        "generation_rules": {
            "learning_content_generation_enabled": False,
            "dialogue_generation_enabled": False,
            "question_generation_enabled": False,
            "use_allowed_grammar_ids_only": True,
            "candidate_grammar_requires_review": bool(candidate_ids),
        },
        "media_rules": {
            "image_generation_enabled": False,
            "audio_generation_enabled": False,
        },
    }


def main():
    grammar_records = load_json(GRAMMAR_PATH)
    source_report = load_json(SOURCE_REPORT_PATH)
    warning_ids = {row["id"] for row in source_report.get("warning_rows", [])}

    records_by_level = {}
    for record in grammar_records:
        records_by_level.setdefault(record["level"], []).append(record)

    all_super_categories = unique_sorted(record.get("super_category", "") for record in grammar_records)
    all_sub_categories = unique_sorted(record.get("sub_category", "") for record in grammar_records)
    all_super_category_set = set(all_super_categories)
    all_sub_category_set = set(all_sub_categories)

    profile_files = []
    profile_summaries = {}
    warning_status = {}

    for level in PROFILE_ORDER:
        profile = build_profile(
            level,
            records_by_level,
            warning_ids,
            all_super_category_set,
            all_sub_category_set,
        )
        profile_path = LEVEL_PROFILE_DIR / f"{level}.json"
        write_json(profile_path, profile)
        profile_files.append(str(profile_path.relative_to(BASE_DIR)).replace("\\", "/"))

        allowed = set(profile["allowed_grammar_ids"])
        candidates = set(profile["candidate_grammar_ids"])
        blocked = set(profile["blocked_grammar_ids"])
        warning_status[level] = {
            warning_id: {
                "blocked": warning_id in blocked,
                "absent_from_allowed": warning_id not in allowed,
                "absent_from_candidates": warning_id not in candidates,
            }
            for warning_id in sorted(warning_ids)
        }

        base_allowed_count = len(profile["allowed_grammar_ids"])
        candidate_count = len(profile["candidate_grammar_ids"])
        ratio_limit = math.floor(base_allowed_count * 0.15)
        profile_summaries[level] = {
            "allowed_count": base_allowed_count,
            "candidate_count": candidate_count,
            "blocked_count": len(profile["blocked_grammar_ids"]),
            "candidate_ratio_limit": ratio_limit,
            "candidate_ratio_passed": candidate_count <= ratio_limit,
            "candidate_selection_status": profile["candidate_selection_status"],
        }

    report = {
        "profile_files": profile_files,
        "profiles": profile_summaries,
        "warning_ids": sorted(warning_ids),
        "warning_ids_blocked_status": warning_status,
        "c2_inactive_confirmation": {
            "c2_records_preserved_in_grammar_profile": len(records_by_level.get("C2", [])),
            "c2_profile_created": False,
            "c2_active": False,
        },
    }
    write_json(LEVEL_REPORT_PATH, report)

    print("Level profiles generated successfully.")
    for level in PROFILE_ORDER:
        summary = profile_summaries[level]
        print(
            f"{level}: allowed={summary['allowed_count']} "
            f"candidate={summary['candidate_count']} blocked={summary['blocked_count']}"
        )
    print("C2 active profile: not created")


if __name__ == "__main__":
    main()
