#!/usr/bin/env python3
"""Independent readback checks for R7 route-batch evidence intake outputs."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from ulga.builders import build_a1fs_v1_r7_route_batch_execution_and_replay_closure as r7

def main() -> int:
    p=argparse.ArgumentParser()
    for name in ("intake","intake-safe","session","session-safe","replay"):
        p.add_argument("--"+name, type=Path, required=True)
    a=p.parse_args(); values=[r7.read_json(getattr(a,n.replace('-','_'))) for n in ("intake","intake-safe","session","session-safe","replay")]
    intake,safe,session,session_safe,replay=values; errors=[]
    checks=((intake,"intake_sha256"),(safe,"report_sha256"),(session,"manifest_sha256"),(session_safe,"report_sha256"),(replay,"replay_sha256"))
    for value,field in checks:
        core={k:v for k,v in value.items() if k!=field}
        if value.get(field)!=r7.digest(core): errors.append(f"digest_invalid:{field}")
    try: r7.safe_scan(safe); r7.safe_scan(session_safe)
    except r7.ExecutionError as exc: errors.append(str(exc))
    rows=intake.get("classifications",[]); batches=session.get("session_batches",[])
    if len(rows)!=209 or intake.get("counts",{}).get("work_item_count")!=209: errors.append("planner_denominator_invalid")
    if len({row.get("work_item_id") for row in rows})!=209: errors.append("work_identity_invalid")
    if any(len(row.get("work_item_ids",[]))!=1 for row in batches): errors.append("unsafe_batch_capacity")
    if intake.get("counts",{}).get("synthetic_evidence_count")!=0: errors.append("synthetic_evidence_detected")
    if session.get("remaining_work_item_count")!=len(batches): errors.append("remaining_batch_count_drift")
    if safe.get("a2_unlocked") is not False or session_safe.get("a2_unlocked") is not False: errors.append("a2_lock_broken")
    result={"validation_status":r7.STATUS if not errors else "FAIL_R7_ROUTE_BATCH_EXECUTION_VALIDATION",
            "error_count":len(errors),"errors":errors,"work_item_count":len(rows),"session_batch_count":len(batches)}
    print(json.dumps(result,indent=2)); return 0 if not errors else 1
if __name__=="__main__": raise SystemExit(main())
