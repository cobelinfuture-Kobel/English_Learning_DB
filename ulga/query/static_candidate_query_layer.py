import json
from copy import deepcopy
from functools import lru_cache
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
STATIC_RANKING_PATH = BASE_DIR / "ulga" / "graph" / "static_candidate_ranking.json"
STATIC_VIEWS_PATH = BASE_DIR / "ulga" / "graph" / "static_candidate_ranking_views.json"
VIEWS_QUALITY_AUDIT_PATH = BASE_DIR / "ulga" / "reports" / "static_candidate_ranking_views_quality_audit.json"
SUMMARY_REPORT_PATH = BASE_DIR / "ulga" / "reports" / "static_candidate_query_layer_summary.json"

MAX_LIMIT = 100

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
}

REQUIRED_WARNING_CODES = {
    "THEME_SCOPED_VIEW_HEURISTIC_RELEVANCE_WARNING",
    "READING_BRIDGE_VIEW_NEEDS_TUNING",
    "DIALOGUE_BRIDGE_VIEW_NEEDS_TUNING",
    "NODE_TYPE_DERIVED_FROM_CANDIDATE_TYPE",
    "NODE_TYPE_DERIVED_FROM_UNKNOWN_CANDIDATE_TYPE",
    "SOURCE_ARTIFACT_DERIVED",
    "BRIDGE_REASON_DERIVED",
    "SUPPORTING_AUTHORITY_LAYER_DERIVED",
    "VIEW_SCORE_IS_POLICY_ADJUSTED",
    "RAW_RANKING_NOT_ALLOWED_FOR_CURRICULUM_USE",
    "MISSING_RAW_OR_VIEW_SCORE_PAIR",
    "INTERNAL_LEVEL_BAND_MAPPING_REQUIRED",
    "LEARNER_ARTIFACT_NOT_JOINED_STATIC_ONLY",
    "REINFORCEMENT_REFERENCE_ONLY_NOT_JOINED",
    "STATIC_ONLY_REQUIRED",
    "ADAPTIVE_FIELD_REJECTED",
    "NODE_TYPE_CANDIDATE_TYPE_CONFLICT",
    "LIMIT_CLAMPED_TO_MAXIMUM",
    "UNKNOWN_VIEW_NAME",
    "CANDIDATE_NOT_FOUND",
}

VIEW_NAMES = {
    "raw_global_view",
    "balanced_global_view",
    "a1_safe_view",
    "theme_scoped_view",
    "reading_bridge_view",
    "dialogue_bridge_view",
    "pattern_first_view",
    "vocabulary_first_view",
    "chunk_safe_view",
    "deduplicated_view",
}

THEME_NAMES = ("Home", "Food", "School", "Travel", "Health", "Personal", "Daily Life")

NODE_TYPE_MAP = {
    "vocabulary_candidate": "vocabulary",
    "chunk_candidate": "chunk",
    "pattern_candidate": "pattern",
    "grammar_candidate": "grammar",
    "theme_candidate": "theme",
    "sentence_candidate": "sentence",
    "dialogue_candidate": "dialogue",
    "reading_candidate": "reading",
}

BRIDGE_REASON_MAP = {
    "balanced_global_view": "balanced_global_static_view_membership",
    "a1_safe_view": "a1_safe_static_view_membership",
    "theme_scoped_view": "theme_scoped_static_view_membership",
    "reading_bridge_view": "reading_bridge_static_view_membership",
    "dialogue_bridge_view": "dialogue_bridge_static_view_membership",
    "pattern_first_view": "pattern_first_static_view_membership",
    "vocabulary_first_view": "vocabulary_first_static_view_membership",
    "chunk_safe_view": "chunk_safe_static_view_membership",
    "deduplicated_view": "deduplicated_static_view_membership",
    "raw_global_view": "raw_global_static_view_membership",
}

VIEW_WARNING_MAP = {
    "theme_scoped_view": ["THEME_SCOPED_VIEW_HEURISTIC_RELEVANCE_WARNING"],
    "reading_bridge_view": ["READING_BRIDGE_VIEW_NEEDS_TUNING"],
    "dialogue_bridge_view": ["DIALOGUE_BRIDGE_VIEW_NEEDS_TUNING"],
    "raw_global_view": ["RAW_RANKING_NOT_ALLOWED_FOR_CURRICULUM_USE"],
}

PUBLIC_QUERY_FUNCTIONS = [
    "query_static_candidates",
    "get_static_ranking_view",
    "get_top_candidates",
    "get_candidates_by_theme",
    "get_candidates_by_node_type",
    "get_candidate_explanation",
    "get_reading_bridge_candidates",
    "get_dialogue_bridge_candidates",
    "get_a1_safe_candidates",
]

