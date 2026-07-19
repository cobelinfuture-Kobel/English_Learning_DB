#!/usr/bin/env python3
"""Full-fix M12G learner-contract validation and learner-safe rendering.

This module wraps the existing M12G M3/M6/M7 orchestration. It does not alter
canonical authority, scoring answers, the frozen Asset Body packages, or the A2
lock. It rejects incomplete or ambiguous learner contracts before a private
reassessment package is created and renders every permitted learner-facing
stimulus field in the offline UI.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterator, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_e4s_a1v1_m12g_remediation_reassessment_execution as base  # noqa: E402
from ulga.builders import build_a1fs_v1_shared_learner_stimulus_contract_renderer as stimulus

TASK_ID = "E4S-A1V1-M12G_LearnerContractRenderingAndAssessmentValidityFullFix"
SCHEMA_VERSION = "e4s.a1v1.m12g.assessment_validity_fullfix.v1"
STATUS = "PASS_M12G_ASSESSMENT_VALIDITY_FULLFIX_READY"
REPORT_FILENAME = "m12g_assessment_validity_fullfix.safe.json"

ORDERED_MODES = {"ordered_tokens", "ordered_morphemes"}
CONTEXT_REQUIRED_TASKS = {
    "text_mode_writing_checkpoint",
    "context_choice",
}
BLANK_RE = re.compile(r"_{2,}|\[blank\]|<blank>|\{blank\}", re.IGNORECASE)


class AssessmentValidityError(base.ReassessmentError):
    """Fail-closed learner-visible assessment validity error."""


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _nonempty_string_list(value: Any, *, minimum: int = 1) -> bool:
    return (
        isinstance(value, list)
        and len(value) >= minimum
        and all(_nonempty_string(item) for item in value)
    )


def _visible_context(value: Any) -> bool:
    if not isinstance(value, Mapping) or not value:
        return False
    for child in value.values():
        if _nonempty_string(child):
            return True
        if _nonempty_string_list(child):
            return True
        if isinstance(child, Mapping) and _visible_context(child):
            return True
    return False


def _contract_fingerprint(contract: Mapping[str, Any]) -> str:
    learner_visible = {
        key: contract.get(key)
        for key in (
            "prompt",
            "response_mode",
            "context",
            "options",
            "supplied_tokens",
            "supplied_morphemes",
            "gap_display_tokens",
            "word_bank",
        )
        if key in contract
    }
    return base.digest(learner_visible)


def validate_learner_contract(
    *,
    item_id: str,
    task_type: str,
    learner: Mapping[str, Any],
    scoring: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate one learner-visible contract against its response semantics."""
    prompt = learner.get("prompt")
    if not _nonempty_string(prompt):
        raise AssessmentValidityError(f"learner_prompt_missing:{item_id}")

    response_mode = str(learner.get("response_mode") or "short_text")
    response_type = str(scoring.get("response_type") or "")
    context = learner.get("context")
    options = learner.get("options")
    supplied_tokens = learner.get("supplied_tokens")
    supplied_morphemes = learner.get("supplied_morphemes")
    gap_tokens = learner.get("gap_display_tokens")
    word_bank = learner.get("word_bank")

    if response_mode == "select_one":
        if not _nonempty_string_list(options, minimum=2):
            raise AssessmentValidityError(f"select_one_options_missing:{item_id}")
        if len(set(options)) != len(options):
            raise AssessmentValidityError(f"select_one_options_duplicate:{item_id}")
        accepted = scoring.get("accepted_texts")
        if not _nonempty_string_list(accepted):
            raise AssessmentValidityError(f"select_one_answer_contract_missing:{item_id}")
        if any(answer not in options for answer in accepted):
            raise AssessmentValidityError(f"select_one_answer_outside_options:{item_id}")
        if response_type != "string":
            raise AssessmentValidityError(f"select_one_response_type_invalid:{item_id}")

    elif response_mode == "ordered_tokens":
        if not _nonempty_string_list(supplied_tokens, minimum=2):
            raise AssessmentValidityError(f"ordered_tokens_stimulus_missing:{item_id}")
        accepted = scoring.get("accepted_sequence")
        if not _nonempty_string_list(accepted, minimum=2):
            raise AssessmentValidityError(f"ordered_tokens_answer_contract_missing:{item_id}")
        if Counter(supplied_tokens) != Counter(accepted):
            raise AssessmentValidityError(f"ordered_tokens_partition_mismatch:{item_id}")
        if response_type != "string_array":
            raise AssessmentValidityError(f"ordered_tokens_response_type_invalid:{item_id}")

    elif response_mode == "ordered_morphemes":
        if not _nonempty_string_list(supplied_morphemes, minimum=2):
            raise AssessmentValidityError(f"ordered_morphemes_stimulus_missing:{item_id}")
        accepted = scoring.get("accepted_sequence")
        if not _nonempty_string_list(accepted, minimum=2):
            raise AssessmentValidityError(f"ordered_morphemes_answer_contract_missing:{item_id}")
        if Counter(supplied_morphemes) != Counter(accepted):
            raise AssessmentValidityError(f"ordered_morphemes_partition_mismatch:{item_id}")
        if response_type != "string_array":
            raise AssessmentValidityError(f"ordered_morphemes_response_type_invalid:{item_id}")

    elif task_type == "structured_gap_fill":
        if not _nonempty_string_list(gap_tokens):
            raise AssessmentValidityError(f"gap_display_tokens_missing:{item_id}")
        rendered_gap = " ".join(gap_tokens)
        if not BLANK_RE.search(rendered_gap):
            raise AssessmentValidityError(f"gap_placeholder_missing:{item_id}")
        disambiguated = (
            _visible_context(context)
            or _nonempty_string_list(options, minimum=2)
            or _nonempty_string_list(word_bank, minimum=2)
        )
        if not disambiguated:
            raise AssessmentValidityError(f"gap_disambiguating_stimulus_missing:{item_id}")
        if response_type != "string":
            raise AssessmentValidityError(f"gap_response_type_invalid:{item_id}")

    else:
        prompt_requires_context = "for the situation" in str(prompt).casefold()
        feature_rubric = str(scoring.get("scoring_mode") or "") == "FEATURE_RUBRIC"
        if task_type in CONTEXT_REQUIRED_TASKS or feature_rubric or prompt_requires_context:
            if not _visible_context(context):
                raise AssessmentValidityError(f"context_stimulus_missing:{item_id}")
        if response_type != "string":
            raise AssessmentValidityError(f"short_text_response_type_invalid:{item_id}")

    safe_scoring = deepcopy(dict(scoring))
    try:
        safe_learner = stimulus.ensure_learner_contract(
  item_id=item_id,
  task_type=task_type,
  learner=deepcopy(dict(learner)),
  scoring=safe_scoring,
        )
    except stimulus.StimulusContractError as exc:
        raise AssessmentValidityError(str(exc)) from exc
    safe_learner["assessment_validity"] = {
        "status": "PASS",
        "response_mode": response_mode,
        "stimulus_complete": safe_learner["stimulus_validation"]["answerability_pass"],
        "shared_stimulus_contract_status": stimulus.STATUS,
    }
    return safe_learner, safe_scoring


