import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

OUTPUT_PATH = BASE_DIR / "ulga" / "graph" / "static_candidate_ranking.json"

DEPENDENCY_GRAPH_PATH = BASE_DIR / "ulga" / "graph" / "dependency_graph.json"
THEME_SPIRAL_GRAPH_PATH = BASE_DIR / "ulga" / "graph" / "theme_spiral_graph.json"
PATTERN_CONSTRAINTS_PATH = BASE_DIR / "ulga" / "graph" / "pattern_vocabulary_constraints.json"
PATTERN_QUERY_CONTRACT_PATH = BASE_DIR / "ulga" / "graph" / "pattern_vocabulary_candidate_query_contract.json"
PATTERNS_PATH = BASE_DIR / "ulga" / "graph" / "sentence_patterns.json"
VOCABULARY_NODES_PATH = BASE_DIR / "ulga" / "graph" / "vocabulary_nodes.json"
VOCABULARY_SOURCE_PATH = BASE_DIR / "vocabulary" / "json" / "vocabulary.json"
CHUNK_NODES_PATH = BASE_DIR / "ulga" / "graph" / "chunk_nodes.json"
CHUNK_GRAMMAR_METADATA_PATH = BASE_DIR / "ulga" / "graph" / "chunk_grammar_metadata.json"
THEME_MAPPING_PATH = BASE_DIR / "themes" / "theme_vocab_mapping.json"

SCHEMA_VERSION = "ULGA_S10C_STATIC_CANDIDATE_RANKING_V1"
SOURCE = "ULGA_S10C_STATIC_CANDIDATE_RANKING"
RANKING_MODE = "static_offline"
ADAPTIVE_ENABLED = False

WEIGHTS = {
    "dependency_readiness_score": 0.30,
    "frequency_score": 0.20,
    "theme_spiral_score": 0.20,
    "reinforcement_score": 0.20,
    "authority_confidence_score": 0.10,
}

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

REQUIRED_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]
LEVEL_ORDER = {level: index for index, level in enumerate(REQUIRED_LEVELS)}
CANDIDATE_TYPE_ORDER = {
    "pattern_candidate": 0,
    "vocabulary_candidate": 1,
    "chunk_candidate": 2,
}
FREQUENCY_BAND_SCORE = {
    "tier_1": 1.0,
    "tier_2": 0.85,
    "tier_3": 0.70,
    "tier_4": 0.50,
    "tier_5": 0.25,
    "core": 1.0,
    "common": 0.85,
    "extended": 0.55,
    "low": 0.25,
}
PRIORITY_BAND_SCORE = {
    "core": 1.0,
    "common": 0.8,
    "extended": 0.55,
    "low": 0.2,
}


def read_json(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_json_optional(path, default):
    if not path.exists():
        return default
    return read_json(path)


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False, sort_keys=False)
        handle.write("\n")


def clamp(value, default=0.0):
    if value is None:
        value = default
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = float(default)
    return max(0.0, min(1.0, value))


def round4(value):
    return round(clamp(value), 4)


def normalize_text(value):
    return str(value or "").strip().lower()