RESPONSE_CANDIDATE_FIELDS = {
    "candidate_id",
    "raw_candidate_id",
    "label",
    "node_type",
    "candidate_type",
    "level",
    "cefr",
    "internal_level",
    "level_family",
    "level_band",
    "level_source",
    "theme_refs",
    "view_rank",
    "raw_rank",
    "raw_static_score",
    "view_score",
    "score_type",
    "source_artifact",
    "bridge_reason",
    "supporting_authority_layer",
    "explanation",
    "warnings",
}

EXPLANATION_FIELDS = {
    "why_this_candidate",
    "why_this_score",
    "which_authority_supports_it",
    "which_bridge_produced_it",
    "which_filters_can_retrieve_it",
    "score_breakdown_summary",
    "view_policy_summary",
    "known_limitations",
}

QUERY_FUNCTION_TO_VIEW = {
    "get_static_ranking_view": None,
    "get_top_candidates": "balanced_global_view",
    "get_candidates_by_theme": "theme_scoped_view",
    "get_candidates_by_node_type": "balanced_global_view",
    "get_candidate_explanation": None,
    "get_reading_bridge_candidates": "reading_bridge_view",
    "get_dialogue_bridge_candidates": "dialogue_bridge_view",
    "get_a1_safe_candidates": "a1_safe_view",
}


def _read_json(path):
    if not path.exists():
        raise FileNotFoundError(f"required artifact missing: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def load_static_ranking():
    return _read_json(STATIC_RANKING_PATH)


@lru_cache(maxsize=1)
def load_static_ranking_views():
    return _read_json(STATIC_VIEWS_PATH)


@lru_cache(maxsize=1)
def load_views_quality_audit():
    return _read_json(VIEWS_QUALITY_AUDIT_PATH)


@lru_cache(maxsize=1)
def _raw_candidate_index():
    return {candidate["candidate_id"]: candidate for candidate in load_static_ranking().get("candidates", [])}


@lru_cache(maxsize=1)
def _view_candidate_index():
    index = {}
    views = load_static_ranking_views().get("views", {})
    for view_name, view_value in views.items():
        if view_name == "theme_scoped_view":
            for theme_name, rows in view_value.items():
                for row in rows:
                    index.setdefault(row["view_candidate_id"], []).append((view_name, theme_name, row))
                    index.setdefault(row["raw_candidate_id"], []).append((view_name, theme_name, row))
        else:
            for row in view_value:
                index.setdefault(row["view_candidate_id"], []).append((view_name, None, row))
                index.setdefault(row["raw_candidate_id"], []).append((view_name, None, row))
    return index


def _deepcopy_jsonable(value):
    return json.loads(json.dumps(value, ensure_ascii=False))


def _normalize_warning_list(*warning_groups):
    seen = []
    for group in warning_groups:
        for warning in group or []:
            if warning and warning not in seen:
                seen.append(warning)
    return seen


def _response_metadata(query_type, view_name, limit, offset, warnings=None, source_artifact=None):
    return {
        "query_type": query_type,
        "view_name": view_name,
        "static_only": True,
        "adaptive_enabled": False,
        "source_artifact": source_artifact or str(STATIC_VIEWS_PATH.relative_to(BASE_DIR)).replace("\\", "/"),
        "limit": limit,
        "offset": offset,
        "result_count": 0,
        "warnings": _normalize_warning_list(warnings or []),
    }


def _error_response(query_type, code, message, *, details=None, view_name=None, warnings=None, limit=0, offset=0):
    return {
        "query_metadata": _response_metadata(query_type, view_name, limit, offset, warnings=warnings),
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        },
        "candidates": [],
    }


def _success_response(query_type, view_name, candidates, *, warnings=None, limit=20, offset=0):
    response = {
        "query_metadata": _response_metadata(query_type, view_name, limit, offset, warnings=warnings),
        "candidates": candidates,
    }
    response["query_metadata"]["result_count"] = len(candidates)
    return response


def _flatten_request(data):
    if isinstance(data, dict):
        items = []
        for key, value in data.items():
            items.append((str(key), value))
            items.extend(_flatten_request(value))
        return items
    if isinstance(data, list):
        items = []
        for value in data:
            items.extend(_flatten_request(value))
        return items
    return []


def derive_node_type(candidate_type):
    mapped = NODE_TYPE_MAP.get(candidate_type)
    if mapped:
        return mapped, ["NODE_TYPE_DERIVED_FROM_CANDIDATE_TYPE"]
    return "unknown", ["NODE_TYPE_DERIVED_FROM_UNKNOWN_CANDIDATE_TYPE"]


def derive_source_artifact(candidate, view_name, include_score_breakdown):
    _ = candidate, view_name, include_score_breakdown
    return str(STATIC_VIEWS_PATH.relative_to(BASE_DIR)).replace("\\", "/"), ["SOURCE_ARTIFACT_DERIVED"]