def learner_item(item: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    learner = item.get("learner_contract")
    scoring = item.get("private_scoring_contract")
    item_id = str(item.get("item_id") or "")
    if not isinstance(learner, Mapping) or not isinstance(scoring, Mapping):
        raise AssessmentValidityError(f"source_item_contract_missing:{item_id}")
    return validate_learner_contract(
        item_id=item_id,
        task_type=str(item.get("task_type") or ""),
        learner=learner,
        scoring=scoring,
    )


def choose_source_items(
    source_item: Mapping[str, Any],
    bank_items: Mapping[str, Mapping[str, Any]],
    required_count: int,
) -> list[dict[str, Any]]:
    item_id = str(source_item.get("item_id") or "")
    grammar_unit = str(source_item.get("grammar_unit_id") or "")
    skill = str(source_item.get("skill") or "").casefold()
    candidates = [
        row
        for row in bank_items.values()
        if str(row.get("grammar_unit_id") or "") == grammar_unit
        and str(row.get("skill") or "").casefold() == skill
    ]
    candidates.sort(key=lambda row: (str(row.get("item_id")) == item_id, str(row.get("item_id"))))

    valid: list[dict[str, Any]] = []
    rejected: dict[str, str] = {}
    fingerprints: set[str] = set()
    for row in candidates:
        candidate_id = str(row.get("item_id") or "")
        try:
            learner, _ = learner_item(row)
        except AssessmentValidityError as exc:
            rejected[candidate_id] = str(exc).split(":", 1)[0]
            continue
        fingerprint = _contract_fingerprint(learner)
        if fingerprint in fingerprints:
            rejected[candidate_id] = "duplicate_learner_stimulus"
            continue
        fingerprints.add(fingerprint)
        valid.append(dict(row))

    if len(valid) < required_count:
        detail = ",".join(f"{key}={value}" for key, value in sorted(rejected.items()))
        raise AssessmentValidityError(
            f"valid_reassessment_items_insufficient:{item_id}:"
            f"required={required_count}:valid={len(valid)}:rejected={detail}"
        )
    return valid[:required_count]


def html_ui(package: Mapping[str, Any]) -> str:
    public_package = {
        "task_id": package["task_id"],
        "package_sha256": package["package_sha256"],
        "learner_id": package["learner_id"],
        "tasks": package["tasks"],
    }
    data = json.dumps(public_package, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang='zh-Hant'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>M12G 重新評量</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:920px;margin:0 auto;padding:24px;background:#f7f7f7;color:#1a1a1a}}
article{{background:white;border:1px solid #bbb;border-radius:8px;padding:18px;margin:16px 0}}
.stimulus{{background:#f3f5f7;border-left:4px solid #666;padding:12px;margin:12px 0;white-space:pre-wrap}}
.tokens span{{display:inline-block;border:1px solid #777;border-radius:5px;padding:5px 8px;margin:3px;background:white}}
textarea,select,input{{width:100%;box-sizing:border-box;padding:9px;margin:6px 0}}
.teacher{{border:1px dashed #777;margin-top:16px;padding:12px;background:#fafafa}}
.teacher label{{display:block;margin:7px 0}}
.teacher input[type=checkbox]{{width:auto;margin-right:8px}}
button{{padding:10px 18px;font-weight:600}}
.error{{color:#a00000;font-weight:600}}
</style>
</head>
<body>
<h1>M12G 重新評量</h1>
<p>請先完成學習者作答。標示為「教師審核」的區域由教師填寫。</p>
<div id='errors' class='error' aria-live='polite'></div>
<label>Reviewer ID（只有教師審核題需要）<input id='reviewer'></label>
<main id='root'></main>
<button id='save'>下載作答檔</button>
<script>
{stimulus.JS_RENDERER}
const pkg={data};
const root=document.getElementById('root');
const errorBox=document.getElementById('errors');
const text=(tag,value,className)=>{{const e=document.createElement(tag);e.textContent=String(value??'');if(className)e.className=className;return e}};
function addList(container,label,values,field){{
  if(!Array.isArray(values)||!values.length)return;
  container.appendChild(text('strong',label));
  const box=document.createElement('div');box.className='tokens';box.dataset.field=field;
  values.forEach(value=>box.appendChild(text('span',value)));
  container.appendChild(box);
}}
pkg.tasks.forEach((task,index)=>{{
  const contract=task.learner_contract||{{}};
  const article=document.createElement('article');article.dataset.taskId=task.task_instance_id;
  article.appendChild(text('h2',`${{index+1}}. ${{contract.prompt||''}}`));
  renderA1FSStimulus(article,contract);
  let control;
  if(contract.response_mode==='select_one'){{
    control=document.createElement('select');control.dataset.response='';
    const empty=document.createElement('option');empty.value='';empty.textContent='請選擇';control.appendChild(empty);
    (contract.options||[]).forEach(value=>{{const option=document.createElement('option');option.value=value;option.textContent=value;control.appendChild(option)}});
  }}else{{
    control=document.createElement('textarea');control.rows=3;control.dataset.response='';
    if((contract.response_mode||'').startsWith('ordered_'))control.placeholder='請依正確順序輸入，項目之間用 | 分隔';
  }}
  article.appendChild(control);
  if(task.human_review_required){{
    const fieldset=document.createElement('fieldset');fieldset.className='teacher';fieldset.dataset.review='';
    fieldset.appendChild(text('legend','教師審核'));
    const decision=document.createElement('select');decision.dataset.decision='';
    ['','APPROVE','REJECT','DEFER'].forEach(value=>{{const option=document.createElement('option');option.value=value;option.textContent=value||'請選擇審核結果';decision.appendChild(option)}});
    fieldset.appendChild(decision);
    [['grammar_target_match','目標文法正確'],['meaning_matches_context','意思符合情境'],['complete_response','回答完整']].forEach(([key,label])=>{{
      const wrapper=document.createElement('label');const checkbox=document.createElement('input');checkbox.type='checkbox';checkbox.dataset.criterion=key;wrapper.appendChild(checkbox);wrapper.appendChild(document.createTextNode(label));fieldset.appendChild(wrapper);
    }});
    article.appendChild(fieldset);
  }}
  root.appendChild(article);
}});
document.getElementById('save').onclick=()=>{{
  errorBox.textContent='';
  const now=new Date().toISOString();const reviewer=document.getElementById('reviewer').value.trim();
  const articles=[...root.querySelectorAll('article')];const errors=[];
  const attempts=pkg.tasks.map((task,index)=>{{
    const article=articles[index];const control=article.querySelector('[data-response]');const raw=control.value.trim();
    if(!raw)errors.push(`第 ${{index+1}} 題尚未作答`);
    const mode=task.learner_contract.response_mode||'';
    const response=mode.startsWith('ordered_')?raw.split('|').map(value=>value.trim()).filter(Boolean):raw;
    let operator_review=null;
    if(task.human_review_required){{
      const fieldset=article.querySelector('[data-review]');const decision=fieldset.querySelector('[data-decision]').value;
      const criteria=Object.fromEntries([...fieldset.querySelectorAll('[data-criterion]')].map(box=>[box.dataset.criterion,box.checked]));
      if(!reviewer)errors.push('教師審核題需要 Reviewer ID');
      if(!decision)errors.push(`第 ${{index+1}} 題尚未選擇教師審核結果`);
      if(decision==='APPROVE'&&!Object.values(criteria).every(Boolean))errors.push(`第 ${{index+1}} 題 APPROVE 時三項標準都必須通過`);
      operator_review={{decision,reviewer_id:reviewer,reviewed_at:now,criteria,notes:null}};
    }}
    return{{task_instance_id:task.task_instance_id,response,submitted_at:now,operator_review}};
  }});
  if(errors.length){{errorBox.textContent=[...new Set(errors)].join('；');return;}}
  const output={{task_id:pkg.task_id,schema_version:'{base.REGISTRY_SCHEMA_VERSION}',private_local_only:true,package_sha256:pkg.package_sha256,learner_id:pkg.learner_id,attempts}};
  const blob=new Blob([JSON.stringify(output,null,2)],{{type:'application/json'}});const link=document.createElement('a');link.href=URL.createObjectURL(blob);link.download='m12g_reassessment_response_registry.private.json';link.click();URL.revokeObjectURL(link.href);
}};
</script>
</body>
</html>"""


@contextmanager
def patched_base() -> Iterator[None]:
    originals = (base.learner_item, base.choose_source_items, base.html_ui)
    base.learner_item = learner_item
    base.choose_source_items = choose_source_items
    base.html_ui = html_ui
    try:
        yield
    finally:
        base.learner_item, base.choose_source_items, base.html_ui = originals


def prepare(**kwargs: Any) -> dict[str, Any]:
    with patched_base():
        result = base.prepare(**kwargs)
    package = base.read_json(result["package_path"], "package")
    tasks = package.get("tasks", [])
    if not isinstance(tasks, list) or not tasks:
        raise AssessmentValidityError("prepared_tasks_missing")
    for task in tasks:
        contract = task.get("learner_contract", {})
        if contract.get("assessment_validity", {}).get("status") != "PASS":
            raise AssessmentValidityError(f"prepared_task_not_valid:{task.get('task_instance_id')}")
    html_text = Path(result["html_path"]).read_text(encoding="utf-8")
    required_markers = ("gap_display_tokens", "supplied_tokens", "supplied_morphemes", "教師審核")
    if any(marker not in html_text for marker in required_markers):
        raise AssessmentValidityError("renderer_marker_missing")
    mode_counts = Counter(str(task.get("learner_contract", {}).get("response_mode") or "short_text") for task in tasks)
    report = dict(result["report"])
    report.update({
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": STATUS,
        "learner_contract_valid_count": len(tasks),
        "rendered_task_count": len(tasks),
        "response_mode_counts": dict(sorted(mode_counts.items())),
        "assessment_validity_gate": "PASS_FAIL_CLOSED",
        "legacy_incomplete_package_reusable": False,
    })
    report_path = Path(kwargs["target_root"]) / REPORT_FILENAME
    base.write_private(report_path, report)
    result["report"] = report
    result["report_path"] = report_path
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_cmd = commands.add_parser("prepare")
    for name in ("source-bank", "base-consumer", "base-graph", "source-database", "resolved-root", "m12e1-root", "output-root"):
        prepare_cmd.add_argument(f"--{name}", type=Path, required=True)
    prepare_cmd.add_argument("--learner-id", required=True)
    prepare_cmd.add_argument("--display-label", required=True)
    args = parser.parse_args(argv)
    try:
        result = prepare(
            source_bank_path=args.source_bank,
            base_consumer_path=args.base_consumer,
            base_graph_path=args.base_graph,
            source_database_path=args.source_database,
            resolved_root=args.resolved_root,
            m12e1_root=args.m12e1_root,
            learner_id=args.learner_id,
            display_label=args.display_label,
            target_root=args.output_root,
        )
        report = result["report"]
        print(json.dumps({
            "validation_status": report["validation_status"],
            "pending_node_count": report["pending_node_count"],
            "required_attempt_count": report["required_attempt_count"],
            "learner_contract_valid_count": report["learner_contract_valid_count"],
            "a2_lock_state": report["a2_lock_state"],
            "stop_reason": report["stop_reason"],
            "html": str(result["html_path"]),
            "package": str(result["package_path"]),
            "database": str(result["database_path"]),
            "report": str(result["report_path"]),
        }, ensure_ascii=False, sort_keys=True))
        return 0
    except (AssessmentValidityError, base.ReassessmentError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
