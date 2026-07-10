"""Synthetic builder scaffold for ReadingV1 PracticeBank contract fixtures.

This builder intentionally does not read RAZ files and does not persist raw source
text. It emits a synthetic, candidate-only PracticeBank object that exercises the
contract, policy validator, canonical A1 PracticeItem grammar gate, package
grammar-gate accounting, and deterministic validation materialization.
"""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional


TASK_ID = "R7-M104E23C_A1PracticeBankValidatedBuildMaterialization"
CANONICAL_GRAMMAR_ID = "GRAMMAR_PRESENT_SIMPLE_BASIC_STATEMENTS"
CANONICAL_GRAMMAR_TEXT = "They go to school."
GRAMMAR_GATE_VERSION = "a1_practice_item_grammar_gate.v1"


def _grammar_gate() -> Dict[str, Any]:
    return {
        "gate_version": GRAMMAR_GATE_VERSION,
        "validation_targets": [
            {
                "grammar_id": CANONICAL_GRAMMAR_ID,
                "text": CANONICAL_GRAMMAR_TEXT,
                "target_role": "synthetic_practice_item_derived_text",
            }
        ],
        "require_all_focus_matches": True,
        "validator_mode": "OFFLINE_STATIC_PROTOTYPE",
        "production_runtime_validator": False,
        "learner_state_write": False,
    }


def _base_item(item_id: str, question_type: str, prompt: str, answer_key: Any) -> Dict[str, Any]:
    return {
        "item_id": item_id,
        "schema_version": "reading_v1_practice_item.v1",
        "authority_status": "candidate_only",
        "promotion_status": "not_promoted",
        "level_stage": "RV1-S3",
        "stage_name": "A2-lite bridge / Flyers-entry",
        "theme": "DailyRoutine",
        "situation": "synthetic_contract_fixture",
        "question_type": question_type,
        "skill_area": "reading",
        "cambridge_alignment": {
            "cefr_band": "A1",
            "yle_band": "Flyers-entry",
            "alignment_role": "difficulty_reference_not_exam_clone",
        },
        "spiral_binding": {
            "spiral_from_stage": "RV1-S2",
            "spiral_to_stage": "RV1-S3",
            "stage_new_focus": ["sequence_reading"],
            "stage_reinforcement": ["routine_actions", "literal_comprehension"],
        },
        "content_binding": {
            "grammar_focus": [CANONICAL_GRAMMAR_ID],
            "patterns": ["First, ___. Then, ___."],
            "vocabulary_refs": ["SYNTH_VOCAB_DAILY_ROUTINE"],
            "chunk_refs": [],
            "theme_refs": ["SYNTH_THEME_DAILY_ROUTINE"],
        },
        "grammar_gate": _grammar_gate(),
        "source_trace": {
            "source_family": "synthetic_contract_fixture",
            "source_system": "reading_v1_contract_fixture",
            "source_level": "synthetic",
            "source_book_ref": None,
            "source_unit_ref": f"synthetic_unit_{item_id.lower()}",
            "source_sentence_refs": [f"synthetic_sentence_{item_id.lower()}"],
            "source_page_ref": None,
            "source_locator": f"synthetic://reading_v1/{item_id}",
            "source_payload_stored": False,
        },
        "display_payload": {
            "display_text": None,
            "display_text_type": "derived_or_locator_only",
            "display_text_source": "synthetic_contract_fixture",
            "raw_source_text_copied": False,
            "full_passage_text_copied": False,
        },
        "question": {
            "prompt": prompt,
            "prompt_language": "en",
            "options": [],
            "requires_image": False,
            "requires_audio": False,
        },
        "answer_model": {
            "answer_type": "short_text",
            "answer_key": answer_key,
            "accepted_answers": [],
            "case_sensitive": False,
            "requires_exact_match": False,
        },
        "answer_evidence": {
            "evidence_type": "direct_literal_text_or_locator",
            "evidence_refs": [f"synthetic_evidence_{item_id.lower()}"],
            "evidence_quote_allowed": False,
            "source_sentence_ref": f"synthetic_sentence_{item_id.lower()}",
            "source_locator": f"synthetic://reading_v1/{item_id}#evidence",
            "directness": "direct",
        },
        "policy_flags": {
            "private_homework_only": True,
            "not_for_public_export": True,
            "not_for_commercial_distribution": True,
            "public_preview_allowed": False,
            "raw_raz_text_persisted": False,
            "full_passage_text_persisted": False,
            "source_payload_copied_to_repo": False,
        },
        "html_gate": {
            "html_ready": False,
            "html_ready_reason": None,
            "render_mode": "local_private_homework_only",
        },
        "validator_status": {
            "status": "NOT_RUN",
            "errors": [],
            "warnings": [],
        },
    }


