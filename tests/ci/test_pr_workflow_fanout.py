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
    assert report["catch_all_pull_request_workflow_count"] <= 2
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
