from __future__ import annotations

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


def test_v100_prerequisite_chain_reaches_v111_without_shared_state_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _, _ = legacy.product_root(tmp_path)
    before = legacy.core.shared_identity(root)
    _use_fixture_acceptance(monkeypatch)

    result = chain.upgrade_prerequisites(
        product_root=root,
        code_root=_minimal_code_root(tmp_path),
        output_root=tmp_path / "upgrade-output",
    )

    assert result["initial_version"] == "1.0.0"
    assert result["prerequisite_final_version"] == "1.1.1"
    assert result["direct_version_file_edit_used"] is False
    assert [step["target_version"] for step in result["steps"]] == [
        "1.1.0",
        "1.1.1",
    ]
    assert all(step["atomic_update_channel_reused"] for step in result["steps"])
    assert chain._current_version(root) == "1.1.1"
    assert legacy.core.shared_identity(root) == before
    assert (root / "releases/1.1.0/release_manifest.json").is_file()
    assert (root / "releases/1.1.1/release_manifest.json").is_file()


def test_v110_prerequisite_chain_only_runs_exact_sequence_step(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _use_fixture_acceptance(monkeypatch)
    root, _, _ = legacy.product_root(tmp_path)
    code_root = _minimal_code_root(tmp_path)
    first = chain.upgrade_prerequisites(
        product_root=root,
        code_root=code_root,
        output_root=tmp_path / "first",
    )
    assert first["prerequisite_final_version"] == "1.1.1"
    legacy.r01.rollback(product_root=root, version="1.1.0")

    second = chain.upgrade_prerequisites(
        product_root=root,
        code_root=code_root,
        output_root=tmp_path / "second",
    )
    assert second["initial_version"] == "1.1.0"
    assert [step["target_version"] for step in second["steps"]] == ["1.1.1"]
    assert chain._current_version(root) == "1.1.1"


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
