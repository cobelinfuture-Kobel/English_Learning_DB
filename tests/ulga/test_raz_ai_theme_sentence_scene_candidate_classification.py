from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_ai_theme_sentence_scene_candidate_classification as builder
from ulga.validators import validate_raz_ai_theme_sentence_scene_candidate_classification as validator


def _authority(name: str, forms: list[str]) -> dict:
    rows = [{
        "id": f"{name}:{index:02d}",
        "form": form,
        "normalized": deep.normalize(form),
        "regex": deep._literal_template(form) if name in {"chunks", "patterns"} else None,
        "metadata": {},
    } for index, form in enumerate(forms, 1)]
    return {
        "rows": rows,
        "count": len(rows),
        "ids": {row["id"] for row in rows},
        "source_path": f"fixture/{name}.json",
        "source_sha256": "a" * 64,
    }


def _authorities() -> dict:
    return {
        "vocabulary": _authority(
            "vocabulary",
            ["child", "book", "school", "read", "happy", "because", "bus", "map"],
        ),
        "chunks": _authority("chunks", ["at school", "read sth", "because of sth"]),
        "patterns": _authority(
            "patterns", ["I can {verb_stem}.", "because {clause}", "Where is {noun_phrase}?"]
        ),
        "themes": _authority("themes", ["School", "Travel"]),
    }


def _record(index: int, level: str) -> dict:
    text = (
        "The child looks at a map near the bus."
        if level in {"G", "J", "W"}
        else "The child can read a book at school."
    )
    theme = "Travel" if level in {"G", "J", "W"} else "School"
    ref = f"RAZ_{level}_{index}_P001"
    review_uid = f"{ref}::page_passage_review_v1"
    bridge_uid = f"{ref}::reading_authority_bridge_v1"
    return {
        "page_unit_id": ref,
        "book_id": str(index),
        "level": level,
        "title": "Fixture",
        "page_number": 1,
        "sentence_count": 1,
        "text": text,
        "content_unit_tags": {"has_direct_speech": False, "has_sequence": False},
        "theme_tags": {"primary_theme": theme, "mapped_theme": theme},
        "reuse_tags": {"reusability_tags": ["picture_prompt_seed"]},
        "_review": {
            "review_candidate_uid": review_uid,
            "review_state": "ready_for_review",
            "review_status": "pending",
            "review_decision": None,
        },
        "_bridge": {
            "bridge_candidate_uid": bridge_uid,
            "source_review_candidate_uid": review_uid,
            "bridge_status": "bridge_candidate",
            "allowed_authority_targets": ["ReadingAuthority", "ContentQueryLayer"],
            "authority_status": "candidate_only",
            "promotion_status": "promotion_blocked",
        },
    }


def _records() -> list[dict]:
    return [_record(index, level) for index, level in enumerate(builder.LEVELS, 1)]


def _file_index(records: list[dict]) -> list[dict]:
    return [{
        "level": level,
        "derived_path": f"derived/Level_{level}/enriched/raz_{level}_page_unit_enriched.json",
        "review_path": f"review/Level_{level}/raz_{level}_page_passage_review_candidates.json",
        "bridge_path": f"bridge/reading_authority/Level_{level}/raz_{level}_reading_authority_bridge_candidates.json",
        "derived_sha256": "b" * 64,
        "review_sha256": "c" * 64,
        "bridge_sha256": "d" * 64,
        "record_count": 1,
        "book_count": 1,
    } for level in builder.LEVELS]


def _package():
    records = _records()
    return builder.build_package(
        records,
        _file_index(records),
        _authorities(),
        {},
        expected_record_count=len(records),
        expected_book_count=len(records),
    )


def test_processes_derived_review_bridge_for_every_a_w_record():
    package = _package()
    scope = package["source_scope"]
    summary = package["classification_summary"]

    assert scope["levels"] == list(builder.LEVELS)
    assert scope["derived_record_count"] == 23
    assert scope["review_candidate_count"] == 23
    assert scope["bridge_candidate_count"] == 23
    assert summary["sentence_seed_candidate_count"] == 23
    assert summary["scene_seed_candidate_count"] == 23
    assert summary["cross_link_count"] == 23
    assert package["classification_gate"]["decision"] == "THREE_LAYER_CLASSIFICATION_READY_FOR_REVIEW"


def test_review_bridge_states_remain_pending_candidate_and_blocked():
    package = _package()
    summary = package["classification_summary"]

    assert summary["review_status_counts"] == {"pending": 23}
    assert summary["bridge_status_counts"] == {"bridge_candidate": 23}
    assert summary["promotion_status_counts"] == {"promotion_blocked": 23}
    assert all(
        row["review_bridge_state"]["reading_authority_allowed"]
        for row in package["sentence_seed_candidates"]
    )
    assert package["classification_gate"]["ready_for_canonical_promotion"] is False
    assert package["classification_gate"]["ready_for_learning_unit_population"] is False


def test_source_bands_and_a1_suitability_keep_high_levels_evidence_only():
    package = _package()
    rows = {row["source_level"]: row for row in package["sentence_seed_candidates"]}

    assert rows["A"]["source_band"] == "AF"
    assert rows["I"]["source_band"] == "GI"
    assert rows["J"]["source_band"] == "JM"
    assert rows["N"]["source_band"] == "NQ"
    assert rows["W"]["source_band"] == "RW"
    assert rows["I"]["level_suitability_status"] == "A1_A1PLUS_REVIEW_REQUIRED"
    assert rows["J"]["level_suitability_status"] == "SOURCE_EVIDENCE_ONLY_A1_A1PLUS_REWRITE_REQUIRED"
    assert rows["W"]["level_suitability_status"] == "SOURCE_EVIDENCE_ONLY_A1_A1PLUS_REWRITE_REQUIRED"


def test_theme_sentence_scene_cross_links_include_review_and_bridge_lineage():
    package = _package()
    assert package["theme_situation_candidates"]
    for row in package["cross_links"]:
        assert row["theme_situation_candidate_ids"]
        assert row["review_candidate_uid"].endswith("page_passage_review_v1")
        assert row["bridge_candidate_uid"].endswith("reading_authority_bridge_v1")


def test_validator_accepts_package_and_rejects_tampering():
    package = _package()
    valid = validator.validate_package(
        package,
        rebuilt=package,
        schema_path=Path(__file__).resolve().parents[2]
        / "ulga/schemas/raz_ai_theme_sentence_scene_candidate_classification.schema.json",
    )
    assert valid["error_count"] == 0, valid

    tampered = deepcopy(package)
    tampered["classification_summary"]["bridge_status_counts"] = {}
    failed = validator.validate_package(tampered)
    assert "package_sha256_mismatch" in failed["errors"]
    assert "bridge_status_counts_mismatch" in failed["errors"]


def test_safe_package_rejects_source_text_and_linkage_stays_unread():
    package = _package()
    assert package["source_scope"]["linkage_read_performed"] is False
    package["source_text"] = "forbidden"
    assert builder.scan_forbidden_safe_keys(package)