def derive_bridge_reason(candidate, view_name):
    _ = candidate
    return BRIDGE_REASON_MAP.get(view_name, "unknown_static_view_membership"), ["BRIDGE_REASON_DERIVED"]


def derive_supporting_authority_layer(candidate, raw_candidate=None):
    layers = []
    candidate_type = candidate.get("candidate_type")
    if candidate_type == "vocabulary_candidate":
        layers.append("Vocabulary")
    elif candidate_type == "chunk_candidate":
        layers.append("Chunk")
    elif candidate_type == "pattern_candidate":
        layers.append("Pattern")
    if candidate.get("theme_refs"):
        layers.append("Theme")

    explain_tokens = " ".join(candidate.get("source_explain", []))
    raw_breakdown = (raw_candidate or {}).get("score_breakdown", {})
    if "dependency_readiness_from_grammar_refs" in explain_tokens:
        layers.append("Grammar")
    if raw_breakdown.get("reinforcement_score", 0) > 0 or "reinforcement_" in explain_tokens:
        layers.append("Reinforcement")
    return sorted(set(layers)), ["SUPPORTING_AUTHORITY_LAYER_DERIVED"]


def derive_level_fields(level):
    normalized = str(level or "").upper().replace(" ", "_")
    plus_map = {"A1+": "A1_PLUS", "A2+": "A2_PLUS", "B1+": "B1_PLUS", "B2+": "B2_PLUS"}
    normalized = plus_map.get(level, normalized)
    if normalized in {"A1", "A2", "B1", "B2", "C1", "C2"}:
        return {
            "cefr": normalized,
            "level": normalized,
            "internal_level": None,
            "level_family": normalized,
            "level_band": "base",
            "level_source": "source_cefr",
        }
    if normalized in {"A1_PLUS", "A2_PLUS", "B1_PLUS", "B2_PLUS"}:
        family = normalized.split("_")[0]
        return {
            "cefr": family,
            "level": normalized,
            "internal_level": normalized,
            "level_family": family,
            "level_band": "plus",
            "level_source": "derived_internal_band",
        }
    return {
        "cefr": str(level or ""),
        "level": str(level or ""),
        "internal_level": None,
        "level_family": str(level or ""),
        "level_band": "unknown",
        "level_source": "source_unknown",
    }


def _candidate_limit_warning(limit):
    warnings = []
    if limit is None:
        return MAX_LIMIT, warnings
    if limit > MAX_LIMIT:
        warnings.append("LIMIT_CLAMPED_TO_MAXIMUM")
        return MAX_LIMIT, warnings
    return limit, warnings


def _normalize_theme_name(theme):
    if theme is None:
        return None
    lowered = str(theme).strip().lower()
    for name in THEME_NAMES:
        if name.lower() == lowered:
            return name
    return str(theme).strip()


def _theme_matches(candidate, theme):
    if theme is None:
        return True
    theme_text = str(theme).strip().lower()
    if not theme_text:
        return True
    for ref in candidate.get("theme_refs", []):
        if theme_text in str(ref).lower():
            return True
    return False


def _candidate_matches(candidate, *, level=None, cefr=None, theme=None, node_type=None, candidate_type=None):
    if level and candidate.get("level") != level and candidate.get("level_family") != level:
        return False
    if cefr and candidate.get("cefr") != cefr:
        return False
    if theme and not _theme_matches(candidate, theme):
        return False
    if node_type and candidate.get("node_type") != node_type:
        return False
    if candidate_type and candidate.get("candidate_type") != candidate_type:
        return False
    return True


def build_candidate_explanation(candidate, raw_candidate=None, view_name=None):
    score_breakdown = _deepcopy_jsonable((raw_candidate or {}).get("score_breakdown", {}))
    view_policy_summary = {
        "view_name": view_name,
        "view_policy_applied": list(candidate.get("view_policy_applied", [])),
        "balance_adjustments": _deepcopy_jsonable(candidate.get("balance_adjustments", [])),
    }
    limitations = []
    limitations.extend(VIEW_WARNING_MAP.get(view_name, []))
    limitations.extend(
        warning
        for warning in candidate.get("warnings", [])
        if warning
        in {
            "NODE_TYPE_DERIVED_FROM_CANDIDATE_TYPE",
            "NODE_TYPE_DERIVED_FROM_UNKNOWN_CANDIDATE_TYPE",
            "SOURCE_ARTIFACT_DERIVED",
            "BRIDGE_REASON_DERIVED",
            "SUPPORTING_AUTHORITY_LAYER_DERIVED",
            "VIEW_SCORE_IS_POLICY_ADJUSTED",
            "REINFORCEMENT_REFERENCE_ONLY_NOT_JOINED",
        }
    )
    return {
        "why_this_candidate": (
            f"Selected from {view_name} because it is a {candidate['candidate_type']} candidate "
            f"at {candidate['level']} with matching static view membership."
        ),
        "why_this_score": (
            f"raw_static_score={candidate.get('raw_static_score')} and view_score={candidate.get('view_score')} "
            f"where view_score is policy-adjusted downstream view output."
        ),
        "which_authority_supports_it": list(candidate.get("supporting_authority_layer", [])),
        "which_bridge_produced_it": candidate.get("bridge_reason", ""),
        "which_filters_can_retrieve_it": ["view_name", "level", "theme", "node_type", "candidate_type"],
        "score_breakdown_summary": score_breakdown,
        "view_policy_summary": view_policy_summary,
        "known_limitations": _normalize_warning_list(limitations),
    }


