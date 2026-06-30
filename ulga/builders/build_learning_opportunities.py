import json
import re
from collections import Counter, defaultdict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

SENTENCE_PATTERNS_PATH = BASE_DIR / "ulga" / "graph" / "sentence_patterns.json"
CONSTRAINTS_PATH = BASE_DIR / "ulga" / "graph" / "pattern_vocabulary_constraints.json"
QUERY_CONTRACT_PATH = BASE_DIR / "ulga" / "graph" / "pattern_vocabulary_candidate_query_contract.json"
DEPENDENCY_GRAPH_PATH = BASE_DIR / "ulga" / "graph" / "dependency_graph.json"
THEME_SPIRAL_GRAPH_PATH = BASE_DIR / "ulga" / "graph" / "theme_spiral_graph.json"
THEME_NODES_PATH = BASE_DIR / "ulga" / "graph" / "theme_nodes.json"
VOCABULARY_NODES_PATH = BASE_DIR / "ulga" / "graph" / "vocabulary_nodes.json"
VOCABULARY_THEME_EDGES_REFINED_PATH = BASE_DIR / "ulga" / "graph" / "vocabulary_theme_edges.refined.json"
VOCABULARY_THEME_EDGES_PATH = BASE_DIR / "ulga" / "graph" / "vocabulary_theme_edges.json"
CHUNK_NODES_PATH = BASE_DIR / "ulga" / "graph" / "chunk_nodes.json"
CHUNK_THEME_HINT_ENHANCED_PATH = BASE_DIR / "chunk_profile" / "json" / "chunk_theme_hint_enhanced_mapping.json"
LEARNING_SIGNAL_POLICY_PATH = BASE_DIR / "ulga" / "schema" / "learning_signal_policy.json"
LEARNER_STATE_PATH = BASE_DIR / "ulga" / "learner_state" / "learner_state.json"

OPPORTUNITIES_OUT_PATH = BASE_DIR / "ulga" / "graph" / "learning_opportunities.json"
SUMMARY_OUT_PATH = BASE_DIR / "ulga" / "reports" / "learning_opportunity_summary.json"

SOURCE = "ULGA_S10B_LEARNING_OPPORTUNITY_AUTHORITY"
CONTRACT_VERSION = "ULGA-S10B"
VOCABULARY_LIMIT_PER_OPPORTUNITY = 5
CEFR_ORDER = ["A1", "A2", "B1", "B2", "C1", "C2"]
CEFR_RANK = {level: index for index, level in enumerate(CEFR_ORDER)}
INPUT_PATHS = [
    SENTENCE_PATTERNS_PATH,
    CONSTRAINTS_PATH,
    QUERY_CONTRACT_PATH,
    DEPENDENCY_GRAPH_PATH,
    THEME_SPIRAL_GRAPH_PATH,
    THEME_NODES_PATH,
    VOCABULARY_NODES_PATH,
    VOCABULARY_THEME_EDGES_REFINED_PATH,
    VOCABULARY_THEME_EDGES_PATH,
    CHUNK_NODES_PATH,
    CHUNK_THEME_HINT_ENHANCED_PATH,
    LEARNING_SIGNAL_POLICY_PATH,
    LEARNER_STATE_PATH,
]
ALLOWED_THEME_SOURCES = {
    "pattern_theme_ref",
    "pattern_slot_gate",
    "vocabulary_theme",
    "chunk_theme_hint",
    "theme_consensus",
    "general_fallback",
}


def read_json_optional(path):
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, sort_keys=False)
        f.write("\n")


def relative_path(path):
    return path.relative_to(BASE_DIR).as_posix()


def unique_sorted(values):
    return sorted({value for value in values if value})


def without_general(values):
    return [value for value in values if value and value != "General"]


def tokenize(value):
    return {
        token
        for token in re.split(r"[^a-z0-9]+", str(value or "").lower())
        if token
    }


def singularize_token(token):
    if token.endswith("ies") and len(token) > 3:
        return f"{token[:-3]}y"
    if token.endswith("s") and len(token) > 3:
        return token[:-1]
    return token


def normalize_tokens(values):
    tokens = set()
    for value in values:
        for token in tokenize(value):
            tokens.add(token)
            tokens.add(singularize_token(token))
    return tokens


def cefr_allows(candidate_level, max_level):
    if not max_level or max_level not in CEFR_RANK:
        return True
    if not candidate_level or candidate_level not in CEFR_RANK:
        return False
    return CEFR_RANK[candidate_level] <= CEFR_RANK[max_level]


