#!/usr/bin/env python3
"""Prepare a state-preserving M12G additional reassessment continuation batch.

This builder reads the current M12G database after real reassessment evidence has
already been imported. It preserves that evidence, computes the remaining pass
requirement from M7, cycles the existing Authority-reviewed task contracts, and
creates new task-instance identities only. Ordered responses use explicit token
selection in the offline UI; no free-text delimiter parsing is permitted.

It never rewrites prior outcomes, relaxes mastery policy, modifies canonical
Authority or graph content, or unlocks A2.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_e4s_a1v1_m12g_remediation_reassessment_execution as base  # noqa: E402
from ulga.builders import build_e4s_a1v1_m12g_learner_contract_assessment_validity_fullfix as fullfix  # noqa: E402

TASK_ID = "E4S-A1V1-M12G_AdditionalReassessmentContinuation"
SCHEMA_VERSION = "e4s.a1v1.m12g.additional_reassessment_continuation.v1"
STATUS = "PASS_M12G_ADDITIONAL_REASSESSMENT_CONTINUATION_READY"
PACKAGE_FILENAME = "m12g_additional_reassessment_package.private.json"
TEMPLATE_FILENAME = "m12g_additional_reassessment_response_template.private.json"
HTML_FILENAME = "m12g_additional_reassessment_ui.private.html"
REPORT_FILENAME = "m12g_additional_reassessment_prepare.safe.json"
EXPECTED_PENDING_NODES = 2
EXPECTED_ADDITIONAL_ATTEMPTS = 10
TOKEN_CAPTURE_CONTRACT = "TOKEN_SELECTION_ARRAY_V1"
PROHIBITED_DELIMITER_EXPRESSION = "split(" + chr(39) + "|" + chr(39) + ")"


class ContinuationError(base.ReassessmentError):
    """Fail-closed continuation preparation error."""


def _write(path: Path, value: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)
    os.chmod(path, 0o600)
    return path


def _load_bound_package(
    *, package_path: Path, consumer_path: Path, graph_path: Path, learner_id: str
) -> dict[str, Any]:
    package = base.read_json(
        base.local_path(package_path, "source_package"), "source_package"
    )
    base.require(
        package.get("schema_version"),
        base.PACKAGE_SCHEMA_VERSION,
        "source_package_schema",
    )
    base.require(package.get("learner_id"), learner_id, "source_package_learner")
    expected_hash = base.digest(
        {key: value for key, value in package.items() if key != "package_sha256"}
    )
    base.require(package.get("package_sha256"), expected_hash, "source_package_hash")
    base.require(
        package.get("source_consumer_sha256"),
        base.file_sha(consumer_path),
        "source_package_consumer_hash",
    )
    base.require(
        package.get("source_graph_sha256"),
        base.file_sha(graph_path),
        "source_package_graph_hash",
    )
    tasks = package.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise ContinuationError("source_package_tasks_invalid")
    task_ids = [str(row.get("task_instance_id") or "") for row in tasks]
    if any(not value for value in task_ids) or len(set(task_ids)) != len(task_ids):
        raise ContinuationError("source_package_task_identity_invalid")
    return package


def _validated_source_tasks(
    *, package: Mapping[str, Any], consumer: Mapping[str, Any]
) -> dict[str, list[dict[str, Any]]]:
    assets = {
        str(row.get("asset_key")): row
        for row in consumer.get("asset_records", [])
        if isinstance(row, Mapping)
    }
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in package["tasks"]:
        task = deepcopy(dict(row))
        node_id = str(task.get("node_id") or "")
        asset_key = str(task.get("asset_key") or "")
        if not node_id or asset_key not in assets:
            raise ContinuationError(
                f"source_task_asset_binding_invalid:{task.get('task_instance_id')}"
            )
        learner = task.get("learner_contract")
        if not isinstance(learner, Mapping):
            raise ContinuationError(
                f"source_task_learner_contract_missing:{task.get('task_instance_id')}"
            )
        if learner.get("assessment_validity", {}).get("status") != "PASS":
            raise ContinuationError(
                f"source_task_assessment_validity_missing:{task.get('task_instance_id')}"
            )
        response_mode = str(learner.get("response_mode") or "short_text")
        response_type = str(task.get("response_type") or "")
        if response_mode in fullfix.ORDERED_MODES:
            supplied = (
                learner.get("supplied_tokens")
                if response_mode == "ordered_tokens"
                else learner.get("supplied_morphemes")
            )
            if (
                response_type != "string_array"
                or not isinstance(supplied, list)
                or len(supplied) < 2
                or not all(
                    isinstance(value, str) and value.strip() for value in supplied
                )
            ):
                raise ContinuationError(
                    f"source_task_ordered_contract_invalid:{task.get('task_instance_id')}"
                )
        elif response_type != "string":
            raise ContinuationError(
                f"source_task_response_type_invalid:{task.get('task_instance_id')}"
            )
        grouped[node_id].append(task)
    for rows in grouped.values():
        rows.sort(
            key=lambda row: (
                int(row.get("attempt_order", 0)),
                str(row.get("task_instance_id")),
            )
        )
    return grouped


def _continuation_package(
    *,
    source_package: Mapping[str, Any],
    consumer: Mapping[str, Any],
    state: Mapping[str, Any],
    learner_id: str,
    consumer_path: Path,
    graph_path: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    pending = list(state.get("pending", []))
    base.require(
        len(pending), EXPECTED_PENDING_NODES, "continuation_pending_node_count"
    )
    states = {
        str(row.get("node_id")): row
        for row in state.get("snapshot", {}).get("node_states", [])
        if isinstance(row, Mapping)
    }
    source_by_node = _validated_source_tasks(
        package=source_package, consumer=consumer
    )
    tasks: list[dict[str, Any]] = []
    node_plan: list[dict[str, Any]] = []
    seed = base.digest(
        [
            source_package["package_sha256"],
            state.get("snapshot", {}).get("snapshot_id"),
            sorted(str(row.get("node_id")) for row in pending),
        ]
    )

    for queue in sorted(pending, key=lambda row: str(row.get("node_id"))):
        node_id = str(queue.get("node_id") or "")
        node_state = states.get(node_id)
        if not node_state:
            raise ContinuationError(f"continuation_node_state_missing:{node_id}")
        required = base.additional_passes_required(node_state)
        if required < 1:
            raise ContinuationError(
                f"continuation_node_needs_no_attempts:{node_id}"
            )
        source_tasks = source_by_node.get(node_id, [])
        if len(source_tasks) < 2:
            raise ContinuationError(
                f"continuation_source_task_partition_insufficient:{node_id}"
            )

        node_task_ids: list[str] = []
        for order in range(1, required + 1):
            source = source_tasks[(order - 1) % len(source_tasks)]
            task = deepcopy(source)
            task_id = "M12G_CONT_TASK:" + base.digest(
                [seed, node_id, source["task_instance_id"], order]
            )[:24]
            task.update(
                {
                    "task_instance_id": task_id,
                    "attempt_order": order,
                    "continuation_batch": TASK_ID,
                    "continuation_source_task_instance_id": source[
                        "task_instance_id"
                    ],
                    "continuation_cycle_index": order,
                }
            )
            tasks.append(task)
            node_task_ids.append(task_id)

        node_plan.append(
            {
                "node_id": node_id,
                "reassessment_id": str(queue.get("reassessment_id") or ""),
                "required_successful_attempt_count": required,
                "source_pass_count": int(node_state.get("pass_count", 0)),
                "source_fail_count": int(node_state.get("fail_count", 0)),
                "source_resolved_attempt_count": int(
                    node_state.get("resolved_attempt_count", 0)
                ),
                "source_pass_rate": float(node_state.get("pass_rate", 0.0)),
                "task_instance_ids": node_task_ids,
            }
        )

    tasks.sort(
        key=lambda row: (
            str(row["node_id"]),
            int(row["attempt_order"]),
            str(row["task_instance_id"]),
        )
    )
    if len(tasks) != EXPECTED_ADDITIONAL_ATTEMPTS:
        raise ContinuationError(
            "continuation_attempt_count_changed:"
            f"expected={EXPECTED_ADDITIONAL_ATTEMPTS}:actual={len(tasks)}"
        )
    if len({row["task_instance_id"] for row in tasks}) != len(tasks):
        raise ContinuationError("continuation_task_identity_collision")

    core = {
        "task_id": base.TASK_ID,
        "schema_version": base.PACKAGE_SCHEMA_VERSION,
        "private_local_only": True,
        "learner_id": learner_id,
        "pending_node_count": len(node_plan),
        "required_attempt_count": len(tasks),
        "node_plan": node_plan,
        "tasks": tasks,
        "source_consumer_sha256": base.file_sha(consumer_path),
        "source_graph_sha256": base.file_sha(graph_path),
        "continuation_contract": {
            "task_id": TASK_ID,
            "schema_version": SCHEMA_VERSION,
            "source_package_sha256": source_package["package_sha256"],
            "historical_outcomes_rewritten": False,
            "mastery_policy_relaxed": False,
            "new_authority_items_created": False,
            "ordered_response_capture": TOKEN_CAPTURE_CONTRACT,
        },
        "claim_boundaries": {
            "answer_material_included": False,
            "scoring_rubric_included": False,
            "a2_content_included": False,
            "public_delivery": False,
            "prior_evidence_modified": False,
        },
    }
    return {**core, "package_sha256": base.digest(core)}, node_plan


def html_ui(package: Mapping[str, Any]) -> str:
    public = {
        "task_id": package["task_id"],
        "package_sha256": package["package_sha256"],
        "learner_id": package["learner_id"],
        "tasks": package["tasks"],
    }
    data = json.dumps(public, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang='zh-Hant'>
<head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>M12G 追加重新評量</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:920px;margin:auto;padding:24px;background:#f7f7f7;color:#1a1a1a}}
article{{background:white;border:1px solid #bbb;border-radius:8px;padding:18px;margin:16px 0}}
.stimulus{{background:#f3f5f7;border-left:4px solid #666;padding:12px;white-space:pre-wrap}}
.token-bank,.token-answer{{min-height:48px;border:1px solid #888;border-radius:6px;padding:8px;margin:8px 0;background:#fff}}
.token-answer{{border-width:2px;background:#f8fbff}}
.token-button{{width:auto;margin:4px;padding:8px 12px;border:1px solid #555;border-radius:5px;background:#fff;cursor:pointer}}
textarea,select,input{{width:100%;box-sizing:border-box;padding:9px;margin:6px 0}}
.teacher{{border:1px dashed #777;margin-top:16px;padding:12px;background:#fafafa}}
.teacher label{{display:block;margin:7px 0}}.teacher input[type=checkbox]{{width:auto;margin-right:8px}}
.error{{color:#a00000;font-weight:600}}button{{padding:10px 18px;font-weight:600}}
</style></head>
<body><h1>M12G 追加重新評量</h1>
<p>排列題請依序點選單字；點選答案區中的單字可移回題目區。</p>
<div id='errors' class='error' aria-live='polite'></div>
<label>Reviewer ID（只有教師審核題需要）<input id='reviewer'></label>
<main id='root'></main><button id='save'>下載作答檔</button>
<script>
const pkg={data},root=document.getElementById('root'),errorBox=document.getElementById('errors');
const make=(tag,value,cls)=>{{const e=document.createElement(tag);if(value!==undefined)e.textContent=String(value);if(cls)e.className=cls;return e}};
function orderedControl(article,values){{
  const bank=make('div',undefined,'token-bank'),answer=make('div',undefined,'token-answer');
  bank.dataset.tokenBank='';answer.dataset.tokenAnswer='';article._ordered=[];
  const add=(container,value,index,selected)=>{{const b=make('button',value,'token-button');b.type='button';b.dataset.tokenIndex=String(index);b.onclick=()=>{{
    if(selected){{article._ordered=article._ordered.filter(x=>x.index!==index);add(bank,value,index,false);}}
    else{{article._ordered.push({{index,value}});add(answer,value,index,true);}}
    b.remove();
  }};container.appendChild(b)}};
  values.forEach((value,index)=>add(bank,value,index,false));
  article.appendChild(make('strong','可選單字'));article.appendChild(bank);
  article.appendChild(make('strong','你的排列答案'));article.appendChild(answer);
}}
pkg.tasks.forEach((task,index)=>{{
  const contract=task.learner_contract||{{}},article=make('article');article.dataset.taskId=task.task_instance_id;
  article.appendChild(make('h2',`${{index+1}}. ${{contract.prompt||''}}`));
  if(contract.context){{article.appendChild(make('strong','情境／資料'));article.appendChild(make('pre',JSON.stringify(contract.context,null,2),'stimulus'));}}
  const mode=contract.response_mode||'';
  if(mode==='ordered_tokens'||mode==='ordered_morphemes'){{
    const values=mode==='ordered_tokens'?(contract.supplied_tokens||[]):(contract.supplied_morphemes||[]);orderedControl(article,values);
  }}else if(mode==='select_one'){{
    const select=make('select');select.dataset.response='';const empty=make('option','請選擇');empty.value='';select.appendChild(empty);
    (contract.options||[]).forEach(value=>{{const o=make('option',value);o.value=value;select.appendChild(o)}});article.appendChild(select);
  }}else{{const area=make('textarea');area.rows=3;area.dataset.response='';article.appendChild(area)}}
  if(task.human_review_required){{
    const fieldset=make('fieldset',undefined,'teacher');fieldset.dataset.review='';fieldset.appendChild(make('legend','教師審核'));
    const decision=make('select');decision.dataset.decision='';['','APPROVE','REJECT','DEFER'].forEach(value=>{{const o=make('option',value||'請選擇審核結果');o.value=value;decision.appendChild(o)}});fieldset.appendChild(decision);
    [['grammar_target_match','目標文法正確'],['meaning_matches_context','意思符合情境'],['complete_response','回答完整']].forEach(([key,label])=>{{const w=make('label'),c=make('input');c.type='checkbox';c.dataset.criterion=key;w.appendChild(c);w.appendChild(document.createTextNode(label));fieldset.appendChild(w)}});article.appendChild(fieldset);
  }}
  root.appendChild(article);
}});
document.getElementById('save').onclick=()=>{{
  errorBox.textContent='';const reviewer=document.getElementById('reviewer').value.trim(),articles=[...root.querySelectorAll('article')],errors=[];
  const attempts=pkg.tasks.map((task,index)=>{{
    const article=articles[index],mode=task.learner_contract.response_mode||'';let response;
    if(mode==='ordered_tokens'||mode==='ordered_morphemes'){{
      response=(article._ordered||[]).map(row=>row.value);const expected=mode==='ordered_tokens'?(task.learner_contract.supplied_tokens||[]):(task.learner_contract.supplied_morphemes||[]);
      if(response.length!==expected.length)errors.push(`第 ${{index+1}} 題尚未完成全部單字排列`);
    }}else{{const raw=article.querySelector('[data-response]').value.trim();response=raw;if(!raw)errors.push(`第 ${{index+1}} 題尚未作答`);}}
    const submittedAt=new Date(Date.now()+index).toISOString();let operator_review=null;
    if(task.human_review_required){{const f=article.querySelector('[data-review]'),decision=f.querySelector('[data-decision]').value,criteria=Object.fromEntries([...f.querySelectorAll('[data-criterion]')].map(c=>[c.dataset.criterion,c.checked]));if(!reviewer)errors.push('教師審核題需要 Reviewer ID');if(!decision)errors.push(`第 ${{index+1}} 題尚未選擇教師審核結果`);if(decision==='APPROVE'&&!Object.values(criteria).every(Boolean))errors.push(`第 ${{index+1}} 題 APPROVE 時三項標準都必須通過`);operator_review={{decision,reviewer_id:reviewer,reviewed_at:submittedAt,criteria,notes:null}};}}
    return{{task_instance_id:task.task_instance_id,response,submitted_at:submittedAt,operator_review}};
  }});
  if(errors.length){{errorBox.textContent=[...new Set(errors)].join('；');return;}}
  const output={{task_id:pkg.task_id,schema_version:'{base.REGISTRY_SCHEMA_VERSION}',private_local_only:true,package_sha256:pkg.package_sha256,learner_id:pkg.learner_id,attempts}},blob=new Blob([JSON.stringify(output,null,2)],{{type:'application/json'}}),link=document.createElement('a');link.href=URL.createObjectURL(blob);link.download='m12g_additional_reassessment_response_registry.private.json';link.click();URL.revokeObjectURL(link.href);
}};
</script></body></html>"""