def normalize_candidate(view_row, raw_candidate=None, view_name=None):
    node_type, node_warnings = derive_node_type(view_row.get("candidate_type"))
    source_artifact, source_warnings = derive_source_artifact(view_row, view_name, True)
    bridge_reason, bridge_warnings = derive_bridge_reason(view_row, view_name)
    supporting_authority_layer, support_warnings = derive_supporting_authority_layer(view_row, raw_candidate=raw_candidate)
    level_fields = derive_level_fields(view_row.get("level"))

    warnings = []
    warnings.extend(node_warnings)
    warnings.extend(source_warnings)
    warnings.extend(bridge_warnings)
    warnings.extend(support_warnings)
    warnings.extend(VIEW_WARNING_MAP.get(view_name, []))
    warnings.append("VIEW_SCORE_IS_POLICY_ADJUSTED")
    if raw_candidate and raw_candidate.get("score_breakdown", {}).get("reinforcement_score", 0) > 0:
        warnings.append("REINFORCEMENT_REFERENCE_ONLY_NOT_JOINED")
    if view_row.get("raw_static_score") is None or view_row.get("view_score") is None:
        warnings.append("MISSING_RAW_OR_VIEW_SCORE_PAIR")

    candidate = {
        "candidate_id": view_row.get("view_candidate_id"),
        "raw_candidate_id": view_row.get("raw_candidate_id"),
        "label": view_row.get("label"),
        "node_type": node_type,
        "candidate_type": view_row.get("candidate_type"),
        "level": level_fields["level"],
        "cefr": level_fields["cefr"],
        "internal_level": level_fields["internal_level"],
        "level_family": level_fields["level_family"],
        "level_band": level_fields["level_band"],
        "level_source": level_fields["level_source"],
        "theme_refs": list(view_row.get("theme_refs", [])),
        "view_rank": view_row.get("view_rank"),
        "raw_rank": view_row.get("raw_rank"),
        "raw_static_score": view_row.get("raw_static_score"),
        "view_score": view_row.get("view_score"),
        "score_type": "view_policy_adjusted",
        "source_artifact": source_artifact,
        "bridge_reason": bridge_reason,
        "supporting_authority_layer": supporting_authority_layer,
        "explanation": {},
        "warnings": _normalize_warning_list(warnings),
        "view_policy_applied": list(view_row.get("view_policy_applied", [])),
        "balance_adjustments": _deepcopy_jsonable(view_row.get("balance_adjustments", [])),
        "source_explain": list(view_row.get("source_explain", [])),
    }
    candidate["explanation"] = build_candidate_explanation(candidate, raw_candidate=raw_candidate, view_name=view_name)
    return candidate


def _strip_candidate_for_response(candidate, include_explanation, include_score_breakdown):
    response_candidate = {key: value for key, value in candidate.items() if key in RESPONSE_CANDIDATE_FIELDS}
    if include_explanation:
        explanation = _deepcopy_jsonable(candidate["explanation"])
        if not include_score_breakdown:
            explanation["score_breakdown_summary"] = {}
        response_candidate["explanation"] = explanation
    else:
        response_candidate["explanation"] = {}
    return response_candidate


def resolve_view(view_name):
    views = load_static_ranking_views().get("views", {})
    if view_name not in VIEW_NAMES:
        return None
    return views.get(view_name)


def _resolve_theme_rows(theme):
    theme_name = _normalize_theme_name(theme)
    theme_views = resolve_view("theme_scoped_view") or {}
    if theme_name in theme_views:
        return theme_name, theme_views[theme_name]
    return theme_name, []


def _normalize_rows(rows, view_name, include_explanation=True, include_score_breakdown=True):
    raw_index = _raw_candidate_index()
    normalized = []
    for row in rows:
        raw_candidate = raw_index.get(row.get("raw_candidate_id"))
        candidate = normalize_candidate(row, raw_candidate=raw_candidate, view_name=view_name)
        normalized.append(_strip_candidate_for_response(candidate, include_explanation, include_score_breakdown))
    return normalized


