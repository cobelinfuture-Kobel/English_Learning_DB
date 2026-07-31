from __future__ import annotations

import importlib.util
from pathlib import Path

from ulga.builders import (
    build_a1fs_ops_v1_unit01_real62_postmerge_disposable_full_product_integration_acceptance
    as integration,
)
from ulga.builders import (
    build_a1fs_ops_v1_unit01_student_package_chromium_main_product_entry_acceptance
    as builder,
)
from ulga.builders import (
    build_a1fs_v1_razq01f_fullfix_real62_semantic_lexical_anchor_fallback
    as razq01f,
)
from ulga.validators import (
    validate_a1fs_ops_v1_unit01_student_package_chromium_main_product_entry_acceptance
    as validator,
)


def load_previous_test():
    path = Path(__file__).with_name(
        "test_a1fs_ops_v1_unit01_real62_disposable_full_product_integration_ci.py"
    )
    spec = importlib.util.spec_from_file_location("_chromium_entry_fixture", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_unit01_student_entry_is_authenticated_and_chromium_printable(
    tmp_path: Path,
) -> None:
    previous = load_previous_test()
    fixture = previous.load_fixture()
    source_root = previous.make_v121_product(tmp_path, fixture)
    disposable_root = tmp_path / "disposable-product"
    evidence_database = tmp_path / "evidence.sqlite3"
    multisession_root = tmp_path / "multisession-evidence"
    fixture.setup_database(evidence_database)
    approved = fixture.approved_real44()
    learner_id = "learner-razq01f-ci"

    # Reuse the canonical passing Real62 fixture identities. This milestone tests
    # authenticated static delivery and Chromium rendering, not a new RAZQ01F
    # deterministic selector seed.
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

    chromium = builder.discover_chromium()
    report = builder.build_acceptance(
        disposable_product_root=disposable_root,
        approved_content=approved,
        chromium_path=chromium,
    )
    result = validator.validate(
        disposable_product_root=disposable_root,
        approved_content=approved,
    )

    assert report["status"] == builder.PASS_STATUS
    assert report["runtime_item_count"] == 474
    assert report["chromium_render_count"] == 4
    assert report["prelearning_pdf_page_count"] >= 7
    assert report["questionbank_sample_pdf_page_count"] >= 7
    assert report["prelearning_pdf_pass"] is True
    assert report["questionbank_stage_sample_pdf_pass"] is True
    assert report["chromium_screenshot_pass"] is True
    assert report["unauthenticated_access_blocked"] is True
    assert report["authenticated_entry_http_pass"] is True
    assert report["authenticated_http_readback"][
        "unauthenticated_prelearning_status"
    ] == 401
    assert report["authenticated_http_readback"][
        "authenticated_prelearning_status"
    ] == 200
    assert report["authenticated_http_readback"][
        "authenticated_questionbank_status"
    ] == 200
    assert report["teacher_files_unchanged"] is True
    assert report["source_product_root_unchanged"] is True
    assert report["second_question_bank_created"] is False
    assert report["formal_production_activation_approved"] is False
    assert report["production_root_mutated"] is False
    assert report["unit02_to_unit24_modified"] is False
    assert report["a2_unlocked"] is False

    assert result["validation_status"] == validator.PASS_STATUS
    assert result["error_count"] == 0, result["errors"]
    assert result["runtime_item_count"] == 474
    assert result["chromium_render_count"] == 4
    assert result["teacher_file_count_preserved"] == 2
    assert result["main_entry_file_count"] == 7
    assert result["authenticated_http_route_count"] == 2
    assert result["authenticated_http_readback_pass"] is True

    package_root = disposable_root / "shared/print_packages/unit01"
    acceptance_root = package_root / "acceptance"
    assert (acceptance_root / "unit01_prelearning_chromium.pdf").read_bytes().startswith(
        b"%PDF"
    )
    assert (
        acceptance_root / "unit01_questionbank_stage_sample_chromium.pdf"
    ).read_bytes().startswith(b"%PDF")
    assert (acceptance_root / "unit01_prelearning_chromium.png").read_bytes()[:8] == (
        b"\x89PNG\r\n\x1a\n"
    )
    assert (
        acceptance_root / "unit01_questionbank_stage_sample_chromium.png"
    ).read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"

    _version, static_root = builder._product_static_root(disposable_root)
    main_index = (static_root / "index.html").read_text(encoding="utf-8")
    assert builder.ENTRY_PANEL_ID in main_index
    assert f"/{builder.ENTRY_DIRECTORY}/prelearning.html" in main_index
    assert f"/{builder.ENTRY_DIRECTORY}/questionbank.html" in main_index
    assert "teacher/index.private.html" not in main_index

    entry_questionbank = static_root / builder.ENTRY_DIRECTORY / "questionbank.html"
    entry_questionbank.write_text(
        entry_questionbank.read_text(encoding="utf-8") + "\n<!-- correct_answer -->\n",
        encoding="utf-8",
    )
    failed = validator.validate(
        disposable_product_root=disposable_root,
        approved_content=approved,
    )
    assert failed["validation_status"] == validator.FAIL_STATUS
    assert failed["error_count"] == 1
    assert "main_entry_private_marker_exposed" in failed["errors"][0]
