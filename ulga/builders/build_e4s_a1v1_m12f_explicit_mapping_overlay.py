#!/usr/bin/env python3
"""Build a private, fail-closed M12F mapping overlay for frozen A1FS consumers."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6  # noqa: E402
from ulga.builders import build_e4s_a1v1_m08_text_mode_learner_session as m08  # noqa: E402
from ulga.builders import build_e4s_a1v1_m12f_m12e1_to_a1fs_remediation_bridge as bridge  # noqa: E402

TASK_ID = "E4S-A1V1-M12F_ExplicitMappingOverlay"
SCHEMA_VERSION = "e4s.a1v1.m12f.explicit_mapping_overlay.v3"
AUTHORITY_TASK_ID = "E4S-A1V1-M12F_ExplicitMappingAuthority"
AUTHORITY_SCHEMA_VERSION = "e4s.a1v1.m12f.explicit_mapping_authority.v1"
CANDIDATE_STATUS = "PASS_M12F_MAPPING_CANDIDATES_READY_FOR_OPERATOR_REVIEW"
CANDIDATE_BLOCKED_STATUS = "BLOCKED_M12F_MAPPING_CANDIDATE_EVIDENCE_INSUFFICIENT"
OVERLAY_STATUS = "PASS_M12F_EXPLICIT_MAPPING_OVERLAY_READY"
NEXT_SHORT_STEP = "E4S-A1V1-M12F_M12E1ResolvedEvidenceToA1FSRemediationBridge"
EXPECTED_COUNT = bridge.EXPECTED_ATTEMPTS
CAPTURE_ROLES = m6.CAPTURE_ROLES
CANDIDATE_REVIEW_STOP = "OPERATOR_MAPPING_SELECTION_REQUIRED"
CANDIDATE_EVIDENCE_STOP = "MAPPING_CANDIDATE_EVIDENCE_REQUIRED"

STOP_TOKENS = {
    "grammar", "a1", "a1plus", "tfx", "basic", "item", "practice",
    "assessment", "reading", "writing", "the", "and", "for", "with",
    "from", "this", "that", "be", "place",
}
TASK_MARKERS = {
    "form_choice": {"choose", "choice", "option", "select"},
    "context_choice": {"choose", "choice", "option", "select"},
    "structured_gap_fill": {"blank", "cloze", "complete", "fill", "gap", "missing"},
    "text_mode_writing_checkpoint": {"phrase", "produce", "production", "sentence", "write"},
}
TOKEN_VARIANTS = {
    "adjective": {"adjective", "adjectives"},
    "adverb": {"adverb", "adverbs"},
    "article": {"article", "articles"},
    "articles": {"article", "articles"},
    "interrogative": {"interrogative", "interrogatives"},
    "interrogatives": {"interrogative", "interrogatives"},
    "phrase": {"phrase", "phrases"},
    "phrases": {"phrase", "phrases"},
    "preposition": {"preposition", "prepositions"},
    "prepositions": {"preposition", "prepositions"},
}

# Only fields that describe the actual learner task, answer, or acceptance rule may
# prove content equivalence. Source passages and operational routing text are
# intentionally excluded because real-package review showed they create false hits.
EVIDENCE_ROOT_KEYS = {
    "mode", "body_title", "body_text", "prompt", "question", "questions",
    "instruction", "instructions", "task", "tasks", "items", "options",
    "answer", "answers", "acceptable_answer", "acceptable_answers",
    "acceptable_evidence", "rationale", "rubric", "acceptance_rule",
    "expected_evidence", "pass_rule", "response_mode", "task_type",
}
EVIDENCE_DENY_KEYS = {
    "unseen_text", "source_text", "passage", "transcript", "text", "text_ref",
    "context", "critical_failure", "diagnostic_route", "teacher_delivery",
    "scaffold_and_fade", "private_scoring_contract", "body",
}


class OverlayError(ValueError):
    """Fail-closed explicit mapping overlay error."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def canonical_sha(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise OverlayError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise OverlayError(f"{code}_not_object")
    return value


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    os.chmod(path, 0o600)