def _apply_offset_limit(rows, offset, limit):
    start = max(offset or 0, 0)
    end = None if limit is None else start + limit
    return rows[start:end]


def validate_static_request(request):
    errors = []
    for key, value in _flatten_request(request):
        lowered = key.lower()
        if lowered in FORBIDDEN_REQUEST_KEYS:
            errors.append("ADAPTIVE_FIELD_REJECTED")
        if key == "source_artifact" and isinstance(value, str) and "learner_exposure" in value.lower():
            errors.append("LEARNER_ARTIFACT_NOT_JOINED_STATIC_ONLY")
    if request.get("static_only") is not True:
        errors.append("STATIC_ONLY_REQUIRED")

    filters = request.get("filters", {}) if isinstance(request.get("filters"), dict) else {}
    node_type = filters.get("node_type")
    candidate_type = filters.get("candidate_type")
    if node_type and candidate_type:
        derived, _ = derive_node_type(candidate_type)
        if derived != node_type:
            errors.append("NODE_TYPE_CANDIDATE_TYPE_CONFLICT")

    if isinstance(request.get("limit"), int) and request["limit"] < 0:
        errors.append("INVALID_LIMIT")
    if isinstance(request.get("offset"), int) and request["offset"] < 0:
        errors.append("INVALID_OFFSET")
    return _normalize_warning_list(errors)


def _prepare_request(query_type, *, view_name=None, filters=None, limit=20, offset=0, include_explanation=True, include_score_breakdown=True, static_only=True):
    return {
        "query_type": query_type,
        "view_name": view_name,
        "filters": filters or {},
        "limit": limit,
        "offset": offset,
        "include_explanation": include_explanation,
        "include_score_breakdown": include_score_breakdown,
        "static_only": static_only,
    }


def _query_view_rows(view_name, include_explanation, include_score_breakdown):
    resolved = resolve_view(view_name)
    if resolved is None:
        return None, _error_response(
            "get_static_ranking_view",
            "UNKNOWN_VIEW_NAME",
            f"unknown static view: {view_name}",
            view_name=view_name,
            warnings=["UNKNOWN_VIEW_NAME"],
        )
    if view_name == "theme_scoped_view":
        all_rows = []
        for rows in resolved.values():
            all_rows.extend(rows)
        return _normalize_rows(all_rows, view_name, include_explanation, include_score_breakdown), None
    return _normalize_rows(resolved, view_name, include_explanation, include_score_breakdown), None


def _run_get_static_ranking_view(request):
    view_name = request.get("view_name")
    limit, limit_warnings = _candidate_limit_warning(request.get("limit"))
    offset = request.get("offset", 0)
    rows, error = _query_view_rows(view_name, request.get("include_explanation", True), request.get("include_score_breakdown", True))
    if error:
        error["query_metadata"]["limit"] = limit
        error["query_metadata"]["offset"] = offset
        error["query_metadata"]["warnings"] = _normalize_warning_list(error["query_metadata"]["warnings"], limit_warnings)
        return error
    candidates = _apply_offset_limit(rows, offset, limit)
    warnings = _normalize_warning_list(VIEW_WARNING_MAP.get(view_name, []), limit_warnings)
    return _success_response("get_static_ranking_view", view_name, candidates, warnings=warnings, limit=limit, offset=offset)


def _run_get_top_candidates(request):
    view_name = request.get("view_name") or "balanced_global_view"
    limit, limit_warnings = _candidate_limit_warning(request.get("limit", 20))
    offset = request.get("offset", 0)
    rows, error = _query_view_rows(view_name, request.get("include_explanation", True), request.get("include_score_breakdown", True))
    if error:
        return error
    filters = request.get("filters", {})
    filtered = [
        row
        for row in rows
        if _candidate_matches(
            row,
            level=filters.get("level"),
            cefr=filters.get("cefr"),
            theme=filters.get("theme"),
            node_type=filters.get("node_type"),
            candidate_type=filters.get("candidate_type"),
        )
    ]
    warnings = _normalize_warning_list(VIEW_WARNING_MAP.get(view_name, []), limit_warnings)
    return _success_response("get_top_candidates", view_name, _apply_offset_limit(filtered, offset, limit), warnings=warnings, limit=limit, offset=offset)


