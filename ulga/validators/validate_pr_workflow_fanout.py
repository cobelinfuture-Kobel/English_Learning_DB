from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterable

PASS_STATUS = "PASS_A1FS_CI_GOV_V1_PR_WORKFLOW_FANOUT"
FAIL_STATUS = "FAIL_A1FS_CI_GOV_V1_PR_WORKFLOW_FANOUT"

GLOBAL_PR_WORKFLOWS = {"english-db-ci-readback.yml"}

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

# Registered roots are role declarations, not a hard-coded KET routing architecture.
# Future evidence/storage roots are added here without changing the classifier algorithm.
STORAGE_EVIDENCE_PREFIXES = ("data/ket/",)

IMPACT_STORAGE_ONLY = "STORAGE_ONLY"
IMPACT_DOCS_ONLY = "DOCS_ONLY"
IMPACT_CI_GOVERNANCE = "CI_GOVERNANCE"
IMPACT_KET_FOCUSED = "KET_FOCUSED"
IMPACT_FULL = "FULL"

CI_GOVERNANCE_PATHS = {
    "docs/ulga/E4S_CI_WORKFLOW_CONTRACT.md",
    "ulga/validators/validate_pr_workflow_fanout.py",
    "tests/ci/test_pr_workflow_fanout.py",
}
CI_GOVERNANCE_PREFIXES = (".github/workflows/",)

KET_FOCUSED_PREFIXES = (
    "data/ket/",
    "tests/ci/test_ket_data_",
    "ulga/validators/validate_ket_data_",
)

_EVENT_LINE = re.compile(r"^  ([A-Za-z0-9_-]+):(?:\s*.*)?$")
_TOP_LEVEL_CONCURRENCY = re.compile(r"^concurrency:\s*$", re.MULTILINE)
_CANCEL_IN_PROGRESS = re.compile(r"^\s{2}cancel-in-progress:\s*true\s*$", re.MULTILINE)
_UNIT_TOKEN = re.compile(r"(?:^|[/_.-])(?:unit|u)0?([1-9]\d?)(?=[^0-9]|$)", re.IGNORECASE)


def _normalize_repo_path(value: str) -> str:
    return value.strip().replace("\\", "/").lstrip("./")


def _under(path: str, prefix: str) -> bool:
    prefix = _normalize_repo_path(prefix).rstrip("/") + "/"
    return path.startswith(prefix)


def _is_docs_path(path: str) -> bool:
    return path == "README.md" or path.startswith("docs/")


def _is_ci_governance_path(path: str) -> bool:
    return path in CI_GOVERNANCE_PATHS or any(_under(path, p) for p in CI_GOVERNANCE_PREFIXES)


def _is_ket_focused_path(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in KET_FOCUSED_PREFIXES)


def _unit_scope(path: str) -> str | None:
    match = _UNIT_TOKEN.search(path)
    if not match:
        return None
    return f"UNIT{int(match.group(1)):02d}"


def classify_changed_paths(
    changed_paths: Iterable[str],
    *,
    storage_prefixes: Iterable[str] = STORAGE_EVIDENCE_PREFIXES,
) -> dict[str, Any]:
    paths = sorted({_normalize_repo_path(p) for p in changed_paths if _normalize_repo_path(p)})
    storage = tuple(_normalize_repo_path(p).rstrip("/") + "/" for p in storage_prefixes)

    def is_storage(path: str) -> bool:
        return any(path.startswith(prefix) for prefix in storage)

    if not paths:
        return {
            "impact_scope": IMPACT_FULL,
            "changed_path_count": 0,
            "changed_paths": [],
            "reason": "empty_or_manual_scope_fails_safe_to_full",
        }

    if all(is_storage(path) for path in paths):
        return {
            "impact_scope": IMPACT_STORAGE_ONLY,
            "changed_path_count": len(paths),
            "changed_paths": paths,
            "reason": "all_paths_registered_storage_evidence",
        }

    if all(_is_ci_governance_path(path) for path in paths):
        return {
            "impact_scope": IMPACT_CI_GOVERNANCE,
            "changed_path_count": len(paths),
            "changed_paths": paths,
            "reason": "all_paths_ci_governance",
        }

    if all(_is_ket_focused_path(path) for path in paths) and any(not is_storage(path) for path in paths):
        return {
            "impact_scope": IMPACT_KET_FOCUSED,
            "changed_path_count": len(paths),
            "changed_paths": paths,
            "reason": "ket_data_plus_ket_focused_validation_surface",
        }

    if all(_is_docs_path(path) for path in paths):
        return {
            "impact_scope": IMPACT_DOCS_ONLY,
            "changed_path_count": len(paths),
            "changed_paths": paths,
            "reason": "ordinary_docs_only",
        }

    unit_by_path = {path: _unit_scope(path) for path in paths}
    units = {scope for scope in unit_by_path.values() if scope}
    non_unit_non_docs = [
        path for path, scope in unit_by_path.items()
        if scope is None and not _is_docs_path(path)
    ]
    if len(units) == 1 and not non_unit_non_docs:
        scope = next(iter(units))
        return {
            "impact_scope": scope,
            "changed_path_count": len(paths),
            "changed_paths": paths,
            "unit_scopes": sorted(units),
            "reason": "single_unit_impact",
        }

    return {
        "impact_scope": IMPACT_FULL,
        "changed_path_count": len(paths),
        "changed_paths": paths,
        "unit_scopes": sorted(units),
        "reason": "unknown_mixed_or_shared_scope_fails_safe_to_full",
    }


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
    return any(re.match(r"^\s{4}(paths|paths-ignore):\s*$", line) for line in event_block)


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

        if path.name == "english-db-ci-readback.yml":
            if "--classify-paths-file" not in text:
                errors.append("english_db_ci_missing_impact_classifier")
            if "CI_ROUTE=FULL" not in text:
                errors.append("english_db_ci_missing_explicit_full_route")
            if "CI_ROUTE=STORAGE_ONLY" not in text:
                errors.append("english_db_ci_missing_storage_route")
            if "CI_ROUTE=UNIT_FOCUSED" not in text:
                errors.append("english_db_ci_missing_unit_route")

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

    return {
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


def _write_github_output(path: Path, report: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"impact_scope={report['impact_scope']}\n")
        handle.write(f"impact_reason={report['reason']}\n")
        handle.write(f"changed_path_count={report['changed_path_count']}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate PR fan-out and classify CI impact.")
    parser.add_argument("--workflow-dir", type=Path, default=Path(".github/workflows"))
    parser.add_argument("--report", type=Path)
    parser.add_argument("--classify-paths-file", type=Path)
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()

    if args.classify_paths_file is not None:
        changed = args.classify_paths_file.read_text(encoding="utf-8").splitlines()
        report = classify_changed_paths(changed)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if args.github_output:
            _write_github_output(args.github_output, report)
        return 0

    report = validate_workflows(args.workflow_dir)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered + "\n", encoding="utf-8")
    return 0 if report["validation_status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
