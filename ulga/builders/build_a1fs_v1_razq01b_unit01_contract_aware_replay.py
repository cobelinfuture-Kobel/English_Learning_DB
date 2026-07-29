#!/usr/bin/env python3
"""Replay Unit01 RAZ candidates against the operator-approved content contract."""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_razq01a_unit01_unit02_authority_aware_windowed_filter_fullfix as fullfix
from ulga.builders import build_a1fs_v1_razq01a_unit01_unit02_filter_calibration as base
from ulga.builders import build_a1fs_v1_razq01b_unit01_content_contract as content_contract

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Produces calibration and capacity reports only; no learner-facing content, scoring, state, audio, A2, or canonical question bank is written."
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-RAZQ01B_Unit01ContentContractOperatorReviewAndContractAwareReplay"
SCHEMA_VERSION = "a1fs.v1.razq01b.unit01_contract_aware_replay.v1"
APPROVAL_SCHEMA_VERSION = "a1fs.v1.razq01b.unit01_content_contract_approval.v1"
PASS_STATUS = "PASS_A1FS_V1_RAZQ01B_UNIT01_CONTRACT_AWARE_REPLAY"
APPROVAL_STATUS = "APPROVED_AS_RECONCILED"
APPROVED_CONTRACT_SHA256 = "5600f1208789d820b33338965d7dda9ee9d707caab7be1ec5014690e0f3dbdbb"
DEFAULT_CONTRACT = content_contract.DEFAULT_OUTPUT
DEFAULT_APPROVAL = Path("ulga/graph/a1fs_v1_razq01b_unit01_content_contract_approval.json")
NEXT_SHORT_STEP = "A1FS-V1-RAZQ01C_Unit01FourSkillCandidateSelectionFromContractAwareReplay"
OUTPUT_REPORT = "a1fs_v1_razq01b_unit01_contract_aware_replay.json"
OUTPUT_VALIDATION = "a1fs_v1_razq01b_unit01_contract_aware_replay_validation.json"
OUTPUT_MATRIX = "a1fs_v1_razq01b_unit01_contract_aware_distinct_capacity_matrix.csv"


class ReplayError(ValueError):
    pass


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReplayError(f"JSON_UNREADABLE={path}:{exc}") from exc
    if not isinstance(value, dict):
        raise ReplayError(f"JSON_OBJECT_REQUIRED={path}")
    return value


def build_operator_approval() -> dict[str, Any]:
    return {
        "schema_version": APPROVAL_SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "unit_id": content_contract.UNIT_ID,
        "decision_status": APPROVAL_STATUS,
        "approved_contract_sha256": APPROVED_CONTRACT_SHA256,
        "approved_dimensions": [
            "ACTIVE_VOCABULARY",
            "RECEPTIVE_VOCABULARY",
            "CANONICAL_CHUNKS",
            "INSTRUCTIONAL_PHRASES",
            "SENTENCE_FRAMES",
            "MATERIAL_SELECTION_POLICY",
        ],
        "decision_source": "EXPLICIT_OPERATOR_TASK_INVOCATION",
        "decision_source_text": "Unit01ContentContractOperatorReviewAndContractAwareReplay",
        "effective_date": "2026-07-29",
        "boundaries": {
            "unit02_to_unit24_modified": False,
            "canonical_question_bank_written": False,
            "learner_facing_content_written": False,
            "audio_enabled": False,
            "speaking_capture_enabled": False,
            "a2_unlocked": False,
            "parallel_curriculum_created": False,
        },
        "next_short_step": "A1FS-V1-RAZQ01B_Unit01ProductionContractAwareReplayAndReadback",
    }


def verify_operator_approval(contract: Mapping[str, Any], approval: Mapping[str, Any]) -> dict[str, Any]:
    content_contract.verify_contract_digest(contract)
    if contract.get("contract_sha256") != APPROVED_CONTRACT_SHA256:
        raise ReplayError("APPROVED_CONTRACT_DIGEST_MISMATCH")
    if approval != build_operator_approval():
        raise ReplayError("OPERATOR_APPROVAL_MANIFEST_INVALID")
    if approval.get("approved_contract_sha256") != contract.get("contract_sha256"):
        raise ReplayError("OPERATOR_APPROVAL_NOT_BOUND_TO_CONTRACT")
    expected_dimensions = contract.get("operator_review", {}).get("review_dimensions", [])
    if approval.get("approved_dimensions") != expected_dimensions:
        raise ReplayError("OPERATOR_APPROVED_DIMENSIONS_MISMATCH")
    if any(approval.get("boundaries", {}).values()):
        raise ReplayError("OPERATOR_APPROVAL_BOUNDARY_INVALID")
    return {
        "operator_approval_verified": True,
        "decision_status": approval["decision_status"],
        "approved_contract_sha256": contract["contract_sha256"],
        "approved_dimension_count": len(approval["approved_dimensions"]),
    }


