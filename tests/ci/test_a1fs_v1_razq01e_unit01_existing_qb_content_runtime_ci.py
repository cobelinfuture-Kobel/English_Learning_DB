from __future__ import annotations

import json
import sqlite3
from copy import deepcopy
from pathlib import Path

import pytest

from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.builders import (
    build_a1fs_v1_razq01b_unit01_content_contract as contract_builder,
)
from ulga.builders import (
    build_a1fs_v1_razq01d_unit01_micro_scene_passage_dialogue_admission_three_skill_projection_unit02_handoff
    as content_builder,
)
from ulga.builders import (
    build_a1fs_v1_razq01e_unit01_approved_content_existing_qb_learner_stimulus_runtime
    as builder,
)
from ulga.validators import (
    validate_a1fs_v1_razq01e_unit01_approved_content_existing_qb_learner_stimulus_runtime
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
        "matched_sentence_frame_ids": [],
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
        "big": "a big box",
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
    rows.append(
        {
            "gap_spec_id": "U01-GAP-ARTICLE-AN",
            "gap_dimension": "ARTICLE_FORM",
            "target_articles": ["an"],
            "candidate_only": True,
            "generated": True,
        }
    )
    for frame_id in (
        "U01-AF01",
        "U01-AF02",
        "U01-AF03",
        "U01-F01",
        "U01-F02",
        "U01-F03",
        "U01-F04",
        "U01-F05",
        "U01-F06",
    ):
        rows.append(
            {
                "gap_spec_id": f"U01-GAP-FRAME-{frame_id}",
                "gap_dimension": "SENTENCE_FRAME",
                "target_sentence_frame_ids": [frame_id],
                "candidate_only": True,
                "generated": True,
            }
        )
    return rows


def selection_report() -> dict:
    selected = [
        candidate(
            "SRC-SHARED",
            "SEM-DIRECT",
            "DIRECT_MODEL",
            "This is a tree.",
            ["tree"],
        ),
        candidate(
            "SRC-SHARED",
            "SEM-ACTION",
            "CONTROLLED_PRACTICE_SOURCE",
            "The big cat runs.",
            ["cat"],
            ["big"],
        ),
        candidate(
            "SRC-REWRITE",
            "SEM-IMITATE",
            "REWRITE_REQUIRED",
            "They can be as big as a room.",
            ["room"],
            ["big"],
            flags=["COMPARATIVE_PRESENT", "UNAPPROVED_MODAL_SCAFFOLD"],
        ),
        candidate(
            "SRC-CONTEXT",
            "SEM-DIALOGUE",
            "CONTEXT_SOURCE",
            "Would you like to come to the park with us?",
            ["park"],
        ),
        candidate(
            "SRC-REJECT",
            "SEM-REJECT",
            "REJECT",
            '"Do not eat the tree!',
            ["tree"],
            flags=["UNBALANCED_QUOTATION", "NEGATIVE_IMPERATIVE_PRESENT"],
        ),
    ]
    return {
        "schema_version": content_builder.upstream.SCHEMA_VERSION,
        "task_id": content_builder.upstream.TASK_ID,
        "status": content_builder.upstream.PASS_STATUS,
        "scope": {
            "allowed_units": [content_builder.UNIT_ID],
            "canonical_promotion": False,
            "a2_status": "LOCKED",
        },
        "selection_summary": {"strict_candidate_count": len(selected)},
        "selected_candidates": selected,
        "coverage": {"project_authored_gap_specs": gap_specs()},
    }


def approved_content() -> dict:
    _candidate, approved, _safe = content_builder.build_admission(
        selection_report(), contract=contract_builder.build_contract()
    )
    return approved


def fixture_database(tmp_path: Path) -> Path:
    database = tmp_path / "learner_progress.sqlite3"
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
            builder.qb02.UNIT01_LESSONS.items(), 1
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
                "learner-ci",
                "Learner",
                "zh-TW",
                "Asia/Taipei",
                "ACTIVE",
                1,
                "2026-07-31T00:00:00Z",
                "2026-07-31T00:00:00Z",
            ),
        )
    return database


