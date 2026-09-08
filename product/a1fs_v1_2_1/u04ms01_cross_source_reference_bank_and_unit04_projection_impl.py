from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

TASK_ID = "A1FS-V1-U04MS01_CrossSourceReferenceBankAndUnit04Projection"
STATUS = "PASS_A1FS_V1_U04MS01_CROSS_SOURCE_REFERENCE_BANK_AND_UNIT04_PROJECTION"
A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Read-only cross-source reference projection over existing canonical/derived authorities; "
    "does not author or promote learner-facing content."
)

CAMBRIDGE_MOVERS_FORMAT_URL = (
    "https://www.cambridgeenglish.org/exams-and-tests/qualifications/young-learners/"
    "paper/movers/format/"
)
CAMBRIDGE_MOVERS_DIGITAL_FORMAT_URL = (
    "https://www.cambridgeenglish.org/exams-and-tests/qualifications/young-learners/"
    "digital/movers/format/"
)
IELTS_GENERAL_SAMPLE_URL = (
    "https://www.ielts.org/take-a-test/preparation-resources/sample-test-questions/"
    "general-training-test"
)

Q02 = "ulga/contracts/a1fs_v1_u04_q02_vocabulary_authority.json"
Q04 = "ulga/contracts/a1fs_v1_u04_q04_place_chunk_authority.json"
Q05 = "ulga/contracts/a1fs_v1_u04_q05_core_sentence_frame_authority.json"
Q06 = "ulga/contracts/a1fs_v1_u04_q06_sentence_assets.json"


class ProjectionError(ValueError):
    pass


def _repo_root(repo_root: Path | str | None = None) -> Path:
    if repo_root is not None:
        return Path(repo_root).resolve()
    return Path(__file__).resolve().parents[2]


