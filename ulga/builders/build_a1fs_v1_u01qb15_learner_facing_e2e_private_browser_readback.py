#!/usr/bin/env python3
"""Governance-bound Edge-only entry point for the U01QB15 private browser readback."""
from __future__ import annotations

import argparse
import json
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


def _browser_finish_snapshot(cdp: Any) -> dict[str, Any]:
    """Read learner/browser and backend session state after a finish transition stalls.

    The learner UI catches API errors and writes only to ``#status``.  Without this
    readback a completion/abandon failure collapses into a generic wait timeout and
    hides the actual backend contract error.  This snapshot is acceptance-only and
    does not mutate learner state.
    """
    value = cdp.evaluate(
        """(async()=>{
          const safeApi=async path=>{
            try{return {ok:true,value:await api(path)}}
            catch(error){return {ok:false,error:String(error&&error.message||error)}}
          };
          const note=(document.querySelector('#lane-note')||{}).textContent||'';
          const match=note.match(/Form\s+(\d+)/);
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
            backend_active_session:await safeApi('/api/session/active'),
            backend_u01qb15_form:await safeApi('/api/u01qb15/form/active')
          };
        })()""",
        await_promise=True,
    )
    return dict(value) if isinstance(value, dict) else {"snapshot_invalid": value}


def _finish_active_with_diagnostics(cdp: Any, *, complete_session: bool) -> None:
    """Finish a browser session and surface the true async failure instead of timeout."""
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
# This changes only failure observability; the product API, session completion
# policy and learner state transitions remain authoritative in the existing runtime.
_impl._finish_active = _finish_active_with_diagnostics


def _fresh_run_output(requested: Path) -> Path:
    """Return a never-before-used sibling output path without touching stale browser state."""
    requested = Path(requested).resolve()
    requested.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(8):
        candidate = requested.with_name(
            f"{requested.name}.run-{uuid.uuid4().hex[:12]}"
        )
        if not candidate.exists():
            return candidate
    raise PrivateBrowserReadbackError("FRESH_DISPOSABLE_OUTPUT_ALLOCATION_FAILED")


def _run_with_fresh_replace(
    *,
    output_dir: Path,
    replace: bool,
    edge: Path | None,
    source_state_root: Path | None,
):
    """Use a fresh disposable output/profile whenever --replace is requested.

    A stale browser profile may still have Edge extension/background activity on
    Windows.  Deleting that live tree is inherently racy (WinError 3/145), so a
    replacement run never mutates or removes the previous output.  It allocates
    a fresh sibling directory and therefore a fresh Edge user-data-dir.
    """
    requested_output = Path(output_dir).resolve()
    actual_output = _fresh_run_output(requested_output) if replace else requested_output
    report = _impl.run_readback(
        output_dir=actual_output,
        replace=False,
        chromium_path=edge,
        source_state_root=source_state_root,
    )
    return report, actual_output


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--edge", type=Path)
    parser.add_argument("--source-state-root", type=Path)
    args = parser.parse_args(argv)
    try:
        report, actual_output = _run_with_fresh_replace(
            output_dir=args.output_dir,
            replace=args.replace,
            edge=args.edge,
            source_state_root=args.source_state_root,
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
    print(f"REPORT={actual_output / 'u01qb15_learner_facing_e2e_browser_readback.json'}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
