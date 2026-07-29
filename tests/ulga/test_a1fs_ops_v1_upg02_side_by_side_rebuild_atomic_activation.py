from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Mapping

import pytest

from tests.ulga import (
    _a1fs_online_v1_2_u01e_s05_release_migration_acceptance_core as s05_fixture,
)
from ulga.builders import (
    build_a1fs_ops_v1_upg02_side_by_side_rebuild_atomic_activation as rebuild,
)


def _source_root(tmp_path: Path) -> Path:
    root = s05_fixture.source_v111_root(tmp_path / "source")
    cache = root / "releases/1.1.1/app/ulga/builders/__pycache__"
    cache.mkdir(parents=True, exist_ok=True)
    (cache / "transient.cpython-312.pyc").write_bytes(b"transient")
    return root


def _fake_upgrade(**kwargs: Any) -> Mapping[str, Any]:
    root = Path(kwargs["product_root"])
    source = root / "releases/1.1.1"
    target = root / "releases/1.2.1"
    rebuild._copy_clean_tree(source, target)

    def rewrite(value: Any) -> Any:
        if isinstance(value, str):
            return value.replace("releases/1.1.1/", "releases/1.2.1/")
        if isinstance(value, list):
            return [rewrite(row) for row in value]
        if isinstance(value, dict):
            return {key: rewrite(child) for key, child in value.items()}
        return value

    manifest_path = target / "release_manifest.json"
    manifest = rewrite(json.loads(manifest_path.read_text(encoding="utf-8")))
    manifest["product_version"] = "1.2.1"
    manifest["release_id"] = "TEST-SIDE-BY-SIDE-1.2.1"
    rebuild.r01.write_json(manifest_path, manifest)
    version_path = target / "VERSION.json"
    version = json.loads(version_path.read_text(encoding="utf-8"))
    version["product_version"] = "1.2.1"
    rebuild.r01.write_json(version_path, version)
    (target / "checksums.json").unlink(missing_ok=True)
    rebuild.r01._write_checksums(target)
    rebuild.r01.validate_release(target)
    rebuild.r01._atomic_text(root / "current_version.txt", "1.2.1\n")
    return {"validation_status": "PASS_FAKE_CLEAN_REBUILD"}


def _fake_validator(root: Path) -> Mapping[str, Any]:
    assert rebuild.r01._current_version(root) == "1.2.1"
    manifest = rebuild.r01.validate_release(root / "releases/1.2.1")
    return {
        "product_version": manifest["product_version"],
        "release_checksums_valid": True,
    }


def test_successful_rebuild_activates_clean_root_and_retains_old_root(
    tmp_path: Path,
) -> None:
    root = _source_root(tmp_path)
    database = root / "shared/database/learner_runtime.sqlite3"
    before = rebuild.learner_database_projection(database)
    messages: list[str] = []

    result = rebuild.rebuild_and_activate(
        product_root=root,
        code_root=Path(__file__).resolve().parents[2],
        reporter=messages.append,
        upgrade_action=_fake_upgrade,
        final_validator=_fake_validator,
    )

    assert result["validation_status"] == rebuild.PASS_STATUS
    assert result["current_version"] == "1.2.1"
    assert rebuild.r01._current_version(root) == "1.2.1"
    backup = Path(result["activation"]["previous_product_backup_root"])
    assert backup.is_dir()
    assert rebuild.r01._current_version(backup) == "1.1.1"
    assert rebuild.learner_database_projection(
        root / "shared/database/learner_runtime.sqlite3"
    ) == before
    assert result["learner_owned_database_state_preserved"] is True
    assert result["canonical_learner_state_preserved"] is True
    assert result["in_place_upgrade_used"] is False
    assert result["active_root_mutated_before_acceptance"] is False
    assert result["old_product_retained"] is True
    assert not list(root.rglob("__pycache__"))
    assert not list(root.rglob("*.pyc"))
    assert any(message.startswith("REBUILD_PHASE") for message in messages)
    assert messages[-1] == "REBUILD_COMPLETE current_version=1.2.1"


def test_failed_rebuild_never_exchanges_active_root(tmp_path: Path) -> None:
    root = _source_root(tmp_path)
    original_manifest = rebuild.r01.file_digest(
        root / "releases/1.1.1/release_manifest.json"
    )

    def fail_upgrade(**_kwargs: Any) -> Mapping[str, Any]:
        raise RuntimeError("injected_rebuild_failure")

    with pytest.raises(RuntimeError, match="injected_rebuild_failure"):
        rebuild.rebuild_and_activate(
            product_root=root,
            code_root=Path(__file__).resolve().parents[2],
            upgrade_action=fail_upgrade,
            final_validator=_fake_validator,
        )

    assert root.is_dir()
    assert rebuild.r01._current_version(root) == "1.1.1"
    assert rebuild.r01.file_digest(
        root / "releases/1.1.1/release_manifest.json"
    ) == original_manifest
    assert not list(root.parent.glob(f"{root.name}.pre_rebuild_*"))
    pending = rebuild._prepare_paths(root)["pending"]
    assert pending.is_dir()


def test_learner_owned_state_drift_blocks_directory_exchange(tmp_path: Path) -> None:
    root = _source_root(tmp_path)

    def drifting_upgrade(**kwargs: Any) -> Mapping[str, Any]:
        result = dict(_fake_upgrade(**kwargs))
        database = Path(kwargs["product_root"]) / "shared/database/learner_runtime.sqlite3"
        import sqlite3

        with sqlite3.connect(database) as connection:
            row = connection.execute(
                "SELECT learner_id FROM learner_profiles ORDER BY learner_id LIMIT 1"
            ).fetchone()
            assert row
            connection.execute(
                "UPDATE learner_profiles SET profile_state='SUSPENDED' WHERE learner_id=?",
                (str(row[0]),),
            )
            connection.commit()
        return result

    with pytest.raises(
        rebuild.SideBySideRebuildError,
        match="LEARNER_OWNED_DATABASE_STATE_CHANGED_DURING_REBUILD",
    ):
        rebuild.rebuild_and_activate(
            product_root=root,
            code_root=Path(__file__).resolve().parents[2],
            upgrade_action=drifting_upgrade,
            final_validator=_fake_validator,
        )

    assert root.is_dir()
    assert rebuild.r01._current_version(root) == "1.1.1"
    assert not list(root.parent.glob(f"{root.name}.pre_rebuild_*"))


def test_plan_declares_non_in_place_boundary(tmp_path: Path) -> None:
    root = _source_root(tmp_path)
    plan = rebuild.build_plan(
        product_root=root,
        code_root=Path(__file__).resolve().parents[2],
    )
    assert plan["validation_status"] == rebuild.PLAN_STATUS
    assert plan["mode"] == "SIDE_BY_SIDE_REBUILD"
    assert plan["in_place_upgrade_used"] is False
    assert plan["active_root_mutated_before_acceptance"] is False
    assert plan["old_root_retained_after_activation"] is True
    assert plan["bytecode_writes_disabled"] is True


def test_operator_entry_disables_bytecode_and_has_no_powershell() -> None:
    repository = Path(__file__).resolve().parents[2]
    script = repository / "scripts/REBUILD_A1FS.py"
    text = script.read_text(encoding="utf-8")
    lowered = text.casefold()
    assert "PYTHONDONTWRITEBYTECODE" in text
    assert "sys.dont_write_bytecode = True" in text
    assert "build_a1fs_ops_v1_upg02_side_by_side_rebuild_atomic_activation" in text
    assert ".ps1" not in lowered
    assert "powershell" not in lowered
