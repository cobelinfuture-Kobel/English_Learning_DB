import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

SENTENCE_PATTERNS_PATH = BASE_DIR / "ulga" / "graph" / "sentence_patterns.json"
CONSTRAINTS_OUT_PATH = BASE_DIR / "ulga" / "graph" / "pattern_vocabulary_constraints.json"
QUERY_CONTRACT_OUT_PATH = BASE_DIR / "ulga" / "graph" / "pattern_vocabulary_candidate_query_contract.json"
SUMMARY_OUT_PATH = BASE_DIR / "ulga" / "reports" / "pattern_vocabulary_constraint_summary.json"

CONTRACT_VERSION = "S7D_v1"
ACTIVE_LIMIT_DEFAULT = 50
ACTIVE_LIMIT_MAX = 200

CEFR_ORDER = ["A1", "A2", "B1", "B2", "C1", "C2"]

SLOT_COMPATIBILITY_RULES = {
    "noun_phrase": {
        "compatibility_classes": ["common_noun_phrase", "generic_object"],
        "allowed_pos": ["noun", "phrase", "pronoun"],
        "requires_countability": True,
    },
    "noun_phrase_1": {
        "compatibility_classes": ["common_noun_phrase", "generic_object"],
        "allowed_pos": ["noun", "phrase", "pronoun"],
        "requires_countability": True,
    },
    "noun_phrase_2": {
        "compatibility_classes": ["common_noun_phrase", "generic_object"],
        "allowed_pos": ["noun", "phrase", "pronoun"],
        "requires_countability": True,
    },
    "sth": {
        "compatibility_classes": ["common_noun_phrase", "generic_object"],
        "allowed_pos": ["noun", "phrase"],
        "thing_only": True,
        "requires_countability": True,
    },
    "sb": {
        "compatibility_classes": ["person_entity", "generic_person"],
        "allowed_pos": ["noun", "pronoun", "phrase"],
        "person_only": True,
    },
    "proper_noun": {
        "compatibility_classes": ["person_entity"],
        "allowed_pos": ["noun"],
        "person_only": True,
    },
    "name": {
        "compatibility_classes": ["person_entity"],
        "allowed_pos": ["noun"],
        "person_only": True,
    },
    "adjective": {
        "compatibility_classes": ["descriptive_adjective"],
        "allowed_pos": ["adjective"],
    },
    "verb": {
        "compatibility_classes": ["action_verb"],
        "allowed_pos": ["verb", "phrasal verb"],
    },
    "verb_stem": {
        "compatibility_classes": ["action_verb"],
        "allowed_pos": ["verb", "phrasal verb"],
    },
    "base_verb": {
        "compatibility_classes": ["action_verb"],
        "allowed_pos": ["verb", "phrasal verb"],
    },
    "verb_gerund": {
        "compatibility_classes": ["activity_gerund"],
        "allowed_pos": ["verb", "phrasal verb"],
        "requires_gerund_capable": True,
    },
    "gerund": {
        "compatibility_classes": ["activity_gerund"],
        "allowed_pos": ["verb", "phrasal verb"],
        "requires_gerund_capable": True,
    },
    "verb_infinitive": {
        "compatibility_classes": ["action_verb"],
        "allowed_pos": ["verb", "phrasal verb"],
    },
    "infinitive": {
        "compatibility_classes": ["action_verb"],
        "allowed_pos": ["verb", "phrasal verb"],
    },
    "time": {
        "compatibility_classes": ["time_expression"],
        "allowed_pos": ["noun", "phrase", "adverb"],
    },
    "time_phrase": {
        "compatibility_classes": ["time_expression"],
        "allowed_pos": ["noun", "phrase", "adverb"],
    },
    "location": {
        "compatibility_classes": ["location_entity"],
        "allowed_pos": ["noun", "phrase"],
        "location_only": True,
    },
}


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def unique_sorted(values):
    return sorted({value for value in values if value})


def normalize_slot_type(slot_type):
    aliases = {
        "noun": "noun_phrase",
        "plural_noun": "noun_phrase",
        "singular_noun": "noun_phrase",
        "count_noun_phrase": "noun_phrase",
        "mass_noun": "noun_phrase",
        "object": "sth",
        "person": "sb",
        "activity": "verb_gerund",
        "place": "location",
        "verb_phrase": "verb",
    }
    return aliases.get(slot_type, slot_type)


