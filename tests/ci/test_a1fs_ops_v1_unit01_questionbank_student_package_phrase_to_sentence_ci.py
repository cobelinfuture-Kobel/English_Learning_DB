from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from ulga.builders import (
    build_a1fs_ops_v1_unit01_questionbank_student_package_phrase_to_sentence
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
    validate_a1fs_ops_v1_unit01_questionbank_student_package_phrase_to_sentence
    as validator,
)


def load_previous_test():
    path = Path(__file__).with_name(
        "test_a1fs_ops_v1_unit01_real62_disposable_full_product_integration_ci.py"
    )
    spec = importlib.util.spec_from_file_location("_student_package_fixture", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_unit01_student_package_preserves_teacher_and_orders_phrase_before_sentence(
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
    razq01f.install_fullfix()
    evidence = razq01f.run_acceptance(
        database=evidence_database,
        approved_content=approved,
        learner_id=learner_id,
        output_root=multisession_root,
        session_prefix="session-student-package-ci",
    )
    assert evidence["status"] == razq01f.PASS_STATUS
    integrated = integration.integrate_disposable_product(
        source_product_root=source_root,
        disposable_product_root=disposable_root,
        approved_content=approved,
        multisession_root=multisession_root,
        learner_id=learner_id,
        release_session_id="session-student-package-release-ci",
    )
    assert integrated["status"] == integration.PASS_STATUS

    report = builder.build_student_package(
        disposable_product_root=disposable_root,
        approved_content=approved,
    )
    result = validator.validate(
        disposable_product_root=disposable_root,
        approved_content=approved,
    )

    assert report["status"] == builder.PASS_STATUS
    assert report["runtime_item_count"] == 474
    assert report["stage_count"] == 7
    assert report["teacher_files_unchanged"] is True
    assert report["learner_images_present"] is False
    assert report["learner_answer_leakage_count"] == 0
    assert report["phrase_before_sentence_order"] is True
    assert report["second_question_bank_created"] is False
    assert report["formal_production_activation_approved"] is False
    assert result["validation_status"] == validator.PASS_STATUS
    assert result["error_count"] == 0, result["errors"]
    assert result["runtime_item_count"] == 474
    assert result["pattern_family_count"] == 12
    assert result["stage_count"] == 7
    assert result["teacher_file_count_preserved"] == 2

    output_root = disposable_root / "shared/print_packages/unit01"
    student = json.loads(
        (output_root / "learner" / builder.STUDENT_DATA_NAME).read_text(
            encoding="utf-8"
        )
    )
    questions = student["questions"]
    assert len(questions) == 474
    assert [row["student_item_no"] for row in questions] == list(range(1, 475))
    assert [row["layout_stage_rank"] for row in questions] == sorted(
        row["layout_stage_rank"] for row in questions
    )
    assert "teacher_file_identities" not in student
    assert all("content_origin" not in row for row in questions)
    assert all("correct_answer" not in row for row in questions)
    assert all("item_id" not in row for row in questions)

    learner_index = (output_root / "learner/index.html").read_text(encoding="utf-8")
    prelearning = (output_root / "learner/prelearning.html").read_text(
        encoding="utf-8"
    )
    questionbank = (output_root / "learner/questionbank.html").read_text(
        encoding="utf-8"
    )
    assert "Pre-learning" in learner_index
    assert "QuestionBank" in learner_index
    assert "teacher/index.private.html" not in learner_index
    assert "Part 1" in prelearning and "Part 6" in prelearning
    assert "Phrase 1" in questionbank
    assert "connected sentences" in questionbank
    assert "<img" not in (learner_index + prelearning + questionbank).casefold()

    student_path = output_root / "learner" / builder.STUDENT_DATA_NAME
    tampered = json.loads(student_path.read_text(encoding="utf-8"))
    tampered["questions"][0]["correct_answer"] = "leak"
    student_path.write_text(
        json.dumps(tampered, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    failed = validator.validate(
        disposable_product_root=disposable_root,
        approved_content=approved,
    )
    assert failed["validation_status"] == validator.FAIL_STATUS
    assert failed["error_count"] == 1
