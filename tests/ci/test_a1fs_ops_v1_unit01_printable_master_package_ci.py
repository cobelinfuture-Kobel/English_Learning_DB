from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from ulga.builders import (
    build_a1fs_ops_v1_unit01_canonical_question_bank_vocabulary_chunk_sentence_printable_master_package
    as builder,
)
from ulga.builders import (
    build_a1fs_ops_v1_unit01_real62_postmerge_disposable_full_product_integration_acceptance
    as integration,
)
from ulga.builders import (
    build_a1fs_v1_razq01f_fullfix_real62_semantic_lexical_anchor_fallback
    as razq01f,
)
from ulga.validators import (
    validate_a1fs_ops_v1_unit01_canonical_question_bank_vocabulary_chunk_sentence_printable_master_package
    as validator,
)


def load_previous_test():
    path = Path(__file__).with_name(
        "test_a1fs_ops_v1_unit01_real62_disposable_full_product_integration_ci.py"
    )
    spec = importlib.util.spec_from_file_location("_real62_disposable_fixture", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_unit01_printable_master_package_is_complete_and_learner_safe(
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
    razq01f.install_fullfix()
    evidence = razq01f.run_acceptance(
        database=evidence_database,
        approved_content=approved,
        learner_id="learner-razq01f-ci",
        output_root=multisession_root,
        session_prefix="session-razq01f-ci",
    )
    assert evidence["status"] == razq01f.PASS_STATUS
    integrated = integration.integrate_disposable_product(
        source_product_root=source_root,
        disposable_product_root=disposable_root,
        approved_content=approved,
        multisession_root=multisession_root,
        learner_id="learner-razq01f-ci",
        release_session_id="session-razq01g-release-ci",
    )
    assert integrated["status"] == integration.PASS_STATUS

    report = builder.build_package(
        disposable_product_root=disposable_root,
        approved_content=approved,
    )
    result = validator.validate(
        disposable_product_root=disposable_root,
        approved_content=approved,
    )

    assert report["status"] == builder.PASS_STATUS
    assert report["runtime_item_count"] == 474
    assert report["base_item_count"] == 288
    assert report["extension_item_count"] == 186
    assert report["active_vocabulary_count"] == 22
    assert report["canonical_chunk_count"] == 3
    assert report["instructional_phrase_count"] == 21
    assert report["sentence_frame_count"] == 11
    assert report["model_sentence_count"] > 0
    assert report["learner_answer_leakage_count"] == 0
    assert report["raw_raz_identity_leakage_count"] == 0
    assert report["browser_print_available"] is True
    assert report["main_product_print_button_integrated"] is False
    assert report["formal_production_activation_approved"] is False
    assert result["validation_status"] == validator.PASS_STATUS
    assert result["error_count"] == 0, result["errors"]

    output_root = disposable_root / builder.DEFAULT_RELATIVE_OUTPUT
    learner_data = json.loads(
        (output_root / "learner/unit01_learner_print_data.json").read_text(
            encoding="utf-8"
        )
    )
    teacher_data = json.loads(
        (
            output_root / "teacher/unit01_teacher_print_data.private.json"
        ).read_text(encoding="utf-8")
    )
    assert len(learner_data["questions"]) == 474
    assert len(teacher_data["questions"]) == 474
    learner_text = json.dumps(learner_data, ensure_ascii=False).casefold()
    assert all(
        marker.casefold() not in learner_text
        for marker in builder.FORBIDDEN_LEARNER_MARKERS
    )
    assert any(
        row.get("correct_answer") is not None
        for row in teacher_data["questions"]
    )
    learner_html = (output_root / "learner/index.html").read_text(
        encoding="utf-8"
    )
    teacher_html = (output_root / "teacher/index.private.html").read_text(
        encoding="utf-8"
    )
    assert "window.print()" in learner_html
    assert "window.print()" in teacher_html
    assert "列印／另存 PDF" in learner_html
    assert "Private teacher edition" in teacher_html

    learner_path = output_root / "learner/unit01_learner_print_data.json"
    tampered = json.loads(learner_path.read_text(encoding="utf-8"))
    tampered["correct_answer"] = "leak"
    learner_path.write_text(
        json.dumps(tampered, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    failed = validator.validate(
        disposable_product_root=disposable_root,
        approved_content=approved,
    )
    assert failed["validation_status"] == validator.FAIL_STATUS
    assert failed["error_count"] == 1
