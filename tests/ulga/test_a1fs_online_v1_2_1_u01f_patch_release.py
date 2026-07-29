from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

import pytest

from ulga.builders import _a1fs_online_v1_2_1_u01f_static as static_patch
from ulga.builders import build_a1fs_online_v1_s14_learner_facing_curriculum_progress_semantics as s14
from ulga.builders import build_a1fs_online_v1_2_1_u01f_patch_release as patch
from ulga.builders import build_a1fs_online_v1_2_u01e_s03_fixed_multitype_item_bank as s03


def test_s00_reproduces_v12_single_select_first_position_defect() -> None:
    rows = [
        row
        for row in s03.ITEM_SPECS
        if s03.QUESTION_TYPE_CONTRACTS[str(row["question_type"])][
            "interaction_mode"
        ]
        == "SINGLE_SELECT"
    ]
    assert len(rows) == 5
    assert all(list(row["options"]).index(row["correct_answer"]) == 0 for row in rows)


def _pending_readiness() -> dict:
    return {
        "session_id": "S",
        "lesson_id": "L",
        "skill": "WRITING",
        "session_state": "ACTIVE",
        "session_version": 9,
        "gate_mode": "OLD",
        "required_response_count": 8,
        "attempted_response_count": 8,
        "passed_response_count": 7,
        "not_attempted_count": 0,
        "retry_required_count": 0,
        "pending_human_review_count": 1,
        "completion_allowed": False,
        "blocking_reason_codes": ["HUMAN_REVIEW_PENDING"],
        "assets": [],
        "mastery_claimed": False,
    }


def test_s01_pending_review_is_nonblocking_but_not_pass_or_mastery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        patch._BASE_V12_APPLICATION,
        "completion_readiness",
        lambda _self, _session_id: _pending_readiness(),
    )
    app = object.__new__(patch.V121Application)
    value = app.completion_readiness("S")
    assert value["completion_allowed"] is True
    assert value["assessment_resolution_state"] == "PENDING_HUMAN_REVIEW"
    assert value["pending_review_counts_as_pass"] is False
    assert value["pending_review_counts_as_mastery"] is False
    assert value["blocking_reason_codes"] == []


def test_s01_reject_remains_a_completion_blocker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = _pending_readiness()
    value.update(
        {
            "passed_response_count": 7,
            "pending_human_review_count": 0,
            "retry_required_count": 1,
            "blocking_reason_codes": ["LATEST_ATTEMPT_RETRY_REQUIRED"],
        }
    )
    monkeypatch.setattr(
        patch._BASE_V12_APPLICATION,
        "completion_readiness",
        lambda _self, _session_id: value,
    )
    app = object.__new__(patch.V121Application)
    result = app.completion_readiness("S")
    assert result["completion_allowed"] is False
    assert result["blocking_reason_codes"] == ["LATEST_ATTEMPT_RETRY_REQUIRED"]


def test_s01_review_uses_existing_canonical_refresh(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = tmp_path / "learner.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TABLE response_attempts(attempt_id TEXT PRIMARY KEY,learner_id TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO response_attempts VALUES('A1','LEARNER_1')"
        )
    monkeypatch.setattr(
        patch._BASE_V12_APPLICATION,
        "review_attempt",
        lambda _self, _payload, reviewer_id: {
            "review_result": {"outcome": "HUMAN_APPROVE"},
            "mastery_refreshed": False,
        },
    )
    app = object.__new__(patch.V121Application)
    app.database_path = database
    calls: list[str] = []
    app.refresh_canonical_learning = lambda *, learner_id: calls.append(learner_id) or {
        "evaluation_state": "EVALUATED"
    }
    result = app.review_attempt({"attempt_id": "A1"}, reviewer_id="REVIEWER")
    assert calls == ["LEARNER_1"]
    assert result["mastery_refreshed"] is True
    assert result["canonical_learning_refresh"]["evaluation_state"] == "EVALUATED"
    assert result["session_reopened"] is False


