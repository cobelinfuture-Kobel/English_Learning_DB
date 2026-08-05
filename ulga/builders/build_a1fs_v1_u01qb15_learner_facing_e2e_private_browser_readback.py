#!/usr/bin/env python3
"""Governance-bound Edge-only entry point for the U01QB15 private browser readback."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Sequence

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Runs only a disposable-state Microsoft Edge acceptance over the already-approved U01QB15 learner product; it authors no canonical learner content or learner-state authority."

from ulga.builders import _a1fs_v1_u01qb15_edge_only_private_browser_fullfix as _edge  # noqa: E402
from ulga.builders import _a1fs_v1_u01qb15_learner_facing_e2e_private_browser_readback_impl as _impl  # noqa: E402
from ulga.builders._a1fs_v1_u01qb15_learner_facing_e2e_private_browser_readback_impl import *  # noqa: F401,F403,E402

# Runtime authority for this entry point is Edge only. The underlying reusable
# implementation still accepts a browser-path parameter, but both discovery and
# launch are replaced here so Chrome/Chromium cannot be selected accidentally.
_impl.chromium_support.discover_chromium = _edge.discover_edge_only
_impl._launch_chromium = _edge.launch_edge_only

WINDOWS_EXECUTION_ROOT_MAX = 96
WINDOWS_PROJECTED_PATH_MAX = 220
SHORT_EXECUTION_NAMESPACE = "a1u01"
M7_SNAPSHOT_NAME = "a1fs_v1_m7_mastery_snapshot.private.json"
EVIDENCE_NAMES = (
    "product.stdout.log",
    "product.stderr.log",
    "unit01_u01qb15_reading_form.png",
)


def _browser_finish_snapshot(cdp: Any) -> dict[str, Any]:
    """Read compact browser/backend finish state without dumping learner content."""
    value = cdp.evaluate(
        r"""(async()=>{
          const safeApi=async path=>{
            try{return {ok:true,value:await api(path)}}
            catch(error){return {ok:false,error:String(error&&error.message||error)}}
          };
          const compactSession=value=>{
            if(!value||value.active!==true)return {active:false};
            const session=value.session||{};
            return {active:true,session:{
              session_id:session.session_id||null,
              session_version:session.session_version??null,
              lesson_id:session.lesson_id||null,
              skill:session.skill||null,
              session_state:session.session_state||null
            },asset_count:Array.isArray(value.assets)?value.assets.length:0};
          };
          const compactForm=value=>{
            if(!value||value.active!==true)return {active:false};
            const form=value.form||{};
            const gate=value.completion_gate||{};
            return {active:true,form:{
              session_id:form.session_id||null,
              session_version:form.session_version??null,
              form_ordinal:form.form_ordinal??null,
              skill:form.skill||null,
              blueprint_activity_count:form.blueprint_activity_count??0
            },completion_gate:{
              completion_allowed:Boolean(gate.completion_allowed),
              required_response_count:gate.required_response_count??0,
              passed_response_count:gate.passed_response_count??0,
              pending_human_review_count:gate.pending_human_review_count??0,
              retry_required_count:gate.retry_required_count??0
            }};
          };
          const note=(document.querySelector('#lane-note')||{}).textContent||'';
          const match=note.match(/Form\s+(\d+)/);
          const rawSession=await safeApi('/api/session/active');
          const rawForm=await safeApi('/api/u01qb15/form/active');
          return {
            ui_status:(document.querySelector('#status')||{}).textContent||'',
            lane_note:note,
            form_ordinal:Number((match||[])[1]||0),
            complete_disabled:Boolean(complete&&complete.disabled),
            u01qb15_card_count:document.querySelectorAll('[data-u01qb15-item-id]').length,
            active:active?{
              session_id:active.session_id,
              session_version:active.session_version,
              lesson_id:active.lesson_id,
              skill:active.skill,
              session_state:active.session_state
            }:null,
            pending_resume:pendingResume?{
              session_id:pendingResume.session&&pendingResume.session.session_id,
              session_version:pendingResume.session&&pendingResume.session.session_version,
              lesson_id:pendingResume.session&&pendingResume.session.lesson_id,
              skill:pendingResume.session&&pendingResume.session.skill,
              session_state:pendingResume.session&&pendingResume.session.session_state
            }:null,
            backend_active_session:rawSession.ok?{ok:true,value:compactSession(rawSession.value)}:rawSession,
            backend_u01qb15_form:rawForm.ok?{ok:true,value:compactForm(rawForm.value)}:rawForm
          };
        })()""",
        await_promise=True,
    )
    return dict(value) if isinstance(value, dict) else {"snapshot_invalid": value}


def _finish_active_with_diagnostics(cdp: Any, *, complete_session: bool) -> None:
    """Finish a browser session and surface compact async failure evidence."""
    button = "complete" if complete_session else "abandon"
    action = "COMPLETE" if complete_session else "ABANDON"
    if complete_session:
        _impl._wait_eval(cdp, "active&&complete.disabled===false")

    before = _browser_finish_snapshot(cdp)
    cdp.evaluate(f"{button}.click();true")
    deadline = time.monotonic() + 20
    last_state: Any = None
    while time.monotonic() < deadline:
        try:
            last_state = cdp.evaluate(
                "({done:active===null&&pendingResume===null,"
                "active_session_id:active&&active.session_id,"
                "active_session_version:active&&active.session_version,"
                "pending_session_id:pendingResume&&pendingResume.session&&pendingResume.session.session_id,"
                "ui_status:(document.querySelector('#status')||{}).textContent||''})"
            )
            if isinstance(last_state, dict) and last_state.get("done") is True:
                return
        except _impl.PrivateBrowserReadbackError:
            pass
        time.sleep(0.1)

    after = _browser_finish_snapshot(cdp)
    diagnostic = {
        "action": action,
        "before": before,
        "after": after,
        "last_poll": last_state,
    }
    raise _impl.PrivateBrowserReadbackError(
        "SESSION_FINISH_STATE_NOT_CLEARED:"
        + json.dumps(diagnostic, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )


# All run_readback() finish/abandon calls now use the diagnostic-preserving path.
_impl._finish_active = _finish_active_with_diagnostics


def _fresh_run_output(requested: Path) -> Path:
    """Return a never-before-used sibling report output without deleting old evidence."""
    requested = Path(requested).resolve()
    requested.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(8):
        candidate = requested.with_name(
            f"{requested.name}.run-{uuid.uuid4().hex[:12]}"
        )
        if not candidate.exists():
            return candidate
    raise PrivateBrowserReadbackError("FRESH_REPORT_OUTPUT_ALLOCATION_FAILED")


def _projected_execution_paths(execution_output: Path) -> dict[str, Path]:
    """Project the deepest known learner/runtime paths before any private replay starts."""
    root = Path(execution_output)
    state = root / "disposable_state"
    learner_root = (
        state
        / "shared/learner_state/canonical_learning_state"
        / _impl.e2e.impl.base.DEFAULT_LEARNER_ID
    )
    return {
        "execution_root": root,
        "database": state / "shared/database/learner_runtime.sqlite3",
        "m7_snapshot": learner_root / "m7" / M7_SNAPSHOT_NAME,
        "edge_profile_root": root / "chromium_profile",
    }


def _assert_windows_path_budget(execution_output: Path) -> dict[str, int]:
    projected = _projected_execution_paths(execution_output)
    lengths = {name: len(str(path)) for name, path in projected.items()}
    if lengths["execution_root"] > WINDOWS_EXECUTION_ROOT_MAX:
        raise PrivateBrowserReadbackError(
            "WINDOWS_EXECUTION_ROOT_PATH_BUDGET_EXCEEDED:"
            f"{lengths['execution_root']}:{WINDOWS_EXECUTION_ROOT_MAX}:{projected['execution_root']}"
        )
    longest_name, longest_length = max(lengths.items(), key=lambda row: row[1])
    if longest_length > WINDOWS_PROJECTED_PATH_MAX:
        raise PrivateBrowserReadbackError(
            "WINDOWS_PROJECTED_PATH_BUDGET_EXCEEDED:"
            f"{longest_name}:{longest_length}:{WINDOWS_PROJECTED_PATH_MAX}:{projected[longest_name]}"
        )
    return lengths


def _fresh_short_execution_output(base_root: Path | None = None) -> tuple[Path, dict[str, int]]:
    """Allocate a short OS-temp execution root for disposable state and Edge profile."""
    root = (
        Path(base_root).resolve()
        if base_root is not None
        else (Path(tempfile.gettempdir()).resolve() / SHORT_EXECUTION_NAMESPACE)
    )
    root.mkdir(parents=True, exist_ok=True)
    for _ in range(8):
        candidate = root / f"r-{uuid.uuid4().hex[:8]}"
        if candidate.exists():
            continue
        lengths = _assert_windows_path_budget(candidate)
        return candidate, lengths
    raise PrivateBrowserReadbackError("FRESH_SHORT_EXECUTION_OUTPUT_ALLOCATION_FAILED")


def _copy_execution_evidence(
    execution_output: Path,
    report_output: Path,
    *,
    report: dict[str, Any] | None,
    path_lengths: dict[str, int],
) -> dict[str, Any] | None:
    """Copy compact evidence back to the repo-side report directory, never the disposable state."""
    execution_output = Path(execution_output)
    report_output = Path(report_output)
    report_output.mkdir(parents=True, exist_ok=True)
    for name in EVIDENCE_NAMES:
        source = execution_output / name
        if source.is_file():
            shutil.copy2(source, report_output / name)
    if report is None:
        return None
    copied = dict(report)
    chromium = dict(copied.get("chromium") or {})
    screenshot = dict(chromium.get("screenshot") or {})
    copied_screenshot = report_output / "unit01_u01qb15_reading_form.png"
    if copied_screenshot.is_file():
        screenshot["path"] = str(copied_screenshot)
    chromium["screenshot"] = screenshot
    copied["chromium"] = chromium
    copied["private_execution_path_budget"] = {
        "execution_root": str(execution_output),
        "report_output": str(report_output),
        "execution_root_max": WINDOWS_EXECUTION_ROOT_MAX,
        "projected_path_max": WINDOWS_PROJECTED_PATH_MAX,
        "projected_path_lengths": dict(path_lengths),
        "disposable_state_separated_from_report_output": True,
        "windows_max_path_margin_enforced": True,
    }
    (report_output / "u01qb15_learner_facing_e2e_browser_readback.json").write_text(
        json.dumps(copied, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return copied


def _run_with_fresh_replace(
    *,
    output_dir: Path,
    replace: bool,
    edge: Path | None,
    source_state_root: Path | None,
    execution_root: Path | None = None,
):
    requested_output = Path(output_dir).resolve()
    report_output = _fresh_run_output(requested_output) if replace else requested_output
    execution_output, path_lengths = _fresh_short_execution_output(execution_root)
    try:
        report = _impl.run_readback(
            output_dir=execution_output,
            replace=False,
            chromium_path=edge,
            source_state_root=source_state_root,
        )
    except Exception as exc:
        _copy_execution_evidence(
            execution_output,
            report_output,
            report=None,
            path_lengths=path_lengths,
        )
        raise PrivateBrowserReadbackError(
            f"{exc};EVIDENCE_OUTPUT={report_output};SHORT_EXECUTION_ROOT={execution_output}"
        ) from exc
    copied = _copy_execution_evidence(
        execution_output,
        report_output,
        report=dict(report),
        path_lengths=path_lengths,
    )
    if copied is None:
        raise PrivateBrowserReadbackError("COPIED_BROWSER_REPORT_MISSING")
    return copied, report_output, execution_output


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--edge", type=Path)
    parser.add_argument("--source-state-root", type=Path)
    parser.add_argument(
        "--execution-root",
        type=Path,
        help="Optional short base directory for disposable state and Edge profile; defaults to the OS temp directory.",
    )
    args = parser.parse_args(argv)
    try:
        report, actual_output, execution_output = _run_with_fresh_replace(
            output_dir=args.output_dir,
            replace=args.replace,
            edge=args.edge,
            source_state_root=args.source_state_root,
            execution_root=args.execution_root,
        )
    except Exception as exc:
        print("STATUS=FAIL_A1FS_V1_U01QB15_LEARNER_FACING_E2E_PRIVATE_BROWSER_READBACK")
        print(f"ERROR={exc}")
        return 1
    print(f"STATUS={report['status']}")
    print("BROWSER=MICROSOFT_EDGE")
    print(f"QUESTIONBANK_REVISION={report['source_authority']['questionbank_revision']}")
    print(f"RUNTIME_ITEMS={report['source_authority']['runtime_item_count']}")
    print(f"READING_FORM={report['reading']['initial_form_ordinal']}")
    print(f"READING_BLUEPRINT_CARDS={report['reading']['blueprint_card_count']}")
    print(f"READING_NEXT_FORM={report['reading']['next_form_ordinal']}")
    print(f"WRITING_FORM={report['writing']['form_ordinal']}")
    print(f"WRITING_OUTCOME={report['writing']['outcome']}")
    print(f"SPEAKING_FORM={report['speaking']['initial_form_ordinal']}")
    print(f"SPEAKING_BLUEPRINT_CARDS={report['speaking']['blueprint_card_count']}")
    print(f"SPEAKING_NEXT_FORM={report['speaking']['next_form_ordinal']}")
    print(f"SUPPORT_FILLER_EXPOSURES={report['disposable_runtime']['support_filler_exposure_count']}")
    print(f"CANONICAL_SOURCE_STATE_UNCHANGED={report['canonical_source_state_unchanged']}")
    print(f"REQUESTED_OUTPUT={Path(args.output_dir).resolve()}")
    print(f"ACTUAL_OUTPUT={actual_output}")
    print(f"SHORT_EXECUTION_ROOT={execution_output}")
    print(f"REPORT={actual_output / 'u01qb15_learner_facing_e2e_browser_readback.json'}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())