def rule_for_slot_type(slot_type):
    normalized = normalize_slot_type(slot_type)
    return SLOT_COMPATIBILITY_RULES.get(
        normalized,
        {
            "compatibility_classes": ["generic_object"],
            "allowed_pos": ["noun", "phrase"],
            "requires_countability": True,
        },
    )


def frequency_bands_for_level(cefr_level):
    if cefr_level in {"A1", "A2"}:
        return ["core", "common"]
    return ["core", "common", "extended"]


def theme_gate_for_pattern(meta):
    source = meta.get("source")
    theme_refs = meta.get("theme_refs", [])
    if source == "MANUAL_A1_CORE_PATTERN" and theme_refs:
        return {
            "mode": "hard_filter",
            "allowed_theme_ids": theme_refs,
            "inherit_from_pattern_theme_refs": True,
        }
    if source == "CHUNK_GRAMMAR_METADATA_DERIVED":
        return {
            "mode": "soft_filter",
            "allowed_theme_ids": [],
            "inherit_from_pattern_theme_refs": False,
        }
    return {
        "mode": "none",
        "allowed_theme_ids": [],
        "inherit_from_pattern_theme_refs": False,
    }


def merge_slot_rules(slot):
    slot_type = slot.get("slot_type")
    raw_types = slot.get("allowed_slot_types") if slot_type == "multi_type" else [slot_type]
    raw_types = raw_types or [slot_type]

    compatibility_classes = []
    allowed_pos = []
    flags = {
        "requires_gerund_capable": False,
        "requires_plural_capable": False,
        "requires_countability": False,
        "person_only": False,
        "thing_only": False,
        "location_only": False,
    }

    for raw_type in raw_types:
        rule = rule_for_slot_type(raw_type)
        compatibility_classes.extend(rule.get("compatibility_classes", []))
        allowed_pos.extend(rule.get("allowed_pos", []))
        for flag in flags:
            flags[flag] = flags[flag] or bool(rule.get(flag, False))

    return {
        "compatibility_classes": unique_sorted(compatibility_classes),
        "allowed_pos": unique_sorted(allowed_pos),
        **flags,
    }


def build_slot_constraint(slot, meta):
    cefr_level = meta.get("cefr_level")
    merged = merge_slot_rules(slot)
    theme_gate = theme_gate_for_pattern(meta)
    frequency_bands = frequency_bands_for_level(cefr_level)

    return {
        "slot_id": slot.get("slot_id"),
        "slot_label": slot.get("slot_label"),
        "slot_type": slot.get("slot_type"),
        "allowed_slot_types": slot.get("allowed_slot_types", []),
        "compatibility_classes": merged["compatibility_classes"],
        "allowed_pos": merged["allowed_pos"],
        "cefr_gate": {
            "mode": "max_cefr",
            "max_level": cefr_level,
            "allow_lower": True,
            "allow_plus_one_for_review": False,
        },
        "theme_gate": theme_gate,
        "frequency_hint": {
            "mode": "ranking_signal",
            "preferred_bands": frequency_bands,
            "low_frequency_allowed": True,
        },
        "morphology_requirements": {
            "requires_gerund_capable": merged["requires_gerund_capable"],
            "requires_plural_capable": merged["requires_plural_capable"],
            "requires_countability": merged["requires_countability"],
        },
        "candidate_query": {
            "allowed_pos": merged["allowed_pos"],
            "max_cefr": cefr_level,
            "theme_mode": theme_gate["mode"],
            "frequency_mode": "ranking_signal",
            "limit_default": ACTIVE_LIMIT_DEFAULT,
        },
        "person_only": merged["person_only"],
        "thing_only": merged["thing_only"],
        "location_only": merged["location_only"],
    }


def build_query_contract():
    return {
        "contract_version": CONTRACT_VERSION,
        "limit_default": ACTIVE_LIMIT_DEFAULT,
        "limit_max": ACTIVE_LIMIT_MAX,
        "query_inputs": {
            "pattern_id": "required",
            "slot_id": "required",
            "learner_id": "optional",
            "theme_context": "optional",
            "cefr_ceiling": "optional",
            "limit": "optional",
        },
        "gate_order": [
            "review_status",
            "generator_allowed",
            "slot_constraint",
            "cefr_gate",
            "pos_gate",
            "morphology_gate",
        ],
        "ranking_signals": [
            "theme_match",
            "frequency_band",
            "learner_mastery_gap",
            "recency",
            "diversity",
        ],
        "output_shape": {
            "vocabulary_node_id": "string",
            "lemma": "string",
            "pos": "string",
            "cefr_level": "string",
            "theme_ids": "array",
            "frequency_band": "string",
            "score": "number",
            "reasons": "array",
        },
        "materialization_policy": {
            "full_pattern_vocabulary_edges": False,
            "candidate_pool_generated_at_query_time": True,
        },
    }


