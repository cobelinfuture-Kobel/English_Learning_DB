from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

PASS_STATUS = "PASS_A1FS_CI_GOV_V1_PR_WORKFLOW_FANOUT"
FAIL_STATUS = "FAIL_A1FS_CI_GOV_V1_PR_WORKFLOW_FANOUT"

GLOBAL_PR_WORKFLOWS = {
    "english-db-ci-readback.yml",
}

ALLOWED_AUTOMATIC_PR_WORKFLOWS = {
    "a1fs-ci-fanout-governance.yml",
    "a1fs-v1-canonical-content-governance.yml",
    "a1fs-v1-cp07f-r3c-semantic-bridge.yml",
    "english-db-ci-readback.yml",
}

MANUAL_HISTORICAL_DISPATCH = "a1fs-historical-regression-dispatch.yml"

CLOSED_AUTOMATIC_WORKFLOWS = {
    "ket-comp-transcript-final-consolidation.yml",
    "reading-v1-p1-tests.yml",
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
    "e4s-a1v1-m12e-representative-evidence-qa.yml",
    "e4s-a1v1-m12e-human-defer-guard.yml",
    "e4s-a1v1-m12e1-human-review-materialization.yml",
    "e4s-a1v1-m12f-m12e1-to-a1fs-remediation-bridge.yml",
    "e4s-a1v1-m12g-assessment-validity-fullfix.yml",
}

_EVENT_LINE = re.compile(r"^  ([A-Za-z0-9_-]+):(?:\s*.*)?$")
_TOP_LEVEL_CONCURRENCY = re.compile(r"^concurrency:\s*$", re.MULTILINE)
_CANCEL_IN_PROGRESS = re.compile(r"^\s{2}cancel-in-progress:\s*true\s*$", re.MULTILINE)


def _workflow_files(workflow_dir: Path) -> list[Path]:
    return sorted(
        [*workflow_dir.glob("*.yml"), *workflow_dir.glob("*.yaml")],
        key=lambda path: path.name,
    )


def _extract_on_block(text: str) -> list[str]:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line == "on:":
            block: list[str] = []
            for candidate in lines[index + 1 :]:
                if candidate and not candidate.startswith((" ", "\t", "#")):
                    break
                block.append(candidate)
            return block
        if line.startswith("on:"):
            return [line]
    return []


def _event_block(on_block: list[str], event_name: str) -> list[str]:
    if len(on_block) == 1 and on_block[0].startswith("on:"):
        return on_block if event_name in on_block[0] else []

    start: int | None = None
    for index, line in enumerate(on_block):
        match = _EVENT_LINE.match(line)
        if match and match.group(1) == event_name:
            start = index
            break
    if start is None:
        return []

    block = [on_block[start]]
    for line in on_block[start + 1 :]:
        if _EVENT_LINE.match(line):
            break
        block.append(line)
    return block


def _has_event(on_block: list[str], event_name: str) -> bool:
    return bool(_event_block(on_block, event_name))


def _has_path_scope(event_block: list[str]) -> bool:
    return any(
        re.match(r"^\s{4}(paths|paths-ignore):\s*$", line)
        for line in event_block
    )


