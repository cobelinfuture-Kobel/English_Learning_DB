#!/usr/bin/env python3
"""Replay real R7 evidence and build the representative-acceptance gate artifact."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6
from ulga.builders import build_a1fs_v1_r5_local_edge_runtime_complete_evidence_collector as r5

TASK_ID = "A1FS-V1-R7_RealEvidenceAUTOFAILRootCauseAndRepresentativeAcceptanceGate"
SCHEMA_VERSION = "a1fs.v1.r7.real_evidence_autofail_representative_acceptance.v1"
PASS_STATUS = "PASS_R7_REPRESENTATIVE_REAL_EVIDENCE_ACCEPTANCE"
BLOCKED_STATUS = "BLOCKED_R7_REPRESENTATIVE_REAL_EVIDENCE_ACCEPTANCE"
A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Audits stored runtime evidence only; cannot create canonical, projection, media, or Excel content."

ROOT_CAUSES = {
    "LEARNER_CONTENT_ERROR",
    "RESPONSE_FORMAT_MISMATCH",
    "SCORING_CONTRACT_TOO_NARROW",
    "PROMPT_INSTRUCTION_COMPLEXITY_RISK",
    "PROMPT_INSTRUCTION_AMBIGUITY",
    "SOURCE_SCORING_MISALIGNMENT",
    "RUNTIME_PRESENTATION_DEFECT",
    "TELEMETRY_OR_EVIDENCE_DEFECT",
    "HUMAN_SEMANTIC_REVIEW_REQUIRED",
}
ENGINEERING_DEFECT_CAUSES = {
    "SCORING_CONTRACT_TOO_NARROW",
    "PROMPT_INSTRUCTION_AMBIGUITY",
    "SOURCE_SCORING_MISALIGNMENT",
    "RUNTIME_PRESENTATION_DEFECT",
    "TELEMETRY_OR_EVIDENCE_DEFECT",
}
REPRESENTATIVE_SOURCE_KINDS = {"TEXT", "DIALOGUE", "TABLE"}
REPRESENTATIVE_SKILLS = {"READING", "WRITING"}
STOPWORDS = {
    "a", "an", "and", "at", "because", "but", "by", "for", "from", "in", "is",
    "it", "of", "on", "or", "the", "their", "there", "this", "to", "was", "with",
}


class GateError(RuntimeError):
    """Closed-gate input or binding error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GateError(f"json_unreadable:{Path(path).name}:{exc}") from exc
    if not isinstance(value, dict):
        raise GateError(f"json_object_required:{Path(path).name}")
    return value


def validate_owned_digest(value: Mapping[str, Any], field: str) -> None:
    actual = value.get(field)
    core = {key: row for key, row in value.items() if key != field}
    if not isinstance(actual, str) or actual != digest(core):
        raise GateError(f"owned_digest_invalid:{field}")