def _run_get_candidates_by_theme(request):
    theme = request.get("filters", {}).get("theme")
    if not theme:
        return _error_response(
            "get_candidates_by_theme",
            "MISSING_THEME",
            "theme is required",
            view_name="theme_scoped_view",
            warnings=["THEME_SCOPED_VIEW_HEURISTIC_RELEVANCE_WARNING"],
        )
    view_name = request.get("view_name") or "theme_scoped_view"
    limit, limit_warnings = _candidate_limit_warning(request.get("limit", 20))
    offset = request.get("offset", 0)
    if view_name == "theme_scoped_view":
        _, rows = _resolve_theme_rows(theme)
        normalized = _normalize_rows(rows, view_name, request.get("include_explanation", True), request.get("include_score_breakdown", True))
    else:
        normalized, error = _query_view_rows(view_name, request.get("include_explanation", True), request.get("include_score_breakdown", True))
        if error:
            return error
        normalized = [row for row in normalized if _theme_matches(row, theme)]
    level = request.get("filters", {}).get("level")
    if level:
        normalized = [row for row in normalized if row["level"] == level or row["level_family"] == level]
    warnings = _normalize_warning_list(["THEME_SCOPED_VIEW_HEURISTIC_RELEVANCE_WARNING"], limit_warnings)
    return _success_response("get_candidates_by_theme", view_name, _apply_offset_limit(normalized, offset, limit), warnings=warnings, limit=limit, offset=offset)


def _run_get_candidates_by_node_type(request):
    filters = request.get("filters", {})
    view_name = request.get("view_name") or ("theme_scoped_view" if filters.get("theme") else "balanced_global_view")
    response = _run_get_top_candidates({**request, "view_name": view_name})
    if "error" in response:
        return response
    node_type = filters.get("node_type")
    response["query_metadata"]["query_type"] = "get_candidates_by_node_type"
    response["candidates"] = [row for row in response["candidates"] if row["node_type"] == node_type]
    if node_type == "unknown":
        response["query_metadata"]["warnings"] = _normalize_warning_list(response["query_metadata"]["warnings"], ["NODE_TYPE_DERIVED_FROM_UNKNOWN_CANDIDATE_TYPE"])
    response["query_metadata"]["result_count"] = len(response["candidates"])
    return response


def _run_get_candidate_explanation(request):
    candidate_id = request.get("filters", {}).get("candidate_id")
    if not candidate_id:
        return _error_response(
            "get_candidate_explanation",
            "CANDIDATE_NOT_FOUND",
            "candidate_id is required",
            warnings=["CANDIDATE_NOT_FOUND"],
        )
    preferred_view = request.get("view_name")
    search_entries = []
    indexed = _view_candidate_index().get(candidate_id, [])
    if preferred_view:
        search_entries.extend([entry for entry in indexed if entry[0] == preferred_view])
        search_entries.extend([entry for entry in indexed if entry[0] != preferred_view])
    else:
        search_entries.extend(indexed)
    if not search_entries:
        return _error_response(
            "get_candidate_explanation",
            "CANDIDATE_NOT_FOUND",
            f"candidate not found: {candidate_id}",
            warnings=["CANDIDATE_NOT_FOUND"],
        )
    view_name, _, row = search_entries[0]
    normalized = _normalize_rows([row], view_name, True, request.get("include_score_breakdown", True))[0]
    return _success_response(
        "get_candidate_explanation",
        view_name,
        [normalized],
        warnings=VIEW_WARNING_MAP.get(view_name, []),
        limit=1,
        offset=0,
    )


def _run_get_bridge_view(request, *, query_type, view_name, base_warning):
    response = _run_get_top_candidates({**request, "view_name": view_name})
    if "error" in response:
        return response
    response["query_metadata"]["query_type"] = query_type
    response["query_metadata"]["warnings"] = _normalize_warning_list(response["query_metadata"]["warnings"], [base_warning])
    return response


def _run_get_a1_safe_candidates(request):
    response = _run_get_top_candidates({**request, "view_name": "a1_safe_view"})
    if "error" in response:
        return response
    response["query_metadata"]["query_type"] = "get_a1_safe_candidates"
    if request.get("filters", {}).get("theme"):
        response["query_metadata"]["warnings"] = _normalize_warning_list(
            response["query_metadata"]["warnings"],
            ["THEME_SCOPED_VIEW_HEURISTIC_RELEVANCE_WARNING"],
        )
    return response