def _load_json(path: Path) -> Any:
    if not path.is_file():
        raise ProjectionError(f"required_source_missing:{path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _records(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [row for row in value if isinstance(row, dict)]
    if not isinstance(value, dict):
        return []
    for key in ("records", "items", "entries", "rows", "vocabulary", "assets", "chunks"):
        rows = value.get(key)
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    values = list(value.values())
    if values and all(isinstance(row, dict) for row in values):
        return values
    return []


def _first(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _level(row: dict[str, Any]) -> str:
    value = _first(row, "level", "cefr", "cefr_level", "curriculum_level")
    return value.upper().replace(" ", "_")


def _pos(row: dict[str, Any]) -> str:
    value = _first(row, "part_of_speech", "pos", "original_part_of_speech")
    return value.casefold().replace(" ", "_") or "unknown"


def _surface(row: dict[str, Any]) -> str:
    return _first(row, "chunk", "surface", "word", "base_word", "lemma", "text")


def _path_entry(root: Path, *relative_paths: str) -> dict[str, Any]:
    checks = [(relative, (root / relative).exists()) for relative in relative_paths]
    existing = [relative for relative, exists in checks if exists]
    return {
        "candidate_locators": list(relative_paths),
        "resolved_locators": existing,
        "integration_anchor_resolved": bool(existing),
    }


def _source_registry(root: Path) -> list[dict[str, Any]]:
    registry = [
        {
            "source_id": "EGP",
            "authority_role": "GRAMMAR_CEFR_AUTHORITY",
            "learner_facing_authority": False,
            "canonical_promotion_allowed": True,
            "use_policy": "Grammar identity/CEFR evidence; current Unit01-04 authority still controls unlock.",
            **_path_entry(
                root,
                "grammar_profile/source/English Grammar Profile Online.xlsx",
                "grammar_profile/json/grammar_profile.json",
            ),
        },
        {
            "source_id": "EVP",
            "authority_role": "LEXICAL_SENSE_CEFR_AUTHORITY",
            "learner_facing_authority": False,
            "canonical_promotion_allowed": True,
            "use_policy": "Canonical lexical sense/CEFR identity; not a unit exposure claim by itself.",
            **_path_entry(
                root,
                "vocabulary/source/English Vocabulary Profile Online.xlsx",
                "vocabulary/json/vocabulary_active.json",
            ),
        },
        {
            "source_id": "NGSL_SFI",
            "authority_role": "FREQUENCY_PRIORITY_EVIDENCE",
            "learner_facing_authority": False,
            "canonical_promotion_allowed": False,
            "use_policy": "Ranking/usefulness evidence only; never overrides EVP/Unit authority.",
            **_path_entry(
                root,
                "vocabulary/source/NGSL+with+SFI+(31K).xlsx",
                "vocabulary/mapping/frequency_ranking.json",
            ),
        },
        {
            "source_id": "GLOBAL_CHUNK_AUTHORITY",
            "authority_role": "CANONICAL_CHUNK_AND_GENERATOR_SAFE_REFERENCE",
            "learner_facing_authority": False,
            "canonical_promotion_allowed": True,
            "use_policy": "Canonical/equivalence/usage/safe-layer reference; Unit projection controls use.",
            **_path_entry(
                root,
                "chunk_profile/json/chunks.json",
                "chunk_profile/json/chunk_equivalence_groups.json",
                "chunk_profile/json/chunk_usage_class_mapping.json",
                "chunk_profile/json/chunks_generator_safe.json",
            ),
        },
        {
            "source_id": "CAMBRIDGE_OFFICIAL",
            "authority_role": "YLE_KET_CHILD_STAGE_AND_ASSESSMENT_REFERENCE",
            "learner_facing_authority": False,
            "canonical_promotion_allowed": False,
            "use_policy": "Task mechanics/child-stage evidence; do not copy official question wording.",
            "official_urls": [CAMBRIDGE_MOVERS_FORMAT_URL, CAMBRIDGE_MOVERS_DIGITAL_FORMAT_URL],
            **_path_entry(root, "vocabulary/cambridge/authority_candidates"),
        },
        {
            "source_id": "IELTS_OFFICIAL",
            "authority_role": "TASK_MECHANICS_REFERENCE_ONLY",
            "learner_facing_authority": False,
            "canonical_promotion_allowed": False,
            "use_policy": "May borrow information-processing mechanics only; IELTS language difficulty is prohibited.",
            "official_urls": [IELTS_GENERAL_SAMPLE_URL],
            **_path_entry(root, "vocabulary/cambridge/ielts_analysis"),
        },
        {
            "source_id": "KET_FOUR_SKILL_PREREQUISITE",
            "authority_role": "FORMAL_PREREQUISITE_AND_RESOURCE_EVIDENCE",
            "learner_facing_authority": False,
            "canonical_promotion_allowed": False,
            "use_policy": "Existing A1FS prerequisite/resource evidence; no second curriculum graph.",
            "private_body_policy": "PRIVATE_OR_DERIVED_CONSUMER_INPUT",
            **_path_entry(
                root,
                "ulga/builders/cp07b_ket99_canonical_mapping_and_instructional_sequence_overlay_impl.py",
                "tests/ulga/test_a1fs_v1_cp07b_ket99_canonical_mapping_and_instructional_sequence_overlay.py",
            ),
        },
        {
            "source_id": "KET99_SRT",
            "authority_role": "NON_AUTHORITATIVE_TEACHER_DELIVERY_DIALOGUE_USAGE_EVIDENCE",
            "learner_facing_authority": False,
            "canonical_promotion_allowed": False,
            "use_policy": "P004-P102 derived transcript evidence only; raw transcript remains private.",
            "private_body_policy": "RAW_TEXT_PRIVATE_ONLY",
            **_path_entry(
                root,
                "ulga/builders/build_ket_comp_transcript_final_consolidation.py",
                ".github/workflows/ket99-srt-one-shot-publication.yml",
            ),
        },
        {
            "source_id": "RAZ_AW",
            "authority_role": "NON_AUTHORITATIVE_READING_CONTEXT_EXPOSURE_EVIDENCE",
            "learner_facing_authority": False,
            "canonical_promotion_allowed": False,
            "use_policy": "Approved/derived context evidence; never overrides EGP/EVP/current Unit authority.",
            "private_body_policy": "RAW_AND_ADMITTED_BODIES_PRIVATE_OR_DERIVED",
            **_path_entry(root, "ulga/builders/build_raz_ai_acl_v1_s05_material_registry.py"),
        },
        {
            "source_id": "UNIT01_04_AUTHORITY",
            "authority_role": "CURRENT_LEARNER_EXPOSURE_AND_UNIT_SCOPE_AUTHORITY",
            "learner_facing_authority": True,
            "canonical_promotion_allowed": False,
            "use_policy": "Controls what Unit04 may expose/assess after cumulative Unit01-03 reuse.",
            **_path_entry(root, Q02, Q04, Q05, Q06),
        },
    ]
    return registry


def _vocabulary_reference(root: Path) -> dict[str, Any]:
    path = root / "vocabulary/json/vocabulary_active.json"
    rows = _records(_load_json(path))
    by_level = Counter(_level(row) or "UNKNOWN" for row in rows)
    a1_rows = [row for row in rows if _level(row) in {"A1", "PRE_A1", "PRE-A1"}]
    pos = Counter(_pos(row) for row in a1_rows)
    return {
        "source": str(path.relative_to(root)),
        "count_semantics": "REFERENCE_ELIGIBLE_ACTIVE_CANONICAL_LEXICAL_ROWS_NOT_LEARNER_EXPOSURE",
        "active_row_count": len(rows),
        "by_level": dict(sorted(by_level.items())),
        "a1_reference_row_count": len(a1_rows),
        "a1_pos_counts": dict(sorted(pos.items())),
        "requested_pos_counts": {
            "nouns": sum(count for key, count in pos.items() if key.startswith("noun")),
            "verbs": sum(count for key, count in pos.items() if key.startswith("verb")),
            "adjectives": sum(count for key, count in pos.items() if key.startswith("adjective")),
            "adverbs": sum(count for key, count in pos.items() if key.startswith("adverb")),
        },
    }


def _chunk_reference(root: Path, place_relations: Iterable[str]) -> dict[str, Any]:
    path = root / "chunk_profile/json/chunks_generator_safe.json"
    rows = [row for row in _records(_load_json(path)) if row.get("generator_allowed", True)]
    by_level = Counter(_level(row) or "UNKNOWN" for row in rows)
    a1_rows = [row for row in rows if _level(row) in {"A1", "PRE_A1", "PRE-A1"}]
    usage = Counter(_first(row, "usage_class") or "unknown" for row in a1_rows)
    relation_prefixes = tuple(f"{value.casefold()} " for value in sorted(set(place_relations), key=len, reverse=True))

    def is_question(row: dict[str, Any]) -> bool:
        text = _surface(row).strip().casefold()
        if text.endswith("?"):
            return True
        return bool(re.match(r"^(who|what|where|when|why|how|which|whose|is|are|do|does|can|have|has)\b", text))

    question_count = sum(is_question(row) for row in a1_rows)
    dialogue_classes = {"discourse_marker", "opinion_expression", "evaluation_expression"}
    functional_classes = dialogue_classes | {"frequency_expression", "sentence_adverbial"}
    return {
        "source": str(path.relative_to(root)),
        "count_semantics": "REFERENCE_ONLY_GENERATOR_SAFE_ROWS; PROXIES ARE NOT CANONICAL NP/VP AUTHORITIES",
        "generator_safe_row_count": len(rows),
        "by_level": dict(sorted(by_level.items())),
        "a1_reference_row_count": len(a1_rows),
        "a1_usage_class_counts": dict(sorted(usage.items())),
        "requested_category_proxies": {
            "noun_phrases": {
                "count": usage.get("compound_noun", 0),
                "rule": "usage_class=compound_noun; conservative proxy, not all noun phrases",
            },
            "verb_phrases": {
                "count": usage.get("phrasal_verb", 0),
                "rule": "usage_class=phrasal_verb only; lower-bound proxy, not all verb phrases",
            },
            "time_phrases": {
                "count": usage.get("time_phrase", 0),
                "rule": "usage_class=time_phrase",
            },
            "question_chunks": {
                "count": question_count,
                "rule": "question-mark or deterministic interrogative/question-auxiliary prefix",
            },
            "dialogue_chunks": {
                "count": sum(1 for row in a1_rows if _first(row, "usage_class") in dialogue_classes or is_question(row)),
                "rule": "question proxy OR discourse/opinion/evaluation usage class",
            },
            "functional_chunks": {
                "count": sum(1 for row in a1_rows if _first(row, "usage_class") in functional_classes or is_question(row)),
                "rule": "question proxy OR discourse/opinion/evaluation/frequency/sentence-adverbial class",
            },
            "a1_place_phrase_reference_lower_bound": {
                "count": sum(_surface(row).casefold().startswith(relation_prefixes) for row in a1_rows if relation_prefixes),
                "rule": "surface begins with a current Unit04 target/support relation; reference-only lower bound",
            },
        },
    }


def _validate_authorities(q02: dict[str, Any], q04: dict[str, Any], q05: dict[str, Any], q06: dict[str, Any]) -> None:
    expected = {
        "q02": (q02.get("status"), "PASS_Q02_UNIT04_VOCABULARY_AUTHORITY_LOCK"),
        "q04": (q04.get("status"), "PASS_Q04_UNIT04_PLACE_CHUNK_AUTHORITY_AND_CUMULATIVE_DEDUP"),
        "q05": (q05.get("status"), "PASS_Q05_UNIT04_CORE_SENTENCE_FRAME_AUTHORITY"),
        "q06": (q06.get("status"), "PASS_Q06_UNIT04_SENTENCE_ASSET_PRODUCTION_AND_SEMANTIC_ADMISSION"),
    }
    bad = [f"{key}:{actual}" for key, (actual, wanted) in expected.items() if actual != wanted]
    if bad:
        raise ProjectionError("unit04_authority_not_pass:" + ",".join(bad))


def build_unit04_reference_projection(repo_root: Path | str | None = None) -> dict[str, Any]:
    root = _repo_root(repo_root)
    q02 = _load_json(root / Q02)
    q04 = _load_json(root / Q04)
    q05 = _load_json(root / Q05)
    q06 = _load_json(root / Q06)
    _validate_authorities(q02, q04, q05, q06)

    registry = _source_registry(root)
    unresolved = [row["source_id"] for row in registry if not row["integration_anchor_resolved"]]
    if unresolved:
        raise ProjectionError("unresolved_public_integration_anchor:" + ",".join(unresolved))

    chunk_counts = q04["dedup_result"]
    frame_counts = q05["frame_dedup_and_counts"]
    sentence_counts = q06["coverage"]
    baseline = q06["prior_cumulative_baseline"]
    place_counts = q04["delta_vs_unit03"]
    location_carriers = q04["carrier_authority"]

    target_relations = [row["relation_surface"] for row in q04["target_relation_chunk_groups"]]
    support_relations = [row["support_pattern"] for row in q04["yle_safe_support_chunk_groups"]]

    if sentence_counts["cumulative_sentence_assets_after_q06"] != baseline["cumulative_distinct"] + sentence_counts["unit04_new_admitted_sentence_assets"]:
        raise ProjectionError("sentence_cumulative_arithmetic_mismatch")
    if chunk_counts["cumulative_distinct_surfaces"] != chunk_counts["prior_distinct"] + chunk_counts["unit04_new_surface_total"]:
        raise ProjectionError("chunk_cumulative_arithmetic_mismatch")
    if frame_counts["cumulative_exact_frames"] != frame_counts["prior_exact_frames"] + frame_counts["new_exact_frames_total"]:
        raise ProjectionError("frame_cumulative_arithmetic_mismatch")

    vocabulary_reference = _vocabulary_reference(root)
    chunk_reference = _chunk_reference(root, [*target_relations, *support_relations])

    result = {
        "schema_version": "a1fs.v1.u04ms01.cross_source_reference_projection.v1",
        "task_id": TASK_ID,
        "status": STATUS,
        "unit_id": "GRAMMAR_BASIC_PREPOSITIONS_PLACE",
        "unit_number": 4,
        "scope": {
            "current_grammar_scope": ["UNIT01", "UNIT02", "UNIT03", "UNIT04"],
            "a2_unlocked": False,
            "unit05_plus_grammar_learner_facing_allowed": False,
            "canonical_authority_mutated": False,
            "learner_content_authored": False,
            "reference_counts_are_additive": False,
        },
        "source_registry": registry,
        "source_resolution": {
            "registered_source_count": len(registry),
            "unresolved_public_integration_anchor_count": len(unresolved),
            "unresolved_source_ids": unresolved,
        },
        "unit04_authoritative_asset_roles": {
            "vocabulary": {
                "direct_active_location_carriers": location_carriers["q02_selected_life_place_carrier_count"],
                "new_global_vocabulary_identities": location_carriers["new_global_vocabulary_identity_count"],
                "cumulative_learned_vocabulary_denominator": None,
                "denominator_status": "NOT_ENCODED_AS_ONE_CUMULATIVE_UNIT01_04_VOCABULARY_COUNT",
            },
            "chunk_surfaces": {
                "DIRECT_ACTIVE": chunk_counts["unit04_new_surface_total"],
                "REVIEW_REUSE": chunk_counts["prior_distinct"],
                "CUMULATIVE": chunk_counts["cumulative_distinct_surfaces"],
            },
            "place_phrases": {
                "TARGET_CURRENT_POOL": place_counts["unit04_target_place_chunk_pool_after_reuse"],
                "SUPPORT_CURRENT_POOL": place_counts["unit04_place_support_chunk_pool"],
                "CURRENT_TOTAL": place_counts["unit04_place_focused_chunk_pool_total"],
                "TARGET_RELATIONS": target_relations,
                "SUPPORT_RELATIONS": support_relations,
            },
            "exact_sentence_frames": {
                "DIRECT_ACTIVE": frame_counts["new_exact_frames_total"],
                "REVIEW_REUSE": frame_counts["prior_exact_frames"],
                "CUMULATIVE": frame_counts["cumulative_exact_frames"],
                "CANONICAL_PATTERN_FAMILIES": frame_counts["cumulative_pattern_families"],
            },
            "sentence_assets": {
                "DIRECT_ACTIVE": sentence_counts["unit04_new_admitted_sentence_assets"],
                "REVIEW_REUSE": baseline["cumulative_distinct"],
                "CUMULATIVE": sentence_counts["cumulative_sentence_assets_after_q06"],
                "TARGET_NEW": sentence_counts["target_relation_asset_count"],
                "SUPPORT_NEW": sentence_counts["support_relation_asset_count"],
            },
        },
        "reference_only_pools": {
            "vocabulary": vocabulary_reference,
            "chunks": chunk_reference,
            "usage_rule": (
                "REFERENCE_ONLY pools may supply candidate evidence for MS02+ only after current-unit grammar, "
                "canonical identity, scene semantics, and learner-facing admission gates pass."
            ),
        },
        "reference_authority_boundaries": {
            "egp_overrides_unit_unlock": False,
            "evp_row_implies_learned": False,
            "ngsl_can_promote_lexical_identity": False,
            "cambridge_can_create_second_lexical_authority": False,
            "ielts_language_import_allowed": False,
            "ket99_srt_canonical_promotion_allowed": False,
            "raz_aw_canonical_promotion_allowed": False,
            "unit05_plus_grammar_leak_count": 0,
            "a2_plus_unlock_count": 0,
        },
        "next_short_step": "A1FS-V1-U04MS02_MultiSentenceAssessmentTypeCapabilityProof",
    }
    result["projection_sha256"] = hashlib.sha256(
        json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return result


def compact_readback(projection: dict[str, Any]) -> dict[str, Any]:
    assets = projection["unit04_authoritative_asset_roles"]
    vocab_ref = projection["reference_only_pools"]["vocabulary"]
    chunk_ref = projection["reference_only_pools"]["chunks"]
    return {
        "status": projection["status"],
        "registered_sources": projection["source_resolution"]["registered_source_count"],
        "unresolved_sources": projection["source_resolution"]["unresolved_public_integration_anchor_count"],
        "unit04_location_carriers": assets["vocabulary"]["direct_active_location_carriers"],
        "cumulative_chunks": assets["chunk_surfaces"]["CUMULATIVE"],
        "place_phrases": assets["place_phrases"]["CURRENT_TOTAL"],
        "cumulative_exact_frames": assets["exact_sentence_frames"]["CUMULATIVE"],
        "cumulative_sentence_assets": assets["sentence_assets"]["CUMULATIVE"],
        "a1_reference_vocabulary_rows": vocab_ref["a1_reference_row_count"],
        "a1_reference_generator_safe_chunks": chunk_ref["a1_reference_row_count"],
        "a2_unlocked": projection["scope"]["a2_unlocked"],
        "unit05_plus_grammar_leak_count": projection["reference_authority_boundaries"]["unit05_plus_grammar_leak_count"],
        "projection_sha256": projection["projection_sha256"],
    }


if __name__ == "__main__":
    print(json.dumps(compact_readback(build_unit04_reference_projection()), ensure_ascii=False, sort_keys=True))
