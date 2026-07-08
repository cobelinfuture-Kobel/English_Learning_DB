import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
DRAFTS_PATH = BASE / "ulga" / "learning_units" / "draft" / "a1_a1plus_clear_lane_learning_unit_draft_artifacts.json"
TASK_ID = "R7-M104E16B_A1A1PlusDraftArtifactFieldCompletionPatch_NoNewDesignDocs"

EXAMPLES = {
    "clauses_coordinated_form": "I have a pen and a book.",
    "clauses_declarative_form": "This is my bag.",
    "clauses_interrogatives_form": "Where is my book?",
    "clauses_subordinated_form_use": "I am happy because I am at home.",
    "pronouns_indefinite_thing_one_body_etc_form": "Someone is at the door.",
    "verbs_patterns_with_to_and_ing_form": "I want to play.",
    "pronouns_subject_object_form": "She sees him.",
    "adjectives_position_form": "It is a red ball.",
    "determiners_articles_form": "I have a book.",
    "determiners_articles_form_use": "The book is on the table.",
    "determiners_demonstratives_use": "This book is blue.",
    "determiners_quantity_form": "I have two pencils.",
    "nouns_plural_form": "I have two books.",
    "prepositions_prepostions_form": "The cat is on the chair.",
    "verbs_prepositional_form": "I look at the picture.",
    "nouns_noun_phrases_form": "The big dog runs.",
    "nouns_noun_phrases_grammatical_functions_form": "The girl sees a dog.",
    "questions_yes_no_form": "Is it a book?",
    "nouns_types_form": "A book is a count noun.",
}

NEGATIVE_EXAMPLES = {
    "adjectives_position_form": "It is a ball red.",
    "determiners_articles_form": "I have book.",
    "determiners_articles_form_use": "A book on the table is the first mention.",
    "determiners_demonstratives_use": "This are books.",
    "determiners_quantity_form": "I have many pencil.",
    "nouns_plural_form": "I have two book.",
    "prepositions_prepostions_form": "The cat is chair.",
    "questions_yes_no_form": "It is a book?",
}


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def evidence(cluster_id):
    return {
        "primary": [f"EGP_ROW_CLUSTER:{cluster_id}"],
        "support": ["EVP_SUPPORT", "RAZ_SUPPORT"],
        "context": ["CAMBRIDGE_EXAM_CONTEXT_ONLY"],
        "policy": "BALANCED_SOURCE_GROUNDED",
    }


def base_meta(cluster_id, cluster_key):
    return {
        "patch_status": "draft_field_completed_not_canonical",
        "source_cluster_id": cluster_id,
        "source_cluster_key": cluster_key,
        "evidence": evidence(cluster_id),
        "requires_operator_review_before_promotion": True,
    }


def slot_model(cluster_id, cluster_key, unit):
    head = unit.get("phrase_head_type", "phrase")
    meta = base_meta(cluster_id, cluster_key)
    meta.update({
        "model_type": "phrase_slot_model",
        "phrase_head_type": head,
        "slots": [
            {"slot": "modifier_or_determiner", "required": False},
            {"slot": "head", "required": True, "head_type": head},
            {"slot": "complement", "required": False},
        ],
    })
    return meta


def head_pattern(cluster_id, cluster_key, unit):
    meta = base_meta(cluster_id, cluster_key)
    meta.update({
        "model_type": "construction_head_pattern",
        "construction_type": unit.get("construction_type", "construction"),
        "head": cluster_key.split("|")[0].strip().lower(),
        "pattern_scope": cluster_key,
    })
    return meta


def complement_model(cluster_id, cluster_key, unit):
    meta = base_meta(cluster_id, cluster_key)
    meta.update({
        "model_type": "construction_complement_model",
        "construction_type": unit.get("construction_type", "construction"),
        "complements": [
            {"slot": "required_complement", "required": False},
            {"slot": "optional_expansion", "required": False},
        ],
    })
    return meta


def sentence_role_model(cluster_id, cluster_key):
    meta = base_meta(cluster_id, cluster_key)
    meta.update({
        "model_type": "sentence_role_model",
        "roles": [
            {"role": "subject", "required": True},
            {"role": "predicate", "required": True},
            {"role": "object_or_complement", "required": False},
        ],
    })
    return meta


def slot_sequence(cluster_id, cluster_key):
    return [
        {"slot": "subject", "required": True, "source_cluster_id": cluster_id, "source_cluster_key": cluster_key, "evidence": evidence(cluster_id)},
        {"slot": "verb_or_be", "required": True, "source_cluster_id": cluster_id, "source_cluster_key": cluster_key, "evidence": evidence(cluster_id)},
        {"slot": "object_or_complement", "required": False, "source_cluster_id": cluster_id, "source_cluster_key": cluster_key, "evidence": evidence(cluster_id)},
    ]


def component_refs(cluster_id):
    return [
        f"candidate_component:{cluster_id}:subject_role",
        f"candidate_component:{cluster_id}:object_role",
    ]


