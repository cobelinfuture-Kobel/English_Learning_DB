from __future__ import annotations

import json
import re
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any

from ulga.builders import build_raz_level_discovery as level_discovery


BASE_DIR = Path(__file__).resolve().parents[2]
DERIVED_ROOT = BASE_DIR / "raz_output_jsons" / "derived"
SUMMARY_REPORT_PATH = BASE_DIR / "ulga" / "reports" / "raz_reusable_content_seed_query_layer_summary.json"
VALIDATION_REPORT_PATH = BASE_DIR / "ulga" / "reports" / "raz_reusable_content_seed_query_layer_validation.json"

MAX_LIMIT = 100
DEFAULT_LIMIT = 20
LEVELS = level_discovery.ALL_VALID_LEVEL_CODES
RECORD_TYPES = {"sentence", "page_unit", "reuse_unit"}
QUERY_TYPES = {
    "find_reusable_seeds",
    "find_short_reading_seeds",
    "find_exercise_seeds",
    "find_dialogue_rewrite_seeds",
    "find_picture_prompt_seeds",
    "find_theme_seeds",
    "explain_seed",
}

FORBIDDEN_REQUEST_KEYS = {
    "learner_id",
    "student_id",
    "mastery",
    "learner_state",
    "adaptive",
    "personalized",
    "assessment_feedback",
    "event_log",
    "runtime_profile",
    "promote_to_authority",
    "generate_exercise",
    "generate_dialogue",
    "generate_reading",
}

REQUIRED_WARNING_CODES = {
    "UNKNOWN_THEME_EXCLUDED_BY_DEFAULT",
    "UNKNOWN_THEME_INCLUDED_BY_REQUEST",
    "SECTION_HEADING_EXCLUDED_BY_DEFAULT",
    "HUMAN_REVIEW_REQUIRED_EXCLUDED_BY_DEFAULT",
    "GRAMMAR_FILTER_IS_RULE_BASED",
    "VOCABULARY_FILTER_IS_RULE_BASED",
    "CEFR_NOT_AUTHORITY_LINKED",
    "LIMIT_CLAMPED_TO_MAXIMUM",
    "NO_RESULTS_FOUND",
    "STATIC_ONLY_REQUIRED",
    "ADAPTIVE_FIELD_REJECTED",
    "GENERATED_CONTENT_NOT_RETURNED",
    "AUTHORITY_PROMOTION_NOT_ALLOWED",
    "UNKNOWN_QUERY_TYPE",
    "SEED_NOT_FOUND",
    "INVALID_RECORD_TYPE_FILTER",
    "INVALID_LEVEL_FILTER",
}

REQUIRED_SEED_CARD_FIELDS = {
    "seed_id",
    "seed_type",
    "source",
    "text_preview",
    "text",
    "content_unit",
    "theme",
    "linguistic",
    "pedagogy",
    "qa",
    "ranking",
}
LEVEL_FILTER_PATTERN = re.compile(r"^[A-Z]$")


