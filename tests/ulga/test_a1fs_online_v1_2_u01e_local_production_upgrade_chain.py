from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from tests.ulga import test_a1fs_v1_1_m02_unit01_local_product_acceptance_release as legacy
from ulga.builders import (
    build_a1fs_online_v1_2_u01e_local_production_upgrade_chain as chain,
)


def _minimal_code_root(tmp_path: Path) -> Path:
    root = tmp_path / "code"
    (root / "ulga").mkdir(parents=True)
    (root / "ulga/__init__.py").write_text("\n", encoding="utf-8")
    return root


def _use_fixture_acceptance(monkeypatch: pytest.MonkeyPatch) -> None:
    original = chain.v110.materialize

    def materialize_with_fixture_acceptance(**kwargs):
        return original(**kwargs, acceptance_runner=legacy.fake_acceptance)

    monkeypatch.setattr(chain.v110, "materialize", materialize_with_fixture_acceptance)


def _add_deep_m7_m8_state(root: Path) -> None:
    canary = (
        root
        / "shared/learner_state/canonical_learning_state"
        / "A1FS_ONLINE_V1_S15_SCORED_JOURNEY_CANARY"
    )
    m7 = canary / "m7/a1fs_v1_m7_mastery_snapshot.private.json"
    m8 = canary / "m8/a1fs_v1_m8_retention_snapshot.private.json"
    m7.parent.mkdir(parents=True, exist_ok=True)
    m8.parent.mkdir(parents=True, exist_ok=True)
    m7.write_text('{"status":"m7-preserved"}\n', encoding="utf-8")
    m8.write_text('{"status":"m8-preserved"}\n', encoding="utf-8")


