from __future__ import annotations

import json
import sqlite3
from copy import deepcopy
from pathlib import Path

from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.builders import (
    build_a1fs_v1_razq01b_unit01_content_contract as contract_builder,
)
from ulga.builders import (
    build_a1fs_v1_razq01d_unit01_micro_scene_passage_dialogue_admission_three_skill_projection_unit02_handoff
    as content_builder,
)
from ulga.builders import (
    build_a1fs_v1_razq01f_unit01_real_content_multi_session_diversity_learner_use_acceptance
    as builder,
)
from ulga.validators import (
    validate_a1fs_v1_razq01f_unit01_real_content_multi_session_diversity_learner_use_acceptance
    as validator,
)


def candidate(
    source: str,
    semantic: str,
    selection_class: str,
    text: str,
    nouns: list[str],
    adjectives: list[str] | None = None,
    *,
    flags: list[str] | None = None,
    frames: list[str] | None = None,
) -> dict:
    return {
        "source_record_id": source,
        "semantic_identity": semantic,
        "source_level": "B",
        "source_type": "page_unit",
        "text_excerpt": text,
        "selection_class": selection_class,
        "selection_reasons": ["RAZQ01F_CI_FIXTURE"],
        "structural_flags": list(flags or []),
        "matched_sentence_frame_ids": list(frames or []),
        "direct_task_candidate_roles": [
            "READING_TASK_CANDIDATE",
            "WRITING_TASK_CANDIDATE",
            "SPEAKING_TASK_CANDIDATE",
        ],
        "active_noun_hits": nouns,
        "active_adjective_hits": list(adjectives or []),
        "direct_noun_phrases": [],
        "adjective_noun_phrases": [],
        "very_adjective_noun_phrases": [],
        "canonical_admission": False,
        "human_review_required": selection_class != "REJECT",
    }


def gap_specs() -> list[dict]:
    rows: list[dict] = []
    noun_forms = {
        "apple": ["an apple", "the apple"],
        "bag": ["a bag", "the bag"],
        "bed": ["a bed", "the bed"],
        "book": ["a book", "the book"],
        "box": ["a box", "the box"],
        "cat": ["a cat", "the cat"],
        "classroom": ["a classroom", "the classroom"],
        "desk": ["a desk", "the desk"],
        "dog": ["a dog", "the dog"],
        "door": ["a door", "the door"],
        "egg": ["an egg", "the egg"],
        "park": ["a park", "the park"],
        "room": ["a room", "the room"],
        "shop": ["a shop", "the shop"],
        "tree": ["a tree", "the tree"],
        "window": ["a window", "the window"],
    }
    for noun, forms in noun_forms.items():
        rows.append(
            {
                "gap_spec_id": f"U01-GAP-NOUN-{noun.upper()}",
                "gap_dimension": "ACTIVE_NOUN",
                "target_lemmas": [noun],
                "required_memory_forms": forms,
                "candidate_only": True,
                "generated": True,
            }
        )
    adjective_forms = {
        "blue": "a blue bag",
        "new": "a new book",
        "old": "an old book",
        "red": "a red book",
        "small": "a small bag",
    }
    for adjective, phrase in adjective_forms.items():
        rows.append(
            {
                "gap_spec_id": f"U01-GAP-ADJECTIVE-{adjective.upper()}",
                "gap_dimension": "ACTIVE_ADJECTIVE",
                "target_lemmas": [adjective],
                "required_memory_forms": [phrase],
                "candidate_only": True,
                "generated": True,
            }
        )
    assert len(rows) == 21
    return rows


