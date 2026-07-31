from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from ulga.builders import (
    build_a1fs_ops_v1_unit01_real62_postmerge_disposable_full_product_integration_acceptance
    as builder,
)
from ulga.builders import (
    build_a1fs_v1_razq01f_fullfix_real62_semantic_lexical_anchor_fallback
    as razq01f,
)
from ulga.validators import (
    validate_a1fs_ops_v1_unit01_real62_postmerge_disposable_full_product_integration_acceptance
    as validator,
)


def load_fixture():
    path = Path(__file__).with_name(
        "test_a1fs_v1_razq01f_unit01_multisession_reconciliation_ci.py"
    )
    spec = importlib.util.spec_from_file_location("_razq01f_fixture", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_s05_fixture():
    path = (
        Path(__file__).resolve().parents[1]
        / "ulga"
        / "_a1fs_online_v1_2_u01e_s05_release_migration_acceptance_core.py"
    )
    spec = importlib.util.spec_from_file_location("_s05_fixture", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_v121_product(tmp_path: Path, fixture) -> Path:
    from ulga.builders import (
        build_a1fs_ops_v1_upg02_side_by_side_rebuild_atomic_activation as upg02,
    )

    s05_fixture = load_s05_fixture()
    root = s05_fixture.source_v111_root(tmp_path / "source-product")
    source = root / "releases/1.1.1"
    target = root / "releases/1.2.1"
    upg02._copy_clean_tree(source, target)

    def rewrite(value):
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
    manifest["release_id"] = "TEST-REAL62-DISPOSABLE-1.2.1"
    upg02.r01.write_json(manifest_path, manifest)
    version_path = target / "VERSION.json"
    version = json.loads(version_path.read_text(encoding="utf-8"))
    version["product_version"] = "1.2.1"
    upg02.r01.write_json(version_path, version)
    (target / "checksums.json").unlink(missing_ok=True)
    upg02.r01._write_checksums(target)
    upg02.r01.validate_release(target)
    upg02.r01._atomic_text(root / "current_version.txt", "1.2.1\n")

    database = root / "shared/database/learner_runtime.sqlite3"
    database.unlink(missing_ok=True)
    fixture.setup_database(database)
    return root


def test_real62_integrates_into_disposable_full_product_without_source_mutation(
    tmp_path: Path,
) -> None:
    fixture = load_fixture()
    source_root = make_v121_product(tmp_path, fixture)
    disposable_root = tmp_path / "disposable-product"
    evidence_database = tmp_path / "evidence.sqlite3"
    multisession_root = tmp_path / "multisession-evidence"
    fixture.setup_database(evidence_database)
    approved = fixture.approved_real44()
    razq01f.install_fullfix()
    source_evidence = razq01f.run_acceptance(
        database=evidence_database,
        approved_content=approved,
        learner_id="learner-razq01f-ci",
        output_root=multisession_root,
        session_prefix="session-razq01f-ci",
    )
    assert source_evidence["status"] == razq01f.PASS_STATUS

    source_before = builder._product_identity(source_root)
    report = builder.integrate_disposable_product(
        source_product_root=source_root,
        disposable_product_root=disposable_root,
        approved_content=approved,
        multisession_root=multisession_root,
        learner_id="learner-razq01f-ci",
        release_session_id="real62-disposable-release-session",
    )
    result = validator.validate(
        source_product_root=source_root,
        disposable_product_root=disposable_root,
        approved_content=approved,
        multisession_root=multisession_root,
    )

    assert report["status"] == builder.PASS_STATUS
    assert report["source_product_root_unchanged"] is True
    assert report["disposable_copy_validated"] is True
    assert report["activation_simulation_pass"] is True
    assert report["rollback_simulation_pass"] is True
    assert report["base_runtime_item_count"] == 288
    assert report["extension_item_count"] == 186
    assert report["combined_runtime_item_count"] == 474
    assert report["idempotent_materialization_reused"] is True
    assert report["http_canary"]["attempt_outcome"] == "AUTO_PASS"
    assert report["post_canary_exposure_count"] == 1
    assert report["post_canary_attempt_count"] == 1
    assert report["formal_production_activation_approved"] is False
    assert report["production_root_mutated"] is False
    assert builder._product_identity(source_root) == source_before
    assert result["validation_status"] == validator.PASS_STATUS
    assert result["error_count"] == 0, result["errors"]

    report_path = disposable_root / "shared/reports" / builder.REPORT_NAME
    tampered = json.loads(report_path.read_text(encoding="utf-8"))
    tampered["combined_runtime_item_count"] = 475
    report_path.write_text(
        json.dumps(tampered, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    failed = validator.validate(
        source_product_root=source_root,
        disposable_product_root=disposable_root,
        approved_content=approved,
        multisession_root=multisession_root,
    )
    assert failed["validation_status"] == validator.FAIL_STATUS
    assert failed["error_count"] == 1
    assert "readback_digest_invalid" in failed["errors"][0]
