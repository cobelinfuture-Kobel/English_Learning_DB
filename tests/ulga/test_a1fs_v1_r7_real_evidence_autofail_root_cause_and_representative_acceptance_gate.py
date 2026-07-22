import json
import sqlite3

from ulga.builders import (
    build_a1fs_v1_r7_real_evidence_autofail_root_cause_and_representative_acceptance_gate as gate,
)
from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6
from ulga.validators import (
    validate_a1fs_v1_r7_real_evidence_autofail_root_cause_and_representative_acceptance_gate as validator,
)


def _item(item_id, *, skill, prompt, response_mode, scoring_mode, accepted, source_kind="TEXT"):
    scoring = {
        "response_type": "string", "scoring_mode": scoring_mode,
        "accepted_texts": accepted, "accepted_sequence": None,
        "case_insensitive": True, "punctuation_tolerance": True,
    }
    if scoring_mode == "FEATURE_RUBRIC":
        scoring["rubric"] = {"meaning": "required"}
    manifest = [] if source_kind == "OPTIONS" else [{
        "kind": source_kind,
        "payload": "Sara is asking Mia to meet at the community cafe and bring the lunch box. Basketball is the activity.",
    }]
    return {
        "item_id": item_id, "skill": skill,
        "learner_contract": {
            "prompt": prompt, "response_mode": response_mode,
            "stimulus_render_manifest": manifest,
        },
        "private_scoring_contract": scoring,
    }


def _fixture(tmp_path):
    database = tmp_path / "runtime.sqlite3"
    connection = sqlite3.connect(database)
    connection.executescript(
        """
        CREATE TABLE edge_runtime_items(item_id TEXT PRIMARY KEY,item_json TEXT NOT NULL);
        CREATE TABLE edge_sessions(session_id TEXT PRIMARY KEY,learner_id TEXT,session_state TEXT,started_at TEXT);
        CREATE TABLE edge_assignments(session_id TEXT,item_id TEXT,assignment_state TEXT);
        CREATE TABLE edge_attempts(
          attempt_id TEXT PRIMARY KEY,session_id TEXT,learner_id TEXT,item_id TEXT,response_json TEXT,
          response_time_ms INTEGER,hint_count INTEGER,revision_count INTEGER,submitted_at TEXT,
          validity_status TEXT,previous_hash TEXT,attempt_hash TEXT);
        CREATE TABLE edge_scoring_results(
          attempt_id TEXT PRIMARY KEY,scoring_mode TEXT,outcome TEXT,score REAL,
          human_review_required INTEGER,scored_at TEXT,scoring_contract_digest TEXT);
        CREATE TABLE edge_runtime_events(event_seq INTEGER PRIMARY KEY,event_type TEXT,payload_json TEXT);
        """
    )
    items = {
        "FAIL_SEM": _item(
            "FAIL_SEM", skill="READING",
            prompt="State the main message and cite the words that decide your answer.",
            response_mode="short_text", scoring_mode="NORMALIZED_TEXT",
            accepted=["Sara asks Mia to meet at the cafe and bring the lunch box."],
        ),
        "FAIL_FORMAT": _item(
            "FAIL_FORMAT", skill="READING", prompt="Where will the reader meet?",
            response_mode="short_text", scoring_mode="NORMALIZED_TEXT", accepted=["pool"],
        ),
        "FAIL_COMPLEX": _item(
            "FAIL_COMPLEX", skill="READING",
            prompt="State the main message and cite the words that decide your answer.",
            response_mode="short_text", scoring_mode="NORMALIZED_TEXT",
            accepted=["The notice invites readers and gives arrangements."],
        ),
        "PASS": _item(
            "PASS", skill="READING", prompt="Choose the correct question.",
            response_mode="select_one", scoring_mode="EXACT_OPTION",
            accepted=["Are you happy?"], source_kind="OPTIONS",
        ),
        "TARGET": _item(
            "TARGET", skill="WRITING", prompt="Write a short message.",
            response_mode="short_text", scoring_mode="FEATURE_RUBRIC", accepted=[],
        ),
    }
    for item_id, item in items.items():
        connection.execute("INSERT INTO edge_runtime_items VALUES(?,?)", (item_id, gate.canonical(item)))
    entries = []
    for index in range(1, 11):
        session_id = f"S{index:03d}"
        item_id = (
            "FAIL_SEM" if index <= 3 else
            "FAIL_FORMAT" if index <= 6 else
            "FAIL_COMPLEX" if index < 10 else "PASS"
        )
        if index <= 3:
            response = "Sara is asking Mia to meet her at the community cafe on Monday and bring the green lunch box."
        elif index <= 6:
            response = "(at) the pool"
        else:
            response = "basketball" if index < 10 else "Are you happy?"
        scoring = items[item_id]["private_scoring_contract"]
        outcome, score = m6.ResponseEvidenceStore.score(scoring, response)
        attempt_id = f"A{index:03d}"
        reference = {"reference_sha256": gate.digest({"session": session_id})}
        connection.execute("INSERT INTO edge_sessions VALUES(?,?,?,?)", (session_id, "L", "COMPLETED", f"2026-01-{index:02d}T00:00:00Z"))
        connection.execute("INSERT INTO edge_assignments VALUES(?,?,?)", (session_id, item_id, "SUBMITTED"))
        connection.execute(
            "INSERT INTO edge_attempts VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (attempt_id, session_id, "L", item_id, gate.canonical(response), 1000, 0, 0,
             f"2026-01-{index:02d}T00:01:00Z", "VALID", "0" * 64, f"{index:064x}"),
        )
        connection.execute(
            "INSERT INTO edge_scoring_results VALUES(?,?,?,?,?,?,?)",
            (attempt_id, scoring["scoring_mode"], outcome, score, 0,
             f"2026-01-{index:02d}T00:01:00Z", gate.digest(scoring)),
        )
        event = {
            "attempt_id": attempt_id, "telemetry_status": "CAPTURED_RUNTIME",
            "learner_rendered_stimulus_reference": reference,
        }
        connection.execute("INSERT INTO edge_runtime_events VALUES(?,?,?)", (index, "EDGE_RESPONSE_CAPTURED", gate.canonical(event)))
        entries.append({
            "attempt_id": attempt_id, "session_id": session_id, "item_id": item_id,
            "validity_status": "VALID", "outcome": outcome, "score": score,
            "telemetry_status": "CAPTURED_RUNTIME", "learner_rendered_stimulus_reference": reference,
        })
    connection.execute("INSERT INTO edge_sessions VALUES(?,?,?,?)", ("R7_REAL_PROJECTED_SESSION_011", "L", "ACTIVE", "2026-02-01T00:00:00Z"))
    connection.execute("INSERT INTO edge_assignments VALUES(?,?,?)", ("R7_REAL_PROJECTED_SESSION_011", "PASS", "ASSIGNED"))
    connection.commit()
    connection.close()

    evidence = {
        "learner_id": "L", "entries": entries,
        "objective_summary": {"synthetic_evidence_count": 0},
        "claim_boundaries": {"a2_unlocked": False},
    }
    evidence["package_sha256"] = gate.digest(evidence)
    deliveries = [
        *[
            {
                "work_item_id": f"W_{item_id}", "item_id": item_id, "projection_applied": True,
                "projected_learner_contract": items[item_id]["learner_contract"],
            }
            for item_id in ("FAIL_SEM", "FAIL_FORMAT", "FAIL_COMPLEX")
        ],
        {
            "work_item_id": "W_PASS", "item_id": "PASS", "projection_applied": False,
            "projected_learner_contract": items["PASS"]["learner_contract"],
        },
        {
            "work_item_id": "W_TARGET", "item_id": "TARGET", "projection_applied": False,
            "projected_learner_contract": items["TARGET"]["learner_contract"],
        },
    ]
    projection = {"deliveries": deliveries}
    projection["projection_sha256"] = gate.digest(projection)
    return database, evidence, projection