class QueryValidationError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _read_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"required artifact missing: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"required artifact missing: {path}")
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _stable_path(path: Path) -> str:
    try:
        return str(path.relative_to(BASE_DIR)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _listify(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _text_preview(text: str, max_len: int = 120) -> str:
    clean = " ".join((text or "").split())
    if len(clean) <= max_len:
        return clean
    return clean[: max_len - 3].rstrip() + "..."


def _collect_forbidden_keys(value: Any, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            key_path = f"{prefix}.{key}" if prefix else str(key)
            if key in FORBIDDEN_REQUEST_KEYS:
                found.append(key_path)
            found.extend(_collect_forbidden_keys(nested, key_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(_collect_forbidden_keys(item, f"{prefix}[{index}]"))
    return found


def _level_of(record: dict[str, Any]) -> str | None:
    return record.get("level") or record.get("source_tags", {}).get("raz_level")


def _seed_id_for(record: dict[str, Any], record_type: str) -> str:
    if record_type == "sentence":
        return record.get("candidate_id") or record.get("source_tags", {}).get("candidate_id")
    if record_type == "page_unit":
        return record.get("page_unit_id") or record.get("source_tags", {}).get("page_unit_id")
    if record_type == "reuse_unit":
        return record.get("reuse_unit_id") or record.get("source_page_unit_id")
    raise ValueError(f"unknown record_type: {record_type}")


def _source_for(record: dict[str, Any], record_type: str, source_file: Path) -> dict[str, Any]:
    source_tags = deepcopy(record.get("source_tags", {}))
    level = _level_of(record)
    source = {
        "source": source_tags.get("source", "RAZ"),
        "source_type": source_tags.get("source_type", "raz_audio_timeline"),
        "extraction_method": source_tags.get("extraction_method", "bookAudioContent"),
        "extractor_version": source_tags.get("extractor_version"),
        "raz_level": level,
        "book_id": record.get("book_id") or source_tags.get("book_id"),
        "book_title": record.get("title") or source_tags.get("book_title"),
        "page_number": record.get("page_number") or source_tags.get("page_number"),
        "page_unit_id": record.get("page_unit_id") or record.get("source_page_unit_id") or source_tags.get("page_unit_id"),
        "candidate_id": record.get("candidate_id") or source_tags.get("candidate_id"),
        "raw_file_path": source_tags.get("raw_file_path"),
        "derived_file_path": _stable_path(source_file),
    }
    if record_type == "reuse_unit":
        source["reuse_unit_id"] = record.get("reuse_unit_id")
        source["source_page_unit_id"] = record.get("source_page_unit_id")
        source["source_sentence_candidate_ids"] = record.get("source_sentence_candidate_ids", [])
    return source


def _content_unit_for(record: dict[str, Any], record_type: str) -> dict[str, Any]:
    content = deepcopy(record.get("content_unit_tags", {}))
    content.setdefault("content_unit_type", record_type)
    content.setdefault("sentence_count", record.get("sentence_count", 1))
    content.setdefault("has_heading", bool(content.get("is_heading")))
    content.setdefault("has_direct_speech", bool(content.get("is_direct_speech")))
    content.setdefault("has_sequence", False)
    content.setdefault("record_type", record_type)
    return content


def _theme_for(record: dict[str, Any]) -> dict[str, Any]:
    theme = deepcopy(record.get("theme_tags", {}))
    theme.setdefault("mapped_theme", "Unknown")
    theme.setdefault("primary_theme", theme.get("mapped_theme", "Unknown"))
    theme.setdefault("subthemes", [])
    theme.setdefault("theme_confidence", 0.0)
    theme.setdefault("theme_source", "missing")
    return theme


def _linguistic_for(record: dict[str, Any]) -> dict[str, Any]:
    linguistic = deepcopy(record.get("linguistic_tags", {}))
    linguistic.setdefault("cefr_estimate", None)
    linguistic.setdefault("grammar_tags", [])
    linguistic.setdefault("sentence_pattern_tags", [])
    linguistic.setdefault("vocabulary_tags", [])
    linguistic.setdefault("chunk_tags", [])
    return linguistic


def _pedagogy_for(record: dict[str, Any]) -> dict[str, Any]:
    pedagogy = deepcopy(record.get("pedagogical_tags", {}))
    pedagogy.setdefault("skill_area", [])
    pedagogy.setdefault("question_type_candidates", [])
    pedagogy.setdefault("exercise_seed", False)
    pedagogy.setdefault("assessment_seed", False)
    return pedagogy


def _reuse_for(record: dict[str, Any]) -> dict[str, Any]:
    reuse = deepcopy(record.get("reuse_tags", {}))
    reuse.setdefault("is_reusable_unit", True)
    reuse.setdefault("reusability_tags", [])
    reuse.setdefault("derivation_potential", {})
    return reuse


def _qa_for(record: dict[str, Any]) -> dict[str, Any]:
    qa = deepcopy(record.get("qa_tags", {}))
    qa.setdefault("authority_status", record.get("authority_status", "candidate_only"))
    qa.setdefault("promotion_status", record.get("promotion_status", "not_promoted"))
    qa.setdefault("review_status", record.get("review_status", "pending"))
    qa.setdefault("tagging_status", "auto_tagged")
    qa.setdefault("needs_human_review", False)
    qa.setdefault("final_eligible", False)
    qa.setdefault("warnings", [])
    qa.setdefault("confidence", {})
    return qa


def make_seed_card(record: dict[str, Any], record_type: str, source_file: Path, include_text: bool = True) -> dict[str, Any]:
    text = record.get("text") or record.get("clean_text") or ""
    seed_id = _seed_id_for(record, record_type)
    source = _source_for(record, record_type, source_file)
    content = _content_unit_for(record, record_type)
    theme = _theme_for(record)
    linguistic = _linguistic_for(record)
    pedagogy = _pedagogy_for(record)
    reuse = _reuse_for(record)
    qa = _qa_for(record)
    warnings = list(dict.fromkeys(qa.get("warnings", [])))
    return {
        "seed_id": seed_id,
        "seed_type": record_type,
        "source": source,
        "text_preview": _text_preview(text),
        "text": text if include_text else None,
        "content_unit": content,
        "theme": theme,
        "linguistic": linguistic,
        "pedagogy": {
            "skill_area": pedagogy.get("skill_area", []),
            "question_type_candidates": pedagogy.get("question_type_candidates", []),
            "reusability_tags": reuse.get("reusability_tags", []),
            "derivation_potential": reuse.get("derivation_potential", {}),
            "exercise_seed": pedagogy.get("exercise_seed", False),
            "assessment_seed": pedagogy.get("assessment_seed", False),
        },
        "qa": {
            "authority_status": qa.get("authority_status"),
            "promotion_status": qa.get("promotion_status"),
            "review_status": qa.get("review_status"),
            "tagging_status": qa.get("tagging_status"),
            "final_eligible": qa.get("final_eligible"),
            "needs_human_review": qa.get("needs_human_review"),
            "warnings": warnings,
            "confidence": qa.get("confidence", {}),
        },
        "ranking": {
            "seed_score": 0.0,
            "score_reasons": [],
        },
    }


def _discover_enriched_files(derived_root: Path) -> list[tuple[str, str, Path]]:
    files: list[tuple[str, str, Path]] = []
    for level in level_discovery.discover_queryable_levels(derived_root=derived_root):
        base = derived_root / f"Level_{level}" / "enriched"
        files.extend(
            [
                (level, "sentence", base / f"raz_{level}_sentence_enriched.jsonl"),
                (level, "page_unit", base / f"raz_{level}_page_unit_enriched.json"),
                (level, "reuse_unit", base / f"raz_{level}_reuse_unit_enriched.json"),
            ]
        )
    return files


def load_seed_cards(derived_root: Path | None = None, include_text: bool = True) -> list[dict[str, Any]]:
    root = derived_root or DERIVED_ROOT
    cards: list[dict[str, Any]] = []
    for _level, record_type, path in _discover_enriched_files(root):
        if not path.exists():
            continue
        records = _read_jsonl(path) if path.suffix == ".jsonl" else _read_json(path)
        for record in records:
            cards.append(make_seed_card(record, record_type, path, include_text=include_text))
    return cards


@lru_cache(maxsize=4)
def _load_seed_cards_cached(root_str: str, include_text: bool = True) -> tuple[dict[str, Any], ...]:
    return tuple(load_seed_cards(Path(root_str), include_text=include_text))


def load_cached_seed_cards(derived_root: Path | None = None, include_text: bool = True) -> list[dict[str, Any]]:
    root = derived_root or DERIVED_ROOT
    return [deepcopy(card) for card in _load_seed_cards_cached(str(root.resolve()), include_text)]


def validate_seed_request(request: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(request, dict):
        raise QueryValidationError("UNKNOWN_QUERY_TYPE", "request must be a dictionary")
    if request.get("static_only", True) is not True:
        raise QueryValidationError("STATIC_ONLY_REQUIRED", "RAZ seed query layer is static-only")
    forbidden = _collect_forbidden_keys(request)
    if forbidden:
        raise QueryValidationError("ADAPTIVE_FIELD_REJECTED", f"forbidden request keys: {forbidden}")
    query_type = request.get("query_type")
    if query_type not in QUERY_TYPES:
        raise QueryValidationError("UNKNOWN_QUERY_TYPE", f"unknown query_type: {query_type}")
    filters = request.get("filters", {}) or {}
    record_types = set(_listify(filters.get("record_types")))
    if record_types and not record_types <= RECORD_TYPES:
        raise QueryValidationError("INVALID_RECORD_TYPE_FILTER", f"invalid record_types: {sorted(record_types - RECORD_TYPES)}")
    levels = {str(level).upper() for level in _listify(filters.get("levels"))}
    invalid_levels = sorted(level for level in levels if not LEVEL_FILTER_PATTERN.fullmatch(level))
    if invalid_levels:
        raise QueryValidationError("INVALID_LEVEL_FILTER", f"invalid levels: {invalid_levels}")
    limit = request.get("limit", DEFAULT_LIMIT)
    try:
        limit_int = int(limit)
    except (TypeError, ValueError):
        limit_int = DEFAULT_LIMIT
    offset = request.get("offset", 0)
    try:
        offset_int = max(0, int(offset))
    except (TypeError, ValueError):
        offset_int = 0
    warnings: list[str] = []
    if limit_int > MAX_LIMIT:
        limit_int = MAX_LIMIT
        warnings.append("LIMIT_CLAMPED_TO_MAXIMUM")
    if limit_int < 0:
        limit_int = 0
    return {
        "query_type": query_type,
        "filters": filters,
        "ranking_policy": request.get("ranking_policy", {}) or {},
        "limit": limit_int,
        "offset": offset_int,
        "include_text": bool(request.get("include_text", True)),
        "include_explanation": bool(request.get("include_explanation", False)),
        "warnings": warnings,
    }


def _apply_query_defaults(query_type: str, filters: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(filters)
    if query_type == "find_short_reading_seeds":
        out.setdefault("record_types", ["page_unit", "reuse_unit"])
        out.setdefault("reusability_tags", ["short_reading_seed"])
        out.setdefault("min_sentence_count", 2)
    elif query_type == "find_exercise_seeds":
        out.setdefault("reusability_tags", ["exercise_seed"])
    elif query_type == "find_dialogue_rewrite_seeds":
        out.setdefault("record_types", ["page_unit", "reuse_unit"])
        out.setdefault("reusability_tags", ["dialogue_rewrite_seed"])
    elif query_type == "find_picture_prompt_seeds":
        out.setdefault("record_types", ["sentence", "page_unit"])
        out.setdefault("levels", ["A", "B", "C"])
        out.setdefault("reusability_tags", ["picture_prompt_seed"])
    elif query_type == "find_theme_seeds":
        out.setdefault("include_unknown_theme", False)
    return out


def _has_any(card_values: list[Any], requested: list[Any]) -> bool:
    if not requested:
        return True
    return bool(set(card_values) & set(requested))


def _record_matches(card: dict[str, Any], filters: dict[str, Any]) -> tuple[bool, list[str]]:
    warnings: list[str] = []
    level = card["source"].get("raz_level")
    mapped_theme = card["theme"].get("mapped_theme")
    qa_warnings = set(card["qa"].get("warnings", []))
    include_unknown_theme = bool(filters.get("include_unknown_theme", False))
    include_heading = bool(filters.get("include_heading", False))
    include_human_review = bool(filters.get("include_human_review_required", False))
    grammar_strict = bool(filters.get("grammar_strict", False))

    if not include_unknown_theme and mapped_theme == "Unknown":
        return False, ["UNKNOWN_THEME_EXCLUDED_BY_DEFAULT"]
    if include_unknown_theme and mapped_theme == "Unknown":
        warnings.append("UNKNOWN_THEME_INCLUDED_BY_REQUEST")

    is_heading = bool(card["content_unit"].get("is_heading") or card["content_unit"].get("has_heading"))
    if not include_heading and (is_heading or "section_heading_detected" in qa_warnings):
        return False, ["SECTION_HEADING_EXCLUDED_BY_DEFAULT"]

    if not include_human_review and card["qa"].get("needs_human_review"):
        return False, ["HUMAN_REVIEW_REQUIRED_EXCLUDED_BY_DEFAULT"]

    if grammar_strict and "unknown_grammar" in qa_warnings:
        return False, ["GRAMMAR_FILTER_IS_RULE_BASED"]

    levels = _listify(filters.get("levels"))
    if levels and level not in levels:
        return False, warnings

    record_types = _listify(filters.get("record_types"))
    if record_types and card["seed_type"] not in record_types:
        return False, warnings

    mapped_themes = _listify(filters.get("mapped_themes"))
    if mapped_themes and mapped_theme not in mapped_themes:
        return False, warnings

    book_ids = [str(x) for x in _listify(filters.get("book_ids") or filters.get("book_id"))]
    if book_ids and str(card["source"].get("book_id")) not in book_ids:
        return False, warnings

    seed_ids = _listify(filters.get("seed_ids"))
    if seed_ids and card["seed_id"] not in seed_ids:
        return False, warnings

    skill_area = _listify(filters.get("skill_area"))
    if skill_area and not _has_any(card["pedagogy"].get("skill_area", []), skill_area):
        return False, warnings

    question_types = _listify(filters.get("question_type_candidates"))
    if question_types and not _has_any(card["pedagogy"].get("question_type_candidates", []), question_types):
        return False, warnings

    reusability_tags = _listify(filters.get("reusability_tags"))
    if reusability_tags and not _has_any(card["pedagogy"].get("reusability_tags", []), reusability_tags):
        return False, warnings

    grammar_tags = _listify(filters.get("grammar_tags"))
    if grammar_tags:
        warnings.append("GRAMMAR_FILTER_IS_RULE_BASED")
        if not _has_any(card["linguistic"].get("grammar_tags", []), grammar_tags):
            return False, warnings

    vocabulary_words = [str(x).lower() for x in _listify(filters.get("vocabulary_words"))]
    if vocabulary_words:
        warnings.append("VOCABULARY_FILTER_IS_RULE_BASED")
        words = [entry.get("normalized_word") for entry in card["linguistic"].get("vocabulary_tags", []) if isinstance(entry, dict)]
        if not (set(vocabulary_words) & set(words)):
            return False, warnings

    min_sentence_count = filters.get("min_sentence_count")
    max_sentence_count = filters.get("max_sentence_count")
    sentence_count = card["content_unit"].get("sentence_count") or 1
    if min_sentence_count is not None and sentence_count < int(min_sentence_count):
        return False, warnings
    if max_sentence_count is not None and sentence_count > int(max_sentence_count):
        return False, warnings

    for flag in ["has_direct_speech", "has_sequence"]:
        expected = filters.get(flag)
        if expected is not None and bool(card["content_unit"].get(flag)) is not bool(expected):
            return False, warnings

    return True, warnings


def _score_card(card: dict[str, Any], filters: dict[str, Any], ranking_policy: dict[str, Any]) -> dict[str, Any]:
    score = 1.0
    reasons: list[str] = ["base_static_candidate_seed"]

    requested_reuse = set(_listify(filters.get("reusability_tags")))
    reuse_matches = requested_reuse & set(card["pedagogy"].get("reusability_tags", []))
    if reuse_matches:
        score += len(reuse_matches) * 2.0
        reasons.append(f"reusability_match:{','.join(sorted(reuse_matches))}")

    requested_questions = set(_listify(filters.get("question_type_candidates")))
    question_matches = requested_questions & set(card["pedagogy"].get("question_type_candidates", []))
    if question_matches:
        score += len(question_matches) * 1.5
        reasons.append(f"question_type_match:{','.join(sorted(question_matches))}")

    requested_skills = set(_listify(filters.get("skill_area")))
    skill_matches = requested_skills & set(card["pedagogy"].get("skill_area", []))
    if skill_matches:
        score += len(skill_matches) * 0.8
        reasons.append(f"skill_match:{','.join(sorted(skill_matches))}")

    requested_themes = set(_listify(filters.get("mapped_themes")))
    if requested_themes and card["theme"].get("mapped_theme") in requested_themes:
        score += 2.0
        reasons.append("theme_exact_match")

    theme_confidence = float(card["theme"].get("theme_confidence") or 0.0)
    if ranking_policy.get("prefer_higher_theme_confidence", True):
        score += theme_confidence
        reasons.append(f"theme_confidence:{theme_confidence:.2f}")

    sentence_count = int(card["content_unit"].get("sentence_count") or 1)
    if ranking_policy.get("prefer_multi_sentence", True) and sentence_count >= 2:
        score += min(1.5, sentence_count * 0.25)
        reasons.append(f"multi_sentence_count:{sentence_count}")

    if ranking_policy.get("prefer_reuse_unit", True) and card["seed_type"] == "reuse_unit":
        score += 0.5
        reasons.append("reuse_unit_preferred")

    warning_count = len(card["qa"].get("warnings", []))
    if ranking_policy.get("prefer_lower_warning_count", True) and warning_count:
        score -= warning_count * 0.35
        reasons.append(f"warning_penalty:{warning_count}")

    if card["theme"].get("mapped_theme") == "Unknown":
        score -= 1.0
        reasons.append("unknown_theme_penalty")

    card = deepcopy(card)
    card["ranking"] = {
        "seed_score": round(score, 4),
        "score_reasons": reasons,
    }
    return card


def _strip_text_if_needed(card: dict[str, Any], include_text: bool) -> dict[str, Any]:
    if include_text:
        return card
    out = deepcopy(card)
    out["text"] = None
    return out


def _response_metadata(query_type: str, filters: dict[str, Any], warnings: list[str], limit: int, offset: int) -> dict[str, Any]:
    return {
        "query_type": query_type,
        "static_only": True,
        "adaptive_enabled": False,
        "authority_promotion_allowed": False,
        "generated_content_returned": False,
        "unknown_theme_policy": "include_by_request" if filters.get("include_unknown_theme") else "exclude_by_default",
        "section_heading_policy": "include_by_request" if filters.get("include_heading") else "exclude_by_default",
        "limit": limit,
        "offset": offset,
        "warnings": sorted(set(warnings)),
    }


def _error_response(code: str, message: str, query_type: str | None = None) -> dict[str, Any]:
    return {
        "query_metadata": {
            "query_type": query_type,
            "static_only": True,
            "adaptive_enabled": False,
            "authority_promotion_allowed": False,
            "generated_content_returned": False,
            "warnings": [code],
        },
        "error": {
            "code": code,
            "message": message,
        },
        "results": [],
    }


def query_reusable_content_seeds(request: dict[str, Any], derived_root: Path | None = None) -> dict[str, Any]:
    query_type = request.get("query_type") if isinstance(request, dict) else None
    try:
        normalized = validate_seed_request(request)
    except QueryValidationError as exc:
        return _error_response(exc.code, exc.message, query_type=query_type)

    filters = _apply_query_defaults(normalized["query_type"], normalized["filters"])
    warnings: list[str] = list(normalized["warnings"])
    warnings.extend(["GENERATED_CONTENT_NOT_RETURNED", "AUTHORITY_PROMOTION_NOT_ALLOWED", "CEFR_NOT_AUTHORITY_LINKED"])

    cards = load_cached_seed_cards(derived_root=derived_root, include_text=True)
    if normalized["query_type"] == "explain_seed":
        seed_id = filters.get("seed_id") or request.get("seed_id")
        found = [card for card in cards if card["seed_id"] == seed_id]
        if not found:
            return _error_response("SEED_NOT_FOUND", f"seed not found: {seed_id}", query_type="explain_seed")
        scored = _score_card(found[0], filters, normalized["ranking_policy"])
        result = _strip_text_if_needed(scored, normalized["include_text"])
        return {
            "query_metadata": _response_metadata("explain_seed", filters, warnings, 1, 0),
            "result_count": 1,
            "results": [result],
        }

    matched: list[dict[str, Any]] = []
    excluded_warning_counts: dict[str, int] = {}
    for card in cards:
        ok, local_warnings = _record_matches(card, filters)
        if ok:
            warnings.extend(local_warnings)
            matched.append(_score_card(card, filters, normalized["ranking_policy"]))
        else:
            for warning in local_warnings:
                excluded_warning_counts[warning] = excluded_warning_counts.get(warning, 0) + 1

    matched.sort(key=lambda item: (item["ranking"]["seed_score"], item["source"].get("raz_level") or "", item["seed_id"]), reverse=True)
    start = normalized["offset"]
    end = start + normalized["limit"]
    results = [_strip_text_if_needed(card, normalized["include_text"]) for card in matched[start:end]]

    if not results:
        warnings.append("NO_RESULTS_FOUND")

    metadata = _response_metadata(normalized["query_type"], filters, warnings, normalized["limit"], normalized["offset"])
    metadata["filters_applied"] = filters
    metadata["excluded_warning_counts"] = excluded_warning_counts
    metadata["total_matches_before_paging"] = len(matched)
    return {
        "query_metadata": metadata,
        "result_count": len(results),
        "results": results,
    }


def find_reusable_seeds(filters: dict[str, Any] | None = None, limit: int = DEFAULT_LIMIT, offset: int = 0, derived_root: Path | None = None) -> dict[str, Any]:
    return query_reusable_content_seeds({"query_type": "find_reusable_seeds", "filters": filters or {}, "limit": limit, "offset": offset, "static_only": True}, derived_root=derived_root)


def find_short_reading_seeds(filters: dict[str, Any] | None = None, limit: int = DEFAULT_LIMIT, offset: int = 0, derived_root: Path | None = None) -> dict[str, Any]:
    return query_reusable_content_seeds({"query_type": "find_short_reading_seeds", "filters": filters or {}, "limit": limit, "offset": offset, "static_only": True}, derived_root=derived_root)


def find_exercise_seeds(filters: dict[str, Any] | None = None, limit: int = DEFAULT_LIMIT, offset: int = 0, derived_root: Path | None = None) -> dict[str, Any]:
    return query_reusable_content_seeds({"query_type": "find_exercise_seeds", "filters": filters or {}, "limit": limit, "offset": offset, "static_only": True}, derived_root=derived_root)


def find_dialogue_rewrite_seeds(filters: dict[str, Any] | None = None, limit: int = DEFAULT_LIMIT, offset: int = 0, derived_root: Path | None = None) -> dict[str, Any]:
    return query_reusable_content_seeds({"query_type": "find_dialogue_rewrite_seeds", "filters": filters or {}, "limit": limit, "offset": offset, "static_only": True}, derived_root=derived_root)


def find_picture_prompt_seeds(filters: dict[str, Any] | None = None, limit: int = DEFAULT_LIMIT, offset: int = 0, derived_root: Path | None = None) -> dict[str, Any]:
    return query_reusable_content_seeds({"query_type": "find_picture_prompt_seeds", "filters": filters or {}, "limit": limit, "offset": offset, "static_only": True}, derived_root=derived_root)


def find_theme_seeds(mapped_themes: list[str] | str, filters: dict[str, Any] | None = None, limit: int = DEFAULT_LIMIT, offset: int = 0, derived_root: Path | None = None) -> dict[str, Any]:
    merged = deepcopy(filters or {})
    merged["mapped_themes"] = _listify(mapped_themes)
    return query_reusable_content_seeds({"query_type": "find_theme_seeds", "filters": merged, "limit": limit, "offset": offset, "static_only": True}, derived_root=derived_root)


def explain_seed(seed_id: str, include_text: bool = True, derived_root: Path | None = None) -> dict[str, Any]:
    return query_reusable_content_seeds({"query_type": "explain_seed", "seed_id": seed_id, "filters": {"seed_id": seed_id}, "limit": 1, "include_text": include_text, "static_only": True}, derived_root=derived_root)


def build_seed_coverage_matrix(cards: list[dict[str, Any]] | None = None, derived_root: Path | None = None) -> dict[str, Any]:
    rows = cards or load_cached_seed_cards(derived_root=derived_root, include_text=False)
    discovered_levels = sorted({card["source"].get("raz_level") for card in rows if card["source"].get("raz_level")})
    if not discovered_levels and derived_root is not None:
        discovered_levels = level_discovery.discover_queryable_levels(derived_root=derived_root)
    matrix: dict[str, Any] = {level: {"sentence": 0, "page_unit": 0, "reuse_unit": 0, "total": 0} for level in discovered_levels}
    for card in rows:
        level = card["source"].get("raz_level")
        if level not in matrix:
            matrix[level] = {"sentence": 0, "page_unit": 0, "reuse_unit": 0, "total": 0}
        seed_type = card["seed_type"]
        matrix[level][seed_type] += 1
        matrix[level]["total"] += 1
    return matrix


def generate_summary_report(validation_summary: dict[str, Any] | None = None, write_report: bool = True, derived_root: Path | None = None) -> dict[str, Any]:
    cards = load_cached_seed_cards(derived_root=derived_root, include_text=False)
    by_type: dict[str, int] = {record_type: 0 for record_type in sorted(RECORD_TYPES)}
    by_theme: dict[str, int] = {}
    warning_counts: dict[str, int] = {}
    for card in cards:
        by_type[card["seed_type"]] += 1
        theme = card["theme"].get("mapped_theme", "Unknown")
        by_theme[theme] = by_theme.get(theme, 0) + 1
        for warning in card["qa"].get("warnings", []):
            warning_counts[warning] = warning_counts.get(warning, 0) + 1
    summary = {
        "task": "RAZ-S6A_ReusableContentSeed_QueryLayer_Implementation",
        "status": "PASS" if validation_summary is None or validation_summary.get("status") == "PASS" else "CHECK_REQUIRED",
        "derived_root": _stable_path(derived_root or DERIVED_ROOT),
        "total_seed_cards": len(cards),
        "by_record_type": by_type,
        "by_level": build_seed_coverage_matrix(cards=cards),
        "top_mapped_themes": sorted(by_theme.items(), key=lambda item: item[1], reverse=True)[:20],
        "qa_warning_counts": dict(sorted(warning_counts.items(), key=lambda item: item[1], reverse=True)),
        "public_query_functions": sorted(QUERY_TYPES),
        "guardrails": {
            "static_only": True,
            "authority_promotion_allowed": False,
            "generated_content_returned": False,
            "unknown_theme_excluded_by_default": True,
            "section_heading_excluded_by_default": True,
            "human_review_required_excluded_by_default": True,
            "max_limit": MAX_LIMIT,
        },
        "validation_summary": validation_summary or {},
    }
    if write_report:
        SUMMARY_REPORT_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


__all__ = [
    "MAX_LIMIT",
    "QUERY_TYPES",
    "RECORD_TYPES",
    "REQUIRED_WARNING_CODES",
    "REQUIRED_SEED_CARD_FIELDS",
    "SUMMARY_REPORT_PATH",
    "VALIDATION_REPORT_PATH",
    "build_seed_coverage_matrix",
    "explain_seed",
    "find_dialogue_rewrite_seeds",
    "find_exercise_seeds",
    "find_picture_prompt_seeds",
    "find_reusable_seeds",
    "find_short_reading_seeds",
    "find_theme_seeds",
    "generate_summary_report",
    "load_seed_cards",
    "make_seed_card",
    "query_reusable_content_seeds",
    "validate_seed_request",
]