def test_s02_shuffle_is_stable_within_session_and_varies_across_sessions() -> None:
    options = ["correct", "distractor-b", "distractor-c"]
    first = static_patch.stable_option_order("SESSION-1", "ASSET-1", options)
    assert first == static_patch.stable_option_order("SESSION-1", "ASSET-1", options)
    positions = {
        static_patch.stable_option_order(f"SESSION-{index}", "ASSET-1", options).index(
            "correct"
        )
        for index in range(30)
    }
    assert positions == {0, 1, 2}
    assert sorted(first) == sorted(options)


def test_s03_static_surface_fixes_review_payload_and_option_order(tmp_path: Path) -> None:
    root = tmp_path / "static"
    root.mkdir()
    (root / "index.html").write_text(
        '<html><body><main><section id="human-review-panel"></section></main></body></html>',
        encoding="utf-8",
    )
    (root / "styles.css").write_text("body{}", encoding="utf-8")
    (root / "app.js").write_text(
        "const outcomeLabel=value=>({PENDING_HUMAN_REVIEW:'等待人工審核'}[value]);"
        "const options=asset.learner_payload.options||[];"
        "async function submitReview(card,row){const criteria={};const decision='APPROVE',notes='';"
        "const response=await api('/api/human-review/decision',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({attempt_id:row.attempt_id,decision,criteria,notes})});}",
        encoding="utf-8",
    )
    result = static_patch.patch_static(root, root)
    assert result["validation_status"] == "PASS_A1FS_V1_2_1_U01F_STATIC"
    app = (root / "app.js").read_text(encoding="utf-8")
    assert "function stableSessionOptions" in app
    assert "已送交人工審核，可完成本次學習" in app
    assert static_patch.BAD_REVIEW_SUBMIT not in app
    assert static_patch.GOOD_REVIEW_SUBMIT in app
    assert "/api/my-writing-reviews" in app