def normalize_allowed_pos(allowed_pos):
    normalized = set()
    for pos in allowed_pos or []:
        if pos == "phrase":
            normalized.add("noun")
        elif pos == "pronoun":
            normalized.add("noun")
        elif pos == "phrasal verb":
            normalized.add("verb")
        else:
            normalized.add(pos)
    return normalized


def source_pattern_id(pattern):
    return (
        pattern.get("authority_source", {}).get("source_record_id")
        or pattern.get("metadata", {}).get("source_record_id")
        or pattern.get("metadata", {}).get("pattern_id")
        or pattern.get("id")
    )


def node_sort_key(node):
    meta = node.get("metadata", {})
    frequency_rank = meta.get("frequency_rank")
    if not isinstance(frequency_rank, int):
        frequency_rank = 10**9
    frequency_score = meta.get("frequency_score")
    if not isinstance(frequency_score, (int, float)):
        frequency_score = -1
    return (frequency_rank, -frequency_score, node.get("id", ""))


def build_vocabulary_index(vocabulary_nodes):
    by_pos = defaultdict(list)
    for node in vocabulary_nodes or []:
        if node.get("node_type") != "vocabulary":
            continue
        meta = node.get("metadata", {})
        pos = meta.get("part_of_speech")
        if not pos:
            continue
        by_pos[pos].append(node)
    for nodes in by_pos.values():
        nodes.sort(key=node_sort_key)
    return by_pos


def theme_edge_sort_key(edge):
    confidence = edge.get("confidence", {}).get("value")
    if not isinstance(confidence, (int, float)):
        confidence = 0
    weight = edge.get("metadata", {}).get("weight")
    if not isinstance(weight, (int, float)):
        weight = 0
    role = edge.get("metadata", {}).get("retained_role") or edge.get("metadata", {}).get("membership_type")
    role_rank = {"primary": 0, "secondary": 1, "inferred_low_confidence": 2, "inferred": 3}.get(role, 9)
    return (-confidence, -weight, role_rank, edge.get("target_node_id", ""))


def build_vocabulary_theme_index(refined_edges, original_edges):
    source_edges = refined_edges if isinstance(refined_edges, list) and refined_edges else original_edges
    by_vocab = defaultdict(list)
    for edge in source_edges or []:
        source_id = edge.get("source_node_id")
        target_id = edge.get("target_node_id")
        if source_id and target_id and target_id != "General":
            by_vocab[source_id].append(edge)
    return {vocab_id: sorted(edges, key=theme_edge_sort_key) for vocab_id, edges in by_vocab.items()}


def build_chunk_indexes(chunk_nodes, enhanced_hint_mapping):
    chunk_by_id = {}
    hints_by_chunk_id = {}
    if isinstance(chunk_nodes, list):
        for node in chunk_nodes:
            node_id = node.get("id")
            if not node_id:
                continue
            chunk_by_id[node_id] = node
            meta = node.get("metadata", {})
            hints = []
            source_chunk_id = meta.get("source_chunk_id")
            enhanced = (enhanced_hint_mapping or {}).get(source_chunk_id, {})
            hints.extend(enhanced.get("enhanced_theme_hint") or [])
            hints.extend(meta.get("theme_hint") or [])
            hints_by_chunk_id[node_id] = without_general(unique_sorted(hints))
    return chunk_by_id, hints_by_chunk_id


def build_theme_hint_resolver(theme_nodes):
    candidates = []
    if not isinstance(theme_nodes, list):
        return candidates
    for node in theme_nodes:
        meta = node.get("metadata", {})
        theme_id = node.get("id")
        if not theme_id:
            continue
        tokens = normalize_tokens(
            [
                theme_id,
                meta.get("theme_id"),
                meta.get("parent_theme"),
                meta.get("description"),
            ]
        )
        candidates.append((theme_id, tokens))
    return candidates


def resolve_theme_hints_to_refs(hints, theme_hint_resolver):
    resolved = []
    for hint in without_general(hints):
        hint_tokens = normalize_tokens([hint])
        matches = []
        for theme_id, theme_tokens in theme_hint_resolver:
            overlap = hint_tokens & theme_tokens
            if overlap:
                matches.append((-len(overlap), theme_id))
        if matches:
            resolved.append(sorted(matches)[0][1])
    return unique_sorted(resolved)