def _contract_profile(profile: fullfix.Profile, contract: Mapping[str, Any]) -> fullfix.Profile:
    active_rows = contract["vocabulary_contract"]["active_vocabulary"]
    receptive_rows = [
        row
        for row in contract["vocabulary_contract"]["receptive_vocabulary"]
        if row.get("cefr_level") == "A1"
    ]
    active = {str(row["lemma"]).lower() for row in active_rows}
    receptive = {str(row["lemma"]).lower() for row in receptive_rows}
    phrases = [str(row["surface_form"]).lower() for row in contract["chunk_contract"]["instructional_phrases"]]
    chunk_rows = contract["chunk_contract"]["canonical_chunks"]
    chunk_surfaces = [str(row["surface_form"]).lower() for row in chunk_rows]
    lexical = tuple(sorted(active | receptive | set(phrases) | set(chunk_surfaces)))
    grammar = contract["grammar_contract"]
    contexts = tuple(row["context_id"] for row in contract["material_contract"]["context_families"])
    return fullfix.Profile(
        unit_id=profile.unit_id,
        order=profile.order,
        level=profile.level,
        lesson_ids=profile.lesson_ids,
        skills=profile.skills,
        question_types=profile.question_types,
        goals=tuple(grammar["core_functions"]),
        clues=tuple(sorted(set(profile.clues) | {"ARTICLE_SELECTION_AND_NOUN_PHRASE_ONLY"})),
        context_ids=contexts,
        evp_ids=tuple(sorted(str(row["evp_sense_id"]) for row in active_rows)),
        egp_ids=tuple(grammar["core_focus_egp_row_ids"] + grammar["guided_extension_egp_row_ids"]),
        chunk_ids=tuple(str(row["chunk_id"]) for row in chunk_rows),
        pattern_ids=profile.pattern_ids,
        lexical_cues=lexical,
        runtime_cues=profile.runtime_cues,
        authority_sources=tuple(
            sorted(set(profile.authority_sources) | {"UNIT01_OPERATOR_APPROVED_CONTENT_CONTRACT"})
        ),
        prerequisites=profile.prerequisites,
    )


def _contract_lexicon(runtime_lexicon: Sequence[str], contract: Mapping[str, Any]) -> frozenset[str]:
    words = set(str(item).lower() for item in runtime_lexicon)
    words.update(content_contract.active_lemmas(contract))
    words.update(content_contract.receptive_lemmas(contract))
    for section in (
        contract["chunk_contract"]["canonical_chunks"],
        contract["chunk_contract"]["instructional_phrases"],
    ):
        for row in section:
            words.update(
                token.lower()
                for token in fullfix.WORD_RE.findall(str(row.get("surface_form") or ""))
            )
    return frozenset(words)


def _contract_sample(row: Mapping[str, Any]) -> dict[str, Any]:
    value = fullfix._sample(row)
    value["contract_gate"] = row.get("contract_gate")
    return value


@dataclass
class ContractAccumulator(fullfix.Accumulator):
    contract: Mapping[str, Any] | None = None

    def finish(self) -> dict[str, list[dict[str, Any]]]:
        if self.contract is None:
            raise ReplayError("UNIT01_CONTRACT_REQUIRED")
        self.counts["eligible_semantic_distinct_count"] = len(self.groups)
        buckets = {"PASS": [], "BORDERLINE": [], "REJECT": list(self.rejects)}
        for key, original in self.groups.items():
            row, meta = dict(original), self.meta[key]
            row["reusability_tags"] = sorted(meta["tags"])
            if meta["complete"] and not row.get("source_record_id"):
                row["source_record_id"] = sorted(meta["ids"])[0]
            recovered = bool(meta["missing"] and meta["complete"])
            row["lineage_recovered_from_semantic_group"] = recovered
            if recovered:
                self.counts["lineage_group_recovered_count"] += 1
            gate = content_contract.evaluate_material_window(
                str(row.get("text") or ""),
                contract=self.contract,
                known_lexicon=self.lexicon,
                blocked_features=row.get("blocked_grammar_features", []),
                source_level=str(row.get("source_level") or ""),
                lineage_complete=bool(row.get("source_record_id")),
            )
            row["contract_gate"] = gate
            classification = str(gate["classification"])
            reasons = list(gate["reasons"])
            if classification == "PASS" and not row.get("skill_eligibility"):
                classification, reasons = "BORDERLINE", ["NO_STRICT_SKILL_ELIGIBILITY"]
            elif classification == "PASS":
                reasons = ["OPERATOR_APPROVED_UNIT01_CONTRACT_MATCH"]
            row["classification"], row["reasons"] = classification, reasons
            self.counts[f"{classification.lower()}_count"] += 1
            self.levels[row.get("source_level") or "UNKNOWN"] += 1
            self.types[row.get("source_type") or "UNKNOWN"] += 1
            if classification == "PASS":
                self.strict.update(row.get("skill_eligibility", []))
            elif classification == "BORDERLINE":
                self.rewrite.update(row.get("rewrite_skill_eligibility", []))
            else:
                self.reasons.update(reasons)
            buckets[classification].append(_contract_sample(row))
        return {
            name: fullfix._sample_strata(rows, self.sample_limit)
            for name, rows in buckets.items()
        }