def _write_sqlite(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE payload(value TEXT NOT NULL)")
        connection.execute("INSERT INTO payload(value) VALUES(?)", (value,))
        connection.commit()


def _read_sqlite(path: Path) -> str:
    with sqlite3.connect(path) as connection:
        return str(connection.execute("SELECT value FROM payload").fetchone()[0])


def test_v100_prerequisite_chain_reaches_v111_without_shared_state_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _, _ = legacy.product_root(tmp_path)
    _add_deep_m7_m8_state(root)
    before = legacy.core.shared_identity(root)
    _use_fixture_acceptance(monkeypatch)
    output_root = tmp_path / (
        "A1FS_V1_2_U01E_OPERATOR_RUN_WITH_A_DELIBERATELY_LONG_OUTPUT_NAME"
    )

    result = chain.upgrade_prerequisites(
        product_root=root,
        code_root=_minimal_code_root(tmp_path),
        output_root=output_root,
    )

    assert result["initial_version"] == "1.0.0"
    assert result["prerequisite_final_version"] == "1.1.1"
    assert result["direct_version_file_edit_used"] is False
    assert result["short_work_root_used"] is True
    assert result["temporary_work_root_retained"] is False
    assert result["v12_runtime_imported_during_prerequisites"] is False
    assert result["windows_sqlite_copy_mode"] == (
        "DIRECT_NEW_TARGET_VALIDATED_RETRY_EXISTING_TARGET"
    )
    assert [step["target_version"] for step in result["steps"]] == [
        "1.1.0",
        "1.1.1",
    ]
    assert all(step["atomic_update_channel_reused"] for step in result["steps"])
    assert chain._current_version(root) == "1.1.1"
    assert legacy.core.shared_identity(root) == before
    assert (root / "releases/1.1.0/release_manifest.json").is_file()
    assert (root / "releases/1.1.1/release_manifest.json").is_file()
    assert (output_root / "prerequisites/v1_1_0/m02.safe.json").is_file()
    assert (output_root / "prerequisites/v1_1_1/m02f.safe.json").is_file()
    assert not chain._short_work_root(root, "PRE").exists()


def test_v110_prerequisite_chain_only_runs_exact_sequence_step(tmp_path: Path) -> None:
    root = legacy.installed_v110_root(tmp_path)
    before = legacy.core.shared_identity(root)

    result = chain.upgrade_prerequisites(
        product_root=root,
        code_root=_minimal_code_root(tmp_path),
        output_root=tmp_path / "upgrade-output",
    )

    assert result["initial_version"] == "1.1.0"
    assert result["prerequisite_final_version"] == "1.1.1"
    assert result["v12_runtime_imported_during_prerequisites"] is False
    assert [step["target_version"] for step in result["steps"]] == ["1.1.1"]
    assert chain._current_version(root) == "1.1.1"
    assert legacy.core.shared_identity(root) == before
    assert not chain._short_work_root(root, "PRE").exists()


def test_new_acceptance_sqlite_copy_does_not_require_os_replace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source.sqlite3"
    target = tmp_path / "acceptance/shared/database/learner_runtime.sqlite3"
    _write_sqlite(source, "source-value")
    replace_calls = 0

    def forbidden_replace(*_args, **_kwargs):
        nonlocal replace_calls
        replace_calls += 1
        raise PermissionError(5, "simulated Windows rename lock")

    monkeypatch.setattr(chain.os, "replace", forbidden_replace)
    chain._windows_safe_copy_sqlite(source, target)

    assert replace_calls == 0
    assert _read_sqlite(target) == "source-value"
    assert not target.with_suffix(target.suffix + ".u01e-copying").exists()


def test_existing_sqlite_replace_retries_transient_windows_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source.sqlite3"
    target = tmp_path / "target.sqlite3"
    _write_sqlite(source, "new-value")
    _write_sqlite(target, "old-value")
    actual_replace = chain.os.replace
    attempts = 0

    def flaky_replace(source_path, target_path):
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise PermissionError(5, "simulated transient Windows file lock")
        actual_replace(source_path, target_path)

    monkeypatch.setattr(chain.os, "replace", flaky_replace)
    monkeypatch.setattr(chain.time, "sleep", lambda _seconds: None)
    chain._windows_safe_copy_sqlite(source, target)

    assert attempts == 3
    assert _read_sqlite(target) == "new-value"
    assert not target.with_suffix(target.suffix + ".u01e-copying").exists()


def test_short_work_root_is_sibling_not_requested_output_descendant(
    tmp_path: Path,
) -> None:
    root, _, _ = legacy.product_root(tmp_path)
    long_output = tmp_path / "nested" / "operator" / "output" / ("x" * 100)
    work = chain._short_work_root(root, "PRE")
    assert work.parent == root.parent
    assert work.name.startswith(".A1FS_U12_PRE_")
    assert not work.is_relative_to(root)
    assert not work.is_relative_to(long_output)
    assert len(str(work)) < len(str(long_output))


def test_fresh_upgrade_chain_import_does_not_patch_v11_bootstrap() -> None:
    repository = Path(__file__).resolve().parents[2]
    script = "\n".join(
        [
            "from ulga.builders import build_a1fs_online_v1_s14_learner_facing_curriculum_progress_semantics as s14",
            "before = s14._decorate_bootstrap",
            "from ulga.builders import build_a1fs_online_v1_2_u01e_local_production_upgrade_chain as chain",
            "assert s14._decorate_bootstrap is before",
            "assert 'operator' not in chain.__dict__",
            "assert chain.r01._copy_sqlite is not chain._windows_safe_copy_sqlite",
        ]
    )
    subprocess.run(
        [sys.executable, "-c", script],
        cwd=repository,
        check=True,
    )


def test_unsupported_source_version_fails_closed(tmp_path: Path) -> None:
    root, _, _ = legacy.product_root(tmp_path)
    (root / "current_version.txt").write_text("0.9.0\n", encoding="ascii")
    with pytest.raises(chain.UpgradeChainError, match="SUPPORTED_SOURCE_VERSION_REQUIRED"):
        chain.upgrade_prerequisites(
            product_root=root,
            code_root=_minimal_code_root(tmp_path),
            output_root=tmp_path / "out",
        )


def test_operator_script_declares_full_supported_version_chain() -> None:
    repository = Path(__file__).resolve().parents[2]
    script = repository / "scripts/INSTALL_AND_ACCEPT_A1FS_V1_2_U01E.ps1"
    text = script.read_text(encoding="utf-8")
    assert '@("1.0.0", "1.1.0", "1.1.1", "1.2.0")' in text
    assert "build_a1fs_online_v1_2_u01e_local_production_upgrade_chain" in text
    assert "SOURCE_VERSION=$CurrentVersion" in text
    assert "Set-Content" not in text