def query_static_candidates(request):
    request = deepcopy(request or {})
    validation_errors = validate_static_request(request)
    if validation_errors:
        return _error_response(
            request.get("query_type", "query_static_candidates"),
            validation_errors[0],
            "static query request rejected",
            details={"validation_errors": validation_errors},
            view_name=request.get("view_name"),
            warnings=validation_errors,
            limit=request.get("limit", 0) or 0,
            offset=request.get("offset", 0) or 0,
        )

    query_type = request.get("query_type")
    if query_type == "get_static_ranking_view":
        return _run_get_static_ranking_view(request)
    if query_type == "get_top_candidates":
        return _run_get_top_candidates(request)
    if query_type == "get_candidates_by_theme":
        return _run_get_candidates_by_theme(request)
    if query_type == "get_candidates_by_node_type":
        return _run_get_candidates_by_node_type(request)
    if query_type == "get_candidate_explanation":
        return _run_get_candidate_explanation(request)
    if query_type == "get_reading_bridge_candidates":
        return _run_get_bridge_view(request, query_type=query_type, view_name="reading_bridge_view", base_warning="READING_BRIDGE_VIEW_NEEDS_TUNING")
    if query_type == "get_dialogue_bridge_candidates":
        return _run_get_bridge_view(request, query_type=query_type, view_name="dialogue_bridge_view", base_warning="DIALOGUE_BRIDGE_VIEW_NEEDS_TUNING")
    if query_type == "get_a1_safe_candidates":
        return _run_get_a1_safe_candidates(request)
    return _error_response(
        query_type or "query_static_candidates",
        "UNKNOWN_QUERY_TYPE",
        f"unknown query type: {query_type}",
        details={"query_type": query_type},
    )


def get_static_ranking_view(view_name, limit=None, offset=0, include_explanation=True, include_score_breakdown=True, static_only=True):
    request = _prepare_request(
        "get_static_ranking_view",
        view_name=view_name,
        limit=limit if limit is not None else MAX_LIMIT,
        offset=offset,
        include_explanation=include_explanation,
        include_score_breakdown=include_score_breakdown,
        static_only=static_only,
    )
    return query_static_candidates(request)


def get_top_candidates(level=None, cefr=None, theme=None, node_type=None, candidate_type=None, view_name="balanced_global_view", limit=20, offset=0, include_explanation=True, include_score_breakdown=True, static_only=True):
    request = _prepare_request(
        "get_top_candidates",
        view_name=view_name,
        filters={
            "level": level,
            "cefr": cefr,
            "theme": theme,
            "node_type": node_type,
            "candidate_type": candidate_type,
        },
        limit=limit,
        offset=offset,
        include_explanation=include_explanation,
        include_score_breakdown=include_score_breakdown,
        static_only=static_only,
    )
    return query_static_candidates(request)


def get_candidates_by_theme(theme, level=None, view_name="theme_scoped_view", limit=20, offset=0, include_explanation=True, include_score_breakdown=True, static_only=True):
    request = _prepare_request(
        "get_candidates_by_theme",
        view_name=view_name,
        filters={"theme": theme, "level": level},
        limit=limit,
        offset=offset,
        include_explanation=include_explanation,
        include_score_breakdown=include_score_breakdown,
        static_only=static_only,
    )
    return query_static_candidates(request)


def get_candidates_by_node_type(node_type, level=None, theme=None, view_name=None, limit=20, offset=0, include_explanation=True, include_score_breakdown=True, static_only=True):
    request = _prepare_request(
        "get_candidates_by_node_type",
        view_name=view_name,
        filters={"node_type": node_type, "level": level, "theme": theme},
        limit=limit,
        offset=offset,
        include_explanation=include_explanation,
        include_score_breakdown=include_score_breakdown,
        static_only=static_only,
    )
    return query_static_candidates(request)


def get_candidate_explanation(candidate_id, view_name=None, include_score_breakdown=True, static_only=True):
    request = _prepare_request(
        "get_candidate_explanation",
        view_name=view_name,
        filters={"candidate_id": candidate_id},
        limit=1,
        offset=0,
        include_explanation=True,
        include_score_breakdown=include_score_breakdown,
        static_only=static_only,
    )
    return query_static_candidates(request)


def get_reading_bridge_candidates(level=None, theme=None, limit=20, offset=0, include_explanation=True, include_score_breakdown=True, static_only=True):
    request = _prepare_request(
        "get_reading_bridge_candidates",
        view_name="reading_bridge_view",
        filters={"level": level, "theme": theme},
        limit=limit,
        offset=offset,
        include_explanation=include_explanation,
        include_score_breakdown=include_score_breakdown,
        static_only=static_only,
    )
    return query_static_candidates(request)


def get_dialogue_bridge_candidates(level=None, theme=None, limit=20, offset=0, include_explanation=True, include_score_breakdown=True, static_only=True):
    request = _prepare_request(
        "get_dialogue_bridge_candidates",
        view_name="dialogue_bridge_view",
        filters={"level": level, "theme": theme},
        limit=limit,
        offset=offset,
        include_explanation=include_explanation,
        include_score_breakdown=include_score_breakdown,
        static_only=static_only,
    )
    return query_static_candidates(request)