def run_replay(
    *,
    repo_root: Path,
    index_path: Path,
    output_dir: Path,
    contract_path: Path = DEFAULT_CONTRACT,
    approval_path: Path = DEFAULT_APPROVAL,
    max_records: int | None = None,
    sample_limit: int = 30,
    progress_every: int = 50_000,
) -> dict[str, Any]:
    contract = _load_json(contract_path)
    approval = _load_json(approval_path)
    approval_validation = verify_operator_approval(contract, approval)
    profiles, runtime_lexicon = fullfix.build_unit_profiles(repo_root, limit=1)
    profile = _contract_profile(profiles[0], contract)
    if profile.unit_id != content_contract.UNIT_ID:
        raise ReplayError("UNIT01_PROFILE_ID_MISMATCH")
    lexicon = _contract_lexicon(runtime_lexicon, contract)
    acc = ContractAccumulator(profile, lexicon, sample_limit, contract=contract)
    scanned = 0
    for record in base.iter_query_index(index_path):
        scanned += 1
        text = base.extract_text(record)
        level = base._first(record, fullfix.LEVEL_KEYS).upper()
        source_type = base._first(record, fullfix.TYPE_KEYS)
        acc.counts["raw_records_scanned"] += 1
        if (
            level not in fullfix.DIRECT_LEVELS | fullfix.REWRITE_LEVELS
            or source_type not in fullfix.VALID_TYPES
            or len(fullfix.WORD_RE.findall(text)) < 3
        ):
            reason = "SOURCE_OR_TEXT_PREFILTER_FAILED"
            acc.counts["prefilter_reject_record_count"] += 1
            acc.reasons[reason] += 1
            if len(acc.rejects) < sample_limit:
                acc.rejects.append(
                    {
                        "classification": "REJECT",
                        "reasons": [reason],
                        "source_level": level,
                        "source_type": source_type,
                        "source_path": base._first(record, fullfix.PATH_KEYS),
                        "source_record_id": base._first(record, fullfix.LINEAGE_KEYS),
                        "text_excerpt": text[:600],
                    }
                )
        else:
            windows = fullfix.candidate_windows(text, profile)
            if not windows:
                acc.counts["no_candidate_window_record_count"] += 1
                acc.reasons["NO_TARGET_WINDOW"] += 1
            else:
                acc.counts["source_records_with_candidate_windows"] += 1
                acc.counts["candidate_windows_generated"] += len(windows)
                for window in windows:
                    acc.add(fullfix._result(record, text, window, profile, lexicon))
        if progress_every and scanned % progress_every == 0:
            print(f"PROGRESS_RECORDS_SCANNED={scanned}")
        if max_records is not None and scanned >= max_records:
            break
    if not scanned:
        raise ReplayError("QUERY_INDEX_EMPTY")
    samples = acc.finish()
    unit = {
        "unit_profile": profile.as_dict(),
        "filter_funnel": dict(sorted(acc.counts.items())),
        "rejection_reasons": dict(acc.reasons.most_common()),
        "strict_skill_capacity": dict(acc.strict.most_common()),
        "rewrite_skill_capacity": dict(acc.rewrite.most_common()),
        "source_level_distribution": dict(sorted(acc.levels.items())),
        "source_type_distribution": dict(acc.types.most_common()),
        "samples": samples,
    }
    validation = {
        **approval_validation,
        "unit_count": 1,
        "unit01_only": True,
        "contract_profile_overlay_applied": (
            "UNIT01_OPERATOR_APPROVED_CONTENT_CONTRACT" in profile.authority_sources
        ),
        "contract_material_gate_applied": True,
        "semantic_group_lineage_recovery_applied": True,
        "windowed_filter_applied": True,
        "canonical_content_modified": False,
        "unit02_to_unit24_modified": False,
        "a2_unlocked": False,
    }
    boolean_gates = (
        "operator_approval_verified",
        "unit01_only",
        "contract_profile_overlay_applied",
        "contract_material_gate_applied",
        "semantic_group_lineage_recovery_applied",
        "windowed_filter_applied",
    )
    if not all(validation[key] is True for key in boolean_gates):
        raise ReplayError("CONTRACT_AWARE_REPLAY_VALIDATION_FAILED")
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / OUTPUT_REPORT
    validation_path = output_dir / OUTPUT_VALIDATION
    matrix_path = output_dir / OUTPUT_MATRIX
    report = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "scope": {
            "allowed_units": [content_contract.UNIT_ID],
            "blocked_units": "UNIT_02_TO_UNIT_24",
            "a2_status": "LOCKED",
            "canonical_promotion": False,
            "learner_facing_content_write": False,
        },
        "inputs": {
            "query_index_path": str(index_path),
            "repo_root": str(repo_root),
            "contract_path": str(contract_path),
            "approval_path": str(approval_path),
            "approved_contract_sha256": contract["contract_sha256"],
            "effective_lexicon_size": len(lexicon),
        },
        "records_scanned": scanned,
        "partial_scan": max_records is not None and scanned >= max_records,
        "unit": unit,
        "validation": validation,
        "outputs": {
            "report": str(report_path),
            "validation": str(validation_path),
            "capacity_matrix": str(matrix_path),
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    validation_path.write_text(
        json.dumps(
            {
                "schema_version": SCHEMA_VERSION,
                "task_id": TASK_ID,
                "status": PASS_STATUS,
                "records_scanned": scanned,
                "validation": validation,
                "next_short_step": NEXT_SHORT_STEP,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    fields = [
        "unit_id",
        "sequence_order",
        "level",
        "raw_records_scanned",
        "source_records_with_candidate_windows",
        "candidate_windows_generated",
        "eligible_projection_distinct_count",
        "eligible_semantic_distinct_count",
        "lineage_group_recovered_count",
        "pass_count",
        "borderline_count",
        "reject_count",
        "reading_source_eligible_capacity",
        "listening_script_eligible_capacity",
        "speaking_prompt_eligible_capacity",
        "writing_seed_eligible_capacity",
        "reading_rewrite_candidate_capacity",
        "listening_rewrite_candidate_capacity",
        "speaking_rewrite_candidate_capacity",
        "writing_rewrite_candidate_capacity",
    ]
    with matrix_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        funnel = unit["filter_funnel"]
        strict = unit["strict_skill_capacity"]
        rewrite = unit["rewrite_skill_capacity"]
        writer.writerow(
            {
                "unit_id": profile.unit_id,
                "sequence_order": profile.order,
                "level": profile.level,
                **{key: funnel.get(key, 0) for key in fields if key in funnel},
                "reading_source_eligible_capacity": strict.get("READING_SOURCE_ELIGIBLE", 0),
                "listening_script_eligible_capacity": strict.get("LISTENING_SCRIPT_ELIGIBLE", 0),
                "speaking_prompt_eligible_capacity": strict.get("SPEAKING_PROMPT_ELIGIBLE", 0),
                "writing_seed_eligible_capacity": strict.get("WRITING_SEED_ELIGIBLE", 0),
                "reading_rewrite_candidate_capacity": rewrite.get("READING_REWRITE_CANDIDATE", 0),
                "listening_rewrite_candidate_capacity": rewrite.get("LISTENING_REWRITE_CANDIDATE", 0),
                "speaking_rewrite_candidate_capacity": rewrite.get("SPEAKING_REWRITE_CANDIDATE", 0),
                "writing_rewrite_candidate_capacity": rewrite.get("WRITING_REWRITE_CANDIDATE", 0),
            }
        )
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--index-path", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--approval", type=Path, default=DEFAULT_APPROVAL)
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
            max_records=args.max_records,
            sample_limit=args.sample_limit,
            progress_every=args.progress_every,
        )
    except (ReplayError, fullfix.CalibrationError, ValueError, KeyError, TypeError) as exc:
        print("STATUS=FAIL_A1FS_V1_RAZQ01B_UNIT01_CONTRACT_AWARE_REPLAY")
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
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
