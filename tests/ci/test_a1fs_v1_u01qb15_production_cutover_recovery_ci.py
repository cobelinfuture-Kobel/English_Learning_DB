from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


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


def test_manifest_routes_to_recovery_safe_consumer_without_changing_product_denominators() -> None:
    manifest = json.loads(
        (REPO_ROOT / "product/a1fs_v1_2_1/product_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["serve_module"] == (
        "product.a1fs_v1_2_1.u01qb15_runtime_server_e2e"
    )
    assert manifest["start_command"] == (
        "python -m product.a1fs_v1_2_1.u01qb15_runtime_server_e2e start"
    )
    assert manifest["unit_count"] == 24
    assert manifest["lesson_count"] == 72
    assert manifest["asset_count"] == 277
    assert manifest["unit01_questionbank_runtime_item_count"] == 474
    assert manifest["unit01_questionbank_form_count"] == 12
    assert manifest["unit01_questionbank_blueprint_activity_count"] == 240


def test_exact_partial_u01qb15_migration_is_recoverable_without_rerunning_migration() -> None:
    result = _run_isolated(
        r'''
import json, sqlite3, tempfile
from pathlib import Path
from product.a1fs_v1_2_1 import u01qb15_runtime_server_recovery as recovery

with tempfile.TemporaryDirectory() as tmp:
    db = Path(tmp) / "partial.sqlite3"
    with sqlite3.connect(db) as connection:
        connection.executescript("""
        CREATE TABLE u01qb15_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE u01qb02_item_catalog(item_id INTEGER);
        CREATE TABLE razq01e_extension_items(item_id INTEGER);
        CREATE TABLE u01qb02_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE razq01e_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        """)
        connection.executemany(
            "INSERT INTO u01qb15_metadata(key,value) VALUES(?,?)",
            [
                ("validation_status", recovery.impl.private_runner.u15.PASS_STATUS),
                ("canonical_revision", recovery.impl.private_runner.u15.CANONICAL_REVISION),
                ("base_artifact_sha256", "a" * 64),
                ("extension_artifact_sha256", "b" * 64),
            ],
        )
        connection.executemany("INSERT INTO u01qb02_item_catalog VALUES(?)", [(i,) for i in range(474)])
        connection.executemany("INSERT INTO razq01e_extension_items VALUES(?)", [(i,) for i in range(186)])
        connection.commit()
    capacity = {
        "runtime_bindable_scene_count": 31,
        "deferred_scene_refs": ["U01-MA-FOOD-04"],
        "verified_activity_count": 240,
        "all_36_skill_sessions_distinct_item_capacity_proven": True,
    }
    state = recovery._partial_migration_state(
        db,
        expected_base_artifact_sha256="a" * 64,
        expected_extension_artifact_sha256="b" * 64,
        capacity=capacity,
    )
    print(json.dumps({
        "runtime": state["runtime_item_count"],
        "extension": state["extension_item_count"],
        "base": state["base_item_count"],
        "recovered": state["recovered_existing_migration"],
        "deferred": state["per_scene_runtime_capacity"]["deferred_scene_refs"],
    }))
'''
    )
    assert result == {
        "runtime": 474,
        "extension": 186,
        "base": 288,
        "recovered": True,
        "deferred": ["U01-MA-FOOD-04"],
    }


def test_partial_recovery_fails_closed_on_real62_extension_identity_drift() -> None:
    result = _run_isolated(
        r'''
import json, sqlite3, tempfile
from pathlib import Path
from product.a1fs_v1_2_1 import u01qb15_runtime_server_recovery as recovery

with tempfile.TemporaryDirectory() as tmp:
    db = Path(tmp) / "partial.sqlite3"
    with sqlite3.connect(db) as connection:
        connection.executescript("""
        CREATE TABLE u01qb15_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE u01qb02_item_catalog(item_id INTEGER);
        CREATE TABLE razq01e_extension_items(item_id INTEGER);
        CREATE TABLE u01qb02_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE razq01e_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        """)
        connection.executemany(
            "INSERT INTO u01qb15_metadata(key,value) VALUES(?,?)",
            [
                ("validation_status", recovery.impl.private_runner.u15.PASS_STATUS),
                ("canonical_revision", recovery.impl.private_runner.u15.CANONICAL_REVISION),
                ("base_artifact_sha256", "a" * 64),
                ("extension_artifact_sha256", "c" * 64),
            ],
        )
        connection.executemany("INSERT INTO u01qb02_item_catalog VALUES(?)", [(i,) for i in range(474)])
        connection.executemany("INSERT INTO razq01e_extension_items VALUES(?)", [(i,) for i in range(186)])
        connection.commit()
    try:
        recovery._partial_migration_state(
            db,
            expected_base_artifact_sha256="a" * 64,
            expected_extension_artifact_sha256="b" * 64,
            capacity={},
        )
    except recovery.ProductCutoverRecoveryError as exc:
        print(json.dumps({"error": str(exc)}))
    else:
        raise SystemExit("identity drift was not rejected")
'''
    )
    assert result["error"] == "PARTIAL_REAL62_EXTENSION_ARTIFACT_IDENTITY_DRIFT"


def test_fresh_cutover_executes_original_consumer_inside_existing_r1_deferred_scene_adapter() -> None:
    result = _run_isolated(
        r'''
import json
from pathlib import Path
from product.a1fs_v1_2_1 import u01qb15_runtime_server_recovery as recovery

original_semantics = recovery.impl.u13._scene_semantic_index
seen = {"inside": False}

def fake_original(*, database, real62_path):
    seen["inside"] = (
        recovery.impl.u13._scene_semantic_index
        is recovery.r1.tolerant_scene_semantic_index
    )
    return {"status": "PASS"}

recovery._ORIGINAL_CUTOVER_DATABASE = fake_original
value = recovery._fresh_cutover_with_deferred_scene_adapter(
    database=Path("unused.sqlite3"), real62_path=Path("unused.json")
)
print(json.dumps({
    "inside": seen["inside"],
    "restored": recovery.impl.u13._scene_semantic_index is original_semantics,
    "status": value["status"],
}))
'''
    )
    assert result == {"inside": True, "restored": True, "status": "PASS"}


def test_recovery_facade_is_non_content_producer_and_keeps_same_primary_task_identity() -> None:
    result = _run_isolated(
        r'''
import json
from product.a1fs_v1_2_1 import u01qb15_runtime_server_recovery as recovery
print(json.dumps({
    "mode": recovery.A1FS_CONTENT_POLICY_MODE,
    "has_exemption": bool(recovery.A1FS_CONTENT_POLICY_EXEMPTION),
    "same_task": recovery.TASK_ID == recovery.impl.TASK_ID,
    "same_next": recovery.NEXT_SHORT_STEP == recovery.impl.NEXT_SHORT_STEP,
    "module": recovery.MODULE,
}))
'''
    )
    assert result["mode"] == "NOT_CONTENT_PRODUCER"
    assert result["has_exemption"] is True
    assert result["same_task"] is True
    assert result["same_next"] is True
    assert result["module"].endswith("u01qb15_runtime_server_recovery")