def test_replays_stored_scores_and_selects_one_minimal_writing_feature_rubric_session(tmp_path):
    database, evidence, projection = _fixture(tmp_path)
    first = gate.build(database_path=database, evidence_package=evidence, projection=projection)
    second = gate.build(database_path=database, evidence_package=evidence, projection=projection)
    assert first == second
    assert first["counts"]["real_valid_attempt_count"] == 10
    assert first["counts"]["auto_pass_valid_count"] == 1
    assert first["counts"]["auto_fail_valid_count"] == 9
    assert first["counts"]["scoring_reproducibility_failure_count"] == 0
    assert first["coverage"]["missing"]["skills"] == ["WRITING"]
    assert first["coverage"]["missing"]["scoring_modes"] == ["FEATURE_RUBRIC"]
    assert [row["work_item_id"] for row in first["targeted_queue"]] == ["W_TARGET"]
    assert first["session_011"]["disposition"] == "SAFELY_ABANDON_REQUIRED_NOT_TARGETED"
    assert validator.validate_artifact(first)["error_count"] == 0


def test_autofail_classification_is_closed_and_does_not_copy_private_answers(tmp_path):
    database, evidence, projection = _fixture(tmp_path)
    artifact = gate.build(database_path=database, evidence_package=evidence, projection=projection)
    assert len(artifact["autofail_root_causes"]) == 9
    assert all(row["root_cause"] in gate.ROOT_CAUSES for row in artifact["autofail_root_causes"])
    serialized = gate.canonical(artifact)
    assert '"response":' not in serialized
    assert '"accepted_texts":' not in serialized
    assert '"access_token":' not in serialized


def test_validator_detects_digest_and_count_tampering(tmp_path):
    database, evidence, projection = _fixture(tmp_path)
    artifact = gate.build(database_path=database, evidence_package=evidence, projection=projection)
    artifact["counts"]["scoring_reproducibility_failure_count"] = 99
    result = validator.validate_artifact(artifact)
    assert result["error_count"] >= 2
    assert "artifact_digest_invalid" in result["errors"]
    assert "replay_failure_count_mismatch" in result["errors"]