def prepare(
    *,
    source_package_path: Path,
    consumer_path: Path,
    graph_path: Path,
    database_path: Path,
    learner_id: str,
    target_root: Path,
) -> dict[str, Any]:
    target_root = base.output_root(target_root)
    consumer_path = base.local_path(consumer_path, "consumer")
    graph_path = base.local_path(graph_path, "graph")
    database_path = base.local_path(database_path, "database")
    consumer, graph = base.load_consumer_graph(consumer_path, graph_path)
    source_package = _load_bound_package(
        package_path=source_package_path,
        consumer_path=consumer_path,
        graph_path=graph_path,
        learner_id=learner_id,
    )
    before = base.file_sha(database_path)
    state = base.database_state(database_path, consumer_path, graph_path, learner_id)
    package, node_plan = _continuation_package(
        source_package=source_package,
        consumer=consumer,
        state=state,
        learner_id=learner_id,
        consumer_path=consumer_path,
        graph_path=graph_path,
    )

    package_path = _write(target_root / PACKAGE_FILENAME, package)
    template = {
        "task_id": base.TASK_ID,
        "schema_version": base.REGISTRY_SCHEMA_VERSION,
        "private_local_only": True,
        "package_sha256": package["package_sha256"],
        "learner_id": learner_id,
        "attempts": [
            {
                "task_instance_id": row["task_instance_id"],
                "response": None,
                "submitted_at": None,
                "operator_review": {
                    "decision": None,
                    "reviewer_id": None,
                    "reviewed_at": None,
                    "criteria": {
                        "grammar_target_match": None,
                        "meaning_matches_context": None,
                        "complete_response": None,
                    },
                    "notes": None,
                }
                if row["human_review_required"]
                else None,
            }
            for row in package["tasks"]
        ],
    }
    template_path = _write(target_root / TEMPLATE_FILENAME, template)
    html_path = target_root / HTML_FILENAME
    html_path.write_text(html_ui(package), encoding="utf-8")
    os.chmod(html_path, 0o600)

    ordered_count = sum(
        str(row.get("learner_contract", {}).get("response_mode"))
        in fullfix.ORDERED_MODES
        for row in package["tasks"]
    )
    report = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": STATUS,
        "pending_node_count": len(node_plan),
        "required_attempt_count": len(package["tasks"]),
        "required_attempt_count_by_node": {
            row["node_id"]: row["required_successful_attempt_count"]
            for row in node_plan
        },
        "source_state": {
            row["node_id"]: {
                "pass_count": row["source_pass_count"],
                "fail_count": row["source_fail_count"],
                "resolved_attempt_count": row["source_resolved_attempt_count"],
                "pass_rate": row["source_pass_rate"],
            }
            for row in node_plan
        },
        "ordered_task_count": ordered_count,
        "ordered_response_capture": TOKEN_CAPTURE_CONTRACT,
        "free_text_delimiter_parsing_used": False,
        "source_database_original_modified": base.file_sha(database_path) != before,
        "a2_lock_state": graph["a2_lock_contract"]["state"],
        "claim_boundaries": {
            "prior_outcome_rewritten": False,
            "mastery_policy_relaxed": False,
            "canonical_graph_modified": False,
            "a2_payload_access_granted": False,
            "retention_confirmed": False,
        },
        "stop_reason": "REAL_ADDITIONAL_REASSESSMENT_EVIDENCE_REQUIRED",
        "next_short_step": base.TASK_ID,
    }
    if report["source_database_original_modified"]:
        raise ContinuationError("source_database_modified_during_prepare")
    if report["a2_lock_state"] not in {"LOCKED", "LOCKED_BY_DESIGN"}:
        raise ContinuationError("a2_lock_state_invalid")
    html_text = html_path.read_text(encoding="utf-8")
    if PROHIBITED_DELIMITER_EXPRESSION in html_text:
        raise ContinuationError("ordered_ui_contract_invalid")
    required_markers = (
        "dataset.tokenBank",
        "dataset.tokenAnswer",
        "article._ordered",
    )
    if any(marker not in html_text for marker in required_markers):
        raise ContinuationError("ordered_ui_marker_missing")
    report_path = _write(target_root / REPORT_FILENAME, report)
    return {
        "report": report,
        "report_path": report_path,
        "package_path": package_path,
        "template_path": template_path,
        "html_path": html_path,
        "consumer_path": consumer_path,
        "graph_path": graph_path,
        "database_path": database_path,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-package", type=Path, required=True)
    parser.add_argument("--consumer", type=Path, required=True)
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--learner-id", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = prepare(
            source_package_path=args.source_package,
            consumer_path=args.consumer,
            graph_path=args.graph,
            database_path=args.database,
            learner_id=args.learner_id,
            target_root=args.output_root,
        )
        report = result["report"]
        print(
            json.dumps(
                {
                    "validation_status": report["validation_status"],
                    "pending_node_count": report["pending_node_count"],
                    "required_attempt_count": report["required_attempt_count"],
                    "required_attempt_count_by_node": report[
                        "required_attempt_count_by_node"
                    ],
                    "ordered_task_count": report["ordered_task_count"],
                    "ordered_response_capture": report[
                        "ordered_response_capture"
                    ],
                    "source_database_original_modified": report[
                        "source_database_original_modified"
                    ],
                    "a2_lock_state": report["a2_lock_state"],
                    "stop_reason": report["stop_reason"],
                    "package": str(result["package_path"]),
                    "html": str(result["html_path"]),
                    "database": str(result["database_path"]),
                    "report": str(result["report_path"]),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    except (
        ContinuationError,
        base.ReassessmentError,
        fullfix.AssessmentValidityError,
        OSError,
        sqlite3.Error,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
