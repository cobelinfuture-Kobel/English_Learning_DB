from __future__ import annotations

import importlib.util
from pathlib import Path

from ulga.builders import (
    build_a1fs_ops_v1_unit01_real62_postmerge_disposable_full_product_integration_acceptance
    as integration,
)
from ulga.builders import (
    build_a1fs_ops_v1_unit01_student_package_local_private_materialization_operator_readback
    as builder,
)
from ulga.builders import (
    build_a1fs_v1_razq01f_fullfix_real62_semantic_lexical_anchor_fallback
    as razq01f,
)
from ulga.validators import (
    validate_a1fs_ops_v1_unit01_student_package_local_private_materialization_operator_readback
    as validator,
)


def load_previous_test():
    path = Path(__file__).with_name(
        "test_a1fs_ops_v1_unit01_real62_disposable_full_product_integration_ci.py"
    )
    spec = importlib.util.spec_from_file_location("_operator_fixture", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_unit01_local_operator_uses_real_v121_runtime_and_safe_readback(
    tmp_path: Path,
) -> None:
    previous = load_previous_test()
    fixture = previous.load_fixture()
    source_root = previous.make_v121_product(tmp_path, fixture)
    product_root = tmp_path / "disposable-product"
    evidence_database = tmp_path / "evidence.sqlite3"
    multisession_root = tmp_path / "multisession-evidence"
    fixture.setup_database(evidence_database)
    approved = fixture.approved_real44()
    learner_id = "learner-razq01f-ci"

    razq01f.install_fullfix()
    evidence = razq01f.run_acceptance(
        database=evidence_database,
        approved_content=approved,
        learner_id=learner_id,
        output_root=multisession_root,
        session_prefix="session-razq01f-ci",
    )
    assert evidence["status"] == razq01f.PASS_STATUS
    integrated = integration.integrate_disposable_product(
        source_product_root=source_root,
        disposable_product_root=product_root,
        approved_content=approved,
        multisession_root=multisession_root,
        learner_id=learner_id,
        release_session_id="session-razq01g-release-ci",
    )
    assert integrated["status"] == integration.PASS_STATUS

    auth_path = product_root / "shared/auth/auth_state.sqlite3"
    username = "operator-ci"
    password = "operator-ci-password"
    config = (
        builder.v121.v12._core.s17.s16.s15.s13.PersistentBoundaryConfig.from_values(
            username=username,
            password=password,
            session_secret="operator-ci-session-signing-secret-2026-safe-only",
            mode="local",
            allowed_origin="http://127.0.0.1",
            allowed_host="127.0.0.1",
            revocation_db_path=auth_path,
            port=0,
        )
    )
    chromium = builder.entry_builder.discover_chromium()
    report = builder.materialize_and_accept(
        product_root=product_root,
        approved_content=approved,
        chromium_path=chromium,
        config=config,
        credentials={"username": username, "password": password},
    )
    result = validator.validate(
        product_root=product_root,
        approved_content=approved,
    )

    assert report["status"] == builder.PASS_STATUS
    assert report["product_version"] == "1.2.1"
    assert report["runtime_item_count"] == 474
    assert report["entry_acceptance_status"] == builder.entry_builder.PASS_STATUS
    assert report["entry_validation_status"] == builder.entry_validator.PASS_STATUS
    assert report["runtime_http_readback"]["unit_count"] == 24
    assert report["runtime_http_readback"]["product_version"] == "1.2.1"
    assert report["runtime_http_readback"][
        "unauthenticated_prelearning_status"
    ] == 401
    assert report["runtime_http_readback"][
        "authenticated_bootstrap_status"
    ] == 200
    assert report["runtime_http_readback"][
        "authenticated_progress_status"
    ] == 200
    assert report["runtime_http_readback"][
        "authenticated_prelearning_status"
    ] == 200
    assert report["runtime_http_readback"][
        "authenticated_questionbank_status"
    ] == 200
    assert report["real_v121_application_used"] is True
    assert report["real_learner_database_used"] is True
    assert report["existing_auth_boundary_reused"] is True
    assert report["existing_progress_api_reused"] is True
    assert report["existing_question_bank_reused"] is True
    assert report["secrets_serialized"] is False
    assert report["absolute_local_paths_serialized"] is False
    assert report["second_question_bank_created"] is False
    assert report["formal_production_activation_approved"] is False
    assert report["production_root_mutated"] is False
    assert report["public_delivery"] is False
    assert report["unit02_to_unit24_modified"] is False
    assert report["a2_unlocked"] is False

    assert result["validation_status"] == validator.PASS_STATUS, result["errors"]
    assert result["error_count"] == 0, result["errors"]
    assert result["runtime_item_count"] == 474
    assert result["unit_count"] == 24
    assert result["authenticated_route_count"] == 4
    assert result["relative_artifact_count"] == 5
    assert result["entry_validation_error_count"] == 0

    safe_report = product_root / "shared/reports" / builder.REPORT_NAME
    text = safe_report.read_text(encoding="utf-8")
    assert str(product_root) not in text
    assert password not in text
    assert "session-signing-secret" not in text
    assert "A1FS_S11_AUTH_PASSWORD" not in text

    # A digest-valid report containing a secret-like key still fails the
    # independent safe-readback scan.
    tampered = builder.entry_builder.load(safe_report)
    tampered["password"] = "forbidden"
    core = {
        key: value
        for key, value in tampered.items()
        if key != "readback_sha256"
    }
    tampered["readback_sha256"] = builder.entry_builder.digest(core)
    builder.entry_builder.atomic_json(safe_report, tampered)
    failed = validator.validate(
        product_root=product_root,
        approved_content=approved,
    )
    assert failed["validation_status"] == validator.FAIL_STATUS
    assert failed["error_count"] == 1
    assert "operator_readback_private_key:password" in failed["errors"][0]
