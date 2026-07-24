from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/a1fs-v1-cp07f-r3c-semantic-bridge.yml"

RETAINED_OPTIONAL_OVERLAY_FILES = (
    "ulga/builders/build_ket99_pku_evidence_reference_learning_value_evaluation.py",
    "ulga/validators/validate_ket99_pku_evidence_reference_learning_value_evaluation.py",
    "ulga/builders/build_ket99_pku_selected_reading_teacher_delivery_remediation_assets.py",
    "ulga/validators/validate_ket99_pku_selected_reading_teacher_delivery_remediation_assets.py",
)

ROLLED_BACK_RUNTIME_COUPLING_FILES = (
    "ulga/builders/build_ket99_pku_selected_reading_asset_consumer_activation_canary.py",
    "ulga/validators/validate_ket99_pku_selected_reading_asset_consumer_activation_canary.py",
    "tests/ulga/test_ket99_pku_selected_reading_asset_consumer_activation_canary.py",
    "ulga/builders/build_ket99_pku_m4d_private_chain_materialization.py",
    "ulga/validators/validate_ket99_pku_m4d_private_chain_materialization.py",
    "tests/ulga/test_ket99_pku_m4d_private_chain_materialization.py",
    "ulga/builders/run_ket99_pku_m4d_private_chain_materialization.py",
)


def test_m4b_m4c_optional_overlay_is_retained() -> None:
    for relative in RETAINED_OPTIONAL_OVERLAY_FILES:
        assert (ROOT / relative).is_file(), relative


def test_m4d_runtime_coupling_is_rolled_back() -> None:
    for relative in ROLLED_BACK_RUNTIME_COUPLING_FILES:
        assert not (ROOT / relative).exists(), relative


def test_focused_workflow_keeps_m4c_and_drops_runtime_coupling() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "build_ket99_pku_selected_reading_teacher_delivery_remediation_assets.py" in workflow
    assert "test_ket99_pku_optional_overlay_freeze_and_runtime_coupling_rollback.py" in workflow
    for relative in ROLLED_BACK_RUNTIME_COUPLING_FILES:
        assert Path(relative).name not in workflow, relative