def build_constraints(patterns):
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    constraints = []
    skipped_patterns = []
    slot_type_counts = Counter()
    compatibility_counts = Counter()
    cefr_counts = Counter()
    theme_counts = Counter()
    frequency_counts = Counter()

    for node in patterns:
        meta = node.get("metadata", {})
        is_active = meta.get("review_status") == "accepted" and meta.get("generator_allowed") is True
        slots = meta.get("slots", [])
        if not is_active:
            skipped_patterns.append(
                {
                    "pattern_node_id": node.get("id"),
                    "review_status": meta.get("review_status"),
                    "generator_allowed": meta.get("generator_allowed"),
                    "reason": "inactive_review_status_or_generator_blocked",
                }
            )
            continue

        slot_constraints = [build_slot_constraint(slot, meta) for slot in slots]
        for constraint in slot_constraints:
            slot_type_counts[constraint["slot_type"]] += 1
            cefr_counts[constraint["cefr_gate"]["max_level"]] += 1
            theme_counts[constraint["theme_gate"]["mode"]] += 1
            frequency_counts[constraint["frequency_hint"]["mode"]] += 1
            for compat in constraint["compatibility_classes"]:
                compatibility_counts[compat] += 1

        constraints.append(
            {
                "contract_version": CONTRACT_VERSION,
                "active": True,
                "pattern_id": node.get("authority_source", {}).get("source_record_id"),
                "pattern_node_id": node.get("id"),
                "canonical_pattern": meta.get("canonical_pattern"),
                "source": meta.get("source"),
                "cefr_level": meta.get("cefr_level"),
                "review_status": meta.get("review_status"),
                "generator_allowed": meta.get("generator_allowed"),
                "slot_constraints": slot_constraints,
                "authority_source": {
                    "source_name": "ULGA Pattern Vocabulary Constraint Builder",
                    "source_file": "ulga/builders/build_pattern_vocabulary_constraints.py",
                    "derivation": "rule_based",
                },
                "version": {
                    "contract": CONTRACT_VERSION,
                    "source_version": "1.0.0",
                    "generated_at": generated_at,
                },
            }
        )

    summary = {
        "stage": "ULGA-S7D",
        "contract_version": CONTRACT_VERSION,
        "source_pattern_count": len(patterns),
        "active_constraint_count": len(constraints),
        "inactive_skipped_pattern_count": len(skipped_patterns),
        "slot_constraint_count": sum(len(record["slot_constraints"]) for record in constraints),
        "slot_type_distribution": dict(slot_type_counts),
        "compatibility_class_distribution": dict(compatibility_counts),
        "cefr_gate_distribution": dict(cefr_counts),
        "theme_gate_distribution": dict(theme_counts),
        "frequency_hint_distribution": dict(frequency_counts),
        "candidate_query_limit_default": ACTIVE_LIMIT_DEFAULT,
        "full_pattern_vocabulary_edges_generated": False,
        "skipped_pattern_samples": skipped_patterns[:20],
    }

    return constraints, summary


def main():
    print("Building Pattern Vocabulary Constraint layer...")
    patterns = load_json(SENTENCE_PATTERNS_PATH)
    constraints, summary = build_constraints(patterns)
    query_contract = build_query_contract()

    write_json(CONSTRAINTS_OUT_PATH, constraints)
    write_json(QUERY_CONTRACT_OUT_PATH, query_contract)
    write_json(SUMMARY_OUT_PATH, summary)

    print(f"Wrote {len(constraints)} active constraints to {CONSTRAINTS_OUT_PATH}")
    print(f"Wrote candidate query contract to {QUERY_CONTRACT_OUT_PATH}")
    print(f"Wrote summary to {SUMMARY_OUT_PATH}")
    print("Pattern Vocabulary Constraint build complete.")


if __name__ == "__main__":
    main()
