from __future__ import annotations

import importlib.util
import json
import sqlite3
import threading
import urllib.request
from copy import deepcopy
from pathlib import Path

import pytest

from ulga.builders import (
    build_a1fs_v1_razq01f_fullfix_real62_semantic_lexical_anchor_fallback
    as razq01f,
)
from ulga.builders import (
    build_a1fs_v1_razq01g_unit01_real_content_learner_product_release_readiness_acceptance
    as builder,
)
from ulga.validators import (
    validate_a1fs_v1_razq01g_unit01_real_content_learner_product_release_readiness_acceptance
    as validator,
)


def load_razq01f_fixture():
    path = Path(__file__).with_name(
        "test_a1fs_v1_razq01f_unit01_multisession_reconciliation_ci.py"
    )
    spec = importlib.util.spec_from_file_location("_razq01f_fixture", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def post_json(url: str, payload: dict) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def private_item(database: Path, item_id: str) -> dict:
    with sqlite3.connect(database) as connection:
        row = connection.execute(
            "SELECT private_item_json FROM u01qb02_item_catalog WHERE item_id=?",
            (item_id,),
        ).fetchone()
    assert row is not None
    return json.loads(row[0])


def test_razq01g_builds_and_serves_real_content_release_candidate(tmp_path: Path):
    fixture = load_razq01f_fixture()
    database = tmp_path / "learner_progress.sqlite3"
    multisession_root = tmp_path / "razq01f"
    release_root = tmp_path / "razq01g"
    fixture.setup_database(database)
    approved = fixture.approved_real44()
    razq01f.install_fullfix()

    source = razq01f.run_acceptance(
        database=database,
        approved_content=approved,
        learner_id="learner-razq01f-ci",
        output_root=multisession_root,
        session_prefix="session-razq01f-ci",
    )
    assert source["status"] == razq01f.PASS_STATUS

    release = builder.build_release_candidate(
        database=database,
        approved_content=approved,
        learner_id="learner-razq01f-ci",
        multisession_root=multisession_root,
        release_root=release_root,
        release_session_id="session-razq01g-release-ci",
    )
    result = validator.validate(
        database=database,
        approved_content=approved,
        multisession_root=multisession_root,
        release_root=release_root,
    )

    assert release["status"] == builder.PASS_STATUS
    assert release["release_state"] == "READY_FOR_LOCAL_PRIVATE_LEARNER_CANARY"
    assert release["formal_full_product_release_approved"] is False
    assert release["public_delivery"] is False
    assert release["private_localhost_only"] is True
    assert release["item_count"] == 10
    assert release["distinct_item_count"] == 10
    assert release["distinct_content_asset_count"] == 10
    assert release["authoritative_extension_content_count"] >= 2
    assert release["fresh_cross_session_content_count"] >= 0
    assert result["validation_status"] == validator.PASS_STATUS
    assert result["error_count"] == 0, result["errors"]
    assert result["exposure_count"] == 0
    assert result["attempt_count"] == 0

    with pytest.raises(builder.ReleaseReadinessError, match="loopback"):
        builder.create_server(
            database=database,
            release_root=release_root,
            host="0.0.0.0",
            port=0,
        )

    server = builder.create_server(
        database=database,
        release_root=release_root,
        host="127.0.0.1",
        port=0,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    base = f"http://{host}:{port}"
    try:
        with urllib.request.urlopen(f"{base}/api/session", timeout=10) as response:
            session = json.loads(response.read().decode("utf-8"))
        assert session["session_id"] == "session-razq01g-release-ci"
        assert session["item_count"] == 10
        assert all("content_binding" in row for row in session["items"])

        for name in ("index.html", "styles.css", "app.js"):
            with urllib.request.urlopen(f"{base}/{name}", timeout=10) as response:
                assert response.status == 200
                assert response.read()

        item = next(row for row in session["items"] if row["capture_enabled"] is True)
        exposed = post_json(
            f"{base}/api/exposure",
            {
                "item_id": item["item_id"],
                "expected_session_version": session["session_version"],
            },
        )
        answer = deepcopy(private_item(database, item["item_id"])["correct_answer"])
        attempted = post_json(
            f"{base}/api/attempt",
            {
                "item_id": item["item_id"],
                "response": answer,
                "expected_session_version": exposed["session_version"],
            },
        )
        assert attempted["outcome"] == "AUTO_PASS"
        assert attempted["m6_response_scoring_reused"] is True
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=10)

    after = validator.validate(
        database=database,
        approved_content=approved,
        multisession_root=multisession_root,
        release_root=release_root,
    )
    assert after["validation_status"] == validator.PASS_STATUS
    assert after["error_count"] == 0, after["errors"]
    assert after["exposure_count"] == 1
    assert after["attempt_count"] == 1

    with sqlite3.connect(database) as connection:
        parallel_tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'razq01g%'"
        ).fetchall()
    assert parallel_tables == []

    manifest_path = release_root / builder.RELEASE_MANIFEST_NAME
    tampered = json.loads(manifest_path.read_text(encoding="utf-8"))
    tampered["public_delivery"] = True
    manifest_path.write_text(
        json.dumps(tampered, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    failed = validator.validate(
        database=database,
        approved_content=approved,
        multisession_root=multisession_root,
        release_root=release_root,
    )
    assert failed["validation_status"] == validator.FAIL_STATUS
    assert failed["error_count"] == 1
    assert "release_manifest_digest_invalid" in failed["errors"][0]