def safe_local_root(path: Path) -> Path:
    resolved = path.resolve()
    approved = (REPO_ROOT / ".local").resolve()
    if not resolved.is_relative_to(approved):
        raise OverlayError(f"path_outside_local:{resolved}")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def safe_local_file(path: Path, code: str) -> Path:
    resolved = path.resolve()
    approved = (REPO_ROOT / ".local").resolve()
    if not resolved.is_relative_to(approved):
        raise OverlayError(f"{code}_outside_local:{resolved}")
    if not resolved.is_file():
        raise OverlayError(f"{code}_missing:{resolved}")
    return resolved


def require(actual: Any, expected: Any, code: str) -> None:
    if actual != expected:
        raise OverlayError(f"{code}:expected={expected!r}:actual={actual!r}")


def load_sources(source_bank_path: Path, consumer_path: Path, graph_path: Path) -> dict[str, Any]:
    bank = read_json(source_bank_path, "source_bank")
    consumer = read_json(consumer_path, "consumer")
    graph = read_json(graph_path, "graph")
    require(bank.get("task_id"), m08.TASK_ID, "bank_task")
    require(bank.get("schema_version"), m08.SESSION_SCHEMA_VERSION, "bank_schema")
    require(consumer.get("validation_status"), bridge.CONSUMER_STATUS, "consumer_status")
    require(graph.get("validation_status"), bridge.GRAPH_STATUS, "graph_status")
    require(consumer.get("source_graph_sha256"), file_sha(graph_path), "consumer_graph_hash")
    items = bank.get("items")
    assets = consumer.get("asset_records")
    if not isinstance(items, list) or not isinstance(assets, list):
        raise OverlayError("source_arrays_invalid")
    by_item = {str(row.get("item_id")): row for row in items if isinstance(row, Mapping)}
    if len(by_item) < EXPECTED_COUNT:
        raise OverlayError("source_bank_item_count_invalid")
    return {
        "bank": bank,
        "bank_hash": m08.sha256_value(bank),
        "consumer": consumer,
        "consumer_hash": file_sha(consumer_path),
        "graph": graph,
        "graph_hash": file_sha(graph_path),
        "items_by_id": by_item,
        "assets": assets,
    }


def required_coverage(graph: Mapping[str, Any]) -> dict[str, set[str]]:
    required = set(graph.get("a2_lock_contract", {}).get("required_mastery_node_ids", []))
    covered: dict[str, set[str]] = {}
    for row in graph.get("coverage", []):
        node_id = str(row.get("node_id") or "")
        if node_id not in required:
            continue
        for asset_id in row.get("asset_body_ids", []):
            covered.setdefault(str(asset_id), set()).add(node_id)
    return covered


def normalize_text(value: str) -> str:
    value = value.casefold().replace("_", " ").replace("-", " ")
    value = re.sub(r"[^a-z0-9']+", " ", value)
    return " ".join(value.split())


def concept_tokens(item: Mapping[str, Any]) -> set[str]:
    raw = " ".join((str(item.get("item_id") or ""), str(item.get("grammar_unit_id") or "")))
    tokens = set(re.findall(r"[a-z]+", raw.casefold()))
    return {token for token in tokens if token not in STOP_TOKENS and len(token) > 1}


def target_anchor_phrases(item: Mapping[str, Any]) -> list[str]:
    contract = item.get("private_scoring_contract")
    values: list[str] = []
    if isinstance(contract, Mapping):
        for key in ("accepted_texts", "model_texts"):
            raw = contract.get(key)
            if isinstance(raw, list):
                values.extend(str(value) for value in raw if isinstance(value, str))
    anchors: set[str] = set()
    for value in values:
        normalized = normalize_text(value)
        if len(normalized) >= 6 and len(re.findall(r"[a-z0-9']+", normalized)) >= 2:
            anchors.add(normalized)
    return sorted(anchors)