def approved_real44() -> dict:
    frame_ids = [
        "U01-AF01",
        "U01-AF02",
        "U01-AF03",
        "U01-F01",
        "U01-F02",
        "U01-F03",
        "U01-F04",
        "U01-F05",
        "U01-F06",
    ]
    selected: list[dict] = []
    for index in range(41):
        frame = frame_ids[index % len(frame_ids)]
        mode = index % 4
        if mode == 0:
            noun = "apple" if index == 0 else "book"
            article = "an" if noun == "apple" else "a"
            row = candidate(
                f"SRC-{index // 2:02d}",
                f"SEM-{index:02d}",
                "DIRECT_MODEL",
                f"This is {article} {noun}.",
                [noun],
                frames=[frame],
            )
        elif mode == 1:
            row = candidate(
                f"SRC-{index // 2:02d}",
                f"SEM-{index:02d}",
                "CONTROLLED_PRACTICE_SOURCE",
                "The big cat runs.",
                ["cat"],
                ["big"],
                frames=[frame],
            )
        elif mode == 2:
            row = candidate(
                f"SRC-{index // 2:02d}",
                f"SEM-{index:02d}",
                "CONTEXT_SOURCE",
                "Would you like to come to the park with us?",
                ["park"],
                frames=[frame],
            )
        else:
            row = candidate(
                f"SRC-{index // 2:02d}",
                f"SEM-{index:02d}",
                "REWRITE_REQUIRED",
                "They can be as big as a room.",
                ["room"],
                ["big"],
                flags=["COMPARATIVE_PRESENT", "UNAPPROVED_MODAL_SCAFFOLD"],
                frames=[frame],
            )
        selected.append(row)
    for index in range(3):
        selected.append(
            candidate(
                f"SRC-REJECT-{index}",
                f"SEM-REJECT-{index}",
                "REJECT",
                '"Do not eat the tree!',
                ["tree"],
                flags=["UNBALANCED_QUOTATION", "NEGATIVE_IMPERATIVE_PRESENT"],
            )
        )
    report = {
        "schema_version": content_builder.upstream.SCHEMA_VERSION,
        "task_id": content_builder.upstream.TASK_ID,
        "status": content_builder.upstream.PASS_STATUS,
        "scope": {
            "allowed_units": [content_builder.UNIT_ID],
            "canonical_promotion": False,
            "a2_status": "LOCKED",
        },
        "selection_summary": {"strict_candidate_count": 44},
        "selected_candidates": selected,
        "coverage": {"project_authored_gap_specs": gap_specs()},
    }
    _candidate, approved, _safe = content_builder.build_admission(
        report, contract=contract_builder.build_contract()
    )
    coverage = approved["payload"]["coverage_readback"]
    assert coverage["auto_transformed_source_count"] == 41
    assert coverage["auto_reject_count"] == 3
    assert coverage["project_authored_gap_spec_count"] == 21
    assert coverage["approved_content_asset_count"] == 62
    assert coverage["unit01_coverage"]["complete"] is True
    return approved


def setup_database(database: Path) -> None:
    with sqlite3.connect(database) as connection:
        connection.executescript(m3.SCHEMA_SQL)
        connection.executemany(
            "INSERT INTO metadata(key,value) VALUES(?,?)",
            {
                "task_id": m3.TASK_ID,
                "schema_version": m3.SCHEMA_VERSION,
                "validation_status": m3.STATUS,
                "consumer_sha256": "a" * 64,
                "mastery_write_enabled": "false",
                "a2_session_enabled": "false",
            }.items(),
        )
        for index, (skill, lesson_id) in enumerate(
            builder.extension_runtime.qb02.UNIT01_LESSONS.items(), 1
        ):
            connection.execute(
                "INSERT INTO lesson_catalog VALUES(?,?,?,?,?,?,?)",
                (
                    lesson_id,
                    f"LESSON:U01:{index}",
                    skill,
                    "A1",
                    json.dumps(["CHK" if skill == "READING" else "PRD"]),
                    "[]",
                    1,
                ),
            )
        connection.execute(
            "INSERT INTO learner_profiles VALUES(?,?,?,?,?,?,?,?)",
            (
                "learner-razq01f-ci",
                "Learner",
                "zh-TW",
                "Asia/Taipei",
                "ACTIVE",
                1,
                "2026-07-31T00:00:00Z",
                "2026-07-31T00:00:00Z",
            ),
        )


def test_razq01f_reconciles_both_consumers_across_real_multi_session_use(
    tmp_path: Path,
):
    database = tmp_path / "learner_progress.sqlite3"
    output_root = tmp_path / "razq01f"
    setup_database(database)
    approved = approved_real44()

    report = builder.run_acceptance(
        database=database,
        approved_content=approved,
        learner_id="learner-razq01f-ci",
        output_root=output_root,
        session_prefix="session-razq01f-ci",
    )
    result = validator.validate(
        database=database,
        approved_content=approved,
        output_root=output_root,
    )

    assert report["status"] == builder.PASS_STATUS
    assert report["combined_runtime_item_count"] == 474
    assert report["session_count"] == 3
    assert report["exposure_count"] == 30
    assert report["attempt_count"] == 3
    assert report["auto_pass_count"] == 3
    assert report["distinct_item_count_across_sessions"] >= 20
    assert report["distinct_content_asset_count_across_sessions"] >= 20
    assert all(
        row["authoritative_extension_content_count"] >= 2
        for row in report["sessions"]
    )
    assert all(row["attempt_outcome"] == "AUTO_PASS" for row in report["sessions"])
    assert result["validation_status"] == validator.PASS_STATUS
    assert result["error_count"] == 0, result["errors"]
    assert result["session_count"] == 3
    assert result["exposure_count"] == 30
    assert result["attempt_count"] == 3

    with sqlite3.connect(database) as connection:
        razq01f_tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'razq01f%'"
        ).fetchall()
    assert razq01f_tables == []

    tampered = deepcopy(report)
    tampered["sessions"][0]["content_asset_ids"][0] = "U01-TAMPERED-ASSET"
    (output_root / "razq01f_multisession_readback.json").write_text(
        json.dumps(tampered, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    failed = validator.validate(
        database=database,
        approved_content=approved,
        output_root=output_root,
    )
    assert failed["validation_status"] == validator.FAIL_STATUS
    assert failed["error_count"] == 1
    assert "readback_digest_invalid" in failed["errors"][0]