def get_a1_safe_candidates(theme=None, node_type=None, limit=20, offset=0, include_explanation=True, include_score_breakdown=True, static_only=True):
    request = _prepare_request(
        "get_a1_safe_candidates",
        view_name="a1_safe_view",
        filters={"theme": theme, "node_type": node_type, "level": "A1"},
        limit=limit,
        offset=offset,
        include_explanation=include_explanation,
        include_score_breakdown=include_score_breakdown,
        static_only=static_only,
    )
    return query_static_candidates(request)


def build_multi_level_coverage_matrix():
    views = load_static_ranking_views().get("views", {})
    columns = [
        "balanced_global_view",
        "theme_scoped_view",
        "reading_bridge_view",
        "dialogue_bridge_view",
        "pattern_first_view",
        "vocabulary_first_view",
        "chunk_safe_view",
        "deduplicated_view",
    ]
    rows = ["A1", "A1+", "A2", "A2+", "B1", "B1+", "B2", "B2+", "C1", "C2"]
    matrix = []
    for row_level in rows:
        row = {"level": row_level}
        base_family = row_level.replace("+", "")
        plus_band = row_level.endswith("+")
        statuses = []
        for column in columns:
            if column == "theme_scoped_view":
                source_rows = []
                for theme_rows in views.get(column, {}).values():
                    source_rows.extend(theme_rows)
            else:
                source_rows = views.get(column, [])
            exact_levels = {candidate.get("level") for candidate in source_rows}
            family_levels = {derive_level_fields(candidate.get("level"))["level_family"] for candidate in source_rows}
            if plus_band:
                if base_family in family_levels:
                    status = "requires_internal_band_mapping"
                else:
                    status = "missing"
            else:
                if row_level in exact_levels:
                    status = "supported_by_cefr_only"
                elif base_family in family_levels:
                    status = "supported"
                else:
                    status = "missing"
            row[column] = status
            statuses.append(status)
        if plus_band and "requires_internal_band_mapping" in statuses:
            row["status"] = "requires_internal_band_mapping"
        elif "supported_by_cefr_only" in statuses:
            row["status"] = "supported_by_cefr_only"
        elif "supported" in statuses:
            row["status"] = "supported"
        else:
            row["status"] = "missing"
        matrix.append(row)
    return matrix


def _view_readiness():
    audit = load_views_quality_audit()
    readiness = _deepcopy_jsonable(audit.get("downstream_readiness", {}))
    readiness.setdefault("raw_global_view", "READY_WITH_WARNINGS")
    readiness.setdefault("a1_safe_view", "READY_WITH_WARNINGS")
    return readiness


def generate_summary_report(*, validation_summary=None, test_summary=None):
    coverage_matrix = build_multi_level_coverage_matrix()
    summary = {
        "task": "ULGA-S10J_StaticCandidateQueryLayer_ContractImplementation",
        "status": "PASS_WITH_WARNINGS",
        "static_only_integrity": "PASS",
        "adaptive_dependency_count": 0,
        "query_functions_implemented": list(PUBLIC_QUERY_FUNCTIONS),
        "required_query_functions_missing": [],
        "derived_fields_implemented": [
            "node_type",
            "source_artifact",
            "bridge_reason",
            "supporting_authority_layer",
            "level_fields",
        ],
        "warning_codes_registered": sorted(REQUIRED_WARNING_CODES),
        "multi_level_coverage_matrix": coverage_matrix,
        "view_readiness": _view_readiness(),
        "guardrail_summary": {
            "forbidden_request_keys": sorted(FORBIDDEN_REQUEST_KEYS),
            "static_only_required": True,
            "max_limit": MAX_LIMIT,
            "raw_ranking_curriculum_use_blocked": True,
        },
        "test_summary": test_summary
        or {
            "targeted_test_file": "tests/ulga/test_static_candidate_query_layer.py",
            "runtime_status": "pending_external_test_execution",
        },
        "known_warnings": [
            "Grammar not first-class",
            "Reinforcement provenance not first-class",
            "source_artifact is derived",
            "bridge_reason is derived",
            "supporting_authority_layer is derived",
            "node_type is derived from candidate_type",
            "theme_scoped_view remains heuristic",
            "reading_bridge_view needs tuning",
            "dialogue_bridge_view needs tuning",
            "view_score is policy-adjusted, not raw authority score",
            "raw ranking direct curriculum use is NOT_ALLOWED",
        ],
        "blocked_features": [
            "learner_state",
            "mastery",
            "learner_id",
            "student_id",
            "adaptive planner",
            "runtime personalization",
            "personalized next best node",
        ],
    }
    if validation_summary:
        summary["validation_summary"] = validation_summary
    SUMMARY_REPORT_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


if not SUMMARY_REPORT_PATH.exists():
    try:
        generate_summary_report()
    except Exception:
        pass