def token_present(token: str, words: set[str]) -> bool:
    return bool(TOKEN_VARIANTS.get(token, {token}) & words)


def task_markers(item: Mapping[str, Any]) -> set[str]:
    return TASK_MARKERS.get(str(item.get("task_type") or ""), set())


def evidence_strings(value: Any, allowed: bool = False) -> list[str]:
    found: list[str] = []
    if isinstance(value, str):
        if allowed:
            found.append(value)
        return found
    if isinstance(value, list):
        if allowed:
            for child in value:
                found.extend(evidence_strings(child, True))
        return found
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            key = str(raw_key).casefold()
            if key in EVIDENCE_DENY_KEYS:
                continue
            child_allowed = allowed or key in EVIDENCE_ROOT_KEYS
            found.extend(evidence_strings(child, child_allowed))
    return found


def content_equivalence_evidence(asset: Mapping[str, Any], source_item: Mapping[str, Any]) -> dict[str, Any]:
    payload = asset.get("payload")
    scoped_strings = evidence_strings(payload)
    text = normalize_text(" ".join(scoped_strings))
    words = set(re.findall(r"[a-z0-9']+", text))

    concepts = sorted(concept_tokens(source_item))
    matched_concepts = sorted(token for token in concepts if token_present(token, words))
    concept_complete = bool(concepts) and len(matched_concepts) == len(concepts)

    anchors = target_anchor_phrases(source_item)
    matched_anchors = sorted(anchor for anchor in anchors if anchor in text)

    markers = sorted(task_markers(source_item))
    matched_markers = sorted(marker for marker in markers if marker in words)
    task_shape_match = bool(markers) and bool(matched_markers)

    approved = bool(matched_anchors) or (concept_complete and task_shape_match)
    reasons: list[str] = []
    if matched_anchors:
        reasons.append("EXACT_TARGET_ANCHOR")
    if concept_complete:
        reasons.append("GRAMMAR_CONCEPT_COMPLETE")
    if task_shape_match:
        reasons.append("TASK_SHAPE_MARKER")
    if not approved:
        reasons.append("CONTENT_EQUIVALENCE_UNPROVEN")

    score = len(matched_anchors) * 100 + len(matched_concepts) * 20 + len(matched_markers) * 5
    return {
        "approved": approved,
        "score": score,
        "evidence_field_scope": "TASK_ANSWER_ACCEPTANCE_ONLY",
        "evidence_string_count": len(scoped_strings),
        "concept_tokens": concepts,
        "matched_concept_tokens": matched_concepts,
        "target_anchor_count": len(anchors),
        "matched_target_anchor_count": len(matched_anchors),
        "matched_target_anchor_sha256": [
            hashlib.sha256(anchor.encode("utf-8")).hexdigest() for anchor in matched_anchors
        ],
        "task_markers": markers,
        "matched_task_markers": matched_markers,
        "reasons": reasons,
    }


def structural_contract(asset: Mapping[str, Any], source_item: Mapping[str, Any]) -> tuple[bool, str]:
    try:
        derived = m6.derive_contract(asset)
    except Exception:
        return False, "UNREADABLE"
    source = source_item.get("private_scoring_contract")
    if not isinstance(source, Mapping):
        return False, str(derived.get("scoring_mode") or "NONE")
    compatible = bool(derived.get("capture_enabled")) and derived.get("response_type") == source.get("response_type")
    source_mode = str(source.get("scoring_mode") or "")
    if source_mode == "FEATURE_RUBRIC":
        compatible = compatible and str(asset.get("role")) in {"PRD", "XFR", "EVD"}
    else:
        compatible = compatible and str(asset.get("role")) in CAPTURE_ROLES
    return compatible, str(derived.get("scoring_mode") or "NONE")