def test_learner_feedback_is_scoped_to_default_learner(tmp_path: Path) -> None:
    database = tmp_path / "feedback.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE response_attempts(
              attempt_id TEXT PRIMARY KEY,learner_id TEXT,lesson_id TEXT,
              asset_key TEXT,response_json TEXT,submitted_at TEXT
            );
            CREATE TABLE scoring_results(attempt_id TEXT PRIMARY KEY,outcome TEXT);
            CREATE TABLE response_contracts(asset_key TEXT PRIMARY KEY,skill TEXT);
            CREATE TABLE human_review_queue(
              attempt_id TEXT PRIMARY KEY,decision TEXT,reviewed_at TEXT,
              criteria_json TEXT,notes TEXT
            );
            """
        )
        connection.executemany(
            "INSERT INTO response_contracts VALUES(?,?)",
            [("W1", "WRITING"), ("W2", "WRITING")],
        )
        connection.executemany(
            "INSERT INTO response_attempts VALUES(?,?,?,?,?,?)",
            [
                ("A1", "L1", "LESSON", "W1", json.dumps("My sentence."), "2026-01-01T00:00:00Z"),
                ("A2", "L2", "LESSON", "W2", json.dumps("Other."), "2026-01-02T00:00:00Z"),
            ],
        )
        connection.executemany(
            "INSERT INTO scoring_results VALUES(?,?)",
            [("A1", "HUMAN_APPROVE"), ("A2", "HUMAN_REJECT")],
        )
        connection.executemany(
            "INSERT INTO human_review_queue VALUES(?,?,?,?,?)",
            [
                ("A1", "APPROVE", "2026-01-03T00:00:00Z", "{}", "Good."),
                ("A2", "REJECT", "2026-01-03T00:00:00Z", "{}", "Fix."),
            ],
        )
    app = object.__new__(patch.V121Application)
    app.database_path = database
    app.default_learner_id = "L1"
    value = app.learner_review_feedback()
    assert value["review_count"] == 1
    assert value["reviews"][0]["response"] == "My sentence."
    assert value["reviews"][0]["notes"] == "Good."


def _v121_bootstrap_fixture() -> dict:
    return {
        "learner_product_semantics": {"unit_label_count": 24},
        "units": [
            {
                "grammar_unit_id": grammar_id,
                "sequence_index": label["sequence_index"],
                "lanes": [
                    {
                        "skill": skill,
                        "lesson_id": f"A1FS_ONLINE_V1:{grammar_id}:{skill}",
                        "asset_count": (
                            patch.EXPECTED_UNIT01_COUNTS[skill]
                            if grammar_id == patch.v12._core.m01.UNIT_ID
                            else {"READING": 4, "WRITING": 4, "SPEAKING": 3}[skill]
                        ),
                        "assets": [],
                    }
                    for skill in ("READING", "WRITING", "SPEAKING")
                ],
            }
            for grammar_id, label in sorted(
                s14.UNIT_LABELS.items(),
                key=lambda row: row[1]["sequence_index"],
            )
        ]
    }


def test_v121_public_application_bootstrap_accepts_runtime_277_asset_denominator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        patch._BASE_V12_APPLICATION,
        "bootstrap",
        lambda _self: _v121_bootstrap_fixture(),
    )
    app = object.__new__(patch.V121Application)
    value = app.bootstrap()
    assert value["product_version"] == patch.TARGET_VERSION
    assert value["validation_status"] == patch.PASS_STATUS
    assert sum(
        lane["asset_count"]
        for unit in value["units"]
        for lane in unit["lanes"]
    ) == patch.EXPECTED_ASSET_COUNT
    assert value["learner_product_semantics"]["unit_label_count"] == 24


def test_release_start_uses_manifest_serve_module_and_release_only_pythonpath(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "product"
    app_root = root / "releases" / patch.TARGET_VERSION / "app"
    app_root.mkdir(parents=True)
    (root / "shared").mkdir()
    manifest = {
        "product_version": patch.TARGET_VERSION,
        "app_root": f"releases/{patch.TARGET_VERSION}/app",
        "serve_module": patch.MODULE,
    }
    captured: dict[str, object] = {}

    class ProbeSocket:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def connect_ex(self, _address):
            return 1

    class ProbeProcess:
        pid = 12345

        def poll(self):
            return None

        def terminate(self):
            captured["terminated"] = True

    def popen(args, **kwargs):
        captured["args"] = args
        captured["cwd"] = kwargs["cwd"]
        captured["env"] = kwargs["env"]
        return ProbeProcess()

    monkeypatch.setenv("A1FS_S11_AUTH_USERNAME", "operator")
    monkeypatch.setenv("A1FS_S11_AUTH_PASSWORD", "password")
    monkeypatch.setenv("A1FS_S11_SESSION_SECRET", "secret")
    monkeypatch.setenv("PYTHONPATH", str(Path(__file__).resolve().parents[2]))
    monkeypatch.setattr(patch.r01, "_load_product", lambda _root: (patch.TARGET_VERSION, manifest, {}, {}))
    monkeypatch.setattr(patch.r01, "_resolve", lambda base, rel: Path(base) / rel)
    monkeypatch.setattr(patch.r01.socket, "socket", lambda: ProbeSocket())
    monkeypatch.setattr(patch.r01.subprocess, "Popen", popen)
    health_calls = {"count": 0}

    def health(_port, _timeout=2.0):
        health_calls["count"] += 1
        return health_calls["count"] == 1

    monkeypatch.setattr(patch.r01, "_health", health)

    result = patch.r01.start(product_root=root, port=8765)

    assert result["status"] == "PASS_A1FS_V1_STARTED"
    assert captured["args"][2] == patch.MODULE
    assert captured["cwd"] == app_root
    env = captured["env"]
    assert isinstance(env, dict)
    assert env["PYTHONPATH"] == str(app_root)
    assert os.pathsep not in env["PYTHONPATH"]
    assert env["PYTHONDONTWRITEBYTECODE"] == "1"


def test_v121_release_packaging_copies_runtime_acceptance_modules(tmp_path: Path) -> None:
    root = tmp_path / "product"
    _minimal_product(root)
    candidate, _static_result = patch.build_candidate_release(
        product_root=root,
        code_root=tmp_path,
        output_root=tmp_path / "output",
    )
    app_builders = candidate / "app/ulga/builders"
    copied = {
        "s14": app_builders / Path(s14.__file__).name,
        "s05": app_builders / Path(patch.v12.__file__).name,
        "s05_core": app_builders / Path(patch.v12._core.__file__).name,
        "v121": app_builders / Path(patch.__file__).name,
    }
    assert all(path.is_file() for path in copied.values())
    for source, packaged in (
        (Path(s14.__file__), copied["s14"]),
        (Path(patch.v12.__file__), copied["s05"]),
        (Path(patch.v12._core.__file__), copied["s05_core"]),
        (Path(patch.__file__), copied["v121"]),
    ):
        assert patch.r01.file_digest(source) == patch.r01.file_digest(packaged)


def test_v121_authenticated_http_readback_records_failure_trace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("A1FS_S11_AUTH_USERNAME", "operator")
    monkeypatch.setenv("A1FS_S11_AUTH_PASSWORD", "password")
    monkeypatch.setenv("A1FS_S11_SESSION_SECRET", "secret")
    calls: list[str] = []

    def request_runner(_port, method, path, payload=None, **kwargs):
        del payload, kwargs
        calls.append(f"{method} {path}")
        if path == "/auth/login":
            return {"csrf_token": "token"}, {"Set-Cookie": "a1fs=test; Path=/"}
        raise ConnectionError("remote closed")

    with pytest.raises(patch.U01FPatchError, match="HTTP_REQUEST_FAILED.*api/bootstrap"):
        patch.authenticated_http_readback(
            port=8765,
            request_runner=request_runner,
        )
    assert calls == ["POST /auth/login", "GET /api/bootstrap"]


def test_v121_decorator_accepts_runtime_277_asset_denominator() -> None:
    bootstrap = {
        "units": [
            {
                "grammar_unit_id": grammar_id,
                "sequence_index": label["sequence_index"],
                "lanes": [
                    {
                        "skill": skill,
                        "lesson_id": f"A1FS_ONLINE_V1:{grammar_id}:{skill}",
                        "asset_count": (
                            patch.EXPECTED_UNIT01_COUNTS[skill]
                            if grammar_id == patch.v12._core.m01.UNIT_ID
                            else {"READING": 4, "WRITING": 4, "SPEAKING": 3}[skill]
                        ),
                        "assets": [],
                    }
                    for skill in ("READING", "WRITING", "SPEAKING")
                ],
            }
            for grammar_id, label in sorted(
                s14.UNIT_LABELS.items(),
                key=lambda row: row[1]["sequence_index"],
            )
        ]
    }
    value = s14._decorate_bootstrap(
        bootstrap,
        expected_asset_count=patch.EXPECTED_ASSET_COUNT,
    )
    assert sum(
        lane["asset_count"]
        for unit in value["units"]
        for lane in unit["lanes"]
    ) == patch.EXPECTED_ASSET_COUNT
    assert value["learner_product_semantics"]["unit_label_count"] == 24


def _minimal_product(root: Path) -> None:
    grammar_ids = [patch.v12._core.m01.UNIT_ID] + [f"GRAMMAR_DUMMY_{i:02d}" for i in range(2, 25)]
    sequence = {grammar_id: index for index, grammar_id in enumerate(grammar_ids, start=1)}
    bundles = {}
    for grammar_id in grammar_ids:
        for skill, count in (("READING", 4), ("WRITING", 4), ("SPEAKING", 3)):
            if grammar_id == patch.v12._core.m01.UNIT_ID:
                count = patch.EXPECTED_UNIT01_COUNTS[skill]
            lesson_id = f"A1FS_ONLINE_V1:{grammar_id}:{skill}"
            bundles[lesson_id] = {
                "lesson": {"lesson_id": lesson_id, "skill": skill, "level": "A1"},
                "assets": [
                    {
                        "asset_key": f"{lesson_id}:A{index}",
                        "learner_payload": {"options": []},
                    }
                    for index in range(count)
                ],
            }
    assert sum(len(row["assets"]) for row in bundles.values()) == 277

    release = root / "releases" / patch.SOURCE_VERSION
    static = release / "runtime" / "secure_static"
    app = release / "app" / "ulga" / "builders"
    static.mkdir(parents=True)
    app.mkdir(parents=True)
    (release / "runtime" / "graph.json").write_text("{}", encoding="utf-8")
    (release / "runtime" / "bundles.json").write_text(
        json.dumps(bundles), encoding="utf-8"
    )
    (release / "runtime" / "sequence.json").write_text(
        json.dumps(sequence), encoding="utf-8"
    )
    (release / "runtime" / "unit01_target_registry.json").write_text(
        json.dumps(
            {
                "items": [
                    {"runtime_status": "RUNTIME_ACTIVE", "identity": index}
                    for index in range(24)
                ]
            }
        ),
        encoding="utf-8",
    )
    (static / "index.html").write_text(
        '<html><body><main><section id="human-review-panel"></section></main></body></html>',
        encoding="utf-8",
    )
    (static / "styles.css").write_text("body{}", encoding="utf-8")
    (static / "app.js").write_text(
        "const outcomeLabel=value=>({PENDING_HUMAN_REVIEW:'等待人工審核'}[value]);"
        "const options=asset.learner_payload.options||[];"
        "async function submitReview(card,row){const criteria={};const decision='APPROVE',notes='';"
        "const response=await api('/api/human-review/decision',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({attempt_id:row.attempt_id,decision,criteria,notes})});}",
        encoding="utf-8",
    )
    manifest = patch.r01._release_manifest(patch.SOURCE_VERSION)
    manifest.update(
        {
            "product_version": patch.SOURCE_VERSION,
            "release_id": "V12_FIXTURE",
            "unit01_target_registry_path": f"releases/{patch.SOURCE_VERSION}/runtime/unit01_target_registry.json",
            "serve_module": "fixture.module",
            "unit_count": 24,
            "lesson_count": 72,
            "asset_count": 277,
        }
    )
    patch.r01.write_json(release / "release_manifest.json", manifest)
    patch.r01._write_checksums(release)

    shared = root / "shared"
    (shared / "database").mkdir(parents=True)
    (shared / "auth").mkdir(parents=True)
    (shared / "learner_state" / "canonical_learning_state").mkdir(parents=True)
    with sqlite3.connect(shared / "database" / "learner_runtime.sqlite3") as connection:
        connection.execute(
            "CREATE TABLE learner_profiles(learner_id TEXT PRIMARY KEY,profile_state TEXT)"
        )
        connection.execute("INSERT INTO learner_profiles VALUES('L1','ACTIVE')")
    with sqlite3.connect(shared / "auth" / "auth_state.sqlite3") as connection:
        connection.execute("CREATE TABLE auth(value TEXT)")
    (root / "current_version.txt").write_text(patch.SOURCE_VERSION + "\n", encoding="ascii")


def test_s04_patch_release_install_rollback_and_forward_switch(tmp_path: Path) -> None:
    root = tmp_path / "product"
    _minimal_product(root)
    candidate, static_result = patch.build_candidate_release(
        product_root=root, code_root=tmp_path, output_root=tmp_path / "output"
    )
    assert static_result["stable_session_shuffle_present"] is True
    manifest = patch.r01.read_json(candidate / "release_manifest.json", "candidate")
    assert manifest["product_version"] == "1.2.1"
    assert manifest["serve_module"] == patch.MODULE
    assert manifest["database_migration_mode"] == "NONE_SHARED_STATE_PRESERVED"

    patch.r01.install_candidate(
        product_root=root, candidate=candidate, version=patch.TARGET_VERSION
    )
    assert patch.r01._current_version(root) == "1.2.1"
    installed = patch.installed_product_readback(root)
    assert installed["unit_count"] == 24
    assert installed["lesson_count"] == 72
    assert installed["asset_count"] == 277
    assert installed["unit01_counts"] == {"READING": 10, "WRITING": 8, "SPEAKING": 6}

    patch.r01.rollback(product_root=root, version=patch.SOURCE_VERSION)
    assert patch.r01._current_version(root) == "1.2.0"
    patch.r01._switch_version(root, patch.TARGET_VERSION)
    assert patch.r01._current_version(root) == "1.2.1"
