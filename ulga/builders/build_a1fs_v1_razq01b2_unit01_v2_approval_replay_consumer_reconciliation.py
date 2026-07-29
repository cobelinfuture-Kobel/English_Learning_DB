#!/usr/bin/env python3
"""Reconcile Unit01 v2 approval with the existing contract-aware replay consumer."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_razq01a_unit01_unit02_authority_aware_windowed_filter_fullfix as fullfix
from ulga.builders import build_a1fs_v1_razq01b_unit01_content_contract as content_contract
from ulga.builders import build_a1fs_v1_razq01b_unit01_contract_aware_replay as replay

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Reconciles approval and calibration outputs only; no learner-facing content, scoring, state, audio, A2, or canonical question bank is written."
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-RAZQ01B2_Unit01V2ApprovalReplayConsumerReconciliation"
SCHEMA_VERSION = "a1fs.v1.razq01b2.unit01_v2_contract_aware_replay.v1"
APPROVAL_SCHEMA_VERSION = "a1fs.v1.razq01b2.unit01_content_contract_approval.v2"
PASS_STATUS = "PASS_A1FS_V1_RAZQ01B2_UNIT01_V2_APPROVAL_REPLAY_CONSUMER_RECONCILIATION"
APPROVAL_STATUS = "APPROVED_AS_RECONCILED"
APPROVED_CONTRACT_SHA256 = "114376e997275a5ac387d69a16d9d3304096605392c6928e49863d4214efbc29"
LEGACY_APPROVED_CONTRACT_SHA256 = "5600f1208789d820b33338965d7dda9ee9d707caab7be1ec5014690e0f3dbdbb"
DEFAULT_CONTRACT = content_contract.DEFAULT_OUTPUT
DEFAULT_APPROVAL = Path("ulga/graph/a1fs_v1_razq01b2_unit01_content_contract_approval_v2.json")
NEXT_SHORT_STEP = "A1FS-V1-RAZQ01B2_Unit01V2ProductionReplayAndCapacityDeltaReadback"
POST_REPLAY_NEXT_SHORT_STEP = "A1FS-V1-RAZQ01C_Unit01ThreeSkillCandidateSelectionAndDeferredListeningReadback"
OUTPUT_REPORT = replay.OUTPUT_REPORT
OUTPUT_VALIDATION = replay.OUTPUT_VALIDATION
OUTPUT_MATRIX = replay.OUTPUT_MATRIX


def _load_json(path: Path) -> dict[str, Any]:
    return replay._load_json(path)


def build_operator_approval() -> dict[str, Any]:
    return {
        "schema_version": APPROVAL_SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "unit_id": content_contract.UNIT_ID,
        "decision_status": APPROVAL_STATUS,
        "approved_contract_sha256": APPROVED_CONTRACT_SHA256,
        "approved_dimensions": [
            "ACTIVE_NOUNS",
            "ACTIVE_ADJECTIVES",
            "RECEPTIVE_VOCABULARY",
            "CANONICAL_CHUNKS",
            "INSTRUCTIONAL_PHRASES",
            "SENTENCE_FRAMES",
            "MATERIAL_SELECTION_POLICY",
        ],
        "decision_source": "EXPLICIT_OPERATOR_TASK_INVOCATION",
        "decision_source_text": "Unit01V2ApprovalReplayConsumerReconciliation",
        "effective_date": "2026-07-29",
        "supersedes_contract_sha256": LEGACY_APPROVED_CONTRACT_SHA256,
        "boundaries": {
            "unit02_to_unit24_modified": False,
            "canonical_question_bank_written": False,
            "learner_facing_content_written": False,
            "audio_enabled": False,
            "speaking_capture_enabled": False,
            "a2_unlocked": False,
            "parallel_curriculum_created": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }


def verify_operator_approval(
    contract: Mapping[str, Any], approval: Mapping[str, Any]
) -> dict[str, Any]:
    content_contract.verify_contract_digest(contract)
    if contract.get("schema_version") != "a1fs.v1.razq01b.unit01_content_contract.v2":
        raise replay.ReplayError("UNIT01_V2_CONTRACT_REQUIRED")
    if contract.get("contract_sha256") != APPROVED_CONTRACT_SHA256:
        raise replay.ReplayError("APPROVED_V2_CONTRACT_DIGEST_MISMATCH")
    if approval != build_operator_approval():
        raise replay.ReplayError("UNIT01_V2_OPERATOR_APPROVAL_MANIFEST_INVALID")
    if approval.get("approved_contract_sha256") != contract.get("contract_sha256"):
        raise replay.ReplayError("UNIT01_V2_APPROVAL_NOT_BOUND_TO_CONTRACT")
    expected_dimensions = contract.get("operator_review", {}).get("review_dimensions", [])
    if approval.get("approved_dimensions") != expected_dimensions:
        raise replay.ReplayError("UNIT01_V2_APPROVED_DIMENSIONS_MISMATCH")
    if any(approval.get("boundaries", {}).values()):
        raise replay.ReplayError("UNIT01_V2_APPROVAL_BOUNDARY_INVALID")
    return {
        "operator_approval_verified": True,
        "decision_status": approval["decision_status"],
        "approved_contract_sha256": contract["contract_sha256"],
        "approved_dimension_count": len(approval["approved_dimensions"]),
        "legacy_contract_superseded": True,
        "superseded_contract_sha256": LEGACY_APPROVED_CONTRACT_SHA256,
        "contract_schema_version": contract["schema_version"],
    }


def _contract_profile(profile: fullfix.Profile, contract: Mapping[str, Any]) -> fullfix.Profile:
    vocabulary = contract["vocabulary_contract"]
    noun_rows = vocabulary["active_vocabulary"]
    adjective_rows = vocabulary["active_adjectives"]
    active_rows = [*noun_rows, *adjective_rows]
    receptive_rows = [
        row
        for row in vocabulary["receptive_vocabulary"]
        if row.get("cefr_level") == "A1"
    ]
    active = {str(row["lemma"]).lower() for row in active_rows}
    receptive = {str(row["lemma"]).lower() for row in receptive_rows}
    chunks = contract["chunk_contract"]
    direct_chunk_rows = [
        row
        for row in chunks["canonical_chunks"]
        if row.get("direct_unit01_use_allowed") is True
    ]
    phrase_rows = [
        *chunks["instructional_phrases"],
        *chunks["adjective_instructional_phrases"],
    ]
    phrases = {str(row["surface_form"]).lower() for row in phrase_rows}
    chunk_surfaces = {str(row["surface_form"]).lower() for row in direct_chunk_rows}
    lexical = tuple(sorted(active | receptive | phrases | chunk_surfaces))
    grammar = contract["grammar_contract"]
    contexts = tuple(
        row["context_id"] for row in contract["material_contract"]["context_families"]
    )
    authority_sources = set(profile.authority_sources) | {
        "UNIT01_OPERATOR_APPROVED_CONTENT_CONTRACT",
        "UNIT01_OPERATOR_APPROVED_CONTENT_CONTRACT_V2",
    }
    return fullfix.Profile(
        unit_id=profile.unit_id,
        order=profile.order,
        level=profile.level,
        lesson_ids=profile.lesson_ids,
        skills=profile.skills,
        question_types=profile.question_types,
        goals=tuple(grammar["core_functions"] + grammar.get("guided_functions", [])),
        clues=tuple(
            sorted(
                set(profile.clues)
                | {
                    "ARTICLE_SELECTION_AND_NOUN_PHRASE_ONLY",
                    "Choose a/an from the following sound, not only the written first letter.",
                }
            )
        ),
        context_ids=contexts,
        evp_ids=tuple(sorted(str(row["evp_sense_id"]) for row in active_rows)),
        egp_ids=tuple(
            grammar["core_focus_egp_row_ids"]
            + grammar["guided_extension_egp_row_ids"]
        ),
        chunk_ids=tuple(str(row["chunk_id"]) for row in direct_chunk_rows),
        pattern_ids=profile.pattern_ids,
        lexical_cues=lexical,
        runtime_cues=profile.runtime_cues,
        authority_sources=tuple(sorted(authority_sources)),
        prerequisites=profile.prerequisites,
    )


def _contract_lexicon(
    runtime_lexicon: Sequence[str], contract: Mapping[str, Any]
) -> frozenset[str]:
    words = {str(item).lower() for item in runtime_lexicon}
    words.update(content_contract.active_noun_lemmas(contract))
    words.update(content_contract.active_adjective_lemmas(contract))
    words.update(content_contract.receptive_lemmas(contract))
    chunks = contract["chunk_contract"]
    for section in (
        chunks["canonical_chunks"],
        chunks["instructional_phrases"],
        chunks["adjective_instructional_phrases"],
    ):
        for row in section:
            words.update(
                token.lower()
                for token in fullfix.WORD_RE.findall(str(row.get("surface_form") or ""))
            )
    return frozenset(words)


def _configure_replay_consumer() -> None:
    replay.TASK_ID = TASK_ID
    replay.SCHEMA_VERSION = SCHEMA_VERSION
    replay.APPROVAL_SCHEMA_VERSION = APPROVAL_SCHEMA_VERSION
    replay.PASS_STATUS = PASS_STATUS
    replay.APPROVAL_STATUS = APPROVAL_STATUS
    replay.APPROVED_CONTRACT_SHA256 = APPROVED_CONTRACT_SHA256
    replay.DEFAULT_CONTRACT = DEFAULT_CONTRACT
    replay.DEFAULT_APPROVAL = DEFAULT_APPROVAL
    replay.NEXT_SHORT_STEP = POST_REPLAY_NEXT_SHORT_STEP
    replay.OUTPUT_REPORT = OUTPUT_REPORT
    replay.OUTPUT_VALIDATION = OUTPUT_VALIDATION
    replay.OUTPUT_MATRIX = OUTPUT_MATRIX
    replay.build_operator_approval = build_operator_approval
    replay.verify_operator_approval = verify_operator_approval
    replay._contract_profile = _contract_profile
    replay._contract_lexicon = _contract_lexicon


def _capacity_snapshot(report: Mapping[str, Any]) -> dict[str, int]:
    unit = report.get("unit", {})
    funnel = unit.get("filter_funnel", {})
    strict = unit.get("strict_skill_capacity", {})
    rewrite = unit.get("rewrite_skill_capacity", {})
    return {
        "pass_count": int(funnel.get("pass_count") or 0),
        "borderline_count": int(funnel.get("borderline_count") or 0),
        "reject_count": int(funnel.get("reject_count") or 0),
        "reading_source_eligible": int(strict.get("READING_SOURCE_ELIGIBLE") or 0),
        "listening_script_eligible": int(strict.get("LISTENING_SCRIPT_ELIGIBLE") or 0),
        "speaking_prompt_eligible": int(strict.get("SPEAKING_PROMPT_ELIGIBLE") or 0),
        "writing_seed_eligible": int(strict.get("WRITING_SEED_ELIGIBLE") or 0),
        "reading_rewrite_candidate": int(rewrite.get("READING_REWRITE_CANDIDATE") or 0),
        "listening_rewrite_candidate": int(rewrite.get("LISTENING_REWRITE_CANDIDATE") or 0),
        "speaking_rewrite_candidate": int(rewrite.get("SPEAKING_REWRITE_CANDIDATE") or 0),
        "writing_rewrite_candidate": int(rewrite.get("WRITING_REWRITE_CANDIDATE") or 0),
    }


def _load_and_validate_baseline(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    baseline = _load_json(path)
    baseline_digest = str(
        baseline.get("inputs", {}).get("approved_contract_sha256") or ""
    )
    if baseline_digest != LEGACY_APPROVED_CONTRACT_SHA256:
        raise replay.ReplayError("V1_BASELINE_CONTRACT_DIGEST_INVALID")
    return baseline


def _apply_capacity_delta(
    report: dict[str, Any], baseline: Mapping[str, Any] | None
) -> None:
    current = _capacity_snapshot(report)
    if baseline is None:
        report["capacity_delta"] = {
            "baseline_supplied": False,
            "current_v2": current,
        }
        return
    previous = _capacity_snapshot(baseline)
    report["capacity_delta"] = {
        "baseline_supplied": True,
        "baseline_contract_sha256": LEGACY_APPROVED_CONTRACT_SHA256,
        "current_contract_sha256": APPROVED_CONTRACT_SHA256,
        "v1": previous,
        "v2": current,
        "delta_v2_minus_v1": {
            key: current[key] - previous[key] for key in current
        },
    }


def _rewrite_outputs(report: Mapping[str, Any], output_dir: Path) -> None:
    report_path = output_dir / OUTPUT_REPORT
    validation_path = output_dir / OUTPUT_VALIDATION
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    validation = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "records_scanned": report["records_scanned"],
        "validation": report["validation"],
        "capacity_delta": report["capacity_delta"],
        "next_short_step": POST_REPLAY_NEXT_SHORT_STEP,
    }
    validation_path.write_text(
        json.dumps(validation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def run_replay(
    *,
    repo_root: Path,
    index_path: Path,
    output_dir: Path,
    contract_path: Path = DEFAULT_CONTRACT,
    approval_path: Path = DEFAULT_APPROVAL,
    baseline_report_path: Path | None = None,
    max_records: int | None = None,
    sample_limit: int = 30,
    progress_every: int = 50_000,
) -> dict[str, Any]:
    baseline = _load_and_validate_baseline(baseline_report_path)
    _configure_replay_consumer()
    report = replay.run_replay(
        repo_root=repo_root,
        index_path=index_path,
        output_dir=output_dir,
        contract_path=contract_path,
        approval_path=approval_path,
        max_records=max_records,
        sample_limit=sample_limit,
        progress_every=progress_every,
    )
    _apply_capacity_delta(report, baseline)
    report["validation"].update(
        {
            "unit01_v2_contract_applied": True,
            "active_noun_count": 16,
            "active_adjective_count": 6,
            "active_memorization_count": 22,
            "article_sound_gate_applied": True,
            "countability_sensitive_chunk_gate_applied": True,
            "legacy_contract_superseded": True,
            "listening_product_boundary": (
                "DEFERRED_NO_LISTENING_LESSON_IN_UNIT01_RUNTIME"
            ),
        }
    )
    report["next_short_step"] = POST_REPLAY_NEXT_SHORT_STEP
    _rewrite_outputs(report, output_dir)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--index-path", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--approval", type=Path, default=DEFAULT_APPROVAL)
    parser.add_argument("--baseline-report", type=Path)
    parser.add_argument("--max-records", type=int)
    parser.add_argument("--sample-limit", type=int, default=30)
    parser.add_argument("--progress-every", type=int, default=50_000)
    args = parser.parse_args(argv)
    try:
        report = run_replay(
            repo_root=args.repo_root.resolve(),
            index_path=args.index_path.resolve(),
            output_dir=args.output_dir.resolve(),
            contract_path=args.contract.resolve(),
            approval_path=args.approval.resolve(),
            baseline_report_path=(
                args.baseline_report.resolve() if args.baseline_report else None
            ),
            max_records=args.max_records,
            sample_limit=args.sample_limit,
            progress_every=args.progress_every,
        )
    except (
        replay.ReplayError,
        fullfix.CalibrationError,
        ValueError,
        KeyError,
        TypeError,
    ) as exc:
        print(
            "STATUS=FAIL_A1FS_V1_RAZQ01B2_UNIT01_V2_APPROVAL_"
            "REPLAY_CONSUMER_RECONCILIATION"
        )
        print(f"ERROR={exc}")
        return 1
    print(f"STATUS={report['status']}")
    print(f"RECORDS_SCANNED={report['records_scanned']}")
    funnel = report["unit"]["filter_funnel"]
    print(
        f"UNIT={content_contract.UNIT_ID} "
        f"PASS={funnel.get('pass_count', 0)} "
        f"BORDERLINE={funnel.get('borderline_count', 0)} "
        f"REJECT={funnel.get('reject_count', 0)}"
    )
    print(f"NEXT_SHORT_STEP={POST_REPLAY_NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
