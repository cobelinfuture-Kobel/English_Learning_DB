from __future__ import annotations

import json
import shutil
from pathlib import Path

from tests.ulga import (
    _a1fs_online_v1_2_u01e_s05_release_migration_acceptance_core as s05_fixture,
)
from ulga.builders import (
    build_a1fs_ops_v1_upg01_release_residual_reconciliation_fullfix as fix,
)


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    root = s05_fixture.source_v111_root(tmp_path / "product")
    source = fix.s05.source_product(root)
    overlay = fix.s05.build_runtime_overlay(source)
    candidate, _ = fix.s05.build_candidate_release(
        source=source,
        overlay=overlay,
        package_root=tmp_path / "package",
        code_root=Path(__file__).resolve().parents[2],
    )
    return root, candidate


def test_valid_inactive_release_and_stale_backup_are_reactivated_safely(
    tmp_path: Path,
) -> None:
    root, candidate = _fixture(tmp_path)
    first = fix._BASE_INSTALL_CANDIDATE(
        product_root=root,
        candidate=candidate,
        version="1.2.0",
    )
    target = root / "releases/1.2.0"
    target_identity = fix.release_resume_identity(target)
    shared_before = fix.r01.file_digest(
        root / "shared/database/learner_runtime.sqlite3"
    )
    fix.r01.rollback(product_root=root, version="1.1.1")
    stale_staging = root / "staging/1.2.0.pending"
    shutil.copytree(candidate, stale_staging)

    result = fix.resumable_install_candidate(
        product_root=root,
        candidate=candidate,
        version="1.2.0",
    )

    assert first["status"] == "PASS_ATOMIC_UPDATE_ACTIVATED"
    assert result["status"] == "PASS_ATOMIC_UPDATE_REACTIVATED_VALID_EXISTING_RELEASE"
    assert fix.r01._current_version(root) == "1.2.0"
    assert fix.release_resume_identity(target) == target_identity
    assert fix.r01.file_digest(
        root / "shared/database/learner_runtime.sqlite3"
    ) == shared_before
    reconciliation = result["upg01_release_residual_reconciliation"]
    assert reconciliation["existing_release_reused"] is True
    assert reconciliation["release_identity_match"] is True
    assert reconciliation["staging_quarantined"]
    assert reconciliation["stale_backup_quarantined"]
    assert reconciliation["fresh_backup_created"] is True
    assert Path(result["backup_root"]).is_dir()


def test_mismatched_inactive_release_is_quarantined_then_reinstalled(
    tmp_path: Path,
) -> None:
    root, candidate = _fixture(tmp_path)
    fix._BASE_INSTALL_CANDIDATE(
        product_root=root,
        candidate=candidate,
        version="1.2.0",
    )
    fix.r01.rollback(product_root=root, version="1.1.1")

    changed = tmp_path / "changed/1.2.0"
    shutil.copytree(candidate, changed)
    sequence_path = changed / "runtime/sequence.json"
    sequence = json.loads(sequence_path.read_text(encoding="utf-8"))
    sequence["UPG01_RESUME_TEST_ONLY"] = 999
    fix.r01.write_json(sequence_path, sequence)
    (changed / "checksums.json").unlink()
    fix.r01._write_checksums(changed)
    fix.r01.validate_release(changed)
    changed_identity = fix.release_resume_identity(changed)

    result = fix.resumable_install_candidate(
        product_root=root,
        candidate=changed,
        version="1.2.0",
    )

    assert result["status"] == "PASS_ATOMIC_UPDATE_ACTIVATED"
    assert fix.r01._current_version(root) == "1.2.0"
    assert fix.release_resume_identity(root / "releases/1.2.0") == changed_identity
    reconciliation = result["upg01_release_residual_reconciliation"]
    assert reconciliation["existing_release_reused"] is False
    assert reconciliation["release_identity_match"] is False
    assert reconciliation["existing_release_quarantined"]
    assert Path(reconciliation["existing_release_quarantined"]).is_dir()
    assert reconciliation["stale_backup_quarantined"]


def test_active_release_is_never_replaced(tmp_path: Path) -> None:
    root, candidate = _fixture(tmp_path)
    fix._BASE_INSTALL_CANDIDATE(
        product_root=root,
        candidate=candidate,
        version="1.2.0",
    )
    before = fix.release_resume_identity(root / "releases/1.2.0")

    result = fix.resumable_install_candidate(
        product_root=root,
        candidate=candidate,
        version="1.2.0",
    )

    assert result["status"] == "PASS_TARGET_RELEASE_ALREADY_ACTIVE"
    assert fix.release_resume_identity(root / "releases/1.2.0") == before
    assert result["upg01_release_residual_reconciliation"][
        "existing_release_quarantined"
    ] is None


def test_activation_patches_shared_r01_installer_and_entry_metadata() -> None:
    fix.activate()
    assert fix.r01.install_candidate is fix.resumable_install_candidate
    plan = fix._entry_metadata({"validation_status": fix.PLAN_PASS_STATUS})
    compatibility = plan["residual_u01e_contract_compatibility"]
    assert compatibility["inactive_release_resume_enabled"] is True
    assert compatibility["stale_staging_reconciliation_enabled"] is True
    assert compatibility["stale_backup_reconciliation_enabled"] is True
    assert compatibility["active_release_replacement_allowed"] is False
    assert compatibility["shared_state_deletion_allowed"] is False


def test_operator_script_routes_to_release_residual_reconciliation() -> None:
    script = Path(__file__).resolve().parents[2] / "scripts/UPGRADE_A1FS.py"
    text = script.read_text(encoding="utf-8")
    assert "build_a1fs_ops_v1_upg01_release_residual_reconciliation_fullfix" in text
    lowered = text.casefold()
    assert ".ps1" not in lowered
    assert "powershell" not in lowered