def build_synthetic_practice_bank() -> Dict[str, Any]:
    """Build the raw contract fixture without executing validation."""

    items: List[Dict[str, Any]] = [
        _base_item("RV1_ITEM_000001", "literal_who", "Who is in the routine?", "the child"),
        _base_item("RV1_ITEM_000002", "literal_what", "What does the child do first?", "wake up"),
        _base_item("RV1_ITEM_000003", "literal_where", "Where does the child go?", "school"),
        _base_item("RV1_ITEM_000004", "true_false", "The child goes to school.", True),
        _base_item("RV1_ITEM_000005", "sentence_ordering", "Put the routine in order.", ["sent_001", "sent_002", "sent_003"]),
        _base_item("RV1_ITEM_000006", "cloze_vocabulary", "The child goes to ____.", "school"),
    ]

    items[3]["answer_model"]["answer_type"] = "boolean"
    items[4]["answer_model"]["answer_type"] = "ordered_ids"
    items[4]["answer_evidence"]["evidence_refs"] = ["synthetic_sequence_001", "synthetic_sequence_002", "synthetic_sequence_003"]
    items[5]["answer_model"]["answer_type"] = "cloze_text"
    items[5]["answer_model"]["accepted_answers"] = []

    return {
        "practice_bank_id": "RV1_PB_SYNTHETIC_CONTRACT_000001",
        "schema_version": "reading_v1_practice_bank.v1",
        "pipeline_stage": "candidate_practice_bank",
        "authority_status": "candidate_only",
        "promotion_status": "not_promoted",
        "private_homework_only": True,
        "not_for_public_export": True,
        "not_for_commercial_distribution": True,
        "source_payload_policy": {
            "raw_source_text_persisted": False,
            "full_passage_text_persisted": False,
            "source_payload_copied_to_repo": False,
            "display_text_policy": "derived_or_locator_only",
        },
        "scope": {
            "level_stage": "RV1-S3",
            "stage_name": "A2-lite bridge / Flyers-entry",
            "theme": "DailyRoutine",
            "situation": "synthetic_contract_fixture",
            "question_types": [
                "literal_who",
                "literal_what",
                "literal_where",
                "true_false",
                "sentence_ordering",
                "cloze_vocabulary",
            ],
            "item_count": len(items),
        },
        "spiral_plan": {
            "spiral_from_stage": "RV1-S2",
            "spiral_to_stage": "RV1-S3",
            "stage_new_focus": ["sequence_reading"],
            "stage_reinforcement": ["routine_actions", "literal_comprehension"],
        },
        "source_selection": {
            "source_family": "synthetic_contract_fixture",
            "source_system": "reading_v1_contract_fixture",
            "source_query_ref": "synthetic://reading_v1/query/contract_fixture",
            "source_unit_refs": [item["source_trace"]["source_unit_ref"] for item in items],
        },
        "items": items,
        "validation_summary": {
            "validator_status": "NOT_RUN",
            "html_ready_count": 0,
            "blocked_count": 0,
            "grammar_gate_status": "NOT_RUN",
            "grammar_gate_pass_count": 0,
            "grammar_gate_fail_count": 0,
            "grammar_validation_target_count": 0,
            "grammar_matched_target_count": 0,
            "warning_count": 0,
            "error_count": 0,
        },
        "build_metadata": {
            "builder_name": "build_reading_v1_practice_bank",
            "builder_version": "0.4.0",
            "built_at": None,
            "git_commit": None,
            "validated": False,
            "validation_task_id": None,
        },
    }


def materialize_validation(
    package: Mapping[str, Any],
    report: Mapping[str, Any],
) -> Dict[str, Any]:
    """Return a validated copy of ``package`` using a deterministic report."""

    output = deepcopy(dict(package))
    items = output.get("items")
    item_reports = report.get("item_reports")
    if not isinstance(items, list) or not isinstance(item_reports, list) or len(items) != len(item_reports):
        raise ValueError("PracticeBank items and validation item_reports must be aligned one-to-one.")

    for item, item_report in zip(items, item_reports):
        grammar_report = item_report.get("grammar_gate_report", {})
        item["validator_status"] = {
            "status": item_report.get("validator_status", "FAIL"),
            "errors": deepcopy(item_report.get("errors", [])),
            "warnings": deepcopy(item_report.get("warnings", [])),
            "grammar_gate_status": grammar_report.get("gate_status", "FAIL"),
            "grammar_validation_target_count": grammar_report.get("validation_target_count", 0),
            "grammar_matched_target_count": grammar_report.get("matched_target_count", 0),
        }
        html_ready = item_report.get("computed_html_ready") is True
        item["html_gate"]["html_ready"] = html_ready
        item["html_gate"]["html_ready_reason"] = (
            None if html_ready else "blocked_by_practice_bank_validation"
        )

    summary = report.get("summary", {})
    grammar_summary = report.get("grammar_gate_summary", {})
    output["validation_summary"] = {
        "validator_status": report.get("validator_status", "FAIL"),
        "html_ready_count": summary.get("html_ready_count", 0),
        "blocked_count": summary.get("blocked_count", len(items)),
        "grammar_gate_status": "PASS" if grammar_summary.get("all_items_pass") is True else "FAIL",
        "grammar_gate_pass_count": summary.get("grammar_gate_pass_count", 0),
        "grammar_gate_fail_count": summary.get("grammar_gate_fail_count", len(items)),
        "grammar_validation_target_count": summary.get("grammar_validation_target_count", 0),
        "grammar_matched_target_count": summary.get("grammar_matched_target_count", 0),
        "warning_count": summary.get("warning_count", 0),
        "error_count": summary.get("error_count", 0),
    }
    build_metadata = output.setdefault("build_metadata", {})
    build_metadata["validated"] = True
    build_metadata["validation_task_id"] = report.get("task_id", TASK_ID)
    return output


def build_validated_synthetic_practice_bank() -> Dict[str, Any]:
    """Build, validate, and materialize the synthetic PracticeBank fixture."""

    from ulga.validators.validate_reading_v1_practice_bank import validate_package

    package = build_synthetic_practice_bank()
    report = validate_package(package)
    return materialize_validation(package, report)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Build a synthetic ReadingV1 PracticeBank contract fixture.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Write the unvalidated contract fixture instead of the validated materialized fixture.",
    )
    args = parser.parse_args(argv)

    package = build_synthetic_practice_bank() if args.raw else build_validated_synthetic_practice_bank()
    package["build_metadata"]["built_at"] = datetime.now(timezone.utc).isoformat()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(package, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