def normalize_topic(value):
    text = normalize_text(value)
    if not text:
        return ""
    replacements = {
        "&": "and",
        "_": " ",
        "-": " ",
        "/": " ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = " ".join(text.split())
    aliases = {
        "home": "homes and buildings",
        "homes": "homes and buildings",
        "housing": "homes and buildings",
        "food": "food and drink",
        "drink": "food and drink",
        "shopping": "shopping",
        "travel": "travel",
        "money": "money",
        "communication": "communication",
        "education": "education",
        "work": "work",
        "health": "body and health",
        "medical": "body and health",
        "body": "body and health",
        "technology": "technology",
        "relationships": "relationships",
        "personality": "people: personality",
        "appearance": "people: appearance",
        "actions": "people: actions",
        "natural world": "natural world",
        "describing things": "describing things",
        "arts and media": "arts and media",
        "clothes": "clothes",
    }
    return aliases.get(text, text)


def slugify_parent_theme(value):
    text = normalize_text(value).replace("(bridge)", "").strip()
    return "_".join(part for part in text.replace("/", " ").split() if part)


def contains_forbidden_adaptive_content(payload):
    if isinstance(payload, dict):
        for key, value in payload.items():
            if any(token in normalize_text(key) for token in FORBIDDEN_ADAPTIVE_KEYWORDS):
                return True
            if contains_forbidden_adaptive_content(value):
                return True
        return False
    if isinstance(payload, list):
        return any(contains_forbidden_adaptive_content(item) for item in payload)
    if isinstance(payload, str):
        text = payload.lower()
        return any(token in text for token in FORBIDDEN_ADAPTIVE_KEYWORDS)
    return False


def build_theme_catalog(theme_mapping_payload):
    themes = theme_mapping_payload.get("themes", []) if isinstance(theme_mapping_payload, dict) else []
    theme_index = {}
    topic_index = defaultdict(list)
    parent_stage_index = {}

    for item in themes:
        if not isinstance(item, dict):
            continue
        theme_id = item.get("theme_id")
        level = item.get("level")
        if not theme_id or level not in LEVEL_ORDER:
            continue
        theme_index[theme_id] = item
        parent_stage_index[(slugify_parent_theme(item.get("parent_theme")), level)] = theme_id
        for topic in item.get("primary_topics", []) or []:
            topic_index[normalize_topic(topic)].append((theme_id, 1.0, level))
        for topic in item.get("secondary_topics", []) or []:
            topic_index[normalize_topic(topic)].append((theme_id, 0.7, level))

    return theme_index, topic_index, parent_stage_index


def select_theme_refs(level, topics, topic_index):
    choices = []
    for topic in topics:
        normalized = normalize_topic(topic)
        if not normalized:
            continue
        for theme_id, weight, theme_level in topic_index.get(normalized, []):
            level_match = 1.0 if theme_level == level else 0.6
            choices.append((weight * level_match, theme_id))
    if not choices:
        return []
    deduped = {}
    for score, theme_id in choices:
        deduped[theme_id] = max(score, deduped.get(theme_id, 0.0))
    ranked = sorted(deduped.items(), key=lambda item: (-item[1], item[0]))
    return [theme_id for theme_id, _score in ranked[:3]]


def build_spiral_indexes(theme_spiral_payload):
    stage_score = {}
    edge_count = defaultdict(int)
    parent_level_to_stage = {}
    themes_with_edges = set()

    for node in theme_spiral_payload.get("theme_stage_nodes", []) if isinstance(theme_spiral_payload, dict) else []:
        if not isinstance(node, dict):
            continue
        stage_id = node.get("stage_id")
        theme_id = node.get("theme_id")
        level = node.get("cefr_band")
        if stage_id:
            stage_score[stage_id] = 0.7
        if theme_id and level in LEVEL_ORDER:
            parent_level_to_stage[(theme_id, level)] = stage_id

    for edge in theme_spiral_payload.get("spiral_edges", []) if isinstance(theme_spiral_payload, dict) else []:
        if not isinstance(edge, dict) or edge.get("review_status") != "accepted":
            continue
        source_stage_id = edge.get("source_stage_id")
        target_stage_id = edge.get("target_stage_id")
        theme_id = edge.get("theme_id")
        stage_gap = 1
        for evidence in edge.get("evidence", []) or []:
            if isinstance(evidence, dict) and isinstance(evidence.get("stage_gap"), int):
                stage_gap = evidence["stage_gap"]
                break
        score = 1.0 if stage_gap <= 1 else 0.75 if stage_gap <= 2 else 0.55
        for stage_id in [source_stage_id, target_stage_id]:
            if stage_id:
                stage_score[stage_id] = max(stage_score.get(stage_id, 0.7), score)
                edge_count[stage_id] += 1
        if theme_id:
            themes_with_edges.add(theme_id)

    return stage_score, dict(edge_count), parent_level_to_stage, themes_with_edges


def build_dependency_index(dependency_payload):
    incoming = Counter()
    accepted_nodes = set()
    for edge in dependency_payload.get("edges", []) if isinstance(dependency_payload, dict) else []:
        if not isinstance(edge, dict) or edge.get("review_status") != "accepted":
            continue
        source = edge.get("source_node_id")
        target = edge.get("target_node_id")
        if source:
            accepted_nodes.add(source)
        if target:
            accepted_nodes.add(target)
            incoming[target] += 1
    max_incoming = max(incoming.values(), default=0)
    return incoming, accepted_nodes, max_incoming


def build_pattern_constraint_index(pattern_constraints):
    index = {}
    for record in pattern_constraints if isinstance(pattern_constraints, list) else []:
        if not isinstance(record, dict):
            continue
        pattern_node_id = record.get("pattern_node_id")
        if pattern_node_id:
            index[pattern_node_id] = record
    return index


def build_vocabulary_source_index(vocabulary_source):
    index = {}
    for record in vocabulary_source if isinstance(vocabulary_source, list) else []:
        if not isinstance(record, dict):
            continue
        vocab_id = record.get("vocab_id")
        if vocab_id:
            index[vocab_id] = record
    return index


def build_chunk_metadata_index(chunk_metadata):
    index = {}
    for record in chunk_metadata if isinstance(chunk_metadata, list) else []:
        if not isinstance(record, dict):
            continue
        chunk_id = record.get("chunk_id")
        if chunk_id:
            index[chunk_id] = record
    return index


def infer_pattern_frequency_score(node, constraint):
    meta = node.get("metadata", {})
    difficulty = clamp(1.0 - float(meta.get("difficulty_score", 0.5)), default=0.5)
    band_scores = []
    for slot in constraint.get("slot_constraints", []) if isinstance(constraint, dict) else []:
        freq_hint = slot.get("frequency_hint", {}) if isinstance(slot, dict) else {}
        for band in freq_hint.get("preferred_bands", []) or []:
            band_scores.append(FREQUENCY_BAND_SCORE.get(normalize_text(band), 0.55))
    band_score = sum(band_scores) / len(band_scores) if band_scores else 0.6
    return round4((difficulty * 0.7) + (band_score * 0.3))


def infer_pattern_dependency_score(node, dependency_incoming, max_dependency_incoming):
    meta = node.get("metadata", {})
    grammar_refs = meta.get("grammar_refs", []) or []
    difficulty = clamp(meta.get("difficulty_score", 0.5), default=0.5)
    if not grammar_refs:
        return round4(1.0 - (difficulty * 0.35))
    burdens = []
    for grammar_ref in grammar_refs:
        if max_dependency_incoming <= 0:
            burdens.append(0.0)
        else:
            burdens.append(min(dependency_incoming.get(grammar_ref, 0) / max_dependency_incoming, 1.0))
    burden = sum(burdens) / len(burdens)
    return round4(1.0 - (burden * 0.7) - (difficulty * 0.2))


def infer_pattern_reinforcement_score(node, constraint):
    meta = node.get("metadata", {})
    slots = meta.get("slots", []) or []
    theme_refs = meta.get("theme_refs", []) or []
    grammar_refs = meta.get("grammar_refs", []) or []
    chunk_refs = meta.get("chunk_refs", []) or []
    support_density = min((len(slots) + len(theme_refs) + len(grammar_refs) + len(chunk_refs)) / 8.0, 1.0)
    constraint_bonus = min(len(constraint.get("slot_constraints", []) or []) / 3.0, 1.0) if isinstance(constraint, dict) else 0.0
    return round4((support_density * 0.7) + (constraint_bonus * 0.3))


def infer_vocabulary_dependency_score(node, source_record):
    grammar_prereqs = node.get("metadata", {}).get("grammar_prerequisites", []) or []
    review_required = bool(source_record.get("review_required")) if isinstance(source_record, dict) else False
    penalty = min(len(grammar_prereqs) * 0.2, 0.4) + (0.15 if review_required else 0.0)
    return round4(1.0 - penalty)


def infer_vocabulary_frequency_score(node, source_record):
    meta = node.get("metadata", {})
    if isinstance(meta.get("frequency_score"), (int, float)):
        return round4(float(meta["frequency_score"]) / 100.0)
    if isinstance(source_record, dict) and isinstance(source_record.get("frequency_score"), (int, float)):
        return round4(float(source_record["frequency_score"]) / 100.0)
    band = normalize_text(source_record.get("frequency_band")) if isinstance(source_record, dict) else ""
    return round4(FREQUENCY_BAND_SCORE.get(band, 0.5))


def infer_vocabulary_reinforcement_score(node, theme_refs, source_record):
    meta = node.get("metadata", {})
    chunk_count = int(meta.get("chunk_count") or 0)
    theme_score = min(len(theme_refs) / 3.0, 1.0)
    band_score = FREQUENCY_BAND_SCORE.get(normalize_text(source_record.get("frequency_band")), 0.5) if isinstance(source_record, dict) else 0.5
    chunk_score = min(chunk_count / 5.0, 1.0)
    return round4((theme_score * 0.3) + (chunk_score * 0.4) + (band_score * 0.3))


def infer_chunk_dependency_score(node, chunk_meta):
    if not isinstance(chunk_meta, dict):
        return 0.6
    if chunk_meta.get("manual_review_required"):
        return 0.3
    prereq_penalty = min(len(chunk_meta.get("grammar_prerequisites", []) or []) * 0.2, 0.4)
    return round4(1.0 - prereq_penalty)


def infer_chunk_frequency_score(node):
    meta = node.get("metadata", {})
    if isinstance(meta.get("frequency_proxy_score"), (int, float)):
        return round4(meta["frequency_proxy_score"])
    return round4(PRIORITY_BAND_SCORE.get(normalize_text(meta.get("priority_band")), 0.5))


def infer_chunk_reinforcement_score(node, chunk_meta, theme_refs):
    meta = node.get("metadata", {})
    pattern_seed = 1.0 if isinstance(chunk_meta, dict) and chunk_meta.get("pattern_seed") else 0.0
    slot_density = min(float((chunk_meta or {}).get("slot_count") or 0) / 3.0, 1.0)
    theme_score = min(len(theme_refs) / 3.0, 1.0)
    priority_score = PRIORITY_BAND_SCORE.get(normalize_text(meta.get("priority_band")), 0.5)
    return round4((pattern_seed * 0.4) + (slot_density * 0.3) + (theme_score * 0.1) + (priority_score * 0.2))


def infer_theme_spiral_score(level, theme_refs, theme_index, stage_score, parent_level_to_stage):
    if not theme_refs:
        return 0.5
    scores = []
    for theme_ref in theme_refs:
        theme_key = theme_ref.split("theme:", 1)[-1]
        theme_record = theme_index.get(theme_key)
        if theme_record:
            stage_key = slugify_parent_theme(theme_record.get("parent_theme"))
            stage_id = parent_level_to_stage.get((stage_key, level))
            if stage_id:
                scores.append(stage_score.get(stage_id, 0.8))
                continue
        theme_suffix = slugify_parent_theme(theme_ref.split("theme:", 1)[-1])
        stage_id = parent_level_to_stage.get((theme_suffix, level))
        if stage_id:
            scores.append(stage_score.get(stage_id, 0.8))
        else:
            scores.append(0.65)
    return round4(sum(scores) / len(scores))


def compute_static_score(breakdown):
    total = 0.0
    for key, weight in WEIGHTS.items():
        total += clamp(breakdown.get(key, 0.0)) * weight
    return round(total + 1e-10, 4)


def make_candidate_record(candidate_id, candidate_type, label, level, theme_refs, breakdown, explain):
    return {
        "rank": 0,
        "candidate_id": candidate_id,
        "candidate_type": candidate_type,
        "label": label,
        "level": level,
        "theme_refs": theme_refs,
        "static_score": compute_static_score(breakdown),
        "score_breakdown": {key: round4(value) for key, value in breakdown.items()},
        "explain": explain,
        "blocked": False,
        "block_reasons": [],
    }


def make_blocked_record(candidate_id, candidate_type, label, level, theme_refs, reason):
    scrubbed_id = candidate_id or ""
    scrubbed_label = label or ""
    if reason == "forbidden_adaptive_feature_detected" or contains_forbidden_adaptive_content(
        {"candidate_id": scrubbed_id, "label": scrubbed_label, "theme_refs": theme_refs or []}
    ):
        scrubbed_id = "scrubbed_forbidden_candidate"
        scrubbed_label = "[scrubbed forbidden candidate]"
    return {
        "rank": 0,
        "candidate_id": scrubbed_id,
        "candidate_type": candidate_type or "",
        "label": scrubbed_label,
        "level": level or "",
        "theme_refs": theme_refs or [],
        "static_score": 0.0,
        "score_breakdown": {
            "dependency_readiness_score": 0.0,
            "frequency_score": 0.0,
            "theme_spiral_score": 0.0,
            "reinforcement_score": 0.0,
            "authority_confidence_score": 0.0,
        },
        "explain": [f"blocked:{reason}"],
        "blocked": True,
        "block_reasons": [reason],
    }


def candidate_sort_key(candidate):
    return (
        -candidate["static_score"],
        LEVEL_ORDER.get(candidate["level"], math.inf),
        CANDIDATE_TYPE_ORDER.get(candidate["candidate_type"], math.inf),
        candidate["candidate_id"],
    )


def validate_candidate_record(candidate):
    if not candidate.get("candidate_id"):
        return "candidate_id_missing"
    if candidate.get("candidate_type") not in CANDIDATE_TYPE_ORDER:
        return "candidate_type_unknown"
    if candidate.get("level") not in LEVEL_ORDER:
        return "level_missing"
    if not candidate.get("label"):
        return "label_missing"
    if contains_forbidden_adaptive_content(candidate):
        return "forbidden_adaptive_feature_detected"
    return None


def build_candidates(input_bundle):
    dependency_incoming, accepted_dependency_nodes, max_dependency_incoming = build_dependency_index(
        input_bundle["dependency_graph"]
    )
    stage_score, _edge_count, parent_level_to_stage, _themes_with_edges = build_spiral_indexes(
        input_bundle["theme_spiral_graph"]
    )
    theme_index, topic_index, _parent_stage_index = build_theme_catalog(input_bundle["theme_mapping"])
    pattern_constraint_index = build_pattern_constraint_index(input_bundle["pattern_constraints"])
    vocabulary_source_index = build_vocabulary_source_index(input_bundle["vocabulary_source"])
    chunk_metadata_index = build_chunk_metadata_index(input_bundle["chunk_grammar_metadata"])

    active_candidates = []
    blocked_candidates = []
    warnings = []

    for node in input_bundle["patterns"] if isinstance(input_bundle["patterns"], list) else []:
        if not isinstance(node, dict):
            continue
        meta = node.get("metadata", {})
        candidate_id = node.get("id")
        candidate_type = "pattern_candidate"
        label = node.get("label")
        level = node.get("cefr_level")
        theme_refs = [theme for theme in meta.get("theme_refs", []) or [] if isinstance(theme, str) and theme]
        constraint = pattern_constraint_index.get(candidate_id, {})

        if meta.get("review_status") != "accepted":
            blocked_candidates.append(make_blocked_record(candidate_id, candidate_type, label, level, theme_refs, "schema_invalid"))
            continue
        if not meta.get("generator_allowed", False):
            blocked_candidates.append(make_blocked_record(candidate_id, candidate_type, label, level, theme_refs, "not_generator_allowed"))
            continue
        if any(ref and ref not in accepted_dependency_nodes and dependency_incoming.get(ref, 0) == 0 for ref in meta.get("grammar_refs", []) or []):
            blocked_candidates.append(make_blocked_record(candidate_id, candidate_type, label, level, theme_refs, "dependency_conflict"))
            continue

        breakdown = {
            "dependency_readiness_score": infer_pattern_dependency_score(node, dependency_incoming, max_dependency_incoming),
            "frequency_score": infer_pattern_frequency_score(node, constraint),
            "theme_spiral_score": infer_theme_spiral_score(level, theme_refs, theme_index, stage_score, parent_level_to_stage),
            "reinforcement_score": infer_pattern_reinforcement_score(node, constraint),
            "authority_confidence_score": round4((node.get("confidence") or {}).get("value", 0.0)),
        }
        explain = [
            "static_offline_pattern",
            "pattern_authority_accepted",
            "dependency_readiness_from_grammar_refs",
            "frequency_inferred_from_pattern_difficulty_and_slot_preferences",
        ]
        if theme_refs:
            explain.append("theme_spiral_from_pattern_theme_refs")
        candidate = make_candidate_record(candidate_id, candidate_type, label, level, theme_refs, breakdown, explain)
        error = validate_candidate_record(candidate)
        if error:
            blocked_candidates.append(make_blocked_record(candidate_id, candidate_type, label, level, theme_refs, error))
            continue
        active_candidates.append(candidate)

    for node in input_bundle["vocabulary_nodes"] if isinstance(input_bundle["vocabulary_nodes"], list) else []:
        if not isinstance(node, dict):
            continue
        meta = node.get("metadata", {})
        candidate_id = node.get("id")
        candidate_type = "vocabulary_candidate"
        label = node.get("label")
        level = node.get("cefr_level")
        source_id = meta.get("source_vocabulary_id")
        source_record = vocabulary_source_index.get(source_id, {})
        topics = [source_record.get("topic"), source_record.get("raw_topic")]
        theme_refs = [f"theme:{theme_id}" for theme_id in select_theme_refs(level, topics, topic_index)]

        if isinstance(source_record, dict) and source_record and source_record.get("active") is False:
            blocked_candidates.append(make_blocked_record(candidate_id, candidate_type, label, level, theme_refs, "schema_invalid"))
            continue

        breakdown = {
            "dependency_readiness_score": infer_vocabulary_dependency_score(node, source_record),
            "frequency_score": infer_vocabulary_frequency_score(node, source_record),
            "theme_spiral_score": infer_theme_spiral_score(level, theme_refs, theme_index, stage_score, parent_level_to_stage),
            "reinforcement_score": infer_vocabulary_reinforcement_score(node, theme_refs, source_record),
            "authority_confidence_score": round4((node.get("confidence") or {}).get("value", 0.0)),
        }
        explain = [
            "static_offline_vocabulary",
            "frequency_from_vocabulary_authority",
            "reinforcement_from_chunk_and_theme_connectivity",
        ]
        if theme_refs:
            explain.append("theme_spiral_from_topic_to_theme_mapping")
        else:
            explain.append("theme_spiral_defaulted_due_to_missing_theme_mapping")
        candidate = make_candidate_record(candidate_id, candidate_type, label, level, theme_refs, breakdown, explain)
        error = validate_candidate_record(candidate)
        if error:
            blocked_candidates.append(make_blocked_record(candidate_id, candidate_type, label, level, theme_refs, error))
            continue
        active_candidates.append(candidate)

    for node in input_bundle["chunk_nodes"] if isinstance(input_bundle["chunk_nodes"], list) else []:
        if not isinstance(node, dict):
            continue
        meta = node.get("metadata", {})
        candidate_id = node.get("id")
        candidate_type = "chunk_candidate"
        label = node.get("label")
        level = node.get("cefr_level")
        chunk_meta = chunk_metadata_index.get(candidate_id, {})
        topics = [meta.get("topic"), *(meta.get("theme_hint") or [])]
        theme_refs = [f"theme:{theme_id}" for theme_id in select_theme_refs(level, topics, topic_index)]

        if meta.get("generator_allowed") is False:
            blocked_candidates.append(make_blocked_record(candidate_id, candidate_type, label, level, theme_refs, "not_generator_allowed"))
            continue
        if isinstance(chunk_meta, dict) and chunk_meta.get("manual_review_required"):
            blocked_candidates.append(make_blocked_record(candidate_id, candidate_type, label, level, theme_refs, "schema_invalid"))
            continue

        breakdown = {
            "dependency_readiness_score": infer_chunk_dependency_score(node, chunk_meta),
            "frequency_score": infer_chunk_frequency_score(node),
            "theme_spiral_score": infer_theme_spiral_score(level, theme_refs, theme_index, stage_score, parent_level_to_stage),
            "reinforcement_score": infer_chunk_reinforcement_score(node, chunk_meta, theme_refs),
            "authority_confidence_score": round4((node.get("confidence") or {}).get("value", 0.0)),
        }
        explain = [
            "static_offline_chunk",
            "frequency_from_chunk_proxy",
            "reinforcement_from_pattern_seed_and_slot_density",
        ]
        if theme_refs:
            explain.append("theme_spiral_from_chunk_topic_or_theme_hint")
        candidate = make_candidate_record(candidate_id, candidate_type, label, level, theme_refs, breakdown, explain)
        error = validate_candidate_record(candidate)
        if error:
            blocked_candidates.append(make_blocked_record(candidate_id, candidate_type, label, level, theme_refs, error))
            continue
        active_candidates.append(candidate)

    active_candidates.sort(key=candidate_sort_key)
    for index, candidate in enumerate(active_candidates, start=1):
        candidate["rank"] = index

    return active_candidates, blocked_candidates, warnings


def load_default_input_bundle():
    missing_optional_inputs = []

    def load_required(path, key):
        if not path.exists():
            raise FileNotFoundError(f"Required input missing for {key}: {path}")
        return read_json(path)

    def load_optional(path):
        if not path.exists():
            missing_optional_inputs.append({"path": str(path.relative_to(BASE_DIR)).replace("\\", "/"), "input_status": "missing_optional_input"})
            return None
        return read_json(path)

    return {
        "dependency_graph": load_required(DEPENDENCY_GRAPH_PATH, "dependency_graph"),
        "theme_spiral_graph": load_required(THEME_SPIRAL_GRAPH_PATH, "theme_spiral_graph"),
        "pattern_constraints": load_required(PATTERN_CONSTRAINTS_PATH, "pattern_constraints"),
        "pattern_query_contract": load_optional(PATTERN_QUERY_CONTRACT_PATH) or {},
        "patterns": load_required(PATTERNS_PATH, "patterns"),
        "vocabulary_nodes": load_required(VOCABULARY_NODES_PATH, "vocabulary_nodes"),
        "vocabulary_source": load_optional(VOCABULARY_SOURCE_PATH) or [],
        "chunk_nodes": load_required(CHUNK_NODES_PATH, "chunk_nodes"),
        "chunk_grammar_metadata": load_optional(CHUNK_GRAMMAR_METADATA_PATH) or [],
        "theme_mapping": load_optional(THEME_MAPPING_PATH) or {"themes": []},
        "missing_optional_inputs": missing_optional_inputs,
    }


def build_ranking_payload(input_bundle=None):
    bundle = input_bundle or load_default_input_bundle()
    candidates, blocked_candidates, warnings = build_candidates(bundle)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "ranking_mode": RANKING_MODE,
        "adaptive_enabled": ADAPTIVE_ENABLED,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source": SOURCE,
        "weights": WEIGHTS,
        "candidates": candidates,
        "blocked_candidates": blocked_candidates,
        "warnings": warnings,
        "missing_optional_inputs": bundle.get("missing_optional_inputs", []),
    }
    return payload


def build_static_candidate_ranking(output_path=OUTPUT_PATH):
    payload = build_ranking_payload()
    write_json(output_path, payload)
    print(f"Static Candidate Ranking build: {len(payload['candidates'])} active / {len(payload['blocked_candidates'])} blocked")
    return payload


if __name__ == "__main__":
    build_static_candidate_ranking()
