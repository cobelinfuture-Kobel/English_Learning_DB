from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]

TASK_NAME = "RAZ-S6R_GH_P1_TargetedPatchPlan"
LEVELS = ("G", "H")
WARNING_FAMILIES = (
    "unknown_theme",
    "unknown_pattern",
    "unknown_grammar",
    "section_heading_detected",
    "human_review_required",
    "malformed_or_schema_warning",
    "dialogue_or_quotation_warning",
)

S6Q_DOC_PATH = BASE_DIR / "docs" / "ulga" / "RAZ_S6Q_GH_TAGGING_RERUN_DELTA_QA.md"
S6Q_REPORT_PATH = BASE_DIR / "ulga" / "reports" / "raz_gh_tagging_rerun_delta_qa.json"
S6P_DOC_PATH = BASE_DIR / "docs" / "ulga" / "RAZ_S6P_GH_TARGETED_TAXONOMY_AND_PATTERN_PATCH_IMPLEMENTATION.md"
S6P_REPORT_PATH = BASE_DIR / "ulga" / "reports" / "raz_gh_targeted_taxonomy_and_pattern_patch_implementation.json"
S6O_DOC_PATH = BASE_DIR / "docs" / "ulga" / "RAZ_S6O_GH_TARGETED_TAXONOMY_AND_PATTERN_PATCH_PLAN.md"
S6O_REPORT_PATH = BASE_DIR / "ulga" / "reports" / "raz_gh_targeted_taxonomy_and_pattern_patch_plan.json"
S6N_DOC_PATH = BASE_DIR / "docs" / "ulga" / "RAZ_S6N_WARNING_REPORT_COVERAGE_PATCH.md"
S6N_REPORT_PATH = BASE_DIR / "ulga" / "reports" / "raz_warning_report_coverage_patch.json"
S6M_DOC_PATH = BASE_DIR / "docs" / "ulga" / "RAZ_S6M_H_WARNING_CLUSTER_AND_REPORT_COVERAGE_QA.md"
S6M_REPORT_PATH = BASE_DIR / "ulga" / "reports" / "raz_h_warning_cluster_and_report_coverage_qa.json"

SUMMARY_REPORT_PATH = BASE_DIR / "raz_output_jsons" / "derived" / "reports" / "raz_tagging_summary.json"
WARNING_REPORT_PATH = BASE_DIR / "raz_output_jsons" / "derived" / "reports" / "raz_tagging_warnings.json"
SCHEMA_REPORT_PATH = BASE_DIR / "raz_output_jsons" / "derived" / "reports" / "raz_tagging_schema_validation.json"

SEED_POLICY_PATH = BASE_DIR / "ulga" / "policies" / "raz_seed_query_layer_policy.json"
SEED_QUERY_PATH = BASE_DIR / "ulga" / "query" / "raz_reusable_content_seed_query_layer.py"
SEED_VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_raz_reusable_content_seed_query_layer.py"
DISCOVERY_BUILDER_PATH = BASE_DIR / "ulga" / "builders" / "build_raz_level_discovery.py"
DISCOVERY_VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_raz_level_discovery.py"
DRIFT_VALIDATOR_PATH = BASE_DIR / "ulga" / "validators" / "validate_raz_downstream_discovery_drift.py"
LEVEL_DISCOVERY_SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "raz_level_discovery_summary.json"
LEVEL_DISCOVERY_VALIDATION_PATH = BASE_DIR / "ulga" / "reports" / "raz_level_discovery_validation.json"
SEED_SUMMARY_PATH = BASE_DIR / "ulga" / "reports" / "raz_reusable_content_seed_query_layer_summary.json"
SEED_VALIDATION_PATH = BASE_DIR / "ulga" / "reports" / "raz_reusable_content_seed_query_layer_validation.json"
DRIFT_VALIDATION_PATH = BASE_DIR / "ulga" / "reports" / "raz_downstream_discovery_drift_validation.json"

PIPELINE_PATH = BASE_DIR / "tools" / "raz_normalized_tagging_pipeline.py"
PIPELINE_TEST_PATH = BASE_DIR / "tests" / "test_raz_normalized_tagging_pipeline.py"

OUTPUT_JSON_PATH = BASE_DIR / "ulga" / "reports" / "raz_gh_p1_targeted_patch_plan.json"
OUTPUT_MARKDOWN_PATH = BASE_DIR / "docs" / "ulga" / "RAZ_S6R_GH_P1_TARGETED_PATCH_PLAN.md"


THEME_TITLE_GROUPS = {
    "social_emotional_moral_choice": {
        "titles": {
            "Being a Leftie",
            "Billy Gets Lost",
            "Cool as a Cuke",
            "Doing the Right Thing",
            "Gordon Finds His Way",
            "Molly's New Home",
            "New Rule!",
            "Peace and Quiet",
            "Rude Robot",
            "Tag-Along Goat",
            "The Day I Needed Help",
        },
        "confidence": "HIGH",
        "rule_pollution_risk": "LOW",
        "implementation_style": "title/book-level mapping",
        "patch_priority": "P1_IMPLEMENT",
    },
    "culture_holiday_tradition": {
        "titles": {
            "A President's Day",
            "American Symbols",
            "Mystery Valentine",
            "My Eid al-Fitr",
            "Nami's Gifts",
            "Sam's Fourth of July",
            "Stars and Stripes",
            "The Legend of Nian",
            "Welcome to Turkey",
            "Wing's Visit to Singapore",
        },
        "confidence": "HIGH",
        "rule_pollution_risk": "LOW",
        "implementation_style": "title/book-level mapping",
        "patch_priority": "P1_IMPLEMENT",
    },
    "fantasy_monsters_royalty": {
        "titles": {
            "A Monster Fish Tale",
            "Club Monster",
            "Cinderella",
            "Monster Halloween",
            "Monsters' Stormy Day",
            "Monsters on Wheels",
            "Pedro's Burro",
            "Pip, the Monster Princess",
            "Rapunzel",
            "Stormingo!",
            "The Empty Pot",
            "The Little Red Hen",
            "The Stonecutter",
            "Troll Bridge",
        },
        "confidence": "MEDIUM",
        "rule_pollution_risk": "MEDIUM",
        "implementation_style": "title/book-level mapping",
        "patch_priority": "P1_IMPLEMENT",
    },
    "math_counting_measurement_leftover": {
        "titles": {
            "How Many Is Fifty?",
            "I Collect That!",
            "In and Out of the Toy Box",
            "Living Or Nonliving?",
            "Math Test Mix-Up",
            "Signs Are Everywhere",
            "Tens and Ones Together",
            "Time of Day",
            "Twenty, More or Less",
            "What in the World Is That?",
            "Which One Is More?",
        },
        "confidence": "HIGH",
        "rule_pollution_risk": "LOW",
        "implementation_style": "no-change",
        "patch_priority": "P2_DEFER",
    },
    "poetry_literary_misc_deferred": {
        "titles": {
            "Anna and the Dancing Goose",
            "How Many Rhymes?",
            "Ough is Tough",
            "The Owl and the Pussycat",
        },
        "confidence": "LOW",
        "rule_pollution_risk": "HIGH",
        "implementation_style": "no-change",
        "patch_priority": "DEFER",
    },
}

