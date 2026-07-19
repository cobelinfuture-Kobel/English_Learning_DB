#!/usr/bin/env python3
"""Shared learner-visible stimulus contract, answerability validator, and renderer.

This module is the single contract authority for learner-facing stimulus delivery
across A1FS V1 consumers. It does not score responses, mutate canonical language
authority, generate questions, or unlock A2 content.
"""
from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from typing import Any, Mapping, Sequence

TASK_ID = "A1FS-V1_SharedLearnerStimulusContractRenderer"
SCHEMA_VERSION = "a1fs.v1.shared_learner_stimulus_contract.v1"
STATUS = "PASS_A1FS_V1_SHARED_LEARNER_STIMULUS_CONTRACT_RENDERER"

DEPENDENCY_KINDS = {
    "TEXT", "DIALOGUE", "IMAGE", "AUDIO", "TABLE", "OPTIONS",
    "TOKENS", "MORPHEMES", "WORD_BANK", "GAP_DISPLAY",
}
RENDERER_TYPES = {
    "TEXT_PASSAGE", "DIALOGUE_TURNS", "IMAGE_ASSET", "AUDIO_PLAYER",
    "DATA_TABLE", "OPTION_LIST", "TOKEN_LIST", "MORPHEME_LIST",
    "WORD_BANK", "GAP_DISPLAY",
}

PROMPT_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "TEXT": (
        re.compile(r"文本|文章|短文|故事|段落|根據(?:本文|文章|短文|內容)|文中"),
        re.compile(r"\b(?:text|passage|paragraph|story)\b", re.I),
    ),
    "DIALOGUE": (
        re.compile(r"對話|交談|兩人說|人物說"),
        re.compile(r"\b(?:dialogue|conversation|speakers?)\b", re.I),
    ),
    "IMAGE": (
        re.compile(r"圖片|圖中|看圖|照片|插圖"),
        re.compile(r"\b(?:image|picture|photo|illustration)\b", re.I),
    ),
    "AUDIO": (
        re.compile(r"聽(?:完|到|音訊|錄音|對話)|音訊|錄音|播放"),
        re.compile(r"\b(?:listen|audio|recording|playback)\b", re.I),
    ),
    "TABLE": (
        re.compile(r"表格|圖表|資料表"),
        re.compile(r"\b(?:table|chart)\b", re.I),
    ),
}

KIND_RENDERER = {
    "TEXT": "TEXT_PASSAGE",
    "DIALOGUE": "DIALOGUE_TURNS",
    "IMAGE": "IMAGE_ASSET",
    "AUDIO": "AUDIO_PLAYER",
    "TABLE": "DATA_TABLE",
    "OPTIONS": "OPTION_LIST",
    "TOKENS": "TOKEN_LIST",
    "MORPHEMES": "MORPHEME_LIST",
    "WORD_BANK": "WORD_BANK",
    "GAP_DISPLAY": "GAP_DISPLAY",
}

CONTEXT_PATHS: tuple[tuple[str, str, str], ...] = (
    ("TEXT", "context.source_text", "TEXT_PASSAGE"),
    ("TEXT", "context.passage", "TEXT_PASSAGE"),
    ("TEXT", "context.text", "TEXT_PASSAGE"),
    ("TEXT", "context.paragraph", "TEXT_PASSAGE"),
    ("TEXT", "context.story", "TEXT_PASSAGE"),
    ("DIALOGUE", "context.dialogue", "DIALOGUE_TURNS"),
    ("DIALOGUE", "context.turns", "DIALOGUE_TURNS"),
    ("IMAGE", "context.image_ref", "IMAGE_ASSET"),
    ("IMAGE", "context.image_url", "IMAGE_ASSET"),
    ("IMAGE", "context.image_id", "IMAGE_ASSET"),
    ("AUDIO", "context.audio_ref", "AUDIO_PLAYER"),
    ("AUDIO", "context.audio_url", "AUDIO_PLAYER"),
    ("AUDIO", "context.audio_id", "AUDIO_PLAYER"),
    ("TABLE", "context.table", "DATA_TABLE"),
    ("TABLE", "context.rows", "DATA_TABLE"),
)

