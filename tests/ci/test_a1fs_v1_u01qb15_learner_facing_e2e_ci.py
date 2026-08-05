from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE = "product.a1fs_v1_2_1.u01qb15_runtime_server_e2e"


def _run_isolated(script: str) -> dict:
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    return json.loads(completed.stdout)


def test_manifest_and_secure_static_activate_unit01_e2e_adapter_without_changing_release_denominators() -> None:
    manifest = json.loads(
        (REPO_ROOT / "product/a1fs_v1_2_1/product_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    index = (
        REPO_ROOT / "product/a1fs_v1_2_1/runtime/secure_static/index.html"
    ).read_text(encoding="utf-8")
    adapter = (
        REPO_ROOT / "product/a1fs_v1_2_1/runtime/secure_static/u01qb15.js"
    ).read_text(encoding="utf-8")

    assert manifest["serve_module"] == MODULE
    assert manifest["start_command"] == f"python -m {MODULE} start"
    assert manifest["unit_count"] == 24
    assert manifest["lesson_count"] == 72
    assert manifest["asset_count"] == 277
    assert manifest["unit01_questionbank_runtime_item_count"] == 474
    assert manifest["unit01_questionbank_form_count"] == 12
    assert manifest["unit01_questionbank_blueprint_activity_count"] == 240
    assert manifest["unit01_questionbank_form_selection_mode"] == (
        "ORDERED_PER_SKILL_COMPLETION"
    )
    assert '<script src="/app.js"></script><script src="/u01qb15.js"></script>' in index
    assert "/api/u01qb15/form/start" in adapter
    assert "/api/u01qb15/form/active" in adapter
    assert "/api/u01qb15/exposure" in adapter
    assert "/api/u01qb15/response" in adapter
    assert "return u01qb15LegacyBegin(lane)" in adapter
    assert "complete.disabled=!gate.completion_allowed" in adapter


def test_u01qb15_secure_static_route_is_authenticated_and_does_not_fall_through_to_legacy_404() -> None:
    result = _run_isolated(
        r'''
import json, tempfile
from pathlib import Path
from product.a1fs_v1_2_1 import u01qb15_runtime_server_e2e as e2e

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    adapter = root / "u01qb15.js"
    adapter.write_text("'use strict';\nwindow.__u01qb15_loaded=true;\n", encoding="utf-8")

    class Server:
        secure_static_root = root

    class FakeHandler:
        def __init__(self, *, claims):
            self.path = "/u01qb15.js"
            self.server = Server()
            self.claims_value = claims
            self.static_call = None
            self.json_call = None
            self.fallback_called = False
        def _transport_valid(self):
            return True
        def _claims(self):
            return self.claims_value
        def _static(self, path, content_type):
            self.static_call = [str(path), content_type]
        def _json(self, status, value):
            self.json_call = [status, value]

    authenticated = FakeHandler(claims={"sub":"learner"})
    e2e._do_get_with_u01qb15_static(authenticated)

    anonymous = FakeHandler(claims=None)
    e2e._do_get_with_u01qb15_static(anonymous)

    fallback = FakeHandler(claims={"sub":"learner"})
    fallback.path = "/app.js"
    original = e2e._ORIGINAL_HANDLER_GET
    try:
        e2e._ORIGINAL_HANDLER_GET = lambda self: setattr(self, "fallback_called", True)
        e2e._do_get_with_u01qb15_static(fallback)
    finally:
        e2e._ORIGINAL_HANDLER_GET = original

    print(json.dumps({
        "authenticated_static": authenticated.static_call,
        "authenticated_json": authenticated.json_call,
        "anonymous_static": anonymous.static_call,
        "anonymous_json": anonymous.json_call,
        "fallback_called": fallback.fallback_called,
    }))
'''
    )
    assert result["authenticated_static"][0].endswith("u01qb15.js")
    assert result["authenticated_static"][1] == "application/javascript; charset=utf-8"
    assert result["authenticated_json"] is None
    assert result["anonymous_static"] is None
    assert result["anonymous_json"] == [401, {"error": "authentication_required"}]
    assert result["fallback_called"] is True


def test_unit01_form_progression_is_ordered_per_skill_and_caps_at_twelve() -> None:
    result = _run_isolated(
        r'''
import json, sqlite3, tempfile
from pathlib import Path
from product.a1fs_v1_2_1 import u01qb15_runtime_server_e2e as e2e

with tempfile.TemporaryDirectory() as tmp:
    db = Path(tmp) / "progress.sqlite3"
    with sqlite3.connect(db) as connection:
        connection.executescript("""
        CREATE TABLE learning_sessions(
          session_id TEXT PRIMARY KEY,
          learner_id TEXT NOT NULL,
          skill TEXT NOT NULL,
          session_state TEXT NOT NULL
        );
        CREATE TABLE u01qb13_session_bindings(
          session_id TEXT NOT NULL,
          activity_id TEXT NOT NULL
        );
        """)
        for index in range(1, 3):
            sid = f"R{index}"
            connection.execute(
                "INSERT INTO learning_sessions VALUES(?,?,?,?)",
                (sid, "L", "READING", "COMPLETED"),
            )
            connection.execute(
                "INSERT INTO u01qb13_session_bindings VALUES(?,?)",
                (sid, f"A{index}"),
            )
        for index in range(1, 13):
            sid = f"W{index}"
            connection.execute(
                "INSERT INTO learning_sessions VALUES(?,?,?,?)",
                (sid, "L", "WRITING", "COMPLETED"),
            )
            connection.execute(
                "INSERT INTO u01qb13_session_bindings VALUES(?,?)",
                (sid, f"B{index}"),
            )
        connection.commit()
    print(json.dumps({
        "reading": e2e.next_form_ordinal(db, learner_id="L", skill="READING"),
        "writing": e2e.next_form_ordinal(db, learner_id="L", skill="WRITING"),
        "speaking": e2e.next_form_ordinal(db, learner_id="L", skill="SPEAKING"),
    }))
'''
    )
    assert result == {"reading": 3, "writing": None, "speaking": 1}


def test_start_form_fills_expected_ordinal_and_rejects_skipping() -> None:
    result = _run_isolated(
        r'''
import json, sqlite3, tempfile
from pathlib import Path
from product.a1fs_v1_2_1 import u01qb15_runtime_server_e2e as e2e

with tempfile.TemporaryDirectory() as tmp:
    db = Path(tmp) / "ordered.sqlite3"
    with sqlite3.connect(db) as connection:
        connection.executescript("""
        CREATE TABLE learning_sessions(
          session_id TEXT PRIMARY KEY,
          learner_id TEXT NOT NULL,
          skill TEXT NOT NULL,
          session_state TEXT NOT NULL
        );
        CREATE TABLE u01qb13_session_bindings(
          session_id TEXT NOT NULL,
          activity_id TEXT NOT NULL
        );
        """)
        connection.execute(
            "INSERT INTO learning_sessions VALUES(?,?,?,?)",
            ("R1", "L", "READING", "COMPLETED"),
        )
        connection.execute(
            "INSERT INTO u01qb13_session_bindings VALUES(?,?)",
            ("R1", "A1"),
        )
        connection.commit()

    class Fake:
        database_path = db
        default_learner_id = "L"

    captured = {}
    def fake_start(self, payload):
        captured.update(payload)
        return {"session_id":"S2","session_version":1,"skill":payload["skill"]}

    e2e._ORIGINAL_START_FORM = fake_start
    started = e2e._start_u01qb15_form_ordered(Fake(), {"skill":"READING"})
    rejected = None
    try:
        e2e._start_u01qb15_form_ordered(
            Fake(), {"skill":"READING", "form_ordinal":7}
        )
    except e2e.LearnerFacingE2EError as exc:
        rejected = str(exc)
    print(json.dumps({
        "captured_form": captured["form_ordinal"],
        "ordered_form": started["ordered_form_ordinal"],
        "mode": started["form_selection_mode"],
        "rejected": rejected,
    }))
'''
    )
    assert result["captured_form"] == 2
    assert result["ordered_form"] == 2
    assert result["mode"] == "ORDERED_PER_SKILL_COMPLETION"
    assert result["rejected"] == "UNIT01_FORM_SEQUENCE_OUT_OF_ORDER:READING:7:2"


def test_e2e_facade_preserves_existing_runtime_authority_and_policy_boundary() -> None:
    result = _run_isolated(
        r'''
import json
from product.a1fs_v1_2_1 import u01qb15_runtime_server_e2e as e2e
print(json.dumps({
    "mode": e2e.A1FS_CONTENT_POLICY_MODE,
    "has_exemption": bool(e2e.A1FS_CONTENT_POLICY_EXEMPTION),
    "impl_module": e2e.impl.MODULE,
    "base_module": e2e.impl.base.MODULE,
    "next": e2e.NEXT_SHORT_STEP,
}))
'''
    )
    assert result["mode"] == "NOT_CONTENT_PRODUCER"
    assert result["has_exemption"] is True
    assert result["impl_module"] == MODULE
    assert result["base_module"] == MODULE
    assert result["next"] == "A1FS-V1-U01QB15_LearnerFacingE2EPrivateBrowserReadback"


def test_u01qb15_adapter_javascript_parses_when_node_is_available() -> None:
    node = shutil.which("node")
    if node is None:
        return
    path = REPO_ROOT / "product/a1fs_v1_2_1/runtime/secure_static/u01qb15.js"
    completed = subprocess.run(
        [node, "--check", str(path)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
