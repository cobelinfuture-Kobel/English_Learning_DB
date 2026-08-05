from __future__ import annotations

from pathlib import Path

import pytest

from ulga.builders import build_a1fs_online_v1_s14_learner_facing_curriculum_progress_semantics as s14


UNIT01_TARGET_COUNTS = {"READING": 10, "WRITING": 8, "SPEAKING": 6}
LEGACY_OTHER_UNIT_COUNTS = {"READING": 4, "WRITING": 4, "SPEAKING": 3}


def _bootstrap() -> dict:
    units = []
    for grammar_id, label in sorted(s14.UNIT_LABELS.items(), key=lambda row: row[1]["sequence_index"]):
        counts = (
            UNIT01_TARGET_COUNTS
            if int(label["sequence_index"]) == 1
            else LEGACY_OTHER_UNIT_COUNTS
        )
        units.append(
            {
                "grammar_unit_id": grammar_id,
                "sequence_index": label["sequence_index"],
                "lanes": [
                    {"skill": "READING", "lesson_id": f"A1FS_ONLINE_V1:{grammar_id}:READING", "asset_count": counts["READING"], "assets": []},
                    {"skill": "WRITING", "lesson_id": f"A1FS_ONLINE_V1:{grammar_id}:WRITING", "asset_count": counts["WRITING"], "assets": []},
                    {"skill": "SPEAKING", "lesson_id": f"A1FS_ONLINE_V1:{grammar_id}:SPEAKING", "asset_count": counts["SPEAKING"], "assets": []},
                ],
            }
        )
    return {"task_id": "S09", "product_status": "S09", "unit_count": 24, "units": units}


def _progress() -> dict:
    return {
        "summary": {
            "profile_active": True,
            "session_count": 3,
            "completed_session_count": 3,
            "active_session_count": 0,
            "exposure_count": 12,
            "attempt_count": 0,
            "auto_pass_count": 0,
            "auto_fail_count": 0,
            "pending_human_review_count": 0,
            "abandoned_session_count": 0,
            "unit_count_with_sessions": 2,
            "skill_count_with_sessions": 1,
        },
        "skills": {
            "READING": {
                "session_count": 3,
                "completed_session_count": 3,
                "attempt_count": 0,
                "auto_pass_count": 0,
                "auto_fail_count": 0,
            }
        },
        "units": {
            "GRAMMAR_ARTICLES_BASIC": {
                "session_count": 2,
                "completed_session_count": 2,
                "abandoned_session_count": 0,
            },
            "GRAMMAR_REGULAR_PLURAL_NOUNS": {
                "session_count": 1,
                "completed_session_count": 1,
                "abandoned_session_count": 0,
            },
        },
        "last_event_hash_present": True,
        "readback_sha256": "0" * 64,
    }


def test_s14_has_exact_twentyfour_bilingual_canonical_unit_labels() -> None:
    assert len(s14.UNIT_LABELS) == 24
    assert [row["sequence_index"] for row in s14.UNIT_LABELS.values()] == list(range(1, 25))
    assert set(s14.UNIT_LABELS) == {
        "GRAMMAR_ARTICLES_BASIC",
        "GRAMMAR_REGULAR_PLURAL_NOUNS",
        "GRAMMAR_SUBJECT_PRONOUNS",
        "GRAMMAR_BASIC_PREPOSITIONS_PLACE",
        "GRAMMAR_BE_VERB_BASIC",
        "GRAMMAR_CAN_STATEMENT",
        "GRAMMAR_DEMONSTRATIVES_CONTRAST",
        "GRAMMAR_OBJECT_PRONOUNS_BASIC",
        "GRAMMAR_POSSESSIVE_ADJECTIVES_BASIC",
        "GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS",
        "GRAMMAR_ADJECTIVE_PHRASES_A1",
        "GRAMMAR_ADVERB_PHRASES_A1",
        "GRAMMAR_BE_INTERROGATIVES_A1",
        "GRAMMAR_CAN_NEGATIVE_A1",
        "GRAMMAR_COORDINATION_A1",
        "GRAMMAR_DECLARATIVE_CLAUSE_FORMS_A1",
        "GRAMMAR_PAST_SIMPLE_A1",
        "GRAMMAR_PRESENT_SIMPLE_NEGATIVES",
        "GRAMMAR_THERE_IS",
        "GRAMMAR_VERB_COMPLEMENT_PATTERNS_A1",
        "GRAMMAR_WILL_FUTURE_A1",
        "GRAMMAR_BECAUSE_REASON_CLAUSES_A1",
        "GRAMMAR_NOUN_PHRASES_A1",
        "GRAMMAR_PRESENT_SIMPLE_YES_NO_QUESTIONS",
    }
    for grammar_id, row in s14.UNIT_LABELS.items():
        assert row["title_zh"]
        assert row["title_en"]
        assert grammar_id not in row["learner_label"]