def test_razq01e_existing_qb_runtime_and_learner_stimulus_ci(tmp_path: Path):
    content = approved_content()
    candidate_artifact, approved, safe = builder.build_extension_package(content)
    package = validator.validate_package(approved, safe)
    asset_count = len(content["payload"]["content_assets"])
    extension_count = asset_count * len(content_builder.SKILLS)

    assert candidate_artifact["artifact_role"] == builder.policy_artifact.CANDIDATE_ROLE
    assert approved["artifact_role"] == builder.policy_artifact.APPROVED_ROLE
    assert package["validation_status"] == "PASS_A1FS_V1_RAZQ01E_PACKAGE_VALIDATION"
    assert package["extension_item_count"] == extension_count
    assert (
        package["combined_runtime_item_count"]
        == builder.bank.EXPECTED_APPROVED_COUNT + extension_count
    )

    database = fixture_database(tmp_path)
    first_runtime = builder.materialize_runtime(database, approved)
    second_runtime = builder.materialize_runtime(database, approved)
    assert first_runtime["extension_item_count"] == extension_count
    assert second_runtime["base_runtime_readback"]["existing_materialization_reused"] is True

    session = m3.LearnerStateStore(database).start_session(
        learner_id="learner-ci",
        lesson_id=builder.qb02.UNIT01_LESSONS["READING"],
        session_id="session-ci",
        at="2026-07-31T00:01:00Z",
    )
    plan = builder.assemble_session_with_content(
        database,
        learner_id="learner-ci",
        session_id="session-ci",
    )
    assert plan["item_count"] == builder.qb02.SESSION_SIZE
    assert plan["content_extension_item_count"] >= builder.MIN_CONTENT_ITEMS_PER_SESSION
    assert plan["answer_keys_exposed"] is False

    output_root = tmp_path / "workbench"
    manifest = builder.build_workbench_with_content(
        database=database,
        learner_id="learner-ci",
        session_id="session-ci",
        output_root=output_root,
    )
    assert manifest["content_extension_item_count"] >= builder.MIN_CONTENT_ITEMS_PER_SESSION
    bundle = json.loads(
        (output_root / "session.private.json").read_text(encoding="utf-8")
    )
    content_items = [
        row
        for row in bundle["items"]
        if row.get("content_extension_task_id") == builder.TASK_ID
    ]
    assert len(content_items) >= builder.MIN_CONTENT_ITEMS_PER_SESSION
    assert all(row.get("content_asset_id") for row in content_items)

    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """SELECT c.private_item_json
            FROM u01qb02_session_items s
            JOIN razq01e_extension_items e USING(item_id)
            JOIN u01qb02_item_catalog c USING(item_id)
            WHERE s.session_id=? AND e.skill='READING'
            ORDER BY s.item_position LIMIT 1""",
            ("session-ci",),
        ).fetchone()
    assert row is not None
    private_item = json.loads(row["private_item_json"])
    runtime = builder.qb02.Unit01ApprovedVariantSessionRuntime(database)
    exposure = runtime.record_item_exposure(
        session_id="session-ci",
        item_id=private_item["item_id"],
        expected_session_version=session["session_version"],
        exposure_id="exposure-ci",
        at="2026-07-31T00:02:00Z",
    )
    attempt = runtime.capture_response(
        learner_id="learner-ci",
        session_id="session-ci",
        item_id=private_item["item_id"],
        response=private_item["correct_answer"],
        expected_session_version=exposure["session_version"],
        attempt_id="attempt-ci",
        submitted_at="2026-07-31T00:03:00Z",
    )
    assert attempt["outcome"] == "AUTO_PASS"

    runtime_report = validator.validate_runtime(database, approved)
    workbench_report = validator.validate_workbench(output_root, database, approved)
    assert runtime_report["error_count"] == 0, runtime_report["errors"]
    assert (
        workbench_report["validation_status"]
        == "PASS_A1FS_V1_RAZQ01E_WORKBENCH_VALIDATION"
    )
    assert (
        runtime_report["combined_runtime_item_count"]
        == builder.bank.EXPECTED_APPROVED_COUNT + extension_count
    )


def test_razq01e_safe_readback_tampering_fails_closed():
    content = approved_content()
    _candidate, approved, safe = builder.build_extension_package(content)
    tampered = deepcopy(safe)
    tampered["extension_item_hashes"][0]["item_sha256"] = "f" * 64
    with pytest.raises(
        validator.ContentRuntimeValidationError,
        match="safe_hash_invalid|safe_item_hash_binding_invalid",
    ):
        validator.validate_package(approved, tampered)
