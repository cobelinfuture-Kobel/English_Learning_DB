from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ARCHIVED_MANUAL_ONLY = {
    "e4s-a1v1-m05-listening-v1.yml",
    "e4s-a1v1-m06-speaking-v1.yml",
    "e4s-a1v1-m07-four-skill-closure.yml",
    "e4s-a1v1-m08-text-mode-session.yml",
    "e4s-a1v1-m09-private-runtime.yml",
    "e4s-a1v1-m10-coverage-recheck.yml",
    "e4s-a1v1-m11-candidate-content-review.yml",
    "e4s-a1v1-m11a-authority-evidence-review.yml",
    "e4s-a1v1-m11b-authority-exception-resolution.yml",
    "e4s-a1v1-m11c-authority-reviewed-runtime.yml",
    "e4s-a1v1-m11d-system-acceptance-closeout.yml",
    "e4s-a1v1-m12-real-pilot-evidence-capture.yml",
    "e4s-a1v1-m12c-real-evidence-qa-iteration.yml",
    "e4s-a1v1-m12d-representative-pilot-expansion.yml",
    "e4s-a1v1-m12e-human-defer-guard.yml",
    "e4s-a1v1-m12e-representative-evidence-qa.yml",
    "e4s-a1v1-m12e1-human-review-materialization.yml",
    "e4s-a1v1-m12f-m12e1-to-a1fs-remediation-bridge.yml",
    "e4s-a1v1-m12g-assessment-validity-fullfix.yml",
    "ket-comp-transcript-final-consolidation.yml",
    "reading-v1-p1-tests.yml",
}

UNSCOPED_PR_ALLOWLIST = {"english-db-ci-readback.yml"}
GLOBAL_SCOPED_PR_ALLOWLIST = {"a1fs-v1-canonical-content-governance.yml"}
FORBIDDEN_TASK_PATHS = {
    "**",
    "docs/**",
    "tests/**",
    "tests/ulga/**",
    "tools/**",
    "ulga/**",
    ".github/workflows/**",
}
DEFAULT_MAX_MATCHING_PR_WORKFLOWS = 3


@dataclass(frozen=True)
class WorkflowPolicy:
    filename: str
    triggers: frozenset[str]
    pull_request_paths: tuple[str, ...]
    cancel_in_progress: bool

    @property
    def has_pull_request(self) -> bool:
        return "pull_request" in self.triggers or "pull_request_target" in self.triggers


def _top_level_block(lines: list[str], key: str) -> list[str]:
    start = None
    for index, line in enumerate(lines):
        if re.match(rf"^{re.escape(key)}:\s*", line):
            start = index + 1
            break
    if start is None:
        return []
    block: list[str] = []
    for line in lines[start:]:
        if line.strip() and not line.startswith((" ", "\t", "#")):
            break
        block.append(line)
    return block


def _inline_on_value(lines: list[str]) -> str:
    for line in lines:
        match = re.match(r"^on:\s*(.+?)\s*$", line)
        if match:
            return match.group(1)
    return ""


def _trigger_names(lines: list[str]) -> set[str]:
    names: set[str] = set()
    inline = _inline_on_value(lines)
    if inline:
        for candidate in ("push", "pull_request", "pull_request_target", "workflow_dispatch"):
            if re.search(rf"\b{candidate}\b", inline):
                names.add(candidate)
    for line in _top_level_block(lines, "on"):
        match = re.match(r"^\s{2}([A-Za-z0-9_-]+):", line)
        if match:
            names.add(match.group(1))
    return names


def _trigger_block(lines: list[str], trigger: str) -> list[str]:
    on_block = _top_level_block(lines, "on")
    start = None
    for index, line in enumerate(on_block):
        if re.match(rf"^\s{{2}}{re.escape(trigger)}:\s*", line):
            start = index + 1
            break
    if start is None:
        return []
    block: list[str] = []
    for line in on_block[start:]:
        if line.strip() and re.match(r"^\s{2}\S", line):
            break
        block.append(line)
    return block


def _extract_paths(lines: list[str], trigger: str) -> tuple[str, ...]:
    block = _trigger_block(lines, trigger)
    paths: list[str] = []
    collecting = False
    for line in block:
        inline = re.match(r"^\s{4}paths:\s*\[(.*)\]\s*$", line)
        if inline:
            values = [value.strip().strip("'\"") for value in inline.group(1).split(",")]
            paths.extend(value for value in values if value)
            collecting = False
            continue
        if re.match(r"^\s{4}paths:\s*$", line):
            collecting = True
            continue
        if collecting:
            item = re.match(r"^\s{6}-\s*['\"]?(.+?)['\"]?\s*$", line)
            if item:
                paths.append(item.group(1))
                continue
            if line.strip() and len(line) - len(line.lstrip()) <= 4:
                collecting = False
    return tuple(paths)


def _cancel_in_progress(lines: list[str]) -> bool:
    return any(
        re.match(r"^\s{2}cancel-in-progress:\s*true\s*$", line, re.IGNORECASE)
        for line in _top_level_block(lines, "concurrency")
    )


