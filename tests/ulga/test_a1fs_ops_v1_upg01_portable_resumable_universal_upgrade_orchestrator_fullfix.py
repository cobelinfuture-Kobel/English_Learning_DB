from __future__ import annotations

import json
from pathlib import Path

import pytest

from ulga.builders import (
    build_a1fs_ops_v1_upg01_portable_resumable_universal_upgrade_orchestrator_fullfix as upg,
)


def _code_root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "ulga" / "builders").mkdir(parents=True)
    (root / "scripts").mkdir()
    return root


def _manifest(root: Path, version: str) -> None:
    release = root / "releases" / version
    release.mkdir(parents=True, exist_ok=True)
    (release / "release_manifest.json").write_text(
        json.dumps(
            {
                "program_id": "A1FS-ONLINE-V1",
                "release_id": f"TEST-{version}",
                "product_version": version,
            }
        ),
        encoding="utf-8",
    )


def _product_root(tmp_path: Path, version: str = "1.1.1") -> Path:
    root = tmp_path / "A1FS_V1"
    (root / "shared").mkdir(parents=True)
    (root / "current_version.txt").write_text(version + "\n", encoding="ascii")
    for release_version in upg.VERSION_ORDER:
        if upg._version_index(release_version) <= upg._version_index(version):
            _manifest(root, release_version)
    return root


def _outside_paths(tmp_path: Path) -> tuple[Path, Path]:
    return tmp_path / "upgrade-output", tmp_path / "upgrade-state" / "journal.json"


def _patch_apply_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(upg, "_missing_environment", lambda: [])
    monkeypatch.setattr(
        upg,
        "_runtime_state",
        lambda _root: {"pid_file_present": False, "pid": None, "pid_alive": False},
    )
    monkeypatch.setattr(
        upg,
        "_stop_runtime_if_needed",
        lambda _root, _port: {"action": "NO_RUNTIME_PID"},
    )
    monkeypatch.setattr(upg, "_acceptance_fingerprint", lambda **_kwargs: "stable")


def test_registry_builds_complete_supported_route() -> None:
    assert [spec.target_version for spec in upg.build_route("1.1.1", "1.2.1")] == [
        "1.2.0",
        "1.2.1",
    ]
    assert [spec.target_version for spec in upg.build_route("1.2.0", "1.2.1")] == [
        "1.2.1"
    ]
    assert upg.build_route("1.2.1", "1.2.1") == []
    with pytest.raises(upg.UpgradeOrchestratorError, match="TARGET_BEHIND_CURRENT"):
        upg.build_route("1.2.1", "1.2.0")