def atomic_write(path: Path, value: Mapping[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)


def _words(value: str) -> set[str]:
    return {
        token for token in re.findall(r"[^\W_]+", value.casefold(), flags=re.UNICODE)
        if token not in STOPWORDS and len(token) > 1
    }


def _ratio(left: set[str], right: set[str]) -> float:
    return round(len(left & right) / len(right), 4) if right else 0.0


def _format_core(value: str) -> str:
    normalized = m6.norm(re.sub(r"\(([^)]+)\)", r"\1", value))
    parts = normalized.split()
    while parts and parts[0] in {"a", "an", "at", "in", "on", "the", "to"}:
        parts.pop(0)
    return " ".join(parts)


def _manifest_kinds(learner_contract: Mapping[str, Any]) -> list[str]:
    return sorted({
        str(row.get("kind"))
        for row in learner_contract.get("stimulus_render_manifest", [])
        if isinstance(row, Mapping) and row.get("kind") in REPRESENTATIVE_SOURCE_KINDS
    })


def _source_text(learner_contract: Mapping[str, Any]) -> str:
    values = []
    for row in learner_contract.get("stimulus_render_manifest", []):
        if not isinstance(row, Mapping) or row.get("kind") not in REPRESENTATIVE_SOURCE_KINDS:
            continue
        payload = row.get("payload")
        values.append(payload if isinstance(payload, str) else canonical(payload))
    return "\n".join(values)


def classify_autofail(
    *, learner_contract: Mapping[str, Any], scoring_contract: Mapping[str, Any], response: Any,
    telemetry_ok: bool, replay_ok: bool,
) -> tuple[str, dict[str, Any]]:
    if not telemetry_ok or not replay_ok:
        return "TELEMETRY_OR_EVIDENCE_DEFECT", {
            "telemetry_ok": telemetry_ok, "replay_ok": replay_ok,
        }
    prompt = str(learner_contract.get("prompt") or "")
    source = _source_text(learner_contract)
    accepted = [str(row) for row in scoring_contract.get("accepted_texts", []) if isinstance(row, str)]
    response_text = response if isinstance(response, str) else " ".join(str(row) for row in response)
    normalized = m6.norm(response_text)
    normalized_accepted = [m6.norm(row) for row in accepted]
    response_words, source_words = _words(response_text), _words(source)
    accepted_coverages = [_ratio(response_words, _words(row)) for row in accepted]
    accepted_coverage = max(accepted_coverages, default=0.0)
    source_support = _ratio(source_words, response_words)
    signals = {
        "response_sha256": digest(response),
        "normalized_response_sha256": digest(normalized),
        "accepted_forms_sha256": digest(accepted),
        "prompt_sha256": digest(prompt),
        "source_sha256": digest(source),
        "accepted_token_coverage": accepted_coverage,
        "response_source_support": source_support,
        "response_word_count": len(response_words),
        "prompt_has_compound_instruction": bool(re.search(r"\b(and|then|also)\b", prompt, re.I)),
        "response_has_explicit_evidence": bool(re.search(r"evidence|key words|[\"“”]", response_text, re.I)),
    }
    if any(_format_core(response_text) == _format_core(row) for row in accepted):
        return "RESPONSE_FORMAT_MISMATCH", signals
    if scoring_contract.get("scoring_mode") == "FEATURE_RUBRIC":
        return "HUMAN_SEMANTIC_REVIEW_REQUIRED", signals
    if scoring_contract.get("scoring_mode") == "NORMALIZED_TEXT":
        if signals["response_has_explicit_evidence"] and accepted_coverage >= 0.35:
            return "SCORING_CONTRACT_TOO_NARROW", signals
        if accepted_coverage >= 0.55 and source_support >= 0.55:
            return "SCORING_CONTRACT_TOO_NARROW", signals
        if signals["prompt_has_compound_instruction"] and source_support >= 0.45:
            return "PROMPT_INSTRUCTION_COMPLEXITY_RISK", signals
    if normalized in normalized_accepted:
        return "TELEMETRY_OR_EVIDENCE_DEFECT", signals
    return "LEARNER_CONTENT_ERROR", signals


def _coverage_values(rows: Iterable[Mapping[str, Any]]) -> dict[str, list[Any]]:
    rows = list(rows)
    return {
        "source_kinds": sorted({kind for row in rows for kind in row["source_kinds"]}),
        "response_modes": sorted({row["response_mode"] for row in rows}),
        "scoring_modes": sorted({row["scoring_mode"] for row in rows}),
        "skills": sorted({row["skill"] for row in rows if row["skill"] in REPRESENTATIVE_SKILLS}),
        "projection_applied": sorted({bool(row["projection_applied"]) for row in rows}),
    }


def _missing(universe: Mapping[str, list[Any]], evidenced: Mapping[str, list[Any]]) -> dict[str, list[Any]]:
    return {
        key: [value for value in universe[key] if value not in evidenced[key]]
        for key in universe
    }


def _dimension_tokens(row: Mapping[str, Any]) -> set[tuple[str, Any]]:
    tokens = {
        ("response_modes", row["response_mode"]),
        ("scoring_modes", row["scoring_mode"]),
        ("skills", row["skill"]),
        ("projection_applied", bool(row["projection_applied"])),
    }
    tokens.update(("source_kinds", kind) for kind in row["source_kinds"])
    return tokens


def select_targeted_queue(
    universe_rows: Sequence[Mapping[str, Any]], missing: Mapping[str, list[Any]], *, limit: int = 6,
) -> list[dict[str, Any]]:
    uncovered = {(key, value) for key, values in missing.items() for value in values}
    candidates = [row for row in universe_rows if not row["evidenced"]]
    selected: list[dict[str, Any]] = []
    while uncovered and candidates and len(selected) < limit:
        ranked = [(_dimension_tokens(row) & uncovered, index, row) for index, row in enumerate(candidates)]
        covered, _, winner = max(ranked, key=lambda value: (len(value[0]), -value[1]))
        if not covered:
            break
        selected.append({
            "work_item_id": winner["work_item_id"],
            "item_id": winner["item_id"],
            "missing_coverage": [f"{key}={value}" for key, value in sorted(covered, key=str)],
        })
        uncovered -= covered
        candidates = [row for row in candidates if row["work_item_id"] != winner["work_item_id"]]
    return selected


def build(
    *, database_path: Path, evidence_package: Mapping[str, Any], projection: Mapping[str, Any],
    remediation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    validate_owned_digest(evidence_package, "package_sha256")
    validate_owned_digest(projection, "projection_sha256")
    deliveries = projection.get("deliveries")
    if not isinstance(deliveries, list) or not deliveries:
        raise GateError("projection_deliveries_required")
    delivery_by_item = {str(row.get("item_id")): row for row in deliveries}
    if len(delivery_by_item) != len(deliveries):
        raise GateError("projection_item_identity_duplicate")
    evidence_entries = evidence_package.get("entries")
    if not isinstance(evidence_entries, list):
        raise GateError("evidence_entries_required")
    evidence_by_attempt = {str(row.get("attempt_id")): row for row in evidence_entries}
    if len(evidence_by_attempt) != len(evidence_entries):
        raise GateError("evidence_attempt_identity_duplicate")
    if remediation is not None:
        validate_owned_digest(remediation, "artifact_sha256")

    binding_errors: list[str] = []
    system_errors: list[str] = []
    with sqlite3.connect(f"file:{Path(database_path)}?mode=ro", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            system_errors.append("sqlite_integrity_check_failed")
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            system_errors.append("sqlite_foreign_key_check_failed")
        item_rows = connection.execute("SELECT item_id,item_json FROM edge_runtime_items").fetchall()
        items = {row["item_id"]: json.loads(row["item_json"]) for row in item_rows}
        table_names = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"edge_scoring_contract_snapshots", "edge_runtime_scoring_contract_overrides"}.issubset(table_names):
            raise GateError("scoring_contract_registry_missing")
        snapshot_contracts: dict[str, dict[str, Any]] = {}
        for snapshot_row in connection.execute("SELECT scoring_contract_digest,contract_json FROM edge_scoring_contract_snapshots"):
            try:
                snapshot_contract = json.loads(snapshot_row["contract_json"])
            except json.JSONDecodeError:
                binding_errors.append(f"scoring_snapshot_json_invalid:{snapshot_row['scoring_contract_digest']}")
                continue
            if digest(snapshot_contract) != snapshot_row["scoring_contract_digest"]:
                binding_errors.append(f"scoring_snapshot_digest_mismatch:{snapshot_row['scoring_contract_digest']}")
                continue
            snapshot_contracts[snapshot_row["scoring_contract_digest"]] = snapshot_contract
        override_rows = {
            row["item_id"]: dict(row)
            for row in connection.execute("SELECT * FROM edge_runtime_scoring_contract_overrides WHERE status='ACTIVE'")
        }
        attempt_rows = connection.execute(
            """SELECT a.*,s.scoring_mode,s.outcome,s.score,s.human_review_required,
            s.scoring_contract_digest,se.session_state,i.item_json,q.decision
            FROM edge_attempts a JOIN edge_scoring_results s USING(attempt_id)
            JOIN edge_sessions se USING(session_id) JOIN edge_runtime_items i USING(item_id)
            JOIN edge_review_queue q USING(attempt_id)
            WHERE a.learner_id=? ORDER BY a.submitted_at,a.attempt_id""",
            (str(evidence_package.get("learner_id") or ""),),
        ).fetchall()
        event_rows = connection.execute(
            "SELECT payload_json FROM edge_runtime_events WHERE event_type='EDGE_RESPONSE_CAPTURED' ORDER BY event_seq"
        ).fetchall()
        events = {}
        for row in event_rows:
            payload = json.loads(row[0])
            if payload.get("attempt_id"):
                events[str(payload["attempt_id"])] = payload
        session_011_rows = connection.execute(
            """SELECT se.session_id,se.session_state,a.assignment_state,a.item_id
            FROM edge_sessions se JOIN edge_assignments a USING(session_id)
            WHERE se.session_id='R7_REAL_PROJECTED_SESSION_011'
            ORDER BY a.item_id"""
        ).fetchall()

    if len(attempt_rows) != len(evidence_entries):
        binding_errors.append("database_evidence_attempt_count_mismatch")
    synthetic_count = int(evidence_package.get("objective_summary", {}).get("synthetic_evidence_count", 0) or 0)
    synthetic_count += sum(int(bool(row.get("synthetic") or row.get("simulated"))) for row in evidence_entries)

    universe_rows: list[dict[str, Any]] = []
    for delivery in deliveries:
        item_id = str(delivery.get("item_id") or "")
        item = items.get(item_id)
        if not item:
            binding_errors.append(f"runtime_item_missing:{item_id}")
            continue
        learner = delivery.get("projected_learner_contract") or item.get("learner_contract") or {}
        scoring = item.get("private_scoring_contract") or {}
        override = override_rows.get(item_id)
        if override:
            base_digest = digest(scoring)
            effective = snapshot_contracts.get(override["effective_contract_digest"])
            try:
                override_body = json.loads(override["override_contract_json"])
            except json.JSONDecodeError:
                override_body = None
            if (
                override["base_contract_digest"] != base_digest
                or effective is None or override_body != effective
                or digest(effective) != override["effective_contract_digest"]
                or override["effective_contract_digest"] == base_digest
            ):
                binding_errors.append(f"effective_scoring_contract_invalid:{item_id}")
            else:
                scoring = effective
        universe_rows.append({
            "work_item_id": delivery.get("work_item_id"), "item_id": item_id,
            "source_kinds": _manifest_kinds(learner),
            "response_mode": learner.get("response_mode"), "scoring_mode": scoring.get("scoring_mode"),
            "skill": item.get("skill"), "projection_applied": bool(delivery.get("projection_applied")),
            "evidenced": False,
        })

    replay_rows: list[dict[str, Any]] = []
    root_rows: list[dict[str, Any]] = []
    evidenced_rows: list[dict[str, Any]] = []
    evidenced_items: set[str] = set()
    for row in attempt_rows:
        attempt_id = row["attempt_id"]
        item = json.loads(row["item_json"])
        learner = item.get("learner_contract") or {}
        scoring = snapshot_contracts.get(row["scoring_contract_digest"])
        if scoring is None:
            binding_errors.append(f"historical_scoring_contract_missing:{attempt_id}")
            scoring = {}
        response = json.loads(row["response_json"])
        evidence = evidence_by_attempt.get(attempt_id)
        delivery = delivery_by_item.get(row["item_id"])
        event = events.get(attempt_id)
        if evidence is None:
            binding_errors.append(f"evidence_attempt_missing:{attempt_id}")
        if delivery is None:
            binding_errors.append(f"projection_delivery_missing:{row['item_id']}")
        if evidence and any(evidence.get(key) != row[key] for key in ("session_id", "item_id", "validity_status")):
            binding_errors.append(f"evidence_database_identity_mismatch:{attempt_id}")
        if row["scoring_contract_digest"] != digest(scoring):
            binding_errors.append(f"scoring_contract_digest_mismatch:{attempt_id}")
        try:
            replay_outcome, replay_score = m6.ResponseEvidenceStore.score(scoring, response)
            replay_error = None
        except Exception as exc:  # scorer errors are gate evidence, not a builder crash
            replay_outcome, replay_score, replay_error = None, None, type(exc).__name__
        if scoring.get("scoring_mode") == "FEATURE_RUBRIC" and row["decision"] != "PENDING":
            replay_outcome = {"APPROVE": "HUMAN_APPROVE", "REJECT": "HUMAN_REJECT", "DEFER": "HUMAN_DEFER"}.get(row["decision"])
            replay_score = 1.0 if row["decision"] == "APPROVE" else 0.0 if row["decision"] == "REJECT" else None
        replay_ok = replay_error is None and replay_outcome == row["outcome"] and replay_score == row["score"]
        telemetry_ok = bool(
            evidence and event
            and evidence.get("telemetry_status") == "CAPTURED_RUNTIME"
            and event.get("telemetry_status") == "CAPTURED_RUNTIME"
            and evidence.get("learner_rendered_stimulus_reference") == event.get("learner_rendered_stimulus_reference")
        )
        replay_rows.append({
            "attempt_id": attempt_id, "stored_outcome": row["outcome"], "stored_score": row["score"],
            "recomputed_outcome": replay_outcome, "recomputed_score": replay_score,
            "replay_match": replay_ok, "replay_error": replay_error,
            "telemetry_binding_verified": telemetry_ok,
        })
        evidenced_items.add(row["item_id"])
        evidenced_rows.append({
            "work_item_id": delivery.get("work_item_id") if delivery else None,
            "item_id": row["item_id"], "source_kinds": _manifest_kinds(learner),
            "response_mode": learner.get("response_mode"), "scoring_mode": scoring.get("scoring_mode"),
            "skill": item.get("skill"), "projection_applied": bool(delivery and delivery.get("projection_applied")),
            "evidenced": True,
        })
        if row["outcome"] == "AUTO_FAIL":
            cause, signals = classify_autofail(
                learner_contract=learner, scoring_contract=scoring, response=response,
                telemetry_ok=telemetry_ok, replay_ok=replay_ok,
            )
            root_rows.append({
                "attempt_id": attempt_id, "session_id": row["session_id"],
                "work_item_id": delivery.get("work_item_id") if delivery else None,
                "item_id": row["item_id"], "root_cause": cause,
                "stored_score": row["score"], "recomputed_score": replay_score,
                "response_mode": learner.get("response_mode"), "scoring_mode": scoring.get("scoring_mode"),
                "skill": item.get("skill"), "projection_applied": bool(delivery and delivery.get("projection_applied")),
                "source_kinds": _manifest_kinds(learner), "signals": signals,
            })

    for row in universe_rows:
        row["evidenced"] = row["item_id"] in evidenced_items
    universe = _coverage_values(universe_rows)
    evidenced = _coverage_values(evidenced_rows)
    missing = _missing(universe, evidenced)
    targeted = select_targeted_queue(universe_rows, missing)
    replay_failures = sum(not row["replay_match"] for row in replay_rows)
    root_counts = Counter(row["root_cause"] for row in root_rows)
    if remediation is not None:
        remediation_core = {
            key: remediation.get(key) for key in (
                "task_id", "schema_version", "source_gate_sha256", "source_bank_sha256",
                "candidate_identity", "plans",
            )
        }
        if remediation.get("remediation_sha256") != r5.digest(remediation_core):
            binding_errors.append("remediation_owned_digest_invalid")
    remediation_by_attempt = {
        str(row.get("attempt_id")): row
        for row in (remediation or {}).get("applied_records", []) if isinstance(row, Mapping)
    }
    engineering_rows = [row for row in root_rows if row["root_cause"] in ENGINEERING_DEFECT_CAUSES]
    verified_remediation_attempts: set[str] = set()
    for defect in engineering_rows:
        record = remediation_by_attempt.get(defect["attempt_id"])
        if not record:
            continue
        base_digest = digest(items[defect["item_id"]].get("private_scoring_contract") or {})
        override = override_rows.get(defect["item_id"])
        effective_digest = record.get("effective_contract_digest")
        snapshot = snapshot_contracts.get(str(effective_digest))
        if all((
            record.get("item_id") == defect["item_id"],
            record.get("root_cause") == defect["root_cause"],
            record.get("base_contract_digest") == base_digest,
            effective_digest != base_digest,
            override is not None,
            override and override.get("base_contract_digest") == base_digest,
            override and override.get("effective_contract_digest") == effective_digest,
            override and override.get("remediation_sha256") == (remediation or {}).get("remediation_sha256"),
            snapshot is not None and digest(snapshot) == effective_digest,
        )):
            verified_remediation_attempts.add(defect["attempt_id"])
    identified_defects = len(engineering_rows)
    remediated_defects = len(verified_remediation_attempts)
    unresolved_defects = identified_defects - remediated_defects
    for row in root_rows:
        if row["attempt_id"] in verified_remediation_attempts:
            row["remediation_status"] = "VERIFIED_REMEDIATED_FUTURE_ONLY"
        elif row["root_cause"] in ENGINEERING_DEFECT_CAUSES:
            row["remediation_status"] = "UNRESOLVED"
        else:
            row["remediation_status"] = "NOT_APPLICABLE"
    valid_count = sum(row.get("validity_status") == "VALID" for row in evidence_entries)
    auto_pass_count = sum(row.get("outcome") == "AUTO_PASS" for row in evidence_entries)
    auto_fail_count = sum(row.get("outcome") == "AUTO_FAIL" for row in evidence_entries)
    coverage_complete = not any(missing.values())
    gate_pass = all((
        valid_count >= 10, auto_pass_count > 0, auto_fail_count > 0, replay_failures == 0,
        not binding_errors, not system_errors, synthetic_count == 0, unresolved_defects == 0,
        coverage_complete, evidence_package.get("claim_boundaries", {}).get("a2_unlocked") is False,
    ))
    targeted_ids = [row["work_item_id"] for row in targeted]
    session_011 = dict(session_011_rows[0]) if session_011_rows else None
    session_011_delivery = delivery_by_item.get(session_011["item_id"]) if session_011 else None
    session_011_work = session_011_delivery.get("work_item_id") if session_011_delivery else None
    if session_011 and session_011_work in targeted_ids:
        disposition = "RETAIN_FOR_TARGETED_ACCEPTANCE"
    elif session_011 and session_011.get("session_state") == "ABANDONED":
        disposition = "SAFELY_ABANDONED_NOT_REQUIRED_BY_TARGETED_GATE"
    elif session_011:
        disposition = "SAFELY_ABANDON_REQUIRED_NOT_TARGETED"
    else:
        disposition = "SESSION_011_NOT_FOUND"
    core = {
        "task_id": TASK_ID, "schema_version": SCHEMA_VERSION,
        "source_bindings": {
            "database_sha256": file_digest(database_path),
            "evidence_package_sha256": evidence_package["package_sha256"],
            "projection_sha256": projection["projection_sha256"],
            "remediation_artifact_sha256": remediation.get("artifact_sha256") if remediation else None,
            "remediation_sha256": remediation.get("remediation_sha256") if remediation else None,
        },
        "counts": {
            "real_valid_attempt_count": valid_count, "auto_pass_valid_count": auto_pass_count,
            "auto_fail_valid_count": auto_fail_count, "scoring_reproducibility_count": len(replay_rows),
            "scoring_reproducibility_failure_count": replay_failures,
            "binding_error_count": len(binding_errors), "system_error_count": len(system_errors),
            "synthetic_evidence_count": synthetic_count,
            "identified_engineering_defect_count": identified_defects,
            "remediated_engineering_defect_count": remediated_defects,
            "unresolved_engineering_defect_count": unresolved_defects,
            "targeted_additional_real_session_count": len(targeted),
        },
        "replay_results": replay_rows,
        "autofail_root_causes": root_rows,
        "autofail_root_cause_counts": {cause: root_counts.get(cause, 0) for cause in sorted(ROOT_CAUSES)},
        "errors": {"binding": binding_errors, "system": system_errors},
        "coverage": {"universe": universe, "evidenced": evidenced, "missing": missing},
        "verification": {
            "projection_applied_true_verified": True in evidenced["projection_applied"],
            "projection_applied_false_verified": False in evidenced["projection_applied"],
            "auto_pass_path_verified": auto_pass_count > 0,
            "auto_fail_path_verified": auto_fail_count > 0,
            "human_review_path_status": "VERIFIED" if "FEATURE_RUBRIC" in evidenced["scoring_modes"] else "NOT_YET_EVIDENCED",
            "required_representative_coverage_complete": coverage_complete,
        },
        "targeted_queue": targeted,
        "session_011": {
            "disposition": disposition, "current_state": session_011.get("session_state") if session_011 else None,
            "assignment_state": session_011.get("assignment_state") if session_011 else None,
            "attempt_count": sum(row["session_id"] == "R7_REAL_PROJECTED_SESSION_011" for row in attempt_rows),
            "work_item_id": session_011_work,
        },
        "representative_acceptance_status": PASS_STATUS if gate_pass else BLOCKED_STATUS,
        "a2_unlocked": False,
        "next_resume_task": "A1FS-V1_FinalSystemAcceptanceAndCloseout" if gate_pass else TASK_ID,
    }
    return {**core, "artifact_sha256": digest(core)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--evidence-package", type=Path, required=True)
    parser.add_argument("--projection", type=Path, required=True)
    parser.add_argument("--remediation-artifact", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    artifact = build(
        database_path=args.database,
        evidence_package=read_json(args.evidence_package),
        projection=read_json(args.projection),
        remediation=read_json(args.remediation_artifact) if args.remediation_artifact else None,
    )
    atomic_write(args.output, artifact)
    print(json.dumps({
        "representative_acceptance_status": artifact["representative_acceptance_status"],
        **artifact["counts"], "output": str(args.output),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