def select_vocabulary_ids(slot_constraints, vocabulary_index, warnings, pattern_node_id):
    selected = []
    seen = set()
    for slot in slot_constraints:
        candidate_query = slot.get("candidate_query", {})
        allowed_pos = normalize_allowed_pos(
            candidate_query.get("allowed_pos") or slot.get("allowed_pos") or []
        )
        max_cefr = candidate_query.get("max_cefr") or slot.get("cefr_gate", {}).get("max_level")
        slot_found = False
        for pos in sorted(allowed_pos):
            for node in vocabulary_index.get(pos, []):
                if not cefr_allows(node.get("cefr_level"), max_cefr):
                    continue
                node_id = node.get("id")
                if not node_id or node_id in seen:
                    continue
                selected.append(node_id)
                seen.add(node_id)
                slot_found = True
                break
        if not slot_found:
            warnings.append(
                f"{pattern_node_id} has no vocabulary candidate for slot {slot.get('slot_id')}"
            )
        if len(selected) >= VOCABULARY_LIMIT_PER_OPPORTUNITY:
            break
    return selected[:VOCABULARY_LIMIT_PER_OPPORTUNITY]


def build_constraint_index(constraints):
    index = {}
    for record in constraints or []:
        pattern_node_id = record.get("pattern_node_id")
        if pattern_node_id:
            index[pattern_node_id] = record
    return index


def build_dependency_index(dependency_graph):
    index = defaultdict(list)
    for edge in (dependency_graph or {}).get("edges", []):
        if edge.get("relation") != "REQUIRES":
            continue
        source_id = edge.get("source_node_id")
        target_id = edge.get("target_node_id")
        if source_id and target_id:
            index[source_id].append(target_id)
    return {key: unique_sorted(values) for key, values in index.items()}


def dependency_metadata(focus_node_ids, dependency_index):
    requires = []
    for node_id in focus_node_ids:
        requires.extend(dependency_index.get(node_id, []))
    requires = unique_sorted(requires)
    status = "ready" if not requires else "unknown"
    return {
        "status": status,
        "missing_requires": [],
        "requires": requires,
    }


def theme_refs_from_vocabulary(vocabulary_ids, vocabulary_theme_index):
    weighted = Counter()
    for vocab_id in vocabulary_ids:
        for rank, edge in enumerate(vocabulary_theme_index.get(vocab_id, [])[:3], start=1):
            confidence = edge.get("confidence", {}).get("value")
            if not isinstance(confidence, (int, float)):
                confidence = 0.5
            weight = edge.get("metadata", {}).get("weight")
            if not isinstance(weight, (int, float)):
                weight = 0.5
            weighted[edge["target_node_id"]] += (confidence * weight) / rank
    return [theme for theme, _ in weighted.most_common(3)]


def consensus_theme_refs(vocabulary_ids, vocabulary_theme_index):
    votes = []
    for vocab_id in vocabulary_ids:
        edges = vocabulary_theme_index.get(vocab_id, [])
        if edges:
            votes.append(edges[0]["target_node_id"])
    if not votes:
        return []
    counts = Counter(votes)
    theme, count = counts.most_common(1)[0]
    if count / len(votes) >= 0.70:
        return [theme]
    return []


def theme_refs_from_chunks(chunk_ids, chunk_hint_index, theme_hint_resolver):
    hints = []
    for chunk_id in chunk_ids:
        hints.extend(chunk_hint_index.get(chunk_id, []))
    return resolve_theme_hints_to_refs(hints, theme_hint_resolver)


def collect_theme_refs(
    pattern,
    constraint_record,
    vocabulary_ids,
    chunk_ids,
    vocabulary_theme_index,
    chunk_hint_index,
    theme_hint_resolver,
    warnings,
):
    meta = pattern.get("metadata", {})
    theme_refs = without_general(meta.get("theme_refs") or [])
    if theme_refs:
        return unique_sorted(theme_refs), {"source": "pattern_theme_ref", "confidence": 1.0}

    slot_theme_refs = []
    if constraint_record:
        for slot in constraint_record.get("slot_constraints", []):
            slot_theme_refs.extend(slot.get("theme_gate", {}).get("allowed_theme_ids", []) or [])
    slot_theme_refs = without_general(unique_sorted(slot_theme_refs))
    if slot_theme_refs:
        return slot_theme_refs, {"source": "pattern_slot_gate", "confidence": 0.9}

    vocabulary_theme_refs = without_general(theme_refs_from_vocabulary(vocabulary_ids, vocabulary_theme_index))
    if vocabulary_theme_refs:
        return vocabulary_theme_refs, {"source": "vocabulary_theme", "confidence": 0.8}

    chunk_theme_refs = without_general(theme_refs_from_chunks(chunk_ids, chunk_hint_index, theme_hint_resolver))
    if chunk_theme_refs:
        return chunk_theme_refs, {"source": "chunk_theme_hint", "confidence": 0.7}

    consensus_refs = without_general(consensus_theme_refs(vocabulary_ids, vocabulary_theme_index))
    if consensus_refs:
        return consensus_refs, {"source": "theme_consensus", "confidence": 0.75}

    warnings.append(f"{pattern.get('id')} has no specific theme source; defaulted to General")
    return ["General"], {"source": "general_fallback", "confidence": 0.1}