def test_plan_only_auto_contract_is_read_only(tmp_path: Path) -> None:
    code = _code_root(tmp_path)
    product = _product_root(tmp_path)
    output, journal = _outside_paths(tmp_path)
    before = sorted(str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*"))

    plan = upg.build_plan(
        code_root=code,
        product_root=product,
        output_root=output,
        journal_path=journal,
        target_version="latest",
    )

    after = sorted(str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*"))
    assert before == after
    assert plan["validation_status"] == upg.PLAN_PASS_STATUS
    assert plan["current_version"] == "1.1.1"
    assert plan["target_version"] == "1.2.1"
    assert [row["target_version"] for row in plan["migration_route"]] == [
        "1.2.0",
        "1.2.1",
    ]
    assert plan["plan_only_mutation_count"] == 0
    assert not output.exists()
    assert not journal.exists()


def test_upgrade_resumes_from_actual_version_and_is_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    code = _code_root(tmp_path)
    product = _product_root(tmp_path)
    output, journal = _outside_paths(tmp_path)
    _patch_apply_runtime(monkeypatch)
    calls: list[str] = []

    def migrate(spec: upg.MigrationSpec, **kwargs):
        del kwargs
        calls.append(spec.target_version)
        _manifest(product, spec.target_version)
        (product / "current_version.txt").write_text(
            spec.target_version + "\n", encoding="ascii"
        )
        return {"validation_status": "PASS_DELEGATED"}

    acceptance_calls: list[str] = []
    monkeypatch.setattr(upg, "_execute_migration", migrate)
    monkeypatch.setattr(
        upg,
        "_run_acceptance",
        lambda spec, **_kwargs: acceptance_calls.append(spec.target_version)
        or {"validation_status": "PASS_ACCEPTANCE"},
    )

    first = upg.upgrade(
        code_root=code,
        product_root=product,
        output_root=output,
        journal_path=journal,
    )
    assert calls == ["1.2.0", "1.2.1"]
    assert acceptance_calls == ["1.2.1", "1.2.1"]
    assert first["source_version"] == "1.1.1"
    assert first["current_version"] == "1.2.1"
    assert first["idempotent_acceptance"]["pass"] is True

    calls.clear()
    acceptance_calls.clear()
    second = upg.upgrade(
        code_root=code,
        product_root=product,
        output_root=output,
        journal_path=journal,
    )
    assert calls == []
    assert acceptance_calls == ["1.2.1", "1.2.1"]
    assert second["source_version"] == "1.2.1"
    assert second["current_version"] == "1.2.1"
    assert second["resumed"] is True


def test_interrupted_journal_resumes_only_remaining_step(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    code = _code_root(tmp_path)
    product = _product_root(tmp_path, version="1.2.0")
    output, journal = _outside_paths(tmp_path)
    _patch_apply_runtime(monkeypatch)
    plan = upg.build_plan(
        code_root=code,
        product_root=product,
        output_root=output,
        journal_path=journal,
    )
    journal.parent.mkdir(parents=True)
    journal.write_text(
        json.dumps(
            {
                "task_id": upg.TASK_ID,
                "program_id": upg.PROGRAM_ID,
                "schema_version": upg.SCHEMA_VERSION,
                "status": "RUNNING",
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
                "product_lineage_identity": plan["product_lineage_identity"],
                "product_root": str(product),
                "initial_version": "1.1.1",
                "current_version": "1.2.0",
                "target_version": "1.2.1",
                "completed_steps": [
                    {
                        "step_id": "A1FS_OPS_UPGRADE_TO_1_2_0",
                        "target_version": "1.2.0",
                        "status": "PASS",
                    }
                ],
                "active_step": "A1FS_OPS_UPGRADE_TO_1_2_1",
                "attempt_count": 1,
                "resume_count": 0,
            }
        ),
        encoding="utf-8",
    )
    calls: list[str] = []

    def migrate(spec: upg.MigrationSpec, **kwargs):
        del kwargs
        calls.append(spec.target_version)
        _manifest(product, spec.target_version)
        (product / "current_version.txt").write_text(
            spec.target_version + "\n", encoding="ascii"
        )
        return {"validation_status": "PASS"}

    monkeypatch.setattr(upg, "_execute_migration", migrate)
    monkeypatch.setattr(
        upg, "_run_acceptance", lambda _spec, **_kwargs: {"validation_status": "PASS"}
    )

    result = upg.upgrade(
        code_root=code,
        product_root=product,
        output_root=output,
        journal_path=journal,
    )
    assert calls == ["1.2.1"]
    assert result["source_version"] == "1.1.1"
    assert result["resumed"] is True
    assert result["resume_count"] == 1


def test_failed_migration_rolls_back_to_starting_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    code = _code_root(tmp_path)
    product = _product_root(tmp_path)
    output, journal = _outside_paths(tmp_path)
    _patch_apply_runtime(monkeypatch)

    def fail_after_switch(spec: upg.MigrationSpec, **kwargs):
        del kwargs
        _manifest(product, spec.target_version)
        (product / "current_version.txt").write_text(
            spec.target_version + "\n", encoding="ascii"
        )
        raise RuntimeError("simulated interruption")

    def rollback(**kwargs):
        initial = kwargs["initial_version"]
        (product / "current_version.txt").write_text(initial + "\n", encoding="ascii")
        return {
            "validation_status": upg.ROLLBACK_STATUS,
            "rollback_version": initial,
        }

    monkeypatch.setattr(upg, "_execute_migration", fail_after_switch)
    monkeypatch.setattr(upg, "_rollback", rollback)

    with pytest.raises(
        upg.UpgradeOrchestratorError,
        match="UPGRADE_FAILED_AUTOMATIC_ROLLBACK_PASS",
    ):
        upg.upgrade(
            code_root=code,
            product_root=product,
            output_root=output,
            journal_path=journal,
        )

    assert (
        product / "current_version.txt"
    ).read_text(encoding="ascii").strip() == "1.1.1"
    value = json.loads(journal.read_text(encoding="utf-8"))
    assert value["status"] == "ROLLED_BACK"
    assert value["rollback"]["validation_status"] == upg.ROLLBACK_STATUS


def test_single_powershell_entry_is_portable() -> None:
    repository = Path(__file__).resolve().parents[2]
    script = repository / "scripts" / "UPGRADE_A1FS.ps1"
    text = script.read_text(encoding="utf-8")
    assert "[switch]$PlanOnly" in text
    assert "build_a1fs_ops_v1_upg01_portable_resumable" in text
    assert "A1FS_PRODUCT_ROOT" not in text
    assert "G:\\HomeWork" not in text
    assert "C:\\Users" not in text
    assert "INSTALL_AND_ACCEPT_A1FS_V1_2" not in text