def build_candidate_report(source: Mapping[str, Any], item_ids: list[str], limit: int = 5) -> dict[str, Any]:
    if limit < 1 or limit > 20:
        raise OverlayError("candidate_limit_invalid")
    coverage = required_coverage(source["graph"])
    rows: list[dict[str, Any]] = []
    for item_id in sorted(item_ids):
        item = source["items_by_id"].get(item_id)
        if not item:
            raise OverlayError(f"candidate_item_missing:{item_id}")
        skill = str(item.get("skill") or "").upper()
        source_contract = item.get("private_scoring_contract") or {}
        candidates: list[dict[str, Any]] = []
        structurally_compatible_count = 0
        rejected_content_equivalence_count = 0
        for asset in source["assets"]:
            if asset.get("level") not in {"A1", "A1+"}:
                continue
            if str(asset.get("skill") or "").upper() != skill:
                continue
            node_ids = sorted(coverage.get(str(asset.get("asset_id")), set()))
            if not node_ids:
                continue
            compatible, existing_mode = structural_contract(asset, item)
            if not compatible:
                continue
            structurally_compatible_count += 1
            evidence = content_equivalence_evidence(asset, item)
            if not evidence["approved"]:
                rejected_content_equivalence_count += 1
                continue
            candidates.append({
                "asset_key": str(asset.get("asset_key")),
                "asset_id": str(asset.get("asset_id")),
                "lesson_id": str(asset.get("lesson_id")),
                "level": str(asset.get("level")),
                "role": str(asset.get("role")),
                "existing_scoring_mode": existing_mode,
                "source_scoring_mode": str(source_contract.get("scoring_mode") or ""),
                "content_equivalence_score": evidence["score"],
                "content_equivalence_evidence": evidence,
                "required_node_ids": node_ids,
            })
        candidates.sort(key=lambda row: (
            -row["content_equivalence_score"], row["lesson_id"], row["role"], row["asset_key"]
        ))
        rows.append({
            "item_id": item_id,
            "skill": skill,
            "grammar_unit_id": str(item.get("grammar_unit_id") or ""),
            "concept_tokens": sorted(concept_tokens(item)),
            "target_anchor_count": len(target_anchor_phrases(item)),
            "task_markers": sorted(task_markers(item)),
            "structurally_compatible_count": structurally_compatible_count,
            "rejected_content_equivalence_count": rejected_content_equivalence_count,
            "candidate_count": len(candidates),
            "top_candidates": candidates[:limit],
        })
    blocked_item_ids = [row["item_id"] for row in rows if row["candidate_count"] == 0]
    ready = not blocked_item_ids
    return {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": CANDIDATE_STATUS if ready else CANDIDATE_BLOCKED_STATUS,
        "source_session_bank_sha256": source["bank_hash"],
        "source_consumer_sha256": source["consumer_hash"],
        "source_graph_sha256": source["graph_hash"],
        "item_count": len(rows),
        "blocked_item_ids": blocked_item_ids,
        "items": rows,
        "claim_boundaries": {
            "operator_mapping_approved": False,
            "consumer_overlay_written": False,
            "frozen_package_modified": False,
            "canonical_graph_modified": False,
            "canonical_authority_write": False,
            "a2_content_promoted": False,
        },
        "stop_reason": CANDIDATE_REVIEW_STOP if ready else CANDIDATE_EVIDENCE_STOP,
        "next_short_step": TASK_ID,
    }