def composition_rule(cluster_id, cluster_key):
    meta = base_meta(cluster_id, cluster_key)
    meta.update({
        "model_type": "composite_learning_unit_rule",
        "rule": "combine role-specific component nodes only after source review",
        "component_selection_policy": "existing_or_operator_reviewed_component_refs_only",
    })
    return meta


def role_mapping(cluster_id, cluster_key):
    meta = base_meta(cluster_id, cluster_key)
    meta.update({
        "model_type": "composite_role_mapping",
        "roles": {
            "subject_form": "subject_position",
            "object_form": "object_position",
        },
    })
    return meta


def constraints_for(cluster_id, cluster_key):
    return [{
        "constraint_id": f"constraint:{cluster_id}",
        "constraint_status": "draft_field_completed_not_canonical",
        "description": f"Use only within the A1/A1+ source cluster scope: {cluster_key}.",
        "evidence": evidence(cluster_id),
    }]


def usage_constraint_evidence(cluster_id, cluster_key):
    return {
        "patch_status": "draft_field_completed_not_canonical",
        "constraint_scope": cluster_key,
        "evidence": evidence(cluster_id),
        "requires_operator_review_before_promotion": True,
    }


def patch_examples(unit, cluster_id):
    example = EXAMPLES.get(cluster_id, "This is an A1 sentence.")
    if "positive_examples" in unit:
        unit["positive_examples"] = [example]
    if "negative_examples" in unit:
        unit["negative_examples"] = [NEGATIVE_EXAMPLES[cluster_id]] if cluster_id in NEGATIVE_EXAMPLES else []
    if "examples" in unit:
        unit["examples"] = [example]


def patch_unit(artifact):
    cluster = artifact["source_cluster"]
    cluster_id = cluster["cluster_id"]
    cluster_key = cluster["cluster_key"]
    unit = artifact["draft_learning_unit"]
    lut = unit["learning_unit_type"]
    patched = 0

    if lut == "CONSTRUCTION_NODE":
        unit["head_pattern"] = head_pattern(cluster_id, cluster_key, unit)
        unit["complement_model"] = complement_model(cluster_id, cluster_key, unit)
        unit["constraints"] = constraints_for(cluster_id, cluster_key)
        patched += 2
    elif lut == "PHRASE_PATTERN_NODE":
        unit["slot_model"] = slot_model(cluster_id, cluster_key, unit)
        unit["constraints"] = constraints_for(cluster_id, cluster_key)
        patched += 1
    elif lut == "SENTENCE_PATTERN_NODE":
        unit["sentence_role_model"] = sentence_role_model(cluster_id, cluster_key)
        unit["slot_sequence"] = slot_sequence(cluster_id, cluster_key)
        patched += 2
    elif lut == "MULTI_NODE_COMPOSITE":
        unit["component_node_refs"] = component_refs(cluster_id)
        unit["composition_rule"] = composition_rule(cluster_id, cluster_key)
        unit["role_mapping"] = role_mapping(cluster_id, cluster_key)
        patched += 3
    elif lut == "USAGE_CONSTRAINT":
        unit["allowed_values"] = ["count_noun", "uncount_noun", "proper_noun"]
        unit["blocked_values"] = ["unreviewed_noun_type_promotion"]
        unit["constraint_evidence"] = usage_constraint_evidence(cluster_id, cluster_key)

    patch_examples(unit, cluster_id)
    patched += 1
    artifact["field_completion_patch"] = {
        "task_id": TASK_ID,
        "patch_status": "PATCHED_DRAFT_FIELDS_NOT_CANONICAL",
        "patched_field_count": patched,
        "coverage_credit_now": 0,
        "requires_operator_review_before_promotion": True,
        "canonical_grammar_write_allowed": False,
        "canonical_pattern_write_allowed": False,
    }
    return patched


def main():
    data = load_json(DRAFTS_PATH)
    artifacts = data.get("draft_artifacts", [])
    if len(artifacts) != 19:
        raise ValueError(f"Expected 19 draft artifacts, got {len(artifacts)}")
    patched_fields = 0
    for artifact in artifacts:
        patched_fields += patch_unit(artifact)
    data["field_completion_patch_metadata"] = {
        "task_id": TASK_ID,
        "patch_status": "PATCHED_DRAFT_FIELDS_NOT_CANONICAL",
        "draft_artifact_count": len(artifacts),
        "patched_field_count": patched_fields,
        "coverage_credit_now": 0,
        "new_design_docs_created": False,
        "new_planning_docs_created": False,
        "canonical_grammar_write_allowed": False,
        "canonical_pattern_write_allowed": False,
        "a2_a2plus_progression_allowed": False,
        "next_short_step": "R7-M104E16C_A1A1PlusCoverageRecheckAfterDraftPatch_NoNewDesignDocs",
    }
    write_json(DRAFTS_PATH, data)
    print("A1/A1+ draft artifact field completion patch: PASS")
    print("Draft artifacts patched:", len(artifacts))
    print("Patched fields:", patched_fields)
    print("Coverage credit now: 0")


if __name__ == "__main__":
    main()