def parse_workflow(path: Path) -> WorkflowPolicy:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    triggers = _trigger_names(lines)
    pr_paths = _extract_paths(lines, "pull_request") or _extract_paths(lines, "pull_request_target")
    return WorkflowPolicy(
        filename=path.name,
        triggers=frozenset(triggers),
        pull_request_paths=pr_paths,
        cancel_in_progress=_cancel_in_progress(lines),
    )


def _matches_path(pattern: str, changed_path: str) -> bool:
    pattern = pattern.lstrip("./")
    changed_path = changed_path.lstrip("./")
    if pattern.endswith("/**"):
        prefix = pattern[:-3].rstrip("/")
        return changed_path == prefix or changed_path.startswith(prefix + "/")
    return fnmatch.fnmatchcase(changed_path, pattern)


def workflow_matches_changes(workflow: WorkflowPolicy, changed_paths: Iterable[str]) -> bool:
    if not workflow.has_pull_request:
        return False
    if not workflow.pull_request_paths:
        return True
    return any(
        _matches_path(pattern, changed_path)
        for pattern in workflow.pull_request_paths
        for changed_path in changed_paths
    )


def validate_workflows(
    workflow_dir: Path,
    *,
    changed_paths: Iterable[str] = (),
    max_matching: int = DEFAULT_MAX_MATCHING_PR_WORKFLOWS,
) -> dict[str, object]:
    paths = sorted([*workflow_dir.glob("*.yml"), *workflow_dir.glob("*.yaml")])
    workflows = [parse_workflow(path) for path in paths]
    errors: list[str] = []

    by_name = {workflow.filename: workflow for workflow in workflows}
    missing_archived = sorted(ARCHIVED_MANUAL_ONLY - set(by_name))
    errors.extend(f"archived_workflow_missing:{name}" for name in missing_archived)

    for filename in sorted(ARCHIVED_MANUAL_ONLY & set(by_name)):
        workflow = by_name[filename]
        if workflow.triggers != frozenset({"workflow_dispatch"}):
            errors.append(
                f"archived_workflow_not_manual_only:{filename}:{','.join(sorted(workflow.triggers))}"
            )
        if not workflow.cancel_in_progress:
            errors.append(f"archived_workflow_missing_concurrency:{filename}")

    pr_workflows = [workflow for workflow in workflows if workflow.has_pull_request]
    for workflow in pr_workflows:
        if not workflow.cancel_in_progress:
            errors.append(f"pr_workflow_missing_concurrency:{workflow.filename}")
        if not workflow.pull_request_paths and workflow.filename not in UNSCOPED_PR_ALLOWLIST:
            errors.append(f"unscoped_pr_workflow_not_allowed:{workflow.filename}")
        if (
            workflow.filename not in GLOBAL_SCOPED_PR_ALLOWLIST
            and workflow.filename not in UNSCOPED_PR_ALLOWLIST
        ):
            broad = sorted(set(workflow.pull_request_paths) & FORBIDDEN_TASK_PATHS)
            if broad:
                errors.append(f"task_workflow_paths_too_broad:{workflow.filename}:{','.join(broad)}")

    changed_paths = tuple(changed_paths)
    matching = [
        workflow.filename
        for workflow in pr_workflows
        if changed_paths and workflow_matches_changes(workflow, changed_paths)
    ]
    if changed_paths and len(matching) > max_matching:
        errors.append(
            f"changed_file_fanout_exceeded:{len(matching)}>{max_matching}:{','.join(sorted(matching))}"
        )

    return {
        "validation_status": "PASS_PR_WORKFLOW_FANOUT_POLICY" if not errors else "FAIL_PR_WORKFLOW_FANOUT_POLICY",
        "workflow_count": len(workflows),
        "automatic_pr_workflow_count": len(pr_workflows),
        "unscoped_pr_workflow_count": sum(not workflow.pull_request_paths for workflow in pr_workflows),
        "archived_manual_only_count": sum(
            filename in by_name and by_name[filename].triggers == frozenset({"workflow_dispatch"})
            for filename in ARCHIVED_MANUAL_ONLY
        ),
        "changed_path_count": len(changed_paths),
        "matching_pr_workflow_count": len(matching),
        "matching_pr_workflows": sorted(matching),
        "max_matching_pr_workflows": max_matching,
        "errors": errors,
    }


def changed_paths_from_git(base: str) -> tuple[str, ...]:
    completed = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return tuple(line.strip() for line in completed.stdout.splitlines() if line.strip())


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate GitHub Actions PR fan-out policy.")
    parser.add_argument("--workflow-dir", type=Path, default=Path(".github/workflows"))
    parser.add_argument("--changed-from")
    parser.add_argument("--max-matching", type=int, default=DEFAULT_MAX_MATCHING_PR_WORKFLOWS)
    args = parser.parse_args()

    changed_paths = changed_paths_from_git(args.changed_from) if args.changed_from else ()
    report = validate_workflows(
        args.workflow_dir,
        changed_paths=changed_paths,
        max_matching=args.max_matching,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if not report["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
