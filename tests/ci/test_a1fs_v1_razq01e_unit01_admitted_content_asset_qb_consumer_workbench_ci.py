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
    build_a1fs_v1_razq01e_unit01_admitted_content_asset_qb_consumer_workbench
    as builder,
)
from ulga.builders import (
    build_a1fs_v1_u01qb02_unit01_approved_variant_session_runtime as qb02,
)
from ulga.validators import (
    validate_a1fs_v1_razq01e_unit01_admitted_content_asset_qb_consumer_workbench
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
        "selection_reasons": ["RAZQ01E_CI_FIXTURE"],
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
    """Mirror the production denominator: 16 noun gaps + 5 adjective gaps = 21."""
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
    # BIG is deliberately covered by source-derived assets; these five remain
    # project-authored completion rows, matching the formal 21-row denominator.
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
    accepted: list[dict] = []
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
        accepted.append(row)

    selected = list(accepted)
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
            qb02.UNIT01_LESSONS.items(), 1
        ):
            connection.execute(
                "INSERT INTO lesson_catalog VALUES(?,?,?,?,?,?,?)",
                (
                    lesson_id,
                    f"LESSON:U01:{index}",
                    skill,
                    "A1",
                    json.dumps(["CHK"]),
                    "[]",
                    1,
                ),
            )
        connection.execute(
            "INSERT INTO learner_profiles VALUES(?,?,?,?,?,?,?,?)",
            (
                "learner-razq01e-ci",
                "Learner",
                "zh-TW",
                "Asia/Taipei",
                "ACTIVE",
                1,
                "2026-07-31T00:00:00Z",
                "2026-07-31T00:00:00Z",
            ),
        )


def test_razq01e_binds_real62_assets_to_existing_u01qb_session_and_workbench(
    tmp_path: Path,
):
    database = tmp_path / "learner_progress.sqlite3"
    setup_database(database)
    runtime = qb02.Unit01ApprovedVariantSessionRuntime(database)
    initialized = runtime.initialize()
    m3.LearnerStateStore(database).start_session(
        learner_id="learner-razq01e-ci",
        lesson_id=qb02.UNIT01_LESSONS["READING"],
        session_id="session-razq01e-ci",
        at="2026-07-31T00:01:00Z",
    )
    approved = approved_real44()
    output = tmp_path / "workbench"
    manifest = builder.build_workbench(
        database=database,
        learner_id="learner-razq01e-ci",
        session_id="session-razq01e-ci",
        approved_content=approved,
        output_root=output,
    )
    report = validator.validate(
        database=database,
        approved_content=approved,
        output_root=output,
    )
    bundle = json.loads(
        (output / "session.private.json").read_text(encoding="utf-8")
    )

    assert initialized["registered_item_count"] == 288
    assert manifest["validation_status"] == builder.PASS_STATUS
    assert manifest["content_asset_available_count"] == 62
    assert manifest["content_asset_bound_count"] == 10
    assert manifest["distinct_bound_content_asset_count"] == 10
    assert bundle["content_consumer_bound"] is True
    assert len({row["content_binding"]["content_asset_id"] for row in bundle["items"]}) == 10
    assert all("學習素材：" in row["stimulus"] for row in bundle["items"])
    assert all(row["question_stimulus"] in row["stimulus"] for row in bundle["items"])
    assert report["status"] == builder.PASS_STATUS
    assert report["error_count"] == 0
    assert report["available_content_asset_count"] == 62
    assert report["bound_content_asset_count"] == 10
    assert report["distinct_bound_content_asset_count"] == 10
    assert report["u01qb02_session_plan_count"] == 1
    assert report["existing_u01qb03_workbench_reused"] is True
    assert report["raw_raz_identity_exposed"] is False