THEME_CATEGORY_ORDER = [
    "social_emotional_moral_choice",
    "culture_holiday_tradition",
    "fantasy_monsters_royalty",
    "math_counting_measurement_leftover",
    "poetry_literary_misc_deferred",
]

POETRY_PATTERN_TITLES = {"Anna and the Dancing Goose", "How Many Rhymes?", "Ough is Tough", "The Owl and the Pussycat"}
IMPERATIVE_STARTERS = {
    "beware",
    "cover",
    "dig",
    "drop",
    "fill",
    "find",
    "get",
    "listen",
    "look",
    "make",
    "move",
    "never",
    "pat",
    "roll",
    "run",
    "use",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def stable_path(path: Path) -> str:
    return path.relative_to(BASE_DIR).as_posix()


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").replace("\n", " ")).strip()


def text_signature(text: str) -> str:
    cleaned = clean_text(text).lower()
    cleaned = re.sub(r"\d+", "<num>", cleaned)
    cleaned = re.sub(r"\b[a-z]{1,2}\b", "<w>", cleaned)
    cleaned = re.sub(r"[^a-z<>\s]", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def summarize_counter(counter: Counter[str], limit: int = 10) -> list[dict[str, Any]]:
    return [{"key": key, "count": count} for key, count in counter.most_common(limit)]


def sample_records(records: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for record in records[:limit]:
        samples.append(
            {
                "record_id": record["record_id"],
                "level": record["level"],
                "book_id": record["book_id"],
                "title": record["title"],
                "page_unit_id": record.get("page_unit_id"),
                "record_type": record["record_type"],
                "text": record["text"],
                "warnings": record["warnings"],
            }
        )
    return samples


def build_level_paths(level: str) -> dict[str, Path]:
    root = BASE_DIR / "raz_output_jsons" / "derived" / f"Level_{level}"
    return {
        "sentence_normalized": root / "normalized" / f"raz_{level}_sentence_normalized.jsonl",
        "page_normalized": root / "normalized" / f"raz_{level}_page_unit_normalized.json",
        "reuse_normalized": root / "normalized" / f"raz_{level}_reuse_unit_normalized.json",
        "sentence_enriched": root / "enriched" / f"raz_{level}_sentence_enriched.jsonl",
        "page_enriched": root / "enriched" / f"raz_{level}_page_unit_enriched.json",
        "reuse_enriched": root / "enriched" / f"raz_{level}_reuse_unit_enriched.json",
    }


def infer_record_type(record_id: str, content_unit_type: str | None) -> str:
    if content_unit_type:
        return content_unit_type
    if "_P" in record_id and "_CAND_" not in record_id and "_REUSE_" not in record_id:
        return "page_unit"
    if "_REUSE_" in record_id:
        return "reuse_unit"
    return "sentence"


def load_level_records(level: str, flat_warnings: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    paths = build_level_paths(level)
    normalized_by_id: dict[str, dict[str, Any]] = {}
    enriched_by_id: dict[str, dict[str, Any]] = {}

    normalized_sentence = load_jsonl(paths["sentence_normalized"])
    normalized_page = load_json(paths["page_normalized"])
    normalized_reuse = load_json(paths["reuse_normalized"])
    enriched_sentence = load_jsonl(paths["sentence_enriched"])
    enriched_page = load_json(paths["page_enriched"])
    enriched_reuse = load_json(paths["reuse_enriched"])

    for row in normalized_sentence:
        normalized_by_id[row["candidate_id"]] = row
    for row in normalized_page:
        normalized_by_id[row["page_unit_id"]] = row
    for row in normalized_reuse:
        normalized_by_id[row["reuse_unit_id"]] = row

    for row in enriched_sentence:
        enriched_by_id[row["candidate_id"]] = row
    for row in enriched_page:
        enriched_by_id[row["page_unit_id"]] = row
    for row in enriched_reuse:
        enriched_by_id[row["reuse_unit_id"]] = row

    warning_types_by_record: dict[str, set[str]] = defaultdict(set)
    for row in flat_warnings:
        if row.get("level") == level:
            warning_types_by_record[str(row["record_id"])].add(str(row["warning_type"]))

    records: list[dict[str, Any]] = []
    for record_id, row in enriched_by_id.items():
        qa_tags = row.get("qa_tags") or {}
        source_tags = row.get("source_tags") or {}
        content_unit_tags = row.get("content_unit_tags") or {}
        linguistic_tags = row.get("linguistic_tags") or {}
        warnings = set(qa_tags.get("warnings") or [])
        if qa_tags.get("needs_human_review"):
            warnings.add("human_review_required")
        warnings.update(warning_types_by_record.get(record_id, set()))

        normalized = normalized_by_id.get(record_id, {})
        text = row.get("text") or normalized.get("text") or normalized.get("clean_text") or ""
        grammar_tags = list(linguistic_tags.get("grammar_tags") or [])
        pattern_tags = list(linguistic_tags.get("sentence_pattern_tags") or [])
        records.append(
            {
                "record_id": record_id,
                "level": level,
                "record_type": infer_record_type(record_id, content_unit_tags.get("content_unit_type")),
                "book_id": str(source_tags.get("book_id") or row.get("book_id") or ""),
                "title": str(source_tags.get("book_title") or row.get("title") or ""),
                "page_unit_id": source_tags.get("page_unit_id") or row.get("source_page_unit_id") or row.get("page_unit_id"),
                "text": clean_text(text),
                "text_signature": text_signature(text),
                "warnings": sorted(warnings),
                "needs_human_review": bool(qa_tags.get("needs_human_review")),
                "review_status": qa_tags.get("review_status"),
                "mapped_theme": (row.get("theme_tags") or {}).get("mapped_theme"),
                "grammar_tags": grammar_tags,
                "pattern_tags": pattern_tags,
                "is_heading": bool(content_unit_tags.get("is_heading")),
                "is_direct_speech": bool(content_unit_tags.get("is_direct_speech")),
                "is_question": bool(content_unit_tags.get("is_question")),
                "is_imperative": bool(content_unit_tags.get("is_imperative")),
            }
        )

    counts = {
        "sentence_normalized": len(normalized_sentence),
        "page_normalized": len(normalized_page),
        "reuse_normalized": len(normalized_reuse),
        "sentence_enriched": len(enriched_sentence),
        "page_enriched": len(enriched_page),
        "reuse_enriched": len(enriched_reuse),
    }
    return records, counts


def count_family(records: list[dict[str, Any]], family: str) -> int:
    if family == "human_review_required":
        return sum(1 for record in records if record["needs_human_review"])
    return sum(1 for record in records if family in record["warnings"])


def theme_category_for_record(record: dict[str, Any]) -> str:
    title = record["title"]
    for category in THEME_CATEGORY_ORDER:
        if title in THEME_TITLE_GROUPS[category]["titles"]:
            return category
    if record["record_type"] == "section_heading":
        return "broad_narrative_ambiguous_residual"
    if title in {"American Football", "Blue Whales: Giant Mammals", "Groundhog Goes Outside", "Hedgehogs", "Pocket Parks", "Ships and Boats", "Soccer", "The Mighty Mississippi"}:
        return "other"
    return "broad_narrative_ambiguous_residual"


def has_adjacent_repeat(text: str) -> bool:
    words = re.findall(r"[a-z']+", text.lower())
    return any(words[i] == words[i + 1] for i in range(len(words) - 1))


def preposition_count(text: str) -> int:
    return len(
        re.findall(
            r"\b(in|on|at|under|over|into|from|with|by|near|around|through|across|behind|inside|outside|before|after|for|to|of)\b",
            text.lower(),
        )
    )


def pattern_category_for_record(record: dict[str, Any]) -> str:
    text = record["text"]
    lower = text.lower()
    if record["is_direct_speech"] or '"' in text:
        return "quoted_expressive_sentence"
    if record["is_question"] or text.endswith("?"):
        return "question_like_residual"
    if record["is_imperative"]:
        return "imperative_procedural_residual"
    if "[" in text and "]" in text:
        return "pronunciation_artifact_residual"
    if record["title"] in POETRY_PATTERN_TITLES or lower.count(",") >= 2 or "..." in text or has_adjacent_repeat(text):
        return "poetic_repetitive_line"
    if text.startswith(("And ", "Then ")) and preposition_count(text) >= 1:
        return "narrative_inversion"
    if re.search(r"\b(before|after|when|while|until|because|if|that|which|who)\b", lower):
        return "relative_or_temporal_clause_tail"
    if re.search(r"\b(and|but|or|so|yet)\b", lower) and "," in text:
        return "compound_predicate_or_clause_chain"
    if preposition_count(text) >= 2:
        return "prepositional_expansion"
    if len(re.findall(r"[A-Za-z']+", text)) <= 3 or not text.endswith((".", "!", "?")):
        return "malformed_fragment_like_residual"
    return "other"


def grammar_category_for_record(record: dict[str, Any]) -> str:
    text = record["text"]
    lower = text.lower()
    first_word_match = re.match(r"^([A-Za-z']+)", lower)
    first_word = first_word_match.group(1) if first_word_match else ""
    if record["is_heading"] or record["record_type"] == "section_heading":
        return "section_heading_driven_artifact"
    if record["is_imperative"] or first_word in IMPERATIVE_STARTERS:
        return "imperative_procedural"
    if record["is_question"] or text.endswith("?"):
        return "question_form_residual"
    if re.search(r"\b(and|but|or|so|then|that|which|who|when|while|because|if|after|before)\b", lower):
        return "compound_relative_grammar_residual"
    if re.search(r"\b(am|is|are|was|were|have|has|had|do|does|did|can|could|will|would|should|must)\b", lower) or text.endswith((".", "!")):
        return "present_simple_linking_still_missed"
    return "other"


def summarize_unknown_theme(records: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    groups = defaultdict(list)
    for record in records:
        if "unknown_theme" in record["warnings"]:
            groups[theme_category_for_record(record)].append(record)

    categories: dict[str, Any] = {}
    for category, rows in groups.items():
        meta = THEME_TITLE_GROUPS.get(category, {})
        categories[category] = {
            "evidence_count": len(rows),
            "levels_observed": sorted({row["level"] for row in rows}),
            "sample_records": sample_records(rows, 5),
            "title_book_concentration": summarize_counter(Counter(f'{row["book_id"]} | {row["title"]}' for row in rows), 8),
            "confidence": meta.get("confidence", "LOW"),
            "rule_pollution_risk": meta.get("rule_pollution_risk", "HIGH"),
            "expected_reduction": round(len(rows) * 0.75) if category in {"social_emotional_moral_choice", "culture_holiday_tradition", "fantasy_monsters_royalty"} else 0,
            "implementation_style": meta.get("implementation_style", "no-change"),
            "patch_priority": meta.get("patch_priority", "DEFER"),
        }

    authorizations = [
        build_candidate_authorization(
            candidate_id="THM_P1_SOCIAL_EMOTIONAL_MORAL_CHOICE",
            candidate_type="theme_taxonomy",
            s6o_priority="P1",
            decision="AUTHORIZE_FOR_S6S",
            summary=categories.get("social_emotional_moral_choice", {}),
            implementation_scope="Title/book-level mappings for manners, self-regulation, peer-help, and consequence stories only.",
            required_exclusions=["No body-text heuristic", "No dialogue-keyword free-form mapping"],
            reason="Residual evidence remains concentrated in stable title-level social and moral-choice books.",
        ),
        build_candidate_authorization(
            candidate_id="THM_P1_CULTURE_HOLIDAY_TRADITION",
            candidate_type="theme_taxonomy",
            s6o_priority="P1",
            decision="AUTHORIZE_FOR_S6S",
            summary=categories.get("culture_holiday_tradition", {}),
            implementation_scope="Title/book-level mappings for named holidays, country/culture introductions, and festival stories only.",
            required_exclusions=["No generic food/gift keyword mapping", "No broad geography heuristic"],
            reason="Residuals remain highly title-concentrated and separable from generic narrative books.",
        ),
        build_candidate_authorization(
            candidate_id="THM_P1_FANTASY_MONSTERS_ROYALTY",
            candidate_type="theme_taxonomy",
            s6o_priority="P1",
            decision="AUTHORIZE_FOR_S6S",
            summary=categories.get("fantasy_monsters_royalty", {}),
            implementation_scope="Title/book-level mappings for monster/fantasy/royalty books already concentrated in residual G/H backlog.",
            required_exclusions=["No generic queen/king keyword mapping", "Keep poetry titles excluded"],
            reason="Residuals are still material and mostly concentrated in obvious fantasy-title clusters.",
        ),
        build_candidate_authorization(
            candidate_id="THM_P2_MATH_COUNTING_MEASUREMENT",
            candidate_type="no_change",
            s6o_priority="P2",
            decision="REPLACE_WITH_I_SMOKE_PILOT",
            summary=categories.get("math_counting_measurement_leftover", {}),
            implementation_scope="No G/H P1 work. Revisit after Level I smoke pilot if math residuals remain strategically important.",
            required_exclusions=["No S6S implementation"],
            reason="Residual math volume is mostly G-specific and does not justify widening S6S beyond safer P1 themes.",
        ),
        build_candidate_authorization(
            candidate_id="THM_DEFER_POETRY_LITERARY_MISC",
            candidate_type="no_change",
            s6o_priority="DEFER",
            decision="DEFER",
            summary=categories.get("poetry_literary_misc_deferred", {}),
            implementation_scope="Human-review-only backlog.",
            required_exclusions=["No poetry theme auto-mapping", "No broad literary catch-all"],
            reason="Poetry and literary residuals remain structurally ambiguous and high-risk.",
        ),
    ]
    return {"status": "PASS_WITH_WARNINGS", "categories": categories}, authorizations


def summarize_unknown_pattern(records: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    groups = defaultdict(list)
    for record in records:
        if "unknown_pattern" in record["warnings"]:
            groups[pattern_category_for_record(record)].append(record)

    categories: dict[str, Any] = {}
    for category, rows in groups.items():
        if category in {"quoted_expressive_sentence", "prepositional_expansion", "compound_predicate_or_clause_chain", "relative_or_temporal_clause_tail"}:
            confidence = "MEDIUM"
            risk = "MEDIUM" if category != "prepositional_expansion" else "LOW"
        elif category in {"poetic_repetitive_line", "narrative_inversion", "pronunciation_artifact_residual", "malformed_fragment_like_residual"}:
            confidence = "LOW"
            risk = "HIGH"
        else:
            confidence = "LOW"
            risk = "MEDIUM"
        expected = 0
        if category == "prepositional_expansion":
            expected = round(len(rows) * 0.35)
        elif category == "relative_or_temporal_clause_tail":
            expected = round(len(rows) * 0.45)
        elif category == "compound_predicate_or_clause_chain":
            expected = round(len(rows) * 0.5)
        categories[category] = {
            "evidence_count": len(rows),
            "levels_observed": sorted({row["level"] for row in rows}),
            "sample_records": sample_records(rows, 5),
            "title_book_concentration": summarize_counter(Counter(f'{row["book_id"]} | {row["title"]}' for row in rows), 8),
            "confidence": confidence,
            "rule_pollution_risk": risk,
            "expected_reduction": expected,
            "implementation_style": "conservative rule" if expected else "no-change",
            "patch_priority": "P1_NARROW_SCOPE" if expected else "DEFER",
        }

    authorizations = [
        build_candidate_authorization(
            candidate_id="PAT_P1_QUOTED_EXPRESSIVE_SENTENCE",
            candidate_type="pattern_rule",
            s6o_priority="P1",
            decision="DEFER",
            summary=categories.get("quoted_expressive_sentence", {}),
            implementation_scope="Keep deferred; do not add direct-speech coverage in S6S.",
            required_exclusions=["No dialogue pattern expansion", "No quote-frame generalization"],
            reason="Residual quoted backlog is large but mixes dialogue, literary fragments, and question frames too tightly.",
        ),
        build_candidate_authorization(
            candidate_id="PAT_P1_PREPOSITIONAL_EXPANSION",
            candidate_type="pattern_rule",
            s6o_priority="P1",
            decision="DEFER",
            summary=categories.get("prepositional_expansion", {}),
            implementation_scope="Keep deferred for S6S; reconsider only after theme and imperative deltas.",
            required_exclusions=["No free-form PP catch-all", "No poetry-title coverage"],
            reason="Residual PP-like rows still include rhyme/story artifacts and offer modest incremental reduction.",
        ),
        build_candidate_authorization(
            candidate_id="PAT_P1_COMPOUND_PREDICATE_OR_CLAUSE_CHAIN",
            candidate_type="pattern_rule",
            s6o_priority="P1",
            decision="DEFER",
            summary=categories.get("compound_predicate_or_clause_chain", {}),
            implementation_scope="Keep deferred; not authorized for S6S.",
            required_exclusions=["No broad coordinator rule"],
            reason="Residual evidence is small and overlaps imperative/procedural or narrative structures.",
        ),
        build_candidate_authorization(
            candidate_id="PAT_P1_RELATIVE_OR_TEMPORAL_CLAUSE_TAIL",
            candidate_type="pattern_rule",
            s6o_priority="P1",
            decision="DEFER",
            summary=categories.get("relative_or_temporal_clause_tail", {}),
            implementation_scope="Keep deferred; use sample set as future narrow candidate only.",
            required_exclusions=["No broad subordinate-clause rule"],
            reason="This is the cleanest remaining pattern subset, but evidence is still not strong enough to justify S6S before Level I.",
        ),
        build_candidate_authorization(
            candidate_id="PAT_DEFER_POETIC_REPETITIVE_LINE",
            candidate_type="no_change",
            s6o_priority="DEFER",
            decision="DEFER",
            summary=categories.get("poetic_repetitive_line", {}),
            implementation_scope="Human-review-only backlog.",
            required_exclusions=["No poetry line normalization"],
            reason="Poetic repetitions remain high-pollution by design.",
        ),
        build_candidate_authorization(
            candidate_id="PAT_DEFER_NARRATIVE_INVERSION_AND_ARTIFACT",
            candidate_type="no_change",
            s6o_priority="DEFER",
            decision="DEFER",
            summary=categories.get("narrative_inversion", categories.get("pronunciation_artifact_residual", {})),
            implementation_scope="Human-review-only backlog.",
            required_exclusions=["No inversion acceptance", "No pronunciation artifact acceptance"],
            reason="Narrative inversion and pronunciation artifacts remain low-volume but structurally unsafe.",
        ),
    ]
    return {"status": "PASS_WITH_WARNINGS", "categories": categories}, authorizations


def summarize_unknown_grammar(records: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    groups = defaultdict(list)
    for record in records:
        if "unknown_grammar" in record["warnings"]:
            groups[grammar_category_for_record(record)].append(record)

    categories: dict[str, Any] = {}
    for category, rows in groups.items():
        if category == "imperative_procedural":
            confidence = "HIGH"
            risk = "LOW"
            expected = round(len(rows) * 0.8)
            priority = "P1_NARROW_SCOPE"
        elif category == "present_simple_linking_still_missed":
            confidence = "LOW"
            risk = "HIGH"
            expected = round(len(rows) * 0.2)
            priority = "DEFER"
        elif category == "section_heading_driven_artifact":
            confidence = "HIGH"
            risk = "HIGH"
            expected = 0
            priority = "DEFER"
        elif category == "compound_relative_grammar_residual":
            confidence = "MEDIUM"
            risk = "MEDIUM"
            expected = round(len(rows) * 0.25)
            priority = "DEFER"
        else:
            confidence = "LOW"
            risk = "MEDIUM"
            expected = 0
            priority = "DEFER"
        categories[category] = {
            "evidence_count": len(rows),
            "levels_observed": sorted({row["level"] for row in rows}),
            "sample_records": sample_records(rows, 5),
            "title_book_concentration": summarize_counter(Counter(f'{row["book_id"]} | {row["title"]}' for row in rows), 8),
            "confidence": confidence,
            "rule_pollution_risk": risk,
            "expected_reduction": expected,
            "patch_priority": priority,
        }

    authorizations = [
        build_candidate_authorization(
            candidate_id="GRM_P1_PRESENT_SIMPLE_AND_LINKING_FOLLOWUP",
            candidate_type="grammar_rule",
            s6o_priority="P1",
            decision="DEFER",
            summary=categories.get("present_simple_linking_still_missed", {}),
            implementation_scope="No S6S implementation. Re-evaluate only after future pattern/thematic deltas or Level I pilot evidence.",
            required_exclusions=["No broad present-simple expansion", "No heading spillover"],
            reason="Post-S6P residuals are too mixed; broad follow-up risks overfiring into fragments and procedural text.",
        ),
        build_candidate_authorization(
            candidate_id="GRM_P1_IMPERATIVE_PROCEDURAL",
            candidate_type="grammar_rule",
            s6o_priority="P1",
            decision="AUTHORIZE_NARROW_FOR_S6S",
            summary=categories.get("imperative_procedural", {}),
            implementation_scope="Only clear non-heading procedural imperatives and safety/how-to commands; exclude one-word fragments and headings.",
            required_exclusions=["No section heading acceptance", "No single-token fragment acceptance", "No dialogue imperative broadening"],
            reason="Imperative residuals are small, high-confidence, and separable from heading artifacts.",
        ),
        build_candidate_authorization(
            candidate_id="GRM_DEFER_SECTION_HEADING_ARTIFACTS",
            candidate_type="no_change",
            s6o_priority="DEFER",
            decision="DEFER",
            summary=categories.get("section_heading_driven_artifact", {}),
            implementation_scope="Keep warning-only and query-excluded.",
            required_exclusions=["No heading grammar acceptance"],
            reason="Heading-driven grammar residual remains the dominant non-actionable bucket.",
        ),
    ]
    return {"status": "PASS_WITH_WARNINGS", "categories": categories}, authorizations


def build_candidate_authorization(
    *,
    candidate_id: str,
    candidate_type: str,
    s6o_priority: str,
    decision: str,
    summary: dict[str, Any],
    implementation_scope: str,
    required_exclusions: list[str],
    reason: str,
) -> dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "candidate_type": candidate_type,
        "s6o_priority": s6o_priority,
        "s6r_decision": decision,
        "evidence_count": summary.get("evidence_count", 0),
        "estimated_warning_reduction": summary.get("expected_reduction", 0),
        "confidence": summary.get("confidence", "LOW"),
        "rule_pollution_risk": summary.get("rule_pollution_risk", "HIGH"),
        "implementation_scope": implementation_scope,
        "required_exclusions": required_exclusions,
        "sample_records": summary.get("sample_records", [])[:3],
        "reason": reason,
    }


def build_residual_warning_summary(records_by_level: dict[str, list[dict[str, Any]]], current_metrics: dict[str, dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for level in LEVELS:
        records = records_by_level[level]
        residual_records = [record for record in records if record["warnings"]]
        by_book = Counter()
        by_page_unit = Counter()
        by_signature = Counter()
        for record in residual_records:
            warning_weight = len(record["warnings"])
            by_book[f'{record["book_id"]} | {record["title"]}'] += warning_weight
            if record.get("page_unit_id"):
                by_page_unit[str(record["page_unit_id"])] += warning_weight
            if record["record_type"] == "sentence":
                by_signature[record["text_signature"]] += 1

        enriched = current_metrics[level]["enriched_record_count"]
        summary[level] = {
            "current_enriched_record_count": enriched,
            "current_unknown_theme_count": current_metrics[level]["unknown_theme"],
            "current_unknown_theme_rate": round(current_metrics[level]["unknown_theme"] / enriched, 4),
            "current_unknown_pattern_count": current_metrics[level]["unknown_pattern"],
            "current_unknown_pattern_rate": round(current_metrics[level]["unknown_pattern"] / enriched, 4),
            "current_unknown_grammar_count": current_metrics[level]["unknown_grammar"],
            "current_unknown_grammar_rate": round(current_metrics[level]["unknown_grammar"] / enriched, 4),
            "current_section_heading_detected_count": current_metrics[level]["section_heading_detected"],
            "current_section_heading_detected_rate": round(current_metrics[level]["section_heading_detected"] / enriched, 4),
            "current_human_review_required_count": current_metrics[level]["human_review_required"],
            "current_human_review_required_rate": round(current_metrics[level]["human_review_required"] / enriched, 4),
            "current_malformed_or_schema_warning": current_metrics[level]["malformed_or_schema_warning"],
            "current_dialogue_or_quotation_warning": current_metrics[level]["dialogue_or_quotation_warning"],
            "top_residual_books_by_warning_count": summarize_counter(by_book, 10),
            "top_residual_page_units": summarize_counter(by_page_unit, 10),
            "top_residual_repeated_text_patterns": summarize_counter(by_signature, 10),
        }
    return summary


def build_current_metrics(records_by_level: dict[str, list[dict[str, Any]]], flat_warnings: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    current_metrics: dict[str, dict[str, Any]] = {}
    for level in LEVELS:
        records = records_by_level[level]
        flat_level_counts = Counter(row["warning_type"] for row in flat_warnings if row.get("level") == level)
        current_metrics[level] = {
            "enriched_record_count": len(records),
            "unknown_theme": count_family(records, "unknown_theme"),
            "unknown_pattern": count_family(records, "unknown_pattern"),
            "unknown_grammar": count_family(records, "unknown_grammar"),
            "section_heading_detected": count_family(records, "section_heading_detected"),
            "human_review_required": count_family(records, "human_review_required"),
            "malformed_or_schema_warning": flat_level_counts.get("malformed_or_schema_warning", 0),
            "dialogue_or_quotation_warning": flat_level_counts.get("dialogue_or_quotation_warning", 0),
        }
    return current_metrics


def render_candidate_table(rows: list[dict[str, Any]]) -> str:
    lines = ["| Candidate | Type | Decision | Evidence | Est. Reduction | Confidence | Risk |", "|---|---|---|---:|---:|---|---|"]
    for row in rows:
        lines.append(
            f"| `{row['candidate_id']}` | `{row['candidate_type']}` | `{row['s6r_decision']}` | {row['evidence_count']} | {row['estimated_warning_reduction']} | `{row['confidence']}` | `{row['rule_pollution_risk']}` |"
        )
    return "\n".join(lines)


def build_report(command_results: dict[str, str] | None = None) -> dict[str, Any]:
    commands = command_results or {}
    s6q_report = load_json(S6Q_REPORT_PATH)
    s6p_report = load_json(S6P_REPORT_PATH)
    s6o_report = load_json(S6O_REPORT_PATH)
    s6n_report = load_json(S6N_REPORT_PATH)
    s6m_report = load_json(S6M_REPORT_PATH)
    summary_report = load_json(SUMMARY_REPORT_PATH)
    flat_warnings = load_json(WARNING_REPORT_PATH)
    schema_report = load_json(SCHEMA_REPORT_PATH)
    seed_policy = load_json(SEED_POLICY_PATH)
    level_discovery_summary = load_json(LEVEL_DISCOVERY_SUMMARY_PATH)
    level_discovery_validation = load_json(LEVEL_DISCOVERY_VALIDATION_PATH)
    seed_summary = load_json(SEED_SUMMARY_PATH)
    seed_validation = load_json(SEED_VALIDATION_PATH)
    drift_validation = load_json(DRIFT_VALIDATION_PATH)

    records_by_level: dict[str, list[dict[str, Any]]] = {}
    count_details: dict[str, dict[str, int]] = {}
    for level in LEVELS:
        records, counts = load_level_records(level, flat_warnings)
        records_by_level[level] = records
        count_details[level] = counts

    current_metrics = build_current_metrics(records_by_level, flat_warnings)
    residual_warning_summary = build_residual_warning_summary(records_by_level, current_metrics)

    all_records = [record for level in LEVELS for record in records_by_level[level]]
    theme_analysis, theme_authorizations = summarize_unknown_theme(all_records)
    pattern_analysis, pattern_authorizations = summarize_unknown_pattern(all_records)
    grammar_analysis, grammar_authorizations = summarize_unknown_grammar(all_records)
    candidate_authorization_table = theme_authorizations + pattern_authorizations + grammar_authorizations

    queryable_levels = seed_validation.get("discovered_queryable_levels", [])
    validator_results = {
        "validate_raz_level_discovery": level_discovery_validation.get("status"),
        "validate_raz_reusable_content_seed_query_layer": seed_validation.get("status"),
        "validate_raz_downstream_discovery_drift": drift_validation.get("status"),
        "must_fix_count": (drift_validation.get("summary") or {}).get("must_fix_count", drift_validation.get("must_fix_count", 0)),
    }

    recommendation = "AUTHORIZE_S6S_P1_THEME_PLUS_IMPERATIVE_ONLY"
    status = "PASS_WITH_WARNINGS"
    decision = "RUN_S6S_P1_TARGETED_PATCH_IMPLEMENTATION"
    warnings = [
        "Residual pattern backlog is now dominated by quoted, poetic, question-like, and other ambiguity-heavy structures after S6P removed the low-risk declarative mass.",
        "Theme P1 remains safe only as narrow title/book-level mapping families; broad lexical heuristics are still unsafe.",
        "Present-simple/linking grammar residuals are too mixed to justify a broad follow-up before Level I.",
    ]
    if validator_results["must_fix_count"] > 0 or "G" in queryable_levels or "H" in queryable_levels:
        status = "FAIL"
        recommendation = "BLOCK_FURTHER_PATCHING"
        decision = "BLOCK_FURTHER_EXPANSION"

    report = {
        "task": TASK_NAME,
        "status": status,
        "scope": {
            "levels_analyzed": ["G", "H"],
            "planning_only": True,
            "implementation_changes": False,
            "query_layer_expansion": False,
            "promotion": False,
            "i_w_processing": False,
            "cefr_or_adaptive": False,
        },
        "preflight": {
            "s6q_status": s6q_report.get("status"),
            "s6p_status": s6p_report.get("status"),
            "current_queryable_levels": queryable_levels,
            "current_s6f_must_fix_count": validator_results["must_fix_count"],
            "planning_only": True,
            "production_code_modified": False,
        },
        "source_status": {
            "s6q_status": s6q_report.get("status"),
            "s6p_patch_accepted": s6p_report.get("status") == "PASS",
        },
        "current_metrics": current_metrics,
        "residual_warning_summary": residual_warning_summary,
        "residual_theme_analysis": {
            **theme_analysis,
            "candidate_authorizations": theme_authorizations,
        },
        "residual_pattern_analysis": {
            **pattern_analysis,
            "candidate_authorizations": pattern_authorizations,
        },
        "residual_grammar_analysis": {
            **grammar_analysis,
            "candidate_authorizations": grammar_authorizations,
        },
        "candidate_authorization_table": candidate_authorization_table,
        "recommended_s6s_scope": {
            "recommendation": recommendation,
            "authorized_candidates": [
                row["candidate_id"]
                for row in candidate_authorization_table
                if row["s6r_decision"] in {"AUTHORIZE_FOR_S6S", "AUTHORIZE_NARROW_FOR_S6S"}
            ],
            "not_authorized_candidates": [
                row["candidate_id"]
                for row in candidate_authorization_table
                if row["s6r_decision"] not in {"AUTHORIZE_FOR_S6S", "AUTHORIZE_NARROW_FOR_S6S"}
            ],
            "reason": "Theme P1 families remain materially valuable and safely title-concentrated, while imperative grammar is the only clean grammar follow-up; pattern residuals are now mostly ambiguity-heavy.",
        },
        "section_heading_policy": {
            "keep_warning_only": True,
            "keep_query_exclusion": True,
            "patch_needed": False,
        },
        "human_review_policy": {
            "treat_as_derived_gate": True,
            "patch_directly": False,
        },
        "s6t_delta_qa_plan": {
            "rerun_levels": ["G", "H"],
            "metrics": [
                "unknown_theme_delta",
                "unknown_pattern_delta",
                "unknown_grammar_delta",
                "human_review_required_delta",
                "section_heading_delta",
                "malformed_or_schema_warning",
                "dialogue_or_quotation_warning",
                "count_parity",
                "schema_validation",
                "duplicate_warning_check",
                "traceability",
                "seed_query_boundary",
                "authority_boundary",
                "S6F must_fix_count",
            ],
            "pass_criteria": {
                "unknown_theme_delta": "Negative on both G and H for authorized theme families.",
                "unknown_pattern_delta": "Flat or incidental only; no pattern regression is acceptable because S6S should not touch pattern rules.",
                "unknown_grammar_delta": "Negative only for narrow imperative/procedural subset; broad present-simple bucket must remain stable.",
                "human_review_required_delta": "Negative only through indirect overlap reduction.",
                "section_heading_delta": "Stable within reviewable margin; no direct reduction target.",
                "malformed_or_schema_warning": "Must remain 0.",
                "dialogue_or_quotation_warning": "Must remain 0.",
                "count_parity": "PASS",
                "schema_validation": "PASS",
                "duplicate_warning_check": "0",
                "traceability": "PASS",
                "seed_query_boundary": "G/H remain excluded.",
                "authority_boundary": "candidate_only=PASS and promotion_allowed=PASS.",
                "S6F must_fix_count": "0",
            },
        },
        "seed_query_layer_boundary": {
            "queryable_levels": queryable_levels,
            "g_exposed": "G" in queryable_levels,
            "h_exposed": "H" in queryable_levels,
            "status": "PASS" if queryable_levels == seed_policy.get("approved_levels") else "FAIL",
        },
        "authority_boundary": {
            "candidate_only": "PASS" if drift_validation.get("candidate_only_invariant") == "PASS" else "FAIL",
            "promotion_allowed": "PASS" if drift_validation.get("promotion_allowed_invariant") == "PASS" else "FAIL",
        },
        "validator_results": validator_results,
        "command_results": commands,
        "warnings": warnings,
        "must_fix_findings": [],
        "decision": decision,
        "next_recommended_task": "RAZ-S6S_GH_P1_TARGETED_PATCH_IMPLEMENTATION" if decision == "RUN_S6S_P1_TARGETED_PATCH_IMPLEMENTATION" else "BLOCK_FURTHER_EXPANSION",
        "risk_level": "Low",
        "files_inspected": [
            stable_path(S6Q_DOC_PATH),
            stable_path(S6Q_REPORT_PATH),
            stable_path(S6P_DOC_PATH),
            stable_path(S6P_REPORT_PATH),
            stable_path(S6O_DOC_PATH),
            stable_path(S6O_REPORT_PATH),
            stable_path(S6N_DOC_PATH),
            stable_path(S6N_REPORT_PATH),
            stable_path(S6M_DOC_PATH),
            stable_path(S6M_REPORT_PATH),
            stable_path(SUMMARY_REPORT_PATH),
            stable_path(WARNING_REPORT_PATH),
            stable_path(SCHEMA_REPORT_PATH),
            stable_path(SEED_POLICY_PATH),
            stable_path(SEED_QUERY_PATH),
            stable_path(SEED_VALIDATOR_PATH),
            stable_path(DISCOVERY_BUILDER_PATH),
            stable_path(DISCOVERY_VALIDATOR_PATH),
            stable_path(DRIFT_VALIDATOR_PATH),
            stable_path(LEVEL_DISCOVERY_SUMMARY_PATH),
            stable_path(LEVEL_DISCOVERY_VALIDATION_PATH),
            stable_path(SEED_SUMMARY_PATH),
            stable_path(SEED_VALIDATION_PATH),
            stable_path(DRIFT_VALIDATION_PATH),
            stable_path(PIPELINE_PATH),
            stable_path(PIPELINE_TEST_PATH),
        ] + [stable_path(path) for level in LEVELS for path in build_level_paths(level).values()],
        "files_created": [
            stable_path(BASE_DIR / "tools" / "raz_gh_p1_targeted_patch_plan.py"),
            stable_path(BASE_DIR / "tests" / "ulga" / "test_raz_gh_p1_targeted_patch_plan.py"),
            stable_path(OUTPUT_MARKDOWN_PATH),
            stable_path(OUTPUT_JSON_PATH),
        ],
        "files_modified": [],
        "notes": {
            "count_details": count_details,
            "summary_totals": summary_report.get("totals"),
            "source_statuses": {
                "s6q": s6q_report.get("status"),
                "s6p": s6p_report.get("status"),
                "s6o": s6o_report.get("status"),
                "s6n": s6n_report.get("status"),
                "s6m": s6m_report.get("status"),
            },
            "level_discovery_status": level_discovery_summary.get("levels_by_status"),
            "seed_summary_status": seed_summary.get("status"),
        },
    }
    return report


def render_markdown(report: dict[str, Any]) -> str:
    current_metric_lines = []
    residual_summary_lines = []
    for level in LEVELS:
        metrics = report["current_metrics"][level]
        current_metric_lines.append(
            f"- `{level}`: enriched={metrics['enriched_record_count']}, unknown_theme={metrics['unknown_theme']}, unknown_pattern={metrics['unknown_pattern']}, unknown_grammar={metrics['unknown_grammar']}, section_heading={metrics['section_heading_detected']}, human_review={metrics['human_review_required']}, malformed={metrics['malformed_or_schema_warning']}, dialogue={metrics['dialogue_or_quotation_warning']}"
        )
        summary = report["residual_warning_summary"][level]
        residual_summary_lines.append(
            f"- `{level}`: unknown_theme={summary['current_unknown_theme_count']} ({summary['current_unknown_theme_rate']:.2%}), unknown_pattern={summary['current_unknown_pattern_count']} ({summary['current_unknown_pattern_rate']:.2%}), unknown_grammar={summary['current_unknown_grammar_count']} ({summary['current_unknown_grammar_rate']:.2%}), section_heading={summary['current_section_heading_detected_count']} ({summary['current_section_heading_detected_rate']:.2%}), human_review={summary['current_human_review_required_count']} ({summary['current_human_review_required_rate']:.2%})"
        )

    def render_category_block(title: str, categories: dict[str, Any]) -> str:
        lines = [f"### {title}"]
        for key, value in categories.items():
            lines.append(
                f"- `{key}`: evidence={value['evidence_count']}, levels={value['levels_observed']}, confidence={value['confidence']}, risk={value['rule_pollution_risk']}, expected_reduction={value['expected_reduction']}, priority={value['patch_priority']}"
            )
        return "\n".join(lines)

    return f"""# {TASK_NAME}

## 1. Task name

`{TASK_NAME}`

## 2. Objective

Create a focused post-S6P / post-S6Q P1 patch plan for the remaining G/H backlog without implementing taxonomy, pattern, grammar, query, or promotion changes.

## 3. Scope guardrails

- G/H only.
- Planning only. No production tagging logic changes.
- No I-W processing.
- No seed query layer expansion.
- No promotion, CEFR, adaptive, or learner-state behavior.

## 4. Preflight

- S6Q status: `{report['preflight']['s6q_status']}`
- S6P status: `{report['preflight']['s6p_status']}`
- Current queryable levels: `{report['preflight']['current_queryable_levels']}`
- Current S6F must_fix_count: `{report['preflight']['current_s6f_must_fix_count']}`
- Planning only: `{report['preflight']['planning_only']}`
- Production code modified: `{report['preflight']['production_code_modified']}`

## 5. Files inspected

{chr(10).join(f"- `{path}`" for path in report["files_inspected"])}

## 6. Files created

{chr(10).join(f"- `{path}`" for path in report["files_created"])}

## 7. Files modified

- None

## 8. Source status from S6Q

- `s6q_status = {report['source_status']['s6q_status']}`
- `s6p_patch_accepted = {report['source_status']['s6p_patch_accepted']}`

## 9. Current G/H metrics

{chr(10).join(current_metric_lines)}

## 10. Residual warning summary

{chr(10).join(residual_summary_lines)}

- `G top books`: {report['residual_warning_summary']['G']['top_residual_books_by_warning_count'][:5]}
- `H top books`: {report['residual_warning_summary']['H']['top_residual_books_by_warning_count'][:5]}
- `G top page units`: {report['residual_warning_summary']['G']['top_residual_page_units'][:5]}
- `H top page units`: {report['residual_warning_summary']['H']['top_residual_page_units'][:5]}
- `G repeated text patterns`: {report['residual_warning_summary']['G']['top_residual_repeated_text_patterns'][:5]}
- `H repeated text patterns`: {report['residual_warning_summary']['H']['top_residual_repeated_text_patterns'][:5]}

## 11. Residual unknown_theme analysis

{render_category_block("Theme Categories", report["residual_theme_analysis"]["categories"])}

## 12. Residual unknown_pattern analysis

{render_category_block("Pattern Categories", report["residual_pattern_analysis"]["categories"])}

## 13. Residual unknown_grammar analysis

{render_category_block("Grammar Categories", report["residual_grammar_analysis"]["categories"])}

## 14. Candidate authorization table

{render_candidate_table(report["candidate_authorization_table"])}

## 15. Recommended S6S scope

- Recommendation: `{report['recommended_s6s_scope']['recommendation']}`
- Authorized candidates: `{report['recommended_s6s_scope']['authorized_candidates']}`
- Not authorized candidates: `{report['recommended_s6s_scope']['not_authorized_candidates']}`
- Reason: `{report['recommended_s6s_scope']['reason']}`

## 16. Candidates explicitly not authorized

{chr(10).join(f"- `{candidate}`" for candidate in report["recommended_s6s_scope"]["not_authorized_candidates"])}

## 17. Section heading policy

- `keep_warning_only = {report['section_heading_policy']['keep_warning_only']}`
- `keep_query_exclusion = {report['section_heading_policy']['keep_query_exclusion']}`
- `patch_needed = {report['section_heading_policy']['patch_needed']}`

## 18. Human review policy

- `treat_as_derived_gate = {report['human_review_policy']['treat_as_derived_gate']}`
- `patch_directly = {report['human_review_policy']['patch_directly']}`

## 19. S6T delta QA plan

- Rerun levels: `{report['s6t_delta_qa_plan']['rerun_levels']}`
- Metrics: `{report['s6t_delta_qa_plan']['metrics']}`
- Pass criteria: `{report['s6t_delta_qa_plan']['pass_criteria']}`

## 20. Seed query layer boundary

- queryable_levels: `{report['seed_query_layer_boundary']['queryable_levels']}`
- `g_exposed = {report['seed_query_layer_boundary']['g_exposed']}`
- `h_exposed = {report['seed_query_layer_boundary']['h_exposed']}`
- status: `{report['seed_query_layer_boundary']['status']}`

## 21. Authority boundary

- `candidate_only = {report['authority_boundary']['candidate_only']}`
- `promotion_allowed = {report['authority_boundary']['promotion_allowed']}`

## 22. Validator results

- `validate_raz_level_discovery = {report['validator_results']['validate_raz_level_discovery']}`
- `validate_raz_reusable_content_seed_query_layer = {report['validator_results']['validate_raz_reusable_content_seed_query_layer']}`
- `validate_raz_downstream_discovery_drift = {report['validator_results']['validate_raz_downstream_discovery_drift']}`
- `must_fix_count = {report['validator_results']['must_fix_count']}`

## 23. Plan status

`{report['status']}`

## 24. Risk level

`{report['risk_level']}`

## 25. Decision for next stage

`{report['decision']}`

## 26. Next recommended task

`{report['next_recommended_task']}`
"""


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build G/H P1 targeted patch plan from current artifacts.")
    parser.add_argument("--command-results-json", default="", help="Optional JSON file mapping command labels to result strings.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    command_results = load_json(Path(args.command_results_json)) if args.command_results_json else {}
    report = build_report(command_results)
    write_json(OUTPUT_JSON_PATH, report)
    OUTPUT_MARKDOWN_PATH.write_text(render_markdown(report) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": report["status"],
                "decision": report["decision"],
                "recommendation": report["recommended_s6s_scope"]["recommendation"],
                "output_json": stable_path(OUTPUT_JSON_PATH),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report["status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