FIELD_DEPENDENCIES = (
    ("options", "OPTIONS", "OPTION_LIST"),
    ("supplied_tokens", "TOKENS", "TOKEN_LIST"),
    ("supplied_morphemes", "MORPHEMES", "MORPHEME_LIST"),
    ("word_bank", "WORD_BANK", "WORD_BANK"),
    ("gap_display_tokens", "GAP_DISPLAY", "GAP_DISPLAY"),
)


class StimulusContractError(ValueError):
    """Fail-closed learner answerability contract error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else value.encode("utf-8") if isinstance(value, str) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _nonempty(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Mapping):
        return bool(value) and any(_nonempty(child) for child in value.values())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return bool(value) and any(_nonempty(child) for child in value)
    return value is not None


def _get_path(value: Mapping[str, Any], path: str) -> Any:
    current: Any = value
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


def prompt_expected_kinds(prompt: Any) -> set[str]:
    text = str(prompt or "").strip()
    result: set[str] = set()
    for kind, patterns in PROMPT_PATTERNS.items():
        if any(pattern.search(text) for pattern in patterns):
            result.add(kind)
    return result


def _dependency(*, dependency_id: str, kind: str, payload_path: str, renderer_type: str, payload: Any, required: bool = True, delivery_state: str = "AVAILABLE") -> dict[str, Any]:
    if kind not in DEPENDENCY_KINDS or renderer_type not in RENDERER_TYPES:
        raise StimulusContractError(f"stimulus_dependency_type_invalid:{dependency_id}")
    return {
        "dependency_id": dependency_id,
        "kind": kind,
        "payload_path": payload_path,
        "renderer_type": renderer_type,
        "required": required,
        "visibility_required": True,
        "delivery_state": delivery_state,
        "payload_sha256": digest(payload) if _nonempty(payload) else None,
    }


def derive_dependencies(learner: Mapping[str, Any], *, media_payload_state: str = "NOT_REQUIRED") -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for kind, path, renderer in CONTEXT_PATHS:
        payload = _get_path(learner, path)
        if _nonempty(payload):
            key = (kind, path)
            if key not in seen:
                rows.append(_dependency(
                    dependency_id=f"DEP_{kind}_{len(rows)+1}", kind=kind,
                    payload_path=path, renderer_type=renderer, payload=payload,
                    delivery_state="DEFERRED_MEDIA_PAYLOAD" if kind == "AUDIO" and media_payload_state == "DEFERRED_MEDIA_PAYLOAD" else "AVAILABLE",
                ))
                seen.add(key)
    context = learner.get("context")
    if _nonempty(context) and not any(row["payload_path"].startswith("context.") for row in rows):
        rows.append(_dependency(
            dependency_id=f"DEP_TEXT_{len(rows)+1}", kind="TEXT",
            payload_path="context", renderer_type="TEXT_PASSAGE", payload=context,
        ))
    for field, kind, renderer in FIELD_DEPENDENCIES:
        payload = learner.get(field)
        if _nonempty(payload):
            rows.append(_dependency(
                dependency_id=f"DEP_{kind}_{len(rows)+1}", kind=kind,
                payload_path=field, renderer_type=renderer, payload=payload,
            ))
    rows.sort(key=lambda row: (row["kind"], row["payload_path"]))
    return rows


def build_render_manifest(learner: Mapping[str, Any], dependencies: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    manifest: list[dict[str, Any]] = []
    labels = {
        "TEXT": "情境／文本", "DIALOGUE": "對話", "IMAGE": "圖片", "AUDIO": "音訊",
        "TABLE": "表格", "OPTIONS": "選項", "TOKENS": "提供的單字",
        "MORPHEMES": "提供的字素", "WORD_BANK": "字詞庫", "GAP_DISPLAY": "填空句型",
    }
    for row in dependencies:
        payload = _get_path(learner, str(row["payload_path"]))
        manifest.append({
            "dependency_id": row["dependency_id"],
            "kind": row["kind"],
            "renderer_type": row["renderer_type"],
            "label": labels[row["kind"]],
            "payload_path": row["payload_path"],
            "payload": deepcopy(payload),
            "payload_sha256": digest(payload) if _nonempty(payload) else None,
            "delivery_state": row["delivery_state"],
        })
    return manifest


def validate_contract(*, item_id: str, learner: Mapping[str, Any], scoring: Mapping[str, Any], media_payload_state: str = "NOT_REQUIRED") -> dict[str, Any]:
    prompt = learner.get("prompt")
    dependencies = derive_dependencies(learner, media_payload_state=media_payload_state)
    actual_kinds = {row["kind"] for row in dependencies}
    expected_kinds = prompt_expected_kinds(prompt)
    errors: list[str] = []
    for kind in sorted(expected_kinds - actual_kinds):
        errors.append(f"REQUIRED_STIMULUS_MISSING:{kind}")
    for row in dependencies:
        payload = _get_path(learner, str(row["payload_path"]))
        if row.get("required") and not _nonempty(payload):
            errors.append(f"REQUIRED_STIMULUS_MISSING:{row['payload_path']}")
        if row.get("renderer_type") not in RENDERER_TYPES:
            errors.append(f"RENDERER_CAPABILITY_MISSING:{row.get('renderer_type')}")
        if row.get("delivery_state") == "DEFERRED_MEDIA_PAYLOAD":
            errors.append(f"MEDIA_PAYLOAD_DEFERRED:{row['dependency_id']}")
    if scoring.get("scoring_may_use_hidden_information") is True:
        errors.append("HIDDEN_SCORING_INFORMATION_FORBIDDEN")
    manifest = build_render_manifest(learner, dependencies)
    manifest_ids = {row["dependency_id"] for row in manifest}
    required_ids = {row["dependency_id"] for row in dependencies if row.get("required") and row.get("visibility_required")}
    if required_ids - manifest_ids:
        errors.append("LEARNER_SERIALIZATION_LOSS")
    if any(row.get("payload_sha256") != next((dep.get("payload_sha256") for dep in dependencies if dep.get("dependency_id") == row.get("dependency_id")), None) for row in manifest):
        errors.append("LEARNER_SERIALIZATION_HASH_MISMATCH")
    standalone = not dependencies and not expected_kinds
    validation = {
        "dependency_declared": standalone or bool(dependencies),
        "required_payload_present": not any(error.startswith("REQUIRED_STIMULUS_MISSING") for error in errors),
        "payload_nonempty": not any(error.startswith("REQUIRED_STIMULUS_MISSING") for error in errors),
        "renderer_supported": not any(error.startswith("RENDERER_CAPABILITY_MISSING") for error in errors),
        "serialization_preserved": not any(error.startswith("LEARNER_SERIALIZATION") for error in errors),
        "answerability_pass": not errors,
        "expected_dependency_kinds": sorted(expected_kinds),
        "actual_dependency_kinds": sorted(actual_kinds),
        "errors": errors,
    }
    contract_core = {
        "schema_version": SCHEMA_VERSION,
        "dependencies": dependencies,
        "answerability_policy": "STANDALONE_PROMPT" if standalone else "ALL_REQUIRED_DEPENDENCIES_VISIBLE",
        "scoring_may_use_hidden_information": False,
    }
    contract = {**contract_core, "contract_sha256": digest(contract_core)}
    return {
        "item_id": item_id,
        "stimulus_contract": contract,
        "stimulus_render_manifest": manifest,
        "stimulus_render_manifest_sha256": digest(manifest),
        "stimulus_validation": validation,
    }


def ensure_learner_contract(*, item_id: str, task_type: str, learner: Mapping[str, Any], scoring: Mapping[str, Any], media_payload_state: str = "NOT_REQUIRED") -> dict[str, Any]:
    del task_type  # reserved for future task-specific policy without changing callers
    result = validate_contract(
        item_id=item_id, learner=learner, scoring=scoring,
        media_payload_state=media_payload_state,
    )
    errors = result["stimulus_validation"]["errors"]
    if errors:
        raise StimulusContractError(f"learner_answerability_failed:{item_id}:" + "|".join(errors))
    value = deepcopy(dict(learner))
    value["stimulus_contract"] = result["stimulus_contract"]
    value["stimulus_render_manifest"] = result["stimulus_render_manifest"]
    value["stimulus_render_manifest_sha256"] = result["stimulus_render_manifest_sha256"]
    value["stimulus_validation"] = result["stimulus_validation"]
    return value


def scan_items(items: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    counters = {
        "total_items": 0, "standalone_items": 0, "text_dependent_items": 0,
        "dialogue_dependent_items": 0, "image_dependent_items": 0,
        "audio_dependent_items": 0, "table_dependent_items": 0,
        "dependency_undeclared": 0, "payload_missing": 0,
        "renderer_unsupported": 0, "serialization_loss": 0,
        "answerability_failed": 0, "media_deferred": 0,
        "ready_for_local_selection": 0,
    }
    failures: list[dict[str, Any]] = []
    for item in items:
        counters["total_items"] += 1
        learner = item.get("learner_contract")
        scoring = item.get("private_scoring_contract")
        item_id = str(item.get("item_id") or "")
        if not isinstance(learner, Mapping) or not isinstance(scoring, Mapping):
            counters["answerability_failed"] += 1
            failures.append({"item_id": item_id, "errors": ["SOURCE_ITEM_CONTRACT_MISSING"]})
            continue
        result = validate_contract(
            item_id=item_id, learner=learner, scoring=scoring,
            media_payload_state=str(item.get("media_payload_state") or "NOT_REQUIRED"),
        )
        kinds = set(result["stimulus_validation"]["actual_dependency_kinds"])
        if not kinds:
            counters["standalone_items"] += 1
        for kind, key in (
            ("TEXT", "text_dependent_items"), ("DIALOGUE", "dialogue_dependent_items"),
            ("IMAGE", "image_dependent_items"), ("AUDIO", "audio_dependent_items"),
            ("TABLE", "table_dependent_items"),
        ):
            if kind in kinds:
                counters[key] += 1
        errors = result["stimulus_validation"]["errors"]
        if any(error.startswith("REQUIRED_STIMULUS_MISSING") for error in errors):
            counters["payload_missing"] += 1
        if any(error.startswith("RENDERER_CAPABILITY_MISSING") for error in errors):
            counters["renderer_unsupported"] += 1
        if any(error.startswith("LEARNER_SERIALIZATION") for error in errors):
            counters["serialization_loss"] += 1
        if any(error.startswith("MEDIA_PAYLOAD_DEFERRED") for error in errors):
            counters["media_deferred"] += 1
        if errors:
            counters["answerability_failed"] += 1
            failures.append({"item_id": item_id, "errors": errors})
        else:
            counters["ready_for_local_selection"] += 1
    report_core = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": STATUS if not failures else "FAIL_A1FS_V1_LEARNER_ANSWERABILITY_SCAN",
        "counts": counters,
        "failures": failures,
    }
    return {**report_core, "report_sha256": digest(report_core)}


JS_RENDERER = r"""
function renderA1FSStimulus(container, learnerContract){
  const manifest=Array.isArray(learnerContract.stimulus_render_manifest)?learnerContract.stimulus_render_manifest:[];
  manifest.forEach(block=>{
    const section=document.createElement('section');section.className='stimulus';section.dataset.dependencyId=block.dependency_id||'';
    const title=document.createElement('strong');title.textContent=String(block.label||block.kind||'資料');section.appendChild(title);
    const payload=block.payload;
    if(block.renderer_type==='IMAGE_ASSET'){
      const img=document.createElement('img');img.alt=String((payload&&payload.alt)||'題目圖片');img.src=String((payload&&payload.url)||payload||'');section.appendChild(img);
    }else if(block.renderer_type==='AUDIO_PLAYER'){
      const audio=document.createElement('audio');audio.controls=true;audio.src=String((payload&&payload.url)||payload||'');section.appendChild(audio);
    }else if(['OPTION_LIST','TOKEN_LIST','MORPHEME_LIST','WORD_BANK','GAP_DISPLAY'].includes(block.renderer_type)){
      const values=Array.isArray(payload)?payload:[payload];const list=document.createElement('div');list.className='tokens';values.forEach(value=>{const span=document.createElement('span');span.textContent=String(value??'');list.appendChild(span)});section.appendChild(list);
    }else{
      const pre=document.createElement('pre');pre.textContent=typeof payload==='string'?payload:JSON.stringify(payload,null,2);section.appendChild(pre);
    }
    container.appendChild(section);
  });
}
"""
