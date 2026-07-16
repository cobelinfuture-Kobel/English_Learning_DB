from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ulga.builders import build_a1fs_v1_m5_four_skill_renderer_learner_ui as m5
from ulga.validators import validate_a1fs_v1_m5_four_skill_renderer_learner_ui as validator


def _fixture(tmp_path: Path) -> tuple[Path, dict[str, Path]]:
    specs = {
        "LISTENING": ("L-A1", "A1", [("AUD", {"learning_script": {"speaker_turns": [{"text": "secret transcript"}], "transcript": "secret", "question": "What time?", "answer": "eight"}}), ("CHK", {"question": "Listen again.", "answer_ref": "secret"})]),
        "SPEAKING": ("S-A1", "A1", [("CTX", {"launch_cue": "Tell me about school."}), ("MOD", {"model_text": "I like my school."}), ("PRD", {"prompt": "Now say your idea."})]),
        "READING": ("R-A1", "A1+", [("TXT", {"text": "Mia goes to school by bus."}), ("CHK", {"question": "How does Mia travel?", "answer": "bus"})]),
        "WRITING": ("W-A1", "A1", [("CTX", {"body_text": "Write to your friend."}), ("NTC", {"focus": "reader and purpose"}), ("PRD", {"prompt": "Write 25 words."}), ("EVD", {"expected_evidence": "private rubric"})]),
        "A2": ("R-A2", "A2", [("TXT", {"text": "locked"})]),
    }
    catalog = []; assets = []
    for skill_key, (lesson, level, rows) in specs.items():
        skill = "READING" if skill_key == "A2" else skill_key
        keys = []
        for role, payload in rows:
            key = f"{lesson}:{role}"; keys.append(key)
            assets.append({"asset_key": key, "asset_id": key, "lesson_id": lesson, "skill": skill, "level": level, "role": role,
                           "payload": payload, "content_digest": hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(), "release_scope": "PRIVATE_INTERNAL_D0"})
        catalog.append({"lesson_id": lesson, "lesson_node_id": f"LESSON:{skill}:{lesson}", "skill": skill, "level": level,
                        "asset_keys": keys, "roles": [role for role, _ in rows], "requirement_node_ids": [], "release_scope": "PRIVATE_INTERNAL_D0"})
    consumer = {"validation_status": m5.CONSUMER_STATUS, "lesson_catalog": catalog, "asset_records": assets,
                "counts": {"lesson_count": 5, "asset_record_count": len(assets), "learning_lesson_count": 4, "a2_handoff_lesson_count": 1}}
    consumer_path = tmp_path / "consumer.json"; consumer_path.write_text(json.dumps(consumer), encoding="utf-8")
    plans = {}
    for skill_key, (lesson, level, _) in specs.items():
        skill = "READING" if skill_key == "A2" else skill_key
        plan = {"validation_status": m5.PLANNER_STATUS, "plan_status": "PLAN_LEARNING_LESSON",
                "selected_lesson": {"lesson_id": lesson, "lesson_node_id": f"LESSON:{skill}:{lesson}", "skill": skill, "level": level, "roles": [], "requirement_node_ids": []}}
        path = tmp_path / f"plan-{skill_key}.json"; path.write_text(json.dumps(plan), encoding="utf-8"); plans[skill_key] = path
    return consumer_path, plans


def test_all_four_skill_renderers_build_and_validate(tmp_path: Path) -> None:
    consumer, plans = _fixture(tmp_path)
    expected = {"LISTENING": 2, "SPEAKING": 3, "READING": 2, "WRITING": 4}
    for skill, count in expected.items():
        output = tmp_path / skill
        manifest = m5.build_ui(consumer_path=consumer, plan_path=plans[skill], output_root=output)
        assert manifest["skill"] == skill and manifest["asset_count"] == count
        report = validator.validate(output, consumer, plans[skill])
        assert report["error_count"] == 0, report["errors"]


def test_listening_script_answer_and_transcript_are_not_disclosed(tmp_path: Path) -> None:
    consumer, plans = _fixture(tmp_path); output = tmp_path / "ui"
    m5.build_ui(consumer_path=consumer, plan_path=plans["LISTENING"], output_root=output)
    bundle = json.loads((output / "lesson.private.json").read_text())
    aud = next(row for row in bundle["assets"] if row["role"] == "AUD")
    text = json.dumps(aud["learner_payload"])
    assert "secret transcript" not in text and '"answer"' not in text and "answer_ref" not in text
    assert "What time?" in text
    assert aud["learner_payload"]["audio_state"] == "AUDIO_DEFERRED_TO_M10"


def test_educator_only_keys_are_removed_from_every_payload(tmp_path: Path) -> None:
    consumer, plans = _fixture(tmp_path); output = tmp_path / "ui"
    m5.build_ui(consumer_path=consumer, plan_path=plans["WRITING"], output_root=output)
    bundle = json.loads((output / "lesson.private.json").read_text())
    assert all(not validator._blocked_keys(row["learner_payload"]) for row in bundle["assets"])


def test_a2_render_is_fail_closed(tmp_path: Path) -> None:
    consumer, plans = _fixture(tmp_path)
    with pytest.raises(m5.RendererError, match="A2_RENDER_LOCKED"):
        m5.build_ui(consumer_path=consumer, plan_path=plans["A2"], output_root=tmp_path / "a2")


def test_non_learning_plan_is_not_renderable(tmp_path: Path) -> None:
    consumer, plans = _fixture(tmp_path); plan = json.loads(plans["READING"].read_text()); plan["plan_status"] = "A2_HANDOFF_READY"
    plans["READING"].write_text(json.dumps(plan), encoding="utf-8")
    with pytest.raises(m5.RendererError, match="plan_not_renderable_learning_lesson"):
        m5.build_ui(consumer_path=consumer, plan_path=plans["READING"], output_root=tmp_path / "bad")


def test_ui_uses_csp_textcontent_keyboard_and_no_inline_script(tmp_path: Path) -> None:
    consumer, plans = _fixture(tmp_path); output = tmp_path / "ui"
    m5.build_ui(consumer_path=consumer, plan_path=plans["SPEAKING"], output_root=output)
    html = (output / "index.html").read_text(); script = (output / "app.js").read_text()
    assert "Content-Security-Policy" in html and '<script src="app.js">' in html
    assert "textContent" in script and "innerHTML" not in script and "ArrowRight" in script


def test_validator_detects_file_tampering(tmp_path: Path) -> None:
    consumer, plans = _fixture(tmp_path); output = tmp_path / "ui"
    m5.build_ui(consumer_path=consumer, plan_path=plans["READING"], output_root=output)
    (output / "styles.css").write_text("tampered", encoding="utf-8")
    report = validator.validate(output, consumer, plans["READING"])
    assert "file_manifest_mismatch:styles.css" in report["errors"]


def test_private_server_rejects_non_loopback_binding(tmp_path: Path) -> None:
    with pytest.raises(m5.RendererError, match="private_server_must_bind_loopback"):
        m5.serve(tmp_path, "0.0.0.0", 8775)