def opportunity_id_for(index, level):
    safe_level = level if level in CEFR_RANK else "UNK"
    return f"LO_{safe_level}_{index:06d}"


def build_learning_opportunities():
    loaded = {path: read_json_optional(path) for path in INPUT_PATHS}
    missing_optional_inputs = [relative_path(path) for path, data in loaded.items() if data is None]
    warnings = []

    patterns = loaded[SENTENCE_PATTERNS_PATH] or []
    constraints = loaded[CONSTRAINTS_PATH] or []
    dependency_graph = loaded[DEPENDENCY_GRAPH_PATH] or {}
    vocabulary_nodes = loaded[VOCABULARY_NODES_PATH] or []
    theme_nodes = loaded[THEME_NODES_PATH] or []
    refined_vocabulary_theme_edges = loaded[VOCABULARY_THEME_EDGES_REFINED_PATH] or []
    vocabulary_theme_edges = loaded[VOCABULARY_THEME_EDGES_PATH] or []
    chunk_nodes = loaded[CHUNK_NODES_PATH] or []
    chunk_theme_hint_mapping = loaded[CHUNK_THEME_HINT_ENHANCED_PATH] or {}

    if not isinstance(patterns, list):
        warnings.append("sentence_patterns.json was not a list; emitted zero opportunities")
        patterns = []
    if not isinstance(constraints, list):
        warnings.append("pattern_vocabulary_constraints.json was not a list; vocabulary focus may be empty")
        constraints = []
    if not isinstance(vocabulary_nodes, list):
        warnings.append("vocabulary_nodes.json was not a list; vocabulary focus may be empty")
        vocabulary_nodes = []

    constraint_index = build_constraint_index(constraints)
    dependency_index = build_dependency_index(dependency_graph)
    vocabulary_index = build_vocabulary_index(vocabulary_nodes)
    vocabulary_theme_index = build_vocabulary_theme_index(refined_vocabulary_theme_edges, vocabulary_theme_edges)
    _, chunk_hint_index = build_chunk_indexes(chunk_nodes, chunk_theme_hint_mapping)
    theme_hint_resolver = build_theme_hint_resolver(theme_nodes)

    active_patterns = [
        pattern
        for pattern in patterns
        if pattern.get("metadata", {}).get("review_status") == "accepted"
        and pattern.get("metadata", {}).get("generator_allowed") is True
    ]
    active_patterns.sort(
        key=lambda pattern: (
            pattern.get("cefr_level") or pattern.get("metadata", {}).get("cefr_level") or "",
            source_pattern_id(pattern) or "",
            pattern.get("id") or "",
        )
    )

    opportunities = []
    default_theme_count = 0
    for index, pattern in enumerate(active_patterns, start=1):
        meta = pattern.get("metadata", {})
        pattern_node_id = pattern.get("id")
        constraint_record = constraint_index.get(pattern_node_id)
        slot_constraints = (constraint_record or {}).get("slot_constraints", [])
        level = pattern.get("cefr_level") or meta.get("cefr_level") or "unknown"
        vocabulary_ids = select_vocabulary_ids(slot_constraints, vocabulary_index, warnings, pattern_node_id)
        grammar_ids = unique_sorted(meta.get("grammar_refs", []))
        pattern_ids = [pattern_node_id] if pattern_node_id else []
        chunk_ids = unique_sorted(meta.get("chunk_refs", []))
        theme_warning_count_before = len(warnings)
        theme_refs, theme_confidence = collect_theme_refs(
            pattern,
            constraint_record,
            vocabulary_ids,
            chunk_ids,
            vocabulary_theme_index,
            chunk_hint_index,
            theme_hint_resolver,
            warnings,
        )
        if len(warnings) > theme_warning_count_before and theme_confidence["source"] == "general_fallback":
            default_theme_count += 1
        focus_node_ids = vocabulary_ids + grammar_ids + pattern_ids + chunk_ids
        dependency = dependency_metadata(focus_node_ids, dependency_index)
        dependency_score = 1.0 if dependency["status"] == "ready" else 0.5

        opportunity = {
            "opportunity_id": opportunity_id_for(index, level),
            "source_pattern_id": source_pattern_id(pattern),
            "candidate_type": "learning_opportunity",
            "level": level,
            "focus_nodes": {
                "vocabulary": vocabulary_ids,
                "grammar": grammar_ids,
                "pattern": pattern_ids,
                "chunk": chunk_ids,
            },
            "theme_refs": theme_refs,
            "theme_confidence": theme_confidence,
            "reinforces": {
                "vocabulary": [],
                "grammar": dependency["requires"],
                "pattern": [],
                "chunk": [],
            },
            "dependency": dependency,
            "ranking_features": {
                "dependency_score": dependency_score,
                "mastery_gap_score": None,
                "reinforcement_score": float(len(dependency["requires"])),
                "theme_continuity_score": None,
                "frequency_score": None,
                "pattern_utility_score": float(len(slot_constraints)),
            },
            "policy_flags": {
                "generator_ready": bool(meta.get("generator_allowed") is True),
                "requires_learner_state": False,
                "has_theme": bool(theme_refs),
                "has_pattern": bool(pattern_ids),
                "has_vocabulary": bool(vocabulary_ids),
                "has_grammar": bool(grammar_ids),
            },
            "source": SOURCE,
        }
        opportunities.append(opportunity)

    opportunities.sort(key=lambda item: (item["level"], item["source_pattern_id"], item["opportunity_id"]))
    for index, opportunity in enumerate(opportunities, start=1):
        opportunity["opportunity_id"] = opportunity_id_for(index, opportunity["level"])

    by_level = Counter(item["level"] for item in opportunities)
    by_theme = Counter(theme for item in opportunities for theme in item["theme_refs"])
    dependency_status_counts = Counter(item["dependency"]["status"] for item in opportunities)
    theme_source_distribution = Counter(
        item.get("theme_confidence", {}).get("source", "general_fallback") for item in opportunities
    )
    general_count = sum(1 for item in opportunities if item.get("theme_refs") == ["General"])
    specific_count = len(opportunities) - general_count
    specific_ratio = round(specific_count / len(opportunities), 6) if opportunities else 0.0
    policy_flag_counts = {
        flag: sum(1 for item in opportunities if item["policy_flags"].get(flag) is True)
        for flag in [
            "generator_ready",
            "requires_learner_state",
            "has_theme",
            "has_pattern",
            "has_vocabulary",
            "has_grammar",
        ]
    }

    if default_theme_count:
        warnings.append(f"{default_theme_count} opportunities defaulted theme_refs to General")
    if len(constraint_index) < len(active_patterns):
        warnings.append(
            f"{len(active_patterns) - len(constraint_index)} active patterns had no constraint record"
        )

    summary = {
        "status": "PASS_WITH_WARNINGS" if warnings or missing_optional_inputs else "PASS",
        "contract_version": CONTRACT_VERSION,
        "source": SOURCE,
        "total_opportunities": len(opportunities),
        "by_level": dict(sorted(by_level.items())),
        "by_theme": dict(sorted(by_theme.items())),
        "theme_source_distribution": dict(sorted(theme_source_distribution.items())),
        "theme_specificity": {
            "specific_count": specific_count,
            "general_count": general_count,
            "specific_ratio": specific_ratio,
        },
        "dependency_status_counts": dict(sorted(dependency_status_counts.items())),
        "policy_flag_counts": policy_flag_counts,
        "missing_optional_inputs": missing_optional_inputs,
        "warnings": warnings,
    }

    write_json(OPPORTUNITIES_OUT_PATH, opportunities)
    write_json(SUMMARY_OUT_PATH, summary)
    print(f"Learning Opportunity Authority build: {summary['status']}")
    print(f"Opportunities: {len(opportunities)}")
    print(f"Warnings: {len(warnings)}")
    return summary


if __name__ == "__main__":
    build_learning_opportunities()