def validate_workflows(workflow_dir: Path) -> dict[str, Any]:
    errors: list[str] = []
    files = _workflow_files(workflow_dir)
    by_name = {path.name: path for path in files}

    for closed_name in sorted(CLOSED_AUTOMATIC_WORKFLOWS):
        if closed_name in by_name:
            errors.append(f"closed_workflow_still_active:{closed_name}")

    dispatcher = by_name.get(MANUAL_HISTORICAL_DISPATCH)
    if dispatcher is None:
        errors.append(f"manual_dispatch_missing:{MANUAL_HISTORICAL_DISPATCH}")
    else:
        dispatcher_text = dispatcher.read_text(encoding="utf-8")
        dispatcher_on = _extract_on_block(dispatcher_text)
        if not _has_event(dispatcher_on, "workflow_dispatch"):
            errors.append("manual_dispatch_missing_workflow_dispatch")
        if _has_event(dispatcher_on, "pull_request"):
            errors.append("manual_dispatch_must_not_use_pull_request")
        if _has_event(dispatcher_on, "push"):
            errors.append("manual_dispatch_must_not_use_push")

    pr_workflows: list[str] = []
    catch_all_pr_workflows: list[str] = []
    path_scoped_pr_workflows: list[str] = []

    for path in files:
        text = path.read_text(encoding="utf-8")
        on_block = _extract_on_block(text)
        pull_request_block = _event_block(on_block, "pull_request")
        if not pull_request_block:
            continue

        pr_workflows.append(path.name)
        if path.name not in ALLOWED_AUTOMATIC_PR_WORKFLOWS:
            errors.append(f"unapproved_automatic_pr_workflow:{path.name}")
        if not _TOP_LEVEL_CONCURRENCY.search(text):
            errors.append(f"pr_workflow_missing_concurrency:{path.name}")
        if not _CANCEL_IN_PROGRESS.search(text):
            errors.append(f"pr_workflow_missing_cancel_in_progress:{path.name}")

        if _has_path_scope(pull_request_block):
            path_scoped_pr_workflows.append(path.name)
        else:
            catch_all_pr_workflows.append(path.name)
            if path.name not in GLOBAL_PR_WORKFLOWS:
                errors.append(f"unauthorized_catch_all_pr_workflow:{path.name}")

    missing_allowed = sorted(ALLOWED_AUTOMATIC_PR_WORKFLOWS - set(pr_workflows))
    if missing_allowed:
        errors.append("required_automatic_pr_workflows_missing:" + ",".join(missing_allowed))

    if len(pr_workflows) > len(ALLOWED_AUTOMATIC_PR_WORKFLOWS):
        errors.append(
            "automatic_pr_workflow_limit_exceeded:"
            f"{len(pr_workflows)}>{len(ALLOWED_AUTOMATIC_PR_WORKFLOWS)}"
        )

    if len(catch_all_pr_workflows) > len(GLOBAL_PR_WORKFLOWS):
        errors.append(
            "catch_all_pr_workflow_limit_exceeded:"
            f"{len(catch_all_pr_workflows)}>{len(GLOBAL_PR_WORKFLOWS)}"
        )

    unknown_global = sorted(set(catch_all_pr_workflows) - GLOBAL_PR_WORKFLOWS)
    if unknown_global:
        errors.append("unknown_global_pr_workflows:" + ",".join(unknown_global))

    report = {
        "validation_status": PASS_STATUS if not errors else FAIL_STATUS,
        "error_count": len(errors),
        "errors": errors,
        "workflow_count": len(files),
        "pull_request_workflow_count": len(pr_workflows),
        "allowed_automatic_pull_request_workflow_count": len(ALLOWED_AUTOMATIC_PR_WORKFLOWS),
        "catch_all_pull_request_workflow_count": len(catch_all_pr_workflows),
        "path_scoped_pull_request_workflow_count": len(path_scoped_pr_workflows),
        "closed_automatic_workflow_count": len(CLOSED_AUTOMATIC_WORKFLOWS),
        "manual_historical_dispatch_present": dispatcher is not None,
        "pull_request_workflows": sorted(pr_workflows),
        "catch_all_pull_request_workflows": sorted(catch_all_pr_workflows),
        "path_scoped_pull_request_workflows": sorted(path_scoped_pr_workflows),
        "ordinary_pr_expected_action_ceiling": 3,
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate GitHub Actions pull-request fan-out governance."
    )
    parser.add_argument(
        "--workflow-dir",
        type=Path,
        default=Path(".github/workflows"),
    )
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    report = validate_workflows(args.workflow_dir)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered + "\n", encoding="utf-8")
    return 0 if report["validation_status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
