from __future__ import annotations

from pathlib import Path

from tools import validate_pr_workflow_fanout as validator

ROOT = Path(__file__).resolve().parents[2]


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_repository_workflow_policy_passes_for_governance_change() -> None:
    changed = (
        ".github/workflows/a1fs-v1-canonical-content-governance.yml",
        ".github/workflows/e4s-a1v1-m11a-authority-evidence-review.yml",
        "tools/validate_pr_workflow_fanout.py",
        "tests/ulga/test_pr_workflow_fanout_policy.py",
    )
    report = validator.validate_workflows(ROOT / ".github/workflows", changed_paths=changed)
    assert report["validation_status"] == "PASS_PR_WORKFLOW_FANOUT_POLICY", report["errors"]
    assert report["archived_manual_only_count"] == len(validator.ARCHIVED_MANUAL_ONLY)
    assert report["matching_pr_workflow_count"] <= validator.DEFAULT_MAX_MATCHING_PR_WORKFLOWS
    assert report["legacy_missing_concurrency_count"] >= 1


def test_rejects_unscoped_changed_task_workflow_and_missing_concurrency(tmp_path: Path) -> None:
    _write(
        tmp_path / "task.yml",
        """name: Task\n\non:\n  pull_request:\n\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo test\n""",
    )
    report = validator.validate_workflows(
        tmp_path,
        changed_paths=(".github/workflows/task.yml",),
    )
    assert "unscoped_pr_workflow_not_allowed:task.yml" in report["errors"]
    assert "pr_workflow_missing_concurrency:task.yml" in report["errors"]


def test_untouched_path_scoped_workflow_without_concurrency_is_warning(tmp_path: Path) -> None:
    _write(
        tmp_path / "legacy.yml",
        """name: Legacy\n\non:\n  pull_request:\n    paths:\n      - \"legacy/file.py\"\n\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo test\n""",
    )
    report = validator.validate_workflows(tmp_path)
    assert report["errors"] == []
    assert "legacy_pr_workflow_missing_concurrency:legacy.yml" in report["warnings"]


def test_rejects_broad_paths_for_task_workflow(tmp_path: Path) -> None:
    _write(
        tmp_path / "task.yml",
        """name: Task\n\non:\n  pull_request:\n    paths:\n      - \"ulga/**\"\n  workflow_dispatch:\n\nconcurrency:\n  group: ${{ github.workflow }}-${{ github.ref }}\n  cancel-in-progress: true\n\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo test\n""",
    )
    report = validator.validate_workflows(tmp_path)
    assert "task_workflow_paths_too_broad:task.yml:ulga/**" in report["errors"]


def test_changed_file_fanout_is_capped(tmp_path: Path) -> None:
    for index in range(4):
        _write(
            tmp_path / f"task-{index}.yml",
            f"""name: Task {index}\n\non:\n  pull_request:\n    paths:\n      - \"target/file.py\"\n\nconcurrency:\n  group: ${{{{ github.workflow }}}}-${{{{ github.ref }}}}\n  cancel-in-progress: true\n\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo test\n""",
        )
    report = validator.validate_workflows(
        tmp_path,
        changed_paths=("target/file.py",),
        max_matching=3,
    )
    assert report["matching_pr_workflow_count"] == 4
    assert any(error.startswith("changed_file_fanout_exceeded:4>3:") for error in report["errors"])