def test_s14_bootstrap_replaces_internal_ids_with_learner_labels_and_preserves_denominators() -> None:
    value = s14._decorate_bootstrap(_bootstrap())
    assert value["task_id"] == s14.TASK_ID
    assert len(value["units"]) == 24
    assert sum(len(unit["lanes"]) for unit in value["units"]) == 72
    assert sum(lane["asset_count"] for unit in value["units"] for lane in unit["lanes"]) == 277
    first = value["units"][0]
    assert first["internal_grammar_unit_id"] == "GRAMMAR_ARTICLES_BASIC"
    assert first["learner_label"] == "01. 冠詞：a、an、the"
    assert first["primary_label_uses_internal_id"] is False
    assert {lane["learner_label"] for lane in first["lanes"]} == {"閱讀", "寫作", "口說練習"}
    assert {lane["skill"]: lane["asset_count"] for lane in first["lanes"]} == UNIT01_TARGET_COUNTS
    speaking = next(lane for lane in first["lanes"] if lane["skill"] == "SPEAKING")
    assert speaking["response_capture_expected"] is False
    assert speaking["recording_enabled"] is False
    assert value["deferred_skills"] == [
        {
            "skill": "LISTENING",
            "learner_label": "聽力（音訊暫緩）",
            "status": "DEFERRED_POST_NOAUDIO_PRODUCT_LAUNCH",
            "audio_enabled": False,
            "lesson_count": 0,
        }
    ]


def test_s14_bootstrap_fails_closed_on_unknown_or_reordered_unit() -> None:
    unknown = _bootstrap()
    unknown["units"][0]["grammar_unit_id"] = "GRAMMAR_UNKNOWN"
    with pytest.raises(s14.LearnerFacingSemanticsError, match="bootstrap_unit_label_missing"):
        s14._decorate_bootstrap(unknown)
    reordered = _bootstrap()
    reordered["units"][0]["sequence_index"] = 24
    with pytest.raises(s14.LearnerFacingSemanticsError, match="bootstrap_sequence_drift"):
        s14._decorate_bootstrap(reordered)


def test_s14_progress_never_promotes_session_completion_to_unit_or_mastery() -> None:
    value = s14._decorate_progress(_progress())
    assert value["summary"]["session_count"] == 3
    assert value["summary"]["session_completed_count"] == 3
    assert value["summary"]["unit_completed_count"] == 0
    assert value["summary"]["mastered_unit_count"] == 0
    assert value["semantic_boundaries"] == {
        "session_completed_means": "ONE_SESSION_ENDED_SUCCESSFULLY",
        "session_completed_implies_lesson_completed": False,
        "session_completed_implies_unit_completed": False,
        "session_completed_implies_mastery": False,
        "exposure_implies_attempt": False,
        "exposure_implies_mastery": False,
        "speaking_is_practice_only": True,
        "listening_is_audio_deferred": True,
    }
    article = value["units"][0]
    assert article["activity_status"] == "SESSION_ACTIVITY_RECORDED"
    assert article["session_completed_count"] == 2
    assert article["unit_completed"] is False
    assert article["mastery_claimed"] is False
    listening = next(row for row in value["skills"] if row["skill"] == "LISTENING")
    assert listening["activity_status"] == "DEFERRED"
    assert listening["session_count"] == 0
    assert value["operator_debug"] == _progress()


def test_s14_secure_static_is_structured_and_raw_debug_is_collapsed(tmp_path: Path) -> None:
    learner = tmp_path / "learner"
    secure = tmp_path / "secure"
    s14._write_learner_static(learner)
    s14.s11._write_secure_static(learner, secure)
    index = (secure / "index.html").read_text(encoding="utf-8")
    app = (secure / "app.js").read_text(encoding="utf-8")
    assert "完成本次學習" in index
    assert "Operator debug readback" in index
    assert "<details>" in index
    assert "/auth.js" in index
    assert "unit.learner_label" in app
    assert "本次學習已完成（SESSION_COMPLETED）" in app
    assert "text(button, unit.grammar_unit_id)" not in app
    assert "text(progress, JSON.stringify" not in app
    assert "innerHTML" not in app


def test_s14_launch_bundle_is_secret_free_and_bound_to_s14(tmp_path: Path) -> None:
    outputs = s14._write_launch_bundle(
        target_root=tmp_path / "launch",
        receipt_path=tmp_path / "receipt.private.json",
        auth_state_db=tmp_path / "s13_auth.sqlite3",
    )
    start = Path(outputs["start_script_path"]).read_text(encoding="utf-8")
    stop = Path(outputs["stop_script_path"]).read_text(encoding="utf-8")
    contract = s14.read_json(Path(outputs["launch_contract_path"]), "contract")
    assert "build_a1fs_online_v1_s14_learner_facing_curriculum_progress_semantics" in start
    assert s14.CANARY_PASSWORD not in start
    assert s14.CANARY_SESSION_SECRET not in start
    assert "PID_OWNERSHIP_MISMATCH" in stop
    assert contract["host"] == "127.0.0.1"
    assert contract["auth_state_database_reused_from_s13"].endswith("s13_auth.sqlite3")
    assert contract["external_network_binding_allowed"] is False
    assert contract["cloudflare_enabled"] is False
    assert contract["audio_enabled"] is False