def load_authority(path: Path, source: Mapping[str, Any], item_ids: list[str]) -> dict[str, str]:
    authority_path = safe_local_file(path, "mapping_authority")
    authority = read_json(authority_path, "mapping_authority")
    require(authority.get("task_id"), AUTHORITY_TASK_ID, "authority_task")
    require(authority.get("schema_version"), AUTHORITY_SCHEMA_VERSION, "authority_schema")
    require(authority.get("approval_state"), "OPERATOR_APPROVED", "authority_approval")
    require(authority.get("source_session_bank_sha256"), source["bank_hash"], "authority_bank_hash")
    require(authority.get("source_consumer_sha256"), source["consumer_hash"], "authority_consumer_hash")
    require(authority.get("source_graph_sha256"), source["graph_hash"], "authority_graph_hash")
    mappings = authority.get("mappings")
    if not isinstance(mappings, list) or len(mappings) != len(item_ids):
        raise OverlayError("authority_mapping_count_invalid")
    by_item: dict[str, str] = {}
    used_assets: set[str] = set()
    for row in mappings:
        if not isinstance(row, Mapping):
            raise OverlayError("authority_mapping_row_invalid")
        item_id = str(row.get("item_id") or "")
        asset_key = str(row.get("asset_key") or "")
        require(row.get("evidence_basis"), "OPERATOR_REVIEWED_CONTENT_EQUIVALENCE", "authority_evidence_basis")
        if not item_id or not asset_key or item_id in by_item:
            raise OverlayError("authority_mapping_identity_invalid")
        if asset_key in used_assets:
            raise OverlayError(f"authority_asset_reused:{asset_key}")
        by_item[item_id] = asset_key
        used_assets.add(asset_key)
    expected = set(item_ids)
    if set(by_item) != expected:
        raise OverlayError(
            f"authority_item_partition_invalid:missing={sorted(expected-set(by_item))}:"
            f"extra={sorted(set(by_item)-expected)}"
        )
    return by_item


