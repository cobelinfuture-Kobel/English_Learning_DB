from __future__ import annotations

import importlib.util
import json
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
    spec = importlib.util.spec_from_file_location(
        "_local_private_operator_fixture",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_unit01_local_private_materialization_discovers_artifact_and_validates(
    tmp_path: Path,
) -> None:
    previous = load_previous_test()
    fixture = previous.load_fixture()
    source_root = previous.make_v121_product(tmp_path, fixture)
    disposable_root = tmp_path / "disposable-product"
    evidence_database = tmp_path / "evidence.sqlite3"
    multisession_root = tmp_path / "multisession-evidence"
    approved_root = tmp_path / "approved-artifacts"
    approved_root.mkdir()
    fixture.setup_database(evidence_database)
    approved = fixture.approved_real44()
    approved_path = approved_root / "unit01_approved_content.json"
    approved_path.write_text(
        json.dumps(approved, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
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
        disposable_product_root=disposable_root,
        approved_content=approved,
        multisession_root=multisession_root,
        learner_id=learner_id,
        release_session_id="session-razq01g-release-ci",
    )
    assert integrated["status"] == integration.PASS_STATUS

    chromium = builder.acceptance.discover_chromium()
    report = builder.materialize_operator_readback(
        disposable_product_root=disposable_root,
        search_roots=[approved_root],
        chromium_path=chromium,
    )
    result = validator.validate(
        disposable_product_root=disposable_root,
        search_roots=[approved_root],
    )

    assert report["status"] == builder.PASS_STATUS
    assert report["runtime_item_count"] == 474
    assert report["approved_content_discovery_mode"] == "ARTIFACT_SHA_DISCOVERY"
    assert report["approved_content_file_name"] == approved_path.name
    assert report["chromium_render_count"] == 4
    assert report["prelearning_pdf_page_count"] >= 7
    assert report["questionbank_sample_pdf_page_count"] >= 7
    assert report["unauthenticated_prelearning_status"] == 401
    assert report["authenticated_prelearning_status"] == 200
    assert report["authenticated_questionbank_status"] == 200
    assert report["operator_visual_confirmation_required"] is True
    assert report["operator_visual_confirmation_completed"] is False
    assert report["formal_production_activation_approved"] is False
    assert report["production_root_mutated"] is False
    assert report["unit02_to_unit24_modified"] is False
    assert report["a2_unlocked"] is False
    assert "approved_content_path" not in report
    assert all(
        not Path(name).is_absolute()
        for name in report["package_relative_outputs"].values()
    )

    assert result["validation_status"] == validator.PASS_STATUS, result["errors"]
    assert result["error_count"] == 0, result["errors"]
    assert result["runtime_item_count"] == 474
    assert result["chromium_render_count"] == 4
    assert result["operator_output_file_count"] == 7
    assert result["authenticated_http_route_count"] == 2
    assert result["teacher_file_count_preserved"] == 2
    assert result["authenticated_http_readback_pass"] is True

    report_path = disposable_root / "shared/reports" / builder.REPORT_NAME
    tampered = json.loads(report_path.read_text(encoding="utf-8"))
    tampered["runtime_item_count"] = 475
    report_path.write_text(
        json.dumps(tampered, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    failed = validator.validate(
        disposable_product_root=disposable_root,
        search_roots=[approved_root],
    )
    assert failed["validation_status"] == validator.FAIL_STATUS
    assert failed["error_count"] == 1
    assert "operator_readback_digest_invalid" in failed["errors"][0]


def test_unit01_approved_content_discovery_fails_closed_on_ambiguity(
    tmp_path: Path,
) -> None:
    expected_sha = "a" * 64
    for name in ("first.json", "second.json"):
        (tmp_path / name).write_text(
            json.dumps(
                {"artifact_sha256": expected_sha},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    try:
        builder.discover_approved_content(
            expected_sha=expected_sha,
            search_roots=[tmp_path],
        )
    except builder.LocalPrivateOperatorError as exc:
        assert "approved_content_ambiguous:2" in str(exc)
    else:
        raise AssertionError("ambiguous approved content was not rejected")
