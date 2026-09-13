from __future__ import annotations

from pathlib import Path

from ulga.validators import validate_pr_workflow_fanout as validator

ROOT = Path(__file__).resolve().parents[2]


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_repository_workflow_fanout_governance_passes() -> None:
    report = validator.validate_workflows(ROOT / ".github/workflows")
    assert report["validation_status"] == validator.PASS_STATUS, report["errors"]
    assert report["catch_all_pull_request_workflow_count"] <= 1
    assert report["ordinary_pr_expected_action_ceiling"] == 3
    assert report["manual_historical_dispatch_present"] is True


def test_non_global_catch_all_pull_request_workflow_fails(tmp_path: Path) -> None:
    workflow_dir = tmp_path / ".github/workflows"
    _write(
        workflow_dir / validator.MANUAL_HISTORICAL_DISPATCH,
        "name: historical\non:\n  workflow_dispatch:\njobs:\n  noop:\n    runs-on: ubuntu-latest\n    steps:\n      - run: true\n",
    )
    _write(
        workflow_dir / "rogue.yml",
        "name: rogue\non:\n  pull_request:\nconcurrency:\n  group: rogue\n  cancel-in-progress: true\njobs:\n  noop:\n    runs-on: ubuntu-latest\n    steps:\n      - run: true\n",
    )

    report = validator.validate_workflows(workflow_dir)
    assert report["validation_status"] == validator.FAIL_STATUS
    assert "unauthorized_catch_all_pr_workflow:rogue.yml" in report["errors"]


def test_path_scoped_pull_request_requires_concurrency(tmp_path: Path) -> None:
    workflow_dir = tmp_path / ".github/workflows"
    _write(
        workflow_dir / validator.MANUAL_HISTORICAL_DISPATCH,
        "name: historical\non:\n  workflow_dispatch:\njobs:\n  noop:\n    runs-on: ubuntu-latest\n    steps:\n      - run: true\n",
    )
    _write(
        workflow_dir / "focused.yml",
        "name: focused\non:\n  pull_request:\n    paths:\n      - tests/focused/**\njobs:\n  noop:\n    runs-on: ubuntu-latest\n    steps:\n      - run: true\n",
    )

    report = validator.validate_workflows(workflow_dir)
    assert report["validation_status"] == validator.FAIL_STATUS
    assert "pr_workflow_missing_concurrency:focused.yml" in report["errors"]
    assert "pr_workflow_missing_cancel_in_progress:focused.yml" in report["errors"]


def test_closed_historical_workflow_cannot_reappear(tmp_path: Path) -> None:
    workflow_dir = tmp_path / ".github/workflows"
    _write(
        workflow_dir / validator.MANUAL_HISTORICAL_DISPATCH,
        "name: historical\non:\n  workflow_dispatch:\njobs:\n  noop:\n    runs-on: ubuntu-latest\n    steps:\n      - run: true\n",
    )
    closed_name = sorted(validator.CLOSED_AUTOMATIC_WORKFLOWS)[0]
    _write(
        workflow_dir / closed_name,
        "name: closed\non:\n  pull_request:\njobs:\n  noop:\n    runs-on: ubuntu-latest\n    steps:\n      - run: true\n",
    )

    report = validator.validate_workflows(workflow_dir)
    assert report["validation_status"] == validator.FAIL_STATUS
    assert f"closed_workflow_still_active:{closed_name}" in report["errors"]


def test_storage_evidence_only_does_not_escalate_to_full() -> None:
    report = validator.classify_changed_paths([
        "data/ket/ket_source_manifest.json",
        "data/ket/ket_task_evidence.jsonl",
    ])
    assert report["impact_scope"] == validator.IMPACT_STORAGE_ONLY


def test_storage_registry_is_generic_not_ket_hardcoded() -> None:
    report = validator.classify_changed_paths(
        ["evidence/vocabulary/source_manifest.json"],
        storage_prefixes=("data/ket/", "evidence/vocabulary/"),
    )
    assert report["impact_scope"] == validator.IMPACT_STORAGE_ONLY


def test_ket_data_plus_ket_validator_is_focused() -> None:
    report = validator.classify_changed_paths([
        "data/ket/ket_source_manifest.json",
        "tests/ci/test_ket_data_s1_page_media_segmentation.py",
    ])
    assert report["impact_scope"] == validator.IMPACT_KET_FOCUSED


def test_ci_governance_change_uses_governance_scope() -> None:
    report = validator.classify_changed_paths([
        ".github/workflows/english-db-ci-readback.yml",
        "docs/ulga/E4S_CI_WORKFLOW_CONTRACT.md",
        "ulga/validators/validate_pr_workflow_fanout.py",
        "tests/ci/test_pr_workflow_fanout.py",
    ])
    assert report["impact_scope"] == validator.IMPACT_CI_GOVERNANCE


def test_single_unit_change_is_unit_scoped() -> None:
    report = validator.classify_changed_paths([
        "ulga/builders/build_a1fs_v1_u04_example.py",
        "tests/ci/test_a1fs_v1_unit04_example.py",
    ])
    assert report["impact_scope"] == "UNIT04"


def test_different_units_fail_safe_to_full() -> None:
    report = validator.classify_changed_paths([
        "ulga/builders/build_a1fs_v1_u02_example.py",
        "tests/ci/test_a1fs_v1_u04_example.py",
    ])
    assert report["impact_scope"] == validator.IMPACT_FULL


def test_shared_runtime_change_fails_safe_to_full() -> None:
    report = validator.classify_changed_paths([
        "ulga/builders/shared_runtime_selector.py",
    ])
    assert report["impact_scope"] == validator.IMPACT_FULL


def test_unknown_path_fails_safe_to_full() -> None:
    report = validator.classify_changed_paths(["unknown/new_surface.bin"])
    assert report["impact_scope"] == validator.IMPACT_FULL


def test_ordinary_docs_are_docs_only() -> None:
    report = validator.classify_changed_paths([
        "docs/reference/example.md",
        "README.md",
    ])
    assert report["impact_scope"] == validator.IMPACT_DOCS_ONLY