def build_overlay(source: Mapping[str, Any], item_ids: list[str], authority_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    mapping = load_authority(authority_path, source, item_ids)
    coverage = required_coverage(source["graph"])
    assets_by_key = {str(row.get("asset_key")): row for row in source["assets"]}
    overlay = deepcopy(source["consumer"])
    overlay_assets = {str(row.get("asset_key")): row for row in overlay["asset_records"]}
    authority_hash = file_sha(authority_path)
    mapped_rows: list[dict[str, Any]] = []
    for item_id in sorted(item_ids):
        asset_key = mapping[item_id]
        original = assets_by_key.get(asset_key)
        asset = overlay_assets.get(asset_key)
        item = source["items_by_id"].get(item_id)
        if original is None or asset is None or item is None:
            raise OverlayError(f"authority_target_missing:{item_id}:{asset_key}")
        if original.get("level") not in {"A1", "A1+"}:
            raise OverlayError(f"authority_target_a2_locked:{item_id}:{asset_key}")
        if str(original.get("skill") or "").casefold() != str(item.get("skill") or "").casefold():
            raise OverlayError(f"authority_skill_mismatch:{item_id}:{asset_key}")
        node_ids = sorted(coverage.get(str(original.get("asset_id")), set()))
        if not node_ids:
            raise OverlayError(f"authority_target_not_required_coverage:{item_id}:{asset_key}")
        source_contract = item.get("private_scoring_contract")
        if not isinstance(source_contract, Mapping):
            raise OverlayError(f"source_scoring_contract_missing:{item_id}")
        role = str(original.get("role") or "")
        if role not in CAPTURE_ROLES:
            raise OverlayError(f"authority_target_not_capture_role:{item_id}:{asset_key}:{role}")
        if source_contract.get("scoring_mode") == "FEATURE_RUBRIC" and role not in {"PRD", "XFR", "EVD"}:
            raise OverlayError(f"authority_feature_rubric_role_invalid:{item_id}:{asset_key}:{role}")
        compatible, _ = structural_contract(original, item)
        if not compatible:
            raise OverlayError(f"authority_target_structural_contract_invalid:{item_id}:{asset_key}")
        evidence = content_equivalence_evidence(original, item)
        if not evidence["approved"]:
            raise OverlayError(f"authority_target_content_equivalence_unproven:{item_id}:{asset_key}")
        payload = asset.get("payload")
        if not isinstance(payload, dict):
            raise OverlayError(f"authority_target_payload_invalid:{item_id}:{asset_key}")
        payload["m12_item_id"] = item_id
        payload["m12_session_bank_sha256"] = source["bank_hash"]
        payload["private_scoring_contract"] = deepcopy(dict(source_contract))
        payload["response_capture_enabled"] = True
        payload["m12_mapping_authority_sha256"] = authority_hash
        payload["m12_mapping_evidence_basis"] = "OPERATOR_REVIEWED_CONTENT_EQUIVALENCE"
        asset["content_digest"] = canonical_sha(payload)
        drift = bridge._contract_drift(asset, item)
        if drift:
            raise OverlayError(f"overlay_contract_drift:{item_id}:{asset_key}:{','.join(drift)}")
        mapped_rows.append({
            "item_id": item_id,
            "asset_key": asset_key,
            "asset_id": str(asset["asset_id"]),
            "lesson_id": str(asset["lesson_id"]),
            "skill": str(asset["skill"]),
            "level": str(asset["level"]),
            "role": str(asset["role"]),
            "required_node_ids": node_ids,
            "content_equivalence_evidence": evidence,
        })
    overlay["m12f_explicit_mapping_overlay"] = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "source_consumer_sha256": source["consumer_hash"],
        "source_session_bank_sha256": source["bank_hash"],
        "mapping_authority_sha256": authority_hash,
        "mapped_count": len(mapped_rows),
        "private_local_only": True,
    }
    report = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": OVERLAY_STATUS,
        "source_session_bank_sha256": source["bank_hash"],
        "source_consumer_sha256": source["consumer_hash"],
        "source_graph_sha256": source["graph_hash"],
        "mapping_authority_sha256": authority_hash,
        "mapped_count": len(mapped_rows),
        "mapped": mapped_rows,
        "claim_boundaries": {
            "operator_mapping_approved": True,
            "consumer_overlay_written": True,
            "frozen_package_modified": False,
            "canonical_graph_modified": False,
            "canonical_authority_write": False,
            "a2_content_promoted": False,
        },
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    if len(mapped_rows) != len(item_ids):
        raise OverlayError("overlay_mapping_count_invalid")
    return overlay, report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("candidates", "overlay"):
        current = sub.add_parser(command)
        current.add_argument("--source-bank", type=Path, required=True)
        current.add_argument("--consumer", type=Path, required=True)
        current.add_argument("--graph", type=Path, required=True)
        current.add_argument("--item-id", action="append", dest="item_ids", required=True)
        current.add_argument("--output-root", type=Path, required=True)
        if command == "candidates":
            current.add_argument("--limit", type=int, default=5)
        else:
            current.add_argument("--mapping-authority", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        output_root = safe_local_root(args.output_root)
        source = load_sources(args.source_bank, args.consumer, args.graph)
        item_ids = list(dict.fromkeys(args.item_ids))
        if len(item_ids) != EXPECTED_COUNT:
            raise OverlayError(f"item_id_count_invalid:expected={EXPECTED_COUNT}:actual={len(item_ids)}")
        if args.command == "candidates":
            report = build_candidate_report(source, item_ids, args.limit)
            output = output_root / "m12f_mapping_candidates.safe.json"
            write_json(output, report)
            shown = {
                "validation_status": report["validation_status"],
                "item_count": report["item_count"],
                "candidate_counts": {row["item_id"]: row["candidate_count"] for row in report["items"]},
                "blocked_item_ids": report["blocked_item_ids"],
                "stop_reason": report["stop_reason"],
                "output": str(output),
            }
        else:
            overlay, report = build_overlay(source, item_ids, args.mapping_authority)
            consumer_output = output_root / "four_skill_asset_body_consumer.m12f_overlay.private.json"
            report_output = output_root / "m12f_explicit_mapping_overlay.safe.json"
            write_json(consumer_output, overlay)
            write_json(report_output, report)
            shown = {
                "validation_status": report["validation_status"],
                "mapped_count": report["mapped_count"],
                "stop_reason": report["stop_reason"],
                "consumer_output": str(consumer_output),
                "report_output": str(report_output),
            }
        print(json.dumps(shown, ensure_ascii=False, sort_keys=True))
        return 0
    except (
        OverlayError, bridge.BridgeError, m6.ResponseEvidenceError,
        OSError, KeyError, TypeError, ValueError,
    ) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
